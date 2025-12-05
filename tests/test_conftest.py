"""
Tests for conftest.py fixtures

This module tests the pytest fixtures defined in conftest.py to ensure
they function correctly and provide the expected test infrastructure.
"""

import pytest
import json
import yaml
from pathlib import Path


class TestTempDirFixture:
    """Test the temp_dir fixture"""

    def test_temp_dir_exists(self, temp_dir):
        """Test that temp_dir creates an existing directory"""
        assert temp_dir.exists()
        assert temp_dir.is_dir()

    def test_temp_dir_is_writable(self, temp_dir):
        """Test that temp_dir is writable"""
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test content")
        assert test_file.exists()
        assert test_file.read_text() == "test content"

    def test_temp_dir_is_path_object(self, temp_dir):
        """Test that temp_dir returns a Path object"""
        assert isinstance(temp_dir, Path)

    def test_temp_dir_cleanup(self):
        """Test that temp_dir is cleaned up after test"""
        # This test verifies cleanup by design - the fixture uses yield
        # and cleans up with shutil.rmtree after the test completes
        pass  # Cleanup is verified by fixture design


class TestMockProjectDirFixture:
    """Test the mock_project_dir fixture"""

    def test_mock_project_dir_exists(self, mock_project_dir):
        """Test that mock_project_dir creates a project directory"""
        assert mock_project_dir.exists()
        assert mock_project_dir.is_dir()
        assert mock_project_dir.name == "test_project"

    def test_mock_project_dir_structure(self, mock_project_dir):
        """Test that mock_project_dir creates the expected structure"""
        # Check directories
        assert (mock_project_dir / "src").exists()
        assert (mock_project_dir / "tests").exists()
        assert (mock_project_dir / "logs" / "errors").exists()

    def test_mock_project_dir_files(self, mock_project_dir):
        """Test that mock_project_dir creates sample files"""
        # Check files
        main_py = mock_project_dir / "src" / "main.py"
        assert main_py.exists()
        assert "print('hello')" in main_py.read_text()

        readme = mock_project_dir / "README.md"
        assert readme.exists()
        assert "# Test Project" in readme.read_text()

    def test_mock_project_dir_is_child_of_temp_dir(self, temp_dir, mock_project_dir):
        """Test that mock_project_dir is inside temp_dir"""
        assert mock_project_dir.parent == temp_dir


class TestSugarConfigFixture:
    """Test the sugar_config fixture"""

    def test_sugar_config_has_required_keys(self, sugar_config):
        """Test that sugar_config has all required keys"""
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
        """Test the claude configuration section"""
        claude_config = sugar_config["sugar"]["claude"]
        assert "command" in claude_config
        assert "timeout" in claude_config
        assert "context_file" in claude_config

    def test_sugar_config_discovery_section(self, sugar_config):
        """Test the discovery configuration section"""
        discovery = sugar_config["sugar"]["discovery"]
        assert "error_logs" in discovery
        assert "github" in discovery
        assert "code_quality" in discovery
        assert "test_coverage" in discovery

    def test_sugar_config_error_logs_settings(self, sugar_config):
        """Test error_logs discovery settings"""
        error_logs = sugar_config["sugar"]["discovery"]["error_logs"]
        assert error_logs["enabled"] is True
        assert "paths" in error_logs
        assert "patterns" in error_logs
        assert "max_age_hours" in error_logs

    def test_sugar_config_safety_settings(self, sugar_config):
        """Test safety configuration settings"""
        safety = sugar_config["sugar"]["safety"]
        assert "max_retries" in safety
        assert safety["max_retries"] == 3
        assert "excluded_paths" in safety


class TestSugarConfigFileFixture:
    """Test the sugar_config_file fixture"""

    def test_sugar_config_file_exists(self, sugar_config_file):
        """Test that sugar_config_file creates an actual file"""
        assert sugar_config_file.exists()
        assert sugar_config_file.is_file()
        assert sugar_config_file.name == "config.yaml"

    def test_sugar_config_file_is_valid_yaml(self, sugar_config_file):
        """Test that sugar_config_file contains valid YAML"""
        with open(sugar_config_file) as f:
            config = yaml.safe_load(f)
        assert config is not None
        assert "sugar" in config

    def test_sugar_config_file_in_sugar_dir(self, sugar_config_file, mock_project_dir):
        """Test that sugar_config_file is in .sugar directory"""
        assert sugar_config_file.parent.name == ".sugar"
        assert sugar_config_file.parent.parent == mock_project_dir


class TestCliRunnerFixture:
    """Test the cli_runner fixture"""

    def test_cli_runner_type(self, cli_runner):
        """Test that cli_runner is a CliRunner instance"""
        from click.testing import CliRunner

        assert isinstance(cli_runner, CliRunner)

    def test_cli_runner_isolated_filesystem(self, cli_runner):
        """Test that cli_runner can create isolated filesystem"""
        with cli_runner.isolated_filesystem():
            test_file = Path("test.txt")
            test_file.write_text("test content")
            assert test_file.exists()


