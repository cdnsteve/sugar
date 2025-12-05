"""
Pytest fixtures for learning module tests.

This module provides shared test fixtures for the Sugar learning subsystem,
which analyzes completed and failed tasks to extract patterns and improve
task scheduling decisions.

Fixture Organization:
--------------------
- Task Data Fixtures: Sample completed and failed task records with realistic
  metadata (sample_completed_tasks, sample_failed_tasks)
- Work Queue Mocks: Pre-configured AsyncMock objects simulating work queue
  behavior (mock_work_queue_with_data, mock_work_queue_empty)
- Scheduler Fixtures: Work items and learning insights for testing the
  adaptive scheduler (sample_work_items, sample_insights)

Task Data Structure:
-------------------
Tasks contain the following fields:
- id: Unique task identifier (e.g., "task-1")
- type: Task category ("bug_fix", "feature", "refactor")
- title: Human-readable description
- priority: Numeric priority (1-10, higher = more urgent)
- status: Current state ("completed", "failed", "pending")
- source: Discovery origin ("error_monitor", "manual", "code_quality")
- attempts: Number of execution attempts
- completed_at: ISO timestamp (completed tasks only)
- result: JSON-encoded execution result with success flag and metrics
- error_message: Failure reason (failed tasks only)
"""

import json
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest


# =============================================================================
# Task Data Fixtures
# =============================================================================


@pytest.fixture
def sample_completed_tasks() -> list[dict[str, Any]]:
    """
    Provide sample completed task records for testing the feedback processor.

    Returns a list of 5 completed tasks with varying characteristics:
    - 3 bug fixes from error_monitor (priorities 5, 7, 6)
    - 1 feature from manual source (priority 3, required 2 attempts)
    - 1 refactor from code_quality (priority 4)

    Each task includes a JSON-encoded `result` field containing:
    - success: Boolean indicating task success
    - result.execution_time: Time in seconds to complete
    - result.actions_taken: List of action identifiers performed
    - result.files_modified: List of file paths changed

    Used by:
        - FeedbackProcessor tests for pattern extraction
        - LearningEngine tests for insight generation
        - Scheduler tests for priority learning validation
    """
    return [
        {
            "id": "task-1",
            "type": "bug_fix",
            "title": "Fix authentication error",
            "priority": 5,
            "status": "completed",
            "source": "error_monitor",
            "attempts": 1,
            "completed_at": "2024-01-15T10:00:00Z",
            "result": json.dumps(
                {
                    "success": True,
                    "result": {
                        "execution_time": 45.5,
                        "actions_taken": ["fixed_bug"],
                        "files_modified": ["src/auth.py"],
                    },
                }
            ),
        },
        {
            "id": "task-2",
            "type": "feature",
            "title": "Add user registration",
            "priority": 3,
            "status": "completed",
            "source": "manual",
            "attempts": 2,
            "completed_at": "2024-01-16T14:00:00Z",
            "result": json.dumps(
                {
                    "success": True,
                    "result": {
                        "execution_time": 120.0,
                        "actions_taken": ["implemented_feature"],
                        "files_modified": ["src/user.py", "src/forms.py"],
                    },
                }
            ),
        },
        {
            "id": "task-3",
            "type": "bug_fix",
            "title": "Fix database connection",
            "priority": 7,
            "status": "completed",
            "source": "error_monitor",
            "attempts": 1,
            "completed_at": "2024-01-17T09:00:00Z",
            "result": json.dumps(
                {
                    "success": True,
                    "result": {
                        "execution_time": 30.0,
                        "actions_taken": ["fixed_bug"],
                        "files_modified": ["src/db.py"],
                    },
                }
            ),
        },
        {
            "id": "task-4",
            "type": "refactor",
            "title": "Refactor auth module",
            "priority": 4,
            "status": "completed",
            "source": "code_quality",
            "attempts": 1,
            "completed_at": "2024-01-18T11:00:00Z",
            "result": json.dumps(
                {
                    "success": True,
                    "result": {
                        "execution_time": 90.0,
                        "actions_taken": ["refactored"],
                        "files_modified": ["src/auth.py"],
                    },
                }
            ),
        },
        {
            "id": "task-5",
            "type": "bug_fix",
            "title": "Fix session handling",
            "priority": 6,
            "status": "completed",
            "source": "error_monitor",
            "attempts": 1,
            "completed_at": "2024-01-19T16:00:00Z",
            "result": json.dumps(
                {
                    "success": True,
                    "result": {
                        "execution_time": 55.0,
                        "actions_taken": ["fixed_bug"],
                        "files_modified": ["src/session.py"],
                    },
                }
            ),
        },
    ]


@pytest.fixture
def sample_failed_tasks() -> list[dict[str, Any]]:
    """
    Provide sample failed task records for testing failure pattern analysis.

    Returns a list of 3 failed tasks demonstrating common failure modes:
    - task-fail-1: Timeout after 3 attempts (feature, manual source)
    - task-fail-2: Missing file after 2 attempts (bug_fix, error_monitor)
    - task-fail-3: Syntax error on first attempt (feature, manual source)

    Failed tasks include an `error_message` field instead of `result`,
    describing the failure reason for pattern extraction.

    Used by:
        - FeedbackProcessor tests for failure pattern identification
        - LearningEngine tests for risk assessment
        - Retry strategy tests
    """
    return [
        {
            "id": "task-fail-1",
            "type": "feature",
            "title": "Add OAuth integration",
            "priority": 4,
            "status": "failed",
            "source": "manual",
            "attempts": 3,
            "error_message": "Timeout: task exceeded time limit",
        },
        {
            "id": "task-fail-2",
            "type": "bug_fix",
            "title": "Fix deployment script",
            "priority": 5,
            "status": "failed",
            "source": "error_monitor",
            "attempts": 2,
            "error_message": "File not found: deploy.sh does not exist",
        },
        {
            "id": "task-fail-3",
            "type": "feature",
            "title": "Add API endpoint",
            "priority": 3,
            "status": "failed",
            "source": "manual",
            "attempts": 1,
            "error_message": "Syntax error: invalid syntax in generated code",
        },
    ]


