"""
Prompt Templates for External Tool Output Interpretation

Sugar has NO knowledge of tool output formats. Claude Code does ALL interpretation.
This module provides configurable prompt templates that instruct Claude Code
to interpret raw output from code quality tools and generate sugar add commands.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from string import Template

logger = logging.getLogger(__name__)


# Default prompt template for tool output interpretation
DEFAULT_TOOL_INTERPRETATION_TEMPLATE = """You are an AI assistant integrated into Sugar, an autonomous development system.
Your task is to interpret raw output from code quality tools and convert it into
Sugar tasks using the 'sugar add' CLI.

## CRITICAL: DO NOT EXECUTE THE TOOL!
The tool has ALREADY been executed. The output is saved to a file.
You MUST read the output from the file path provided below.
NEVER run the tool command yourself - just parse the existing output file.

## Sugar CLI Reference
sugar add [OPTIONS] TITLE
  --type TEXT               Type of task (bug_fix, feature, test, refactor, documentation)
  --priority INTEGER        Priority (1=low, 5=urgent)
  --description TEXT        Detailed description
  --urgent                  Mark as urgent (priority 5)
  --status [pending|hold]   Initial task status

## Tool: ${tool_name}
## Command (already executed): ${command}
## Output File: ${output_file_path}

Read the file at ${output_file_path} to analyze the tool output. DO NOT run the command.

## Your Responsibilities
1. Read and parse the raw tool output from the file (any format: JSON, XML, plain text)
2. Group related issues into logical tasks (NOT one task per warning!)
3. Prioritize based on severity and impact
4. Output executable 'sugar add' shell commands

## Grouping Strategy
Create ONE task for:
- All issues of same rule in same file
- All issues of same rule in same directory (if <10 occurrences)
- Logically connected issues

NEVER create hundreds of individual tasks for lint warnings!
Target: 20-50 tasks max for large codebases.

## Priority Mapping
| Condition                              | Priority |
|----------------------------------------|----------|
| Security vulnerability (Critical/High) | 5        |
| Blocking error / CI failure            | 4        |
| Error (non-blocking)                   | 3        |
| Warning (code smell)                   | 2        |
| Info / style suggestion                | 1        |

## Output Format
Output ONLY executable shell commands, one per line:
sugar add "Fix X issues in Y" --type bug_fix --priority 3 --description "..."

## Important Notes
- Escape special characters in descriptions properly for shell execution
- Keep descriptions concise but informative (max 200 chars)
- Include file paths and line numbers in descriptions when relevant
- Group by logical categories (security, performance, style, etc.)
"""


# Template for security-focused analysis
SECURITY_ANALYSIS_TEMPLATE = """You are a security-focused AI assistant integrated into Sugar.
Your task is to interpret security scan output and create prioritized remediation tasks.

## CRITICAL: DO NOT EXECUTE THE TOOL!
The security scan has ALREADY been executed. The output is saved to a file.
You MUST read the output from the file path provided below.
NEVER run the tool command yourself - just parse the existing output file.

## Sugar CLI Reference
sugar add [OPTIONS] TITLE
  --type TEXT               Type of task (bug_fix, feature, test, refactor, documentation)
  --priority INTEGER        Priority (1=low, 5=urgent)
  --description TEXT        Detailed description
  --urgent                  Mark as urgent (priority 5)
  --status [pending|hold]   Initial task status

## Security Tool: ${tool_name}
## Command (already executed): ${command}
## Output File: ${output_file_path}

Read the file at ${output_file_path} to analyze the security scan output. DO NOT run the command.

## Security Priority Mapping
| Severity      | CVSS Score | Priority |
|---------------|------------|----------|
| Critical      | 9.0-10.0   | 5        |
| High          | 7.0-8.9    | 4        |
| Medium        | 4.0-6.9    | 3        |
| Low           | 0.1-3.9    | 2        |
| Informational | 0.0        | 1        |

