"""
Tests for Sugar CLI commands
"""
import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from sugar.main import cli


class TestSugarInit:
    """Test sugar init command"""
    
    def test_init_creates_sugar_directory(self, cli_runner, temp_dir):
        """Test that sugar init creates .sugar directory and files"""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(cli, ['init'])
            
            assert result.exit_code == 0
            assert "Sugar initialized successfully!" in result.output
            assert Path(".sugar").exists()
            assert Path(".sugar/config.yaml").exists()
            assert Path(".sugar/logs").exists()
            assert Path(".sugar/backups").exists()
            assert Path("logs/errors").exists()
    
    def test_init_with_custom_project_dir(self, cli_runner, temp_dir):
        """Test sugar init with custom project directory"""
        project_dir = temp_dir / "custom_project"
        project_dir.mkdir()
        
        result = cli_runner.invoke(cli, ['init', '--project-dir', str(project_dir)])
        
        assert result.exit_code == 0
        assert (project_dir / ".sugar").exists()
        assert (project_dir / ".sugar/config.yaml").exists()
    
    @patch('sugar.main._find_claude_cli')
    def test_init_claude_cli_detection(self, mock_find_claude, cli_runner):
        """Test Claude CLI detection during init"""
        mock_find_claude.return_value = "/usr/local/bin/claude"
        
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(cli, ['init'])
            
            assert result.exit_code == 0
            assert "Found Claude CLI: /usr/local/bin/claude" in result.output
            
            # Check config contains correct Claude path
            with open(".sugar/config.yaml") as f:
                config = yaml.safe_load(f)
            assert config['sugar']['claude']['command'] == "/usr/local/bin/claude"
    
    @patch('sugar.main._find_claude_cli')
    def test_init_claude_cli_not_found(self, mock_find_claude, cli_runner):
        """Test init when Claude CLI is not found"""
        mock_find_claude.return_value = None
        
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(cli, ['init'])
            
            assert result.exit_code == 0
            assert "Claude CLI not found" in result.output


class TestSugarAdd:
    """Test sugar add command"""
    
    def test_add_task_basic(self, cli_runner, sugar_config_file, mock_project_dir):
        """Test adding a basic task"""
        with cli_runner.isolated_filesystem():
            # Copy config to current directory
            (Path.cwd() / ".sugar").mkdir()
            with open(".sugar/config.yaml", 'w') as f:
                yaml.dump({"sugar": {"storage": {"database": ".sugar/sugar.db"}}}, f)
            
            result = cli_runner.invoke(cli, [
                'add', 
                'Fix authentication bug',
                '--type', 'bug_fix',
                '--priority', '5',
                '--description', 'Fix login issues in auth module'
            ])
            
            assert result.exit_code == 0
            assert "Added bug_fix task: 'Fix authentication bug'" in result.output
            assert "🚨 URGENT" in result.output
    
    def test_add_task_urgent_flag(self, cli_runner):
        """Test adding task with urgent flag"""
        with cli_runner.isolated_filesystem():
            (Path.cwd() / ".sugar").mkdir()
            with open(".sugar/config.yaml", 'w') as f:
                yaml.dump({"sugar": {"storage": {"database": ".sugar/sugar.db"}}}, f)
            
            result = cli_runner.invoke(cli, [
                'add',
                'Critical security fix',
                '--urgent'
            ])
            
            assert result.exit_code == 0
            assert "🚨 URGENT" in result.output
    
    def test_add_task_different_types(self, cli_runner):
        """Test adding tasks of different types"""
        with cli_runner.isolated_filesystem():
            (Path.cwd() / ".sugar").mkdir()
            with open(".sugar/config.yaml", 'w') as f:
                yaml.dump({"sugar": {"storage": {"database": ".sugar/sugar.db"}}}, f)
            
            task_types = ['bug_fix', 'feature', 'test', 'refactor', 'documentation']
            
            for task_type in task_types:
                result = cli_runner.invoke(cli, [
                    'add',
                    f'Test {task_type} task',
                    '--type', task_type
                ])
                assert result.exit_code == 0
                assert f"Added {task_type} task" in result.output


