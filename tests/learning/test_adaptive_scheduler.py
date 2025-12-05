"""
Tests for the AdaptiveScheduler class.
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch

from sugar.learning.adaptive_scheduler import AdaptiveScheduler
from sugar.learning.feedback_processor import FeedbackProcessor


class TestAdaptiveSchedulerInit:
    """Tests for AdaptiveScheduler initialization."""

    def test_init_stores_work_queue(self, mock_work_queue_empty):
        """Test that __init__ stores the work queue reference."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        assert scheduler.work_queue is mock_work_queue_empty

    def test_init_stores_feedback_processor(self, mock_work_queue_empty):
        """Test that __init__ stores the feedback processor reference."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        assert scheduler.feedback_processor is processor

    def test_init_creates_empty_adaptations(self, mock_work_queue_empty):
        """Test that __init__ creates empty adaptations dict."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        assert scheduler.adaptations == {}

    def test_class_constants(self, mock_work_queue_empty):
        """Test that class constants are defined."""
        assert AdaptiveScheduler.SOURCE_EFFECTIVENESS_WEIGHT == 0.1
        assert AdaptiveScheduler.PRIORITY_EFFECTIVENESS_WEIGHT == 0.05


class TestAdaptSystemBehavior:
    """Tests for the adapt_system_behavior method."""

    @pytest.mark.asyncio
    async def test_adapt_system_behavior_returns_adaptations(
        self, mock_work_queue_with_data
    ):
        """Test that adapt_system_behavior returns adaptations dict."""
        processor = FeedbackProcessor(mock_work_queue_with_data)
        await processor.process_feedback()

        scheduler = AdaptiveScheduler(mock_work_queue_with_data, processor)
        adaptations = await scheduler.adapt_system_behavior()

        assert isinstance(adaptations, dict)

    @pytest.mark.asyncio
    async def test_adapt_system_behavior_with_no_recommendations(
        self, mock_work_queue_empty
    ):
        """Test adapt_system_behavior when there are no recommendations."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        adaptations = await scheduler.adapt_system_behavior()

        assert adaptations == {}

    @pytest.mark.asyncio
    async def test_adapt_system_behavior_handles_exception(self, mock_work_queue_empty):
        """Test that adapt_system_behavior handles exceptions gracefully."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        processor.get_adaptive_recommendations = AsyncMock(
            side_effect=Exception("Test error")
        )
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        adaptations = await scheduler.adapt_system_behavior()

        assert adaptations == {}


class TestApplyAdaptations:
    """Tests for the _apply_adaptations method."""

    @pytest.mark.asyncio
    async def test_apply_priority_adjustments(self, mock_work_queue_empty):
        """Test applying priority adjustments."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        recommendations = {"priority_adjustments": {"reduce_complexity": True}}
        applied = await scheduler._apply_adaptations(recommendations)

        assert applied.get("priority_reduction_applied") is True

    @pytest.mark.asyncio
    async def test_apply_discovery_adjustments(self, mock_work_queue_empty):
        """Test applying discovery adjustments."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        recommendations = {"discovery_adjustments": {"boost_error_monitoring": True}}
        applied = await scheduler._apply_adaptations(recommendations)

        assert applied.get("error_monitoring_boosted") is True

    @pytest.mark.asyncio
    async def test_apply_execution_adjustments(self, mock_work_queue_empty):
        """Test applying execution adjustments."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        recommendations = {"execution_adjustments": {"increase_timeout": True}}
        applied = await scheduler._apply_adaptations(recommendations)

        assert applied.get("timeout_increased") is True

    @pytest.mark.asyncio
    async def test_apply_multiple_adjustments(self, mock_work_queue_empty):
        """Test applying multiple types of adjustments."""
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
        """Test applying empty recommendations."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        applied = await scheduler._apply_adaptations({})

        assert applied == {}


class TestAdaptPrioritySystem:
    """Tests for the _adapt_priority_system method."""

    @pytest.mark.asyncio
    async def test_reduce_complexity(self, mock_work_queue_empty):
        """Test reducing complexity when success rate is low."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        changes = await scheduler._adapt_priority_system({"reduce_complexity": True})

        assert changes.get("priority_reduction_applied") is True

    @pytest.mark.asyncio
    async def test_increase_complexity(self, mock_work_queue_empty):
        """Test increasing complexity when success rate is high."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        changes = await scheduler._adapt_priority_system({"increase_complexity": True})

        assert changes.get("priority_boost_applied") is True

    @pytest.mark.asyncio
    async def test_no_changes(self, mock_work_queue_empty):
        """Test no changes when adjustments are empty."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        changes = await scheduler._adapt_priority_system({})

        assert changes == {}


class TestAdaptDiscoveryBehavior:
    """Tests for the _adapt_discovery_behavior method."""

    @pytest.mark.asyncio
    async def test_boost_error_monitoring(self, mock_work_queue_empty):
        """Test boosting error monitoring."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        changes = await scheduler._adapt_discovery_behavior(
            {"boost_error_monitoring": True}
        )

        assert changes.get("error_monitoring_boosted") is True

    @pytest.mark.asyncio
    async def test_boost_code_quality(self, mock_work_queue_empty):
        """Test boosting code quality scanning."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        changes = await scheduler._adapt_discovery_behavior(
            {"boost_code_quality": True}
        )

        assert changes.get("code_quality_boosted") is True

    @pytest.mark.asyncio
    async def test_no_changes(self, mock_work_queue_empty):
        """Test no changes when adjustments are empty."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        changes = await scheduler._adapt_discovery_behavior({})

        assert changes == {}


