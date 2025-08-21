"""
Adaptive Scheduler - Adjust system behavior based on learning insights
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from .feedback_processor import FeedbackProcessor

logger = logging.getLogger(__name__)

class AdaptiveScheduler:
    """Adapt system scheduling and behavior based on learning"""
    
    def __init__(self, work_queue, feedback_processor: FeedbackProcessor):
        self.work_queue = work_queue
        self.feedback_processor = feedback_processor
        self.adaptations = {}
        
    async def adapt_system_behavior(self) -> Dict[str, Any]:
        """Adapt system behavior based on learning insights"""
        
        try:
            # Get adaptive recommendations
            recommendations = await self.feedback_processor.get_adaptive_recommendations()
            
            # Apply adaptations
            adaptations_applied = await self._apply_adaptations(recommendations)
            
            logger.info(f"🎯 Applied {len(adaptations_applied)} behavioral adaptations")
            return adaptations_applied
            
        except Exception as e:
            logger.error(f"Error adapting system behavior: {e}")
            return {}
    
    async def _apply_adaptations(self, recommendations: Dict[str, Any]) -> Dict[str, Any]:
        """Apply specific adaptations based on recommendations"""
        applied = {}
        
        # Priority adjustments
        if recommendations.get('priority_adjustments'):
            priority_changes = await self._adapt_priority_system(
                recommendations['priority_adjustments']
            )
            applied.update(priority_changes)
        
        # Discovery adjustments
        if recommendations.get('discovery_adjustments'):
            discovery_changes = await self._adapt_discovery_behavior(
                recommendations['discovery_adjustments']
            )
            applied.update(discovery_changes)
        
        # Execution adjustments
        if recommendations.get('execution_adjustments'):
            execution_changes = await self._adapt_execution_parameters(
                recommendations['execution_adjustments']
            )
            applied.update(execution_changes)
        
        return applied
    
    async def _adapt_priority_system(self, adjustments: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt priority system based on learning"""
        changes = {}
        
        if adjustments.get('reduce_complexity'):
            # Lower priority for complex tasks
            changes['priority_reduction_applied'] = True
            logger.info("🔽 Reducing priority for complex tasks due to low success rate")
        
        if adjustments.get('increase_complexity'):
            # Boost priority for more challenging tasks
            changes['priority_boost_applied'] = True
            logger.info("🔼 Increasing priority for complex tasks due to high success rate")
        
        return changes
    
    async def _adapt_discovery_behavior(self, adjustments: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt discovery module behavior"""
        changes = {}
        
        if adjustments.get('boost_error_monitoring'):
            changes['error_monitoring_boosted'] = True
            logger.info("📈 Boosting error monitoring frequency - high success rate")
        
        if adjustments.get('boost_code_quality'):
            changes['code_quality_boosted'] = True
            logger.info("📈 Boosting code quality scanning - high success rate")
        
        return changes
    
    async def _adapt_execution_parameters(self, adjustments: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt execution parameters"""
        changes = {}
        
        if adjustments.get('increase_timeout'):
            changes['timeout_increased'] = True
            logger.info("⏱️ Increasing execution timeout to reduce timeout failures")
        
        return changes
    
    async def get_optimized_work_order(self, available_work: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize work order based on learning insights"""
        
        if not available_work:
            return []
        
        try:
            # Get insights from feedback processor
            insights = self.feedback_processor.learning_cache.get('last_insights', {})
            
            # Apply learned optimizations
            optimized_work = await self._apply_learned_ordering(available_work, insights)
            
            return optimized_work
            
        except Exception as e:
            logger.error(f"Error optimizing work order: {e}")
            return available_work  # Return original order on error
    
    async def _apply_learned_ordering(self, work: List[Dict[str, Any]], 
                                    insights: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply learned patterns to optimize work ordering"""
        
        # Get effectiveness metrics
        source_effectiveness = insights.get('discovery_source_effectiveness', {})
        priority_effectiveness = insights.get('priority_effectiveness', {})
        
        # Score each work item based on learned patterns
        scored_work = []
        for item in work:
            score = item['priority']  # Base score from priority
            
            # Boost score based on source effectiveness
            source = item.get('source', '')
            if source in source_effectiveness:
                source_score = source_effectiveness[source].get('value_score', 1)
                score += source_score * 0.1  # Small boost from source effectiveness
            
            # Adjust based on priority effectiveness
            priority = item['priority']
            if priority in priority_effectiveness:
                efficiency = priority_effectiveness[priority].get('efficiency_score', 1)
                score += efficiency * 0.05  # Small boost from priority effectiveness
            
            scored_work.append((score, item))
        
        # Sort by score (highest first)
        scored_work.sort(key=lambda x: x[0], reverse=True)
        
        # Return just the work items
        return [item for score, item in scored_work]