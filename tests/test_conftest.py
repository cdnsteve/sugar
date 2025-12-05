"""
Tests for conftest.py fixtures.

This module validates the pytest fixtures defined in conftest.py, ensuring
they provide reliable, well-structured test infrastructure for the Sugar
autonomous development system.

Fixtures Tested:
    - temp_dir: Temporary directory creation and cleanup
    - mock_project_dir: Mock project structure with typical layout
    - sugar_config: In-memory Sugar configuration dictionary
    - sugar_config_file: YAML configuration file on disk
    - cli_runner: Click CLI test runner for command testing
    - mock_claude_cli: Mocked subprocess.run for Claude CLI calls
    - sample_error_log: Sample JSON error log file
    - sample_tasks: Sample task data structures
    - mock_work_queue: Async work queue with SQLite backend
    - event_loop: Session-scoped asyncio event loop

Test Categories:
    - Individual fixture tests: Verify each fixture works correctly in isolation
    - Integration tests: Verify fixtures work together as expected

Note:
    These tests serve as both validation and documentation for fixture behavior.
    When modifying fixtures in conftest.py, update corresponding tests here.
"""

import pytest
import json
import yaml
from pathlib import Path


class TestTempDirFixture:
    """Tests for the temp_dir fixture.

    The temp_dir fixture provides an isolated temporary directory for each test,
    automatically cleaned up after the test completes. This prevents test
    pollution and ensures reproducible test environments.
    """

    def test_temp_dir_exists(self, temp_dir):
        """Verify temp_dir creates an existing, accessible directory."""
        assert temp_dir.exists()
        assert temp_dir.is_dir()

    def test_temp_dir_is_writable(self, temp_dir):
        """Verify temp_dir allows file creation and modification."""
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test content")
        assert test_file.exists()
        assert test_file.read_text() == "test content"

    def test_temp_dir_is_path_object(self, temp_dir):
        """Verify temp_dir returns a pathlib.Path for consistent path handling."""
        assert isinstance(temp_dir, Path)

    def test_temp_dir_cleanup(self):
        """Document that temp_dir cleanup occurs via fixture teardown.

        The fixture uses a yield pattern with shutil.rmtree to automatically
        clean up the temporary directory after each test completes. This test
        exists to document this behavior; actual cleanup verification would
        require cross-test state tracking.
        """
        pass  # Cleanup is verified by fixture design


class TestMockProjectDirFixture:
    """Tests for the mock_project_dir fixture.

    The mock_project_dir fixture creates a realistic project directory structure
    inside temp_dir, simulating a typical Python project layout that Sugar
    would work with. Includes src/, tests/, logs/errors/, and sample files.
    """

    def test_mock_project_dir_exists(self, mock_project_dir):
        """Verify mock_project_dir creates the base project directory."""
        assert mock_project_dir.exists()
        assert mock_project_dir.is_dir()
        assert mock_project_dir.name == "test_project"

    def test_mock_project_dir_structure(self, mock_project_dir):
        """Verify mock_project_dir creates the expected directory hierarchy.

        Expected structure:
            test_project/
            ├── src/
            ├── tests/
            └── logs/
                └── errors/
        """
        assert (mock_project_dir / "src").exists()
        assert (mock_project_dir / "tests").exists()
        assert (mock_project_dir / "logs" / "errors").exists()

    def test_mock_project_dir_files(self, mock_project_dir):
        """Verify mock_project_dir creates sample files for testing.

        Created files:
            - src/main.py: Sample Python file with minimal content
            - README.md: Standard project documentation file
        """
        main_py = mock_project_dir / "src" / "main.py"
        assert main_py.exists()
        assert "print('hello')" in main_py.read_text()

        readme = mock_project_dir / "README.md"
        assert readme.exists()
        assert "# Test Project" in readme.read_text()

    def test_mock_project_dir_is_child_of_temp_dir(self, temp_dir, mock_project_dir):
        """Verify mock_project_dir is nested inside temp_dir for isolation."""
        assert mock_project_dir.parent == temp_dir


