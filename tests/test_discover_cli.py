"""
Tests for Sugar Discover CLI Command

Tests the sugar discover command including:
- Configuration loading and validation
- Tool filtering (--tool flag)
- Dry-run mode (--dry-run flag)
- Timeout handling (--timeout flag)
- Integration with orchestrator and Claude Code wrapper
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from sugar.cli.discover import _execute_tool_discovery, _parse_sugar_add_commands
from sugar.main import cli


class TestParseSugarAddCommands:
    """Tests for parsing sugar add commands from Claude's output"""

    def test_parse_basic_command(self):
        """Test parsing basic sugar add command"""
        output = 'sugar add "Fix eslint error in auth.js" --type bug_fix --priority 3'
        commands = _parse_sugar_add_commands(output)

        assert len(commands) == 1
        assert commands[0]["title"] == "Fix eslint error in auth.js"
        assert commands[0]["type"] == "bug_fix"
        assert commands[0]["priority"] == 3

    def test_parse_command_with_description(self):
        """Test parsing command with description"""
        output = 'sugar add "Add error handling" --type refactor --priority 2 --description "Handle null values in user input"'
        commands = _parse_sugar_add_commands(output)

        assert len(commands) == 1
        assert commands[0]["title"] == "Add error handling"
        assert commands[0]["description"] == "Handle null values in user input"

    def test_parse_command_with_urgent_flag(self):
        """Test parsing command with --urgent flag"""
        output = 'sugar add "Critical security fix" --type bug_fix --urgent'
        commands = _parse_sugar_add_commands(output)

        assert len(commands) == 1
        assert commands[0]["title"] == "Critical security fix"
        assert commands[0]["priority"] == 5  # Urgent sets priority to 5

    def test_parse_multiple_commands(self):
        """Test parsing multiple sugar add commands"""
        output = """Here are the tasks I found:

sugar add "Fix unused variable warning" --type refactor --priority 2
sugar add "Add type annotations" --type refactor --priority 1
sugar add "Remove dead code in utils.py" --type refactor --priority 2 --description "Clean up unused functions"
"""
        commands = _parse_sugar_add_commands(output)

        assert len(commands) == 3
        assert commands[0]["title"] == "Fix unused variable warning"
        assert commands[1]["title"] == "Add type annotations"
        assert commands[2]["title"] == "Remove dead code in utils.py"

    def test_parse_command_with_defaults(self):
        """Test that defaults are applied when options missing"""
        output = 'sugar add "Simple task"'
        commands = _parse_sugar_add_commands(output)

        assert len(commands) == 1
        assert commands[0]["title"] == "Simple task"
        assert commands[0]["type"] == "refactor"  # Default type
        assert commands[0]["priority"] == 3  # Default priority
        assert commands[0]["status"] == "pending"  # Default status

    def test_parse_command_with_status(self):
        """Test parsing command with explicit status"""
        output = 'sugar add "Blocked task" --type feature --status hold'
        commands = _parse_sugar_add_commands(output)

        assert len(commands) == 1
        assert commands[0]["status"] == "hold"

    def test_parse_empty_output(self):
        """Test parsing empty output returns empty list"""
        commands = _parse_sugar_add_commands("")
        assert commands == []

    def test_parse_output_without_commands(self):
        """Test parsing output with no sugar add commands"""
        output = "No issues found in the codebase. Everything looks clean!"
        commands = _parse_sugar_add_commands(output)
        assert commands == []

    def test_parse_mixed_content(self):
        """Test parsing output with mixed content"""
        output = """Analysis complete.

I found 2 issues that should be addressed:

1. ESLint error: no-unused-vars
sugar add "Remove unused imports in auth.js" --type refactor --priority 2

2. Potential bug
sugar add "Fix null reference in utils.py" --type bug_fix --priority 4 --urgent

The rest of the code looks good.
"""
        commands = _parse_sugar_add_commands(output)

        assert len(commands) == 2
        assert commands[0]["title"] == "Remove unused imports in auth.js"
        assert commands[1]["title"] == "Fix null reference in utils.py"
        assert commands[1]["priority"] == 5  # --urgent overrides priority


