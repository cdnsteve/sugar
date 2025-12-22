"""
Agent SDK Executor - Native Claude Agent SDK integration for Sugar 3.0

This executor replaces the subprocess-based ClaudeWrapper with direct
Claude Agent SDK integration, providing:
- Native Python SDK execution
- Hook-based quality gates
- MCP server support
- Observable execution
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseExecutor, ExecutionResult
from ..agent import SugarAgent, SugarAgentConfig
from ..storage import IssueResponseManager
from ..profiles import IssueResponderProfile
from ..config import IssueResponderConfig
from ..integrations import GitHubClient

logger = logging.getLogger(__name__)


class AgentSDKExecutor(BaseExecutor):
    """
    Executor implementation using the Claude Agent SDK.

    This is Sugar 3.0's primary executor, providing native SDK-based
    task execution with full control over agent behavior.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Agent SDK executor.

        Args:
            config: Configuration dictionary containing:
                - model: Claude model to use
                - timeout: Execution timeout in seconds
                - permission_mode: SDK permission mode
                - quality_gates: Quality gates configuration
                - mcp_servers: MCP server configurations
                - dry_run: Whether to simulate execution
        """
        super().__init__(config)

        # Agent configuration
        self.model = config.get("model", "claude-sonnet-4-20250514")
        self.timeout = config.get("timeout", 300)
        self.permission_mode = config.get("permission_mode", "acceptEdits")

        # Quality gates
        self.quality_gates_config = config.get("quality_gates", {})
        self.quality_gates_enabled = self.quality_gates_config.get("enabled", True)

        # MCP servers
        self.mcp_servers = config.get("mcp_servers", {})

        # Agent instance (lazy initialization)
        self._agent: Optional[SugarAgent] = None
        self._session_active = False

        logger.debug(f"AgentSDKExecutor initialized with model: {self.model}")
        logger.debug(f"Quality gates enabled: {self.quality_gates_enabled}")
        logger.debug(f"Dry run mode: {self.dry_run}")

    def _create_agent_config(self) -> SugarAgentConfig:
        """Create agent configuration from executor config"""
        return SugarAgentConfig(
            model=self.model,
            permission_mode=self.permission_mode,
            mcp_servers=self.mcp_servers,
            quality_gates_enabled=self.quality_gates_enabled,
            timeout=self.timeout,
        )

    async def _get_agent(self) -> SugarAgent:
        """Get or create the agent instance"""
        if self._agent is None:
            agent_config = self._create_agent_config()
            self._agent = SugarAgent(
                config=agent_config,
                quality_gates_config=self.quality_gates_config,
            )
        return self._agent

    async def _execute_issue_response(self, work_item: Dict) -> Dict:
        """Execute an issue response task using IssueResponderProfile"""
        # Extract issue data from work_item context
        context = work_item.get("context", {})
        issue_data = context.get("github_issue", {})
        repo = context.get("repo", "")

        # Load config
        config = IssueResponderConfig.load_from_file(".sugar/config.yaml")

        # Create profile with config settings
        profile = IssueResponderProfile()
        profile.config.settings["max_response_length"] = config.max_response_length
        profile.config.settings["auto_post_threshold"] = config.auto_post_threshold

        # Process input
        input_data = {"issue": issue_data, "repo": repo}
        processed = await profile.process_input(input_data)

        # Execute with agent
        agent_config = SugarAgentConfig(
            model=config.model,
            permission_mode="default",
            allowed_tools=["Read", "Glob", "Grep"],
            system_prompt_additions=profile.get_system_prompt({"repo": repo}),
        )

        agent = SugarAgent(agent_config)
        await agent.start_session()

        try:
            response = await agent.execute(processed["prompt"])
            output_data = {"content": response.content}
            result = await profile.process_output(output_data)

            response_data = result.get("response", {})
            confidence = response_data.get("confidence", 0.0)
            content = response_data.get("content", "")

            # Check if should auto-post
            should_post = confidence >= config.auto_post_threshold

            if should_post:
                # Post to GitHub
                client = GitHubClient(repo=repo)
                client.post_comment(issue_data["number"], content)

                # Record response
                manager = IssueResponseManager()
                await manager.initialize()
                await manager.record_response(
                    repo=repo,
                    issue_number=issue_data["number"],
                    response_type="initial",
                    confidence=confidence,
                    response_content=content,
                    labels_applied=response_data.get("suggested_labels", []),
                    was_auto_posted=True,
                    work_item_id=work_item.get("id"),
                )

            return {
                "success": True,
                "posted": should_post,
                "confidence": confidence,
                "content": content,
            }
        finally:
            await agent.end_session()

    async def execute_work(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a work item using the Claude Agent SDK.

        Args:
            work_item: Work item dictionary

        Returns:
            Result dictionary compatible with Sugar's workflow
        """
        # Check for specialized task types
        task_type = work_item.get("type", "")

        if task_type == "issue_response":
            return await self._execute_issue_response(work_item)

        if self.dry_run:
            logger.info(f"DRY RUN: Simulating execution of {work_item.get('title')}")
            return await self._simulate_execution(work_item)

        start_time = datetime.now(timezone.utc)

        try:
            agent = await self._get_agent()
            result = await agent.execute_work_item(work_item)

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Enhance result with executor metadata
            result["executor"] = "agent_sdk"
            result["model"] = self.model
            result["execution_time"] = execution_time

            logger.info(
                f"Task completed in {execution_time:.2f}s: "
                f"{work_item.get('title', 'unknown')}"
            )

            return result

        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(f"Agent SDK execution failed: {e}")

            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "work_item_id": work_item.get("id"),
                "execution_time": execution_time,
                "executor": "agent_sdk",
                "output": "",
                "files_changed": [],
                "actions_taken": [],
                "summary": f"Execution failed: {e}",
            }

    async def validate(self) -> bool:
        """
        Validate that the Agent SDK executor is properly configured.

        Returns:
            True if ready, False otherwise
        """
        try:
            # Try to import SDK
            from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

            logger.info("Claude Agent SDK is available")
            return True

        except ImportError as e:
            logger.error(f"Claude Agent SDK not installed: {e}")
            logger.error("Install with: pip install claude-agent-sdk")
            return False

        except Exception as e:
            logger.error(f"Agent SDK validation failed: {e}")
            return False

    async def start_session(self) -> None:
        """Start an agent session for continuous execution"""
        if not self._session_active:
            agent = await self._get_agent()
            await agent.start_session()
            self._session_active = True
            logger.info("Agent session started")

    async def end_session(self) -> None:
        """End the current agent session"""
        if self._agent and self._session_active:
            await self._agent.end_session()
            self._session_active = False
            logger.info("Agent session ended")

    async def execute_batch(
        self, work_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple work items in a single session.

        This maintains context between tasks within the same session.

        Args:
            work_items: List of work items to execute

        Returns:
            List of results for each work item
        """
        results = []

        try:
            await self.start_session()

            for work_item in work_items:
                result = await self.execute_work(work_item)
                results.append(result)

                # Check if we should stop (e.g., on failure)
                if not result.get("success") and self.config.get(
                    "stop_on_failure", False
                ):
                    logger.warning("Stopping batch execution due to failure")
                    break

        finally:
            await self.end_session()

        return results

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get execution history from the current session"""
        if self._agent:
            return self._agent.get_execution_history()
        return []

    async def __aenter__(self) -> "AgentSDKExecutor":
        """Async context manager entry"""
        await self.start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit"""
        await self.end_session()
