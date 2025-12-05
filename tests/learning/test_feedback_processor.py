"""
Tests for the FeedbackProcessor class.

The FeedbackProcessor analyzes historical task execution data to extract
actionable insights and patterns. This test module validates:

- Pattern extraction from completed and failed tasks
- Performance metrics calculation (success rates, execution times, velocity)
- Failure categorization and retry effectiveness tracking
- Adaptive recommendations based on learned patterns
- Edge case handling for missing data and boundary conditions

Test Organization
-----------------
Tests are grouped by the FeedbackProcessor method being tested:

- TestFeedbackProcessorInit: Constructor and initialization
- TestProcessFeedback: Main feedback processing pipeline
- TestAnalyzeSuccessPatterns: Success pattern extraction (_analyze_success_patterns)
- TestAnalyzeFailurePatterns: Failure pattern extraction (_analyze_failure_patterns)
- TestCalculatePerformanceMetrics: Metrics calculation (_calculate_performance_metrics)
- TestCategorizeFailure: Error message categorization (_categorize_failure)
- TestExtractExecutionTime: Execution time extraction (_extract_execution_time)
- TestExtractSuccessIndicators: Success indicator extraction (_extract_success_indicators)
- TestGenerateRecommendations: Recommendation generation (_generate_recommendations)
- TestGetAdaptiveRecommendations: Adaptive scheduling recommendations
- TestHealthCheck: Health status reporting
- *Additional/*EdgeCases: Extended coverage for boundary conditions

Fixtures Used
-------------
From tests/learning/conftest.py:
- sample_completed_tasks: 5 completed tasks with various types/sources
- sample_failed_tasks: 3 failed tasks with different error categories
- mock_work_queue_with_data: Mock queue returning sample task data
- mock_work_queue_empty: Mock queue returning empty results

See Also
--------
- sugar.learning.feedback_processor.FeedbackProcessor: Class under test
- tests/learning/conftest.py: Fixture definitions and data structures
"""

import pytest
import pytest_asyncio
import json
from unittest.mock import Mock, AsyncMock, patch

from sugar.learning.feedback_processor import FeedbackProcessor


class TestFeedbackProcessorInit:
    """
    Tests for FeedbackProcessor initialization.

    Validates that the constructor properly stores dependencies and
    initializes internal state for feedback processing.
    """

    def test_init_stores_work_queue(self, mock_work_queue_empty):
        """Verify the work queue dependency is stored for later data retrieval."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        assert processor.work_queue is mock_work_queue_empty

    def test_init_creates_empty_learning_cache(self, mock_work_queue_empty):
        """Verify learning cache starts empty, ready to store processed insights."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        assert processor.learning_cache == {}