class TestDiscoverCliBasic:
    """Tests for basic sugar discover CLI functionality"""

    def test_discover_no_config_file(self, cli_runner):
        """Test discover fails when no config file exists"""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(cli, ["discover"])

            assert result.exit_code == 1
            assert "Configuration file not found" in result.output
            assert "sugar init" in result.output

    def test_discover_no_external_tools_configured(self, cli_runner):
        """Test discover fails when no external tools are configured"""
        with cli_runner.isolated_filesystem():
            Path(".sugar").mkdir()
            with open(".sugar/config.yaml", "w") as f:
                yaml.dump(
                    {
                        "sugar": {
                            "storage": {"database": ".sugar/sugar.db"},
                            "discovery": {"code_quality": {}},
                        }
                    },
                    f,
                )

            result = cli_runner.invoke(cli, ["discover"])

            assert result.exit_code == 1
            assert "No external tools configured" in result.output

    def test_discover_empty_external_tools(self, cli_runner):
        """Test discover fails when external_tools is empty list"""
        with cli_runner.isolated_filesystem():
            Path(".sugar").mkdir()
            with open(".sugar/config.yaml", "w") as f:
                yaml.dump(
                    {
                        "sugar": {
                            "storage": {"database": ".sugar/sugar.db"},
                            "discovery": {"code_quality": {"external_tools": []}},
                        }
                    },
                    f,
                )

            result = cli_runner.invoke(cli, ["discover"])

            assert result.exit_code == 1
            assert "No external tools configured" in result.output

    def test_discover_invalid_tool_config(self, cli_runner):
        """Test discover fails on invalid tool configuration"""
        with cli_runner.isolated_filesystem():
            Path(".sugar").mkdir()
            with open(".sugar/config.yaml", "w") as f:
                yaml.dump(
                    {
                        "sugar": {
                            "storage": {"database": ".sugar/sugar.db"},
                            "discovery": {
                                "code_quality": {
                                    "external_tools": [
                                        {"name": "eslint"}  # Missing command
                                    ]
                                }
                            },
                        }
                    },
                    f,
                )

            result = cli_runner.invoke(cli, ["discover"])

            assert result.exit_code == 1
            assert "Invalid external tool configuration" in result.output


class TestDiscoverToolFiltering:
    """Tests for --tool flag functionality"""

    @patch("sugar.storage.work_queue.WorkQueue")
    @patch("sugar.executor.claude_wrapper.ClaudeWrapper")
    @patch("sugar.discovery.orchestrator.ToolOrchestrator")
    def test_discover_specific_tool(
        self, mock_orchestrator_class, mock_claude_class, mock_queue_class, cli_runner
    ):
        """Test running specific tool with --tool flag"""
        # Setup mocks
        mock_queue = MagicMock()
        mock_queue.initialize = AsyncMock()
        mock_queue_class.return_value = mock_queue

        mock_orchestrator = MagicMock()
        mock_orchestrator.execute_all.return_value = []
        mock_orchestrator_class.return_value = mock_orchestrator

        with cli_runner.isolated_filesystem():
            Path(".sugar").mkdir()
            with open(".sugar/config.yaml", "w") as f:
                yaml.dump(
                    {
                        "sugar": {
                            "storage": {"database": ".sugar/sugar.db"},
                            "claude": {"command": "claude", "timeout": 300},
                            "discovery": {
                                "code_quality": {
                                    "external_tools": [
                                        {"name": "eslint", "command": "npx eslint ."},
                                        {"name": "ruff", "command": "ruff check ."},
                                    ]
                                }
                            },
                        }
                    },
                    f,
                )

            result = cli_runner.invoke(cli, ["discover", "--tool", "eslint"])

            # Should not error due to tool not found
            assert "Tool 'eslint' not found" not in result.output

    def test_discover_tool_not_found(self, cli_runner):
        """Test error when specified tool doesn't exist"""
        with cli_runner.isolated_filesystem():
            Path(".sugar").mkdir()
            with open(".sugar/config.yaml", "w") as f:
                yaml.dump(
                    {
                        "sugar": {
                            "storage": {"database": ".sugar/sugar.db"},
                            "claude": {"command": "claude", "timeout": 300},
                            "discovery": {
                                "code_quality": {
                                    "external_tools": [
                                        {"name": "eslint", "command": "npx eslint ."},
                                    ]
                                }
                            },
                        }
                    },
                    f,
                )

            result = cli_runner.invoke(cli, ["discover", "--tool", "nonexistent"])

            assert result.exit_code == 1
            assert "Tool 'nonexistent' not found" in result.output
            assert "Available tools: eslint" in result.output

    def test_discover_tool_case_insensitive(self, cli_runner):
        """Test that --tool is case insensitive"""
        with cli_runner.isolated_filesystem():
            Path(".sugar").mkdir()
            with open(".sugar/config.yaml", "w") as f:
                yaml.dump(
                    {
                        "sugar": {
                            "storage": {"database": ".sugar/sugar.db"},
                            "claude": {"command": "claude", "timeout": 300},
                            "discovery": {
                                "code_quality": {
                                    "external_tools": [
                                        {"name": "ESLint", "command": "npx eslint ."},
                                    ]
                                }
                            },
                        }
                    },
                    f,
                )

            # Should match case-insensitively
            result = cli_runner.invoke(cli, ["discover", "--tool", "eslint"])

            # Should not error with "Tool not found"
            assert "Tool 'eslint' not found" not in result.output


