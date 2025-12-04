"""
External Tool Configuration - Schema validation and management for external code quality tools

This module provides configuration parsing and validation for external tools
defined in the code_quality.external_tools section of the Sugar configuration.
"""

import os
import re
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ExternalToolConfigError(Exception):
    """Raised when external tool configuration is invalid"""

    pass


@dataclass
class ExternalToolConfig:
    """Configuration for a single external code quality tool"""

    name: str
    command: str

    def get_expanded_command(self) -> str:
        """Return command with environment variables expanded"""
        return expand_env_vars(self.command)


def expand_env_vars(command: str) -> str:
    """
    Expand environment variables in a command string.

    Supports both $VAR and ${VAR} syntax.
    Undefined variables are left as-is with a warning.

    Args:
        command: Command string potentially containing environment variables

    Returns:
        Command string with environment variables expanded
    """
    # Pattern to match $VAR or ${VAR}
    pattern = r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?"

    def replace_var(match):
        var_name = match.group(1)
        value = os.environ.get(var_name)
        if value is None:
            logger.warning(
                f"Environment variable '{var_name}' is not set, "
                f"leaving '{match.group(0)}' unexpanded"
            )
            return match.group(0)
        return value

    return re.sub(pattern, replace_var, command)


def validate_external_tool(
    tool_config: Dict[str, Any], index: int
) -> ExternalToolConfig:
    """
    Validate a single external tool configuration entry.

    Args:
        tool_config: Dictionary containing tool configuration
        index: Index in the external_tools list (for error messages)

    Returns:
        Validated ExternalToolConfig object

    Raises:
        ExternalToolConfigError: If configuration is invalid
    """
    if not isinstance(tool_config, dict):
        raise ExternalToolConfigError(
            f"external_tools[{index}]: Expected dictionary, got {type(tool_config).__name__}"
        )

    # Validate 'name' field
    name = tool_config.get("name")
    if name is None:
        raise ExternalToolConfigError(
            f"external_tools[{index}]: Missing required field 'name'"
        )
    if not isinstance(name, str):
        raise ExternalToolConfigError(
            f"external_tools[{index}]: Field 'name' must be a string, got {type(name).__name__}"
        )
    if not name.strip():
        raise ExternalToolConfigError(
            f"external_tools[{index}]: Field 'name' cannot be empty"
        )

    # Validate 'command' field
    command = tool_config.get("command")
    if command is None:
        raise ExternalToolConfigError(
            f"external_tools[{index}]: Missing required field 'command' for tool '{name}'"
        )
    if not isinstance(command, str):
        raise ExternalToolConfigError(
            f"external_tools[{index}]: Field 'command' must be a string for tool '{name}', "
            f"got {type(command).__name__}"
        )
    if not command.strip():
        raise ExternalToolConfigError(
            f"external_tools[{index}]: Field 'command' cannot be empty for tool '{name}'"
        )

    return ExternalToolConfig(name=name.strip(), command=command.strip())


def validate_external_tools_config(
    config: Optional[List[Dict[str, Any]]],
) -> List[ExternalToolConfig]:
    """
    Validate the external_tools configuration array.

    Args:
        config: The external_tools configuration list from YAML

    Returns:
        List of validated ExternalToolConfig objects

    Raises:
        ExternalToolConfigError: If configuration is invalid
    """
    if config is None:
        return []

    if not isinstance(config, list):
        raise ExternalToolConfigError(
            f"external_tools: Expected list, got {type(config).__name__}"
        )

    validated_tools = []
    seen_names = set()

    for index, tool_config in enumerate(config):
        tool = validate_external_tool(tool_config, index)

        # Check for duplicate names
        if tool.name.lower() in seen_names:
            raise ExternalToolConfigError(
                f"external_tools[{index}]: Duplicate tool name '{tool.name}'"
            )
        seen_names.add(tool.name.lower())

        validated_tools.append(tool)
        logger.debug(f"Validated external tool: {tool.name}")

    return validated_tools


def parse_external_tools_from_code_quality_config(
    code_quality_config: Dict[str, Any],
) -> List[ExternalToolConfig]:
    """
    Parse and validate external_tools from the code_quality configuration section.

    Args:
        code_quality_config: The code_quality section of the Sugar configuration

    Returns:
        List of validated ExternalToolConfig objects

    Raises:
        ExternalToolConfigError: If configuration is invalid
    """
    external_tools = code_quality_config.get("external_tools")
    return validate_external_tools_config(external_tools)


def get_external_tools_config_schema() -> str:
    """
    Return the YAML schema documentation for external_tools configuration.

    Returns:
        String containing YAML schema documentation
    """
    return """
# External Tools Configuration Schema
#
# Add under code_quality section in your sugar configuration:
#
# code_quality:
#   external_tools:
#     - name: string        # Tool identifier (required)
#       command: string     # Shell command to execute (required)
#
# Environment variables in commands are expanded at runtime.
# Supported syntax: $VAR or ${VAR}
#
# Example:
#   code_quality:
#     external_tools:
#       - name: eslint
#         command: "npx eslint . --format json"
#       - name: phpstan
#         command: "vendor/bin/phpstan analyse --error-format=json"
#       - name: ruff
#         command: "ruff check . --output-format json"
#       - name: sonarqube
#         command: "sonar-scanner -Dsonar.token=$SONAR_TOKEN"
"""