class TestProcessFeedback:
    """
    Tests for the process_feedback method.

    The main entry point that orchestrates all analysis phases:
    1. Retrieves recent completed and failed tasks from the work queue
    2. Analyzes success and failure patterns
    3. Calculates performance metrics
    4. Generates actionable recommendations
    5. Caches results for adaptive scheduling use
    """

    @pytest.mark.asyncio
    async def test_process_feedback_returns_insights(
        self, mock_work_queue_with_data, sample_completed_tasks, sample_failed_tasks
    ):
        """Verify all required insight categories are present in the response."""
        processor = FeedbackProcessor(mock_work_queue_with_data)
        insights = await processor.process_feedback()

        assert "success_patterns" in insights
        assert "failure_patterns" in insights
        assert "performance_metrics" in insights
        assert "priority_effectiveness" in insights
        assert "discovery_source_effectiveness" in insights
        assert "execution_time_patterns" in insights
        assert "recommendations" in insights
        assert "timestamp" in insights

    @pytest.mark.asyncio
    async def test_process_feedback_caches_insights(self, mock_work_queue_with_data):
        """Verify insights are cached under 'last_insights' for later retrieval."""
        processor = FeedbackProcessor(mock_work_queue_with_data)
        insights = await processor.process_feedback()

        assert "last_insights" in processor.learning_cache
        assert processor.learning_cache["last_insights"] == insights

    @pytest.mark.asyncio
    async def test_process_feedback_handles_empty_queue(self, mock_work_queue_empty):
        """Verify graceful handling when no historical task data exists."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        insights = await processor.process_feedback()

        assert insights.get("success_patterns") == {}
        assert insights.get("failure_patterns") == {}
        assert insights.get("performance_metrics") == {}

    @pytest.mark.asyncio
    async def test_process_feedback_handles_exception(self, mock_work_queue_empty):
        """Verify exception safety: database errors return empty insights, not crash."""
        mock_work_queue_empty.get_recent_work = AsyncMock(
            side_effect=Exception("Database error")
        )
        processor = FeedbackProcessor(mock_work_queue_empty)
        insights = await processor.process_feedback()

        assert insights == {}


class TestAnalyzeSuccessPatterns:
    """
    Tests for the _analyze_success_patterns method.

    Validates extraction of success patterns from completed tasks, including:
    - Task type frequency counts (bug_fix, feature, refactor)
    - Discovery source effectiveness (error_monitor, manual, code_quality)
    - Success rate calculations by task type
    - Common success indicators from task results
    """

    @pytest.mark.asyncio
    async def test_analyze_success_patterns_counts_task_types(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Verify task types are counted correctly from sample data (3 bug_fix, 1 feature, 1 refactor)."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_success_patterns(sample_completed_tasks)

        assert patterns["successful_task_types"]["bug_fix"] == 3
        assert patterns["successful_task_types"]["feature"] == 1
        assert patterns["successful_task_types"]["refactor"] == 1

    @pytest.mark.asyncio
    async def test_analyze_success_patterns_counts_sources(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Verify discovery sources are counted (3 error_monitor, 1 manual, 1 code_quality)."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_success_patterns(sample_completed_tasks)

        assert patterns["successful_sources"]["error_monitor"] == 3
        assert patterns["successful_sources"]["manual"] == 1
        assert patterns["successful_sources"]["code_quality"] == 1

    @pytest.mark.asyncio
    async def test_analyze_success_patterns_empty_tasks(self, mock_work_queue_empty):
        """Verify empty task list returns empty patterns dict, not None or error."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_success_patterns([])

        assert patterns == {}

    @pytest.mark.asyncio
    async def test_analyze_success_patterns_calculates_rates(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Verify success rate calculation: 3/5 bug_fix tasks = 60% success rate."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_success_patterns(sample_completed_tasks)

        # 3 out of 5 tasks are bug_fix = 60%
        assert patterns["task_type_success_rates"]["bug_fix"] == 60.0


class TestAnalyzeFailurePatterns:
    """
    Tests for the _analyze_failure_patterns method.

    Validates extraction of failure patterns from failed tasks, including:
    - Failed task type frequency counts
    - Error message categorization into failure reason types
    - Retry tracking for tasks with multiple attempts
    - Edge cases like missing error messages
    """

    @pytest.mark.asyncio
    async def test_analyze_failure_patterns_counts_types(
        self, mock_work_queue_empty, sample_failed_tasks
    ):
        """Verify failed task types are counted (2 feature, 1 bug_fix in sample data)."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_failure_patterns(sample_failed_tasks)

        assert patterns["failed_task_types"]["feature"] == 2
        assert patterns["failed_task_types"]["bug_fix"] == 1

    @pytest.mark.asyncio
    async def test_analyze_failure_patterns_categorizes_failures(
        self, mock_work_queue_empty, sample_failed_tasks
    ):
        """Verify error messages are categorized into standard failure types."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_failure_patterns(sample_failed_tasks)

        assert "timeout" in patterns["common_failure_reasons"]
        assert "file_not_found" in patterns["common_failure_reasons"]
        assert "syntax_error" in patterns["common_failure_reasons"]

    @pytest.mark.asyncio
    async def test_analyze_failure_patterns_tracks_retries(
        self, mock_work_queue_empty, sample_failed_tasks
    ):
        """Verify retry information is tracked for multi-attempt failures."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_failure_patterns(sample_failed_tasks)

        # task-fail-1 has 3 attempts, task-fail-2 has 2 attempts
        assert "task-fail-1" in patterns["retry_effectiveness"]
        assert patterns["retry_effectiveness"]["task-fail-1"]["attempts"] == 3

    @pytest.mark.asyncio
    async def test_analyze_failure_patterns_empty_tasks(self, mock_work_queue_empty):
        """Verify empty task list returns empty patterns dict."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_failure_patterns([])

        assert patterns == {}


class TestCalculatePerformanceMetrics:
    """
    Tests for the _calculate_performance_metrics method.

    Validates calculation of aggregate performance statistics:
    - Success rate percentage from completed vs failed task counts
    - Execution time statistics (average, median, min, max)
    - Task completion velocity (tasks per day)
    - Average retry attempts per task
    """

    @pytest.mark.asyncio
    async def test_calculate_metrics_success_rate(
        self, mock_work_queue_empty, sample_completed_tasks, sample_failed_tasks
    ):
        """Verify success rate: 5 completed / (5 + 3 failed) = 62.5%."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        metrics = await processor._calculate_performance_metrics(
            sample_completed_tasks, sample_failed_tasks
        )

        # 5 completed, 3 failed = 5/8 = 62.5%
        assert metrics["success_rate_percent"] == 62.5
        assert metrics["completed_tasks"] == 5
        assert metrics["failed_tasks"] == 3

    @pytest.mark.asyncio
    async def test_calculate_metrics_execution_time_stats(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Verify execution time statistics contain all required fields."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        metrics = await processor._calculate_performance_metrics(
            sample_completed_tasks, []
        )

        time_stats = metrics["execution_time_statistics"]
        assert "average_execution_time" in time_stats
        assert "median_execution_time" in time_stats
        assert "min_execution_time" in time_stats
        assert "max_execution_time" in time_stats

    @pytest.mark.asyncio
    async def test_calculate_metrics_empty_tasks(self, mock_work_queue_empty):
        """Verify empty input returns empty metrics, no division-by-zero errors."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        metrics = await processor._calculate_performance_metrics([], [])

        assert metrics == {}

    @pytest.mark.asyncio
    async def test_calculate_metrics_average_attempts(
        self, mock_work_queue_empty, sample_completed_tasks, sample_failed_tasks
    ):
        """Verify average attempts calculation includes both completed and failed tasks."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        metrics = await processor._calculate_performance_metrics(
            sample_completed_tasks, sample_failed_tasks
        )

        assert "average_attempts_per_task" in metrics
        assert metrics["average_attempts_per_task"] > 0


class TestCategorizeFailure:
    """
    Tests for the _categorize_failure method.

    Validates classification of error messages into standard failure categories:
    - timeout: Task exceeded time limits
    - syntax_error: Code syntax problems
    - file_not_found: Missing file references
    - permission_denied: Access permission issues
    - network_error: Connection and HTTP failures
    - claude_cli_error: Claude CLI tool failures
    - validation_error: Input validation failures
    - resource_error: Memory/disk resource issues
    - unknown_error: Unrecognized error patterns
    """

    @pytest.mark.asyncio
    async def test_categorize_timeout_error(self, mock_work_queue_empty):
        """Verify 'timeout' keyword in error triggers timeout category."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure(
            "Task timed out after 300 seconds"
        )
        assert category == "timeout"

    @pytest.mark.asyncio
    async def test_categorize_syntax_error(self, mock_work_queue_empty):
        """Verify 'SyntaxError' in message triggers syntax_error category."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure(
            "SyntaxError: invalid syntax at line 42"
        )
        assert category == "syntax_error"

    @pytest.mark.asyncio
    async def test_categorize_file_not_found(self, mock_work_queue_empty):
        """Verify file-related errors trigger file_not_found category."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure(
            "FileNotFoundError: No such file or directory"
        )
        assert category == "file_not_found"

    @pytest.mark.asyncio
    async def test_categorize_permission_denied(self, mock_work_queue_empty):
        """Verify permission errors trigger permission_denied category."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure(
            "PermissionError: Permission denied"
        )
        assert category == "permission_denied"

    @pytest.mark.asyncio
    async def test_categorize_network_error(self, mock_work_queue_empty):
        """Verify connection errors trigger network_error category."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure(
            "ConnectionError: Failed to establish connection"
        )
        assert category == "network_error"

    @pytest.mark.asyncio
    async def test_categorize_claude_cli_error(self, mock_work_queue_empty):
        """Verify Claude CLI errors are categorized separately for debugging."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure(
            "Claude CLI error: command not found"
        )
        assert category == "claude_cli_error"

    @pytest.mark.asyncio
    async def test_categorize_unknown_error(self, mock_work_queue_empty):
        """Verify unrecognized errors fall back to unknown_error category."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure("Some random error occurred")
        assert category == "unknown_error"