# =============================================================================
# Work Queue Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_work_queue_with_data(
    sample_completed_tasks: list[dict[str, Any]],
    sample_failed_tasks: list[dict[str, Any]],
) -> Mock:
    """
    Create a mock work queue pre-loaded with completed and failed task data.

    The mock's `get_recent_work` async method returns:
    - Completed tasks when called with status="completed"
    - Failed tasks when called with status="failed"
    - Results are sliced by the `limit` parameter

    Args:
        sample_completed_tasks: Fixture providing completed task records
        sample_failed_tasks: Fixture providing failed task records

    Returns:
        Mock object with configured AsyncMock for get_recent_work method

    Example:
        async def test_feedback(mock_work_queue_with_data):
            tasks = await mock_work_queue_with_data.get_recent_work(
                limit=3, status="completed"
            )
            assert len(tasks) == 3
    """
    mock_queue = Mock()
    mock_queue.get_recent_work = AsyncMock(
        side_effect=lambda limit, status: (
            sample_completed_tasks[:limit]
            if status == "completed"
            else sample_failed_tasks[:limit]
        )
    )
    return mock_queue


@pytest.fixture
def mock_work_queue_empty() -> Mock:
    """
    Create a mock work queue that returns empty results.

    Useful for testing edge cases where no historical task data is available,
    such as first-run scenarios or after data cleanup.

    Returns:
        Mock object with get_recent_work always returning an empty list
    """
    mock_queue = Mock()
    mock_queue.get_recent_work = AsyncMock(return_value=[])
    return mock_queue


# =============================================================================
# Scheduler Test Fixtures
# =============================================================================


@pytest.fixture
def sample_work_items() -> list[dict[str, Any]]:
    """
    Provide sample pending work items for scheduler priority testing.

    Returns 4 work items with different priority/source/type combinations
    to test the scheduler's ability to reorder based on learned patterns:
    - work-1: High-priority bug fix from error_monitor
    - work-2: Lower-priority feature from manual source
    - work-3: Highest-priority refactor from code_quality
    - work-4: Medium-priority bug fix from error_monitor

    These are intentionally minimal compared to sample_completed_tasks,
    containing only the fields needed for scheduling decisions.

    Used by:
        - AdaptiveScheduler tests for priority adjustment
        - Learning integration tests
    """
    return [
        {"id": "work-1", "priority": 5, "source": "error_monitor", "type": "bug_fix"},
        {"id": "work-2", "priority": 3, "source": "manual", "type": "feature"},
        {"id": "work-3", "priority": 7, "source": "code_quality", "type": "refactor"},
        {"id": "work-4", "priority": 4, "source": "error_monitor", "type": "bug_fix"},
    ]


@pytest.fixture
def sample_insights() -> dict[str, Any]:
    """
    Provide pre-computed learning insights for scheduler testing.

    Represents the output from the LearningEngine after analyzing historical
    task data. Contains statistical patterns and recommendations that the
    AdaptiveScheduler uses to optimize task prioritization.

    Structure:
        success_patterns: Counts of successful tasks by type, priority, source
        priority_effectiveness: Per-priority metrics including:
            - task_count: Number of tasks at this priority
            - average_execution_time: Mean completion time in seconds
            - efficiency_score: 0.0-1.0 score (higher = more efficient)
        discovery_source_effectiveness: Per-source metrics including:
            - task_count: Tasks discovered by this source
            - value_score: Weighted value contribution
        recommendations: Actionable suggestions from pattern analysis
        timestamp: When insights were generated

    The sample data reflects patterns from sample_completed_tasks:
    - bug_fix tasks are most successful (3 of 5)
    - error_monitor is the most valuable discovery source
    - Priority 7 has highest efficiency (fastest completion)

    Used by:
        - AdaptiveScheduler tests for priority boost calculations
        - Integration tests validating the learning-to-scheduling pipeline
    """
    return {
        "success_patterns": {
            "successful_task_types": {"bug_fix": 3, "feature": 1, "refactor": 1},
            "successful_priorities": {5: 2, 3: 1, 7: 1, 4: 1},
            "successful_sources": {"error_monitor": 3, "manual": 1, "code_quality": 1},
        },
        "priority_effectiveness": {
            5: {
                "task_count": 2,
                "average_execution_time": 50.0,
                "efficiency_score": 0.8,
            },
            7: {
                "task_count": 1,
                "average_execution_time": 30.0,
                "efficiency_score": 1.0,
            },
            3: {
                "task_count": 1,
                "average_execution_time": 120.0,
                "efficiency_score": 0.3,
            },
        },
        "discovery_source_effectiveness": {
            "error_monitor": {"task_count": 3, "value_score": 15.0},
            "manual": {"task_count": 1, "value_score": 3.0},
            "code_quality": {"task_count": 1, "value_score": 4.0},
        },
        "recommendations": [
            {"type": "focus_area", "action": "prioritize_bug_fix_tasks"},
            {
                "type": "discovery_optimization",
                "action": "optimize_error_monitor_discovery",
            },
        ],
        "timestamp": "2024-01-20T12:00:00",
    }
