"""
Comprehensive test suite for Sugar's configurable task type system.

This module tests the full lifecycle of task types including:
- Database operations via TaskTypeManager (CRUD operations, export/import)
- CLI commands (list, add, show, edit, remove)
- Integration with the main Sugar CLI (add tasks with custom types)
- Database migration and backwards compatibility

Test Classes:
    TestTaskTypeManager: Unit tests for TaskTypeManager database operations
    TestTaskTypeCLI: Integration tests for task-type CLI subcommands
    TestTaskTypeIntegration: End-to-end tests for task types in main CLI workflow
    TestTaskTypeMigration: Database migration and idempotency tests

Fixtures:
    temp_sugar_env: Creates isolated temporary Sugar environment
    task_type_manager: Provides initialized TaskTypeManager with test database

Usage:
    Run all tests: pytest tests/test_task_types.py -v
    Run specific class: pytest tests/test_task_types.py::TestTaskTypeManager -v
"""

import asyncio
import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch
from click.testing import CliRunner

from sugar.main import cli, task_type
from sugar.storage.task_type_manager import TaskTypeManager
from sugar.storage.work_queue import WorkQueue


@pytest.fixture
def temp_sugar_env():
    """
    Create an isolated temporary Sugar environment for testing.

    This fixture sets up a complete Sugar environment in a temporary directory,
    including:
    - A .sugar directory with config.yaml
    - Database path configuration (uses forward slashes for cross-platform YAML)
    - Mock Claude CLI settings (echo command for testing)
    - Dry-run mode enabled to prevent actual Claude invocations

    The fixture changes the current working directory to the temp directory
    during test execution and restores it afterward.

    Yields:
        dict: Environment paths with keys:
            - temp_dir (Path): Root temporary directory
            - sugar_dir (Path): The .sugar configuration directory
            - config_path (Path): Path to config.yaml
            - db_path (Path): Path to the SQLite database file
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        sugar_dir = temp_path / ".sugar"
        sugar_dir.mkdir()

        # Create minimal config
        config_path = sugar_dir / "config.yaml"
        # Use forward slashes for cross-platform compatibility in YAML
        db_path_str = str(sugar_dir / "sugar.db").replace("\\", "/")
        config_content = f"""
sugar:
  storage:
    database: "{db_path_str}"
  claude:
    command: "echo"  # Mock Claude CLI
    timeout: 1800
    context_file: "context.json"
  dry_run: true
  loop_interval: 300
  max_concurrent_work: 1
