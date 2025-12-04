"""
Tool Orchestrator - Executes external code quality tools and captures their raw output

This module provides orchestration for executing configured external tools
via subprocess and capturing their stdout/stderr without any parsing or modification.
"""

import logging
import subprocess
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from .external_tool_config import ExternalToolConfig

logger = logging.getLogger(__name__)

# Default timeout for tool execution (5 minutes)
DEFAULT_TIMEOUT_SECONDS = 300


@dataclass
class ToolResult:
    """Result of executing a single external tool"""

    name: str
    command: str
    stdout: str  # Raw output - NO parsing
    stderr: str
    exit_code: int
    success: bool
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    timed_out: bool = False
    tool_not_found: bool = False

    @property
    def has_output(self) -> bool:
        """Check if the tool produced any output"""
        return bool(self.stdout.strip() or self.stderr.strip())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "command": self.command,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "success": self.success,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "timed_out": self.timed_out,
            "tool_not_found": self.tool_not_found,
        }


class ToolOrchestrator:
    """
    Orchestrates execution of external code quality tools.

    Executes each configured tool via subprocess and captures their raw output
    without any parsing or modification. Handles errors gracefully and provides
    comprehensive result tracking.
    """

    def __init__(
        self,
        external_tools: List[ExternalToolConfig],
        working_dir: Optional[Path] = None,
        default_timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        """
        Initialize the orchestrator with tool configurations.

        Args:
            external_tools: List of validated ExternalToolConfig objects
            working_dir: Working directory for tool execution (defaults to cwd)
            default_timeout: Default timeout in seconds for tool execution
        """
        self.external_tools = external_tools
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        self.default_timeout = default_timeout

        logger.info(
            f"ToolOrchestrator initialized with {len(external_tools)} tools, "
            f"working_dir={self.working_dir}"
        )

    def execute_tool(
        self,
        tool_config: ExternalToolConfig,
        timeout: Optional[int] = None,
    ) -> ToolResult:
        """
        Execute a single tool and return its raw output.

        Args:
            tool_config: Configuration for the tool to execute
            timeout: Optional timeout override in seconds

        Returns:
            ToolResult containing raw stdout/stderr and execution metadata
        """
        timeout = timeout or self.default_timeout
        command = tool_config.get_expanded_command()

        logger.info(f"Executing tool '{tool_config.name}': {command}")

        # Check if the tool's executable exists
        executable = command.split()[0] if command else ""
        if not self._check_executable_exists(executable):
            logger.warning(
                f"Tool '{tool_config.name}' executable not found: {executable}"
            )
            return ToolResult(
                name=tool_config.name,
                command=command,
                stdout="",
                stderr=f"Executable not found: {executable}",
                exit_code=-1,
                success=False,
                error_message=f"Tool executable '{executable}' not found in PATH",
                tool_not_found=True,
            )

        start_time = datetime.now()

        try:
            # Execute the tool via shell to support piping and complex commands
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            duration = (datetime.now() - start_time).total_seconds()

            # Note: Many linters exit with non-zero when they find issues
            # This is expected behavior, so we still capture the output
            logger.info(
                f"Tool '{tool_config.name}' completed with exit code {result.returncode} "
                f"in {duration:.2f}s"
            )

            return ToolResult(
                name=tool_config.name,
                command=command,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                success=True,  # Execution succeeded even if exit code is non-zero
                duration_seconds=duration,
            )

        except subprocess.TimeoutExpired as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Tool '{tool_config.name}' timed out after {timeout}s")
            return ToolResult(
                name=tool_config.name,
                command=command,
                stdout=e.stdout or "" if hasattr(e, "stdout") and e.stdout else "",
                stderr=e.stderr or "" if hasattr(e, "stderr") and e.stderr else "",
                exit_code=-1,
                success=False,
                duration_seconds=duration,
                error_message=f"Tool execution timed out after {timeout} seconds",
                timed_out=True,
            )

        except OSError as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Tool '{tool_config.name}' failed with OS error: {e}")
            return ToolResult(
                name=tool_config.name,
                command=command,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                success=False,
                duration_seconds=duration,
                error_message=f"OS error executing tool: {e}",
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Tool '{tool_config.name}' failed with unexpected error: {e}")
            return ToolResult(
                name=tool_config.name,
                command=command,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                success=False,
                duration_seconds=duration,
                error_message=f"Unexpected error: {e}",
            )

    def execute_all(
        self,
        timeout_per_tool: Optional[int] = None,
    ) -> List[ToolResult]:
        """
        Execute all configured tools and return their results.

        Args:
            timeout_per_tool: Optional timeout override per tool in seconds

        Returns:
            List of ToolResult objects, one per configured tool
        """
        results: List[ToolResult] = []

        if not self.external_tools:
            logger.info("No external tools configured, nothing to execute")
            return results

        logger.info(f"Executing {len(self.external_tools)} configured tools")

        for tool_config in self.external_tools:
            result = self.execute_tool(tool_config, timeout=timeout_per_tool)
            results.append(result)

            # Log summary for each tool
            if result.success:
                status = "completed"
            elif result.timed_out:
                status = "timed out"
            elif result.tool_not_found:
                status = "not found"
            else:
                status = "failed"

            logger.info(
                f"Tool '{result.name}' {status}: "
                f"exit_code={result.exit_code}, "
                f"stdout_len={len(result.stdout)}, "
                f"stderr_len={len(result.stderr)}"
            )

        # Log summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        logger.info(f"Tool execution complete: {successful} succeeded, {failed} failed")

        return results

    def _check_executable_exists(self, executable: str) -> bool:
        """
        Check if an executable exists in PATH or as an absolute path.

        Args:
            executable: The executable name or path to check

        Returns:
            True if executable exists, False otherwise
        """
        if not executable:
            return False

        # Handle common package manager prefixes that don't need checking
        # These run their own checks and provide better error messages
        skip_check_prefixes = ("npx ", "npm ", "yarn ", "pnpm ", "bunx ")
        for prefix in skip_check_prefixes:
            if executable.startswith(prefix) or f" {prefix}" in executable:
                return True

        # Check if it's an absolute path
        if Path(executable).is_absolute():
            return Path(executable).exists()

        # Check if it's in PATH
        return shutil.which(executable) is not None

    def get_tool_names(self) -> List[str]:
        """Return list of configured tool names"""
        return [tool.name for tool in self.external_tools]

    def get_tool_count(self) -> int:
        """Return count of configured tools"""
        return len(self.external_tools)
