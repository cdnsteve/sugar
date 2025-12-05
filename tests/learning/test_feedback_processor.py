"""
Tests for the FeedbackProcessor class.
"""

import pytest
import pytest_asyncio
import json
from unittest.mock import Mock, AsyncMock, patch

from sugar.learning.feedback_processor import FeedbackProcessor


class TestFeedbackProcessorInit:
    """Tests for FeedbackProcessor initialization."""

    def test_init_stores_work_queue(self, mock_work_queue_empty):
        """Test that __init__ stores the work queue reference."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        assert processor.work_queue is mock_work_queue_empty

    def test_init_creates_empty_learning_cache(self, mock_work_queue_empty):
        """Test that __init__ creates an empty learning cache."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        assert processor.learning_cache == {}


class TestProcessFeedback:
    """Tests for the process_feedback method."""

    @pytest.mark.asyncio
    async def test_process_feedback_returns_insights(
        self, mock_work_queue_with_data, sample_completed_tasks, sample_failed_tasks
    ):
        """Test that process_feedback returns comprehensive insights."""
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
        """Test that process_feedback caches the last insights."""
        processor = FeedbackProcessor(mock_work_queue_with_data)
        insights = await processor.process_feedback()

        assert "last_insights" in processor.learning_cache
        assert processor.learning_cache["last_insights"] == insights

    @pytest.mark.asyncio
    async def test_process_feedback_handles_empty_queue(self, mock_work_queue_empty):
        """Test that process_feedback handles empty work queue gracefully."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        insights = await processor.process_feedback()

        assert insights.get("success_patterns") == {}
        assert insights.get("failure_patterns") == {}
        assert insights.get("performance_metrics") == {}

    @pytest.mark.asyncio
    async def test_process_feedback_handles_exception(self, mock_work_queue_empty):
        """Test that process_feedback handles exceptions and returns empty dict."""
        mock_work_queue_empty.get_recent_work = AsyncMock(
            side_effect=Exception("Database error")
        )
        processor = FeedbackProcessor(mock_work_queue_empty)
        insights = await processor.process_feedback()

        assert insights == {}


class TestAnalyzeSuccessPatterns:
    """Tests for the _analyze_success_patterns method."""

    @pytest.mark.asyncio
    async def test_analyze_success_patterns_counts_task_types(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Test that success patterns correctly count task types."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_success_patterns(sample_completed_tasks)

        assert patterns["successful_task_types"]["bug_fix"] == 3
        assert patterns["successful_task_types"]["feature"] == 1
        assert patterns["successful_task_types"]["refactor"] == 1

    @pytest.mark.asyncio
    async def test_analyze_success_patterns_counts_sources(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Test that success patterns correctly count discovery sources."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_success_patterns(sample_completed_tasks)

        assert patterns["successful_sources"]["error_monitor"] == 3
        assert patterns["successful_sources"]["manual"] == 1
        assert patterns["successful_sources"]["code_quality"] == 1

    @pytest.mark.asyncio
    async def test_analyze_success_patterns_empty_tasks(self, mock_work_queue_empty):
        """Test that empty task list returns empty patterns."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_success_patterns([])

        assert patterns == {}

    @pytest.mark.asyncio
    async def test_analyze_success_patterns_calculates_rates(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Test that success rates are calculated correctly."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_success_patterns(sample_completed_tasks)

        # 3 out of 5 tasks are bug_fix = 60%
        assert patterns["task_type_success_rates"]["bug_fix"] == 60.0


class TestAnalyzeFailurePatterns:
    """Tests for the _analyze_failure_patterns method."""

    @pytest.mark.asyncio
    async def test_analyze_failure_patterns_counts_types(
        self, mock_work_queue_empty, sample_failed_tasks
    ):
        """Test that failure patterns correctly count task types."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_failure_patterns(sample_failed_tasks)

        assert patterns["failed_task_types"]["feature"] == 2
        assert patterns["failed_task_types"]["bug_fix"] == 1

    @pytest.mark.asyncio
    async def test_analyze_failure_patterns_categorizes_failures(
        self, mock_work_queue_empty, sample_failed_tasks
    ):
        """Test that failure patterns categorize error messages."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_failure_patterns(sample_failed_tasks)

        assert "timeout" in patterns["common_failure_reasons"]
        assert "file_not_found" in patterns["common_failure_reasons"]
        assert "syntax_error" in patterns["common_failure_reasons"]

    @pytest.mark.asyncio
    async def test_analyze_failure_patterns_tracks_retries(
        self, mock_work_queue_empty, sample_failed_tasks
    ):
        """Test that failure patterns track retry information."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_failure_patterns(sample_failed_tasks)

        # task-fail-1 has 3 attempts, task-fail-2 has 2 attempts
        assert "task-fail-1" in patterns["retry_effectiveness"]
        assert patterns["retry_effectiveness"]["task-fail-1"]["attempts"] == 3

    @pytest.mark.asyncio
    async def test_analyze_failure_patterns_empty_tasks(self, mock_work_queue_empty):
        """Test that empty task list returns empty patterns."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_failure_patterns([])

        assert patterns == {}


class TestCalculatePerformanceMetrics:
    """Tests for the _calculate_performance_metrics method."""

    @pytest.mark.asyncio
    async def test_calculate_metrics_success_rate(
        self, mock_work_queue_empty, sample_completed_tasks, sample_failed_tasks
    ):
        """Test that success rate is calculated correctly."""
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
        """Test that execution time statistics are calculated."""
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
        """Test that empty task lists return empty metrics."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        metrics = await processor._calculate_performance_metrics([], [])

        assert metrics == {}

    @pytest.mark.asyncio
    async def test_calculate_metrics_average_attempts(
        self, mock_work_queue_empty, sample_completed_tasks, sample_failed_tasks
    ):
        """Test that average attempts is calculated correctly."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        metrics = await processor._calculate_performance_metrics(
            sample_completed_tasks, sample_failed_tasks
        )

        assert "average_attempts_per_task" in metrics
        assert metrics["average_attempts_per_task"] > 0


