"""
Tests for ToolOrchestrator.execute_all method.

Tests the execution of multiple external tools in sequence.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from sugar.discovery.external_tool_config import ExternalToolConfig
from sugar.discovery.orchestrator import ToolOrchestrator


class TestToolOrchestratorExecuteAll:
    """Tests for execute_all method"""

    def test_execute_all_empty_tools(self, temp_dir: Path):
        """Test execute_all with no tools configured"""
        orchestrator = ToolOrchestrator([], working_dir=temp_dir)
        results = orchestrator.execute_all()
        assert results == []

    def test_execute_all_multiple_tools(self, temp_dir: Path):
        """Test execute_all with multiple tools"""
        tools = [
            ExternalToolConfig(name="tool1", command="echo one"),
            ExternalToolConfig(name="tool2", command="echo two"),
            ExternalToolConfig(name="tool3", command="echo three"),
        ]
        orchestrator = ToolOrchestrator(tools, working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(stderr="", returncode=0),
                Mock(stderr="", returncode=0),
                Mock(stderr="", returncode=0),
            ]
            results = orchestrator.execute_all()

        assert len(results) == 3
        assert results[0].name == "tool1"
        assert results[1].name == "tool2"
        assert results[2].name == "tool3"
        # All should have output paths
        assert results[0].output_path is not None
        assert results[1].output_path is not None
        assert results[2].output_path is not None

        # Cleanup
        orchestrator.cleanup()

    def test_execute_all_continues_after_failure(self, temp_dir: Path):
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
                    Mock(stderr="", returncode=0),
                    # bad_tool never reaches subprocess
                    Mock(stderr="", returncode=0),
                ]
                results = orchestrator.execute_all()

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[1].tool_not_found is True
        assert results[2].success is True

        # Cleanup
        orchestrator.cleanup()

    def test_execute_all_with_mixed_exit_codes(self, temp_dir: Path):
        """Test execute_all with tools having different exit codes"""
        tools = [
            ExternalToolConfig(name="linter1", command="linter1 ."),
            ExternalToolConfig(name="linter2", command="linter2 ."),
        ]
        orchestrator = ToolOrchestrator(tools, working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            with patch("shutil.which", return_value="/usr/bin/linter"):
                mock_run.side_effect = [
                    Mock(stderr="", returncode=0),
                    Mock(stderr="", returncode=1),
                ]
                results = orchestrator.execute_all()

        # Both should be marked as success (tool ran, captured output)
        assert results[0].success is True
        assert results[0].exit_code == 0
        assert results[1].success is True
        assert results[1].exit_code == 1

        # Cleanup
        orchestrator.cleanup()

    def test_execute_all_custom_timeout(self, temp_dir: Path):
        """Test execute_all with custom timeout per tool"""
        tools = [ExternalToolConfig(name="tool", command="echo test")]
        orchestrator = ToolOrchestrator(
            tools, working_dir=temp_dir, default_timeout=300
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stderr="", returncode=0)
            orchestrator.execute_all(timeout_per_tool=60)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 60

        # Cleanup
        orchestrator.cleanup()

    def test_execute_all_shares_temp_dir(self, temp_dir: Path):
        """Test that all tools share the same temp directory"""
        tools = [
            ExternalToolConfig(name="tool1", command="echo one"),
            ExternalToolConfig(name="tool2", command="echo two"),
        ]
        orchestrator = ToolOrchestrator(tools, working_dir=temp_dir)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(stderr="", returncode=0),
                Mock(stderr="", returncode=0),
            ]
            results = orchestrator.execute_all()

        # All output files should be in the same temp directory
        assert results[0].output_path.parent == results[1].output_path.parent
        assert results[0].output_path.parent == orchestrator.temp_dir

        # Cleanup
        orchestrator.cleanup()
