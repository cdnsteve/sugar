"""
Claude Invoker - Send tool output to Claude Code for interpretation

This module reuses the existing ClaudeWrapper to send external tool output
to Claude Code for interpretation and automatic task generation.
"""

import asyncio
import logging
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from ..executor.claude_wrapper import ClaudeWrapper
from ..discovery.prompt_templates import create_tool_interpretation_prompt

logger = logging.getLogger(__name__)


@dataclass
class ParsedCommand:
    """A parsed sugar add command"""

    title: str
    task_type: str = "bug_fix"
    priority: int = 3
    description: str = ""
    urgent: bool = False
    status: str = "pending"
    raw_command: str = ""
    valid: bool = True
    validation_error: str = ""


@dataclass
class InterpretationResult:
    """Result of interpreting tool output"""

    success: bool
    commands: List[ParsedCommand] = field(default_factory=list)
    raw_response: str = ""
    error_message: str = ""
    execution_time: float = 0.0


class ToolOutputInterpreter:
    """
    Interprets external tool output using Claude Code.

    Uses the existing ClaudeWrapper to send tool output to Claude Code,
    which interprets the output and generates sugar add commands.
    """

    def __init__(
        self,
        prompt_template: Optional[str] = None,
        wrapper_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the interpreter.

        Args:
            prompt_template: Optional custom prompt template. If not provided,
                           uses the default from prompt_templates module.
            wrapper_config: Configuration dict for ClaudeWrapper. If not provided,
                          uses sensible defaults.
        """
        # Default wrapper config for tool interpretation
        default_config = {
            "command": "claude",
            "timeout": 300,  # 5 minutes for interpretation
            "context_file": ".sugar/claude_interpreter_context.json",
            "use_continuous": False,  # Fresh session for each interpretation
            "use_structured_requests": False,  # Use simple prompts
            "enable_agents": False,  # No agent selection needed
            "dry_run": False,  # Actually execute
        }

        if wrapper_config:
            default_config.update(wrapper_config)

        self.wrapper = ClaudeWrapper(default_config)
        self.custom_template = prompt_template
        logger.debug("ToolOutputInterpreter initialized with ClaudeWrapper")

    async def interpret_output(
        self,
        tool_name: str,
        command: str,
        raw_output: str,
        template_type: Optional[str] = None,
    ) -> InterpretationResult:
        """
        Send tool output to Claude Code for interpretation.

        Args:
            tool_name: Name of the tool that generated the output
            command: The command that was executed
            raw_output: The raw output from the tool
            template_type: Optional template type (default, security, coverage, lint)

        Returns:
            InterpretationResult containing parsed sugar add commands
        """
        logger.info(f"Interpreting output from tool: {tool_name}")

        # Build prompt from template
        if self.custom_template:
            # Use custom template with simple substitution
            prompt = self.custom_template.replace("${tool_name}", tool_name)
            prompt = prompt.replace("${command}", command)
            prompt = prompt.replace("${raw_output}", raw_output)
        else:
            # Use the standard template manager
            prompt = create_tool_interpretation_prompt(
                tool_name=tool_name,
                command=command,
                raw_output=raw_output,
                template_type=template_type,
            )

        # Execute via Claude wrapper
        try:
            result = await self._execute_claude_prompt(prompt)

            if not result.get("success", False):
                return InterpretationResult(
                    success=False,
                    error_message=result.get(
                        "error", "Unknown error during interpretation"
                    ),
                    raw_response=result.get("output", ""),
                    execution_time=result.get("execution_time", 0.0),
                )

            # Extract sugar add commands from response
            raw_response = result.get("output", "")
            commands = self._extract_commands(raw_response)

            logger.info(
                f"Extracted {len(commands)} valid commands from Claude response"
            )

            return InterpretationResult(
                success=True,
                commands=commands,
                raw_response=raw_response,
                execution_time=result.get("execution_time", 0.0),
            )

        except Exception as e:
            logger.error(f"Error interpreting tool output: {e}")
            return InterpretationResult(
                success=False,
                error_message=str(e),
            )

    async def _execute_claude_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Execute a prompt via the Claude wrapper.

        Args:
            prompt: The prompt to send to Claude

        Returns:
            Dict with success, output, error, execution_time keys
        """
        # Create a minimal work item for the wrapper
        work_item = {
            "id": "interpreter-task",
            "type": "interpretation",
            "title": "Tool Output Interpretation",
            "description": prompt,
            "priority": 3,
            "source": "tool_interpreter",
        }

        # Use legacy execution path for simple prompt execution
        try:
            # Access the internal CLI execution method
            context = self.wrapper._prepare_context(work_item, continue_session=False)
            result = await self.wrapper._execute_claude_cli(
                prompt, context, continue_session=False
            )

            return {
                "success": result.get("success", False),
                "output": result.get("stdout", ""),
                "error": result.get("stderr", ""),
                "execution_time": result.get("execution_time", 0.0),
            }

        except Exception as e:
            logger.error(f"Claude CLI execution failed: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "execution_time": 0.0,
            }

    def _extract_commands(self, response: str) -> List[ParsedCommand]:
        """
        Extract sugar add commands from Claude's response.

        Args:
            response: The raw response from Claude

        Returns:
            List of ParsedCommand objects
        """
        commands = []
        lines = response.split("\n")

        for line in lines:
            line = line.strip()

            # Skip empty lines and non-command lines
            if not line:
                continue

            # Look for lines starting with "sugar add"
            if line.startswith("sugar add "):
                parsed = self._parse_command(line)
                if parsed.valid:
                    commands.append(parsed)
                else:
                    logger.warning(
                        f"Skipping malformed command: {line} - {parsed.validation_error}"
                    )

        return commands

    def _parse_command(self, command_line: str) -> ParsedCommand:
        """
        Parse a sugar add command line into its components.

        Args:
            command_line: The full command line (e.g., 'sugar add "Fix bug" --type bug_fix')

        Returns:
            ParsedCommand with parsed components
        """
        parsed = ParsedCommand(title="", raw_command=command_line)

        try:
            # Use shlex to properly handle quoted strings
            parts = shlex.split(command_line)
        except ValueError as e:
            parsed.valid = False
            parsed.validation_error = f"Failed to parse command: {e}"
            return parsed

        if len(parts) < 3 or parts[0] != "sugar" or parts[1] != "add":
            parsed.valid = False
            parsed.validation_error = "Command must start with 'sugar add'"
            return parsed

        # Extract positional argument (title)
        # The title should be the first non-option argument after "sugar add"
        i = 2
        title = None

        while i < len(parts):
            if parts[i].startswith("--"):
                # Process option
                option = parts[i][2:]

                if option == "urgent":
                    parsed.urgent = True
                    i += 1
                elif option in ("type", "priority", "description", "status"):
                    if i + 1 >= len(parts):
                        parsed.valid = False
                        parsed.validation_error = f"Option --{option} requires a value"
                        return parsed

                    value = parts[i + 1]
                    if option == "type":
                        parsed.task_type = value
                    elif option == "priority":
                        try:
                            parsed.priority = int(value)
                        except ValueError:
                            parsed.valid = False
                            parsed.validation_error = (
                                f"Priority must be an integer, got: {value}"
                            )
                            return parsed
                    elif option == "description":
                        parsed.description = value
                    elif option == "status":
                        if value not in ("pending", "hold"):
                            parsed.valid = False
                            parsed.validation_error = (
                                f"Status must be 'pending' or 'hold', got: {value}"
                            )
                            return parsed
                        parsed.status = value

                    i += 2
                else:
                    # Unknown option, skip
                    logger.debug(f"Unknown option: --{option}")
                    i += 1
            else:
                # Positional argument (title)
                if title is None:
                    title = parts[i]
                i += 1

        if not title:
            parsed.valid = False
            parsed.validation_error = "Command must have a title"
            return parsed

        parsed.title = title
        return parsed

    def execute_commands(
        self,
        commands: List[ParsedCommand],
        dry_run: bool = False,
    ) -> int:
        """
        Execute sugar add commands to create tasks.

        Args:
            commands: List of ParsedCommand objects to execute
            dry_run: If True, only log commands without executing

        Returns:
            Count of successfully created tasks
        """
        successful = 0

        for cmd in commands:
            if not cmd.valid:
                logger.warning(f"Skipping invalid command: {cmd.validation_error}")
                continue

            # Build the command
            args = ["sugar", "add", cmd.title]

            if cmd.task_type:
                args.extend(["--type", cmd.task_type])
            if cmd.priority:
                args.extend(["--priority", str(cmd.priority)])
            if cmd.description:
                args.extend(["--description", cmd.description])
            if cmd.urgent:
                args.append("--urgent")
            if cmd.status and cmd.status != "pending":
                args.extend(["--status", cmd.status])

            if dry_run:
                logger.info(f"[DRY RUN] Would execute: {' '.join(args)}")
                successful += 1
                continue

            try:
                result = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    logger.info(f"Created task: {cmd.title}")
                    successful += 1
                else:
                    logger.error(
                        f"Failed to create task '{cmd.title}': {result.stderr}"
                    )

            except subprocess.TimeoutExpired:
                logger.error(f"Timeout creating task: {cmd.title}")
            except Exception as e:
                logger.error(f"Error creating task '{cmd.title}': {e}")

        logger.info(f"Successfully created {successful}/{len(commands)} tasks")
        return successful

    async def interpret_and_execute(
        self,
        tool_name: str,
        command: str,
        raw_output: str,
        template_type: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Convenience method to interpret tool output and execute commands in one call.

        Args:
            tool_name: Name of the tool that generated the output
            command: The command that was executed
            raw_output: The raw output from the tool
            template_type: Optional template type
            dry_run: If True, don't actually create tasks

        Returns:
            Dict with interpretation result and execution count
        """
        result = await self.interpret_output(
            tool_name, command, raw_output, template_type
        )

        if not result.success:
            return {
                "success": False,
                "error": result.error_message,
                "tasks_created": 0,
                "commands_found": 0,
            }

        tasks_created = self.execute_commands(result.commands, dry_run=dry_run)

        return {
            "success": True,
            "tasks_created": tasks_created,
            "commands_found": len(result.commands),
            "execution_time": result.execution_time,
            "dry_run": dry_run,
        }


# Export key components
__all__ = [
    "ToolOutputInterpreter",
    "ParsedCommand",
    "InterpretationResult",
]
