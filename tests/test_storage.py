"""
Tests for Sugar storage and work queue functionality
"""
import pytest
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

from sugar.storage.work_queue import WorkQueue


class TestWorkQueue:
    """Test WorkQueue functionality"""
    
    @pytest.mark.asyncio
    async def test_initialize_creates_database(self, temp_dir):
        """Test that initialize creates the database file"""
        db_path = temp_dir / "test.db"
        queue = WorkQueue(str(db_path))
        
        await queue.initialize()
        
        assert db_path.exists()
        await queue.close()
    
    @pytest.mark.asyncio
    async def test_add_work_item(self, mock_work_queue):
        """Test adding a work item to the queue"""
        task_data = {
            "type": "bug_fix",
            "title": "Fix authentication error",
            "description": "Fix login issues in auth module",
            "priority": 5,
            "source": "error_log",
            "context": {"file": "auth.py", "line": 42}
        }
        
        task_id = await mock_work_queue.add_work(task_data)
        
        assert task_id is not None
        assert isinstance(task_id, str)
        
        # Verify task was added
        retrieved_task = await mock_work_queue.get_work_by_id(task_id)
        assert retrieved_task is not None
        assert retrieved_task["title"] == "Fix authentication error"
        assert retrieved_task["priority"] == 5
        assert retrieved_task["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_get_pending_work(self, mock_work_queue):
        """Test retrieving pending work items"""
        # Add multiple tasks with different priorities
        high_priority_task = {
            "type": "bug_fix",
            "title": "Critical bug",
            "priority": 5,
            "source": "manual"
        }
        
        low_priority_task = {
            "type": "feature", 
            "title": "New feature",
            "priority": 2,
            "source": "manual"
        }
        
        await mock_work_queue.add_work(high_priority_task)
        await mock_work_queue.add_work(low_priority_task)
        
        pending_tasks = await mock_work_queue.get_pending_work(limit=10)
        
        assert len(pending_tasks) == 2
        # Should be ordered by priority (high to low)
        assert pending_tasks[0]["priority"] == 5
        assert pending_tasks[1]["priority"] == 2
    
    @pytest.mark.asyncio
    async def test_mark_work_status_transitions(self, mock_work_queue):
        """Test work status transitions"""
        task_data = {
            "type": "test",
            "title": "Add unit tests",
            "priority": 3,
            "source": "manual"
        }
        
        task_id = await mock_work_queue.add_work(task_data)
        
        # Mark as active
        await mock_work_queue.mark_work_active(task_id)
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "active"
        assert task["started_at"] is not None
        
        # Mark as completed
        result = {"success": True, "output": "Tests added successfully"}
        await mock_work_queue.mark_work_completed(task_id, result)
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "completed"
        assert task["completed_at"] is not None
        assert task["result"] == result
    
    @pytest.mark.asyncio
    async def test_mark_work_failed(self, mock_work_queue):
        """Test marking work as failed"""
        task_data = {
            "type": "refactor",
            "title": "Refactor module",
            "priority": 3,
            "source": "manual"
        }
        
        task_id = await mock_work_queue.add_work(task_data)
        await mock_work_queue.mark_work_active(task_id)
        
        error_info = {"error": "Claude CLI failed", "details": "Connection timeout"}
        await mock_work_queue.mark_work_failed(task_id, error_info)
        
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["status"] == "failed"
        assert task["error"] == error_info
        assert task["attempts"] == 1
    
    @pytest.mark.asyncio
    async def test_get_stats(self, mock_work_queue):
        """Test getting queue statistics"""
        # Add tasks with different statuses
        tasks = [
            {"type": "bug_fix", "title": "Task 1", "priority": 5, "source": "manual"},
            {"type": "feature", "title": "Task 2", "priority": 3, "source": "manual"},
            {"type": "test", "title": "Task 3", "priority": 4, "source": "manual"}
        ]
        
        task_ids = []
        for task in tasks:
            task_id = await mock_work_queue.add_work(task)
            task_ids.append(task_id)
        
        # Mark one as completed
        await mock_work_queue.mark_work_active(task_ids[0])
        await mock_work_queue.mark_work_completed(task_ids[0], {"success": True})
        
        # Mark one as failed
        await mock_work_queue.mark_work_active(task_ids[1])
        await mock_work_queue.mark_work_failed(task_ids[1], {"error": "Test error"})
        
        stats = await mock_work_queue.get_stats()
        
        assert stats["total"] == 3
        assert stats["pending"] == 1
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["active"] == 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, mock_work_queue):
        """Test queue health check"""
        health = await mock_work_queue.health_check()
        
        assert "database_path" in health
        assert "total_tasks" in health
        assert "status" in health
        assert health["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_remove_work(self, mock_work_queue):
        """Test removing work items"""
        task_data = {
            "type": "documentation",
            "title": "Update docs",
            "priority": 2,
            "source": "manual"
        }
        
        task_id = await mock_work_queue.add_work(task_data)
        
        # Verify task exists
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task is not None
        
        # Remove task
        success = await mock_work_queue.remove_work(task_id)
        assert success
        
        # Verify task is gone
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task is None
    
    @pytest.mark.asyncio
    async def test_update_work(self, mock_work_queue):
        """Test updating work items"""
        task_data = {
            "type": "feature",
            "title": "Original title",
            "description": "Original description",
            "priority": 3,
            "source": "manual"
        }
        
        task_id = await mock_work_queue.add_work(task_data)
        
        # Update task
        updates = {
            "title": "Updated title",
            "priority": 5,
            "description": "Updated description"
        }
        
        success = await mock_work_queue.update_work(task_id, updates)
        assert success
        
        # Verify updates
        task = await mock_work_queue.get_work_by_id(task_id)
        assert task["title"] == "Updated title"
        assert task["priority"] == 5
        assert task["description"] == "Updated description"
    
    @pytest.mark.asyncio
    async def test_get_recent_work_with_filters(self, mock_work_queue):
        """Test getting recent work with status and type filters"""
        # Add tasks of different types and statuses
        tasks = [
            {"type": "bug_fix", "title": "Bug 1", "priority": 5, "source": "manual"},
            {"type": "bug_fix", "title": "Bug 2", "priority": 4, "source": "manual"},
            {"type": "feature", "title": "Feature 1", "priority": 3, "source": "manual"},
            {"type": "test", "title": "Test 1", "priority": 2, "source": "manual"}
        ]
        
        task_ids = []
        for task in tasks:
            task_id = await mock_work_queue.add_work(task)
            task_ids.append(task_id)
        
        # Mark some as completed
        await mock_work_queue.mark_work_active(task_ids[0])
        await mock_work_queue.mark_work_completed(task_ids[0], {"success": True})
        
        # Test filtering by status
        completed_tasks = await mock_work_queue.get_recent_work(status="completed")
        assert len(completed_tasks) == 1
        assert completed_tasks[0]["title"] == "Bug 1"
        
        # Test filtering by status (pending)
        pending_tasks = await mock_work_queue.get_recent_work(status="pending")
        assert len(pending_tasks) == 3
        
        # Test limiting results
        limited_tasks = await mock_work_queue.get_recent_work(limit=2)
        assert len(limited_tasks) == 2