class TestExtractExecutionTime:
    """
    Tests for the _extract_execution_time method.

    Validates extraction of execution time from various result formats:
    - Nested dict: result.result.execution_time
    - Top-level dict: result.execution_time
    - Duration alias: result.result.duration
    - JSON string: Parsed then extracted
    - Edge cases: None, missing fields, invalid values
    """

    @pytest.mark.asyncio
    async def test_extract_time_from_dict_result(self, mock_work_queue_empty):
        """Verify extraction from nested result.result.execution_time path."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"execution_time": 45.5}}
        time = await processor._extract_execution_time(result)
        assert time == 45.5

    @pytest.mark.asyncio
    async def test_extract_time_from_json_string(self, mock_work_queue_empty):
        """Verify JSON string results are parsed before extraction."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = json.dumps({"result": {"execution_time": 30.0}})
        time = await processor._extract_execution_time(result)
        assert time == 30.0

    @pytest.mark.asyncio
    async def test_extract_time_from_top_level(self, mock_work_queue_empty):
        """Verify fallback to top-level execution_time field."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"execution_time": 60.0}
        time = await processor._extract_execution_time(result)
        assert time == 60.0

    @pytest.mark.asyncio
    async def test_extract_time_from_duration(self, mock_work_queue_empty):
        """Verify 'duration' field is accepted as alias for execution_time."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"duration": 25.0}}
        time = await processor._extract_execution_time(result)
        assert time == 25.0

    @pytest.mark.asyncio
    async def test_extract_time_returns_none_on_missing(self, mock_work_queue_empty):
        """Verify None returned when no time field exists in result."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"success": True}}
        time = await processor._extract_execution_time(result)
        assert time is None

    @pytest.mark.asyncio
    async def test_extract_time_returns_none_on_invalid(self, mock_work_queue_empty):
        """Verify None returned for invalid input (None, non-parseable)."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        time = await processor._extract_execution_time(None)
        assert time is None