class TestDiscoverDryRun:
    """Tests for --dry-run flag functionality"""

    @patch("sugar.storage.work_queue.WorkQueue")
    @patch("sugar.executor.claude_wrapper.ClaudeWrapper")
    def test_discover_dry_run_header(
        self, mock_claude_class, mock_queue_class, cli_runner
    ):
        """Test dry-run shows correct header"""
        mock_queue = MagicMock()
        mock_queue.initialize = AsyncMock()
        mock_queue_class.return_value = mock_queue

        with cli_runner.isolated_filesystem():
            Path(".sugar").mkdir()
            with open(".sugar/config.yaml", "w") as f:
                yaml.dump(
                    {
                        "sugar": {
                            "storage": {"database": ".sugar/sugar.db"},
                            "claude": {"command": "claude", "timeout": 300},
                            "discovery": {
                                "code_quality": {
                                    "external_tools": [
                                        {"name": "echo", "command": "echo test"},
                                    ]
                                }
                            },
                        }
                    },
                    f,
                )

            result = cli_runner.invoke(cli, ["discover", "--dry-run"])

            assert "(DRY-RUN)" in result.output

    @patch("sugar.storage.work_queue.WorkQueue")
    @patch("sugar.executor.claude_wrapper.ClaudeWrapper")
    @patch("subprocess.run")
    def test_discover_dry_run_shows_prompt_preview(
        self, mock_subprocess, mock_claude_class, mock_queue_class, cli_runner
    ):
        """Test dry-run shows prompt preview without creating tasks"""
        mock_queue = MagicMock()
        mock_queue.initialize = AsyncMock()
        mock_queue.add_work = AsyncMock()
        mock_queue_class.return_value = mock_queue

        # Mock subprocess to simulate tool output - write to file handle
        def subprocess_side_effect(*args, **kwargs):
            stdout_file = kwargs.get("stdout")
            if stdout_file and hasattr(stdout_file, "write"):
                stdout_file.write("Tool output line 1\nTool output line 2\n")
            return MagicMock(stderr="", returncode=0)

        mock_subprocess.side_effect = subprocess_side_effect

        with cli_runner.isolated_filesystem():
            Path(".sugar").mkdir()
            with open(".sugar/config.yaml", "w") as f:
                yaml.dump(
                    {
                        "sugar": {
                            "storage": {"database": ".sugar/sugar.db"},
                            "claude": {"command": "claude", "timeout": 300},
                            "discovery": {
                                "code_quality": {
                                    "external_tools": [
                                        {"name": "echo", "command": "echo test"},
                                    ]
                                }
                            },
                        }
                    },
                    f,
                )

            result = cli_runner.invoke(cli, ["discover", "--dry-run"])

            # Should show dry-run messages
            assert "[DRY-RUN]" in result.output
            assert "dry-run complete" in result.output.lower()

            # Should NOT call add_work
            mock_queue.add_work.assert_not_called()