## Grouping Rules for Security Issues
- Group by vulnerability type (e.g., all SQL injection issues together)
- Group by affected component/library
- Keep critical vulnerabilities as separate tasks for immediate attention
- Combine informational findings into single review task

## Output Format
Output ONLY executable shell commands, one per line:
sugar add "Fix [CRITICAL] SQL injection in auth module" --type bug_fix --priority 5 --urgent --description "..."

## Important Notes
- Always include severity level in task title
- Include CVE IDs when available
- Reference affected files/functions in description
- For dependency vulnerabilities, include upgrade path if known
"""


# Template for test coverage analysis
TEST_COVERAGE_TEMPLATE = """You are a test coverage AI assistant integrated into Sugar.
Your task is to interpret test coverage reports and create tasks for improving coverage.

## CRITICAL: DO NOT EXECUTE THE TOOL!
The coverage report has ALREADY been generated. The output is saved to a file.
You MUST read the output from the file path provided below.
NEVER run the tool command yourself - just parse the existing output file.

## Sugar CLI Reference
sugar add [OPTIONS] TITLE
  --type TEXT               Type of task (bug_fix, feature, test, refactor, documentation)
  --priority INTEGER        Priority (1=low, 5=urgent)
  --description TEXT        Detailed description
  --urgent                  Mark as urgent (priority 5)
  --status [pending|hold]   Initial task status

## Coverage Tool: ${tool_name}
## Command (already executed): ${command}
## Output File: ${output_file_path}

Read the file at ${output_file_path} to analyze the coverage report. DO NOT run the command.

## Coverage Priority Mapping
| Coverage Level | Priority |
|----------------|----------|
| 0-25%          | 4        |
| 26-50%         | 3        |
| 51-75%         | 2        |
| 76-100%        | 1        |

## Grouping Strategy
- Group uncovered files by module/package
- Prioritize critical business logic over utilities
- Create separate tasks for unit tests vs integration tests
- Target 5-15 test tasks max

## Output Format
Output ONLY executable shell commands, one per line:
sugar add "Add unit tests for auth module (45% coverage)" --type test --priority 3 --description "..."

## Important Notes
- Focus on files with business logic, not boilerplate
- Mention specific uncovered functions/methods
- Consider complexity when prioritizing
"""


# Template for linting/style analysis
LINT_ANALYSIS_TEMPLATE = """You are a code quality AI assistant integrated into Sugar.
Your task is to interpret linter output and create actionable improvement tasks.

## CRITICAL: DO NOT EXECUTE THE TOOL!
The linter has ALREADY been executed. The output is saved to a file.
You MUST read the output from the file path provided below.
NEVER run the tool command yourself - just parse the existing output file.

## Sugar CLI Reference
sugar add [OPTIONS] TITLE
  --type TEXT               Type of task (bug_fix, feature, test, refactor, documentation)
  --priority INTEGER        Priority (1=low, 5=urgent)
  --description TEXT        Detailed description
  --urgent                  Mark as urgent (priority 5)
  --status [pending|hold]   Initial task status

## Linter: ${tool_name}
## Command (already executed): ${command}
## Output File: ${output_file_path}

Read the file at ${output_file_path} to analyze the linter output. DO NOT run the command.

## Lint Priority Mapping
| Category                    | Priority |
|-----------------------------|----------|
| Error / Likely bug          | 4        |
| Warning / Code smell        | 3        |
| Style / Formatting          | 2        |
| Info / Suggestion           | 1        |

## Aggressive Grouping Rules (IMPORTANT!)
- Group ALL issues of same rule into ONE task
- Create directory-level tasks for widespread issues
- NEVER create more than 30 tasks from lint output
- Combine related rules (e.g., all naming issues together)

## Output Format
Output ONLY executable shell commands, one per line:
sugar add "Fix 47 'unused-import' violations across src/" --type refactor --priority 2 --description "..."

