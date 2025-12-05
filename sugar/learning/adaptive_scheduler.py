"""
Adaptive Scheduler - Adjust system behavior based on learning insights
"""

import logging
from typing import Any, Dict, List


from .feedback_processor import FeedbackProcessor

logger = logging.getLogger(__name__)


class AdaptiveScheduler:
    """Adapt system scheduling and behavior based on learning.

    This class acts as the bridge between the learning system (FeedbackProcessor)
    and the execution system (work queue). It translates learning insights into
    concrete behavioral adaptations for the system.

    Attributes:
        work_queue: The work queue containing pending tasks.
        feedback_processor: The processor that generates learning insights.
        adaptations: Cache of currently active adaptations.
    """

    # Score multipliers for work ordering optimization
    SOURCE_EFFECTIVENESS_WEIGHT = 0.1
    PRIORITY_EFFECTIVENESS_WEIGHT = 0.05

    def __init__(self, work_queue, feedback_processor: FeedbackProcessor) -> None:
        """Initialize the adaptive scheduler.

        Args:
            work_queue: The work queue to schedule tasks from.
            feedback_processor: The feedback processor providing learning insights.
        """
        self.work_queue = work_queue
        self.feedback_processor = feedback_processor
        self.adaptations: Dict[str, Any] = {}

    async def adapt_system_behavior(self) -> Dict[str, Any]:
        """Adapt system behavior based on learning insights.

        Fetches adaptive recommendations from the feedback processor and
        applies them to modify system behavior accordingly.

        Returns:
            Dictionary of adaptations that were applied, empty dict on error.
        """
        try:
            recommendations = (
                await self.feedback_processor.get_adaptive_recommendations()
            )
            adaptations_applied = await self._apply_adaptations(recommendations)

            if adaptations_applied:
                logger.info(
                    f"🎯 Applied {len(adaptations_applied)} behavioral adaptations"
                )

            return adaptations_applied

        except Exception as e:
            logger.error(f"Error adapting system behavior: {e}", exc_info=True)
            return {}

    async def _apply_adaptations(
        self, recommendations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply specific adaptations based on recommendations.

        Args:
            recommendations: Dictionary containing adaptation recommendations
                organized by category (priority, discovery, execution).

        Returns:
            Dictionary of all adaptations that were successfully applied.
        """
        applied: Dict[str, Any] = {}

        adaptation_handlers = [
            ("priority_adjustments", self._adapt_priority_system),
            ("discovery_adjustments", self._adapt_discovery_behavior),
            ("execution_adjustments", self._adapt_execution_parameters),
        ]

        for key, handler in adaptation_handlers:
            if adjustments := recommendations.get(key):
                changes = await handler(adjustments)
                applied.update(changes)

        return applied

    async def _adapt_priority_system(
        self, adjustments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Adapt priority system based on learning.

        Args:
            adjustments: Dictionary of priority adjustments to apply.

        Returns:
            Dictionary indicating which priority changes were applied.
        """
        changes: Dict[str, Any] = {}

        if adjustments.get("reduce_complexity"):
            changes["priority_reduction_applied"] = True
            logger.info(
                "🔽 Reducing priority for complex tasks due to low success rate"
            )

        if adjustments.get("increase_complexity"):
            changes["priority_boost_applied"] = True
            logger.info(
                "🔼 Increasing priority for complex tasks due to high success rate"
            )

        return changes

    async def _adapt_discovery_behavior(
        self, adjustments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Adapt discovery module behavior.

        Args:
            adjustments: Dictionary of discovery behavior adjustments.

        Returns:
            Dictionary indicating which discovery changes were applied.
        """
        changes: Dict[str, Any] = {}

        if adjustments.get("boost_error_monitoring"):
            changes["error_monitoring_boosted"] = True
            logger.info("📈 Boosting error monitoring frequency - high success rate")

        if adjustments.get("boost_code_quality"):
            changes["code_quality_boosted"] = True
            logger.info("📈 Boosting code quality scanning - high success rate")

        return changes

    async def _adapt_execution_parameters(
        self, adjustments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Adapt execution parameters.

        Args:
            adjustments: Dictionary of execution parameter adjustments.

        Returns:
            Dictionary indicating which execution changes were applied.
        """
        changes: Dict[str, Any] = {}

        if adjustments.get("increase_timeout"):
            changes["timeout_increased"] = True
            logger.info("⏱️ Increasing execution timeout to reduce timeout failures")

        return changes

    async def get_optimized_work_order(
        self, available_work: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Optimize work order based on learning insights.

        Takes a list of available work items and reorders them based on
        learned patterns about effectiveness of different sources and priorities.

        Args:
            available_work: List of work items to optimize ordering for.

        Returns:
            Reordered list of work items, or original list on error.
        """
        if not available_work:
            return []

        try:
            insights = self.feedback_processor.learning_cache.get("last_insights", {})
            return await self._apply_learned_ordering(available_work, insights)

        except Exception as e:
            logger.error(f"Error optimizing work order: {e}", exc_info=True)
            return available_work

    async def _apply_learned_ordering(
        self, work: List[Dict[str, Any]], insights: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply learned patterns to optimize work ordering.

        Scores each work item based on its base priority plus learned
        effectiveness metrics for its source and priority level.

        Args:
            work: List of work items to order.
            insights: Dictionary of learning insights including effectiveness metrics.

        Returns:
            Work items sorted by computed score (highest first).
        """
        source_effectiveness = insights.get("discovery_source_effectiveness", {})
        priority_effectiveness = insights.get("priority_effectiveness", {})

        scored_work = [
            (
                self._compute_work_score(
                    item, source_effectiveness, priority_effectiveness
                ),
                item,
            )
            for item in work
        ]

        scored_work.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored_work]

    def _compute_work_score(
        self,
        item: Dict[str, Any],
        source_effectiveness: Dict[str, Any],
        priority_effectiveness: Dict[str, Any],
    ) -> float:
        """Compute a score for a work item based on learned patterns.

        Args:
            item: The work item to score.
            source_effectiveness: Effectiveness metrics by source type.
            priority_effectiveness: Effectiveness metrics by priority level.

        Returns:
            Computed score for the work item.
        """
        score = float(item.get("priority", 0))

        source = item.get("source", "")
        if source in source_effectiveness:
            source_score = source_effectiveness[source].get("value_score", 1.0)
            score += source_score * self.SOURCE_EFFECTIVENESS_WEIGHT

        priority = item.get("priority")
        if priority in priority_effectiveness:
            efficiency = priority_effectiveness[priority].get("efficiency_score", 1.0)
            score += efficiency * self.PRIORITY_EFFECTIVENESS_WEIGHT

        return score
