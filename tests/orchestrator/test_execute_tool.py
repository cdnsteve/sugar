"""
Tests for ToolOrchestrator.execute_tool method.

Tests the execution of individual external tools via subprocess.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from sugar.discovery.external_tool_config import ExternalToolConfig
from sugar.discovery.orchestrator import ToolOrchestrator


class TestToolOrchestratorExecuteTool:
    """Tests for execute_tool method"""

    def test_execute_tool_success(self, temp_dir: Path):
        """Test successful tool execution"""
        tool = ExternalToolConfig(name="echo", command="echo hello")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            # Mock the subprocess to return successfully
            mock_run.return_value = Mock(
                stderr="",
                returncode=0,
            )
            result = orchestrator.execute_tool(tool)

        assert result.name == "echo"
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.success is True
        assert result.timed_out is False
        assert result.tool_not_found is False
        # Output file should exist
        assert result.output_path is not None
        assert result.output_path.exists()

        # Cleanup
        orchestrator.cleanup()

    def test_execute_tool_with_findings(self, temp_dir: Path):
        """Test tool execution with non-zero exit (findings)"""
        tool = ExternalToolConfig(name="eslint", command="npx eslint .")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stderr="",
                returncode=1,  # Linters exit 1 when they find issues
            )
            result = orchestrator.execute_tool(tool)

        # Success should be True because the tool ran successfully
        # (non-zero exit just means issues were found)
        assert result.success is True
        assert result.exit_code == 1
        assert result.output_path is not None

        # Cleanup
        orchestrator.cleanup()

    def test_execute_tool_timeout(self, temp_dir: Path):
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

        # Cleanup
        orchestrator.cleanup()

    def test_execute_tool_not_found(self, temp_dir: Path):
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
        # No output file when tool not found
        assert result.output_path is None

        # Cleanup
        orchestrator.cleanup()

    def test_execute_tool_os_error(self, temp_dir: Path):
        """Test tool execution with OS error"""
        tool = ExternalToolConfig(name="test", command="test cmd")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            with patch("shutil.which", return_value="/usr/bin/test"):
                mock_run.side_effect = OSError("Permission denied")
                result = orchestrator.execute_tool(tool)

        assert result.success is False
        assert "Permission denied" in result.stderr

        # Cleanup
        orchestrator.cleanup()

    def test_execute_tool_unexpected_error(self, temp_dir: Path):
        """Test tool execution with unexpected error"""
        tool = ExternalToolConfig(name="test", command="test cmd")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            with patch("shutil.which", return_value="/usr/bin/test"):
                mock_run.side_effect = RuntimeError("Unexpected!")
                result = orchestrator.execute_tool(tool)

        assert result.success is False
        assert "Unexpected" in result.error_message

        # Cleanup
        orchestrator.cleanup()

    def test_execute_tool_custom_timeout(self, temp_dir: Path):
        """Test tool execution with custom timeout override"""
        tool = ExternalToolConfig(name="echo", command="echo hello")
        orchestrator = ToolOrchestrator(
            [tool], working_dir=temp_dir, default_timeout=300
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stderr="", returncode=0)
            orchestrator.execute_tool(tool, timeout=60)

        # Verify subprocess was called with the overridden timeout
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 60

        # Cleanup
        orchestrator.cleanup()

    def test_execute_tool_uses_shell(self, temp_dir: Path):
        """Test that tool execution uses shell mode"""
        tool = ExternalToolConfig(name="echo", command="echo hello")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stderr="", returncode=0)
            orchestrator.execute_tool(tool)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["shell"] is True
        # Now we use stdout=file instead of capture_output
        assert "stdout" in call_kwargs
        assert call_kwargs["text"] is True

        # Cleanup
        orchestrator.cleanup()

    def test_execute_tool_uses_working_dir(self, temp_dir: Path):
        """Test that tool execution uses specified working directory"""
        tool = ExternalToolConfig(name="pwd", command="pwd")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stderr="", returncode=0)
            orchestrator.execute_tool(tool)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == temp_dir

        # Cleanup
        orchestrator.cleanup()

    def test_execute_tool_with_env_vars(self, temp_dir: Path):
        """Test tool execution with environment variables in command"""
        import os

        with patch.dict(os.environ, {"MY_FLAG": "--verbose"}):
            tool = ExternalToolConfig(name="test", command="test $MY_FLAG")
            orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

            with patch("subprocess.run") as mock_run:
                with patch("shutil.which", return_value="/usr/bin/test"):
                    mock_run.return_value = Mock(stderr="", returncode=0)
                    result = orchestrator.execute_tool(tool)

            # Verify command was expanded
            assert result.command == "test --verbose"

            # Cleanup
            orchestrator.cleanup()

    def test_execute_tool_creates_temp_dir(self, temp_dir: Path):
        """Test that execute_tool creates a temp directory for output"""
        tool = ExternalToolConfig(name="echo", command="echo hello")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        assert orchestrator.temp_dir is None

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stderr="", returncode=0)
            result = orchestrator.execute_tool(tool)

        # Temp dir should now exist
        assert orchestrator.temp_dir is not None
        assert orchestrator.temp_dir.exists()
        assert result.output_path is not None
        assert result.output_path.parent == orchestrator.temp_dir

        # Cleanup
        orchestrator.cleanup()
        assert orchestrator.temp_dir is None

    def test_execute_tool_output_file_naming(self, temp_dir: Path):
        """Test that output files are named after the tool"""
        tool = ExternalToolConfig(name="myeslint", command="npx eslint .")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stderr="", returncode=0)
            result = orchestrator.execute_tool(tool)

        assert result.output_path is not None
        assert "myeslint" in result.output_path.name

        # Cleanup
        orchestrator.cleanup()