## Important Notes
- Count occurrences in task title
- Mention affected directories, not every file
- Consider using --status hold for low-priority style issues
- For auto-fixable issues, mention that in description
"""


class PromptTemplateManager:
    """Manages prompt templates for tool output interpretation"""

    # Built-in template types
    TEMPLATE_TYPES = {
        "default": DEFAULT_TOOL_INTERPRETATION_TEMPLATE,
        "security": SECURITY_ANALYSIS_TEMPLATE,
        "coverage": TEST_COVERAGE_TEMPLATE,
        "lint": LINT_ANALYSIS_TEMPLATE,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the prompt template manager.

        Args:
            config: Optional configuration dict with:
                - templates_dir: Custom templates directory
                - default_template: Default template type or path
                - custom_templates: Dict of template_name -> template_string
        """
        self.config = config or {}
        self.templates_dir = self._get_templates_dir()
        self.custom_templates: Dict[str, str] = self.config.get("custom_templates", {})
        self._load_custom_templates()

    def _get_templates_dir(self) -> Path:
        """Get the templates directory path"""
        # Check config for custom path
        if "templates_dir" in self.config:
            custom_path = Path(self.config["templates_dir"])
            if custom_path.exists():
                return custom_path

        # Default locations (in order of preference)
        default_locations = [
            Path(".sugar/templates"),
            Path.home() / ".sugar" / "templates",
            Path(__file__).parent / "templates",
        ]

        for location in default_locations:
            if location.exists():
                return location

        # Create default location if none exists
        default_location = Path(".sugar/templates")
        default_location.mkdir(parents=True, exist_ok=True)
        return default_location

    def _load_custom_templates(self) -> None:
        """Load custom templates from templates directory"""
        if not self.templates_dir.exists():
            return

        for template_file in self.templates_dir.glob("*.txt"):
            template_name = template_file.stem
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    self.custom_templates[template_name] = f.read()
                logger.debug(f"Loaded custom template: {template_name}")
            except Exception as e:
                logger.warning(f"Failed to load template {template_file}: {e}")

        for template_file in self.templates_dir.glob("*.md"):
            template_name = template_file.stem
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    self.custom_templates[template_name] = f.read()
                logger.debug(f"Loaded custom template: {template_name}")
            except Exception as e:
                logger.warning(f"Failed to load template {template_file}: {e}")

    def get_template(
        self,
        template_type: str = "default",
        tool_name: str = "",
        command: str = "",
        output_file_path: Optional[Path] = None,
    ) -> str:
        """
        Get a prompt template with variables substituted.

        Args:
            template_type: Type of template (default, security, coverage, lint) or custom name
            tool_name: Name of the tool that generated the output
            command: The command that was executed
            output_file_path: Path to the file containing the tool output

        Returns:
            Rendered prompt template string
        """
        # Get base template
        template_str = self._get_base_template(template_type)

        # Use string.Template for safe substitution
        template = Template(template_str)

        # Convert Path to string for template substitution
        output_path_str = str(output_file_path) if output_file_path else ""

        try:
            return template.safe_substitute(
                tool_name=tool_name,
                command=command,
                output_file_path=output_path_str,
            )
        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            # Return template with placeholders if substitution fails
            return template_str

    def _get_base_template(self, template_type: str) -> str:
        """Get the base template string for a given type"""
        # Check custom templates first
        if template_type in self.custom_templates:
            return self.custom_templates[template_type]

        # Check built-in templates
        if template_type in self.TEMPLATE_TYPES:
            return self.TEMPLATE_TYPES[template_type]

        # Fall back to default
        logger.warning(f"Unknown template type '{template_type}', using default")
        return self.TEMPLATE_TYPES["default"]

    def list_available_templates(self) -> Dict[str, str]:
        """
        List all available templates with their descriptions.

        Returns:
            Dict mapping template name to first line (description)
        """
        templates = {}

        # Built-in templates
        for name, content in self.TEMPLATE_TYPES.items():
            first_line = content.strip().split("\n")[0]
            templates[f"builtin:{name}"] = first_line

        # Custom templates
        for name, content in self.custom_templates.items():
            first_line = content.strip().split("\n")[0]
            templates[f"custom:{name}"] = first_line

        return templates

    def save_custom_template(
        self,
        name: str,
        content: str,
        overwrite: bool = False,
    ) -> bool:
        """
        Save a custom template to the templates directory.

        Args:
            name: Template name (without extension)
            content: Template content
            overwrite: Whether to overwrite existing template

        Returns:
            True if saved successfully, False otherwise
        """
        template_path = self.templates_dir / f"{name}.txt"

        if template_path.exists() and not overwrite:
            logger.warning(
                f"Template '{name}' already exists. Use overwrite=True to replace."
            )
            return False

        try:
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            with open(template_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.custom_templates[name] = content
            logger.info(f"Saved custom template: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save template '{name}': {e}")
            return False

    def delete_custom_template(self, name: str) -> bool:
        """
        Delete a custom template.

        Args:
            name: Template name to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        template_path = self.templates_dir / f"{name}.txt"

        if not template_path.exists():
            template_path = self.templates_dir / f"{name}.md"

        if not template_path.exists():
            logger.warning(f"Template '{name}' not found")
            return False

        try:
            template_path.unlink()
            if name in self.custom_templates:
                del self.custom_templates[name]
            logger.info(f"Deleted custom template: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete template '{name}': {e}")
            return False

    def get_template_for_tool(self, tool_name: str) -> str:
        """
        Get the appropriate template type based on tool name.

        Args:
            tool_name: Name of the tool (e.g., 'eslint', 'bandit', 'pytest-cov')

        Returns:
            Template type to use
        """
        tool_lower = tool_name.lower()

        # Security tools
        security_tools = [
            "bandit",
            "snyk",
            "npm audit",
            "safety",
            "trivy",
            "grype",
            "semgrep",
            "sonarqube",
            "checkmarx",
            "fortify",
            "dependency-check",
            "retire",
            "audit",
        ]
        if any(sec_tool in tool_lower for sec_tool in security_tools):
            return "security"

        # Coverage tools
        coverage_tools = [
            "coverage",
            "pytest-cov",
            "istanbul",
            "nyc",
            "codecov",
            "jacoco",
            "cobertura",
            "lcov",
        ]
        if any(cov_tool in tool_lower for cov_tool in coverage_tools):
            return "coverage"

        # Linting tools
        lint_tools = [
            "eslint",
            "pylint",
            "flake8",
            "ruff",
            "mypy",
            "tsc",
            "prettier",
            "black",
            "stylelint",
            "rubocop",
            "golint",
            "clippy",
            "shellcheck",
            "hadolint",
        ]
        if any(lint_tool in tool_lower for lint_tool in lint_tools):
            return "lint"

        # Check for custom template matching tool name
        if tool_lower in self.custom_templates:
            return tool_lower

        return "default"


def create_tool_interpretation_prompt(
    tool_name: str,
    command: str,
    output_file_path: Path,
    template_type: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a prompt for Claude Code to interpret tool output.

    This is the main entry point for generating prompts.

    Args:
        tool_name: Name of the tool that generated the output
        command: The command that was executed
        output_file_path: Path to the file containing the tool output
        template_type: Optional specific template type (auto-detected if not provided)
        config: Optional configuration for template manager

    Returns:
        Complete prompt string for Claude Code
    """
    manager = PromptTemplateManager(config)

    # Auto-detect template type if not specified
    if template_type is None:
        template_type = manager.get_template_for_tool(tool_name)

    return manager.get_template(
        template_type=template_type,
        tool_name=tool_name,
        command=command,
        output_file_path=output_file_path,
    )


# Export key components
__all__ = [
    "PromptTemplateManager",
    "create_tool_interpretation_prompt",
    "DEFAULT_TOOL_INTERPRETATION_TEMPLATE",
    "SECURITY_ANALYSIS_TEMPLATE",
    "TEST_COVERAGE_TEMPLATE",
    "LINT_ANALYSIS_TEMPLATE",
]