class TestDiscoverTimeout:
    """Tests for --timeout flag functionality"""

    @patch("sugar.storage.work_queue.WorkQueue")
    @patch("sugar.executor.claude_wrapper.ClaudeWrapper")
    @patch("subprocess.run")
    def test_discover_custom_timeout(
        self, mock_subprocess, mock_claude_class, mock_queue_class, cli_runner
    ):
        """Test custom timeout is passed to orchestrator"""
        mock_queue = MagicMock()
        mock_queue.initialize = AsyncMock()
        mock_queue_class.return_value = mock_queue

        def subprocess_side_effect(*args, **kwargs):
            stdout_file = kwargs.get("stdout")
            if stdout_file and hasattr(stdout_file, "write"):
                stdout_file.write("output")
            return MagicMock(stderr="", returncode=0)

        mock_subprocess.side_effect = subprocess_side_effect

        with cli_runner.isolated_filesystem():
            Path(".sugar").mkdir()
            with open(".sugar/config.yaml", "w") as f:
                yaml.dump(
                    {
                        "sugar": {
                            "storage": {"database": ".sugar/sugar.db"},
                            "claude": {"command": "claude", "timeout": 300},
                            "discovery": {
                                "code_quality": {
                                    "external_tools": [
                                        {"name": "echo", "command": "echo test"},
                                    ]
                                }
                            },
                        }
                    },
                    f,
                )

            result = cli_runner.invoke(
                cli, ["discover", "--dry-run", "--timeout", "60"]
            )

            # Should not error
            assert result.exit_code == 0

    @patch("sugar.storage.work_queue.WorkQueue")
    @patch("sugar.executor.claude_wrapper.ClaudeWrapper")
    def test_discover_default_timeout(
        self, mock_claude_class, mock_queue_class, cli_runner
    ):
        """Test default timeout value (300 seconds)"""
        mock_queue = MagicMock()
        mock_queue.initialize = AsyncMock()
        mock_queue_class.return_value = mock_queue

        with cli_runner.isolated_filesystem():
            Path(".sugar").mkdir()
            with open(".sugar/config.yaml", "w") as f:
                yaml.dump(
                    {
                        "sugar": {
                            "storage": {"database": ".sugar/sugar.db"},
                            "claude": {"command": "claude", "timeout": 300},
                            "discovery": {
                                "code_quality": {
                                    "external_tools": [
                                        {"name": "echo", "command": "echo test"},
                                    ]
                                }
                            },
                        }
                    },
                    f,
                )

            # Run with default timeout (don't pass --timeout)
            result = cli_runner.invoke(cli, ["discover", "--dry-run"])

            # Should not error - default timeout should work
            assert result.exit_code == 0


class TestDiscoverIntegrationWithOrchestrator:
    """Integration tests for discover CLI with ToolOrchestrator"""

    @patch("sugar.storage.work_queue.WorkQueue")
    @patch("sugar.executor.claude_wrapper.ClaudeWrapper")
    @patch("subprocess.run")
    def test_discover_tool_success(
        self, mock_subprocess, mock_claude_class, mock_queue_class, cli_runner
    ):
        """Test successful tool execution through discover CLI"""
        mock_queue = MagicMock()
        mock_queue.initialize = AsyncMock()
        mock_queue_class.return_value = mock_queue

        # Mock subprocess for tool execution - write to file handle
        def subprocess_side_effect(*args, **kwargs):
            stdout_file = kwargs.get("stdout")
            if stdout_file and hasattr(stdout_file, "write"):
                stdout_file.write('{"errors": []}')
            return MagicMock(stderr="", returncode=0)

        mock_subprocess.side_effect = subprocess_side_effect

        with cli_runner.isolated_filesystem():
            Path(".sugar").mkdir()
            with open(".sugar/config.yaml", "w") as f:
                yaml.dump(
                    {
                        "sugar": {
                            "storage": {"database": ".sugar/sugar.db"},
                            "claude": {"command": "claude", "timeout": 300},
                            "discovery": {
                                "code_quality": {
                                    "external_tools": [
                                        {
                                            "name": "eslint",
                                            "command": "npx eslint . --format json",
                                        },
                                    ]
                                }
                            },
                        }
                    },
                    f,
                )

            result = cli_runner.invoke(cli, ["discover", "--dry-run"])

            # Should show tool execution
            assert "eslint" in result.output
            assert "Completed" in result.output or "DRY-RUN" in result.output

    @patch("sugar.storage.work_queue.WorkQueue")
    @patch("sugar.executor.claude_wrapper.ClaudeWrapper")
    @patch("subprocess.run")
    @patch("shutil.which")
    def test_discover_tool_not_found_graceful(
        self,
        mock_which,
        mock_subprocess,
        mock_claude_class,
        mock_queue_class,
        cli_runner,
    ):
        """Test graceful handling when tool executable not found"""
        mock_queue = MagicMock()
        mock_queue.initialize = AsyncMock()
        mock_queue_class.return_value = mock_queue

        # Simulate tool not found
        mock_which.return_value = None

        with cli_runner.isolated_filesystem():
            Path(".sugar").mkdir()
            with open(".sugar/config.yaml", "w") as f:
                yaml.dump(
                    {
                        "sugar": {
                            "storage": {"database": ".sugar/sugar.db"},
                            "claude": {"command": "claude", "timeout": 300},
                            "discovery": {
                                "code_quality": {
                                    "external_tools": [
                                        {
                                            "name": "nonexistent_tool",
                                            "command": "nonexistent_tool --check",
                                        },
                                    ]
                                }
                            },
                        }
                    },
                    f,
                )

            result = cli_runner.invoke(cli, ["discover"])

            # Should complete (exit 0) but show tool failure
            assert "Failed" in result.output or "not found" in result.output.lower()


