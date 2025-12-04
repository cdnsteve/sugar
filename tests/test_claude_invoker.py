"""
Tests for Claude Invoker Module

Tests the ToolOutputInterpreter and related functionality for
interpreting tool output via Claude Code.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from dataclasses import asdict

from sugar.quality.claude_invoker import (
    ToolOutputInterpreter,
    ParsedCommand,
    InterpretationResult,
)


class TestParsedCommand:
    """Tests for ParsedCommand dataclass"""

    def test_default_values(self):
        """Test default values for ParsedCommand"""
        cmd = ParsedCommand(title="Test task")
        assert cmd.title == "Test task"
        assert cmd.task_type == "bug_fix"
        assert cmd.priority == 3
        assert cmd.description == ""
        assert cmd.urgent is False
        assert cmd.status == "pending"
        assert cmd.valid is True
        assert cmd.validation_error == ""

    def test_custom_values(self):
        """Test custom values for ParsedCommand"""
        cmd = ParsedCommand(
            title="Fix critical bug",
            task_type="feature",
            priority=5,
            description="Important fix",
            urgent=True,
            status="hold",
            raw_command="sugar add 'Fix critical bug' --type feature --priority 5",
            valid=True,
        )
        assert cmd.title == "Fix critical bug"
        assert cmd.task_type == "feature"
        assert cmd.priority == 5
        assert cmd.urgent is True


class TestInterpretationResult:
    """Tests for InterpretationResult dataclass"""

    def test_default_values(self):
        """Test default values for InterpretationResult"""
        result = InterpretationResult(success=True)
        assert result.success is True
        assert result.commands == []
        assert result.raw_response == ""
        assert result.error_message == ""
        assert result.execution_time == 0.0

    def test_with_commands(self):
        """Test InterpretationResult with commands"""
        commands = [
            ParsedCommand(title="Task 1"),
            ParsedCommand(title="Task 2"),
        ]
        result = InterpretationResult(
            success=True,
            commands=commands,
            execution_time=1.5,
        )
        assert len(result.commands) == 2
        assert result.execution_time == 1.5


class TestToolOutputInterpreterInit:
    """Tests for ToolOutputInterpreter initialization"""

    def test_default_init(self):
        """Test initialization with default configuration"""
        interpreter = ToolOutputInterpreter()
        assert interpreter.wrapper is not None
        assert interpreter.custom_template is None

    def test_custom_template(self):
        """Test initialization with custom template"""
        custom_template = "Custom template: ${tool_name}"
        interpreter = ToolOutputInterpreter(prompt_template=custom_template)
        assert interpreter.custom_template == custom_template

    def test_custom_wrapper_config(self):
        """Test initialization with custom wrapper config"""
        config = {
            "command": "/custom/claude",
            "timeout": 600,
        }
        interpreter = ToolOutputInterpreter(wrapper_config=config)
        assert interpreter.wrapper.command == "/custom/claude"
        assert interpreter.wrapper.timeout == 600


class TestCommandParsing:
    """Tests for command parsing functionality"""

    def setup_method(self):
        """Set up test interpreter"""
        self.interpreter = ToolOutputInterpreter()

    def test_parse_simple_command(self):
        """Test parsing a simple sugar add command"""
        cmd = self.interpreter._parse_command('sugar add "Fix authentication bug"')
        assert cmd.valid is True
        assert cmd.title == "Fix authentication bug"
        assert cmd.task_type == "bug_fix"  # default
        assert cmd.priority == 3  # default

    def test_parse_command_with_type(self):
        """Test parsing command with --type option"""
        cmd = self.interpreter._parse_command(
            'sugar add "Implement login feature" --type feature'
        )
        assert cmd.valid is True
        assert cmd.title == "Implement login feature"
        assert cmd.task_type == "feature"

    def test_parse_command_with_priority(self):
        """Test parsing command with --priority option"""
        cmd = self.interpreter._parse_command('sugar add "Critical bug" --priority 5')
        assert cmd.valid is True
        assert cmd.priority == 5

    def test_parse_command_with_description(self):
        """Test parsing command with --description option"""
        cmd = self.interpreter._parse_command(
            'sugar add "Fix bug" --description "This bug causes crashes"'
        )
        assert cmd.valid is True
        assert cmd.description == "This bug causes crashes"

    def test_parse_command_with_urgent_flag(self):
        """Test parsing command with --urgent flag"""
        cmd = self.interpreter._parse_command('sugar add "Urgent issue" --urgent')
        assert cmd.valid is True
        assert cmd.urgent is True

    def test_parse_command_with_status(self):
        """Test parsing command with --status option"""
        cmd = self.interpreter._parse_command(
            'sugar add "Low priority task" --status hold'
        )
        assert cmd.valid is True
        assert cmd.status == "hold"

    def test_parse_command_with_all_options(self):
        """Test parsing command with all options"""
        cmd = self.interpreter._parse_command(
            'sugar add "Complete task" --type bug_fix --priority 4 '
            '--description "Detailed description" --status pending --urgent'
        )
        assert cmd.valid is True
        assert cmd.title == "Complete task"
        assert cmd.task_type == "bug_fix"
        assert cmd.priority == 4
        assert cmd.description == "Detailed description"
        assert cmd.status == "pending"
        assert cmd.urgent is True

    def test_parse_invalid_command_not_sugar(self):
        """Test parsing invalid command that doesn't start with sugar"""
        cmd = self.interpreter._parse_command("npm install something")
        assert cmd.valid is False
        assert "must start with 'sugar add'" in cmd.validation_error

    def test_parse_invalid_command_no_title(self):
        """Test parsing command without title"""
        cmd = self.interpreter._parse_command("sugar add --type bug_fix")
        assert cmd.valid is False
        assert "must have a title" in cmd.validation_error

    def test_parse_invalid_priority(self):
        """Test parsing command with invalid priority"""
        cmd = self.interpreter._parse_command('sugar add "Task" --priority abc')
        assert cmd.valid is False
        assert "must be an integer" in cmd.validation_error

    def test_parse_invalid_status(self):
        """Test parsing command with invalid status"""
        cmd = self.interpreter._parse_command('sugar add "Task" --status invalid')
        assert cmd.valid is False
        assert "must be 'pending' or 'hold'" in cmd.validation_error

    def test_parse_command_with_special_characters(self):
        """Test parsing command with special characters in title"""
        cmd = self.interpreter._parse_command('sugar add "Fix bug in src/auth.py:42"')
        assert cmd.valid is True
        assert cmd.title == "Fix bug in src/auth.py:42"

    def test_parse_command_with_single_quotes(self):
        """Test parsing command with single quotes"""
        cmd = self.interpreter._parse_command(
            "sugar add 'Single quoted title' --type feature"
        )
        assert cmd.valid is True
        assert cmd.title == "Single quoted title"


