"""
Tests for Sugar core loop functionality
"""

import pytest
import asyncio
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from sugar.core.loop import SugarLoop


class TestSugarLoop:
    """Test SugarLoop core functionality"""

    def test_init_with_default_config(self, temp_dir):
        """Test SugarLoop initialization with default config path"""
        config_path = temp_dir / ".sugar" / "config.yaml"
        config_path.parent.mkdir()

        config_data = {
            "sugar": {
                "dry_run": True,
                "loop_interval": 300,
                "max_concurrent_work": 3,
                "claude": {"command": "claude"},
                "storage": {"database": "sugar.db"},
                "discovery": {
                    "error_logs": {"enabled": True},
                    "github": {"enabled": False},
                    "code_quality": {"enabled": True, "root_path": "."},
                    "test_coverage": {"enabled": True, "root_path": "."},
                },
            }
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper"),
            patch("sugar.core.loop.ErrorLogMonitor"),
            patch("sugar.core.loop.CodeQualityScanner"),
            patch("sugar.core.loop.TestCoverageAnalyzer"),
        ):

            loop = SugarLoop(str(config_path))
            assert loop.config == config_data
            assert not loop.running

    def test_config_loading_missing_file(self):
        """Test config loading with missing file"""
        with pytest.raises(FileNotFoundError):
            SugarLoop("/nonexistent/config.yaml")

    @patch("sugar.core.loop.WorkQueue")
    @patch("sugar.core.loop.ClaudeWrapper")
    @patch("sugar.core.loop.ErrorLogMonitor")
    def test_discovery_modules_initialization(
        self, mock_error_monitor, mock_claude, mock_queue, sugar_config_file
    ):
        """Test that discovery modules are initialized correctly"""
        loop = SugarLoop(str(sugar_config_file))

        # Check that enabled discovery modules are initialized
        assert hasattr(loop, "error_monitor")
        assert hasattr(loop, "quality_scanner")
        assert hasattr(loop, "coverage_analyzer")

        # GitHub should not be initialized (disabled in config)
        assert not hasattr(loop, "github_watcher")

    @pytest.mark.asyncio
    async def test_start_stop_loop(self, sugar_config_file):
        """Test starting and stopping the Sugar loop"""
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper"),
            patch("sugar.core.loop.ErrorLogMonitor"),
        ):

            loop = SugarLoop(str(sugar_config_file))

            # Mock the async methods
            loop._run_loop = AsyncMock()
            loop.work_queue.initialize = AsyncMock()
            loop.work_queue.close = AsyncMock()

            # Test start
            start_task = asyncio.create_task(loop.start())
            await asyncio.sleep(0.1)  # Let it start

            assert loop.running

            # Test stop
            await loop.stop()
            assert not loop.running

            # Clean up
            start_task.cancel()
            try:
                await start_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_discover_work(self, sugar_config_file):
        """Test work discovery functionality"""
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper"),
            patch("sugar.core.loop.ErrorLogMonitor") as mock_error_monitor,
            patch("sugar.core.loop.CodeQualityScanner") as mock_quality,
            patch("sugar.core.loop.TestCoverageAnalyzer") as mock_coverage,
        ):

            loop = SugarLoop(str(sugar_config_file))

            # Mock discovery results
            mock_error_monitor.return_value.discover_work.return_value = [
                {"type": "bug_fix", "title": "Fix error", "source": "error_log"}
            ]
            mock_quality.return_value.discover_work.return_value = [
                {"type": "refactor", "title": "Improve code", "source": "code_quality"}
            ]
            mock_coverage.return_value.discover_work.return_value = [
                {"type": "test", "title": "Add tests", "source": "test_coverage"}
            ]

            loop.work_queue.add_work = AsyncMock()

            await loop._discover_work()

            # Should have added 3 tasks (one from each discovery module)
            assert loop.work_queue.add_work.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_work(self, sugar_config_file):
        """Test work execution functionality"""
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper") as mock_claude,
            patch("sugar.core.loop.ErrorLogMonitor"),
        ):

            loop = SugarLoop(str(sugar_config_file))

            # Mock pending work
            mock_tasks = [
                {
                    "id": "task-1",
                    "type": "bug_fix",
                    "title": "Fix auth bug",
                    "description": "Fix authentication issues",
                    "priority": 5,
                }
            ]

            loop.work_queue.get_pending_work = AsyncMock(return_value=mock_tasks)
            loop.work_queue.mark_work_active = AsyncMock()
            loop.work_queue.mark_work_completed = AsyncMock()
            mock_claude.return_value.execute_task = AsyncMock(
                return_value={"success": True, "result": "Task completed successfully"}
            )

            await loop._execute_work()

            # Verify work was marked active and then completed
            loop.work_queue.mark_work_active.assert_called_once()
            loop.work_queue.mark_work_completed.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_work_failure(self, sugar_config_file):
        """Test work execution with failure"""
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper") as mock_claude,
            patch("sugar.core.loop.ErrorLogMonitor"),
        ):

            loop = SugarLoop(str(sugar_config_file))

            mock_tasks = [
                {
                    "id": "task-1",
                    "type": "bug_fix",
                    "title": "Fix auth bug",
                    "priority": 5,
                }
            ]

            loop.work_queue.get_pending_work = AsyncMock(return_value=mock_tasks)
            loop.work_queue.mark_work_active = AsyncMock()
            loop.work_queue.mark_work_failed = AsyncMock()
            mock_claude.return_value.execute_task = AsyncMock(
                return_value={"success": False, "error": "Claude CLI failed"}
            )

            await loop._execute_work()

            # Verify work was marked as failed
            loop.work_queue.mark_work_failed.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_work_execution(self, sugar_config_file):
        """Test concurrent execution of multiple tasks"""
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper") as mock_claude,
            patch("sugar.core.loop.ErrorLogMonitor"),
        ):

            loop = SugarLoop(str(sugar_config_file))

            # Mock multiple pending tasks
            mock_tasks = [
                {
                    "id": f"task-{i}",
                    "type": "bug_fix",
                    "title": f"Task {i}",
                    "priority": 3,
                }
                for i in range(5)
            ]

            loop.work_queue.get_pending_work = AsyncMock(return_value=mock_tasks)
            loop.work_queue.mark_work_active = AsyncMock()
            loop.work_queue.mark_work_completed = AsyncMock()

            # Mock successful execution
            mock_claude.return_value.execute_task = AsyncMock(
                return_value={"success": True, "result": "Task completed"}
            )

            await loop._execute_work()

            # Should execute max_concurrent_work tasks (3 from config)
            assert loop.work_queue.mark_work_active.call_count == 3
            assert loop.work_queue.mark_work_completed.call_count == 3

    def test_load_config_invalid_yaml(self, temp_dir):
        """Test config loading with invalid YAML"""
        config_path = temp_dir / "invalid.yaml"
        config_path.write_text("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            SugarLoop(str(config_path))

    @pytest.mark.asyncio
    async def test_process_feedback(self, sugar_config_file):
        """Test feedback processing functionality"""
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper"),
            patch("sugar.core.loop.ErrorLogMonitor"),
            patch("sugar.core.loop.FeedbackProcessor") as mock_feedback,
            patch("sugar.core.loop.AdaptiveScheduler") as mock_scheduler,
        ):

            loop = SugarLoop(str(sugar_config_file))

            # Mock feedback processing
            mock_feedback.return_value.process_recent_completions = AsyncMock()
            mock_scheduler.return_value.update_priorities = AsyncMock()

            await loop._process_feedback()

            # Verify feedback processing was called
            mock_feedback.return_value.process_recent_completions.assert_called_once()
            mock_scheduler.return_value.update_priorities.assert_called_once()
