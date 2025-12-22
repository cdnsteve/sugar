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
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Type

# Claude Agent SDK imports
# The SDK provides query() as an async generator for streaming responses
from claude_agent_sdk import (
    ClaudeAgentOptions,
    HookMatcher,
    query,
)

# Message types for parsing responses - SDK uses dicts, but may have type classes
try:
    from claude_agent_sdk.types import (
        AssistantMessage,
        TextBlock,
        ToolUseBlock,
        ToolResultBlock,
        ResultMessage,
        SystemMessage,
    )

    SDK_HAS_TYPES = True
except ImportError:
    # SDK returns plain dicts, define helper types
    AssistantMessage = dict
    TextBlock = dict
    ToolUseBlock = dict
    ToolResultBlock = dict
    ResultMessage = dict
    SystemMessage = dict
    SDK_HAS_TYPES = False

from .hooks import QualityGateHooks, HookContext
from .context_manager import ContextManager
from ..utils.toon_encoder import execution_history_to_toon, work_queue_to_toon

logger = logging.getLogger(__name__)


# Transient errors that warrant retry
TRANSIENT_ERRORS = (
    "rate_limit",
    "timeout",
    "connection",
    "temporarily unavailable",
    "overloaded",
    "503",
    "429",
)


def is_transient_error(error: Exception) -> bool:
    """Check if an error is transient and worth retrying."""
    error_str = str(error).lower()
    return any(term in error_str for term in TRANSIENT_ERRORS)


