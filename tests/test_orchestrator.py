"""
Tests for Tool Orchestrator

Tests the ToolOrchestrator class that executes external code quality tools
and captures their raw output via subprocess.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from sugar.discovery.orchestrator import (
    ToolOrchestrator,
    ToolResult,
    DEFAULT_TIMEOUT_SECONDS,
)
from sugar.discovery.external_tool_config import ExternalToolConfig


class TestToolResult:
    """Tests for the ToolResult dataclass"""

    def test_tool_result_creation(self):
        """Test basic ToolResult creation"""
        result = ToolResult(
            name="eslint",
            command="npx eslint .",
            stdout="output",
            stderr="",
            exit_code=0,
            success=True,
        )
        assert result.name == "eslint"
        assert result.command == "npx eslint ."
        assert result.stdout == "output"
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.success is True

    def test_tool_result_defaults(self):
        """Test ToolResult default values"""
        result = ToolResult(
            name="test",
            command="test cmd",
            stdout="",
            stderr="",
            exit_code=0,
            success=True,
        )
        assert result.duration_seconds == 0.0
        assert result.error_message is None
        assert result.timed_out is False
        assert result.tool_not_found is False

    def test_has_output_with_stdout(self):
        """Test has_output property with stdout"""
        result = ToolResult(
            name="test",
            command="cmd",
            stdout="some output",
            stderr="",
            exit_code=0,
            success=True,
        )
        assert result.has_output is True

    def test_has_output_with_stderr(self):
        """Test has_output property with stderr"""
        result = ToolResult(
            name="test",
            command="cmd",
            stdout="",
            stderr="error output",
            exit_code=0,
            success=True,
        )
        assert result.has_output is True

    def test_has_output_with_whitespace_only(self):
        """Test has_output property with whitespace only"""
        result = ToolResult(
            name="test",
            command="cmd",
            stdout="   \n\t  ",
            stderr="",
            exit_code=0,
            success=True,
        )
        assert result.has_output is False

    def test_has_output_empty(self):
        """Test has_output property with no output"""
        result = ToolResult(
            name="test",
            command="cmd",
            stdout="",
            stderr="",
            exit_code=0,
            success=True,
        )
        assert result.has_output is False

    def test_to_dict(self):
        """Test to_dict serialization"""
        result = ToolResult(
            name="eslint",
            command="npx eslint .",
            stdout="output",
            stderr="errors",
            exit_code=1,
            success=True,
            duration_seconds=2.5,
            error_message=None,
            timed_out=False,
            tool_not_found=False,
        )
        d = result.to_dict()
        assert d["name"] == "eslint"
        assert d["command"] == "npx eslint ."
        assert d["stdout"] == "output"
        assert d["stderr"] == "errors"
        assert d["exit_code"] == 1
        assert d["success"] is True
        assert d["duration_seconds"] == 2.5
        assert d["error_message"] is None
        assert d["timed_out"] is False
        assert d["tool_not_found"] is False


class TestToolOrchestratorInit:
    """Tests for ToolOrchestrator initialization"""

    def test_init_with_tools(self, temp_dir):
        """Test orchestrator initialization with tools"""
        tools = [
            ExternalToolConfig(name="eslint", command="npx eslint ."),
            ExternalToolConfig(name="ruff", command="ruff check ."),
        ]
        orchestrator = ToolOrchestrator(tools, working_dir=temp_dir)
        assert len(orchestrator.external_tools) == 2
        assert orchestrator.working_dir == temp_dir
        assert orchestrator.default_timeout == DEFAULT_TIMEOUT_SECONDS

    def test_init_without_tools(self, temp_dir):
        """Test orchestrator initialization without tools"""
        orchestrator = ToolOrchestrator([], working_dir=temp_dir)
        assert len(orchestrator.external_tools) == 0

    def test_init_with_custom_timeout(self, temp_dir):
        """Test orchestrator with custom timeout"""
        orchestrator = ToolOrchestrator([], working_dir=temp_dir, default_timeout=60)
        assert orchestrator.default_timeout == 60

    def test_init_uses_cwd_when_no_working_dir(self):
        """Test orchestrator uses cwd when working_dir not specified"""
        orchestrator = ToolOrchestrator([])
        assert orchestrator.working_dir == Path.cwd()

    def test_get_tool_names(self, temp_dir):
        """Test get_tool_names method"""
        tools = [
            ExternalToolConfig(name="eslint", command="npx eslint ."),
            ExternalToolConfig(name="ruff", command="ruff check ."),
        ]
        orchestrator = ToolOrchestrator(tools, working_dir=temp_dir)
        names = orchestrator.get_tool_names()
        assert names == ["eslint", "ruff"]

    def test_get_tool_count(self, temp_dir):
        """Test get_tool_count method"""
        tools = [
            ExternalToolConfig(name="eslint", command="npx eslint ."),
            ExternalToolConfig(name="ruff", command="ruff check ."),
        ]
        orchestrator = ToolOrchestrator(tools, working_dir=temp_dir)
        assert orchestrator.get_tool_count() == 2


class TestToolOrchestratorExecuteTool:
    """Tests for execute_tool method"""

    def test_execute_tool_success(self, temp_dir):
        """Test successful tool execution"""
        tool = ExternalToolConfig(name="echo", command="echo hello")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="hello\n",
                stderr="",
                returncode=0,
            )
            result = orchestrator.execute_tool(tool)

        assert result.name == "echo"
        assert result.stdout == "hello\n"
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.success is True
        assert result.timed_out is False
        assert result.tool_not_found is False

    def test_execute_tool_with_findings(self, temp_dir):
        """Test tool execution with non-zero exit (findings)"""
        tool = ExternalToolConfig(name="eslint", command="npx eslint .")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout='[{"ruleId":"no-unused-vars","message":"x is defined but never used"}]',
                stderr="",
                returncode=1,  # Linters exit 1 when they find issues
            )
            result = orchestrator.execute_tool(tool)

        # Success should be True because the tool ran successfully
        # (non-zero exit just means issues were found)
        assert result.success is True
        assert result.exit_code == 1
        assert "no-unused-vars" in result.stdout

    def test_execute_tool_timeout(self, temp_dir):
        """Test tool execution timeout"""
        tool = ExternalToolConfig(name="slow", command="sleep 100")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir, default_timeout=1)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep 100", timeout=1)
            result = orchestrator.execute_tool(tool)

        assert result.success is False
        assert result.timed_out is True
        assert result.exit_code == -1
        assert "timed out" in result.error_message

    def test_execute_tool_not_found(self, temp_dir):
        """Test tool execution when executable not found"""
        tool = ExternalToolConfig(
            name="nonexistent", command="nonexistent_tool --version"
        )
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        with patch("shutil.which", return_value=None):
            result = orchestrator.execute_tool(tool)

        assert result.success is False
        assert result.tool_not_found is True
        assert result.exit_code == -1
        assert "not found" in result.error_message.lower()

    def test_execute_tool_os_error(self, temp_dir):
        """Test tool execution with OS error"""
        tool = ExternalToolConfig(name="test", command="test cmd")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            with patch("shutil.which", return_value="/usr/bin/test"):
                mock_run.side_effect = OSError("Permission denied")
                result = orchestrator.execute_tool(tool)

        assert result.success is False
        assert "Permission denied" in result.stderr

    def test_execute_tool_unexpected_error(self, temp_dir):
        """Test tool execution with unexpected error"""
        tool = ExternalToolConfig(name="test", command="test cmd")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            with patch("shutil.which", return_value="/usr/bin/test"):
                mock_run.side_effect = RuntimeError("Unexpected!")
                result = orchestrator.execute_tool(tool)

        assert result.success is False
        assert "Unexpected" in result.error_message

    def test_execute_tool_custom_timeout(self, temp_dir):
        """Test tool execution with custom timeout override"""
        tool = ExternalToolConfig(name="echo", command="echo hello")
        orchestrator = ToolOrchestrator(
            [tool], working_dir=temp_dir, default_timeout=300
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="hello\n", stderr="", returncode=0)
            orchestrator.execute_tool(tool, timeout=60)

        # Verify subprocess was called with the overridden timeout
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 60

    def test_execute_tool_uses_shell(self, temp_dir):
        """Test that tool execution uses shell mode"""
        tool = ExternalToolConfig(name="echo", command="echo hello")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="hello\n", stderr="", returncode=0)
            orchestrator.execute_tool(tool)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["shell"] is True
        assert call_kwargs["capture_output"] is True
        assert call_kwargs["text"] is True

    def test_execute_tool_uses_working_dir(self, temp_dir):
        """Test that tool execution uses specified working directory"""
        tool = ExternalToolConfig(name="pwd", command="pwd")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=str(temp_dir), stderr="", returncode=0)
            orchestrator.execute_tool(tool)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == temp_dir

    def test_execute_tool_with_env_vars(self, temp_dir):
        """Test tool execution with environment variables in command"""
        import os

        with patch.dict(os.environ, {"MY_FLAG": "--verbose"}):
            tool = ExternalToolConfig(name="test", command="test $MY_FLAG")
            orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

            with patch("subprocess.run") as mock_run:
                with patch("shutil.which", return_value="/usr/bin/test"):
                    mock_run.return_value = Mock(stdout="", stderr="", returncode=0)
                    result = orchestrator.execute_tool(tool)

            # Verify command was expanded
            assert result.command == "test --verbose"


class TestToolOrchestratorExecuteAll:
    """Tests for execute_all method"""

    def test_execute_all_empty_tools(self, temp_dir):
        """Test execute_all with no tools configured"""
        orchestrator = ToolOrchestrator([], working_dir=temp_dir)
        results = orchestrator.execute_all()
        assert results == []

    def test_execute_all_multiple_tools(self, temp_dir):
        """Test execute_all with multiple tools"""
        tools = [
            ExternalToolConfig(name="tool1", command="echo one"),
            ExternalToolConfig(name="tool2", command="echo two"),
            ExternalToolConfig(name="tool3", command="echo three"),
        ]
        orchestrator = ToolOrchestrator(tools, working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(stdout="one\n", stderr="", returncode=0),
                Mock(stdout="two\n", stderr="", returncode=0),
                Mock(stdout="three\n", stderr="", returncode=0),
            ]
            results = orchestrator.execute_all()

        assert len(results) == 3
        assert results[0].name == "tool1"
        assert results[0].stdout == "one\n"
        assert results[1].name == "tool2"
        assert results[1].stdout == "two\n"
        assert results[2].name == "tool3"
        assert results[2].stdout == "three\n"

    def test_execute_all_continues_after_failure(self, temp_dir):
        """Test that execute_all continues after a tool failure"""
        tools = [
            ExternalToolConfig(name="good1", command="echo good1"),
            ExternalToolConfig(name="bad", command="bad_tool"),
            ExternalToolConfig(name="good2", command="echo good2"),
        ]
        orchestrator = ToolOrchestrator(tools, working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            with patch("shutil.which") as mock_which:
                # First tool exists, second doesn't, third exists
                mock_which.side_effect = [
                    "/usr/bin/echo",  # good1 exists
                    None,  # bad doesn't exist
                    "/usr/bin/echo",  # good2 exists
                ]
                mock_run.side_effect = [
                    Mock(stdout="good1\n", stderr="", returncode=0),
                    # bad_tool never reaches subprocess
                    Mock(stdout="good2\n", stderr="", returncode=0),
                ]
                results = orchestrator.execute_all()

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[1].tool_not_found is True
        assert results[2].success is True

    def test_execute_all_with_mixed_exit_codes(self, temp_dir):
        """Test execute_all with tools having different exit codes"""
        tools = [
            ExternalToolConfig(name="linter1", command="linter1 ."),
            ExternalToolConfig(name="linter2", command="linter2 ."),
        ]
        orchestrator = ToolOrchestrator(tools, working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            with patch("shutil.which", return_value="/usr/bin/linter"):
                mock_run.side_effect = [
                    Mock(stdout="no issues", stderr="", returncode=0),
                    Mock(stdout="found 3 issues", stderr="", returncode=1),
                ]
                results = orchestrator.execute_all()

        # Both should be marked as success (tool ran, captured output)
        assert results[0].success is True
        assert results[0].exit_code == 0
        assert results[1].success is True
        assert results[1].exit_code == 1

    def test_execute_all_custom_timeout(self, temp_dir):
        """Test execute_all with custom timeout per tool"""
        tools = [ExternalToolConfig(name="tool", command="echo test")]
        orchestrator = ToolOrchestrator(
            tools, working_dir=temp_dir, default_timeout=300
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="test\n", stderr="", returncode=0)
            orchestrator.execute_all(timeout_per_tool=60)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 60


class TestToolOrchestratorCheckExecutable:
    """Tests for _check_executable_exists method"""

    def test_check_npx_command_skipped(self, temp_dir):
        """Test that npx commands skip executable check"""
        orchestrator = ToolOrchestrator([], working_dir=temp_dir)
        # npx commands should always return True (they manage their own checks)
        assert orchestrator._check_executable_exists("npx eslint") is True
        assert orchestrator._check_executable_exists("npm run lint") is True
        assert orchestrator._check_executable_exists("yarn lint") is True
        assert orchestrator._check_executable_exists("pnpm exec eslint") is True
        assert orchestrator._check_executable_exists("bunx lint") is True

    def test_check_absolute_path_exists(self, temp_dir):
        """Test checking absolute path that exists"""
        # Create a test file
        test_file = temp_dir / "test_exe"
        test_file.touch()

        orchestrator = ToolOrchestrator([], working_dir=temp_dir)
        assert orchestrator._check_executable_exists(str(test_file)) is True

    def test_check_absolute_path_not_exists(self, temp_dir):
        """Test checking absolute path that doesn't exist"""
        orchestrator = ToolOrchestrator([], working_dir=temp_dir)
        assert (
            orchestrator._check_executable_exists("/nonexistent/path/to/tool") is False
        )

    def test_check_command_in_path(self, temp_dir):
        """Test checking command in PATH"""
        orchestrator = ToolOrchestrator([], working_dir=temp_dir)
        with patch("shutil.which", return_value="/usr/bin/ruff"):
            assert orchestrator._check_executable_exists("ruff") is True

    def test_check_command_not_in_path(self, temp_dir):
        """Test checking command not in PATH"""
        orchestrator = ToolOrchestrator([], working_dir=temp_dir)
        with patch("shutil.which", return_value=None):
            assert orchestrator._check_executable_exists("nonexistent_tool") is False

    def test_check_empty_executable(self, temp_dir):
        """Test checking empty executable"""
        orchestrator = ToolOrchestrator([], working_dir=temp_dir)
        assert orchestrator._check_executable_exists("") is False