class TestCategorizeFailure:
    """Tests for the _categorize_failure method."""

    @pytest.mark.asyncio
    async def test_categorize_timeout_error(self, mock_work_queue_empty):
        """Test categorization of timeout errors."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure(
            "Task timed out after 300 seconds"
        )
        assert category == "timeout"

    @pytest.mark.asyncio
    async def test_categorize_syntax_error(self, mock_work_queue_empty):
        """Test categorization of syntax errors."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure(
            "SyntaxError: invalid syntax at line 42"
        )
        assert category == "syntax_error"

    @pytest.mark.asyncio
    async def test_categorize_file_not_found(self, mock_work_queue_empty):
        """Test categorization of file not found errors."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure(
            "FileNotFoundError: No such file or directory"
        )
        assert category == "file_not_found"

    @pytest.mark.asyncio
    async def test_categorize_permission_denied(self, mock_work_queue_empty):
        """Test categorization of permission errors."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure(
            "PermissionError: Permission denied"
        )
        assert category == "permission_denied"

    @pytest.mark.asyncio
    async def test_categorize_network_error(self, mock_work_queue_empty):
        """Test categorization of network errors."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure(
            "ConnectionError: Failed to establish connection"
        )
        assert category == "network_error"

    @pytest.mark.asyncio
    async def test_categorize_claude_cli_error(self, mock_work_queue_empty):
        """Test categorization of Claude CLI errors."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure(
            "Claude CLI error: command not found"
        )
        assert category == "claude_cli_error"

    @pytest.mark.asyncio
    async def test_categorize_unknown_error(self, mock_work_queue_empty):
        """Test categorization of unknown errors."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        category = await processor._categorize_failure("Some random error occurred")
        assert category == "unknown_error"


class TestExtractExecutionTime:
    """Tests for the _extract_execution_time method."""

    @pytest.mark.asyncio
    async def test_extract_time_from_dict_result(self, mock_work_queue_empty):
        """Test extraction of execution time from dict result."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"execution_time": 45.5}}
        time = await processor._extract_execution_time(result)
        assert time == 45.5

    @pytest.mark.asyncio
    async def test_extract_time_from_json_string(self, mock_work_queue_empty):
        """Test extraction of execution time from JSON string result."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = json.dumps({"result": {"execution_time": 30.0}})
        time = await processor._extract_execution_time(result)
        assert time == 30.0

    @pytest.mark.asyncio
    async def test_extract_time_from_top_level(self, mock_work_queue_empty):
        """Test extraction of execution time from top level."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"execution_time": 60.0}
        time = await processor._extract_execution_time(result)
        assert time == 60.0

    @pytest.mark.asyncio
    async def test_extract_time_from_duration(self, mock_work_queue_empty):
        """Test extraction of execution time from duration field."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"duration": 25.0}}
        time = await processor._extract_execution_time(result)
        assert time == 25.0

    @pytest.mark.asyncio
    async def test_extract_time_returns_none_on_missing(self, mock_work_queue_empty):
        """Test that None is returned when no time is found."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"success": True}}
        time = await processor._extract_execution_time(result)
        assert time is None

    @pytest.mark.asyncio
    async def test_extract_time_returns_none_on_invalid(self, mock_work_queue_empty):
        """Test that None is returned on invalid input."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        time = await processor._extract_execution_time(None)
        assert time is None


class TestExtractSuccessIndicators:
    """Tests for the _extract_success_indicators method."""

    @pytest.mark.asyncio
    async def test_extract_explicit_success(self, mock_work_queue_empty):
        """Test extraction of explicit success indicator."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"success": True}
        indicators = await processor._extract_success_indicators(result)
        assert "explicit_success" in indicators

    @pytest.mark.asyncio
    async def test_extract_actions_completed(self, mock_work_queue_empty):
        """Test extraction of actions completed indicator."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"actions_taken": ["fixed_bug"]}}
        indicators = await processor._extract_success_indicators(result)
        assert "actions_completed" in indicators

    @pytest.mark.asyncio
    async def test_extract_files_changed(self, mock_work_queue_empty):
        """Test extraction of files changed indicator."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"files_modified": ["src/auth.py"]}}
        indicators = await processor._extract_success_indicators(result)
        assert "files_changed" in indicators

    @pytest.mark.asyncio
    async def test_extract_reasonable_execution_time(self, mock_work_queue_empty):
        """Test extraction of reasonable execution time indicator."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"execution_time": 60}}
        indicators = await processor._extract_success_indicators(result)
        assert "reasonable_execution_time" in indicators

    @pytest.mark.asyncio
    async def test_extract_from_json_string(self, mock_work_queue_empty):
        """Test extraction of indicators from JSON string."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = json.dumps({"success": True, "result": {"actions_taken": ["test"]}})
        indicators = await processor._extract_success_indicators(result)
        assert "explicit_success" in indicators
        assert "actions_completed" in indicators


