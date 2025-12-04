"""
Integration tests that test multiple components together.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

from sugar.quality.claude_invoker import ToolOutputInterpreter


class TestIntegration:
    """Integration tests that test multiple components together"""

    def setup_method(self):
        """Set up temp file for testing"""
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        self.temp_file.write('{"errorCount": 23, "warningCount": 15}')
        self.temp_file.close()
        self.output_path = Path(self.temp_file.name)

    def teardown_method(self):
        """Clean up temp files"""
        if self.output_path.exists():
            self.output_path.unlink()

    @pytest.mark.asyncio
    async def test_full_interpretation_flow(self):
        """Test the full flow from output file path to task commands"""
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
                output_file_path=self.output_path,
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
