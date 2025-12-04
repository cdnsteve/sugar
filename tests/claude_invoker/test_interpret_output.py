"""
Tests for the interpret_output and interpret_and_execute methods.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

from sugar.quality.claude_invoker import ToolOutputInterpreter


class TestInterpretOutput:
    """Tests for the interpret_output method"""

    def setup_method(self):
        """Set up test interpreter with mocked wrapper"""
        self.interpreter = ToolOutputInterpreter()
        # Create a temp file for testing
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        )
        self.temp_file.write("10 problems found")
        self.temp_file.close()
        self.output_path = Path(self.temp_file.name)

    def teardown_method(self):
        """Clean up temp files"""
        if self.output_path.exists():
            self.output_path.unlink()

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
                output_file_path=self.output_path,
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
                output_file_path=self.output_path,
            )

            assert result.success is False
            assert "Claude CLI not available" in result.error_message

    @pytest.mark.asyncio
    async def test_interpret_output_with_custom_template(self):
        """Test interpretation with custom template"""
        custom_template = "Analyze: ${tool_name}\nOutput file: ${output_file_path}"
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
                output_file_path=self.output_path,
            )

            # Verify the prompt was built with custom template
            call_args = mock_exec.call_args[0][0]
            assert "Analyze: test-tool" in call_args
            assert str(self.output_path) in call_args

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
                output_file_path=self.output_path,
            )

            assert result.success is False
            assert "Unexpected error" in result.error_message


class TestInterpretAndExecute:
    """Tests for the interpret_and_execute convenience method"""

    def setup_method(self):
        """Set up test interpreter"""
        self.interpreter = ToolOutputInterpreter()
        # Create a temp file for testing
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        )
        self.temp_file.write("20 problems")
        self.temp_file.close()
        self.output_path = Path(self.temp_file.name)

    def teardown_method(self):
        """Clean up temp files"""
        if self.output_path.exists():
            self.output_path.unlink()

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
                output_file_path=self.output_path,
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
                output_file_path=self.output_path,
            )

            assert result["success"] is False
            assert result["tasks_created"] == 0
