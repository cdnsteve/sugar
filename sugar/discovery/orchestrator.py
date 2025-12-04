"""
Tool Orchestrator - Executes external code quality tools and captures their raw output

This module provides orchestration for executing configured external tools
via subprocess and capturing their stdout/stderr without any parsing or modification.
"""

import atexit
import logging
import shutil
import signal
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import FrameType
from typing import Any, Dict, List, Optional

from .external_tool_config import ExternalToolConfig

logger = logging.getLogger(__name__)

# Default timeout for tool execution (5 minutes)
DEFAULT_TIMEOUT_SECONDS = 300


@dataclass
class ToolResult:
    """Result of executing a single external tool.

    Output is stored in a temporary file to avoid memory issues with large outputs.
    The stdout property provides backward-compatible access by reading from the file.
    """

    name: str
    command: str
    output_path: Optional[Path]  # Path to temp file containing stdout
    stderr: str  # Keep stderr in memory (usually small)
    exit_code: int
    success: bool
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    timed_out: bool = False
    tool_not_found: bool = False

    @property
    def stdout(self) -> str:
        """Read stdout from the output file.

        Returns:
            The contents of the output file, or empty string if no file exists.
        """
        if self.output_path and self.output_path.exists():
            try:
                return self.output_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return ""
        return ""

    @property
    def has_output(self) -> bool:
        """Check if the tool produced any output."""
        return bool(self.stdout.strip() or self.stderr.strip())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "command": self.command,
            "stdout": self.stdout,  # Read from file for serialization
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
        self.temp_dir: Optional[Path] = None
        # Signal handlers can be callable, int (SIG_DFL/SIG_IGN), or None
        self._original_sigint_handler: Any = None
        self._original_sigterm_handler: Any = None

        # Register cleanup handlers
        self._setup_cleanup_handlers()

        logger.info(
            f"ToolOrchestrator initialized with {len(external_tools)} tools, "
            f"working_dir={self.working_dir}"
        )

    def _setup_cleanup_handlers(self) -> None:
        """Register cleanup handlers for signals and atexit."""
        # Register atexit handler
        atexit.register(self.cleanup)

        # Store original signal handlers and register our own
        self._original_sigint_handler = signal.getsignal(signal.SIGINT)
        self._original_sigterm_handler = signal.getsignal(signal.SIGTERM)

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum: int, frame: Optional[FrameType]) -> None:
        """Handle signals by cleaning up and re-raising.

        Args:
            signum: The signal number received
            frame: The current stack frame
        """
        logger.info(f"Received signal {signum}, cleaning up temp directory")
        self.cleanup()

        # Restore and call original handler
        original_handler = (
            self._original_sigint_handler
            if signum == signal.SIGINT
            else self._original_sigterm_handler
        )
        if callable(original_handler):
            original_handler(signum, frame)
        elif original_handler == signal.SIG_DFL:
            # Default behavior - re-raise the signal
            signal.signal(signum, signal.SIG_DFL)
            signal.raise_signal(signum)

    def _ensure_temp_dir(self) -> Path:
        """Create temp directory if not exists.

        Returns:
            Path to the temp directory
        """
        if not self.temp_dir or not self.temp_dir.exists():
            self.temp_dir = Path(tempfile.mkdtemp(prefix="sugar_discover_"))
            logger.debug(f"Created temp directory: {self.temp_dir}")
        return self.temp_dir

    def cleanup(self) -> None:
        """Remove temp directory and all contents.

        Safe to call multiple times.
        """
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                logger.debug(f"Cleaned up temp directory: {self.temp_dir}")
            except OSError as e:
                logger.warning(f"Failed to clean up temp directory: {e}")
            finally:
                self.temp_dir = None

    @staticmethod
    def _decode_stderr(stderr: Any) -> str:
        """Decode stderr to string, handling bytes or None.

        Args:
            stderr: The stderr value (can be str, bytes, or None)

        Returns:
            The stderr as a string
        """
        if stderr is None:
            return ""
        if isinstance(stderr, bytes):
            return stderr.decode("utf-8", errors="replace")
        return str(stderr)

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
            return self._create_not_found_result(tool_config.name, command, executable)

        # Create output file for stdout
        temp_dir = self._ensure_temp_dir()
        output_path = temp_dir / f"{tool_config.name}_output.txt"

        start_time = datetime.now()

        try:
            result = self._run_subprocess(command, timeout, output_path)
            duration = (datetime.now() - start_time).total_seconds()
            return self._create_success_result(
                tool_config.name, command, result, duration, output_path
            )

        except subprocess.TimeoutExpired as e:
            duration = (datetime.now() - start_time).total_seconds()
            return self._handle_timeout_error(
                tool_config.name, command, timeout, e, duration, output_path
            )

        except OSError as e:
            duration = (datetime.now() - start_time).total_seconds()
            return self._handle_os_error(tool_config.name, command, e, duration)

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return self._handle_unexpected_error(tool_config.name, command, e, duration)

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

    def _run_subprocess(
        self, command: str, timeout: int, output_path: Path
    ) -> "subprocess.CompletedProcess[str]":
        """
        Execute a subprocess command with the configured settings.

        Writes stdout directly to the output file to avoid memory issues
        with large outputs.

        Args:
            command: The command to execute
            timeout: Timeout in seconds
            output_path: Path to write stdout to

        Returns:
            CompletedProcess result from subprocess.run
        """
        with open(output_path, "w", encoding="utf-8") as stdout_file:
            return subprocess.run(
                command,
                shell=True,
                cwd=self.working_dir,
                stdout=stdout_file,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )

    def _create_not_found_result(
        self, name: str, command: str, executable: str
    ) -> ToolResult:
        """
        Create a ToolResult for when the executable is not found.

        Args:
            name: Tool name
            command: The command that was attempted
            executable: The executable that was not found

        Returns:
            ToolResult indicating tool not found
        """
        logger.warning(f"Tool '{name}' executable not found: {executable}")
        return ToolResult(
            name=name,
            command=command,
            output_path=None,
            stderr=f"Executable not found: {executable}",
            exit_code=-1,
            success=False,
            error_message=f"Tool executable '{executable}' not found in PATH",
            tool_not_found=True,
        )

    def _create_success_result(
        self,
        name: str,
        command: str,
        result: "subprocess.CompletedProcess[str]",
        duration: float,
        output_path: Path,
    ) -> ToolResult:
        """
        Create a ToolResult for successful tool execution.

        Args:
            name: Tool name
            command: The command that was executed
            result: The subprocess result
            duration: Execution duration in seconds
            output_path: Path to the file containing stdout

        Returns:
            ToolResult with captured output
        """
        # Note: Many linters exit with non-zero when they find issues
        # This is expected behavior, so we still capture the output
        logger.info(
            f"Tool '{name}' completed with exit code {result.returncode} "
            f"in {duration:.2f}s"
        )
        return ToolResult(
            name=name,
            command=command,
            output_path=output_path,
            stderr=result.stderr or "",
            exit_code=result.returncode,
            success=True,  # Execution succeeded even if exit code is non-zero
            duration_seconds=duration,
        )

    def _handle_timeout_error(
        self,
        name: str,
        command: str,
        timeout: int,
        error: subprocess.TimeoutExpired,
        duration: float,
        output_path: Path,
    ) -> ToolResult:
        """
        Handle timeout exception and create appropriate ToolResult.

        Args:
            name: Tool name
            command: The command that was executed
            timeout: The timeout that was exceeded
            error: The TimeoutExpired exception
            duration: Execution duration in seconds
            output_path: Path to the file containing stdout (may have partial output)

        Returns:
            ToolResult indicating timeout
        """
        logger.error(f"Tool '{name}' timed out after {timeout}s")
        return ToolResult(
            name=name,
            command=command,
            output_path=output_path if output_path.exists() else None,
            stderr=self._decode_stderr(getattr(error, "stderr", None)),
            exit_code=-1,
            success=False,
            duration_seconds=duration,
            error_message=f"Tool execution timed out after {timeout} seconds",
            timed_out=True,
        )

    def _handle_os_error(
        self, name: str, command: str, error: OSError, duration: float
    ) -> ToolResult:
        """
        Handle OS error and create appropriate ToolResult.

        Args:
            name: Tool name
            command: The command that was executed
            error: The OSError exception
            duration: Execution duration in seconds

        Returns:
            ToolResult indicating OS error
        """
        logger.error(f"Tool '{name}' failed with OS error: {error}")
        return ToolResult(
            name=name,
            command=command,
            output_path=None,
            stderr=str(error),
            exit_code=-1,
            success=False,
            duration_seconds=duration,
            error_message=f"OS error executing tool: {error}",
        )

    def _handle_unexpected_error(
        self, name: str, command: str, error: Exception, duration: float
    ) -> ToolResult:
        """
        Handle unexpected exception and create appropriate ToolResult.

        Args:
            name: Tool name
            command: The command that was executed
            error: The exception that occurred
            duration: Execution duration in seconds

        Returns:
            ToolResult indicating unexpected error
        """
        logger.error(f"Tool '{name}' failed with unexpected error: {error}")
        return ToolResult(
            name=name,
            command=command,
            output_path=None,
            stderr=str(error),
            exit_code=-1,
            success=False,
            duration_seconds=duration,
            error_message=f"Unexpected error: {error}",
        )

    def get_tool_names(self) -> List[str]:
        """Return list of configured tool names"""
        return [tool.name for tool in self.external_tools]

    def get_tool_count(self) -> int:
        """Return count of configured tools"""
        return len(self.external_tools)