class TestGenerateRecommendations:
    """Tests for the _generate_recommendations method."""

    @pytest.mark.asyncio
    async def test_recommendations_with_insufficient_data(self, mock_work_queue_empty):
        """Test that recommendations indicate need for more data."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        recs = await processor._generate_recommendations([], [])

        assert len(recs) == 1
        assert recs[0]["type"] == "info"
        assert "Collecting data" in recs[0]["message"]

    @pytest.mark.asyncio
    async def test_recommendations_low_success_rate(
        self, mock_work_queue_empty, sample_completed_tasks, sample_failed_tasks
    ):
        """Test recommendations for low success rate scenario."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        # Create scenario with low success rate (2 completed, 5 failed)
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
        """Test recommendations for high success rate scenario."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        # Create scenario with very high success rate (many completed, 0 failed)
        completed = sample_completed_tasks * 4  # 20 completed tasks

        recs = await processor._generate_recommendations(completed, [])

        optimization_rec = next((r for r in recs if r["type"] == "optimization"), None)
        assert optimization_rec is not None
        assert "High success rate" in optimization_rec["message"]

    @pytest.mark.asyncio
    async def test_recommendations_include_focus_area(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Test that recommendations include focus area based on task types."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        recs = await processor._generate_recommendations(sample_completed_tasks, [])

        focus_rec = next((r for r in recs if r["type"] == "focus_area"), None)
        assert focus_rec is not None
        assert "bug_fix" in focus_rec["message"]  # Most common type in sample

    @pytest.mark.asyncio
    async def test_recommendations_include_discovery_optimization(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Test that recommendations include discovery source optimization."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        recs = await processor._generate_recommendations(sample_completed_tasks, [])

        discovery_rec = next(
            (r for r in recs if r["type"] == "discovery_optimization"), None
        )
        assert discovery_rec is not None
        assert "error_monitor" in discovery_rec["message"]  # Most productive source


class TestGetAdaptiveRecommendations:
    """Tests for the get_adaptive_recommendations method."""

    @pytest.mark.asyncio
    async def test_get_recommendations_with_no_cache(self, mock_work_queue_empty):
        """Test that empty dict is returned when no insights are cached."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        adaptations = await processor.get_adaptive_recommendations()
        assert adaptations == {}

    @pytest.mark.asyncio
    async def test_get_recommendations_with_cached_insights(
        self, mock_work_queue_with_data
    ):
        """Test that adaptations are generated from cached insights."""
        processor = FeedbackProcessor(mock_work_queue_with_data)
        await processor.process_feedback()

        adaptations = await processor.get_adaptive_recommendations()

        assert "priority_adjustments" in adaptations
        assert "discovery_adjustments" in adaptations
        assert "execution_adjustments" in adaptations
        assert "scheduling_adjustments" in adaptations