class TestAdaptExecutionParameters:
    """Tests for the _adapt_execution_parameters method."""

    @pytest.mark.asyncio
    async def test_increase_timeout(self, mock_work_queue_empty):
        """Test increasing timeout."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        changes = await scheduler._adapt_execution_parameters(
            {"increase_timeout": True}
        )

        assert changes.get("timeout_increased") is True

    @pytest.mark.asyncio
    async def test_no_changes(self, mock_work_queue_empty):
        """Test no changes when adjustments are empty."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        changes = await scheduler._adapt_execution_parameters({})

        assert changes == {}


class TestGetOptimizedWorkOrder:
    """Tests for the get_optimized_work_order method."""

    @pytest.mark.asyncio
    async def test_empty_work_returns_empty_list(self, mock_work_queue_empty):
        """Test that empty work list returns empty list."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        result = await scheduler.get_optimized_work_order([])

        assert result == []

    @pytest.mark.asyncio
    async def test_orders_by_priority_without_insights(
        self, mock_work_queue_empty, sample_work_items
    ):
        """Test ordering falls back to priority without insights."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        result = await scheduler.get_optimized_work_order(sample_work_items)

        # Should be ordered by priority (highest first)
        assert result[0]["priority"] >= result[1]["priority"]

    @pytest.mark.asyncio
    async def test_orders_with_insights(
        self, mock_work_queue_empty, sample_work_items, sample_insights
    ):
        """Test ordering uses insights when available."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        processor.learning_cache["last_insights"] = sample_insights
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        result = await scheduler.get_optimized_work_order(sample_work_items)

        assert len(result) == len(sample_work_items)
        # Result should be a list of work items
        assert all("id" in item for item in result)

    @pytest.mark.asyncio
    async def test_handles_exception(self, mock_work_queue_empty, sample_work_items):
        """Test that exceptions return original work order."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        processor.learning_cache = Mock()
        processor.learning_cache.get = Mock(side_effect=Exception("Test error"))
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        result = await scheduler.get_optimized_work_order(sample_work_items)

        # Should return original work items on error
        assert result == sample_work_items


class TestApplyLearnedOrdering:
    """Tests for the _apply_learned_ordering method."""

    @pytest.mark.asyncio
    async def test_scores_work_items(
        self, mock_work_queue_empty, sample_work_items, sample_insights
    ):
        """Test that work items are scored and sorted."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        result = await scheduler._apply_learned_ordering(
            sample_work_items, sample_insights
        )

        # Result should be sorted by score (highest first)
        assert len(result) == len(sample_work_items)

    @pytest.mark.asyncio
    async def test_with_empty_insights(self, mock_work_queue_empty, sample_work_items):
        """Test ordering with empty insights."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        result = await scheduler._apply_learned_ordering(sample_work_items, {})

        # Should still return all items, ordered by base priority
        assert len(result) == len(sample_work_items)


class TestComputeWorkScore:
    """Tests for the _compute_work_score method."""

    def test_base_priority_score(self, mock_work_queue_empty):
        """Test that base score is the item priority."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        item = {"priority": 5, "source": "unknown", "type": "feature"}
        score = scheduler._compute_work_score(item, {}, {})

        assert score == 5.0

    def test_source_effectiveness_adds_to_score(self, mock_work_queue_empty):
        """Test that source effectiveness adds to score."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        item = {"priority": 5, "source": "error_monitor"}
        source_effectiveness = {"error_monitor": {"value_score": 10.0}}

        score = scheduler._compute_work_score(item, source_effectiveness, {})

        # 5 + (10 * 0.1) = 6.0
        assert score == 6.0

    def test_priority_effectiveness_adds_to_score(self, mock_work_queue_empty):
        """Test that priority effectiveness adds to score."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        item = {"priority": 5, "source": "unknown"}
        priority_effectiveness = {5: {"efficiency_score": 2.0}}

        score = scheduler._compute_work_score(item, {}, priority_effectiveness)

        # 5 + (2.0 * 0.05) = 5.1
        assert score == 5.1

    def test_combined_effectiveness(self, mock_work_queue_empty):
        """Test combined source and priority effectiveness."""
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
        """Test that missing priority defaults to zero."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        item = {"source": "unknown"}  # No priority field
        score = scheduler._compute_work_score(item, {}, {})

        assert score == 0.0

    def test_unknown_source_no_bonus(self, mock_work_queue_empty):
        """Test that unknown source doesn't add bonus."""
        processor = FeedbackProcessor(mock_work_queue_empty)
        scheduler = AdaptiveScheduler(mock_work_queue_empty, processor)

        item = {"priority": 5, "source": "unknown_source"}
        source_effectiveness = {"error_monitor": {"value_score": 10.0}}

        score = scheduler._compute_work_score(item, source_effectiveness, {})

        # Only base priority, no source bonus
        assert score == 5.0


class TestIntegration:
    """Integration tests for AdaptiveScheduler with FeedbackProcessor."""

    @pytest.mark.asyncio
    async def test_full_adaptation_cycle(self, mock_work_queue_with_data):
        """Test complete adaptation cycle from feedback to scheduling."""
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
        """Test work ordering after feedback processing."""
        processor = FeedbackProcessor(mock_work_queue_with_data)
        scheduler = AdaptiveScheduler(mock_work_queue_with_data, processor)

        # Process feedback
        await processor.process_feedback()

        # Get optimized work order
        ordered = await scheduler.get_optimized_work_order(sample_work_items)

        assert len(ordered) == len(sample_work_items)
        # Verify ordering considers insights
        # Higher scored items should come first