class TestToolOrchestratorIntegration:
    """Integration tests for ToolOrchestrator"""

    def test_real_echo_command(self, temp_dir):
        """Integration test with real echo command"""
        tool = ExternalToolConfig(name="echo", command="echo 'hello world'")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        result = orchestrator.execute_tool(tool)

        assert result.success is True
        assert "hello world" in result.stdout
        assert result.exit_code == 0

    def test_real_nonexistent_command(self, temp_dir):
        """Integration test with nonexistent command"""
        tool = ExternalToolConfig(
            name="nonexistent", command="definitely_not_a_real_command_12345"
        )
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        result = orchestrator.execute_tool(tool)

        assert result.success is False
        assert result.tool_not_found is True

    def test_real_command_with_stderr(self, temp_dir):
        """Integration test capturing stderr"""
        tool = ExternalToolConfig(name="stderr", command="echo error >&2")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        result = orchestrator.execute_tool(tool)

        assert result.success is True
        assert "error" in result.stderr

    def test_duration_tracking(self, temp_dir):
        """Test that duration is tracked"""
        tool = ExternalToolConfig(name="sleep", command="sleep 0.1")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        result = orchestrator.execute_tool(tool)

        assert result.duration_seconds >= 0.1
        assert result.duration_seconds < 1.0  # Should complete quickly


