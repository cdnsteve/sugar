"""
Tests for Sugar core loop functionality.

This module tests the SugarLoop class which orchestrates the main Sugar
autonomous development loop including work discovery, execution, and feedback.
"""

import pytest
import asyncio
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from sugar.core.loop import SugarLoop


# Common patches for SugarLoop initialization
LOOP_PATCHES = [
    "sugar.core.loop.WorkQueue",
    "sugar.core.loop.ClaudeWrapper",
    "sugar.core.loop.ErrorLogMonitor",
    "sugar.core.loop.CodeQualityScanner",
    "sugar.core.loop.TestCoverageAnalyzer",
]


def create_mock_patches():
    """Create a context manager that patches all SugarLoop dependencies."""
    from contextlib import ExitStack

    stack = ExitStack()
    mocks = {}
    for patch_target in LOOP_PATCHES:
        name = patch_target.split(".")[-1]
        mocks[name] = stack.enter_context(patch(patch_target))
    return stack, mocks


class TestSugarLoop:
    """Test SugarLoop core functionality."""

    def test_init_with_default_config(self, temp_dir):
        """Test SugarLoop initialization with default config path."""
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
        """Test config loading with missing file raises FileNotFoundError."""
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
        """Test that discovery modules are initialized correctly.

        Verifies that all enabled discovery modules (error monitor, code quality,
        test coverage) and core components (work queue, claude wrapper) are
        instantiated during SugarLoop initialization.
        """
        loop = SugarLoop(str(sugar_config_file))

        # Verify core components were initialized
        mock_queue.assert_called()
        mock_claude.assert_called()

        # Verify enabled discovery modules were initialized
        mock_error_monitor.assert_called()
        mock_quality.assert_called()
        mock_coverage.assert_called()

    @pytest.mark.asyncio
    async def test_start_stop_loop(self, sugar_config_file):
        """Test starting and stopping the Sugar loop.

        Verifies that the loop can be started and stopped correctly,
        with proper state transitions (running flag).
        """
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper"),
            patch("sugar.core.loop.ErrorLogMonitor"),
        ):
            loop = SugarLoop(str(sugar_config_file))

            # Mock the async methods used by start()
            loop._main_loop = AsyncMock()
            loop.work_queue.initialize = AsyncMock()
            loop.work_queue.close = AsyncMock()

            # Start the loop in a task
            start_task = asyncio.create_task(loop.start())
            await asyncio.sleep(0.05)  # Brief wait for startup

            assert loop.running, "Loop should be running after start()"

            # Stop the loop gracefully
            await loop.stop()
            assert not loop.running, "Loop should not be running after stop()"

            # Clean up the task
            start_task.cancel()
            try:
                await start_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_discover_work(self, sugar_config_file):
        """Test work discovery functionality.

        Verifies that _discover_work() calls discover() on all modules
        and adds the discovered work items to the queue.
        """
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper"),
            patch("sugar.core.loop.ErrorLogMonitor"),
            patch("sugar.core.loop.CodeQualityScanner"),
            patch("sugar.core.loop.TestCoverageAnalyzer"),
        ):
            loop = SugarLoop(str(sugar_config_file))

            # Create mock discovery modules with specific return values
            mock_error_module = AsyncMock()
            mock_error_module.discover = AsyncMock(
                return_value=[
                    {"type": "bug_fix", "title": "Fix error", "source": "error_log"}
                ]
            )
            mock_quality_module = AsyncMock()
            mock_quality_module.discover = AsyncMock(
                return_value=[
                    {
                        "type": "refactor",
                        "title": "Improve code",
                        "source": "code_quality",
                    }
                ]
            )
            mock_coverage_module = AsyncMock()
            mock_coverage_module.discover = AsyncMock(
                return_value=[
                    {"type": "test", "title": "Add tests", "source": "test_coverage"}
                ]
            )
            loop.discovery_modules = [
                mock_error_module,
                mock_quality_module,
                mock_coverage_module,
            ]

            loop.work_queue = AsyncMock()
            loop.work_queue.add_work = AsyncMock()

            await loop._discover_work()

            # Verify each discovery module was called
            mock_error_module.discover.assert_called_once()
            mock_quality_module.discover.assert_called_once()
            mock_coverage_module.discover.assert_called_once()

            # Should have added 3 tasks (one from each discovery module)
            assert loop.work_queue.add_work.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_work(self, sugar_config_file):
        """Test successful work execution.

        Verifies the complete execution flow: get work → prepare workflow →
        execute with Claude → complete workflow → mark work done.
        """
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper"),
            patch("sugar.core.loop.ErrorLogMonitor"),
            patch("sugar.core.loop.WorkflowOrchestrator"),
        ):
            loop = SugarLoop(str(sugar_config_file))

            # Mock a single work item
            mock_task = {
                "id": "task-1",
                "type": "bug_fix",
                "title": "Fix auth bug",
                "description": "Fix authentication issues",
                "priority": 5,
            }

            # Setup mocks - return None after first call to exit the processing loop
            loop.work_queue = AsyncMock()
            loop.work_queue.get_next_work = AsyncMock(side_effect=[mock_task, None])
            loop.work_queue.complete_work = AsyncMock()

            loop.workflow_orchestrator = AsyncMock()
            loop.workflow_orchestrator.prepare_work_execution = AsyncMock(
                return_value={}
            )
            loop.workflow_orchestrator.complete_work_execution = AsyncMock(
                return_value=True
            )

            loop.claude_executor = AsyncMock()
            loop.claude_executor.execute_work = AsyncMock(
                return_value={"success": True, "result": "Task completed successfully"}
            )

            await loop._execute_work()

            # Verify the complete execution flow
            loop.workflow_orchestrator.prepare_work_execution.assert_called_once_with(
                mock_task
            )
            loop.claude_executor.execute_work.assert_called_once_with(mock_task)
            loop.workflow_orchestrator.complete_work_execution.assert_called_once()
            loop.work_queue.complete_work.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_work_failure(self, sugar_config_file):
        """Test work execution failure handling.

        Verifies that when Claude execution fails, the work item is properly
        marked as failed and the failure workflow handler is invoked.
        """
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper"),
            patch("sugar.core.loop.ErrorLogMonitor"),
            patch("sugar.core.loop.WorkflowOrchestrator"),
        ):
            loop = SugarLoop(str(sugar_config_file))

            mock_task = {
                "id": "task-1",
                "type": "bug_fix",
                "title": "Fix auth bug",
                "priority": 5,
            }

            # Setup mocks to simulate failure scenario
            loop.work_queue = AsyncMock()
            loop.work_queue.get_next_work = AsyncMock(side_effect=[mock_task, None])
            loop.work_queue.fail_work = AsyncMock()

            loop.workflow_orchestrator = AsyncMock()
            loop.workflow_orchestrator.prepare_work_execution = AsyncMock(
                return_value={}
            )

            loop.claude_executor = AsyncMock()
            loop.claude_executor.execute_work = AsyncMock(
                side_effect=Exception("Claude CLI failed")
            )

            loop._handle_failed_workflow = AsyncMock()

            await loop._execute_work()

            # Verify failure handling was triggered
            loop.work_queue.fail_work.assert_called_once()
            loop._handle_failed_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_work_with_no_pending_work(self, sugar_config_file):
        """Test _execute_work when no work items are available.

        Verifies that the loop handles empty queue gracefully without errors.
        """
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper"),
            patch("sugar.core.loop.ErrorLogMonitor"),
            patch("sugar.core.loop.WorkflowOrchestrator"),
        ):
            loop = SugarLoop(str(sugar_config_file))

            # Setup mock to return no work
            loop.work_queue = AsyncMock()
            loop.work_queue.get_next_work = AsyncMock(return_value=None)

            loop.workflow_orchestrator = AsyncMock()
            loop.claude_executor = AsyncMock()

            # Should complete without error
            await loop._execute_work()

            # Verify no work was attempted
            loop.workflow_orchestrator.prepare_work_execution.assert_not_called()
            loop.claude_executor.execute_work.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_multiple_work_items(self, sugar_config_file):
        """Test processing multiple work items up to max_concurrent_work limit.

        Verifies that the loop processes work items sequentially up to the
        configured max_concurrent_work limit.
        """
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper"),
            patch("sugar.core.loop.ErrorLogMonitor"),
            patch("sugar.core.loop.WorkflowOrchestrator"),
        ):
            loop = SugarLoop(str(sugar_config_file))

            # Create two mock tasks
            mock_task_1 = {
                "id": "task-1",
                "type": "bug_fix",
                "title": "Task 1",
                "priority": 5,
            }
            mock_task_2 = {
                "id": "task-2",
                "type": "feature",
                "title": "Task 2",
                "priority": 3,
            }

            # Setup mocks - queue returns two tasks then None
            loop.work_queue = AsyncMock()
            loop.work_queue.get_next_work = AsyncMock(
                side_effect=[mock_task_1, mock_task_2, None]
            )
            loop.work_queue.complete_work = AsyncMock()

            loop.workflow_orchestrator = AsyncMock()
            loop.workflow_orchestrator.prepare_work_execution = AsyncMock(
                return_value={}
            )
            loop.workflow_orchestrator.complete_work_execution = AsyncMock(
                return_value=True
            )

            loop.claude_executor = AsyncMock()
            loop.claude_executor.execute_work = AsyncMock(
                return_value={"success": True, "result": "Completed"}
            )

            await loop._execute_work()

            # Should have processed both tasks
            assert loop.claude_executor.execute_work.call_count == 2
            assert loop.work_queue.complete_work.call_count == 2

    def test_load_config_invalid_yaml(self, temp_dir):
        """Test config loading with invalid YAML raises YAMLError."""
        config_path = temp_dir / "invalid.yaml"
        config_path.write_text("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            SugarLoop(str(config_path))

    @pytest.mark.asyncio
    async def test_process_feedback(self, sugar_config_file):
        """Test feedback processing functionality.

        Verifies that _process_feedback() invokes the feedback processor
        and adaptive scheduler to learn from past executions.
        """
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper"),
            patch("sugar.core.loop.ErrorLogMonitor"),
            patch("sugar.core.loop.FeedbackProcessor"),
            patch("sugar.core.loop.AdaptiveScheduler"),
        ):
            loop = SugarLoop(str(sugar_config_file))

            # Setup mocks for feedback processing
            loop.work_queue = AsyncMock()
            loop.work_queue.get_stats = AsyncMock(
                return_value={"pending": 0, "completed": 5, "failed": 1}
            )

            feedback_result = {"recommendations": ["test recommendation"]}
            adaptations_result = ["adaptation1", "adaptation2"]

            loop.feedback_processor = AsyncMock()
            loop.feedback_processor.process_feedback = AsyncMock(
                return_value=feedback_result
            )

            loop.adaptive_scheduler = AsyncMock()
            loop.adaptive_scheduler.adapt_system_behavior = AsyncMock(
                return_value=adaptations_result
            )

            await loop._process_feedback()

            # Verify learning pipeline was executed
            loop.feedback_processor.process_feedback.assert_called_once()
            loop.adaptive_scheduler.adapt_system_behavior.assert_called_once()
            loop.work_queue.get_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_work_with_empty_modules(self, sugar_config_file):
        """Test _discover_work with no discovery modules configured.

        Verifies graceful handling when discovery_modules list is empty.
        """
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper"),
            patch("sugar.core.loop.ErrorLogMonitor"),
        ):
            loop = SugarLoop(str(sugar_config_file))

            # Clear discovery modules
            loop.discovery_modules = []
            loop.work_queue = AsyncMock()
            loop.work_queue.add_work = AsyncMock()

            # Should complete without error
            await loop._discover_work()

            # No work should have been added
            loop.work_queue.add_work.assert_not_called()

    @pytest.mark.asyncio
    async def test_discover_work_module_returns_empty_list(self, sugar_config_file):
        """Test _discover_work when modules return empty results.

        Verifies that empty discovery results don't cause errors.
        """
        with (
            patch("sugar.core.loop.WorkQueue"),
            patch("sugar.core.loop.ClaudeWrapper"),
            patch("sugar.core.loop.ErrorLogMonitor"),
        ):
            loop = SugarLoop(str(sugar_config_file))

            # Create mock module that returns empty list
            mock_module = AsyncMock()
            mock_module.discover = AsyncMock(return_value=[])
            loop.discovery_modules = [mock_module]

            loop.work_queue = AsyncMock()
            loop.work_queue.add_work = AsyncMock()

            await loop._discover_work()

            # Module was called but no work was added
            mock_module.discover.assert_called_once()
            loop.work_queue.add_work.assert_not_called()
