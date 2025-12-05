"""
Tests for ToolOrchestrator cleanup functionality.

Tests the temp directory management and cleanup handlers.
"""

import signal
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from sugar.discovery.external_tool_config import ExternalToolConfig
from sugar.discovery.orchestrator import ToolOrchestrator


class TestToolOrchestratorCleanup:
    """Tests for cleanup functionality"""

    def test_cleanup_removes_temp_dir(self, temp_dir: Path):
        """Test that cleanup removes the temp directory"""
        tool = ExternalToolConfig(name="echo", command="echo hello")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        # Execute a tool to create the temp dir
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stderr="", returncode=0)
            orchestrator.execute_tool(tool)

        # Temp dir should exist
        assert orchestrator.temp_dir is not None
        temp_dir_path = orchestrator.temp_dir
        assert temp_dir_path.exists()

        # Cleanup
        orchestrator.cleanup()

        # Temp dir should be removed
        assert orchestrator.temp_dir is None
        assert not temp_dir_path.exists()

    def test_cleanup_is_idempotent(self, temp_dir: Path):
        """Test that cleanup can be called multiple times safely"""
        tool = ExternalToolConfig(name="echo", command="echo hello")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        # Execute a tool to create the temp dir
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stderr="", returncode=0)
            orchestrator.execute_tool(tool)

        # Multiple cleanup calls should not raise
        orchestrator.cleanup()
        orchestrator.cleanup()
        orchestrator.cleanup()

        assert orchestrator.temp_dir is None

    def test_cleanup_on_no_temp_dir(self, temp_dir: Path):
        """Test that cleanup handles case where no temp dir was created"""
        orchestrator = ToolOrchestrator([], working_dir=temp_dir)

        # No temp dir created
        assert orchestrator.temp_dir is None

        # Cleanup should not raise
        orchestrator.cleanup()
        assert orchestrator.temp_dir is None

    def test_ensure_temp_dir_creates_dir(self, temp_dir: Path):
        """Test that _ensure_temp_dir creates the directory"""
        tool = ExternalToolConfig(name="echo", command="echo hello")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        assert orchestrator.temp_dir is None

        result_dir = orchestrator._ensure_temp_dir()

        assert orchestrator.temp_dir is not None
        assert result_dir == orchestrator.temp_dir
        assert result_dir.exists()
        assert "discover_" in result_dir.name

        # Cleanup
        orchestrator.cleanup()

    def test_ensure_temp_dir_reuses_existing(self, temp_dir: Path):
        """Test that _ensure_temp_dir reuses existing directory"""
        tool = ExternalToolConfig(name="echo", command="echo hello")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        # Create temp dir
        first_dir = orchestrator._ensure_temp_dir()

        # Call again
        second_dir = orchestrator._ensure_temp_dir()

        # Should be the same directory
        assert first_dir == second_dir

        # Cleanup
        orchestrator.cleanup()

    def test_signal_handlers_registered(self, temp_dir: Path):
        """Test that signal handlers are registered on init"""
        tool = ExternalToolConfig(name="echo", command="echo hello")

        # Capture original handlers
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)

        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        # New handlers should be the orchestrator's handler
        current_sigint = signal.getsignal(signal.SIGINT)
        current_sigterm = signal.getsignal(signal.SIGTERM)

        assert current_sigint == orchestrator._signal_handler
        assert current_sigterm == orchestrator._signal_handler

        # Original handlers should be stored
        assert orchestrator._original_sigint_handler == original_sigint
        assert orchestrator._original_sigterm_handler == original_sigterm

        # Restore handlers (cleanup would normally do this on signal)
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)

    def test_decode_stderr_with_string(self, temp_dir: Path):
        """Test _decode_stderr with string input"""
        tool = ExternalToolConfig(name="echo", command="echo hello")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        result = orchestrator._decode_stderr("error message")
        assert result == "error message"

    def test_decode_stderr_with_bytes(self, temp_dir: Path):
        """Test _decode_stderr with bytes input"""
        tool = ExternalToolConfig(name="echo", command="echo hello")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        result = orchestrator._decode_stderr(b"error message")
        assert result == "error message"

    def test_decode_stderr_with_none(self, temp_dir: Path):
        """Test _decode_stderr with None input"""
        tool = ExternalToolConfig(name="echo", command="echo hello")
        orchestrator = ToolOrchestrator([tool], working_dir=temp_dir)

        result = orchestrator._decode_stderr(None)
        assert result == ""

    def test_output_files_cleaned_up(self, temp_dir: Path):
        """Test that output files are cleaned up with temp dir"""
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

        # Collect output paths
        output_paths = [r.output_path for r in results]
        assert all(p is not None for p in output_paths)
        assert all(p.exists() for p in output_paths)

        # Cleanup
        orchestrator.cleanup()

        # All output files should be gone
        assert all(not p.exists() for p in output_paths)
