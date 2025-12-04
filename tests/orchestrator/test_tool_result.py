"""
Tests for ToolResult dataclass.

Tests the ToolResult dataclass that holds the results of external tool execution.
"""

import tempfile
from pathlib import Path

import pytest

from sugar.discovery.orchestrator import ToolResult


class TestToolResult:
    """Tests for the ToolResult dataclass"""

    def test_tool_result_creation(self, tmp_path: Path):
        """Test basic ToolResult creation"""
        output_file = tmp_path / "output.txt"
        output_file.write_text("output")

        result = ToolResult(
            name="eslint",
            command="npx eslint .",
            output_path=output_file,
            stderr="",
            exit_code=0,
            success=True,
        )
        assert result.name == "eslint"
        assert result.command == "npx eslint ."
        assert result.stdout == "output"
        assert result.output_path == output_file
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.success is True

    def test_tool_result_defaults(self, tmp_path: Path):
        """Test ToolResult default values"""
        output_file = tmp_path / "output.txt"
        output_file.write_text("")

        result = ToolResult(
            name="test",
            command="test cmd",
            output_path=output_file,
            stderr="",
            exit_code=0,
            success=True,
        )
        assert result.duration_seconds == 0.0
        assert result.error_message is None
        assert result.timed_out is False
        assert result.tool_not_found is False

    def test_has_output_with_stdout(self, tmp_path: Path):
        """Test has_output property with stdout"""
        output_file = tmp_path / "output.txt"
        output_file.write_text("some output")

        result = ToolResult(
            name="test",
            command="cmd",
            output_path=output_file,
            stderr="",
            exit_code=0,
            success=True,
        )
        assert result.has_output is True

    def test_has_output_with_stderr(self, tmp_path: Path):
        """Test has_output property with stderr"""
        output_file = tmp_path / "output.txt"
        output_file.write_text("")

        result = ToolResult(
            name="test",
            command="cmd",
            output_path=output_file,
            stderr="error output",
            exit_code=0,
            success=True,
        )
        assert result.has_output is True

    def test_has_output_with_whitespace_only(self, tmp_path: Path):
        """Test has_output property with whitespace only"""
        output_file = tmp_path / "output.txt"
        output_file.write_text("   \n\t  ")

        result = ToolResult(
            name="test",
            command="cmd",
            output_path=output_file,
            stderr="",
            exit_code=0,
            success=True,
        )
        assert result.has_output is False

    def test_has_output_empty(self, tmp_path: Path):
        """Test has_output property with no output"""
        output_file = tmp_path / "output.txt"
        output_file.write_text("")

        result = ToolResult(
            name="test",
            command="cmd",
            output_path=output_file,
            stderr="",
            exit_code=0,
            success=True,
        )
        assert result.has_output is False

    def test_has_output_no_file(self):
        """Test has_output property when output_path is None"""
        result = ToolResult(
            name="test",
            command="cmd",
            output_path=None,
            stderr="",
            exit_code=0,
            success=True,
        )
        assert result.has_output is False
        assert result.stdout == ""

    def test_stdout_property_reads_file(self, tmp_path: Path):
        """Test that stdout property reads from the output file"""
        output_file = tmp_path / "output.txt"
        output_file.write_text("file content")

        result = ToolResult(
            name="test",
            command="cmd",
            output_path=output_file,
            stderr="",
            exit_code=0,
            success=True,
        )
        assert result.stdout == "file content"

        # Modify file and check that stdout reflects the change
        output_file.write_text("modified content")
        assert result.stdout == "modified content"

    def test_stdout_property_handles_missing_file(self, tmp_path: Path):
        """Test that stdout property returns empty string if file is deleted"""
        output_file = tmp_path / "output.txt"
        output_file.write_text("content")

        result = ToolResult(
            name="test",
            command="cmd",
            output_path=output_file,
            stderr="",
            exit_code=0,
            success=True,
        )
        assert result.stdout == "content"

        # Delete file
        output_file.unlink()
        assert result.stdout == ""

    def test_to_dict(self, tmp_path: Path):
        """Test to_dict serialization"""
        output_file = tmp_path / "output.txt"
        output_file.write_text("output")

        result = ToolResult(
            name="eslint",
            command="npx eslint .",
            output_path=output_file,
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


class TestToolResultSerialization:
    """Tests for ToolResult serialization"""

    def test_to_dict_complete(self, tmp_path: Path):
        """Test complete serialization of ToolResult"""
        output_file = tmp_path / "output.txt"
        output_file.write_text("Test output\nLine 2")

        result = ToolResult(
            name="test_tool",
            command="test --verbose",
            output_path=output_file,
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
            output_path=None,
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
        assert d["stdout"] == ""
