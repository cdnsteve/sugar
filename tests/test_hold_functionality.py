"""
Tests for Sugar hold/release functionality
"""

import pytest
from datetime import datetime


class TestHoldFunctionality:
    """Test hold/release functionality for tasks"""

    @pytest.mark.asyncio
    async def test_hold_work_basic(self, mock_work_queue):
        """Test basic hold functionality"""
        task_data = {
            "type": "feature",
            "title": "Test hold feature",
            "priority": 3,
            "source": "manual",
        }

        task_id = await mock_work_queue.add_work(task_data)

        # Put task on hold
        success = await mock_work_queue.hold_work(task_id, "Waiting for review")
        assert success

        # Verify task is on hold
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "hold"
        assert task["context"]["hold_reason"] == "Waiting for review"
        assert "held_at" in task["context"]

    @pytest.mark.asyncio
    async def test_hold_work_without_reason(self, mock_work_queue):
        """Test holding work without specifying a reason"""
        task_data = {
            "type": "bug_fix",
            "title": "Fix bug",
            "priority": 4,
            "source": "manual",
        }

        task_id = await mock_work_queue.add_work(task_data)

        # Put task on hold without reason
        success = await mock_work_queue.hold_work(task_id)
        assert success

        # Verify task is on hold
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "hold"
        # Context should not have hold_reason if not provided
        assert "hold_reason" not in task["context"]

    @pytest.mark.asyncio
    async def test_hold_nonexistent_task(self, mock_work_queue):
        """Test holding a task that doesn't exist"""
        success = await mock_work_queue.hold_work("nonexistent-id")
        assert not success

    @pytest.mark.asyncio
    async def test_release_work_basic(self, mock_work_queue):
        """Test basic release functionality"""
        task_data = {
            "type": "test",
            "title": "Add tests",
            "priority": 2,
            "source": "manual",
        }

        task_id = await mock_work_queue.add_work(task_data)

        # Put task on hold first
        await mock_work_queue.hold_work(task_id, "Blocked by dependency")

        # Verify it's on hold
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "hold"

        # Release task
        success = await mock_work_queue.release_work(task_id)
        assert success

        # Verify task is back to pending
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "pending"
        assert "hold_reason" not in task["context"]
        assert "held_at" not in task["context"]
        assert "released_at" in task["context"]

    @pytest.mark.asyncio
    async def test_release_nonexistent_task(self, mock_work_queue):
        """Test releasing a task that doesn't exist"""
        success = await mock_work_queue.release_work("nonexistent-id")
        assert not success

    @pytest.mark.asyncio
    async def test_release_non_hold_task(self, mock_work_queue):
        """Test releasing a task that isn't on hold"""
        task_data = {
            "type": "refactor",
            "title": "Refactor code",
            "priority": 3,
            "source": "manual",
        }

        task_id = await mock_work_queue.add_work(task_data)

        # Try to release task that's not on hold
        success = await mock_work_queue.release_work(task_id)
        assert not success

        # Verify task status unchanged
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_next_work_skips_hold_tasks(self, mock_work_queue):
        """Test that get_next_work skips tasks on hold"""
        # Add two tasks
        task1_data = {
            "type": "feature",
            "title": "Task 1",
            "priority": 5,
            "source": "manual",
        }
        task2_data = {
            "type": "bug_fix",
            "title": "Task 2",
            "priority": 4,
            "source": "manual",
        }

        task1_id = await mock_work_queue.add_work(task1_data)
        task2_id = await mock_work_queue.add_work(task2_data)

        # Put higher priority task on hold
        await mock_work_queue.hold_work(task1_id, "Waiting for approval")

        # Get next work should return the lower priority task
        next_work = await mock_work_queue.get_next_work()
        assert next_work is not None
        assert next_work["id"] == task2_id
        assert next_work["title"] == "Task 2"

    @pytest.mark.asyncio
    async def test_hold_release_preserves_priority_order(self, mock_work_queue):
        """Test that released tasks maintain their priority in the queue"""
        # Add multiple tasks with different priorities
        tasks = [
            {
                "type": "bug_fix",
                "title": "Low priority",
                "priority": 2,
                "source": "manual",
            },
            {
                "type": "feature",
                "title": "High priority",
                "priority": 5,
                "source": "manual",
            },
            {
                "type": "test",
                "title": "Medium priority",
                "priority": 3,
                "source": "manual",
            },
        ]

        task_ids = []
        for task in tasks:
            task_id = await mock_work_queue.add_work(task)
            task_ids.append(task_id)

        # Put high priority task on hold
        await mock_work_queue.hold_work(task_ids[1], "On hold")

        # Get next work - should be medium priority (3)
        next_work = await mock_work_queue.get_next_work()
        assert next_work["priority"] == 3

        # Release high priority task
        await mock_work_queue.release_work(task_ids[1])

        # Get next work - should now be high priority (5)
        next_work = await mock_work_queue.get_next_work()
        assert next_work["priority"] == 5

    @pytest.mark.asyncio
    async def test_stats_include_hold_count(self, mock_work_queue):
        """Test that queue statistics include hold count"""
        # Add tasks with different statuses
        tasks = [
            {
                "type": "bug_fix",
                "title": "Pending task",
                "priority": 3,
                "source": "manual",
            },
            {
                "type": "feature",
                "title": "Hold task 1",
                "priority": 4,
                "source": "manual",
            },
            {
                "type": "test",
                "title": "Hold task 2",
                "priority": 2,
                "source": "manual",
            },
        ]

        task_ids = []
        for task in tasks:
            task_id = await mock_work_queue.add_work(task)
            task_ids.append(task_id)

        # Put two tasks on hold
        await mock_work_queue.hold_work(task_ids[1], "First hold")
        await mock_work_queue.hold_work(task_ids[2], "Second hold")

        # Complete one task
        await mock_work_queue.mark_work_active(task_ids[0])
        await mock_work_queue.mark_work_completed(task_ids[0], {"success": True})

        stats = await mock_work_queue.get_stats()

        assert stats["total"] == 3
        assert stats["pending"] == 0
        assert stats["hold"] == 2
        assert stats["completed"] == 1
        assert stats["failed"] == 0
        assert stats["active"] == 0

    @pytest.mark.asyncio
    async def test_hold_context_data_integrity(self, mock_work_queue):
        """Test that hold context data doesn't interfere with existing context"""
        task_data = {
            "type": "feature",
            "title": "Context test",
            "priority": 3,
            "source": "manual",
            "context": {
                "existing_key": "existing_value",
                "nested": {"data": "preserved"},
            },
        }

        task_id = await mock_work_queue.add_work(task_data)

        # Put on hold
        await mock_work_queue.hold_work(task_id, "Testing context")

        # Verify existing context preserved and hold data added
        task = await mock_work_queue.get_work_by_id(task_id)
        context = task["context"]

        assert context["existing_key"] == "existing_value"
        assert context["nested"]["data"] == "preserved"
        assert context["hold_reason"] == "Testing context"
        assert "held_at" in context

        # Release and verify cleanup
        await mock_work_queue.release_work(task_id)

        task = await mock_work_queue.get_work_by_id(task_id)
        context = task["context"]

        assert context["existing_key"] == "existing_value"
        assert context["nested"]["data"] == "preserved"
        assert "hold_reason" not in context
        assert "held_at" not in context
        assert "released_at" in context

    @pytest.mark.asyncio
    async def test_hold_already_held_task(self, mock_work_queue):
        """Test holding a task that's already on hold updates the reason"""
        task_data = {
            "type": "feature",
            "title": "Already held task",
            "priority": 3,
            "source": "manual",
        }

        task_id = await mock_work_queue.add_work(task_data)

        # Put task on hold first time
        await mock_work_queue.hold_work(task_id, "First reason")
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["context"]["hold_reason"] == "First reason"

        # Put task on hold again with different reason
        success = await mock_work_queue.hold_work(task_id, "Updated reason")
        assert success

        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "hold"
        assert task["context"]["hold_reason"] == "Updated reason"

    @pytest.mark.asyncio
    async def test_hold_completed_task(self, mock_work_queue):
        """Test that completed tasks can still be put on hold"""
        task_data = {
            "type": "test",
            "title": "Completed task",
            "priority": 2,
            "source": "manual",
        }

        task_id = await mock_work_queue.add_work(task_data)

        # Complete the task
        await mock_work_queue.mark_work_active(task_id)
        await mock_work_queue.mark_work_completed(task_id, {"success": True})

        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "completed"

        # Try to put completed task on hold
        success = await mock_work_queue.hold_work(task_id, "Needs review")
        assert success

        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "hold"

    @pytest.mark.asyncio
    async def test_multiple_hold_release_cycles(self, mock_work_queue):
        """Test multiple hold/release cycles on the same task"""
        task_data = {
            "type": "feature",
            "title": "Cycling task",
            "priority": 3,
            "source": "manual",
        }

        task_id = await mock_work_queue.add_work(task_data)

        # First cycle
        await mock_work_queue.hold_work(task_id, "Cycle 1")
        await mock_work_queue.release_work(task_id)

        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "pending"
        assert "released_at" in task["context"]

        # Second cycle
        await mock_work_queue.hold_work(task_id, "Cycle 2")
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "hold"
        assert task["context"]["hold_reason"] == "Cycle 2"

        await mock_work_queue.release_work(task_id)
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "pending"

    @pytest.mark.asyncio
    async def test_held_at_timestamp_format(self, mock_work_queue):
        """Test that held_at timestamp is valid ISO format"""
        task_data = {
            "type": "test",
            "title": "Timestamp test",
            "priority": 2,
            "source": "manual",
        }

        task_id = await mock_work_queue.add_work(task_data)
        await mock_work_queue.hold_work(task_id, "Testing timestamp")

        task = await mock_work_queue.get_work_by_id(task_id)
        held_at = task["context"]["held_at"]

        # Verify it's a valid ISO format timestamp
        parsed = datetime.fromisoformat(held_at)
        assert isinstance(parsed, datetime)

    @pytest.mark.asyncio
    async def test_released_at_timestamp_format(self, mock_work_queue):
        """Test that released_at timestamp is valid ISO format"""
        task_data = {
            "type": "test",
            "title": "Release timestamp test",
            "priority": 2,
            "source": "manual",
        }

        task_id = await mock_work_queue.add_work(task_data)
        await mock_work_queue.hold_work(task_id, "Testing release")
        await mock_work_queue.release_work(task_id)

        task = await mock_work_queue.get_work_by_id(task_id)
        released_at = task["context"]["released_at"]

        # Verify it's a valid ISO format timestamp
        parsed = datetime.fromisoformat(released_at)
        assert isinstance(parsed, datetime)