class TestCommandExtraction:
    """Tests for extracting commands from Claude response"""

    def setup_method(self):
        """Set up test interpreter"""
        self.interpreter = ToolOutputInterpreter()

    def test_extract_single_command(self):
        """Test extracting a single command from response"""
        response = """Here are the tasks I identified:

sugar add "Fix authentication bug" --type bug_fix --priority 4

Please review these tasks."""

        commands = self.interpreter._extract_commands(response)
        assert len(commands) == 1
        assert commands[0].title == "Fix authentication bug"

    def test_extract_multiple_commands(self):
        """Test extracting multiple commands from response"""
        response = """Based on my analysis, I recommend:

sugar add "Fix SQL injection in login" --type bug_fix --priority 5
sugar add "Update password hashing" --type refactor --priority 3
sugar add "Add input validation" --type feature --priority 4

These should address the security issues."""

        commands = self.interpreter._extract_commands(response)
        assert len(commands) == 3
        assert commands[0].title == "Fix SQL injection in login"
        assert commands[1].title == "Update password hashing"
        assert commands[2].title == "Add input validation"

    def test_extract_ignores_non_command_lines(self):
        """Test that non-command lines are ignored"""
        response = """Analysis complete.
Here is my recommendation:
sugar add "Fix bug" --type bug_fix
Note: This is important.
The command above should work."""

        commands = self.interpreter._extract_commands(response)
        assert len(commands) == 1
        assert commands[0].title == "Fix bug"

    def test_extract_handles_empty_response(self):
        """Test extraction from empty response"""
        commands = self.interpreter._extract_commands("")
        assert len(commands) == 0

    def test_extract_handles_no_commands(self):
        """Test extraction from response with no commands"""
        response = """I analyzed the output but found no issues.
No tasks need to be created."""

        commands = self.interpreter._extract_commands(response)
        assert len(commands) == 0

    def test_extract_skips_malformed_commands(self):
        """Test that malformed commands are skipped with warning"""
        response = """sugar add "Valid task" --type bug_fix
sugar add --type bug_fix
sugar add "Another valid" --priority 3"""

        commands = self.interpreter._extract_commands(response)
        # Should have 2 valid commands (middle one has no title)
        assert len(commands) == 2
        assert commands[0].title == "Valid task"
        assert commands[1].title == "Another valid"


