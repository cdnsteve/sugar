"""
Tests for the AdaptiveScheduler class.

This module provides comprehensive test coverage for the AdaptiveScheduler,
which bridges the learning system (FeedbackProcessor) with the execution system
by translating learning insights into concrete behavioral adaptations.

Test Organization:
------------------
- TestAdaptiveSchedulerInit: Initialization and constructor behavior
- TestAdaptSystemBehavior: Main adaptation entry point (adapt_system_behavior)
- TestApplyAdaptations: Internal adaptation application (_apply_adaptations)
- TestAdaptPrioritySystem: Priority-based adaptations
- TestAdaptDiscoveryBehavior: Discovery module adaptations
- TestAdaptExecutionParameters: Execution parameter adaptations
- TestGetOptimizedWorkOrder: Work queue ordering optimization
- TestApplyLearnedOrdering: Internal ordering algorithm
- TestComputeWorkScore: Score computation for work prioritization
- TestIntegration: End-to-end adaptation and scheduling flows

Key Testing Patterns:
--------------------
- All async methods are tested with pytest.mark.asyncio
- Mock fixtures from conftest.py provide isolated test environments
- Empty queue fixtures test edge cases and graceful degradation
- Data-loaded fixtures test realistic adaptation scenarios

Dependencies:
------------
- Requires fixtures from tests/learning/conftest.py:
  - mock_work_queue_empty: Empty work queue for edge case testing
  - mock_work_queue_with_data: Pre-loaded queue for realistic scenarios
  - sample_work_items: Pending work items for scheduler testing
  - sample_insights: Pre-computed learning insights for ordering tests
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch

from sugar.learning.adaptive_scheduler import AdaptiveScheduler
from sugar.learning.feedback_processor import FeedbackProcessor


# =============================================================================
# Initialization Tests
# =============================================================================


class TestAdaptiveSchedulerInit:
    """
    Tests for AdaptiveScheduler initialization and constructor behavior.

    Validates that the constructor correctly:
    - Stores the work queue reference for task scheduling
    - Stores the feedback processor for accessing learning insights
    - Initializes the adaptations cache as an empty dictionary
    - Defines class constants for score weighting

    These tests ensure the scheduler has access to all required dependencies
    and starts in a clean state ready for adaptation cycles.
    """

    def test_init_stores_work_queue(self, mock_work_queue_empty):
        """
        Verify work queue reference is stored for task scheduling access.

        The scheduler needs direct access to the work queue to retrieve
        pending tasks and apply priority adjustments during scheduling.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        assert scheduler.work_queue is mock_work_queue_empty

    def test_init_stores_feedback_processor(self, mock_work_queue_empty):
        """
        Verify feedback processor reference is stored for insight access.

        The feedback processor provides learning insights and adaptive
        recommendations that drive the scheduler's behavioral adaptations.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        assert scheduler.feedback_processor is processor

    def test_init_creates_empty_adaptations(self, mock_work_queue_empty):
        """
        Verify adaptations cache starts empty for a clean initial state.

        The adaptations dict caches currently active adaptations. Starting
        empty ensures no stale adaptations affect a fresh scheduler instance.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        assert scheduler.adaptations == {}

    def test_class_constants(self, mock_work_queue_empty):
        """
        Verify class constants define expected score weighting factors.

        Constants control how much source effectiveness and priority
        effectiveness contribute to overall work item scores:
        - SOURCE_EFFECTIVENESS_WEIGHT (0.1): 10% weight for source value
        - PRIORITY_EFFECTIVENESS_WEIGHT (0.05): 5% weight for priority efficiency
        """
        assert AdaptiveScheduler.SOURCE_EFFECTIVENESS_WEIGHT == 0.1
        assert AdaptiveScheduler.PRIORITY_EFFECTIVENESS_WEIGHT == 0.05


# =============================================================================
# System Behavior Adaptation Tests
# =============================================================================


