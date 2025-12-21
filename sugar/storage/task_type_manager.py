"""Task Type Management System

Provides database operations for managing configurable task types.
Integrates with the existing WorkQueue storage system.
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

import aiosqlite

logger = logging.getLogger(__name__)


class TaskTypeManager:
    """Manages task types in the database"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialized = False

    async def initialize(self):
        """Initialize the task_types table if it doesn't exist"""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            # Check if task_types table exists
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='task_types'"
            )
            table_exists = await cursor.fetchone()

            if not table_exists:
                # Create task_types table
                await db.execute(
                    """
                    CREATE TABLE task_types (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        agent TEXT DEFAULT 'general-purpose',
                        commit_template TEXT,
                        emoji TEXT,
                        file_patterns TEXT DEFAULT '[]',
                        is_default INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                # Populate with default types
                default_types = self._get_default_task_types()
                for task_type in default_types:
                    await db.execute(
                        """
                        INSERT INTO task_types
                        (id, name, description, agent, commit_template, emoji, file_patterns, is_default)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            task_type["id"],
                            task_type["name"],
                            task_type["description"],
                            task_type["agent"],
                            task_type["commit_template"],
                            task_type["emoji"],
                            json.dumps(task_type.get("file_patterns", [])),
                            1,
                        ),
                    )

                await db.commit()
                logger.info("Created task_types table and populated with default types")

        self._initialized = True

    def _get_default_task_types(self) -> List[Dict]:
        """Get the default task types"""
        return [
            {
                "id": "feature",
                "name": "Feature",
                "description": "New feature implementation",
                "agent": "general-purpose",
                "commit_template": "feat: {title}",
                "emoji": "✨",
                "file_patterns": [],
            },
            {
                "id": "bug_fix",
                "name": "Bug Fix",
                "description": "Bug fix or error correction",
                "agent": "general-purpose",
                "commit_template": "fix: {title}",
                "emoji": "🐛",
                "file_patterns": [],
            },
            {
                "id": "refactor",
                "name": "Refactor",
                "description": "Code refactoring",
                "agent": "general-purpose",
                "commit_template": "refactor: {title}",
                "emoji": "♻️",
                "file_patterns": [],
            },
            {
                "id": "docs",
                "name": "Documentation",
                "description": "Documentation updates",
                "agent": "general-purpose",
                "commit_template": "docs: {title}",
                "emoji": "📝",
                "file_patterns": ["*.md", "docs/**"],
            },
            {
                "id": "test",
                "name": "Test",
                "description": "Test creation or updates",
                "agent": "general-purpose",
                "commit_template": "test: {title}",
                "emoji": "🧪",
                "file_patterns": ["test_*.py", "*_test.py", "tests/**"],
            },
            {
                "id": "chore",
                "name": "Chore",
                "description": "Maintenance and chores",
                "agent": "general-purpose",
                "commit_template": "chore: {title}",
                "emoji": "🔧",
                "file_patterns": [],
            },
            {
                "id": "style",
                "name": "Style",
                "description": "Code style and formatting",
                "agent": "general-purpose",
                "commit_template": "style: {title}",
                "emoji": "💄",
                "file_patterns": [],
            },
            {
                "id": "perf",
                "name": "Performance",
                "description": "Performance improvements",
                "agent": "general-purpose",
                "commit_template": "perf: {title}",
                "emoji": "⚡",
                "file_patterns": [],
            },
            {
                "id": "ci",
                "name": "CI/CD",
                "description": "CI/CD configuration",
                "agent": "general-purpose",
                "commit_template": "ci: {title}",
                "emoji": "👷",
                "file_patterns": [".github/**", "Dockerfile", "docker-compose*.yml"],
            },
            {
                "id": "security",
                "name": "Security",
                "description": "Security fixes and improvements",
                "agent": "general-purpose",
                "commit_template": "security: {title}",
                "emoji": "🔒",
                "file_patterns": [],
            },
        ]

    async def get_all_task_types(self) -> List[Dict]:
        """Get all task types from the database"""
        try:
            return await self._get_all_task_types_internal()
        except aiosqlite.OperationalError as e:
            if "no such table: task_types" in str(e):
                await self.initialize()
                return await self._get_all_task_types_internal()
            raise

    async def _get_all_task_types_internal(self) -> List[Dict]:
        """Internal method to get all task types"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM task_types ORDER BY is_default DESC, name ASC"
            )
            rows = await cursor.fetchall()

            result = []
            for row in rows:
                task_type = dict(row)
                # Parse JSON file_patterns
                if task_type.get("file_patterns"):
                    try:
                        task_type["file_patterns"] = json.loads(
                            task_type["file_patterns"]
                        )
                    except json.JSONDecodeError:
                        task_type["file_patterns"] = []
                else:
                    task_type["file_patterns"] = []
                result.append(task_type)

            return result

    async def get_task_type(self, type_id: str) -> Optional[Dict]:
        """Get a specific task type by ID"""
        try:
            return await self._get_task_type_internal(type_id)
        except aiosqlite.OperationalError as e:
            if "no such table: task_types" in str(e):
                await self.initialize()
                return await self._get_task_type_internal(type_id)
            raise

    async def _get_task_type_internal(self, type_id: str) -> Optional[Dict]:
        """Internal method to get a specific task type"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM task_types WHERE id = ?", (type_id,)
            )
            row = await cursor.fetchone()

            if row:
                task_type = dict(row)
                # Parse JSON file_patterns
                if task_type.get("file_patterns"):
                    try:
                        task_type["file_patterns"] = json.loads(
                            task_type["file_patterns"]
                        )
                    except json.JSONDecodeError:
                        task_type["file_patterns"] = []
                else:
                    task_type["file_patterns"] = []
                return task_type

            return None

    async def get_task_type_ids(self) -> List[str]:
        """Get all task type IDs for CLI validation"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT id FROM task_types ORDER BY name ASC")
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
        except aiosqlite.OperationalError as e:
            if "no such table: task_types" in str(e):
                await self.initialize()
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(
                        "SELECT id FROM task_types ORDER BY name ASC"
                    )
                    rows = await cursor.fetchall()
                    return [row[0] for row in rows]
            raise

    async def add_task_type(
        self,
        type_id: str,
        name: str,
        description: str = None,
        agent: str = "general-purpose",
        commit_template: str = None,
        emoji: str = None,
        file_patterns: List[str] = None,
    ) -> bool:
        """Add a new task type"""
        await self.initialize()
        if not commit_template:
            commit_template = f"{type_id}: {{title}}"

        if file_patterns is None:
            file_patterns = []

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO task_types
                    (id, name, description, agent, commit_template, emoji, file_patterns, is_default)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                    (
                        type_id,
                        name,
                        description,
                        agent,
                        commit_template,
                        emoji,
                        json.dumps(file_patterns),
                    ),
                )
                await db.commit()
                logger.info(f"Added new task type: {type_id}")
                return True
        except aiosqlite.IntegrityError:
            logger.error(f"Task type '{type_id}' already exists")
            return False
        except Exception as e:
            logger.error(f"Error adding task type '{type_id}': {e}")
            return False

    async def update_task_type(
        self,
        type_id: str,
        name: str = None,
        description: str = None,
        agent: str = None,
        commit_template: str = None,
        emoji: str = None,
        file_patterns: List[str] = None,
    ) -> bool:
        """Update an existing task type"""
        await self.initialize()
        # First check if task type exists
        existing = await self.get_task_type(type_id)
        if not existing:
            logger.error(f"Task type '{type_id}' not found")
            return False

        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if agent is not None:
            updates.append("agent = ?")
            params.append(agent)
        if commit_template is not None:
            updates.append("commit_template = ?")
            params.append(commit_template)
        if emoji is not None:
            updates.append("emoji = ?")
            params.append(emoji)
        if file_patterns is not None:
            updates.append("file_patterns = ?")
            params.append(json.dumps(file_patterns))

        if not updates:
            logger.warning(f"No updates provided for task type '{type_id}'")
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(type_id)

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    f"UPDATE task_types SET {', '.join(updates)} WHERE id = ?",
                    params,
                )
                await db.commit()
                logger.info(f"Updated task type: {type_id}")
                return True
        except Exception as e:
            logger.error(f"Error updating task type '{type_id}': {e}")
            return False

    async def remove_task_type(self, type_id: str) -> bool:
        """Remove a task type (if not default and no active tasks)"""
        await self.initialize()
        # Check if task type exists and is not default
        existing = await self.get_task_type(type_id)
        if not existing:
            logger.error(f"Task type '{type_id}' not found")
            return False

        if existing["is_default"]:
            logger.error(f"Cannot delete default task type '{type_id}'")
            return False

        # Check if there are active tasks with this type
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM work_items WHERE type = ? AND status NOT IN ('completed', 'failed')",
                (type_id,),
            )
            active_count = (await cursor.fetchone())[0]

            if active_count > 0:
                logger.error(
                    f"Cannot delete task type '{type_id}': {active_count} active tasks exist"
                )
                return False

            try:
                await db.execute("DELETE FROM task_types WHERE id = ?", (type_id,))
                await db.commit()
                logger.info(f"Removed task type: {type_id}")
                return True
            except Exception as e:
                logger.error(f"Error removing task type '{type_id}': {e}")
                return False

    async def export_task_types(self) -> List[Dict]:
        """Export all non-default task types for version control"""
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM task_types WHERE is_default = 0 ORDER BY name ASC"
            )
            rows = await cursor.fetchall()

            result = []
            for row in rows:
                task_type = dict(row)
                # Remove database-specific fields
                task_type.pop("created_at", None)
                task_type.pop("updated_at", None)
                task_type.pop("is_default", None)

                # Parse JSON file_patterns
                if task_type.get("file_patterns"):
                    try:
                        task_type["file_patterns"] = json.loads(
                            task_type["file_patterns"]
                        )
                    except json.JSONDecodeError:
                        task_type["file_patterns"] = []
                else:
                    task_type["file_patterns"] = []

                result.append(task_type)

            return result

    async def import_task_types(
        self, task_types: List[Dict], overwrite: bool = False
    ) -> int:
        """Import task types from external source"""
        await self.initialize()
        imported_count = 0

        for task_type in task_types:
            type_id = task_type.get("id")
            if not type_id:
                logger.warning("Skipping task type without ID")
                continue

            # Check if already exists
            existing = await self.get_task_type(type_id)
            if existing and not overwrite:
                logger.warning(f"Task type '{type_id}' already exists, skipping")
                continue

            if existing and overwrite:
                # Update existing
                success = await self.update_task_type(
                    type_id,
                    name=task_type.get("name"),
                    description=task_type.get("description"),
                    agent=task_type.get("agent"),
                    commit_template=task_type.get("commit_template"),
                    emoji=task_type.get("emoji"),
                    file_patterns=task_type.get("file_patterns", []),
                )
            else:
                # Add new
                success = await self.add_task_type(
                    type_id,
                    name=task_type.get("name", type_id.title()),
                    description=task_type.get("description"),
                    agent=task_type.get("agent", "general-purpose"),
                    commit_template=task_type.get("commit_template"),
                    emoji=task_type.get("emoji"),
                    file_patterns=task_type.get("file_patterns", []),
                )

            if success:
                imported_count += 1

        return imported_count

    async def validate_task_type_id(self, type_id: str) -> bool:
        """Validate that a task type ID exists"""
        await self.initialize()
        existing = await self.get_task_type(type_id)
        return existing is not None

    async def get_agent_for_type(self, type_id: str) -> str:
        """Get the agent configured for a task type"""
        await self.initialize()
        task_type = await self.get_task_type(type_id)
        return (
            task_type.get("agent", "general-purpose")
            if task_type
            else "general-purpose"
        )

    async def get_commit_template_for_type(self, type_id: str) -> str:
        """Get the commit template for a task type"""
        await self.initialize()
        task_type = await self.get_task_type(type_id)
        return (
            task_type.get("commit_template", f"{type_id}: {{title}}")
            if task_type
            else f"{type_id}: {{title}}"
        )

    async def get_file_patterns_for_type(self, type_id: str) -> List[str]:
        """Get the file patterns for a task type"""
        await self.initialize()
        task_type = await self.get_task_type(type_id)
        return task_type.get("file_patterns", []) if task_type else []