class TestToolResultSerialization:
    """Tests for ToolResult serialization"""

    def test_to_dict_complete(self):
        """Test complete serialization of ToolResult"""
        result = ToolResult(
            name="test_tool",
            command="test --verbose",
            stdout="Test output\nLine 2",
            stderr="Warning: something",
            exit_code=2,
            success=True,
            duration_seconds=1.234,
            error_message=None,
            timed_out=False,
            tool_not_found=False,
        )

        d = result.to_dict()

        # All fields should be present
        assert set(d.keys()) == {
            "name",
            "command",
            "stdout",
            "stderr",
            "exit_code",
            "success",
            "duration_seconds",
            "error_message",
            "timed_out",
            "tool_not_found",
        }

        # Values should match
        assert d["name"] == "test_tool"
        assert d["stdout"] == "Test output\nLine 2"
        assert d["exit_code"] == 2

    def test_to_dict_with_error(self):
        """Test serialization of failed ToolResult"""
        result = ToolResult(
            name="failed_tool",
            command="fail",
            stdout="",
            stderr="Error occurred",
            exit_code=-1,
            success=False,
            duration_seconds=0.5,
            error_message="Tool execution failed: Error occurred",
            timed_out=False,
            tool_not_found=True,
        )

        d = result.to_dict()

        assert d["success"] is False
        assert d["error_message"] == "Tool execution failed: Error occurred"
        assert d["tool_not_found"] is True