"""
        config_path.write_text(config_content)

        # Change to temp directory
        old_cwd = os.getcwd()
        os.chdir(temp_path)

        try:
            yield {
                "temp_dir": temp_path,
                "sugar_dir": sugar_dir,
                "config_path": config_path,
                "db_path": sugar_dir / "sugar.db",
            }
        finally:
            os.chdir(old_cwd)


@pytest.fixture
def task_type_manager(temp_sugar_env):
    """
    Initialize TaskTypeManager with a temporary test database.

    This fixture depends on temp_sugar_env and provides a fully initialized
    TaskTypeManager with default task types already populated in the database.

    Args:
        temp_sugar_env: The temporary environment fixture providing db_path

    Returns:
        TaskTypeManager: Initialized manager ready for testing CRUD operations
    """
    db_path = str(temp_sugar_env["db_path"])
    manager = TaskTypeManager(db_path)

    # Initialize the database with default types via WorkQueue
    asyncio.run(_init_database(db_path))

    return manager


async def _init_database(db_path: str) -> None:
    """
    Initialize the database with default task types.

    This helper function creates the database schema and populates the default
    task types (bug_fix, feature, test, refactor, documentation) by initializing
    a WorkQueue instance, which triggers the migration process.

    Args:
        db_path: Path to the SQLite database file

    Note:
        This is used both by the task_type_manager fixture and by CLI tests
        that need to set up their own isolated database within runner.isolated_filesystem().
    """
    work_queue = WorkQueue(db_path)
    await work_queue.initialize()
    # WorkQueue.initialize() creates task_types table and populates defaults


class TestTaskTypeManager:
    """
    Unit tests for TaskTypeManager database operations.

    Tests cover:
    - Default task type initialization (bug_fix, feature, test, refactor, documentation)
    - Adding custom task types with full configuration
    - Duplicate ID rejection
    - Updating existing task types
    - Removing custom vs default task types
    - Export/import functionality for custom types
    """

    @pytest.mark.asyncio
    async def test_get_default_task_types(self, task_type_manager):
        """
        Verify default task types are created during database initialization.

        The system should create 5 default task types, all marked with is_default=1.
        SQLite stores boolean True as integer 1.
        """
        task_types = await task_type_manager.get_all_task_types()

        # Verify expected count of default types
        assert len(task_types) == 5

        # Verify all expected default types are present
        type_ids = [t["id"] for t in task_types]
        expected_defaults = ["bug_fix", "feature", "test", "refactor", "documentation"]
        assert all(default in type_ids for default in expected_defaults)

        # Verify all are marked as default (SQLite returns 1 for boolean True)
        for task_type in task_types:
            assert task_type["is_default"] == 1

    @pytest.mark.asyncio
    async def test_add_custom_task_type(self, task_type_manager):
        """
        Test adding a custom task type with all optional fields populated.

        Verifies that custom task types:
        - Are successfully created with all fields
        - Are marked as non-default (is_default=0)
        - Have file_patterns stored correctly as a list
        """
        success = await task_type_manager.add_task_type(
            "database_migration",
            "Database Migration",
            "Schema and data migrations",
            "tech-lead",
            "migrate: {title}",
            "🗃️",
            ["migrations/*.sql", "schemas/*.py"],
        )

        assert success is True

        # Verify all fields were stored correctly
        task_type = await task_type_manager.get_task_type("database_migration")
        assert task_type is not None
        assert task_type["id"] == "database_migration"
        assert task_type["name"] == "Database Migration"
        assert task_type["description"] == "Schema and data migrations"
        assert task_type["agent"] == "tech-lead"
        assert task_type["commit_template"] == "migrate: {title}"
        assert task_type["emoji"] == "🗃️"
        assert task_type["file_patterns"] == ["migrations/*.sql", "schemas/*.py"]
        # Custom types should NOT be marked as default
        assert task_type["is_default"] == 0

    @pytest.mark.asyncio
    async def test_duplicate_task_type_rejected(self, task_type_manager):
        """
        Test that adding a task type with an existing ID fails gracefully.

        Task type IDs must be unique. Attempting to add a duplicate should
        return False without raising an exception.
        """
        # Add first instance - should succeed
        success1 = await task_type_manager.add_task_type("duplicate_test", "Test Type")
        assert success1 is True

        # Attempt to add with same ID - should fail gracefully
        success2 = await task_type_manager.add_task_type(
            "duplicate_test", "Test Type 2"
        )
        assert success2 is False

    @pytest.mark.asyncio
    async def test_update_task_type(self, task_type_manager):
        """
        Test partial update of an existing task type.

        Updates should allow modifying individual fields without
        affecting other fields.
        """
        # Create task type with minimal fields
        await task_type_manager.add_task_type("update_test", "Original Name")

        # Update specific fields only
        success = await task_type_manager.update_task_type(
            "update_test",
            name="Updated Name",
            description="Updated description",
            emoji="🔄",
        )

        assert success is True

        # Verify only the specified fields were updated
        task_type = await task_type_manager.get_task_type("update_test")
        assert task_type["name"] == "Updated Name"
        assert task_type["description"] == "Updated description"
        assert task_type["emoji"] == "🔄"

    @pytest.mark.asyncio
    async def test_update_nonexistent_task_type(self, task_type_manager):
        """
        Test that updating a non-existent task type returns False.

        The system should handle missing IDs gracefully without exceptions.
        """
        success = await task_type_manager.update_task_type("nonexistent", name="Test")
        assert success is False

    @pytest.mark.asyncio
    async def test_remove_custom_task_type(self, task_type_manager):
        """
        Test successful removal of a custom (non-default) task type.

        Custom task types should be fully deletable from the database.
        """
        # Create a removable custom task type
        await task_type_manager.add_task_type("removable", "Removable Type")

        # Verify it exists before removal
        task_type = await task_type_manager.get_task_type("removable")
        assert task_type is not None

        # Remove the custom type
        success = await task_type_manager.remove_task_type("removable")
        assert success is True

        # Verify it no longer exists in the database
        task_type = await task_type_manager.get_task_type("removable")
        assert task_type is None

    @pytest.mark.asyncio
    async def test_cannot_remove_default_task_type(self, task_type_manager):
        """
        Test that default task types are protected from deletion.

        Default types (is_default=1) should never be removable, ensuring
        the system always has a baseline set of task types available.
        """
        # Attempt to remove a default task type
        success = await task_type_manager.remove_task_type("feature")
        assert success is False

        # Verify the default type is still intact
        task_type = await task_type_manager.get_task_type("feature")
        assert task_type is not None
        assert task_type["is_default"] == 1

    @pytest.mark.asyncio
    async def test_get_task_type_ids(self, task_type_manager):
        """
        Test get_task_type_ids() returns all type IDs for CLI validation.

        This helper is used by the CLI to populate Click.Choice options.
        """
        type_ids = await task_type_manager.get_task_type_ids()

        # Should return all default type IDs
        expected_defaults = ["bug_fix", "documentation", "feature", "refactor", "test"]
        assert sorted(type_ids) == expected_defaults

        # Add a custom type and verify it's included
        await task_type_manager.add_task_type("custom_ids_test", "Custom Type")
        type_ids = await task_type_manager.get_task_type_ids()
        assert "custom_ids_test" in type_ids

    @pytest.mark.asyncio
    async def test_validate_task_type_id_exists(self, task_type_manager):
        """
        Test validate_task_type_id() returns True for existing types.
        """
        # Default types should validate
        is_valid = await task_type_manager.validate_task_type_id("feature")
        assert is_valid is True

        # Custom types should validate after creation
        await task_type_manager.add_task_type("validation_test", "Validation Test")
        is_valid = await task_type_manager.validate_task_type_id("validation_test")
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_task_type_id_not_exists(self, task_type_manager):
        """
        Test validate_task_type_id() returns False for non-existent types.
        """
        is_valid = await task_type_manager.validate_task_type_id("nonexistent_type")
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_get_agent_for_type_existing(self, task_type_manager):
        """
        Test get_agent_for_type() returns configured agent for existing type.
        """
        # Default types have general-purpose agent
        agent = await task_type_manager.get_agent_for_type("feature")
        assert agent == "general-purpose"

        # Custom type with specific agent
        await task_type_manager.add_task_type(
            "agent_test", "Agent Test", agent="tech-lead"
        )
        agent = await task_type_manager.get_agent_for_type("agent_test")
        assert agent == "tech-lead"

    @pytest.mark.asyncio
    async def test_get_agent_for_type_nonexistent(self, task_type_manager):
        """
        Test get_agent_for_type() returns fallback for non-existent type.
        """
        agent = await task_type_manager.get_agent_for_type("nonexistent")
        assert agent == "general-purpose"

    @pytest.mark.asyncio
    async def test_get_commit_template_for_type_existing(self, task_type_manager):
        """
        Test get_commit_template_for_type() returns configured template.
        """
        # Create custom type with specific template
        await task_type_manager.add_task_type(
            "template_test",
            "Template Test",
            commit_template="custom: {title}",
        )
        template = await task_type_manager.get_commit_template_for_type("template_test")
        assert template == "custom: {title}"

    @pytest.mark.asyncio
    async def test_get_commit_template_for_type_nonexistent(self, task_type_manager):
        """
        Test get_commit_template_for_type() returns fallback for non-existent type.
        """
        template = await task_type_manager.get_commit_template_for_type("nonexistent")
        assert template == "nonexistent: {title}"

    @pytest.mark.asyncio
    async def test_get_file_patterns_for_type_existing(self, task_type_manager):
        """
        Test get_file_patterns_for_type() returns configured patterns.
        """
        await task_type_manager.add_task_type(
            "patterns_test",
            "Patterns Test",
            file_patterns=["*.py", "tests/**/*.py"],
        )
        patterns = await task_type_manager.get_file_patterns_for_type("patterns_test")
        assert patterns == ["*.py", "tests/**/*.py"]

    @pytest.mark.asyncio
    async def test_get_file_patterns_for_type_nonexistent(self, task_type_manager):
        """
        Test get_file_patterns_for_type() returns empty list for non-existent type.
        """
        patterns = await task_type_manager.get_file_patterns_for_type("nonexistent")
        assert patterns == []

    @pytest.mark.asyncio
    async def test_update_task_type_no_updates(self, task_type_manager):
        """
        Test update_task_type() returns False when no fields are provided.
        """
        await task_type_manager.add_task_type("no_update_test", "No Update Test")

        # Call update with no actual update parameters
        success = await task_type_manager.update_task_type("no_update_test")
        assert success is False

    @pytest.mark.asyncio
    async def test_export_import_task_types(self, task_type_manager):
        """
        Test export/import round-trip for custom task types.

        This tests the backup/restore workflow:
        1. Export only exports custom types (not defaults)
        2. Exported data can be re-imported after removal
        3. Import count accurately reflects imported types
        """
        # Create custom task types for export
        await task_type_manager.add_task_type("custom1", "Custom Type 1", emoji="🔥")
        await task_type_manager.add_task_type("custom2", "Custom Type 2", emoji="⚡")

        # Export should only include custom types
        exported = await task_type_manager.export_task_types()

        assert len(exported) == 2
        assert any(t["id"] == "custom1" for t in exported)
        assert any(t["id"] == "custom2" for t in exported)

        # Default types should NOT be included in export
        assert not any(t["id"] == "feature" for t in exported)

        # Simulate backup restore scenario: remove then re-import
        await task_type_manager.remove_task_type("custom1")
        await task_type_manager.remove_task_type("custom2")

        # Import the exported data
        imported_count = await task_type_manager.import_task_types(exported)
        assert imported_count == 2

        # Verify types were fully restored
        custom1 = await task_type_manager.get_task_type("custom1")
        custom2 = await task_type_manager.get_task_type("custom2")
        assert custom1 is not None
        assert custom2 is not None

    @pytest.mark.asyncio
    async def test_import_task_types_with_overwrite(self, task_type_manager):
        """
        Test import_task_types() with overwrite=True updates existing types.

        When overwrite is True, existing task types should be updated
        with the new values from the import data.
        """
        # Create initial custom type
        await task_type_manager.add_task_type(
            "overwrite_test",
            "Original Name",
            emoji="🔴",
            description="Original description",
        )

        # Import data with updated values
        import_data = [
            {
                "id": "overwrite_test",
                "name": "Updated Name",
                "emoji": "🟢",
                "description": "Updated description",
            }
        ]

        # Without overwrite, should skip existing
        imported_count = await task_type_manager.import_task_types(
            import_data, overwrite=False
        )
        assert imported_count == 0

        task_type = await task_type_manager.get_task_type("overwrite_test")
        assert task_type["name"] == "Original Name"

        # With overwrite, should update
        imported_count = await task_type_manager.import_task_types(
            import_data, overwrite=True
        )
        assert imported_count == 1

        task_type = await task_type_manager.get_task_type("overwrite_test")
        assert task_type["name"] == "Updated Name"
        assert task_type["emoji"] == "🟢"
        assert task_type["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_import_task_types_skips_entries_without_id(self, task_type_manager):
        """
        Test import_task_types() skips entries that don't have an ID field.

        Invalid entries should be skipped without raising errors.
        """
        import_data = [
            {"name": "No ID Type", "description": "This has no ID"},  # Missing id
            {"id": "valid_import", "name": "Valid Import"},  # Valid
        ]

        imported_count = await task_type_manager.import_task_types(import_data)
        assert imported_count == 1

        # Only the valid entry should exist
        assert await task_type_manager.get_task_type("valid_import") is not None

    @pytest.mark.asyncio
    async def test_cannot_remove_task_type_with_active_tasks(self, task_type_manager):
        """
        Test remove_task_type() fails when there are active tasks of that type.

        Task types with pending/in_progress work items cannot be deleted.
        """
        from sugar.storage.work_queue import WorkQueue

        # Create a removable custom task type
        await task_type_manager.add_task_type("active_tasks_test", "Active Tasks Test")

        # Create a task with this type via WorkQueue
        work_queue = WorkQueue(task_type_manager.db_path)
        await work_queue.initialize()
        await work_queue.add_work(
            {
                "type": "active_tasks_test",
                "title": "Test task",
                "description": "A test task",
                "priority": 3,
            }
        )

        # Try to remove - should fail due to active task
        success = await task_type_manager.remove_task_type("active_tasks_test")
        assert success is False

        # Verify task type still exists
        task_type = await task_type_manager.get_task_type("active_tasks_test")
        assert task_type is not None


class TestTaskTypeCLI:
    """
    Integration tests for the 'task-type' CLI subcommand group.

    These tests use Click's CliRunner with isolated_filesystem() to create
    completely independent test environments. Each test sets up its own
    .sugar directory and database to avoid interference.

    Note: temp_sugar_env fixture is accepted but not directly used in most
    tests since isolated_filesystem() provides better isolation.
    """

    def test_task_type_list_command(self, temp_sugar_env):
        """
        Test 'sugar task-type list' command output.

        Verifies that:
        - Command exits successfully (code 0)
        - Default types are shown with '(default)' suffix
        - Emojis are displayed correctly
        """
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create config with correct local path
            os.makedirs(".sugar", exist_ok=True)
            config_content = """