class TestExecuteCommands:
    """Tests for executing sugar add commands"""

    def setup_method(self):
        """Set up test interpreter"""
        self.interpreter = ToolOutputInterpreter()

    def test_execute_dry_run(self):
        """Test executing commands in dry run mode"""
        commands = [
            ParsedCommand(title="Task 1", task_type="bug_fix", priority=3),
            ParsedCommand(title="Task 2", task_type="feature", priority=4),
        ]

        count = self.interpreter.execute_commands(commands, dry_run=True)
        assert count == 2

    def test_execute_skips_invalid_commands(self):
        """Test that invalid commands are skipped"""
        commands = [
            ParsedCommand(title="Valid task"),
            ParsedCommand(title="", valid=False, validation_error="No title"),
            ParsedCommand(title="Another valid task"),
        ]

        count = self.interpreter.execute_commands(commands, dry_run=True)
        assert count == 2

    @patch("subprocess.run")
    def test_execute_real_commands(self, mock_run):
        """Test executing real sugar add commands"""
        mock_run.return_value = Mock(returncode=0, stdout="Task created", stderr="")

        commands = [
            ParsedCommand(title="Test task", task_type="bug_fix", priority=3),
        ]

        count = self.interpreter.execute_commands(commands, dry_run=False)
        assert count == 1
        mock_run.assert_called_once()

        # Verify command arguments
        call_args = mock_run.call_args[0][0]
        assert "sugar" in call_args
        assert "add" in call_args
        assert "Test task" in call_args

    @patch("subprocess.run")
    def test_execute_handles_failure(self, mock_run):
        """Test handling of command execution failure"""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error")

        commands = [
            ParsedCommand(title="Failing task"),
        ]

        count = self.interpreter.execute_commands(commands, dry_run=False)
        assert count == 0

    @patch("subprocess.run")
    def test_execute_handles_timeout(self, mock_run):
        """Test handling of command timeout"""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="sugar", timeout=30)

        commands = [
            ParsedCommand(title="Slow task"),
        ]

        count = self.interpreter.execute_commands(commands, dry_run=False)
        assert count == 0

    @patch("subprocess.run")
    def test_execute_builds_correct_command(self, mock_run):
        """Test that the correct command arguments are built"""
        mock_run.return_value = Mock(returncode=0)

        commands = [
            ParsedCommand(
                title="Complex task",
                task_type="feature",
                priority=5,
                description="Detailed desc",
                urgent=True,
                status="hold",
            ),
        ]

        self.interpreter.execute_commands(commands, dry_run=False)

        call_args = mock_run.call_args[0][0]
        assert "Complex task" in call_args
        assert "--type" in call_args
        assert "feature" in call_args
        assert "--priority" in call_args
        assert "5" in call_args
        assert "--description" in call_args
        assert "Detailed desc" in call_args
        assert "--urgent" in call_args
        assert "--status" in call_args
        assert "hold" in call_args


