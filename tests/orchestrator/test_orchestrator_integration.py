"""
Integration tests for ToolOrchestrator.

Tests the orchestrator with real commands to verify end-to-end behavior.
"""

import pytest

from sugar.discovery.external_tool_config import ExternalToolConfig
from sugar.discovery.orchestrator import ToolOrchestrator


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