sugar:
  storage:
    database: ".sugar/sugar.db"
  claude:
    command: "echo"  # Mock Claude CLI
    timeout: 1800
    context_file: "context.json"
  dry_run: true
  loop_interval: 300
  max_concurrent_work: 1
"""
            with open(".sugar/config.yaml", "w") as f:
                f.write(config_content)

            # Initialize database using the same path as in the config
            asyncio.run(_init_database(".sugar/sugar.db"))

            # Test list command with proper context
            result = runner.invoke(
                cli, ["--config", ".sugar/config.yaml", "task-type", "list"]
            )
            if result.exit_code != 0:
                print(f"Command failed with exit code {result.exit_code}")
                print(f"Output: {result.output}")
                print(f"Exception: {result.exception}")
            assert result.exit_code == 0
            assert "bug_fix (default)" in result.output
            assert "feature (default)" in result.output
            assert "🐛" in result.output  # Check emoji display

    def test_task_type_add_command(self, temp_sugar_env):
        """
        Test 'sugar task-type add' command with various options.

        Verifies that:
        - Custom task types can be created via CLI
        - All optional fields (name, description, agent, emoji) are accepted
        - Success message includes the emoji and ID
        - New type appears in subsequent list commands
        """
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Setup
            os.makedirs(".sugar", exist_ok=True)
            config_content = """