class TestSugarList:
    """Test sugar list command"""
    
    @patch('sugar.storage.work_queue.WorkQueue')
    def test_list_tasks_all(self, mock_queue_class, cli_runner):
        """Test listing all tasks"""
        mock_queue = MagicMock()
        mock_queue_class.return_value = mock_queue
        mock_queue.get_recent_work.return_value = [
            {
                'id': 'task-1',
                'type': 'bug_fix',
                'title': 'Fix auth bug',
                'description': 'Fix login issues',
                'priority': 5,
                'status': 'pending',
                'created_at': '2024-01-01T12:00:00Z',
                'attempts': 0
            }
        ]
        
        with cli_runner.isolated_filesystem():
            (Path.cwd() / ".sugar").mkdir()
            with open(".sugar/config.yaml", 'w') as f:
                yaml.dump({"sugar": {"storage": {"database": ".sugar/sugar.db"}}}, f)
            
            result = cli_runner.invoke(cli, ['list'])
            
            assert result.exit_code == 0
            assert "Fix auth bug" in result.output
            assert "🚨" in result.output  # Priority 5 should show urgent emoji
    
    @patch('sugar.storage.work_queue.WorkQueue')
    def test_list_tasks_filtered(self, mock_queue_class, cli_runner):
        """Test listing tasks with filters"""
        mock_queue = MagicMock()
        mock_queue_class.return_value = mock_queue
        mock_queue.get_recent_work.return_value = []
        
        with cli_runner.isolated_filesystem():
            (Path.cwd() / ".sugar").mkdir()
            with open(".sugar/config.yaml", 'w') as f:
                yaml.dump({"sugar": {"storage": {"database": ".sugar/sugar.db"}}}, f)
            
            result = cli_runner.invoke(cli, [
                'list',
                '--status', 'pending',
                '--type', 'bug_fix',
                '--limit', '5'
            ])
            
            assert result.exit_code == 0
            mock_queue.get_recent_work.assert_called_with(
                limit=5,
                status='pending'
            )


class TestSugarStatus:
    """Test sugar status command"""
    
    @patch('sugar.storage.work_queue.WorkQueue')
    def test_status_display(self, mock_queue_class, cli_runner):
        """Test status command displays correct information"""
        mock_queue = MagicMock()
        mock_queue_class.return_value = mock_queue
        mock_queue.get_stats.return_value = {
            'total': 10,
            'pending': 3,
            'active': 1,
            'completed': 5,
            'failed': 1,
            'recent_24h': 7
        }
        mock_queue.get_recent_work.return_value = [
            {
                'type': 'bug_fix',
                'title': 'Next urgent task',
                'priority': 5
            }
        ]
        
        with cli_runner.isolated_filesystem():
            (Path.cwd() / ".sugar").mkdir()
            with open(".sugar/config.yaml", 'w') as f:
                yaml.dump({"sugar": {"storage": {"database": ".sugar/sugar.db"}}}, f)
            
            result = cli_runner.invoke(cli, ['status'])
            
            assert result.exit_code == 0
            assert "🤖 Sugar System Status" in result.output
            assert "📊 Total Tasks: 10" in result.output
            assert "⏳ Pending: 3" in result.output
            assert "⚡ Active: 1" in result.output
            assert "✅ Completed: 5" in result.output
            assert "❌ Failed: 1" in result.output


class TestSugarRun:
    """Test sugar run command"""
    
    @patch('sugar.main.SugarLoop')
    def test_run_dry_run_mode(self, mock_loop_class, cli_runner):
        """Test run command in dry run mode"""
        mock_loop = MagicMock()
        mock_loop_class.return_value = mock_loop
        
        with cli_runner.isolated_filesystem():
            (Path.cwd() / ".sugar").mkdir()
            with open(".sugar/config.yaml", 'w') as f:
                yaml.dump({"sugar": {"dry_run": False}}, f)
            
            result = cli_runner.invoke(cli, ['run', '--dry-run', '--once'])
            
            assert result.exit_code == 0
            # Should override config dry_run setting
            mock_loop.config.__setitem__.assert_called()
    
    @patch('sugar.main.SugarLoop')
    def test_run_validate_mode(self, mock_loop_class, cli_runner):
        """Test run command in validate mode"""
        mock_loop = MagicMock()
        mock_loop_class.return_value = mock_loop
        
        with cli_runner.isolated_filesystem():
            (Path.cwd() / ".sugar").mkdir()
            with open(".sugar/config.yaml", 'w') as f:
                yaml.dump({"sugar": {"dry_run": True}}, f)
            
            result = cli_runner.invoke(cli, ['run', '--validate'])
            
            assert result.exit_code == 0