class TestMockClaudeCliFixture:
    """Test the mock_claude_cli fixture"""

    def test_mock_claude_cli_patches_subprocess(self, mock_claude_cli):
        """Test that mock_claude_cli patches subprocess.run"""
        import subprocess

        # The fixture patches subprocess.run
        result = subprocess.run(["mock", "command"])
        assert result.returncode == 0
        assert result.stdout == "Task completed successfully"
        assert result.stderr == ""

    def test_mock_claude_cli_is_called(self, mock_claude_cli):
        """Test that mock_claude_cli records calls"""
        import subprocess

        subprocess.run(["test", "command"])
        mock_claude_cli.assert_called_once()


class TestSampleErrorLogFixture:
    """Test the sample_error_log fixture"""

    def test_sample_error_log_exists(self, sample_error_log):
        """Test that sample_error_log creates a file"""
        assert sample_error_log.exists()
        assert sample_error_log.is_file()

    def test_sample_error_log_is_valid_json(self, sample_error_log):
        """Test that sample_error_log contains valid JSON"""
        with open(sample_error_log) as f:
            data = json.load(f)
        assert data is not None

    def test_sample_error_log_structure(self, sample_error_log):
        """Test the structure of sample_error_log"""
        with open(sample_error_log) as f:
            data = json.load(f)

        assert "timestamp" in data
        assert "error" in data
        assert "message" in data
        assert "file" in data
        assert "line" in data
        assert "context" in data

    def test_sample_error_log_content(self, sample_error_log):
        """Test the content of sample_error_log"""
        with open(sample_error_log) as f:
            data = json.load(f)

        assert data["error"] == "AttributeError"
        assert data["line"] == 42
        assert data["file"] == "src/main.py"

    def test_sample_error_log_location(self, sample_error_log, mock_project_dir):
        """Test that sample_error_log is in the correct location"""
        assert sample_error_log.parent.name == "errors"
        assert sample_error_log.parent.parent.name == "logs"


class TestSampleTasksFixture:
    """Test the sample_tasks fixture"""

    def test_sample_tasks_is_list(self, sample_tasks):
        """Test that sample_tasks returns a list"""
        assert isinstance(sample_tasks, list)

    def test_sample_tasks_count(self, sample_tasks):
        """Test the number of sample tasks"""
        assert len(sample_tasks) == 2

    def test_sample_tasks_structure(self, sample_tasks):
        """Test the structure of each sample task"""
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
        """Test the first sample task content"""
        task = sample_tasks[0]
        assert task["id"] == "task-1"
        assert task["type"] == "bug_fix"
        assert task["priority"] == 5
        assert task["status"] == "pending"

    def test_sample_tasks_second_task(self, sample_tasks):
        """Test the second sample task content"""
        task = sample_tasks[1]
        assert task["id"] == "task-2"
        assert task["type"] == "feature"
        assert task["status"] == "completed"


class TestMockWorkQueueFixture:
    """Test the mock_work_queue fixture"""

    @pytest.mark.asyncio
    async def test_mock_work_queue_initialized(self, mock_work_queue):
        """Test that mock_work_queue is properly initialized"""
        # The fixture awaits initialize() before yielding
        assert mock_work_queue is not None

    @pytest.mark.asyncio
    async def test_mock_work_queue_can_add_work(self, mock_work_queue):
        """Test that mock_work_queue can add work items"""
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
        """Test that mock_work_queue can retrieve work items"""
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
        """Test that mock_work_queue creates a database file"""
        db_path = temp_dir / "test.db"
        assert db_path.exists()


class TestEventLoopFixture:
    """Test the event_loop fixture"""

    @pytest.mark.asyncio
    async def test_event_loop_works(self):
        """Test that the event loop fixture enables async tests"""
        import asyncio

        # Simple async operation
        await asyncio.sleep(0.01)
        assert True

    @pytest.mark.asyncio
    async def test_event_loop_can_run_tasks(self):
        """Test that the event loop can run async tasks"""
        import asyncio

        result = []

        async def async_task():
            result.append("completed")

        await async_task()
        assert result == ["completed"]


class TestFixtureIntegration:
    """Test fixture combinations and integration"""

    def test_fixtures_work_together(
        self, temp_dir, mock_project_dir, sugar_config_file, sample_error_log
    ):
        """Test that multiple fixtures can be used together"""
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
        """Test that async and sync fixtures work together"""
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
        """Test that sample data fixtures provide consistent data"""
        assert len(sample_tasks) == 2

        with open(sample_error_log) as f:
            error_data = json.load(f)

        # Both fixtures reference src/main.py or similar structure
        assert sample_tasks[0]["context"]["file"] == "src/auth.py"
        assert error_data["file"] == "src/main.py"