sugar:
  storage:
    database: ".sugar/sugar.db"
  claude:
    command: "echo"  # Mock Claude CLI
    timeout: 1800
    context_file: "context.json"
  dry_run: true
  loop_interval: 300
  max_concurrent_work: 1
"""
            with open(".sugar/config.yaml", "w") as f:
                f.write(config_content)

            asyncio.run(_init_database(".sugar/sugar.db"))

            # Add custom task type
            result = runner.invoke(
                cli,
                [
                    "--config",
                    ".sugar/config.yaml",
                    "task-type",
                    "add",
                    "security_audit",
                    "--name",
                    "Security Audit",
                    "--description",
                    "Security vulnerability scanning",
                    "--agent",
                    "tech-lead",
                    "--emoji",
                    "🔒",
                ],
            )

            assert result.exit_code == 0
            assert "✅ Added task type: 🔒 security_audit" in result.output

            # Verify it appears in list
            result = runner.invoke(
                cli, ["--config", ".sugar/config.yaml", "task-type", "list"]
            )
            assert result.exit_code == 0
            assert "security_audit" in result.output
            assert "Security Audit" in result.output

    def test_task_type_show_command(self, temp_sugar_env):
        """
        Test 'sugar task-type show <id>' command for detailed task type info.

        Verifies that:
        - Detailed view includes emoji, name, ID, and agent
        - Default types are labeled as '(default)'
        """
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Setup
            os.makedirs(".sugar", exist_ok=True)
            config_content = """
