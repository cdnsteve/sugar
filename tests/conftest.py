"""
Pytest configuration and fixtures for Sugar tests
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import asyncio
import yaml
import json
from click.testing import CliRunner

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)

@pytest.fixture
def mock_project_dir(temp_dir):
    """Create a mock project directory with typical structure"""
    project_dir = temp_dir / "test_project"
    project_dir.mkdir()
    
    # Create typical project structure
    (project_dir / "src").mkdir()
    (project_dir / "tests").mkdir()
    (project_dir / "logs" / "errors").mkdir(parents=True)
    
    # Create some sample files
    (project_dir / "src" / "main.py").write_text("# Sample Python file\nprint('hello')")
    (project_dir / "README.md").write_text("# Test Project")
    
    return project_dir

@pytest.fixture
def sugar_config():
    """Sample Sugar configuration for testing"""
    return {
        "sugar": {
            "loop_interval": 60,
            "max_concurrent_work": 2,
            "dry_run": True,
            "claude": {
                "command": "/mock/path/to/claude",
                "timeout": 300,
                "context_file": ".sugar/context.json"
            },
            "discovery": {
                "error_logs": {
                    "enabled": True,
                    "paths": ["logs/errors/"],
                    "patterns": ["*.json", "*.log"],
                    "max_age_hours": 24
                },
                "github": {
                    "enabled": False
                },
                "code_quality": {
                    "enabled": True,
                    "root_path": ".",
                    "file_extensions": [".py"],
                    "excluded_dirs": ["__pycache__", ".git"]
                },
                "test_coverage": {
                    "enabled": True,
                    "source_dirs": ["src"],
                    "test_dirs": ["tests"]
                }
            },
            "storage": {
                "database": ".sugar/sugar.db",
                "backup_interval": 3600
            },
            "safety": {
                "max_retries": 3,
                "excluded_paths": ["/System", "/usr/bin", ".sugar"]
            },
            "logging": {
                "level": "INFO",
                "file": ".sugar/sugar.log"
            }
        }
    }

@pytest.fixture
def sugar_config_file(mock_project_dir, sugar_config):
    """Create a Sugar config file in the mock project"""
    sugar_dir = mock_project_dir / ".sugar"
    sugar_dir.mkdir()
    
    config_file = sugar_dir / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(sugar_config, f)
    
    return config_file

@pytest.fixture
def cli_runner():
    """Click CLI test runner"""
    return CliRunner()

@pytest.fixture
def mock_claude_cli():
    """Mock Claude CLI responses"""
    with patch('subprocess.run') as mock_run:
        # Mock successful Claude CLI execution
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Task completed successfully"
        mock_run.return_value.stderr = ""
        yield mock_run

@pytest.fixture
def sample_error_log(mock_project_dir):
    """Create a sample error log file"""
    error_file = mock_project_dir / "logs" / "errors" / "test_error.json"
    error_data = {
        "timestamp": "2024-01-01T12:00:00Z",
        "error": "AttributeError",
        "message": "object has no attribute 'method'",
        "file": "src/main.py",
        "line": 42,
        "context": "User authentication module"
    }
    
    with open(error_file, 'w') as f:
        json.dump(error_data, f)
    
    return error_file

@pytest.fixture
def sample_tasks():
    """Sample task data for testing"""
    return [
        {
            "id": "task-1",
            "type": "bug_fix",
            "title": "Fix authentication error",
            "description": "Fix AttributeError in auth module",
            "priority": 5,
            "status": "pending",
            "source": "error_log",
            "context": {"file": "src/auth.py", "line": 42}
        },
        {
            "id": "task-2", 
            "type": "feature",
            "title": "Add user registration",
            "description": "Implement user registration form",
            "priority": 3,
            "status": "completed",
            "source": "manual",
            "context": {"component": "user_management"}
        }
    ]

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def mock_work_queue(temp_dir):
    """Create a mock work queue for testing"""
    from sugar.storage.work_queue import WorkQueue
    
    db_path = temp_dir / "test.db"
    queue = WorkQueue(str(db_path))
    await queue.initialize()
    yield queue
    await queue.close()