async def retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> Any:
    """
    Execute an async function with exponential backoff retry.

    Args:
        func: Async callable to execute
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds

    Returns:
        Result from successful function execution

    Raises:
        Last exception if all retries fail
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_error = e
            if attempt == max_retries or not is_transient_error(e):
                raise

            delay = min(base_delay * (2**attempt), max_delay)
            logger.warning(
                f"Transient error (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                f"Retrying in {delay:.1f}s..."
            )
            await asyncio.sleep(delay)

    raise last_error


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

    # Retry settings for transient errors
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 30.0

    # Context management settings
    context_token_threshold: int = 150000
    context_preserve_recent: int = 10
    context_summarization_enabled: bool = True


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
    - Streaming responses
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
        self.hooks = QualityGateHooks(self.quality_gates_config)
        self._session_active = False
        self._execution_history: List[Dict[str, Any]] = []
        self._current_options: Optional[ClaudeAgentOptions] = None

        # Initialize context manager for automatic summarization
        self.context_manager = ContextManager(
            token_threshold=config.context_token_threshold,
            preserve_recent=config.context_preserve_recent,
        )

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

    def _build_options(self, task_context: Optional[str] = None) -> ClaudeAgentOptions:
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
        """
        Initialize agent session with configured options.

        The SDK uses query() as an async generator, so we just prepare
        the options here for use in execute().
        """
        if self._session_active:
            await self.end_session()

        self._current_options = self._build_options(task_context)
        self._session_active = True
        self.hooks.reset()  # Reset tracking state for new session
        logger.info("Sugar agent session started")

    async def end_session(self) -> None:
        """End the current agent session"""
        if self._session_active:
            self._session_active = False
            self._current_options = None
            # Export context state before clearing (could be persisted)
            context_stats = self.context_manager.get_stats()
            logger.info(
                f"Sugar agent session ended. Context stats: "
                f"{context_stats['total_messages']} messages, "
                f"{context_stats['total_tokens_saved']} tokens saved"
            )

    def get_context_stats(self) -> Dict[str, Any]:
        """Get current context statistics"""
        return self.context_manager.get_stats()

    def clear_context(self) -> None:
        """Clear the context history"""
        self.context_manager.clear()
        logger.info("Context cleared")

    async def _execute_with_streaming(
        self,
        prompt: str,
        options: ClaudeAgentOptions,
    ) -> tuple:
        """
        Internal method to execute query with streaming.

        Returns tuple of (content_parts, tool_uses, files_modified).
        Separated for retry logic.
        """
        content_parts = []
        tool_uses = []
        files_modified = []

        # Use the SDK's query() function which returns an async generator
        async for message in query(prompt=prompt, options=options):
            # Handle different message types from the SDK
            # The SDK may return dicts or typed objects depending on version
            if SDK_HAS_TYPES and isinstance(message, AssistantMessage):
                # Typed SDK - iterate through content blocks
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

            elif isinstance(message, dict):
                # Dict-based SDK response
                msg_type = message.get("type", "")

                if msg_type == "assistant":
                    # Process content blocks
                    content = message.get("content", [])
                    for block in content:
                        block_type = block.get("type", "")
                        if block_type == "text":
                            content_parts.append(block.get("text", ""))
                        elif block_type == "tool_use":
                            tool_use = {
                                "tool": block.get("name", ""),
                                "input": block.get("input", {}),
                            }
                            tool_uses.append(tool_use)

                            # Track file modifications
                            tool_name = block.get("name", "")
                            if tool_name in ("Write", "Edit"):
                                file_path = block.get("input", {}).get("file_path")
                                if file_path and file_path not in files_modified:
                                    files_modified.append(file_path)

                elif msg_type == "text":
                    # Direct text message
                    content_parts.append(message.get("text", ""))

                elif msg_type == "result":
                    # Final result message
                    if message.get("content"):
                        content_parts.append(str(message.get("content", "")))

        return content_parts, tool_uses, files_modified

    async def execute(
        self,
        prompt: str,
        task_context: Optional[str] = None,
    ) -> AgentResponse:
        """
        Execute a task with the agent using Claude Agent SDK.

        Uses the SDK's query() function which returns an async generator
        for streaming responses. Includes retry logic for transient errors.

        Args:
            prompt: The task prompt to execute
            task_context: Optional additional context for the task

        Returns:
            AgentResponse with execution results
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Build options fresh if no session, or use existing
            if not self._session_active:
                await self.start_session(task_context)

            options = self._current_options

            # Track user message in context manager
            self.context_manager.add_message("user", prompt)

            # Execute with retry logic for transient errors
            async def do_query():
                return await self._execute_with_streaming(prompt, options)

            content_parts, tool_uses, files_modified = await retry_with_backoff(
                do_query,
                max_retries=self.config.max_retries,
                base_delay=self.config.retry_base_delay,
                max_delay=self.config.retry_max_delay,
            )

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Track assistant response in context manager
            assistant_content = "\n".join(content_parts)
            self.context_manager.add_message("assistant", assistant_content)

            # Trigger summarization if needed (async operation)
            if self.config.context_summarization_enabled:
                summary = await self.context_manager.trigger_summarization_if_needed()
                if summary:
                    logger.info(
                        f"Context summarized: {summary.original_token_count} -> "
                        f"{summary.summarized_token_count} tokens "
                        f"({summary.messages_summarized} messages)"
                    )

            # Get quality gate results from hooks
            quality_gate_results = self.hooks.get_execution_summary()

            response = AgentResponse(
                success=True,
                content=assistant_content,
                tool_uses=tool_uses,
                files_modified=files_modified,
                execution_time=execution_time,
                quality_gate_results=quality_gate_results,
            )

            # Store in execution history
            self._execution_history.append(
                {
                    "prompt": prompt,
                    "response": response.to_dict(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            logger.info(
                f"Task completed in {execution_time:.2f}s, "
                f"{len(tool_uses)} tool uses, "
                f"{len(files_modified)} files modified"
            )

            return response

        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(f"Agent execution error: {e}")

            return AgentResponse(
                success=False,
                content="",
                execution_time=execution_time,
                error=str(e),
            )

    async def execute_work_item(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "work_item_id": work_item.get("id"),
            "execution_time": response.execution_time,
            "output": response.content,
            "files_changed": response.files_modified,
            "actions_taken": [f"Used {tu['tool']}" for tu in response.tool_uses],
            "summary": self._extract_summary(response.content),
            "agent_sdk": True,
            "quality_gate_results": response.quality_gate_results,
            "error": response.error,
        }

    def _build_work_item_prompt(self, work_item: Dict[str, Any]) -> str:
        """Build prompt from work item with TOON-encoded context"""
        prompt = f"""# Task: {work_item.get('title', 'Development Task')}

## Type: {work_item.get('type', 'feature')}
## Priority: {work_item.get('priority', 3)}/5

## Description
{work_item.get('description', 'No description provided.')}

"""
        # Add execution history in TOON format if available
        if self._execution_history:
            # Convert execution history to TOON format
            history_data = [
                {
                    "title": h.get("prompt", "")[:50],
                    "success": h.get("response", {}).get("success", False),
                    "execution_time": h.get("response", {}).get("execution_time", 0),
                    "files_modified": h.get("response", {}).get("files_modified", []),
                }
                for h in self._execution_history[-5:]  # Last 5 entries
            ]
            toon_history = execution_history_to_toon(history_data)
            prompt += f"""## Recent Execution History (TOON format)
{toon_history}

"""

        prompt += """## Instructions
Please complete this task by:
1. Analyzing the requirements
2. Implementing the solution
3. Testing if applicable
4. Providing a summary of changes

Focus on the specific requirements and follow existing code patterns.
"""
        return prompt

    def _build_work_item_context(self, work_item: Dict[str, Any]) -> str:
        """Build context from work item"""
        context_parts = [
            f"Task ID: {work_item.get('id', 'unknown')}",
            f"Source: {work_item.get('source', 'manual')}",
        ]

        if work_item.get("context"):
            import json

            context_parts.append(
                f"Additional Context: {json.dumps(work_item['context'])}"
            )

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