sugar:
  storage:
    database: ".sugar/sugar.db"
  claude:
    command: "echo"  # Mock Claude CLI
    timeout: 1800
    context_file: "context.json"
  dry_run: true
  loop_interval: 300
  max_concurrent_work: 1
"""
            with open(".sugar/config.yaml", "w") as f:
                f.write(config_content)

            asyncio.run(_init_database(".sugar/sugar.db"))

            # Show default task type
            result = runner.invoke(
                cli, ["--config", ".sugar/config.yaml", "task-type", "show", "feature"]
            )
            assert result.exit_code == 0
            assert "✨ Feature (default)" in result.output
            assert "ID: feature" in result.output
            assert "Agent: general-purpose" in result.output

    def test_task_type_edit_command(self, temp_sugar_env):
        """
        Test 'sugar task-type edit <id>' command for modifying existing types.

        Verifies that:
        - Existing custom task types can be modified
        - Partial updates (only some fields) are supported
        - Changes are persisted and visible in show command
        """
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Setup
            os.makedirs(".sugar", exist_ok=True)
            config_content = """
sugar:
  storage:
    database: ".sugar/sugar.db"
  claude:
    command: "echo"  # Mock Claude CLI
    timeout: 1800
    context_file: "context.json"
  dry_run: true
  loop_interval: 300
  max_concurrent_work: 1
