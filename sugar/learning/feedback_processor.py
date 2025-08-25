"""
Feedback Processor - Learn from execution results and adapt behavior
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import statistics
import re

logger = logging.getLogger(__name__)


class FeedbackProcessor:
    """Process execution feedback and extract learning insights"""

    def __init__(self, work_queue):
        self.work_queue = work_queue
        self.learning_cache = {}  # Cache insights to avoid recomputation

    async def process_feedback(self) -> Dict[str, Any]:
        """Process all execution feedback and generate insights"""

        try:
            # Get recent completed and failed tasks
            completed_tasks = await self.work_queue.get_recent_work(
                limit=50, status="completed"
            )
            failed_tasks = await self.work_queue.get_recent_work(
                limit=20, status="failed"
            )

            # Generate comprehensive insights
            insights = {
                "success_patterns": await self._analyze_success_patterns(
                    completed_tasks
                ),
                "failure_patterns": await self._analyze_failure_patterns(failed_tasks),
                "performance_metrics": await self._calculate_performance_metrics(
                    completed_tasks, failed_tasks
                ),
                "priority_effectiveness": await self._analyze_priority_effectiveness(
                    completed_tasks
                ),
                "discovery_source_effectiveness": await self._analyze_discovery_effectiveness(
                    completed_tasks
                ),
                "execution_time_patterns": await self._analyze_execution_times(
                    completed_tasks
                ),
                "recommendations": await self._generate_recommendations(
                    completed_tasks, failed_tasks
                ),
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Cache for future use
            self.learning_cache["last_insights"] = insights

            logger.info(
                f"🧠 Processed feedback from {len(completed_tasks)} completed and {len(failed_tasks)} failed tasks"
            )
            return insights

        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
            return {}

    async def _analyze_success_patterns(
        self, completed_tasks: List[Dict]
    ) -> Dict[str, Any]:
        """Analyze patterns in successful task executions"""
        if not completed_tasks:
            return {}

        patterns = {
            "successful_task_types": defaultdict(int),
            "successful_priorities": defaultdict(int),
            "successful_sources": defaultdict(int),
            "common_success_indicators": [],
            "optimal_task_characteristics": {},
        }

        for task in completed_tasks:
            # Count successful task types
            patterns["successful_task_types"][task["type"]] += 1
            patterns["successful_priorities"][task["priority"]] += 1
            patterns["successful_sources"][task["source"]] += 1

            # Analyze success indicators from results
            if task.get("result"):
                success_indicators = await self._extract_success_indicators(
                    task["result"]
                )
                patterns["common_success_indicators"].extend(success_indicators)

        # Calculate success rates by category
        total_tasks = len(completed_tasks)
        patterns["task_type_success_rates"] = {
            task_type: (count / total_tasks) * 100
            for task_type, count in patterns["successful_task_types"].items()
        }

        return patterns

    async def _analyze_failure_patterns(
        self, failed_tasks: List[Dict]
    ) -> Dict[str, Any]:
        """Analyze patterns in failed task executions"""
        if not failed_tasks:
            return {}

        patterns = {
            "failed_task_types": defaultdict(int),
            "failed_priorities": defaultdict(int),
            "common_failure_reasons": defaultdict(int),
            "failure_time_patterns": {},
            "retry_effectiveness": {},
        }

        for task in failed_tasks:
            patterns["failed_task_types"][task["type"]] += 1
            patterns["failed_priorities"][task["priority"]] += 1

            # Extract failure reasons
            if task.get("error_message"):
                failure_category = await self._categorize_failure(task["error_message"])
                patterns["common_failure_reasons"][failure_category] += 1

            # Analyze retry patterns
            if task["attempts"] > 1:
                patterns["retry_effectiveness"][task["id"]] = {
                    "attempts": task["attempts"],
                    "final_status": task["status"],
                }

        return patterns

    async def _calculate_performance_metrics(
        self, completed_tasks: List[Dict], failed_tasks: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate overall system performance metrics"""
        total_tasks = len(completed_tasks) + len(failed_tasks)

        if total_tasks == 0:
            return {}

        # Basic success metrics
        success_rate = (len(completed_tasks) / total_tasks) * 100

        # Execution time statistics
        execution_times = []
        for task in completed_tasks:
            if task.get("result") and isinstance(task["result"], (str, dict)):
                exec_time = await self._extract_execution_time(task["result"])
                if exec_time:
                    execution_times.append(exec_time)

        time_stats = {}
        if execution_times:
            time_stats = {
                "average_execution_time": statistics.mean(execution_times),
                "median_execution_time": statistics.median(execution_times),
                "min_execution_time": min(execution_times),
                "max_execution_time": max(execution_times),
            }

        # Task completion velocity (tasks per day)
        if completed_tasks:
            # Calculate time span of completed tasks
            dates = [
                task["completed_at"]
                for task in completed_tasks
                if task.get("completed_at")
            ]
            if len(dates) > 1:
                dates.sort()
                time_span = (
                    datetime.fromisoformat(dates[-1].replace("Z", ""))
                    - datetime.fromisoformat(dates[0].replace("Z", ""))
                ).days
                velocity = len(completed_tasks) / max(1, time_span)
            else:
                velocity = len(completed_tasks)  # All completed in one day
        else:
            velocity = 0

        return {
            "total_tasks_processed": total_tasks,
            "success_rate_percent": success_rate,
            "completed_tasks": len(completed_tasks),
            "failed_tasks": len(failed_tasks),
            "task_completion_velocity_per_day": velocity,
            "execution_time_statistics": time_stats,
            "average_attempts_per_task": (
                statistics.mean(
                    [task["attempts"] for task in completed_tasks + failed_tasks]
                )
                if total_tasks > 0
                else 0
            ),
        }

    async def _analyze_priority_effectiveness(
        self, completed_tasks: List[Dict]
    ) -> Dict[str, Any]:
        """Analyze how well the priority system is working"""
        if not completed_tasks:
            return {}

        priority_analysis = defaultdict(list)

        for task in completed_tasks:
            priority = task["priority"]

            # Get execution time for this task
            exec_time = await self._extract_execution_time(task.get("result"))
            if exec_time:
                priority_analysis[priority].append(
                    {
                        "execution_time": exec_time,
                        "attempts": task["attempts"],
                        "task_type": task["type"],
                    }
                )

        # Calculate effectiveness metrics per priority
        effectiveness = {}
        for priority, tasks in priority_analysis.items():
            if tasks:
                avg_time = statistics.mean([t["execution_time"] for t in tasks])
                avg_attempts = statistics.mean([t["attempts"] for t in tasks])

                effectiveness[priority] = {
                    "task_count": len(tasks),
                    "average_execution_time": avg_time,
                    "average_attempts": avg_attempts,
                    "efficiency_score": len(tasks)
                    / (
                        avg_time * avg_attempts
                    ),  # More tasks, less time/attempts = better
                }

        return effectiveness

    async def _analyze_discovery_effectiveness(
        self, completed_tasks: List[Dict]
    ) -> Dict[str, Any]:
        """Analyze which discovery sources produce the most valuable work"""
        if not completed_tasks:
            return {}

        source_analysis = defaultdict(list)

        for task in completed_tasks:
            source = task.get("source", "unknown")
            exec_time = await self._extract_execution_time(task.get("result"))

            source_analysis[source].append(
                {
                    "task_type": task["type"],
                    "priority": task["priority"],
                    "execution_time": exec_time or 0,
                    "attempts": task["attempts"],
                }
            )

        # Calculate value metrics per source
        source_effectiveness = {}
        for source, tasks in source_analysis.items():
            if tasks:
                # Higher priority tasks are more valuable
                avg_priority = statistics.mean([t["priority"] for t in tasks])
                success_rate = len(tasks) / len(tasks)  # All are completed, so 100%
                avg_attempts = statistics.mean([t["attempts"] for t in tasks])

                # Value score: higher priority, fewer attempts, more tasks = better
                value_score = (avg_priority * len(tasks)) / max(1, avg_attempts)

                source_effectiveness[source] = {
                    "task_count": len(tasks),
                    "average_priority": avg_priority,
                    "success_rate": success_rate,
                    "average_attempts": avg_attempts,
                    "value_score": value_score,
                }

        return source_effectiveness

    async def _analyze_execution_times(
        self, completed_tasks: List[Dict]
    ) -> Dict[str, Any]:
        """Analyze execution time patterns by task characteristics"""
        if not completed_tasks:
            return {}

        time_patterns = {
            "by_task_type": defaultdict(list),
            "by_priority": defaultdict(list),
            "by_source": defaultdict(list),
        }

        for task in completed_tasks:
            exec_time = await self._extract_execution_time(task.get("result"))
            if exec_time:
                time_patterns["by_task_type"][task["type"]].append(exec_time)
                time_patterns["by_priority"][task["priority"]].append(exec_time)
                time_patterns["by_source"][task.get("source", "unknown")].append(
                    exec_time
                )

        # Calculate averages for each category
        analyzed_patterns = {}
        for category, data in time_patterns.items():
            analyzed_patterns[category] = {}
            for key, times in data.items():
                if times:
                    analyzed_patterns[category][key] = {
                        "average_time": statistics.mean(times),
                        "median_time": statistics.median(times),
                        "task_count": len(times),
                    }

        return analyzed_patterns

    async def _generate_recommendations(
        self, completed_tasks: List[Dict], failed_tasks: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on learning"""
        recommendations = []

        total_tasks = len(completed_tasks) + len(failed_tasks)
        if total_tasks < 5:  # Need sufficient data
            return [
                {
                    "type": "info",
                    "message": "Collecting data - recommendations will improve with more task history",
                }
            ]

        success_rate = (len(completed_tasks) / total_tasks) * 100

        # Success rate recommendations
        if success_rate < 70:
            recommendations.append(
                {
                    "type": "priority_adjustment",
                    "message": f"Low success rate ({success_rate:.1f}%). Consider reducing task complexity or improving prompts.",
                    "action": "review_failed_tasks",
                }
            )
        elif success_rate > 95:
            recommendations.append(
                {
                    "type": "optimization",
                    "message": f"High success rate ({success_rate:.1f}%). System could handle more complex tasks.",
                    "action": "increase_task_complexity",
                }
            )

        # Task type recommendations
        if completed_tasks:
            task_type_counts = defaultdict(int)
            for task in completed_tasks:
                task_type_counts[task["type"]] += 1

            most_successful_type = max(task_type_counts.items(), key=lambda x: x[1])

            recommendations.append(
                {
                    "type": "focus_area",
                    "message": f"Most successful task type: {most_successful_type[0]} ({most_successful_type[1]} completed)",
                    "action": f"prioritize_{most_successful_type[0]}_tasks",
                }
            )

        # Discovery source recommendations
        if completed_tasks:
            source_counts = defaultdict(int)
            for task in completed_tasks:
                source_counts[task.get("source", "unknown")] += 1

            if source_counts:
                best_source = max(source_counts.items(), key=lambda x: x[1])
                recommendations.append(
                    {
                        "type": "discovery_optimization",
                        "message": f"Most productive discovery source: {best_source[0]} ({best_source[1]} tasks)",
                        "action": f"optimize_{best_source[0]}_discovery",
                    }
                )

        # Failure pattern recommendations
        if failed_tasks:
            failure_reasons = defaultdict(int)
            for task in failed_tasks:
                if task.get("error_message"):
                    category = await self._categorize_failure(task["error_message"])
                    failure_reasons[category] += 1

            if failure_reasons:
                common_failure = max(failure_reasons.items(), key=lambda x: x[1])
                recommendations.append(
                    {
                        "type": "failure_prevention",
                        "message": f"Common failure pattern: {common_failure[0]} ({common_failure[1]} occurrences)",
                        "action": f"address_{common_failure[0]}_failures",
                    }
                )

        return recommendations

    async def _extract_success_indicators(self, result: Any) -> List[str]:
        """Extract indicators of successful execution from task results"""
        indicators = []

        try:
            if isinstance(result, str):
                result_data = json.loads(result)
            else:
                result_data = result

            # Look for success indicators in the result
            if result_data.get("success"):
                indicators.append("explicit_success")

            if "actions_taken" in result_data.get("result", {}):
                indicators.append("actions_completed")

            if "files_modified" in result_data.get("result", {}):
                files = result_data["result"]["files_modified"]
                if isinstance(files, list) and len(files) > 0:
                    indicators.append("files_changed")

            # Check execution time (reasonable times indicate success)
            exec_time = result_data.get("result", {}).get("execution_time", 0)
            if 1 < exec_time < 300:  # 1 second to 5 minutes is reasonable
                indicators.append("reasonable_execution_time")

        except Exception as e:
            logger.debug(f"Could not extract success indicators: {e}")

        return indicators

    async def _extract_execution_time(self, result: Any) -> Optional[float]:
        """Extract execution time from task result"""
        try:
            if isinstance(result, str):
                result_data = json.loads(result)
            else:
                result_data = result

            # Try different locations where execution time might be stored
            time_locations = [
                result_data.get("result", {}).get("execution_time"),
                result_data.get("execution_time"),
                result_data.get("result", {}).get("duration"),
            ]

            for time_val in time_locations:
                if isinstance(time_val, (int, float)) and time_val > 0:
                    return float(time_val)

        except Exception as e:
            logger.debug(f"Could not extract execution time: {e}")

        return None

    async def _categorize_failure(self, error_message: str) -> str:
        """Categorize failure based on error message"""
        error_lower = error_message.lower()

        # Define failure categories and their patterns
        categories = {
            "timeout": ["timeout", "timed out", "time limit"],
            "syntax_error": ["syntax error", "invalid syntax", "parsing error"],
            "file_not_found": ["file not found", "no such file", "does not exist"],
            "permission_denied": ["permission denied", "access denied", "not allowed"],
            "network_error": ["network", "connection", "http error", "api error"],
            "claude_cli_error": ["claude", "cli error", "command not found"],
            "validation_error": ["validation", "invalid", "format error"],
            "resource_error": ["out of memory", "disk space", "resource"],
        }

        # Check each category
        for category, patterns in categories.items():
            if any(pattern in error_lower for pattern in patterns):
                return category

        return "unknown_error"

    async def get_adaptive_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for adapting system behavior"""

        if "last_insights" not in self.learning_cache:
            return {}

        insights = self.learning_cache["last_insights"]
        recommendations = insights.get("recommendations", [])

        # Convert recommendations into actionable system adjustments
        adaptations = {
            "priority_adjustments": {},
            "discovery_adjustments": {},
            "execution_adjustments": {},
            "scheduling_adjustments": {},
        }

        for rec in recommendations:
            rec_type = rec.get("type")
            action = rec.get("action", "")

            if rec_type == "priority_adjustment":
                adaptations["priority_adjustments"]["reduce_complexity"] = True
            elif rec_type == "optimization" and "increase" in action:
                adaptations["priority_adjustments"]["increase_complexity"] = True
            elif rec_type == "discovery_optimization":
                if "error_monitor" in action:
                    adaptations["discovery_adjustments"][
                        "boost_error_monitoring"
                    ] = True
                elif "code_quality" in action:
                    adaptations["discovery_adjustments"]["boost_code_quality"] = True
            elif rec_type == "failure_prevention":
                if "timeout" in action:
                    adaptations["execution_adjustments"]["increase_timeout"] = True

        return adaptations

    async def health_check(self) -> Dict[str, Any]:
        """Return health status of feedback processor"""
        return {
            "learning_cache_size": len(self.learning_cache),
            "last_processing_time": self.learning_cache.get("last_insights", {}).get(
                "timestamp"
            ),
            "available_insights": list(self.learning_cache.keys()),
        }