class TestExtractSuccessIndicators:
    """
    Tests for the _extract_success_indicators method.

    Validates identification of success signals from task results:
    - explicit_success: Result contains success=True flag
    - actions_completed: Result contains non-empty actions_taken list
    - files_changed: Result contains non-empty files_modified list
    - reasonable_execution_time: Execution time within acceptable bounds (1-300s)

    These indicators help assess task completion quality beyond binary success/fail.
    """

    @pytest.mark.asyncio
    async def test_extract_explicit_success(self, mock_work_queue_empty):
        """Verify explicit success=True flag triggers 'explicit_success' indicator."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"success": True}
        indicators = await processor._extract_success_indicators(result)
        assert "explicit_success" in indicators

    @pytest.mark.asyncio
    async def test_extract_actions_completed(self, mock_work_queue_empty):
        """Verify non-empty actions_taken list triggers 'actions_completed' indicator."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"actions_taken": ["fixed_bug"]}}
        indicators = await processor._extract_success_indicators(result)
        assert "actions_completed" in indicators

    @pytest.mark.asyncio
    async def test_extract_files_changed(self, mock_work_queue_empty):
        """Verify non-empty files_modified list triggers 'files_changed' indicator."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"files_modified": ["src/auth.py"]}}
        indicators = await processor._extract_success_indicators(result)
        assert "files_changed" in indicators

    @pytest.mark.asyncio
    async def test_extract_reasonable_execution_time(self, mock_work_queue_empty):
        """Verify execution time within 1-300s triggers 'reasonable_execution_time'."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"execution_time": 60}}
        indicators = await processor._extract_success_indicators(result)
        assert "reasonable_execution_time" in indicators

    @pytest.mark.asyncio
    async def test_extract_from_json_string(self, mock_work_queue_empty):
        """Verify JSON string results are parsed before indicator extraction."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = json.dumps({"success": True, "result": {"actions_taken": ["test"]}})
        indicators = await processor._extract_success_indicators(result)
        assert "explicit_success" in indicators
        assert "actions_completed" in indicators


class TestGenerateRecommendations:
    """
    Tests for the _generate_recommendations method.

    Validates generation of actionable recommendations based on task patterns:
    - info: Indicates insufficient data for analysis
    - priority_adjustment: Suggests priority changes based on success rates
    - optimization: Suggests increasing task complexity when success is high
    - focus_area: Identifies most successful task types to prioritize
    - discovery_optimization: Highlights most productive discovery sources
    - failure_prevention: Suggests mitigation for common failure patterns
    """

    @pytest.mark.asyncio
    async def test_recommendations_with_insufficient_data(self, mock_work_queue_empty):
        """Verify info recommendation when no task data exists."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        recs = await processor._generate_recommendations([], [])

        assert len(recs) == 1
        assert recs[0]["type"] == "info"
        assert "Collecting data" in recs[0]["message"]

    @pytest.mark.asyncio
    async def test_recommendations_low_success_rate(
        self, mock_work_queue_empty, sample_completed_tasks, sample_failed_tasks
    ):
        """Verify priority_adjustment recommended when success rate is low (<50%)."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        # Create scenario with low success rate (2 completed, 6 failed = 25%)
        completed = sample_completed_tasks[:2]
        failed = sample_failed_tasks * 2  # 6 failed tasks

        recs = await processor._generate_recommendations(completed, failed)

        priority_rec = next(
            (r for r in recs if r["type"] == "priority_adjustment"), None
        )
        assert priority_rec is not None
        assert "Low success rate" in priority_rec["message"]

    @pytest.mark.asyncio
    async def test_recommendations_high_success_rate(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Verify optimization recommended when success rate is very high (>90%)."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        # Create scenario with very high success rate (20 completed, 0 failed = 100%)
        completed = sample_completed_tasks * 4  # 20 completed tasks

        recs = await processor._generate_recommendations(completed, [])

        optimization_rec = next((r for r in recs if r["type"] == "optimization"), None)
        assert optimization_rec is not None
        assert "High success rate" in optimization_rec["message"]

    @pytest.mark.asyncio
    async def test_recommendations_include_focus_area(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Verify focus_area recommendation highlights most successful task type."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        recs = await processor._generate_recommendations(sample_completed_tasks, [])

        focus_rec = next((r for r in recs if r["type"] == "focus_area"), None)
        assert focus_rec is not None
        assert "bug_fix" in focus_rec["message"]  # Most common type in sample

    @pytest.mark.asyncio
    async def test_recommendations_include_discovery_optimization(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Verify discovery_optimization identifies most productive source."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        recs = await processor._generate_recommendations(sample_completed_tasks, [])

        discovery_rec = next(
            (r for r in recs if r["type"] == "discovery_optimization"), None
        )
        assert discovery_rec is not None
        assert "error_monitor" in discovery_rec["message"]  # Most productive source


class TestGetAdaptiveRecommendations:
    """
    Tests for the get_adaptive_recommendations method.

    Validates conversion of cached insights into scheduler-consumable adaptations:
    - priority_adjustments: How to modify task priority calculations
    - discovery_adjustments: How to weight discovery sources
    - execution_adjustments: Timeout and retry policy changes
    - scheduling_adjustments: Task ordering and batching suggestions

    Requires process_feedback() to be called first to populate the cache.
    """

    @pytest.mark.asyncio
    async def test_get_recommendations_with_no_cache(self, mock_work_queue_empty):
        """Verify empty dict returned when process_feedback() hasn't been called."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        adaptations = await processor.get_adaptive_recommendations()
        assert adaptations == {}

    @pytest.mark.asyncio
    async def test_get_recommendations_with_cached_insights(
        self, mock_work_queue_with_data
    ):
        """Verify all adjustment categories are present after processing feedback."""
        processor = FeedbackProcessor(mock_work_queue_with_data)
        await processor.process_feedback()

        adaptations = await processor.get_adaptive_recommendations()

        assert "priority_adjustments" in adaptations
        assert "discovery_adjustments" in adaptations
        assert "execution_adjustments" in adaptations
        assert "scheduling_adjustments" in adaptations