class TestInterpretOutput:
    """Tests for the interpret_output method"""

    def setup_method(self):
        """Set up test interpreter with mocked wrapper"""
        self.interpreter = ToolOutputInterpreter()

    @pytest.mark.asyncio
    async def test_interpret_output_success(self):
        """Test successful interpretation of tool output"""
        # Mock the internal Claude execution
        with patch.object(
            self.interpreter, "_execute_claude_prompt", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = {
                "success": True,
                "output": 'sugar add "Fix bug" --type bug_fix --priority 3',
                "error": "",
                "execution_time": 1.5,
            }

            result = await self.interpreter.interpret_output(
                tool_name="eslint",
                command="eslint src/",
                raw_output="10 problems found",
            )

            assert result.success is True
            assert len(result.commands) == 1
            assert result.commands[0].title == "Fix bug"
            assert result.execution_time == 1.5

    @pytest.mark.asyncio
    async def test_interpret_output_failure(self):
        """Test failed interpretation"""
        with patch.object(
            self.interpreter, "_execute_claude_prompt", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = {
                "success": False,
                "output": "",
                "error": "Claude CLI not available",
                "execution_time": 0.0,
            }

            result = await self.interpreter.interpret_output(
                tool_name="test",
                command="test",
                raw_output="output",
            )

            assert result.success is False
            assert "Claude CLI not available" in result.error_message

    @pytest.mark.asyncio
    async def test_interpret_output_with_custom_template(self):
        """Test interpretation with custom template"""
        custom_template = "Analyze: ${tool_name}\nOutput: ${raw_output}"
        interpreter = ToolOutputInterpreter(prompt_template=custom_template)

        with patch.object(
            interpreter, "_execute_claude_prompt", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = {
                "success": True,
                "output": 'sugar add "Task" --type bug_fix',
                "error": "",
                "execution_time": 1.0,
            }

            await interpreter.interpret_output(
                tool_name="test-tool",
                command="test-cmd",
                raw_output="test output",
            )

            # Verify the prompt was built with custom template
            call_args = mock_exec.call_args[0][0]
            assert "Analyze: test-tool" in call_args
            assert "Output: test output" in call_args

    @pytest.mark.asyncio
    async def test_interpret_output_exception_handling(self):
        """Test exception handling during interpretation"""
        with patch.object(
            self.interpreter, "_execute_claude_prompt", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.side_effect = Exception("Unexpected error")

            result = await self.interpreter.interpret_output(
                tool_name="test",
                command="test",
                raw_output="output",
            )

            assert result.success is False
            assert "Unexpected error" in result.error_message


class TestInterpretAndExecute:
    """Tests for the interpret_and_execute convenience method"""

    def setup_method(self):
        """Set up test interpreter"""
        self.interpreter = ToolOutputInterpreter()

    @pytest.mark.asyncio
    async def test_interpret_and_execute_success(self):
        """Test successful interpretation and execution"""
        with patch.object(
            self.interpreter, "_execute_claude_prompt", new_callable=AsyncMock
        ) as mock_prompt:
            mock_prompt.return_value = {
                "success": True,
                "output": """sugar add "Task 1" --type bug_fix
sugar add "Task 2" --type feature""",
                "error": "",
                "execution_time": 2.0,
            }

            result = await self.interpreter.interpret_and_execute(
                tool_name="eslint",
                command="eslint src/",
                raw_output="20 problems",
                dry_run=True,
            )

            assert result["success"] is True
            assert result["commands_found"] == 2
            assert result["tasks_created"] == 2
            assert result["dry_run"] is True

    @pytest.mark.asyncio
    async def test_interpret_and_execute_interpretation_failure(self):
        """Test handling of interpretation failure"""
        with patch.object(
            self.interpreter, "_execute_claude_prompt", new_callable=AsyncMock
        ) as mock_prompt:
            mock_prompt.return_value = {
                "success": False,
                "output": "",
                "error": "CLI error",
                "execution_time": 0.0,
            }

            result = await self.interpreter.interpret_and_execute(
                tool_name="test",
                command="test",
                raw_output="output",
            )

            assert result["success"] is False
            assert result["tasks_created"] == 0


class TestIntegration:
    """Integration tests that test multiple components together"""

    @pytest.mark.asyncio
    async def test_full_interpretation_flow(self):
        """Test the full flow from raw output to task commands"""
        interpreter = ToolOutputInterpreter()

        # Mock Claude response with realistic output
        mock_response = """Based on the eslint output, I've identified the following tasks:

sugar add "Fix 15 unused-import violations in src/components/" --type refactor --priority 2 --description "Remove unused imports across component files"
sugar add "Fix 5 no-unused-vars warnings in src/utils/" --type refactor --priority 2 --description "Clean up unused variable declarations"
sugar add "Fix 3 prefer-const errors in src/api/" --type bug_fix --priority 3 --description "Convert let declarations to const where appropriate"

These tasks group related issues for efficient resolution."""

        with patch.object(
            interpreter, "_execute_claude_prompt", new_callable=AsyncMock
        ) as mock_prompt:
            mock_prompt.return_value = {
                "success": True,
                "output": mock_response,
                "error": "",
                "execution_time": 5.0,
            }

            result = await interpreter.interpret_and_execute(
                tool_name="eslint",
                command="eslint src/ --format json",
                raw_output='{"errorCount": 23, "warningCount": 15}',
                dry_run=True,
            )

            assert result["success"] is True
            assert result["commands_found"] == 3
            assert result["tasks_created"] == 3

    def test_command_parsing_edge_cases(self):
        """Test command parsing with various edge cases"""
        interpreter = ToolOutputInterpreter()

        test_cases = [
            # Command with escaped quotes in description
            (
                'sugar add "Task" --description "Fix the \\"important\\" bug"',
                True,
                "Task",
            ),
            # Command with multiple spaces
            (
                'sugar add   "Task with spaces"   --type   bug_fix',
                True,
                "Task with spaces",
            ),
            # Empty title
            (
                'sugar add "" --type bug_fix',
                False,
                None,
            ),
        ]

        for cmd_str, expected_valid, expected_title in test_cases:
            cmd = interpreter._parse_command(cmd_str)
            assert cmd.valid == expected_valid, f"Failed for: {cmd_str}"
            if expected_valid:
                assert cmd.title == expected_title, f"Title mismatch for: {cmd_str}"
