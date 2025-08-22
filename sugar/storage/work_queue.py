"""
Work Queue - Manage work items with priorities and persistence
"""
import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import aiosqlite
import uuid

logger = logging.getLogger(__name__)

class WorkQueue:
    """Persistent work queue with priority management"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialized = False
    
    async def initialize(self):
        """Initialize the database and create tables"""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS work_items (
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
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_work_items_priority_status 
                ON work_items (priority DESC, status, created_at)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_work_items_status 
                ON work_items (status)
            """)
            
            await db.commit()
        
        self._initialized = True
        logger.debug(f"✅ Work queue initialized: {self.db_path}")
    
    async def work_exists(self, source_file: str, exclude_statuses: List[str] = None) -> bool:
        """Check if work item with given source_file already exists"""
        if exclude_statuses is None:
            exclude_statuses = ['failed']  # Don't prevent retrying failed items
        
        async with aiosqlite.connect(self.db_path) as db:
            query = "SELECT COUNT(*) FROM work_items WHERE source_file = ?"
            params = [source_file]
            
            if exclude_statuses:
                placeholders = ','.join('?' * len(exclude_statuses))
                query += f" AND status NOT IN ({placeholders})"
                params.extend(exclude_statuses)
            
            cursor = await db.execute(query, params)
            count = (await cursor.fetchone())[0]
            return count > 0

    async def add_work(self, work_item: Dict[str, Any]) -> str:
        """Add a new work item to the queue"""
        work_id = str(uuid.uuid4())
        
        # Set defaults
        work_item.setdefault('status', 'pending')
        work_item.setdefault('priority', 3)
        work_item.setdefault('attempts', 0)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO work_items 
                (id, type, title, description, priority, status, source, source_file, context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                work_id,
                work_item['type'],
                work_item['title'],
                work_item.get('description', ''),
                work_item['priority'],
                work_item['status'],
                work_item.get('source', ''),
                work_item.get('source_file', ''),
                json.dumps(work_item.get('context', {}))
            ))
            await db.commit()
        
        logger.debug(f"➕ Added work item: {work_item['title']} (priority: {work_item['priority']})")
        return work_id
    
    async def get_next_work(self) -> Optional[Dict[str, Any]]:
        """Get the highest priority pending work item"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get highest priority pending work item
            cursor = await db.execute("""
                SELECT * FROM work_items 
                WHERE status = 'pending' 
                ORDER BY priority DESC, created_at ASC 
                LIMIT 1
            """)
            
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            work_item = dict(row)
            
            # Parse JSON context
            if work_item['context']:
                try:
                    work_item['context'] = json.loads(work_item['context'])
                except json.JSONDecodeError:
                    work_item['context'] = {}
            else:
                work_item['context'] = {}
            
            # Mark as active and increment attempts
            await db.execute("""
                UPDATE work_items 
                SET status = 'active', 
                    attempts = attempts + 1,
                    last_attempt_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (work_item['id'],))
            
            await db.commit()
            
            work_item['attempts'] += 1
            logger.debug(f"📋 Retrieved work item: {work_item['title']} (attempt #{work_item['attempts']})")
            
            return work_item
    
    async def complete_work(self, work_id: str, result: Dict[str, Any]):
        """Mark a work item as completed with results"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE work_items 
                SET status = 'completed',
                    result = ?,
                    completed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (json.dumps(result), work_id))
            
            await db.commit()
        
        logger.debug(f"✅ Completed work item: {work_id}")
    
    async def fail_work(self, work_id: str, error_message: str, max_retries: int = 3):
        """Mark a work item as failed, or retry if under retry limit"""
        async with aiosqlite.connect(self.db_path) as db:
            # Get current attempts
            cursor = await db.execute("""
                SELECT attempts, title FROM work_items WHERE id = ?
            """, (work_id,))
            
            row = await cursor.fetchone()
            if not row:
                logger.error(f"Work item not found: {work_id}")
                return
            
            attempts, title = row
            
            if attempts >= max_retries:
                # Final failure
                await db.execute("""
                    UPDATE work_items 
                    SET status = 'failed',
                        error_message = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (error_message, work_id))
                
                logger.error(f"❌ Work item failed permanently: {title} (after {attempts} attempts)")
            else:
                # Retry later
                await db.execute("""
                    UPDATE work_items 
                    SET status = 'pending',
                        error_message = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (error_message, work_id))
                
                logger.warning(f"⚠️ Work item will be retried: {title} (attempt {attempts}/{max_retries})")
            
            await db.commit()
    
    async def get_work_item(self, work_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific work item by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            cursor = await db.execute("""
                SELECT * FROM work_items WHERE id = ?
            """, (work_id,))
            
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            work_item = dict(row)
            
            # Parse JSON fields
            for field in ['context', 'result']:
                if work_item[field]:
                    try:
                        work_item[field] = json.loads(work_item[field])
                    except json.JSONDecodeError:
                        work_item[field] = {}
                else:
                    work_item[field] = {}
            
            return work_item
    
    async def get_recent_work(self, limit: int = 10, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent work items, optionally filtered by status"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            query = "SELECT * FROM work_items"
            params = []
            
            if status:
                query += " WHERE status = ?"
                params.append(status)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            
            work_items = []
            for row in rows:
                work_item = dict(row)
                
                # Parse JSON fields
                for field in ['context', 'result']:
                    if work_item[field]:
                        try:
                            work_item[field] = json.loads(work_item[field])
                        except json.JSONDecodeError:
                            work_item[field] = {}
                    else:
                        work_item[field] = {}
                
                work_items.append(work_item)
            
            return work_items
    
    async def get_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}
            
            # Count by status
            cursor = await db.execute("""
                SELECT status, COUNT(*) as count 
                FROM work_items 
                GROUP BY status
            """)
            
            rows = await cursor.fetchall()
            for row in rows:
                stats[row[0]] = row[1]
            
            # Set defaults for missing statuses
            for status in ['pending', 'active', 'completed', 'failed']:
                stats.setdefault(status, 0)
            
            # Total items
            stats['total'] = sum(stats.values())
            
            # Recent activity (last 24 hours)
            cursor = await db.execute("""
                SELECT COUNT(*) FROM work_items 
                WHERE created_at > datetime('now', '-1 day')
            """)
            stats['recent_24h'] = (await cursor.fetchone())[0]
            
            return stats
    
    async def cleanup_old_items(self, days_old: int = 30):
        """Clean up old completed/failed items"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM work_items 
                WHERE status IN ('completed', 'failed') 
                AND created_at < datetime('now', '-{} days')
            """.format(days_old))
            
            deleted_count = cursor.rowcount
            await db.commit()
            
            if deleted_count > 0:
                logger.info(f"🗑️ Cleaned up {deleted_count} old work items")
            
            return deleted_count
    
    async def get_work_by_id(self, work_id: str) -> Optional[Dict[str, Any]]:
        """Get specific work item by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, type, title, description, priority, status, source, 
                       context, created_at, updated_at, attempts, last_attempt_at, result
                FROM work_items 
                WHERE id = ?
            """, (work_id,)) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'type': row[1], 
                        'title': row[2],
                        'description': row[3],
                        'priority': row[4],
                        'status': row[5],
                        'source': row[6],
                        'context': json.loads(row[7]) if row[7] else {},
                        'created_at': row[8],
                        'updated_at': row[9],
                        'attempts': row[10],
                        'last_attempt_at': row[11],
                        'result': json.loads(row[12]) if row[12] else None
                    }
                return None
    
    async def remove_work(self, work_id: str) -> bool:
        """Remove work item by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM work_items WHERE id = ?", (work_id,))
            await db.commit()
            return cursor.rowcount > 0
    
    async def update_work(self, work_id: str, updates: Dict[str, Any]) -> bool:
        """Update work item by ID"""
        if not updates:
            return False
            
        # Build dynamic UPDATE query
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if key == 'context':
                set_clauses.append(f"{key} = ?")
                values.append(json.dumps(value))
            else:
                set_clauses.append(f"{key} = ?") 
                values.append(value)
        
        values.append(work_id)  # For WHERE clause
        
        query = f"UPDATE work_items SET {', '.join(set_clauses)} WHERE id = ?"
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, values)
            await db.commit()
            return cursor.rowcount > 0

    async def health_check(self) -> dict:
        """Return health status of the work queue"""
        stats = await self.get_stats()
        
        return {
            "initialized": self._initialized,
            "database_path": self.db_path,
            "queue_stats": stats,
            "active_work_items": stats.get('active', 0),
            "pending_work_items": stats.get('pending', 0)
        }