class TestHealthCheck:
    """
    Tests for the health_check method.

    Validates the FeedbackProcessor's health monitoring capability:
    - learning_cache_size: Number of cached insight entries
    - last_processing_time: When feedback was last processed
    - available_insights: List of insight types currently cached

    Used for monitoring and debugging the learning subsystem.
    """

    @pytest.mark.asyncio
    async def test_health_check_returns_status(self, mock_work_queue_empty):
        """Verify health check returns all required status fields."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        health = await processor.health_check()

        assert "learning_cache_size" in health
        assert "last_processing_time" in health
        assert "available_insights" in health

    @pytest.mark.asyncio
    async def test_health_check_reflects_cache_state(self, mock_work_queue_with_data):
        """Verify health check accurately reflects cache state changes."""
        processor = FeedbackProcessor(mock_work_queue_with_data)

        # Before processing - cache should be empty
        health_before = await processor.health_check()
        assert health_before["learning_cache_size"] == 0

        # After processing - cache should contain insights
        await processor.process_feedback()
        health_after = await processor.health_check()
        assert health_after["learning_cache_size"] > 0
        assert "last_insights" in health_after["available_insights"]


class TestCalculatePerformanceMetricsEdgeCases:
    """
    Edge case tests for _calculate_performance_metrics.

    Tests velocity calculation boundary conditions:
    - Single day: All tasks completed on same day
    - Zero completed: Only failed tasks exist
    - Missing dates: Tasks without completed_at field
    """

    @pytest.mark.asyncio
    async def test_velocity_with_single_date(self, mock_work_queue_empty):
        """Verify velocity equals task count when all tasks complete on same day."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        # Tasks with only one date - time_span = 0, max(1, 0) = 1
        single_day_tasks = [
            {
                "id": "task-1",
                "type": "bug_fix",
                "priority": 5,
                "status": "completed",
                "source": "error_monitor",
                "attempts": 1,
                "completed_at": "2024-01-15T10:00:00Z",
                "result": json.dumps({"result": {"execution_time": 45.0}}),
            },
        ]
        metrics = await processor._calculate_performance_metrics(single_day_tasks, [])

        # With only one task/date, velocity should equal the number of tasks
        assert metrics["task_completion_velocity_per_day"] == 1

    @pytest.mark.asyncio
    async def test_velocity_zero_when_no_completed(self, mock_work_queue_empty):
        """Verify velocity is 0 when only failed tasks exist."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        # Only failed tasks, no completed - velocity should be 0
        failed_tasks = [
            {
                "id": "task-fail-1",
                "type": "bug_fix",
                "priority": 5,
                "status": "failed",
                "source": "error_monitor",
                "attempts": 1,
                "error_message": "test error",
            },
        ]
        metrics = await processor._calculate_performance_metrics([], failed_tasks)

        assert metrics["task_completion_velocity_per_day"] == 0


class TestExtractSuccessIndicatorsEdgeCases:
    """
    Edge case tests for _extract_success_indicators.

    Tests boundary conditions for indicator extraction:
    - Invalid JSON strings return empty indicator list
    - Empty files_modified list doesn't trigger files_changed
    - Execution times outside 1-300s range don't trigger reasonable_execution_time
    """

    @pytest.mark.asyncio
    async def test_extract_handles_invalid_json(self, mock_work_queue_empty):
        """Verify invalid JSON returns empty list, not error."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = "not valid json at all"
        indicators = await processor._extract_success_indicators(result)
        assert indicators == []

    @pytest.mark.asyncio
    async def test_extract_handles_empty_files_list(self, mock_work_queue_empty):
        """Verify empty files_modified list doesn't trigger files_changed indicator."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"files_modified": []}}
        indicators = await processor._extract_success_indicators(result)
        assert "files_changed" not in indicators

    @pytest.mark.asyncio
    async def test_extract_handles_execution_time_at_boundaries(
        self, mock_work_queue_empty
    ):
        """Verify times outside 1-300s range don't trigger reasonable_execution_time."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        # Too fast (< 1 second) - likely a no-op or error
        result_fast = {"result": {"execution_time": 0.5}}
        indicators_fast = await processor._extract_success_indicators(result_fast)
        assert "reasonable_execution_time" not in indicators_fast

        # Too slow (> 300 seconds) - likely a timeout or hanging task
        result_slow = {"result": {"execution_time": 400}}
        indicators_slow = await processor._extract_success_indicators(result_slow)
        assert "reasonable_execution_time" not in indicators_slow