"""
            with open(".sugar/config.yaml", "w") as f:
                f.write(config_content)

            asyncio.run(_init_database(".sugar/sugar.db"))

            # Add a custom task type first
            runner.invoke(
                cli,
                [
                    "--config",
                    ".sugar/config.yaml",
                    "task-type",
                    "add",
                    "editable",
                    "--name",
                    "Editable Type",
                ],
            )

            # Edit it
            result = runner.invoke(
                cli,
                [
                    "--config",
                    ".sugar/config.yaml",
                    "task-type",
                    "edit",
                    "editable",
                    "--name",
                    "Updated Name",
                    "--emoji",
                    "🔧",
                ],
            )

            assert result.exit_code == 0
            assert "✅ Updated task type: editable" in result.output

            # Verify changes
            result = runner.invoke(
                cli, ["--config", ".sugar/config.yaml", "task-type", "show", "editable"]
            )
            assert "🔧 Updated Name" in result.output

    def test_task_type_remove_command(self, temp_sugar_env):
        """
        Test 'sugar task-type remove <id>' command with --force flag.

        Verifies that:
        - Custom task types can be removed with --force
        - Success message confirms removal
        - Removed types return 'not found' on subsequent show
        """
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Setup
            os.makedirs(".sugar", exist_ok=True)
            config_content = """
sugar:
  storage:
    database: ".sugar/sugar.db"
  claude:
    command: "echo"  # Mock Claude CLI
    timeout: 1800
    context_file: "context.json"
  dry_run: true
  loop_interval: 300
  max_concurrent_work: 1
"""
            with open(".sugar/config.yaml", "w") as f:
                f.write(config_content)

            asyncio.run(_init_database(".sugar/sugar.db"))

            # Add a custom task type first
            runner.invoke(
                cli,
                [
                    "--config",
                    ".sugar/config.yaml",
                    "task-type",
                    "add",
                    "removable",
                    "--name",
                    "Removable Type",
                ],
            )

            # Remove it with force flag
            result = runner.invoke(
                cli,
                [
                    "--config",
                    ".sugar/config.yaml",
                    "task-type",
                    "remove",
                    "removable",
                    "--force",
                ],
            )

            assert result.exit_code == 0
            assert "✅ Removed task type: removable" in result.output

            # Verify it's gone
            result = runner.invoke(
                cli,
                ["--config", ".sugar/config.yaml", "task-type", "show", "removable"],
            )
            assert result.exit_code == 1
            assert "not found" in result.output

    def test_cannot_remove_default_via_cli(self, temp_sugar_env):
        """
        Test that 'sugar task-type remove' rejects removal of default types.

        Default task types must be protected at both the database layer
        (TaskTypeManager) and the CLI layer. This test verifies the CLI
        returns a non-zero exit code with appropriate error message.
        """
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Setup
            os.makedirs(".sugar", exist_ok=True)
            config_content = """