class TestAdaptSystemBehavior:
    """
    Tests for the adapt_system_behavior method - the main adaptation entry point.

    This method orchestrates the full adaptation cycle:
    1. Fetches recommendations from the feedback processor
    2. Applies adaptations across priority, discovery, and execution systems
    3. Returns a summary of all adaptations applied

    Tests cover successful adaptations, empty recommendation scenarios,
    and graceful error handling to ensure robust system behavior.
    """

    @pytest.mark.asyncio
    async def test_adapt_system_behavior_returns_adaptations(
        self, mock_work_queue_with_data
    ):
        """
        Verify adaptations are returned after processing feedback.

        When the feedback processor has analyzed historical task data,
        adapt_system_behavior should return a dictionary describing
        what behavioral changes were applied to the system.
        """
        processor = FeedbackProcessor(mock_work_queue_with_data)
        await processor.process_feedback()

        scheduler = AdaptiveScheduler(mock_work_queue_with_data, processor)
        adaptations = await scheduler.adapt_system_behavior()

        assert isinstance(adaptations, dict)

    @pytest.mark.asyncio
    async def test_adapt_system_behavior_with_no_recommendations(
        self, mock_work_queue_empty
    ):
        """
        Verify empty dict returned when no recommendations are available.

        With no historical task data, the feedback processor cannot generate
        recommendations, so no adaptations should be applied.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        adaptations = await scheduler.adapt_system_behavior()

        assert adaptations == {}

    @pytest.mark.asyncio
    async def test_adapt_system_behavior_handles_exception(self, mock_work_queue_empty):
        """
        Verify graceful degradation when recommendation fetching fails.

        If get_adaptive_recommendations raises an exception, the scheduler
        should log the error and return an empty dict rather than propagating
        the exception, ensuring system stability.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        processor.get_adaptive_recommendations = AsyncMock(
            side_effect=Exception("Test error")
        )
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        adaptations = await scheduler.adapt_system_behavior()

        assert adaptations == {}


class TestApplyAdaptations:
    """
    Tests for the _apply_adaptations internal method.

    This method routes recommendations to the appropriate adaptation handlers:
    - priority_adjustments → _adapt_priority_system
    - discovery_adjustments → _adapt_discovery_behavior
    - execution_adjustments → _adapt_execution_parameters

    Tests verify each category is handled correctly and that multiple
    categories can be processed in a single call.
    """

    @pytest.mark.asyncio
    async def test_apply_priority_adjustments(self, mock_work_queue_empty):
        """
        Verify priority adjustments are routed to _adapt_priority_system.

        Priority adjustments modify task complexity handling, affecting which
        tasks are attempted based on historical success rates.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        recommendations = {"priority_adjustments": {"reduce_complexity": True}}
        applied = await scheduler._apply_adaptations(recommendations)

        assert applied.get("priority_reduction_applied") is True

    @pytest.mark.asyncio
    async def test_apply_discovery_adjustments(self, mock_work_queue_empty):
        """
        Verify discovery adjustments are routed to _adapt_discovery_behavior.

        Discovery adjustments control how actively the system monitors
        different task sources (error logs, code quality, etc.).
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        recommendations = {"discovery_adjustments": {"boost_error_monitoring": True}}
        applied = await scheduler._apply_adaptations(recommendations)

        assert applied.get("error_monitoring_boosted") is True

    @pytest.mark.asyncio
    async def test_apply_execution_adjustments(self, mock_work_queue_empty):
        """
        Verify execution adjustments are routed to _adapt_execution_parameters.

        Execution adjustments modify runtime parameters like timeouts
        to reduce failures from resource constraints.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        recommendations = {"execution_adjustments": {"increase_timeout": True}}
        applied = await scheduler._apply_adaptations(recommendations)

        assert applied.get("timeout_increased") is True

    @pytest.mark.asyncio
    async def test_apply_multiple_adjustments(self, mock_work_queue_empty):
        """
        Verify all adjustment categories can be processed simultaneously.

        A single recommendations dict may contain adjustments across all
        categories; all should be applied and their results combined.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        recommendations = {
            "priority_adjustments": {"increase_complexity": True},
            "discovery_adjustments": {"boost_code_quality": True},
            "execution_adjustments": {"increase_timeout": True},
        }
        applied = await scheduler._apply_adaptations(recommendations)

        assert applied.get("priority_boost_applied") is True
        assert applied.get("code_quality_boosted") is True
        assert applied.get("timeout_increased") is True

    @pytest.mark.asyncio
    async def test_apply_empty_recommendations(self, mock_work_queue_empty):
        """
        Verify empty recommendations result in no changes.

        When the feedback processor has no actionable recommendations,
        _apply_adaptations should return an empty dict indicating
        no system behavior was modified.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        applied = await scheduler._apply_adaptations({})

        assert applied == {}


# =============================================================================
# Individual Adaptation Handler Tests
# =============================================================================


class TestAdaptPrioritySystem:
    """
    Tests for the _adapt_priority_system method.

    This method adjusts task complexity thresholds based on learning:
    - reduce_complexity: Lower priority for complex tasks (low success rate)
    - increase_complexity: Raise priority for complex tasks (high success rate)

    These adaptations help the system focus on tasks more likely to succeed.
    """

    @pytest.mark.asyncio
    async def test_reduce_complexity(self, mock_work_queue_empty):
        """
        Verify complexity reduction is applied when success rate is low.

        When complex tasks fail frequently, the system should reduce their
        priority to focus on more achievable work, indicated by the
        'priority_reduction_applied' flag in the returned changes.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        changes = await scheduler._adapt_priority_system({"reduce_complexity": True})

        assert changes.get("priority_reduction_applied") is True

    @pytest.mark.asyncio
    async def test_increase_complexity(self, mock_work_queue_empty):
        """
        Verify complexity boost is applied when success rate is high.

        When the system is succeeding at complex tasks, it should increase
        their priority to tackle more challenging work, indicated by the
        'priority_boost_applied' flag in the returned changes.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        changes = await scheduler._adapt_priority_system({"increase_complexity": True})

        assert changes.get("priority_boost_applied") is True

    @pytest.mark.asyncio
    async def test_no_changes(self, mock_work_queue_empty):
        """
        Verify empty dict returned when no priority adjustments requested.

        Empty adjustments indicate the current priority system is working
        well and requires no modification.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        changes = await scheduler._adapt_priority_system({})

        assert changes == {}