class TestGetAdaptiveRecommendationsEdgeCases:
    """
    Edge case tests for get_adaptive_recommendations.

    Tests specific recommendation-to-adaptation mappings:
    - discovery_optimization → discovery_adjustments (code_quality vs error_monitor)
    - failure_prevention → execution_adjustments (timeout handling)
    - optimization → priority_adjustments (complexity increases)

    These tests directly inject cached insights to test specific code paths.
    """

    @pytest.mark.asyncio
    async def test_code_quality_discovery_adjustment(self, mock_work_queue_empty):
        """Verify code_quality discovery recommendation maps to boost_code_quality."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        # Action does NOT contain "error_monitor" to hit the code_quality branch
        processor.learning_cache["last_insights"] = {
            "recommendations": [
                {
                    "type": "discovery_optimization",
                    "action": "boost_code_quality_scanning",
                }
            ]
        }
        adaptations = await processor.get_adaptive_recommendations()

        assert adaptations["discovery_adjustments"].get("boost_code_quality") is True

    @pytest.mark.asyncio
    async def test_error_monitor_discovery_adjustment(self, mock_work_queue_empty):
        """Verify error_monitor discovery recommendation maps to boost_error_monitoring."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        # Action contains "error_monitor" to hit that branch
        processor.learning_cache["last_insights"] = {
            "recommendations": [
                {
                    "type": "discovery_optimization",
                    "action": "optimize_error_monitor_discovery",
                }
            ]
        }
        adaptations = await processor.get_adaptive_recommendations()

        assert (
            adaptations["discovery_adjustments"].get("boost_error_monitoring") is True
        )

    @pytest.mark.asyncio
    async def test_timeout_failure_prevention(self, mock_work_queue_empty):
        """Verify timeout failure_prevention maps to increase_timeout execution adjustment."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        processor.learning_cache["last_insights"] = {
            "recommendations": [
                {"type": "failure_prevention", "action": "address_timeout_failures"}
            ]
        }
        adaptations = await processor.get_adaptive_recommendations()

        assert adaptations["execution_adjustments"].get("increase_timeout") is True

    @pytest.mark.asyncio
    async def test_optimization_increase_complexity(self, mock_work_queue_empty):
        """Verify optimization with 'increase' in action maps to increase_complexity."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        processor.learning_cache["last_insights"] = {
            "recommendations": [
                {"type": "optimization", "action": "increase_task_complexity"}
            ]
        }
        adaptations = await processor.get_adaptive_recommendations()

        assert adaptations["priority_adjustments"].get("increase_complexity") is True


class TestAnalyzePriorityEffectiveness:
    """
    Tests for the _analyze_priority_effectiveness method.

    Validates per-priority-level analysis including:
    - task_count: Number of tasks at each priority level
    - average_execution_time: Mean completion time for that priority
    - efficiency_score: Computed effectiveness score

    Used to identify which priority levels correlate with successful outcomes.
    """

    @pytest.mark.asyncio
    async def test_analyze_priority_effectiveness(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Verify priority levels are tracked with task counts from sample data."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        effectiveness = await processor._analyze_priority_effectiveness(
            sample_completed_tasks
        )

        # Priority 5 appears twice in sample data (task-1, task-fail-2)
        assert 5 in effectiveness
        assert effectiveness[5]["task_count"] >= 1

    @pytest.mark.asyncio
    async def test_analyze_priority_effectiveness_empty(self, mock_work_queue_empty):
        """Verify empty task list returns empty effectiveness dict."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        effectiveness = await processor._analyze_priority_effectiveness([])
        assert effectiveness == {}


class TestAnalyzeDiscoveryEffectiveness:
    """
    Tests for the _analyze_discovery_effectiveness method.

    Validates per-discovery-source analysis including:
    - task_count: Number of tasks from each discovery source
    - value_score: Weighted contribution score based on priority and success

    Used to optimize which discovery sources to prioritize for task generation.
    """

    @pytest.mark.asyncio
    async def test_analyze_discovery_effectiveness(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Verify discovery sources are tracked with counts and value scores."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        effectiveness = await processor._analyze_discovery_effectiveness(
            sample_completed_tasks
        )

        assert "error_monitor" in effectiveness
        assert effectiveness["error_monitor"]["task_count"] == 3
        assert "value_score" in effectiveness["error_monitor"]

    @pytest.mark.asyncio
    async def test_analyze_discovery_effectiveness_empty(self, mock_work_queue_empty):
        """Verify empty task list returns empty effectiveness dict."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        effectiveness = await processor._analyze_discovery_effectiveness([])
        assert effectiveness == {}