class TestSugarConfigFixture:
    """Tests for the sugar_config fixture.

    The sugar_config fixture provides a complete, in-memory Sugar configuration
    dictionary suitable for testing configuration parsing, validation, and
    component initialization without requiring file I/O.
    """

    def test_sugar_config_has_required_keys(self, sugar_config):
        """Verify sugar_config contains all required top-level configuration keys.

        Required keys: loop_interval, max_concurrent_work, dry_run, claude,
        discovery, storage, safety, logging
        """
        assert "sugar" in sugar_config
        config = sugar_config["sugar"]

        # Check top-level keys
        assert "loop_interval" in config
        assert "max_concurrent_work" in config
        assert "dry_run" in config
        assert "claude" in config
        assert "discovery" in config
        assert "storage" in config
        assert "safety" in config
        assert "logging" in config

    def test_sugar_config_claude_section(self, sugar_config):
        """Verify the claude section contains Claude CLI integration settings."""
        claude_config = sugar_config["sugar"]["claude"]
        assert "command" in claude_config
        assert "timeout" in claude_config
        assert "context_file" in claude_config

    def test_sugar_config_discovery_section(self, sugar_config):
        """Verify the discovery section contains all work source configurations.

        Work sources: error_logs, github, code_quality, test_coverage
        """
        discovery = sugar_config["sugar"]["discovery"]
        assert "error_logs" in discovery
        assert "github" in discovery
        assert "code_quality" in discovery
        assert "test_coverage" in discovery

    def test_sugar_config_error_logs_settings(self, sugar_config):
        """Verify error_logs discovery has required settings for log scanning."""
        error_logs = sugar_config["sugar"]["discovery"]["error_logs"]
        assert error_logs["enabled"] is True
        assert "paths" in error_logs
        assert "patterns" in error_logs
        assert "max_age_hours" in error_logs

    def test_sugar_config_safety_settings(self, sugar_config):
        """Verify safety configuration contains protection settings.

        Safety settings prevent dangerous operations and limit retries.
        """
        safety = sugar_config["sugar"]["safety"]
        assert "max_retries" in safety
        assert safety["max_retries"] == 3
        assert "excluded_paths" in safety


class TestSugarConfigFileFixture:
    """Tests for the sugar_config_file fixture.

    The sugar_config_file fixture creates an actual YAML configuration file
    on disk within the mock project's .sugar directory. This enables testing
    of file-based configuration loading and parsing.
    """

    def test_sugar_config_file_exists(self, sugar_config_file):
        """Verify sugar_config_file creates a real file on disk."""
        assert sugar_config_file.exists()
        assert sugar_config_file.is_file()
        assert sugar_config_file.name == "config.yaml"

    def test_sugar_config_file_is_valid_yaml(self, sugar_config_file):
        """Verify sugar_config_file contains parseable YAML content."""
        with open(sugar_config_file) as f:
            config = yaml.safe_load(f)
        assert config is not None
        assert "sugar" in config

    def test_sugar_config_file_in_sugar_dir(self, sugar_config_file, mock_project_dir):
        """Verify sugar_config_file follows expected path: project/.sugar/config.yaml."""
        assert sugar_config_file.parent.name == ".sugar"
        assert sugar_config_file.parent.parent == mock_project_dir


class TestCliRunnerFixture:
    """Tests for the cli_runner fixture.

    The cli_runner fixture provides a Click CliRunner instance for testing
    Sugar's CLI commands. It enables invoking commands programmatically and
    inspecting their output and exit codes.
    """

    def test_cli_runner_type(self, cli_runner):
        """Verify cli_runner is a properly initialized Click CliRunner."""
        from click.testing import CliRunner

        assert isinstance(cli_runner, CliRunner)

    def test_cli_runner_isolated_filesystem(self, cli_runner):
        """Verify cli_runner supports isolated filesystem context for clean tests."""
        with cli_runner.isolated_filesystem():
            test_file = Path("test.txt")
            test_file.write_text("test content")
            assert test_file.exists()