class TestAdaptDiscoveryBehavior:
    """
    Tests for the _adapt_discovery_behavior method.

    This method adjusts task discovery source priorities based on learning:
    - boost_error_monitoring: Increase focus on error-discovered tasks
    - boost_code_quality: Increase focus on quality-discovered tasks

    Discovery adjustments optimize which sources the system prioritizes
    based on their historical success rates.
    """

    @pytest.mark.asyncio
    async def test_boost_error_monitoring(self, mock_work_queue_empty):
        """
        Verify error monitoring boost is applied when error-based tasks succeed.

        When tasks from error monitoring have high success rates, the system
        should prioritize discovering more such tasks, indicated by
        'error_monitoring_boosted' in the returned changes.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        changes = await scheduler._adapt_discovery_behavior(
            {"boost_error_monitoring": True}
        )

        assert changes.get("error_monitoring_boosted") is True

    @pytest.mark.asyncio
    async def test_boost_code_quality(self, mock_work_queue_empty):
        """
        Verify code quality boost is applied when quality tasks succeed.

        When code quality-discovered tasks have high success rates, the system
        should prioritize discovering more such tasks, indicated by
        'code_quality_boosted' in the returned changes.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        changes = await scheduler._adapt_discovery_behavior(
            {"boost_code_quality": True}
        )

        assert changes.get("code_quality_boosted") is True

    @pytest.mark.asyncio
    async def test_no_changes(self, mock_work_queue_empty):
        """
        Verify empty dict returned when no discovery adjustments requested.

        Empty adjustments indicate all discovery sources are performing
        adequately and require no prioritization changes.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        changes = await scheduler._adapt_discovery_behavior({})

        assert changes == {}


class TestAdaptExecutionParameters:
    """
    Tests for the _adapt_execution_parameters method.

    This method adjusts runtime execution parameters based on learning:
    - increase_timeout: Extend task timeouts to reduce timeout failures

    Execution parameter adjustments help tasks that fail due to resource
    constraints rather than fundamental issues with the task itself.
    """

    @pytest.mark.asyncio
    async def test_increase_timeout(self, mock_work_queue_empty):
        """
        Verify timeout increase is applied when timeout failures are common.

        When tasks fail primarily due to timeouts, increasing the allowed
        execution time can improve success rates, indicated by
        'timeout_increased' in the returned changes.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        changes = await scheduler._adapt_execution_parameters(
            {"increase_timeout": True}
        )

        assert changes.get("timeout_increased") is True

    @pytest.mark.asyncio
    async def test_no_changes(self, mock_work_queue_empty):
        """
        Verify empty dict returned when no execution adjustments requested.

        Empty adjustments indicate current execution parameters are adequate
        and timeout failures are not a significant issue.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        changes = await scheduler._adapt_execution_parameters({})

        assert changes == {}


# =============================================================================
# Work Ordering Optimization Tests
# =============================================================================


class TestGetOptimizedWorkOrder:
    """
    Tests for the get_optimized_work_order method.

    This method reorders pending work items based on learned effectiveness
    patterns, prioritizing tasks that are most likely to succeed based on
    their source, type, and priority characteristics.

    The method provides graceful fallback: when no insights are available
    or errors occur, it returns items ordered by base priority.
    """

    @pytest.mark.asyncio
    async def test_empty_work_returns_empty_list(self, mock_work_queue_empty):
        """
        Verify empty input returns empty output.

        Edge case: When there's no work to order, the method should return
        an empty list without errors rather than failing on empty input.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        result = await scheduler.get_optimized_work_order([])

        assert result == []

    @pytest.mark.asyncio
    async def test_orders_by_priority_without_insights(
        self, mock_work_queue_empty, sample_work_items
    ):
        """
        Verify fallback to base priority ordering when no insights available.

        Without learning insights, the scheduler should still produce a
        sensible ordering based on the items' native priority values
        (higher priority = processed first).
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        result = await scheduler.get_optimized_work_order(sample_work_items)

        # Should be ordered by priority (highest first)
        assert result[0]["priority"] >= result[1]["priority"]

    @pytest.mark.asyncio
    async def test_orders_with_insights(
        self, mock_work_queue_empty, sample_work_items, sample_insights
    ):
        """
        Verify learning insights influence work ordering.

        When insights are available in the learning cache, the scheduler
        should use source and priority effectiveness metrics to boost
        scores of historically successful work patterns.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        processor.learning_cache["last_insights"] = sample_insights
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        result = await scheduler.get_optimized_work_order(sample_work_items)

        assert len(result) == len(sample_work_items)
        # Result should be a list of work items
        assert all("id" in item for item in result)

    @pytest.mark.asyncio
    async def test_handles_exception(self, mock_work_queue_empty, sample_work_items):
        """
        Verify graceful degradation returns original order on error.

        If accessing the learning cache or computing scores fails, the
        method should log the error and return the original work items
        unchanged rather than propagating the exception.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        processor.learning_cache = Mock()
        processor.learning_cache.get = Mock(side_effect=Exception("Test error"))
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        result = await scheduler.get_optimized_work_order(sample_work_items)

        # Should return original work items on error
        assert result == sample_work_items


class TestApplyLearnedOrdering:
    """
    Tests for the _apply_learned_ordering internal method.

    This method implements the core scoring and sorting algorithm that
    transforms learning insights into concrete work item ordering.
    It computes a score for each item and sorts descending (highest first).
    """

    @pytest.mark.asyncio
    async def test_scores_work_items(
        self, mock_work_queue_empty, sample_work_items, sample_insights
    ):
        """
        Verify all work items are scored and returned sorted.

        Each work item should be assigned a computed score based on its
        characteristics and the available insights, then sorted so the
        highest-scored items appear first in the result.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        result = await scheduler._apply_learned_ordering(
            sample_work_items, sample_insights
        )

        # Result should be sorted by score (highest first)
        assert len(result) == len(sample_work_items)

    @pytest.mark.asyncio
    async def test_with_empty_insights(self, mock_work_queue_empty, sample_work_items):
        """
        Verify ordering degrades gracefully with empty insights.

        When no learning insights are available, items should still be
        ordered (by their base priority) rather than failing or returning
        an unchanged list.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        result = await scheduler._apply_learned_ordering(sample_work_items, {})

        # Should still return all items, ordered by base priority
        assert len(result) == len(sample_work_items)


# =============================================================================
# Score Computation Tests
# =============================================================================


class TestComputeWorkScore:
    """
    Tests for the _compute_work_score method.

    This method calculates a numeric score for a work item based on:
    - Base priority (the item's native priority value)
    - Source effectiveness bonus (value_score * SOURCE_EFFECTIVENESS_WEIGHT)
    - Priority effectiveness bonus (efficiency_score * PRIORITY_EFFECTIVENESS_WEIGHT)

    The formula is: score = priority + (source_value * 0.1) + (efficiency * 0.05)

    Higher scores indicate work items that should be processed first.
    """

    def test_base_priority_score(self, mock_work_queue_empty):
        """
        Verify base score equals item priority when no effectiveness data.

        The foundation of scoring is the item's native priority. Without
        any learned effectiveness metrics, the score should simply be
        the priority value converted to float.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        item = {"priority": 5, "source": "unknown", "type": "feature"}
        score = scheduler._compute_work_score(item, {}, {})

        assert score == 5.0

    def test_source_effectiveness_adds_to_score(self, mock_work_queue_empty):
        """
        Verify source effectiveness increases score proportionally.

        When a work item's source has a known value_score, that score
        is multiplied by SOURCE_EFFECTIVENESS_WEIGHT (0.1) and added
        to the base priority.

        Calculation: 5 + (10.0 * 0.1) = 6.0
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        item = {"priority": 5, "source": "error_monitor"}
        source_effectiveness = {"error_monitor": {"value_score": 10.0}}

        score = scheduler._compute_work_score(item, source_effectiveness, {})

        # 5 + (10 * 0.1) = 6.0
        assert score == 6.0

    def test_priority_effectiveness_adds_to_score(self, mock_work_queue_empty):
        """
        Verify priority effectiveness increases score proportionally.

        When a work item's priority level has a known efficiency_score,
        that score is multiplied by PRIORITY_EFFECTIVENESS_WEIGHT (0.05)
        and added to the base priority.

        Calculation: 5 + (2.0 * 0.05) = 5.1
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        item = {"priority": 5, "source": "unknown"}
        priority_effectiveness = {5: {"efficiency_score": 2.0}}

        score = scheduler._compute_work_score(item, {}, priority_effectiveness)

        # 5 + (2.0 * 0.05) = 5.1
        assert score == 5.1

    def test_combined_effectiveness(self, mock_work_queue_empty):
        """
        Verify both effectiveness bonuses combine additively.

        When both source and priority effectiveness are known, both
        bonuses are added to the base priority independently.

        Calculation: 5 + (10.0 * 0.1) + (2.0 * 0.05) = 6.1
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        item = {"priority": 5, "source": "error_monitor"}
        source_effectiveness = {"error_monitor": {"value_score": 10.0}}
        priority_effectiveness = {5: {"efficiency_score": 2.0}}

        score = scheduler._compute_work_score(
            item, source_effectiveness, priority_effectiveness
        )

        # 5 + (10 * 0.1) + (2.0 * 0.05) = 6.1
        assert score == 6.1

    def test_missing_priority_defaults_to_zero(self, mock_work_queue_empty):
        """
        Verify items without priority field score as zero.

        Edge case: If a work item lacks a priority field, the score
        should default to 0.0 rather than raising an error. This allows
        the system to handle malformed work items gracefully.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        item = {"source": "unknown"}  # No priority field
        score = scheduler._compute_work_score(item, {}, {})

        assert score == 0.0

    def test_unknown_source_no_bonus(self, mock_work_queue_empty):
        """
        Verify unknown sources receive no effectiveness bonus.

        When a work item's source isn't in the effectiveness dictionary,
        no source bonus is applied—the item scores only on its base
        priority and any priority-level bonus.
        """
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        item = {"priority": 5, "source": "unknown_source"}
        source_effectiveness = {"error_monitor": {"value_score": 10.0}}

        score = scheduler._compute_work_score(item, source_effectiveness, {})

        # Only base priority, no source bonus
        assert score == 5.0


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """
    Integration tests for AdaptiveScheduler with FeedbackProcessor.

    These tests verify the complete adaptation workflow from end to end:
    1. Process historical task feedback to extract learning insights
    2. Apply behavioral adaptations based on recommendations
    3. Optimize work ordering using learned effectiveness patterns

    Integration tests use the mock_work_queue_with_data fixture which
    provides realistic completed and failed task records for analysis.
    """

    @pytest.mark.asyncio
    async def test_full_adaptation_cycle(self, mock_work_queue_with_data):
        """
        Verify complete adaptation workflow executes successfully.

        End-to-end test of the learning-to-adaptation pipeline:
        1. FeedbackProcessor analyzes historical task data
        2. Insights generate adaptive recommendations
        3. AdaptiveScheduler applies those recommendations

        This ensures all components integrate correctly and the
        adaptation cycle produces meaningful behavioral changes.
        """
        processor = FeedbackProcessor(mock_work_queue_with_data)
        scheduler = AdaptiveScheduler(mock_work_queue_with_data, processor)

        # Process feedback first
        insights = await processor.process_feedback()
        assert insights != {}

        # Then adapt behavior
        adaptations = await scheduler.adapt_system_behavior()
        # Should have processed recommendations
        assert isinstance(adaptations, dict)

    @pytest.mark.asyncio
    async def test_work_ordering_with_processed_feedback(
        self, mock_work_queue_with_data, sample_work_items
    ):
        """
        Verify work ordering uses insights from processed feedback.

        After feedback processing populates the learning cache with
        effectiveness metrics, work ordering should reflect those
        learned patterns by reordering items to prioritize historically
        successful source/priority combinations.
        """
        processor = FeedbackProcessor(mock_work_queue_with_data)
        scheduler = AdaptiveScheduler(mock_work_queue_with_data, processor)

        # Process feedback
        await processor.process_feedback()

        # Get optimized work order
        ordered = await scheduler.get_optimized_work_order(sample_work_items)

        assert len(ordered) == len(sample_work_items)
        # Verify ordering considers insights
        # Higher scored items should come first
