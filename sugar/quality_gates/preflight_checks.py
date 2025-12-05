"""
Task Pre-Flight Checks - Feature 6: Pre-Flight Validation

Verifies environment is ready before starting task execution:
- Server/port availability
- Database accessibility
- Test suite runnability
- MCP tool availability
- Git working directory state
"""

import asyncio
import socket
from pathlib import Path
from typing import Any, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class PreFlightCheckResult:
    """Result of a pre-flight check"""

    def __init__(self, check_name: str, passed: bool, **kwargs: Any):
        self.name = check_name
        self.passed = passed
        self.metadata = kwargs

    def __repr__(self) -> str:
        """String representation for debugging"""
        status = "✅" if self.passed else "❌"
        return f"PreFlightCheckResult({status} {self.name})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "passed": self.passed,
            **self.metadata,
        }


class PreFlightChecker:
    """
    Validates environment is ready before task execution
    """

    def __init__(self, config: dict):
        """
        Initialize pre-flight checker

        Args:
            config: Configuration dictionary
        """
        preflight_config = config.get("pre_flight_checks", {})
        self.enabled = preflight_config.get("enabled", False)
        self.block_execution = preflight_config.get("block_execution_if_failed", True)
        self.checks_config = preflight_config.get("checks", [])

    def is_enabled(self) -> bool:
        """Check if pre-flight checks are enabled"""
        return self.enabled

    async def run_all_checks(
        self, task: Dict[str, Any]
    ) -> Tuple[bool, List[PreFlightCheckResult]]:
        """
        Run all pre-flight checks

        Args:
            task: Task dictionary

        Returns:
            Tuple of (all_passed, list of check results)
        """
        if not self.is_enabled():
            return True, []

        # Determine which checks are required for this task type
        task_type = task.get("type", "unknown")
        required_checks = self._get_required_checks_for_task(task_type)

        if not required_checks:
            logger.debug("No pre-flight checks required for this task")
            return True, []

        logger.info(f"🔍 Running {len(required_checks)} pre-flight checks")

        results = []
        for check_config in required_checks:
            result = await self._run_single_check(check_config)
            results.append(result)

        all_passed = all(r.passed for r in results)

        if all_passed:
            logger.info(f"✅ All {len(results)} pre-flight checks passed")
        else:
            failed = [r for r in results if not r.passed]
            logger.error(
                f"❌ {len(failed)} pre-flight checks failed: {[r.name for r in failed]}"
            )

        return all_passed, results

    async def _run_single_check(
        self, check_config: Dict[str, Any]
    ) -> PreFlightCheckResult:
        """
        Run a single pre-flight check

        Args:
            check_config: Check configuration

        Returns:
            PreFlightCheckResult
        """
        check_name = check_config.get("name")
        check_type = check_config.get("type")

        logger.debug(f"Running pre-flight check: {check_name} ({check_type})")

        if check_type == "port_check":
            return await self._check_port(check_config)
        elif check_type == "command":
            return await self._check_command(check_config)
        elif check_type == "tool_check":
            return await self._check_tools(check_config)
        elif check_type == "git_status":
            return await self._check_git_status(check_config)
        elif check_type == "file_exists":
            return await self._check_file_exists(check_config)
        else:
            logger.error(f"Unknown check type: {check_type}")
            return PreFlightCheckResult(
                check_name=check_name,
                passed=False,
                error=f"Unsupported check type: {check_type}",
            )

    async def _check_port(self, check_config: Dict[str, Any]) -> PreFlightCheckResult:
        """Check if a port is listening"""
        check_name = check_config.get("name", "port_check")
        port = check_config.get("port")
        host = check_config.get("host", "localhost")

        if port is None:
            return PreFlightCheckResult(
                check_name=check_name,
                passed=False,
                host=host,
                error="Port not specified in check configuration",
            )

        sock = None
        try:
            # Try to connect to the port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            listening = result == 0

            if listening:
                logger.debug(f"✅ Port check passed: {host}:{port} is listening")
            else:
                logger.warning(f"❌ Port check failed: {host}:{port} not listening")

            return PreFlightCheckResult(
                check_name=check_name,
                passed=listening,
                port=port,
                host=host,
                message=f"Port {port} {'is' if listening else 'is not'} listening on {host}",
            )

        except OSError as e:
            logger.error(f"Error checking port {port}: {e}")
            return PreFlightCheckResult(
                check_name=check_name,
                passed=False,
                port=port,
                host=host,
                error=str(e),
            )
        finally:
            if sock is not None:
                sock.close()

    async def _check_command(
        self, check_config: Dict[str, Any]
    ) -> PreFlightCheckResult:
        """Check if a command runs successfully"""
        check_name = check_config.get("name")
        command = check_config.get("command")
        timeout = check_config.get("timeout", 30)

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
                exit_code = process.returncode

                passed = exit_code == 0

                if passed:
                    logger.debug(f"✅ Command check passed: {command}")
                else:
                    logger.warning(
                        f"❌ Command check failed: {command} (exit code {exit_code})"
                    )

                return PreFlightCheckResult(
                    check_name=check_name,
                    passed=passed,
                    command=command,
                    exit_code=exit_code,
                    message=f"Command exited with code {exit_code}",
                )

            except asyncio.TimeoutError:
                logger.error(f"Command check timed out: {command}")
                process.kill()
                return PreFlightCheckResult(
                    check_name=check_name,
                    passed=False,
                    command=command,
                    error=f"Command timed out after {timeout}s",
                )

        except Exception as e:
            logger.error(f"Error running command check '{command}': {e}")
            return PreFlightCheckResult(
                check_name=check_name,
                passed=False,
                command=command,
                error=str(e),
            )

    async def _check_tools(self, check_config: Dict[str, Any]) -> PreFlightCheckResult:
        """Check if required tools are available"""
        check_name = check_config.get("name", "tool_check")
        tools = check_config.get("tools", [])

        if not tools:
            return PreFlightCheckResult(
                check_name=check_name,
                passed=True,
                available_tools=[],
                missing_tools=[],
                message="No tools to check",
            )

        async def check_single_tool(tool: str) -> Tuple[str, bool]:
            """Check if a single tool is executable"""
            try:
                process = await asyncio.create_subprocess_shell(
                    f"command -v {tool}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await process.communicate()
                return (tool, process.returncode == 0)
            except OSError:
                return (tool, False)

        # Run all tool checks in parallel for better performance
        results = await asyncio.gather(*[check_single_tool(tool) for tool in tools])

        available_tools = [tool for tool, available in results if available]
        missing_tools = [tool for tool, available in results if not available]

        passed = len(missing_tools) == 0

        if passed:
            logger.debug(f"✅ Tool check passed: all {len(tools)} tools available")
        else:
            logger.warning(
                f"❌ Tool check failed: missing tools: {', '.join(missing_tools)}"
            )

        return PreFlightCheckResult(
            check_name=check_name,
            passed=passed,
            available_tools=available_tools,
            missing_tools=missing_tools,
            message=f"{'All tools available' if passed else f'Missing: {missing_tools}'}",
        )

    async def _check_git_status(
        self, check_config: Dict[str, Any]
    ) -> PreFlightCheckResult:
        """Check git working directory state"""
        check_name = check_config.get("name")
        allow_untracked = check_config.get("allow_untracked", True)
        allow_unstaged = check_config.get("allow_unstaged", False)

        try:
            process = await asyncio.create_subprocess_shell(
                "git status --porcelain",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            output = stdout.decode("utf-8")

            # Parse git status output
            untracked = []
            unstaged = []
            staged = []

            for line in output.split("\n"):
                if not line.strip():
                    continue

                status = line[:2]
                file_path = line[3:].strip()

                if status == "??":
                    untracked.append(file_path)
                elif status[0] == " " and status[1] != " ":
                    unstaged.append(file_path)
                elif status[0] != " ":
                    staged.append(file_path)

            # Check if state is acceptable
            issues = []
            if not allow_untracked and untracked:
                issues.append(f"{len(untracked)} untracked files")
            if not allow_unstaged and unstaged:
                issues.append(f"{len(unstaged)} unstaged changes")

            passed = len(issues) == 0

            if passed:
                logger.debug(f"✅ Git status check passed")
            else:
                logger.warning(f"❌ Git status check failed: {', '.join(issues)}")

            return PreFlightCheckResult(
                check_name=check_name,
                passed=passed,
                untracked_count=len(untracked),
                unstaged_count=len(unstaged),
                staged_count=len(staged),
                message=f"{'Working directory clean' if passed else ', '.join(issues)}",
            )

        except Exception as e:
            logger.error(f"Error checking git status: {e}")
            return PreFlightCheckResult(
                check_name=check_name,
                passed=False,
                error=str(e),
            )

    async def _check_file_exists(
        self, check_config: Dict[str, Any]
    ) -> PreFlightCheckResult:
        """Check if a file exists"""
        check_name = check_config.get("name", "file_exists_check")
        file_path = check_config.get("file_path")

        if not file_path:
            return PreFlightCheckResult(
                check_name=check_name,
                passed=False,
                error="file_path not specified in check configuration",
            )

        try:
            exists = Path(file_path).exists()

            if exists:
                logger.debug(f"✅ File exists check passed: {file_path}")
            else:
                logger.warning(f"❌ File exists check failed: {file_path} not found")

            return PreFlightCheckResult(
                check_name=check_name,
                passed=exists,
                file_path=file_path,
                message=f"File {'exists' if exists else 'not found'}: {file_path}",
            )

        except OSError as e:
            logger.error(f"Error checking file existence: {e}")
            return PreFlightCheckResult(
                check_name=check_name,
                passed=False,
                file_path=file_path,
                error=str(e),
            )

    def _get_required_checks_for_task(self, task_type: str) -> List[Dict[str, Any]]:
        """
        Get required checks for a task type

        Args:
            task_type: Type of task (e.g., "bug_fix", "feature")

        Returns:
            List of check configurations required for this task
        """
        required_checks = []

        for check_config in self.checks_config:
            required_for = check_config.get("required_for", [])

            # Check if this check applies to this task type
            if "all_tasks" in required_for or task_type in required_for:
                required_checks.append(check_config)

        return required_checks