class TestDiscoverIntegrationWithClaudeCode:
    """Integration tests for discover CLI with mocked Claude Code"""

    def _setup_mock_queue(self, mock_queue_class):
        """Setup mock work queue with common configuration."""
        mock_queue = MagicMock()
        mock_queue.initialize = AsyncMock()
        mock_queue.add_work = AsyncMock()
        mock_queue_class.return_value = mock_queue
        return mock_queue

    def _setup_mock_claude(
        self, mock_claude_class, *, success=True, output="", error=None, exception=None
    ):
        """Setup mock Claude wrapper with configurable response."""
        mock_claude = MagicMock()
        if exception:
            mock_claude.execute_work = AsyncMock(side_effect=exception)
        else:
            mock_claude.execute_work = AsyncMock(
                return_value={"success": success, "output": output, "error": error}
            )
        mock_claude_class.return_value = mock_claude
        return mock_claude

    def _setup_mock_subprocess(
        self, mock_subprocess, *, stdout="", stderr="", returncode=0
    ):
        """Setup mock subprocess with configurable output.

        Writes stdout to the file handle passed to subprocess.run since
        the orchestrator now writes output to files instead of capturing.
        """

        def subprocess_side_effect(*args, **kwargs):
            # Write stdout to the file handle if provided
            stdout_file = kwargs.get("stdout")
            if stdout_file and hasattr(stdout_file, "write"):
                stdout_file.write(stdout)
            return MagicMock(stderr=stderr, returncode=returncode)

        mock_subprocess.side_effect = subprocess_side_effect

    def _create_discover_config(self, tool_name="tool", tool_command="tool --check"):
        """Create a minimal discover configuration dict."""
        return {
            "sugar": {
                "storage": {"database": ".sugar/sugar.db"},
                "claude": {"command": "claude", "timeout": 300},
                "discovery": {
                    "code_quality": {
                        "external_tools": [{"name": tool_name, "command": tool_command}]
                    }
                },
            }
        }

    def _write_config_file(self, config):
        """Write config to .sugar/config.yaml (must be inside isolated_filesystem)."""
        Path(".sugar").mkdir(exist_ok=True)
        with open(".sugar/config.yaml", "w") as f:
            yaml.dump(config, f)

    @patch("sugar.storage.work_queue.WorkQueue")
    @patch("sugar.executor.claude_wrapper.ClaudeWrapper")
    @patch("subprocess.run")
    def test_discover_creates_tasks_from_claude_output(
        self, mock_subprocess, mock_claude_class, mock_queue_class, cli_runner
    ):
        """Test end-to-end: config → execute → Claude → tasks"""
        claude_output = """Analysis complete. Here are the tasks:

sugar add "Fix no-unused-vars in auth.js" --type refactor --priority 2 --description "Remove unused import at line 15"
sugar add "Add error handling in api.js" --type bug_fix --priority 4 --description "Handle null response"
"""
        mock_queue = self._setup_mock_queue(mock_queue_class)
        self._setup_mock_claude(mock_claude_class, success=True, output=claude_output)
        self._setup_mock_subprocess(
            mock_subprocess,
            stdout='[{"ruleId": "no-unused-vars", "message": "x is unused"}]',
            returncode=1,
        )

        with cli_runner.isolated_filesystem():
            config = self._create_discover_config(
                "eslint", "npx eslint . --format json"
            )
            self._write_config_file(config)

            cli_runner.invoke(cli, ["discover"])

            assert mock_queue.add_work.call_count == 2
            self._verify_task(
                mock_queue, 0, "Fix no-unused-vars in auth.js", "refactor", 2
            )
            self._verify_task(
                mock_queue, 1, "Add error handling in api.js", "bug_fix", 4
            )

    def _verify_task(
        self, mock_queue, index, expected_title, expected_type, expected_priority
    ):
        """Verify a task was added with expected values."""
        calls = mock_queue.add_work.call_args_list
        task = calls[index][0][0]
        assert task["title"] == expected_title
        assert task["type"] == expected_type
        assert task["priority"] == expected_priority

    @patch("sugar.storage.work_queue.WorkQueue")
    @patch("sugar.executor.claude_wrapper.ClaudeWrapper")
    @patch("subprocess.run")
    def test_discover_handles_claude_failure(
        self, mock_subprocess, mock_claude_class, mock_queue_class, cli_runner
    ):
        """Test handling when Claude Code returns an error"""
        mock_queue = self._setup_mock_queue(mock_queue_class)
        self._setup_mock_claude(
            mock_claude_class, success=False, error="Claude Code execution failed"
        )
        self._setup_mock_subprocess(mock_subprocess, stdout="tool output")

        with cli_runner.isolated_filesystem():
            self._write_config_file(self._create_discover_config())
            cli_runner.invoke(cli, ["discover"])
            mock_queue.add_work.assert_not_called()

    @patch("sugar.storage.work_queue.WorkQueue")
    @patch("sugar.executor.claude_wrapper.ClaudeWrapper")
    @patch("subprocess.run")
    def test_discover_handles_claude_exception(
        self, mock_subprocess, mock_claude_class, mock_queue_class, cli_runner
    ):
        """Test handling when Claude Code raises exception"""
        self._setup_mock_queue(mock_queue_class)
        self._setup_mock_claude(
            mock_claude_class, exception=Exception("Connection failed")
        )
        self._setup_mock_subprocess(mock_subprocess, stdout="tool output")

        with cli_runner.isolated_filesystem():
            self._write_config_file(self._create_discover_config())
            result = cli_runner.invoke(cli, ["discover"])
            assert "error" in result.output.lower() or "failed" in result.output.lower()

    @patch("sugar.storage.work_queue.WorkQueue")
    @patch("sugar.executor.claude_wrapper.ClaudeWrapper")
    @patch("subprocess.run")
    def test_discover_handles_no_issues_found(
        self, mock_subprocess, mock_claude_class, mock_queue_class, cli_runner
    ):
        """Test handling when Claude finds no actionable issues"""
        mock_queue = self._setup_mock_queue(mock_queue_class)
        self._setup_mock_claude(
            mock_claude_class,
            success=True,
            output="No issues found. The code looks clean!",
        )
        self._setup_mock_subprocess(mock_subprocess, stdout="[]")

        with cli_runner.isolated_filesystem():
            self._write_config_file(self._create_discover_config())
            result = cli_runner.invoke(cli, ["discover"])

            mock_queue.add_work.assert_not_called()
            assert "0 new tasks" in result.output or "No actionable" in result.output