sugar:
  storage:
    database: ".sugar/sugar.db"
  claude:
    command: "echo"  # Mock Claude CLI
    timeout: 1800
    context_file: "context.json"
  dry_run: true
  loop_interval: 300
  max_concurrent_work: 1
"""
            with open(".sugar/config.yaml", "w") as f:
                f.write(config_content)

            asyncio.run(_init_database(".sugar/sugar.db"))

            # Try to remove default task type
            result = runner.invoke(
                cli,
                [
                    "--config",
                    ".sugar/config.yaml",
                    "task-type",
                    "remove",
                    "feature",
                    "--force",
                ],
            )

            assert result.exit_code == 1
            assert "Cannot remove default task type" in result.output


class TestTaskTypeIntegration:
    """
    End-to-end tests for task types in the main Sugar CLI workflow.

    These tests verify that custom task types integrate correctly with
    the primary 'sugar add' and 'sugar list' commands, including:
    - Using custom types in task creation
    - Error handling for invalid types
    - Filtering tasks by type
    """

    def test_add_task_with_custom_type(self, temp_sugar_env):
        """
        Test creating a task with a custom task type via 'sugar add --type'.

        This tests the full workflow:
        1. Create a custom task type
        2. Use it when adding a new task
        3. Verify the task appears in list with the correct type
        """
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Setup
            os.makedirs(".sugar", exist_ok=True)
            config_content = """
sugar:
  storage:
    database: ".sugar/sugar.db"
  claude:
    command: "echo"  # Mock Claude CLI
    timeout: 1800
    context_file: "context.json"
  dry_run: true
  loop_interval: 300
  max_concurrent_work: 1