class TestAnalyzeExecutionTimes:
    """
    Tests for the _analyze_execution_times method.

    Validates execution time analysis across multiple dimensions:
    - by_task_type: Average times for bug_fix, feature, refactor, etc.
    - by_priority: Average times for each priority level (1-10)
    - by_source: Average times by discovery source

    Used to identify which task characteristics correlate with faster completion.
    """

    @pytest.mark.asyncio
    async def test_analyze_execution_times_by_type(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Verify execution times are grouped and averaged by task type."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_execution_times(sample_completed_tasks)

        assert "by_task_type" in patterns
        assert "bug_fix" in patterns["by_task_type"]
        assert "average_time" in patterns["by_task_type"]["bug_fix"]

    @pytest.mark.asyncio
    async def test_analyze_execution_times_by_priority(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Verify execution times are grouped by priority level."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_execution_times(sample_completed_tasks)

        assert "by_priority" in patterns

    @pytest.mark.asyncio
    async def test_analyze_execution_times_by_source(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Verify execution times are grouped by discovery source."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_execution_times(sample_completed_tasks)

        assert "by_source" in patterns
        assert "error_monitor" in patterns["by_source"]

    @pytest.mark.asyncio
    async def test_analyze_execution_times_empty(self, mock_work_queue_empty):
        """Verify empty task list returns empty patterns dict."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_execution_times([])
        assert patterns == {}


class TestCategorizeFailureAdditional:
    """
    Additional _categorize_failure tests for complete category coverage.

    Extends TestCategorizeFailure with additional error message variations:
    - validation_error: Format and validation failures
    - resource_error: Memory and disk space issues
    - network_error: HTTP and API failures

    Ensures keyword-based categorization handles various message formats.
    """

    @pytest.mark.asyncio
    async def test_categorize_validation_error(self, mock_work_queue_empty):
        """Verify 'Validation' keyword triggers validation_error category."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure(
            "Validation error: input does not match expected format"
        )
        assert category == "validation_error"

    @pytest.mark.asyncio
    async def test_categorize_resource_error(self, mock_work_queue_empty):
        """Verify 'Out of memory' triggers resource_error category."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure(
            "Out of memory: cannot allocate additional resources"
        )
        assert category == "resource_error"

    @pytest.mark.asyncio
    async def test_categorize_disk_space_error(self, mock_work_queue_empty):
        """Verify 'disk space' also triggers resource_error category."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure("No disk space left on device")
        assert category == "resource_error"

    @pytest.mark.asyncio
    async def test_categorize_http_api_error(self, mock_work_queue_empty):
        """Verify 'HTTP Error' triggers network_error category."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure(
            "HTTP Error 500: Internal Server Error from API"
        )
        assert category == "network_error"

    @pytest.mark.asyncio
    async def test_categorize_invalid_format_error(self, mock_work_queue_empty):
        """Verify 'Invalid format' triggers validation_error category."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure(
            "Invalid format error in configuration file"
        )
        assert category == "validation_error"


class TestExtractExecutionTimeAdditional:
    """
    Additional edge case tests for _extract_execution_time.

    Tests invalid and boundary values:
    - Zero value: Should return None (invalid duration)
    - Negative value: Should return None (impossible duration)
    - Integer input: Should convert to float for consistency
    """

    @pytest.mark.asyncio
    async def test_extract_time_zero_value(self, mock_work_queue_empty):
        """Verify zero execution time returns None (indicates incomplete data)."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"execution_time": 0}}
        time = await processor._extract_execution_time(result)
        assert time is None

    @pytest.mark.asyncio
    async def test_extract_time_negative_value(self, mock_work_queue_empty):
        """Verify negative execution time returns None (invalid measurement)."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"execution_time": -5.0}}
        time = await processor._extract_execution_time(result)
        assert time is None

    @pytest.mark.asyncio
    async def test_extract_time_from_integer(self, mock_work_queue_empty):
        """Verify integer time is converted to float for consistent typing."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"execution_time": 45}}
        time = await processor._extract_execution_time(result)
        assert time == 45.0
        assert isinstance(time, float)


class TestCalculatePerformanceMetricsAdditional:
    """
    Additional _calculate_performance_metrics edge case tests.

    Tests velocity calculation with date edge cases:
    - Missing completed_at field: Falls back to task count
    - Same-day completion: Treats as single day (velocity = task count)

    These ensure robust velocity calculation under unusual data conditions.
    """

    @pytest.mark.asyncio
    async def test_velocity_with_no_completed_at_dates(self, mock_work_queue_empty):
        """Verify velocity fallback when tasks lack completed_at timestamps."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        tasks_no_dates = [
            {
                "id": "task-1",
                "type": "bug_fix",
                "priority": 5,
                "status": "completed",
                "source": "error_monitor",
                "attempts": 1,
                "result": '{"result": {"execution_time": 45.0}}',
            },
        ]
        metrics = await processor._calculate_performance_metrics(tasks_no_dates, [])

        # Without dates, velocity should fall back to task count
        assert metrics["task_completion_velocity_per_day"] == 1

    @pytest.mark.asyncio
    async def test_metrics_with_multiple_dates_same_day(self, mock_work_queue_empty):
        """Verify same-day tasks yield velocity = task count (time_span clamped to 1)."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        tasks_same_day = [
            {
                "id": "task-1",
                "type": "bug_fix",
                "priority": 5,
                "status": "completed",
                "source": "error_monitor",
                "attempts": 1,
                "completed_at": "2024-01-15T10:00:00Z",
                "result": '{"result": {"execution_time": 45.0}}',
            },
            {
                "id": "task-2",
                "type": "bug_fix",
                "priority": 5,
                "status": "completed",
                "source": "error_monitor",
                "attempts": 1,
                "completed_at": "2024-01-15T14:00:00Z",
                "result": '{"result": {"execution_time": 30.0}}',
            },
        ]
        metrics = await processor._calculate_performance_metrics(tasks_same_day, [])

        # Same day, so time_span is 0, max(1, 0) = 1, velocity = 2 tasks/day
        assert metrics["task_completion_velocity_per_day"] == 2


class TestAnalyzeFailurePatternsAdditional:
    """
    Additional _analyze_failure_patterns edge case tests.

    Tests handling of incomplete failure data:
    - Missing error_message: Task type counted but no failure reason recorded
    - Single attempt failures: Not tracked in retry_effectiveness (no retry data)

    Ensures graceful degradation when failure metadata is incomplete.
    """

    @pytest.mark.asyncio
    async def test_analyze_failure_no_error_message(self, mock_work_queue_empty):
        """Verify tasks without error_message are counted but not categorized."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        tasks_no_error = [
            {
                "id": "task-fail-1",
                "type": "feature",
                "priority": 4,
                "status": "failed",
                "source": "manual",
                "attempts": 1,
                # No error_message field
            },
        ]
        patterns = await processor._analyze_failure_patterns(tasks_no_error)

        assert patterns["failed_task_types"]["feature"] == 1
        # common_failure_reasons should be empty since no error messages
        assert len(patterns["common_failure_reasons"]) == 0

    @pytest.mark.asyncio
    async def test_analyze_failure_single_attempt(self, mock_work_queue_empty):
        """Verify single-attempt failures excluded from retry_effectiveness tracking."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        tasks_single_attempt = [
            {
                "id": "task-fail-1",
                "type": "feature",
                "priority": 4,
                "status": "failed",
                "source": "manual",
                "attempts": 1,  # Only 1 attempt - no retry data
                "error_message": "Some error",
            },
        ]
        patterns = await processor._analyze_failure_patterns(tasks_single_attempt)

        # Single attempt tasks should not appear in retry_effectiveness
        assert "task-fail-1" not in patterns["retry_effectiveness"]


class TestAnalyzeSuccessPatternsAdditional:
    """
    Additional _analyze_success_patterns edge case tests.

    Tests handling of incomplete success data:
    - Missing result field: Task type/priority counted but no success indicators
    - Priority counting validation: Ensures all priority levels are tracked

    Ensures graceful degradation when task result metadata is incomplete.
    """

    @pytest.mark.asyncio
    async def test_analyze_success_with_no_result(self, mock_work_queue_empty):
        """Verify tasks without result field are counted but have no indicators."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        tasks_no_result = [
            {
                "id": "task-1",
                "type": "bug_fix",
                "priority": 5,
                "status": "completed",
                "source": "error_monitor",
                "attempts": 1,
                # No result field
            },
        ]
        patterns = await processor._analyze_success_patterns(tasks_no_result)

        assert patterns["successful_task_types"]["bug_fix"] == 1
        # common_success_indicators should be empty
        assert len(patterns["common_success_indicators"]) == 0

    @pytest.mark.asyncio
    async def test_analyze_success_counts_priorities(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Verify all priority levels from sample data are tracked."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_success_patterns(sample_completed_tasks)

        # Verify priority counting from sample data (priorities 3, 4, 5, 6, 7)
        assert 5 in patterns["successful_priorities"]
        assert 3 in patterns["successful_priorities"]


class TestGenerateRecommendationsAdditional:
    """
    Additional _generate_recommendations edge case tests.

    Tests recommendation generation with incomplete data:
    - No error_message in failures: Should not generate failure_prevention
      recommendations since there's no pattern to address.

    Ensures recommendations are only generated when actionable data exists.
    """

    @pytest.mark.asyncio
    async def test_recommendations_failure_without_error_message(
        self, mock_work_queue_empty
    ):
        """Verify no failure_prevention recommendation when error messages are missing."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        completed = [
            {
                "id": f"task-{i}",
                "type": "bug_fix",
                "priority": 5,
                "status": "completed",
                "source": "error_monitor",
                "attempts": 1,
            }
            for i in range(5)
        ]
        failed = [
            {
                "id": "task-fail-1",
                "type": "feature",
                "priority": 4,
                "status": "failed",
                "source": "manual",
                "attempts": 1,
                # No error_message - can't identify failure pattern
            },
        ]
        recs = await processor._generate_recommendations(completed, failed)

        # Should not have failure_prevention recommendation without error messages
        failure_rec = next((r for r in recs if r["type"] == "failure_prevention"), None)
        assert failure_rec is None