class TestDiscoverMultipleTools:
    """Tests for running multiple tools"""

    @patch("sugar.storage.work_queue.WorkQueue")
    @patch("sugar.executor.claude_wrapper.ClaudeWrapper")
    @patch("subprocess.run")
    def test_discover_runs_all_tools(
        self, mock_subprocess, mock_claude_class, mock_queue_class, cli_runner
    ):
        """Test discover runs all configured tools"""
        mock_queue = MagicMock()
        mock_queue.initialize = AsyncMock()
        mock_queue.add_work = AsyncMock()
        mock_queue_class.return_value = mock_queue

        mock_claude = MagicMock()
        mock_claude.execute_work = AsyncMock(
            return_value={"success": True, "output": "No issues found"}
        )
        mock_claude_class.return_value = mock_claude

        # Return different outputs for each tool
        mock_subprocess.side_effect = [
            MagicMock(stdout="eslint output", stderr="", returncode=0),
            MagicMock(stdout="ruff output", stderr="", returncode=0),
            MagicMock(stdout="mypy output", stderr="", returncode=0),
        ]

        with cli_runner.isolated_filesystem():
            Path(".sugar").mkdir()
            with open(".sugar/config.yaml", "w") as f:
                yaml.dump(
                    {
                        "sugar": {
                            "storage": {"database": ".sugar/sugar.db"},
                            "claude": {"command": "claude", "timeout": 300},
                            "discovery": {
                                "code_quality": {
                                    "external_tools": [
                                        {"name": "eslint", "command": "npx eslint ."},
                                        {"name": "ruff", "command": "ruff check ."},
                                        {"name": "mypy", "command": "mypy ."},
                                    ]
                                }
                            },
                        }
                    },
                    f,
                )

            result = cli_runner.invoke(cli, ["discover"])

            # Should show all tools
            assert "eslint" in result.output
            assert "ruff" in result.output
            assert "mypy" in result.output

    @patch("sugar.storage.work_queue.WorkQueue")
    @patch("sugar.executor.claude_wrapper.ClaudeWrapper")
    @patch("subprocess.run")
    @patch("shutil.which")
    def test_discover_continues_after_one_tool_fails(
        self,
        mock_which,
        mock_subprocess,
        mock_claude_class,
        mock_queue_class,
        cli_runner,
    ):
        """Test discover continues running other tools after one fails"""
        mock_queue = MagicMock()
        mock_queue.initialize = AsyncMock()
        mock_queue.add_work = AsyncMock()
        mock_queue_class.return_value = mock_queue

        mock_claude = MagicMock()
        mock_claude.execute_work = AsyncMock(
            return_value={"success": True, "output": "No issues"}
        )
        mock_claude_class.return_value = mock_claude

        # First tool (eslint via npx) succeeds, second (bad) fails, third succeeds
        def which_side_effect(cmd):
            if cmd in ("npx", "ruff"):
                return f"/usr/bin/{cmd}"
            return None

        mock_which.side_effect = which_side_effect

        mock_subprocess.side_effect = [
            MagicMock(stdout="eslint output", stderr="", returncode=0),
            # bad_tool never reaches subprocess because which returns None
            MagicMock(stdout="ruff output", stderr="", returncode=0),
        ]

        with cli_runner.isolated_filesystem():
            Path(".sugar").mkdir()
            with open(".sugar/config.yaml", "w") as f:
                yaml.dump(
                    {
                        "sugar": {
                            "storage": {"database": ".sugar/sugar.db"},
                            "claude": {"command": "claude", "timeout": 300},
                            "discovery": {
                                "code_quality": {
                                    "external_tools": [
                                        {"name": "eslint", "command": "npx eslint ."},
                                        {"name": "bad", "command": "bad_tool --check"},
                                        {"name": "ruff", "command": "ruff check ."},
                                    ]
                                }
                            },
                        }
                    },
                    f,
                )

            result = cli_runner.invoke(cli, ["discover"])

            # Should show all three tools attempted
            assert "eslint" in result.output
            assert "bad" in result.output
            assert "ruff" in result.output


class TestDiscoverHelpAndUsage:
    """Tests for help and usage information"""

    def test_discover_help(self, cli_runner):
        """Test discover --help shows usage information"""
        result = cli_runner.invoke(cli, ["discover", "--help"])

        assert result.exit_code == 0
        assert "Run external tool discovery" in result.output
        assert "--tool" in result.output
        assert "--dry-run" in result.output
        assert "--timeout" in result.output

    def test_discover_examples_in_help(self, cli_runner):
        """Test that help includes usage examples"""
        result = cli_runner.invoke(cli, ["discover", "--help"])

        assert result.exit_code == 0
        assert "Examples" in result.output
        assert "sugar discover" in result.output