"""
            with open(".sugar/config.yaml", "w") as f:
                f.write(config_content)

            asyncio.run(_init_database(".sugar/sugar.db"))

            # Add custom task type
            type_result = runner.invoke(
                cli,
                [
                    "--config",
                    ".sugar/config.yaml",
                    "task-type",
                    "add",
                    "integration_test",
                    "--name",
                    "Integration Test",
                    "--agent",
                    "general-purpose",
                ],
            )
            assert (
                type_result.exit_code == 0
            ), f"Task type creation failed: {type_result.output}"

            # Use it in sugar add command
            result = runner.invoke(
                cli,
                [
                    "--config",
                    ".sugar/config.yaml",
                    "add",
                    "Test integration workflow",
                    "--type",
                    "integration_test",
                    "--priority",
                    "4",
                ],
            )

            assert result.exit_code == 0, f"Task creation failed: {result.output}"
            assert "✅ Added integration_test task" in result.output

            # Verify task was created with correct type
            result = runner.invoke(cli, ["--config", ".sugar/config.yaml", "list"])
            assert result.exit_code == 0
            assert "[integration_test]" in result.output
            assert "Test integration workflow" in result.output

    def test_invalid_task_type_rejected(self, temp_sugar_env):
        """
        Test that 'sugar add --type <invalid>' shows helpful error message.

        Click's Choice validation should:
        - Return exit code 2 (Click's invalid input code)
        - Show 'Invalid choice: <type>'
        - Include 'choose from' with valid options
        """
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Setup
            os.makedirs(".sugar", exist_ok=True)
            config_content = """
sugar:
  storage:
    database: ".sugar/sugar.db"
  claude:
    command: "echo"  # Mock Claude CLI
    timeout: 1800
    context_file: "context.json"
  dry_run: true
  loop_interval: 300
  max_concurrent_work: 1
"""
            with open(".sugar/config.yaml", "w") as f:
                f.write(config_content)

            asyncio.run(_init_database(".sugar/sugar.db"))

            # Try to use invalid task type
            result = runner.invoke(
                cli,
                [
                    "--config",
                    ".sugar/config.yaml",
                    "add",
                    "Test task",
                    "--type",
                    "nonexistent_type",
                ],
            )

            assert result.exit_code == 2
            assert "Invalid choice: nonexistent_type" in result.output
            assert "choose from" in result.output

    def test_list_with_custom_type_filter(self, temp_sugar_env):
        """
        Test 'sugar list --type <type>' filters tasks correctly.

        Creates tasks with different types and verifies that filtering
        by a specific type:
        - Shows only tasks matching the filter type
        - Excludes tasks with other types
        """
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Setup
            os.makedirs(".sugar", exist_ok=True)
            config_content = """
sugar:
  storage:
    database: ".sugar/sugar.db"
  claude:
    command: "echo"  # Mock Claude CLI
    timeout: 1800
    context_file: "context.json"
  dry_run: true
  loop_interval: 300
  max_concurrent_work: 1
"""
            with open(".sugar/config.yaml", "w") as f:
                f.write(config_content)

            asyncio.run(_init_database(".sugar/sugar.db"))

            # Add custom task type and task
            runner.invoke(
                cli,
                [
                    "--config",
                    ".sugar/config.yaml",
                    "task-type",
                    "add",
                    "filter_test",
                    "--name",
                    "Filter Test",
                ],
            )
            runner.invoke(
                cli,
                [
                    "--config",
                    ".sugar/config.yaml",
                    "add",
                    "Filterable task",
                    "--type",
                    "filter_test",
                ],
            )
            runner.invoke(
                cli,
                [
                    "--config",
                    ".sugar/config.yaml",
                    "add",
                    "Regular task",
                    "--type",
                    "feature",
                ],
            )

            # Filter by custom type
            result = runner.invoke(
                cli, ["--config", ".sugar/config.yaml", "list", "--type", "filter_test"]
            )

            assert result.exit_code == 0
            assert "[filter_test]" in result.output
            assert "Filterable task" in result.output
            assert "Regular task" not in result.output


class TestTaskTypeMigration:
    """
    Tests for database migration and backwards compatibility.

    These tests verify that:
    - The task_types table is created during WorkQueue initialization
    - Default types are populated automatically
    - Multiple initializations are safe (idempotent)
    """

    def test_migration_creates_task_types_table(self, temp_sugar_env):
        """
        Test that WorkQueue.initialize() creates task_types table with defaults.

        This verifies the migration process:
        1. WorkQueue initialization triggers schema creation
        2. task_types table is created
        3. Default types are populated with expected IDs
        """
        db_path = str(temp_sugar_env["db_path"])

        # WorkQueue.initialize() triggers all database migrations
        work_queue = WorkQueue(db_path)
        asyncio.run(work_queue.initialize())

        # Verify task_types table was created with default data
        manager = TaskTypeManager(db_path)
        task_types = asyncio.run(manager.get_all_task_types())

        # Expect exactly 5 default types
        assert len(task_types) == 5

        # Verify the exact set of default type IDs
        type_ids = {t["id"] for t in task_types}
        expected = {"bug_fix", "feature", "test", "refactor", "documentation"}
        assert type_ids == expected

    def test_migration_is_idempotent(self, temp_sugar_env):
        """
        Test that multiple WorkQueue.initialize() calls are safe.

        This is critical for application restarts and reconnections.
        Running initialize() multiple times should:
        - Not create duplicate task types
        - Not raise errors
        - Leave the database in a consistent state
        """
        db_path = str(temp_sugar_env["db_path"])

        # Simulate application restart by initializing multiple times
        work_queue1 = WorkQueue(db_path)
        asyncio.run(work_queue1.initialize())

        work_queue2 = WorkQueue(db_path)
        asyncio.run(work_queue2.initialize())

        # Verify no duplicate types were created
        manager = TaskTypeManager(db_path)
        task_types = asyncio.run(manager.get_all_task_types())
        assert len(task_types) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