class TestMockClaudeCliFixture:
    """Tests for the mock_claude_cli fixture.

    The mock_claude_cli fixture patches subprocess.run to prevent actual
    Claude CLI execution during tests. Returns predictable success responses
    and enables call verification via the returned mock object.
    """

    def test_mock_claude_cli_patches_subprocess(self, mock_claude_cli):
        """Verify mock_claude_cli intercepts subprocess.run with success response.

        Mock returns:
            - returncode: 0 (success)
            - stdout: 'Task completed successfully'
            - stderr: '' (empty)
        """
        import subprocess

        result = subprocess.run(["mock", "command"])
        assert result.returncode == 0
        assert result.stdout == "Task completed successfully"
        assert result.stderr == ""

    def test_mock_claude_cli_is_called(self, mock_claude_cli):
        """Verify mock_claude_cli records calls for test assertions."""
        import subprocess

        subprocess.run(["test", "command"])
        mock_claude_cli.assert_called_once()


class TestSampleErrorLogFixture:
    """Tests for the sample_error_log fixture.

    The sample_error_log fixture creates a realistic JSON error log file
    in the mock project's logs/errors directory. This enables testing of
    the error log discovery and parsing functionality.
    """

    def test_sample_error_log_exists(self, sample_error_log):
        """Verify sample_error_log creates a file on disk."""
        assert sample_error_log.exists()
        assert sample_error_log.is_file()

    def test_sample_error_log_is_valid_json(self, sample_error_log):
        """Verify sample_error_log contains parseable JSON content."""
        with open(sample_error_log) as f:
            data = json.load(f)
        assert data is not None

    def test_sample_error_log_structure(self, sample_error_log):
        """Verify sample_error_log has all required error log fields.

        Required fields: timestamp, error, message, file, line, context
        """
        with open(sample_error_log) as f:
            data = json.load(f)

        assert "timestamp" in data
        assert "error" in data
        assert "message" in data
        assert "file" in data
        assert "line" in data
        assert "context" in data

    def test_sample_error_log_content(self, sample_error_log):
        """Verify sample_error_log contains expected sample error data.

        Sample error: AttributeError at src/main.py line 42
        """
        with open(sample_error_log) as f:
            data = json.load(f)

        assert data["error"] == "AttributeError"
        assert data["line"] == 42
        assert data["file"] == "src/main.py"

    def test_sample_error_log_location(self, sample_error_log, mock_project_dir):
        """Verify sample_error_log is at project/logs/errors/test_error.json."""
        assert sample_error_log.parent.name == "errors"
        assert sample_error_log.parent.parent.name == "logs"


class TestSampleTasksFixture:
    """Tests for the sample_tasks fixture.

    The sample_tasks fixture provides a list of sample task dictionaries
    representing different work item types and statuses. Useful for testing
    task processing, prioritization, and queue management.
    """

    def test_sample_tasks_is_list(self, sample_tasks):
        """Verify sample_tasks returns a list of task dictionaries."""
        assert isinstance(sample_tasks, list)

    def test_sample_tasks_count(self, sample_tasks):
        """Verify sample_tasks provides exactly 2 sample tasks."""
        assert len(sample_tasks) == 2

    def test_sample_tasks_structure(self, sample_tasks):
        """Verify each sample task has all required fields.

        Required fields: id, type, title, description, priority, status,
        source, context
        """
        required_keys = [
            "id",
            "type",
            "title",
            "description",
            "priority",
            "status",
            "source",
            "context",
        ]

        for task in sample_tasks:
            for key in required_keys:
                assert key in task, f"Missing key '{key}' in task"

    def test_sample_tasks_first_task(self, sample_tasks):
        """Verify first sample task is a pending high-priority bug fix."""
        task = sample_tasks[0]
        assert task["id"] == "task-1"
        assert task["type"] == "bug_fix"
        assert task["priority"] == 5
        assert task["status"] == "pending"

    def test_sample_tasks_second_task(self, sample_tasks):
        """Verify second sample task is a completed feature request."""
        task = sample_tasks[1]
        assert task["id"] == "task-2"
        assert task["type"] == "feature"
        assert task["status"] == "completed"


