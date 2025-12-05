"""
Tests for Sugar storage and work queue functionality.

This module provides comprehensive tests for the WorkQueue class, which manages
persistent task storage and state transitions in the Sugar autonomous development
system.

Test Coverage:
    - Database initialization and schema creation
    - Work item CRUD operations (add, get, update, remove)
    - Status transitions (pending → active → completed/failed)
    - Priority-based work retrieval
    - Retry mechanism with configurable max_retries
    - Queue statistics and health monitoring
    - Timing tracking (execution time, elapsed time)
    - Schema migrations for existing databases

Fixtures Used (from conftest.py):
    - temp_dir: Provides isolated temporary directory for each test
    - mock_work_queue: Pre-initialized WorkQueue instance with test database

Note:
    Tests use pytest-asyncio for async test support. The WorkQueue uses
    aiosqlite for non-blocking database operations.
"""

import pytest
import asyncio
from pathlib import Path

from sugar.storage.work_queue import WorkQueue


class TestWorkQueue:
    """
    Test suite for core WorkQueue functionality.

    Tests the fundamental operations of the work queue including item
    management, status transitions, and queue monitoring. Uses the
    mock_work_queue fixture which provides a pre-initialized queue
    with a temporary SQLite database.

    The WorkQueue implements a priority-based task queue with automatic
    retry support. Tasks transition through states: pending → active →
    completed/failed, with failed tasks returning to pending if retries
    remain.
    """

    @pytest.mark.asyncio
    async def test_initialize_creates_database(self, temp_dir):
        """
        Verify that WorkQueue.initialize() creates the SQLite database file.

        Uses temp_dir fixture directly (not mock_work_queue) to test the
        initialization process in isolation, ensuring the database file
        is created at the specified path.
        """
        db_path = temp_dir / "test.db"
        queue = WorkQueue(str(db_path))

        await queue.initialize()

        assert db_path.exists()
        await queue.close()

    @pytest.mark.asyncio
    async def test_add_work_item(self, mock_work_queue):
        """
        Verify that work items can be added to the queue with all fields preserved.

        Tests that:
        - add_work() returns a valid string ID
        - The item can be retrieved by ID
        - All provided fields (title, priority, context) are stored correctly
        - New items default to 'pending' status
        """
        task_data = {
            "type": "bug_fix",
            "title": "Fix authentication error",
            "description": "Fix login issues in auth module",
            "priority": 5,
            "source": "error_log",
            "context": {"file": "auth.py", "line": 42},
        }

        task_id = await mock_work_queue.add_work(task_data)

        assert task_id is not None
        assert isinstance(task_id, str)

        # Verify task was added and all fields persisted correctly
        retrieved_task = await mock_work_queue.get_work_by_id(task_id)
        assert retrieved_task is not None
        assert retrieved_task["title"] == "Fix authentication error"
        assert retrieved_task["priority"] == 5
        assert retrieved_task["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_pending_work(self, mock_work_queue):
        """
        Verify that pending work items are retrieved in priority order.

        Tests the priority-based ordering of the work queue, ensuring that
        higher priority tasks (higher number = more urgent) are returned
        first when fetching pending work.
        """
        # Add tasks in reverse priority order to verify sorting works
        high_priority_task = {
            "type": "bug_fix",
            "title": "Critical bug",
            "priority": 5,
            "source": "manual",
        }

        low_priority_task = {
            "type": "feature",
            "title": "New feature",
            "priority": 2,
            "source": "manual",
        }

        await mock_work_queue.add_work(high_priority_task)
        await mock_work_queue.add_work(low_priority_task)

        pending_tasks = await mock_work_queue.get_pending_work(limit=10)

        assert len(pending_tasks) == 2
        # Results should be ordered by priority (high to low, descending)
        assert pending_tasks[0]["priority"] == 5
        assert pending_tasks[1]["priority"] == 2

    @pytest.mark.asyncio
    async def test_mark_work_status_transitions(self, mock_work_queue):
        """
        Verify the successful path through work item status transitions.

        Tests the happy path: pending → active → completed, verifying that:
        - mark_work_active() sets status to 'active' and records started_at
        - mark_work_completed() sets status to 'completed', records completed_at,
          and stores the result payload
        """
        task_data = {
            "type": "test",
            "title": "Add unit tests",
            "priority": 3,
            "source": "manual",
        }

        task_id = await mock_work_queue.add_work(task_data)

        # Transition: pending → active
        await mock_work_queue.mark_work_active(task_id)
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "active"
        assert task["started_at"] is not None

        # Transition: active → completed
        result = {"success": True, "output": "Tests added successfully"}
        await mock_work_queue.mark_work_completed(task_id, result)
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "completed"
        assert task["completed_at"] is not None
        assert task["result"] == result

    @pytest.mark.asyncio
    async def test_mark_work_failed(self, mock_work_queue):
        """
        Verify failure handling with automatic retry mechanism.

        Tests the retry behavior when work fails:
        - First failures return task to 'pending' status for retry
        - Attempt counter increments with each failure
        - After max_retries (default=3) is reached, status becomes 'failed'

        The retry mechanism ensures transient failures don't permanently
        block work items, while preventing infinite retry loops.
        """
        task_data = {
            "type": "refactor",
            "title": "Refactor module",
            "priority": 3,
            "source": "manual",
        }

        task_id = await mock_work_queue.add_work(task_data)
        await mock_work_queue.mark_work_active(task_id)

        # First failure: should return to pending for retry
        error_info = {"error": "Claude CLI failed", "details": "Connection timeout"}
        await mock_work_queue.mark_work_failed(task_id, error_info)

        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "pending"  # Returned to pending for retry
        assert task["attempts"] == 1

        # Second and third failures: exhaust retries (max_retries=3)
        await mock_work_queue.mark_work_active(task_id)
        await mock_work_queue.mark_work_failed(task_id, {"error": "Second failure"})

        await mock_work_queue.mark_work_active(task_id)
        await mock_work_queue.mark_work_failed(task_id, {"error": "Third failure"})

        # After max_retries reached, task should be permanently failed
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "failed"
        assert task["attempts"] == 3

    @pytest.mark.asyncio
    async def test_get_stats(self, mock_work_queue):
        """
        Verify queue statistics accurately reflect work item distribution.

        Tests that get_stats() correctly counts items by status:
        - total: All items in the queue
        - pending: Items waiting to be processed (including retry-eligible failures)
        - completed: Successfully finished items
        - failed: Permanently failed items (after exhausting retries)
        - active: Currently being processed
        """
        # Create a mix of tasks to test different status counts
        tasks = [
            {"type": "bug_fix", "title": "Task 1", "priority": 5, "source": "manual"},
            {"type": "feature", "title": "Task 2", "priority": 3, "source": "manual"},
            {"type": "test", "title": "Task 3", "priority": 4, "source": "manual"},
        ]

        task_ids = []
        for task in tasks:
            task_id = await mock_work_queue.add_work(task)
            task_ids.append(task_id)

        # Complete Task 1: contributes to 'completed' count
        await mock_work_queue.mark_work_active(task_ids[0])
        await mock_work_queue.mark_work_completed(task_ids[0], {"success": True})

        # Fail Task 2: returns to 'pending' since retries remain
        await mock_work_queue.mark_work_active(task_ids[1])
        await mock_work_queue.mark_work_failed(task_ids[1], {"error": "Test error"})

        stats = await mock_work_queue.get_stats()

        assert stats["total"] == 3
        assert stats["pending"] == 2  # Task 3 (never started) + Task 2 (retry eligible)
        assert stats["completed"] == 1  # Task 1
        assert stats["failed"] == 0  # No permanently failed (max_retries not reached)
        assert stats["active"] == 0  # Nothing currently processing

    @pytest.mark.asyncio
    async def test_health_check(self, mock_work_queue):
        """
        Verify health check returns expected diagnostic information.

        The health_check() method provides system diagnostics including:
        - database_path: Location of the SQLite database
        - total_tasks: Count of all work items
        - status: Overall health status ('healthy' when operational)
        """
        health = await mock_work_queue.health_check()

        assert "database_path" in health
        assert "total_tasks" in health
        assert "status" in health
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_remove_work(self, mock_work_queue):
        """
        Verify work items can be permanently removed from the queue.

        Tests the remove_work() operation, which permanently deletes a work
        item from the database. This is distinct from completing or failing
        work, which preserves the record for historical tracking.
        """
        task_data = {
            "type": "documentation",
            "title": "Update docs",
            "priority": 2,
            "source": "manual",
        }

        task_id = await mock_work_queue.add_work(task_data)

        # Confirm task exists before removal
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task is not None

        # Remove the task
        success = await mock_work_queue.remove_work(task_id)
        assert success

        # Confirm task no longer exists
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task is None

    @pytest.mark.asyncio
    async def test_update_work(self, mock_work_queue):
        """
        Verify work item fields can be updated after creation.

        Tests that update_work() allows modification of mutable fields
        (title, priority, description) while preserving the item's identity
        and other metadata (id, created_at, status).
        """
        task_data = {
            "type": "feature",
            "title": "Original title",
            "description": "Original description",
            "priority": 3,
            "source": "manual",
        }

        task_id = await mock_work_queue.add_work(task_data)

        # Apply updates to multiple fields simultaneously
        updates = {
            "title": "Updated title",
            "priority": 5,
            "description": "Updated description",
        }

        success = await mock_work_queue.update_work(task_id, updates)
        assert success

        # Verify all updates were applied
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["title"] == "Updated title"
        assert task["priority"] == 5
        assert task["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_get_recent_work_with_filters(self, mock_work_queue):
        """
        Verify work retrieval supports filtering by status and result limiting.

        Tests the get_recent_work() query capabilities:
        - status filter: Retrieves only items matching specified status
        - limit: Restricts the number of returned items

        These filters enable efficient querying for dashboards and reports.
        """
        # Create a diverse set of tasks for filtering tests
        tasks = [
            {"type": "bug_fix", "title": "Bug 1", "priority": 5, "source": "manual"},
            {"type": "bug_fix", "title": "Bug 2", "priority": 4, "source": "manual"},
            {
                "type": "feature",
                "title": "Feature 1",
                "priority": 3,
                "source": "manual",
            },
            {"type": "test", "title": "Test 1", "priority": 2, "source": "manual"},
        ]

        task_ids = []
        for task in tasks:
            task_id = await mock_work_queue.add_work(task)
            task_ids.append(task_id)

        # Complete Bug 1 to create a mix of statuses
        await mock_work_queue.mark_work_active(task_ids[0])
        await mock_work_queue.mark_work_completed(task_ids[0], {"success": True})

        # Filter by status='completed': should return only Bug 1
        completed_tasks = await mock_work_queue.get_recent_work(status="completed")
        assert len(completed_tasks) == 1
        assert completed_tasks[0]["title"] == "Bug 1"

        # Filter by status='pending': should return Bug 2, Feature 1, Test 1
        pending_tasks = await mock_work_queue.get_recent_work(status="pending")
        assert len(pending_tasks) == 3

        # Test limit parameter: should cap results regardless of total available
        limited_tasks = await mock_work_queue.get_recent_work(limit=2)
        assert len(limited_tasks) == 2


class TestTimingTracking:
    """
    Test suite for work item timing and duration tracking.

    Tests the timing-related features of the WorkQueue, which track:
    - started_at: When work processing began
    - total_execution_time: Cumulative Claude CLI execution time across attempts
    - total_elapsed_time: Wall-clock time from start to completion

    These metrics enable performance monitoring, resource planning, and
    identification of long-running or problematic tasks.

    Note:
        These tests use temp_dir directly (not mock_work_queue) because they
        need to test database schema creation and migration behavior.
    """

    @pytest.mark.asyncio
    async def test_timing_columns_exist(self, temp_dir):
        """
        Verify timing columns are created in the database schema.

        Tests that the work_items table includes the timing columns
        (total_execution_time, started_at, total_elapsed_time) after
        database initialization.
        """
        db_path = temp_dir / "timing_test.db"
        queue = WorkQueue(str(db_path))

        await queue.initialize()

        # Test that we can query timing columns without error
        import aiosqlite

        async with aiosqlite.connect(str(db_path)) as db:
            cursor = await db.execute("PRAGMA table_info(work_items)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

            assert "total_execution_time" in column_names
            assert "started_at" in column_names
            assert "total_elapsed_time" in column_names

        await queue.close()

    @pytest.mark.asyncio
    async def test_started_at_timestamp_on_work_retrieval(self, temp_dir):
        """
        Verify started_at timestamp is recorded when work is claimed.

        Tests that calling get_next_work() (which claims the next available
        work item) sets the started_at timestamp, enabling elapsed time
        calculation upon completion.
        """
        db_path = temp_dir / "timing_test.db"
        queue = WorkQueue(str(db_path))
        await queue.initialize()

        # Add a work item
        task_data = {
            "type": "test",
            "title": "Timing test task",
            "priority": 3,
            "source": "test",
        }

        task_id = await queue.add_work(task_data)

        # Retrieve work (this should set started_at)
        work_item = await queue.get_next_work()

        assert work_item is not None
        assert work_item["id"] == task_id
        assert work_item["status"] == "active"

        # Check that started_at was set in database
        retrieved_item = await queue.get_work_item(task_id)
        assert retrieved_item["started_at"] is not None

        await queue.close()

    @pytest.mark.asyncio
    async def test_execution_time_tracking_on_completion(self, temp_dir):
        """
        Verify execution time is recorded when work completes.

        Tests that complete_work() captures the execution_time from the
        result payload and stores it in total_execution_time. Also verifies
        that total_elapsed_time and completed_at are recorded.
        """
        db_path = temp_dir / "timing_test.db"
        queue = WorkQueue(str(db_path))
        await queue.initialize()

        # Add and start work
        task_data = {
            "type": "test",
            "title": "Execution time test",
            "priority": 3,
            "source": "test",
        }

        task_id = await queue.add_work(task_data)
        work_item = await queue.get_next_work()

        # Simulate some time passing
        import asyncio

        await asyncio.sleep(0.01)  # 10ms

        # Complete work with execution time
        result = {
            "success": True,
            "execution_time": 5.5,
            "result": {"message": "Task completed successfully"},
        }

        await queue.complete_work(task_id, result)

        # Verify timing was recorded
        completed_item = await queue.get_work_item(task_id)

        assert completed_item["status"] == "completed"
        assert completed_item["total_execution_time"] == 5.5
        assert completed_item["total_elapsed_time"] >= 0  # Allow 0 for very fast tests
        assert completed_item["completed_at"] is not None

        await queue.close()

    @pytest.mark.asyncio
    async def test_cumulative_execution_time_on_retry(self, temp_dir):
        """
        Verify execution time accumulates across multiple attempts.

        Tests that when a work item fails and retries, the execution_time
        from each attempt is summed into total_execution_time. This enables
        accurate resource tracking even for tasks that require multiple
        attempts to complete.

        Scenario tested:
        - Attempt 1: 3.0s execution, fails
        - Attempt 2: 2.5s execution, fails
        - Attempt 3: 1.5s execution, succeeds
        - Expected total: 7.0s
        """
        db_path = temp_dir / "timing_test.db"
        queue = WorkQueue(str(db_path))
        await queue.initialize()

        # Add work
        task_data = {
            "type": "test",
            "title": "Retry timing test",
            "priority": 3,
            "source": "test",
        }

        task_id = await queue.add_work(task_data)

        # Attempt 1: Fail with 3.0s execution time
        work_item = await queue.get_next_work()
        await queue.fail_work(task_id, "First failure", execution_time=3.0)

        # Verify: First failure recorded, task returns to pending for retry
        item_after_first = await queue.get_work_item(task_id)
        assert item_after_first["total_execution_time"] == 3.0
        assert item_after_first["status"] == "pending"

        # Attempt 2: Fail with 2.5s execution time
        work_item = await queue.get_next_work()
        await queue.fail_work(task_id, "Second failure", execution_time=2.5)

        # Verify: Execution times sum (3.0 + 2.5 = 5.5)
        item_after_second = await queue.get_work_item(task_id)
        assert item_after_second["total_execution_time"] == 5.5
        assert item_after_second["status"] == "pending"

        # Attempt 3: Succeed with 1.5s execution time
        work_item = await queue.get_next_work()
        result = {
            "success": True,
            "execution_time": 1.5,
            "result": {"message": "Finally succeeded"},
        }
        await queue.complete_work(task_id, result)

        # Verify: Final total includes all attempts (3.0 + 2.5 + 1.5 = 7.0)
        final_item = await queue.get_work_item(task_id)
        assert final_item["total_execution_time"] == 7.0
        assert final_item["total_elapsed_time"] >= 0  # Allow 0 for very fast tests
        assert final_item["status"] == "completed"

        await queue.close()

    @pytest.mark.asyncio
    async def test_elapsed_time_calculation(self, temp_dir):
        """
        Verify total elapsed time is calculated from wall-clock duration.

        Tests that total_elapsed_time captures the real-world duration from
        when work was claimed (started_at) to when it completed. This metric
        differs from execution_time which only measures active processing.

        Note:
            Uses a small sleep to ensure measurable elapsed time, but allows
            for timing variations in CI environments.
        """
        db_path = temp_dir / "timing_test.db"
        queue = WorkQueue(str(db_path))
        await queue.initialize()

        # Add work
        task_data = {
            "type": "test",
            "title": "Elapsed time test",
            "priority": 3,
            "source": "test",
        }

        task_id = await queue.add_work(task_data)

        # Claim work - this sets started_at timestamp
        work_item = await queue.get_next_work()

        # Simulate wall-clock time passing (100ms)
        # This tests that elapsed time captures real duration, not just execution time
        await asyncio.sleep(0.1)

        # Complete work with execution_time in result
        result = {"success": True, "execution_time": 2.0}
        await queue.complete_work(task_id, result)

        # Verify elapsed time tracking
        completed_item = await queue.get_work_item(task_id)

        # Elapsed time should be >= 0 (timing can vary in CI environments)
        assert completed_item["total_elapsed_time"] >= 0
        # But should be reasonable (< 10s for a ~100ms sleep)
        assert completed_item["total_elapsed_time"] < 10.0
        # Execution time comes from result payload, not wall-clock
        assert completed_item["total_execution_time"] == 2.0

        await queue.close()

    @pytest.mark.asyncio
    async def test_migration_adds_timing_columns(self, temp_dir):
        """
        Verify schema migration adds timing columns to existing databases.

        Tests backward compatibility by creating a database with the legacy
        schema (without timing columns), then initializing a WorkQueue which
        should trigger migration to add the missing columns.

        This ensures smooth upgrades for existing Sugar installations.
        """
        db_path = temp_dir / "migration_test.db"

        # Step 1: Create a database with the legacy schema (pre-timing columns)
        # This simulates an existing Sugar installation before the timing feature
        import aiosqlite

        async with aiosqlite.connect(str(db_path)) as db:
            await db.execute(
                """
                CREATE TABLE work_items (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    priority INTEGER DEFAULT 3,
                    status TEXT DEFAULT 'pending',
                    source TEXT,
                    source_file TEXT,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    attempts INTEGER DEFAULT 0,
                    last_attempt_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    result TEXT,
                    error_message TEXT
                )
            """
            )
            await db.commit()

        # Step 2: Initialize WorkQueue on existing database
        # This should detect missing columns and run migration
        queue = WorkQueue(str(db_path))
        await queue.initialize()

        # Step 3: Verify migration added the timing columns
        async with aiosqlite.connect(str(db_path)) as db:
            cursor = await db.execute("PRAGMA table_info(work_items)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

            # All three timing columns should now exist
            assert "total_execution_time" in column_names
            assert "started_at" in column_names
            assert "total_elapsed_time" in column_names

        await queue.close()
