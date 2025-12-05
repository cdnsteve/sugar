"""
Pytest fixtures for learning module tests.
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock
import json


@pytest.fixture
def sample_completed_tasks():
    """Sample completed task data for testing feedback processor."""
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
def sample_failed_tasks():
    """Sample failed task data for testing feedback processor."""
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


@pytest.fixture
def mock_work_queue_with_data(sample_completed_tasks, sample_failed_tasks):
    """Create a mock work queue with sample data."""
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
def mock_work_queue_empty():
    """Create a mock work queue with no data."""
    mock_queue = Mock()
    mock_queue.get_recent_work = AsyncMock(return_value=[])
    return mock_queue


@pytest.fixture
def sample_work_items():
    """Sample work items for scheduler testing."""
    return [
        {"id": "work-1", "priority": 5, "source": "error_monitor", "type": "bug_fix"},
        {"id": "work-2", "priority": 3, "source": "manual", "type": "feature"},
        {"id": "work-3", "priority": 7, "source": "code_quality", "type": "refactor"},
        {"id": "work-4", "priority": 4, "source": "error_monitor", "type": "bug_fix"},
    ]


@pytest.fixture
def sample_insights():
    """Sample learning insights for scheduler testing."""
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