class TestHealthCheck:
    """Tests for the health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_returns_status(self, mock_work_queue_empty):
        """Test that health check returns status information."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        health = await processor.health_check()

        assert "learning_cache_size" in health
        assert "last_processing_time" in health
        assert "available_insights" in health

    @pytest.mark.asyncio
    async def test_health_check_reflects_cache_state(self, mock_work_queue_with_data):
        """Test that health check reflects actual cache state."""
        processor = FeedbackProcessor(mock_work_queue_with_data)

        # Before processing
        health_before = await processor.health_check()
        assert health_before["learning_cache_size"] == 0

        # After processing
        await processor.process_feedback()
        health_after = await processor.health_check()
        assert health_after["learning_cache_size"] > 0
        assert "last_insights" in health_after["available_insights"]


class TestCalculatePerformanceMetricsEdgeCases:
    """Additional edge case tests for _calculate_performance_metrics."""

    @pytest.mark.asyncio
    async def test_velocity_with_single_date(self, mock_work_queue_empty):
        """Test velocity calculation when all tasks completed on same day."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        # Tasks with only one date - should fall into "All completed in one day"
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
        """Test velocity is zero when there are no completed tasks."""
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
    """Additional edge case tests for _extract_success_indicators."""

    @pytest.mark.asyncio
    async def test_extract_handles_invalid_json(self, mock_work_queue_empty):
        """Test that invalid JSON is handled gracefully."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = "not valid json at all"
        indicators = await processor._extract_success_indicators(result)
        assert indicators == []

    @pytest.mark.asyncio
    async def test_extract_handles_empty_files_list(self, mock_work_queue_empty):
        """Test that empty files_modified list doesn't add indicator."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        result = {"result": {"files_modified": []}}
        indicators = await processor._extract_success_indicators(result)
        assert "files_changed" not in indicators

    @pytest.mark.asyncio
    async def test_extract_handles_execution_time_at_boundaries(
        self, mock_work_queue_empty
    ):
        """Test execution time outside reasonable range doesn't add indicator."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        # Too fast (< 1 second)
        result_fast = {"result": {"execution_time": 0.5}}
        indicators_fast = await processor._extract_success_indicators(result_fast)
        assert "reasonable_execution_time" not in indicators_fast

        # Too slow (> 300 seconds)
        result_slow = {"result": {"execution_time": 400}}
        indicators_slow = await processor._extract_success_indicators(result_slow)
        assert "reasonable_execution_time" not in indicators_slow