class TestMockWorkQueueFixture:
    """Tests for the mock_work_queue fixture.

    The mock_work_queue fixture provides an initialized async WorkQueue
    instance backed by a SQLite database in temp_dir. Enables testing of
    work item persistence, retrieval, and queue operations.

    Note:
        All tests in this class require pytest.mark.asyncio for async support.
    """

    @pytest.mark.asyncio
    async def test_mock_work_queue_initialized(self, mock_work_queue):
        """Verify mock_work_queue is pre-initialized and ready for operations."""
        # The fixture awaits initialize() before yielding
        assert mock_work_queue is not None

    @pytest.mark.asyncio
    async def test_mock_work_queue_can_add_work(self, mock_work_queue):
        """Verify mock_work_queue accepts new work items and returns task ID."""
        task_data = {
            "type": "test",
            "title": "Test task from fixture test",
            "priority": 3,
            "source": "test",
        }

        task_id = await mock_work_queue.add_work(task_data)
        assert task_id is not None

    @pytest.mark.asyncio
    async def test_mock_work_queue_can_retrieve_work(self, mock_work_queue):
        """Verify mock_work_queue persists and retrieves work items correctly."""
        task_data = {
            "type": "test",
            "title": "Retrievable task",
            "priority": 3,
            "source": "test",
        }

        task_id = await mock_work_queue.add_work(task_data)
        retrieved = await mock_work_queue.get_work_by_id(task_id)

        assert retrieved is not None
        assert retrieved["title"] == "Retrievable task"

    @pytest.mark.asyncio
    async def test_mock_work_queue_database_created(self, mock_work_queue, temp_dir):
        """Verify mock_work_queue creates a SQLite database file at temp_dir/test.db."""
        db_path = temp_dir / "test.db"
        assert db_path.exists()


class TestEventLoopFixture:
    """Tests for the event_loop fixture.

    The event_loop fixture provides a session-scoped asyncio event loop
    for running async tests. This is required by pytest-asyncio for async
    test execution.

    Note:
        The fixture is session-scoped, meaning the same loop is reused across
        all tests in a session for efficiency.
    """

    @pytest.mark.asyncio
    async def test_event_loop_works(self):
        """Verify the event loop enables basic async operations."""
        import asyncio

        # Simple async operation to confirm loop is running
        await asyncio.sleep(0.01)
        assert True

    @pytest.mark.asyncio
    async def test_event_loop_can_run_tasks(self):
        """Verify the event loop can execute coroutines and capture results."""
        import asyncio

        result = []

        async def async_task():
            result.append("completed")

        await async_task()
        assert result == ["completed"]


class TestFixtureIntegration:
    """Integration tests for fixture combinations.

    These tests verify that fixtures can be used together correctly,
    maintaining proper relationships and isolation. Critical for ensuring
    the test infrastructure remains coherent as it evolves.
    """

    def test_fixtures_work_together(
        self, temp_dir, mock_project_dir, sugar_config_file, sample_error_log
    ):
        """Verify multiple fixtures can be combined in a single test.

        Tests the fixture dependency chain:
            temp_dir → mock_project_dir → sugar_config_file
            temp_dir → mock_project_dir → sample_error_log
        """
        # Verify all fixtures are usable
        assert temp_dir.exists()
        assert mock_project_dir.exists()
        assert sugar_config_file.exists()
        assert sample_error_log.exists()

        # Verify relationships
        assert mock_project_dir.parent == temp_dir
        assert sugar_config_file.parent.parent == mock_project_dir
        assert sample_error_log.parent.parent.parent == mock_project_dir

    @pytest.mark.asyncio
    async def test_async_and_sync_fixtures_together(self, temp_dir, mock_work_queue):
        """Verify async fixtures (mock_work_queue) work with sync fixtures (temp_dir)."""
        assert temp_dir.exists()
        task_id = await mock_work_queue.add_work(
            {
                "type": "integration_test",
                "title": "Integration test task",
                "priority": 1,
                "source": "test",
            }
        )
        assert task_id is not None

    def test_sample_data_fixtures(self, sample_tasks, sample_error_log):
        """Verify sample data fixtures provide consistent, related test data.

        Both sample_tasks and sample_error_log reference files in the src/
        directory, maintaining internal consistency for testing scenarios.
        """
        assert len(sample_tasks) == 2

        with open(sample_error_log) as f:
            error_data = json.load(f)

        # Both fixtures reference src/main.py or similar structure
        assert sample_tasks[0]["context"]["file"] == "src/auth.py"
        assert error_data["file"] == "src/main.py"
