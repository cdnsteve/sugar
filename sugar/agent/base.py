"""
SugarAgent - Base agent class using Claude Agent SDK

This is the core agent implementation for Sugar 3.0, providing:
- Native SDK-based execution (replacing subprocess wrapper)
- Hook-based quality gates integration
- MCP server support
- Continuous conversation sessions
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    HookMatcher,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)

from .hooks import QualityGateHooks

logger = logging.getLogger(__name__)


@dataclass
class SugarAgentConfig:
    """Configuration for SugarAgent"""

    # Model settings
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 8192

    # Permission mode: "default", "acceptEdits", "bypassPermissions"
    permission_mode: str = "acceptEdits"

    # Allowed tools (empty = all tools)
    allowed_tools: List[str] = field(default_factory=list)

    # MCP servers configuration
    mcp_servers: Dict[str, Any] = field(default_factory=dict)

    # Quality gates settings
    quality_gates_enabled: bool = True

    # System prompt additions
    system_prompt_additions: str = ""

    # Working directory
    working_directory: Optional[str] = None

    # Timeout for operations (seconds)
    timeout: int = 300


@dataclass
class AgentResponse:
    """Response from agent execution"""

    success: bool
    content: str
    tool_uses: List[Dict[str, Any]] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    error: Optional[str] = None
    quality_gate_results: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "content": self.content,
            "tool_uses": self.tool_uses,
            "files_modified": self.files_modified,
            "execution_time": self.execution_time,
            "error": self.error,
            "quality_gate_results": self.quality_gate_results,
        }


class SugarAgent:
    """
    Sugar's native agent implementation using Claude Agent SDK.

    This replaces the subprocess-based ClaudeWrapper with direct SDK integration,
    enabling:
    - Custom hooks for quality gates
    - MCP server integration
    - Observable execution
    - Continuous conversation context
    """

    def __init__(
        self,
        config: SugarAgentConfig,
        quality_gates_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the Sugar agent.

        Args:
            config: Agent configuration
            quality_gates_config: Optional quality gates configuration
        """
        self.config = config
        self.quality_gates_config = quality_gates_config or {}
        self.client: Optional[ClaudeSDKClient] = None
        self.hooks = QualityGateHooks(self.quality_gates_config)
        self._session_active = False
        self._execution_history: List[Dict[str, Any]] = []

        logger.debug(f"SugarAgent initialized with model: {config.model}")

    def _build_system_prompt(self, task_context: Optional[str] = None) -> str:
        """Build the system prompt for the agent"""
        base_prompt = """You are Sugar, an autonomous development assistant.

Your goal is to complete development tasks efficiently and correctly.
You have access to tools for reading, writing, and executing code.

Guidelines:
- Focus on the specific task requirements
- Follow existing code patterns and conventions
- Make actual file changes to complete tasks
- Test your changes when applicable
- Provide clear summaries of what was accomplished
"""

        if self.config.system_prompt_additions:
            base_prompt += f"\n\n{self.config.system_prompt_additions}"

        if task_context:
            base_prompt += f"\n\nTask Context:\n{task_context}"

        return base_prompt

    def _build_options(
        self, task_context: Optional[str] = None
    ) -> ClaudeAgentOptions:
        """Build ClaudeAgentOptions with hooks and configuration"""
        hooks_config = {}

        if self.config.quality_gates_enabled:
            # PreToolUse hooks for validation before tool execution
            pre_tool_hooks = [
                HookMatcher(
                    matcher="Write|Edit|Bash",
                    hooks=[self.hooks.pre_tool_security_check],
                    timeout=60,
                ),
            ]

            # PostToolUse hooks for auditing after tool execution
            post_tool_hooks = [
                HookMatcher(
                    hooks=[self.hooks.post_tool_audit],
                    timeout=60,
                ),
            ]

            hooks_config = {
                "PreToolUse": pre_tool_hooks,
                "PostToolUse": post_tool_hooks,
            }

        options = ClaudeAgentOptions(
            system_prompt=self._build_system_prompt(task_context),
            allowed_tools=self.config.allowed_tools or None,
            permission_mode=self.config.permission_mode,
            mcp_servers=self.config.mcp_servers or None,
            hooks=hooks_config if hooks_config else None,
        )

        return options

    async def start_session(self, task_context: Optional[str] = None) -> None:
        """Start a new agent session"""
        if self._session_active:
            await self.end_session()

        options = self._build_options(task_context)
        self.client = ClaudeSDKClient(options=options)
        await self.client.__aenter__()
        self._session_active = True
        logger.info("Sugar agent session started")

    async def end_session(self) -> None:
        """End the current agent session"""
        if self.client and self._session_active:
            await self.client.__aexit__(None, None, None)
            self._session_active = False
            self.client = None
            logger.info("Sugar agent session ended")

    async def execute(
        self,
        prompt: str,
        task_context: Optional[str] = None,
    ) -> AgentResponse:
        """
        Execute a task with the agent.

        Args:
            prompt: The task prompt to execute
            task_context: Optional additional context for the task

        Returns:
            AgentResponse with execution results
        """
        start_time = datetime.utcnow()

        try:
            # Start session if not active
            if not self._session_active:
                await self.start_session(task_context)

            # Send the prompt
            await self.client.query(prompt)

            # Collect response
            content_parts = []
            tool_uses = []
            files_modified = []

            async for message in self.client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            content_parts.append(block.text)
                        elif isinstance(block, ToolUseBlock):
                            tool_use = {
                                "tool": block.name,
                                "input": block.input,
                            }
                            tool_uses.append(tool_use)

                            # Track file modifications
                            if block.name in ("Write", "Edit"):
                                file_path = block.input.get("file_path")
                                if file_path and file_path not in files_modified:
                                    files_modified.append(file_path)

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Get quality gate results from hooks
            quality_gate_results = self.hooks.get_execution_summary()

            response = AgentResponse(
                success=True,
                content="\n".join(content_parts),
                tool_uses=tool_uses,
                files_modified=files_modified,
                execution_time=execution_time,
                quality_gate_results=quality_gate_results,
            )

            # Store in execution history
            self._execution_history.append({
                "prompt": prompt,
                "response": response.to_dict(),
                "timestamp": datetime.utcnow().isoformat(),
            })

            logger.info(
                f"Task completed in {execution_time:.2f}s, "
                f"{len(tool_uses)} tool uses, "
                f"{len(files_modified)} files modified"
            )

            return response

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Agent execution error: {e}")

            return AgentResponse(
                success=False,
                content="",
                execution_time=execution_time,
                error=str(e),
            )

    async def execute_work_item(
        self, work_item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a Sugar work item (compatibility with existing workflow).

        Args:
            work_item: Work item dictionary from Sugar's work queue

        Returns:
            Result dictionary compatible with existing Sugar workflow
        """
        # Build prompt from work item
        prompt = self._build_work_item_prompt(work_item)
        task_context = self._build_work_item_context(work_item)

        # Execute
        response = await self.execute(prompt, task_context)

        # Convert to legacy format for compatibility
        return {
            "success": response.success,
            "result": {
                "stdout": response.content,
                "execution_time": response.execution_time,
            },
            "timestamp": datetime.utcnow().isoformat(),
            "work_item_id": work_item.get("id"),
            "execution_time": response.execution_time,
            "output": response.content,
            "files_changed": response.files_modified,
            "actions_taken": [
                f"Used {tu['tool']}" for tu in response.tool_uses
            ],
            "summary": self._extract_summary(response.content),
            "agent_sdk": True,
            "quality_gate_results": response.quality_gate_results,
            "error": response.error,
        }

    def _build_work_item_prompt(self, work_item: Dict[str, Any]) -> str:
        """Build prompt from work item"""
        return f"""# Task: {work_item.get('title', 'Development Task')}

## Type: {work_item.get('type', 'feature')}
## Priority: {work_item.get('priority', 3)}/5

## Description
{work_item.get('description', 'No description provided.')}

## Instructions
Please complete this task by:
1. Analyzing the requirements
2. Implementing the solution
3. Testing if applicable
4. Providing a summary of changes

Focus on the specific requirements and follow existing code patterns.
"""

    def _build_work_item_context(self, work_item: Dict[str, Any]) -> str:
        """Build context from work item"""
        context_parts = [
            f"Task ID: {work_item.get('id', 'unknown')}",
            f"Source: {work_item.get('source', 'manual')}",
        ]

        if work_item.get("context"):
            import json
            context_parts.append(f"Additional Context: {json.dumps(work_item['context'])}")

        return "\n".join(context_parts)

    def _extract_summary(self, content: str) -> str:
        """Extract summary from response content"""
        if not content:
            return ""

        # Take first paragraph or first 200 chars
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                return line[:200]
        return content[:200]

    async def __aenter__(self) -> "SugarAgent":
        """Async context manager entry"""
        await self.start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit"""
        await self.end_session()

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get execution history for this session"""
        return self._execution_history.copy()