class TestGetAdaptiveRecommendationsEdgeCases:
    """Additional edge case tests for get_adaptive_recommendations."""

    @pytest.mark.asyncio
    async def test_code_quality_discovery_adjustment(self, mock_work_queue_empty):
        """Test code_quality discovery optimization is processed."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        # Set up insights with code_quality discovery recommendation
        # Important: action should NOT contain "error_monitor" to hit the elif branch
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
        """Test error_monitor discovery optimization is processed."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        # Action contains error_monitor
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
        """Test timeout failure prevention is processed."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        # Set up insights with timeout failure prevention
        processor.learning_cache["last_insights"] = {
            "recommendations": [
                {"type": "failure_prevention", "action": "address_timeout_failures"}
            ]
        }
        adaptations = await processor.get_adaptive_recommendations()

        assert adaptations["execution_adjustments"].get("increase_timeout") is True

    @pytest.mark.asyncio
    async def test_optimization_increase_complexity(self, mock_work_queue_empty):
        """Test optimization recommendation with increase in action."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        # Set up insights with optimization type and "increase" in action
        processor.learning_cache["last_insights"] = {
            "recommendations": [
                {"type": "optimization", "action": "increase_task_complexity"}
            ]
        }
        adaptations = await processor.get_adaptive_recommendations()

        assert adaptations["priority_adjustments"].get("increase_complexity") is True


class TestAnalyzePriorityEffectiveness:
    """Tests for the _analyze_priority_effectiveness method."""

    @pytest.mark.asyncio
    async def test_analyze_priority_effectiveness(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Test that priority effectiveness is analyzed correctly."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        effectiveness = await processor._analyze_priority_effectiveness(
            sample_completed_tasks
        )

        # Priority 5 appears twice in sample data
        assert 5 in effectiveness
        assert effectiveness[5]["task_count"] >= 1

    @pytest.mark.asyncio
    async def test_analyze_priority_effectiveness_empty(self, mock_work_queue_empty):
        """Test that empty list returns empty dict."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        effectiveness = await processor._analyze_priority_effectiveness([])
        assert effectiveness == {}


class TestAnalyzeDiscoveryEffectiveness:
    """Tests for the _analyze_discovery_effectiveness method."""

    @pytest.mark.asyncio
    async def test_analyze_discovery_effectiveness(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Test that discovery source effectiveness is analyzed correctly."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        effectiveness = await processor._analyze_discovery_effectiveness(
            sample_completed_tasks
        )

        assert "error_monitor" in effectiveness
        assert effectiveness["error_monitor"]["task_count"] == 3
        assert "value_score" in effectiveness["error_monitor"]

    @pytest.mark.asyncio
    async def test_analyze_discovery_effectiveness_empty(self, mock_work_queue_empty):
        """Test that empty list returns empty dict."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        effectiveness = await processor._analyze_discovery_effectiveness([])
        assert effectiveness == {}


class TestAnalyzeExecutionTimes:
    """Tests for the _analyze_execution_times method."""

    @pytest.mark.asyncio
    async def test_analyze_execution_times_by_type(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Test that execution times are analyzed by task type."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_execution_times(sample_completed_tasks)

        assert "by_task_type" in patterns
        assert "bug_fix" in patterns["by_task_type"]
        assert "average_time" in patterns["by_task_type"]["bug_fix"]

    @pytest.mark.asyncio
    async def test_analyze_execution_times_by_priority(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Test that execution times are analyzed by priority."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_execution_times(sample_completed_tasks)

        assert "by_priority" in patterns

    @pytest.mark.asyncio
    async def test_analyze_execution_times_by_source(
        self, mock_work_queue_empty, sample_completed_tasks
    ):
        """Test that execution times are analyzed by source."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_execution_times(sample_completed_tasks)

        assert "by_source" in patterns
        assert "error_monitor" in patterns["by_source"]

    @pytest.mark.asyncio
    async def test_analyze_execution_times_empty(self, mock_work_queue_empty):
        """Test that empty list returns empty dict."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        patterns = await processor._analyze_execution_times([])
        assert patterns == {}
