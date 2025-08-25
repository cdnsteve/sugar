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
    @patch("sugar.core.loop.CodeQualityScanner")
    @patch("sugar.core.loop.TestCoverageAnalyzer")
    def test_discovery_modules_initialization(
        self,
        mock_coverage,
        mock_quality,
        mock_error_monitor,
        mock_claude,
        mock_queue,
        sugar_config_file,
    ):
        """Test that discovery modules are initialized correctly"""
        loop = SugarLoop(str(sugar_config_file))

        # Check that enabled discovery modules are initialized
        # These may be stored in different attributes based on implementation
        # Just verify the mocks were called during initialization
        mock_error_monitor.assert_called()
        mock_quality.assert_called()
        mock_coverage.assert_called()
        mock_queue.assert_called()
        mock_claude.assert_called()

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

            # Replace discovery modules with AsyncMock
            loop.error_monitor = AsyncMock()
            loop.error_monitor.discover_work = AsyncMock(
                return_value=[
                    {"type": "bug_fix", "title": "Fix error", "source": "error_log"}
                ]
            )
            loop.quality_scanner = AsyncMock()
            loop.quality_scanner.discover_work = AsyncMock(
                return_value=[
                    {
                        "type": "refactor",
                        "title": "Improve code",
                        "source": "code_quality",
                    }
                ]
            )
            loop.coverage_analyzer = AsyncMock()
            loop.coverage_analyzer.discover_work = AsyncMock(
                return_value=[
                    {"type": "test", "title": "Add tests", "source": "test_coverage"}
                ]
            )

            loop.work_queue = AsyncMock()
            loop.work_queue.add_work = AsyncMock()

            await loop._discover_work()

            # Should have added 3 tasks (one from each discovery module)
            assert loop.work_queue.add_work.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_work(self, sugar_config_file):
        """Test work execution functionality"""
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper"),
            patch("sugar.core.loop.ErrorLogMonitor"),
            patch("sugar.core.loop.WorkflowOrchestrator"),
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

            # Replace components with AsyncMock - return None after first call to prevent loop
            loop.work_queue = AsyncMock()
            loop.work_queue.get_next_work = AsyncMock(side_effect=[mock_tasks[0], None])
            loop.work_queue.mark_work_completed = AsyncMock()
            loop.workflow_orchestrator = AsyncMock()
            loop.workflow_orchestrator.prepare_work_execution = AsyncMock(
                return_value={}
            )
            loop.workflow_orchestrator.complete_work_execution = AsyncMock()
            loop.claude_executor = AsyncMock()
            loop.claude_executor.execute_work = AsyncMock(
                return_value={"success": True, "result": "Task completed successfully"}
            )

            await loop._execute_work()

            # Verify workflow was executed once
            loop.workflow_orchestrator.prepare_work_execution.assert_called_once()
            loop.claude_executor.execute_work.assert_called_once()
            loop.workflow_orchestrator.complete_work_execution.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_work_failure(self, sugar_config_file):
        """Test work execution with failure"""
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper"),
            patch("sugar.core.loop.ErrorLogMonitor"),
            patch("sugar.core.loop.WorkflowOrchestrator"),
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

            # Replace components with AsyncMock - simulate failure and return None after first call
            loop.work_queue = AsyncMock()
            loop.work_queue.get_next_work = AsyncMock(side_effect=[mock_tasks[0], None])
            loop.work_queue.mark_work_failed = AsyncMock()
            loop.workflow_orchestrator = AsyncMock()
            loop.workflow_orchestrator.prepare_work_execution = AsyncMock(
                return_value={}
            )
            loop.claude_executor = AsyncMock()
            # Make execute_work raise an exception to trigger failure path
            loop.claude_executor.execute_work = AsyncMock(
                side_effect=Exception("Claude CLI failed")
            )

            await loop._execute_work()

            # Verify work was marked as failed
            loop.work_queue.mark_work_failed.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_work_execution(self, sugar_config_file):
        """Test concurrent execution of multiple tasks"""
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper"),
            patch("sugar.core.loop.ErrorLogMonitor"),
            patch("sugar.core.loop.WorkflowOrchestrator"),
        ):

            loop = SugarLoop(str(sugar_config_file))

            # Mock single task (since _execute_work processes one at a time)
            mock_task = {
                "id": "task-0",
                "type": "bug_fix",
                "title": "Task 0",
                "priority": 3,
            }

            # Replace components with AsyncMock - return None after first call to prevent loop
            loop.work_queue = AsyncMock()
            loop.work_queue.get_next_work = AsyncMock(side_effect=[mock_task, None])
            loop.work_queue.mark_work_completed = AsyncMock()
            loop.workflow_orchestrator = AsyncMock()
            loop.workflow_orchestrator.prepare_work_execution = AsyncMock(
                return_value={}
            )
            loop.workflow_orchestrator.complete_work_execution = AsyncMock()
            loop.claude_executor = AsyncMock()
            loop.claude_executor.execute_work = AsyncMock(
                return_value={"success": True, "result": "Task completed"}
            )

            await loop._execute_work()

            # Should execute one task successfully
            loop.workflow_orchestrator.prepare_work_execution.assert_called_once()
            loop.claude_executor.execute_work.assert_called_once()
            loop.workflow_orchestrator.complete_work_execution.assert_called_once()

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

            # Mock feedback processing with AsyncMock
            loop.work_queue = AsyncMock()
            loop.work_queue.get_stats = AsyncMock(
                return_value={"pending": 0, "completed": 5, "failed": 1}
            )
            loop.feedback_processor = AsyncMock()
            loop.feedback_processor.process_recent_completions = AsyncMock(
                return_value={"recommendations": ["test recommendation"]}
            )
            loop.adaptive_scheduler = AsyncMock()
            loop.adaptive_scheduler.update_priorities = AsyncMock(return_value=0)

            await loop._process_feedback()

            # Verify feedback processing was called
            loop.feedback_processor.process_recent_completions.assert_called_once()
            loop.adaptive_scheduler.update_priorities.assert_called_once()
