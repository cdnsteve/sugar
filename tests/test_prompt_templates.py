"""
Tests for Prompt Templates Module

Tests the prompt template functionality for tool output interpretation.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from sugar.discovery.prompt_templates import (
    PromptTemplateManager,
    create_tool_interpretation_prompt,
    DEFAULT_TOOL_INTERPRETATION_TEMPLATE,
    SECURITY_ANALYSIS_TEMPLATE,
    TEST_COVERAGE_TEMPLATE,
    LINT_ANALYSIS_TEMPLATE,
)


# Helper to create temp output files for tests
def create_temp_output_file(content: str = "test output") -> Path:
    """Create a temporary file with given content and return its path."""
    import tempfile

    fd, path = tempfile.mkstemp(suffix=".txt")
    with open(fd, "w") as f:
        f.write(content)
    return Path(path)


class TestPromptTemplateManager:
    """Tests for PromptTemplateManager class"""

    def test_init_default_config(self):
        """Test initialization with default configuration"""
        manager = PromptTemplateManager()
        assert manager.config == {}
        assert isinstance(manager.templates_dir, Path)

    def test_init_custom_config(self):
        """Test initialization with custom configuration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"templates_dir": tmpdir}
            manager = PromptTemplateManager(config)
            assert manager.templates_dir == Path(tmpdir)

    def test_get_builtin_default_template(self):
        """Test getting the default built-in template"""
        output_file = Path("/tmp/test_output.txt")
        manager = PromptTemplateManager()
        template = manager.get_template(
            template_type="default",
            tool_name="test-tool",
            command="test-cmd",
            output_file_path=output_file,
        )

        assert "test-tool" in template
        assert "test-cmd" in template
        assert "/tmp/test_output.txt" in template
        assert "sugar add" in template
        assert "Read the file at" in template

    def test_get_builtin_security_template(self):
        """Test getting the security template"""
        output_file = Path("/tmp/security_output.txt")
        manager = PromptTemplateManager()
        template = manager.get_template(
            template_type="security",
            tool_name="bandit",
            command="bandit -r src/",
            output_file_path=output_file,
        )

        assert "bandit" in template
        assert "Security Priority Mapping" in template
        assert "CVSS Score" in template
        assert "/tmp/security_output.txt" in template

    def test_get_builtin_coverage_template(self):
        """Test getting the coverage template"""
        output_file = Path("/tmp/coverage_output.txt")
        manager = PromptTemplateManager()
        template = manager.get_template(
            template_type="coverage",
            tool_name="pytest-cov",
            command="pytest --cov=src",
            output_file_path=output_file,
        )

        assert "pytest-cov" in template
        assert "Coverage Priority Mapping" in template
        assert "/tmp/coverage_output.txt" in template

    def test_get_builtin_lint_template(self):
        """Test getting the lint template"""
        output_file = Path("/tmp/lint_output.txt")
        manager = PromptTemplateManager()
        template = manager.get_template(
            template_type="lint",
            tool_name="eslint",
            command="eslint src/",
            output_file_path=output_file,
        )

        assert "eslint" in template
        assert "Aggressive Grouping Rules" in template
        assert "/tmp/lint_output.txt" in template

    def test_get_unknown_template_falls_back_to_default(self):
        """Test that unknown template type falls back to default"""
        output_file = Path("/tmp/unknown_output.txt")
        manager = PromptTemplateManager()
        template = manager.get_template(
            template_type="nonexistent",
            tool_name="test",
            command="test",
            output_file_path=output_file,
        )

        # Should contain default template content
        assert "sugar add" in template
        assert "Grouping Strategy" in template

    def test_template_variable_substitution(self):
        """Test that template variables are properly substituted"""
        output_file = Path("/tmp/custom_output.txt")
        manager = PromptTemplateManager()
        template = manager.get_template(
            template_type="default",
            tool_name="my-custom-tool",
            command="my-custom-command --verbose",
            output_file_path=output_file,
        )

        assert "my-custom-tool" in template
        assert "my-custom-command --verbose" in template
        assert "/tmp/custom_output.txt" in template

    def test_list_available_templates(self):
        """Test listing all available templates"""
        manager = PromptTemplateManager()
        templates = manager.list_available_templates()

        # Should have all built-in templates
        assert "builtin:default" in templates
        assert "builtin:security" in templates
        assert "builtin:coverage" in templates
        assert "builtin:lint" in templates

    def test_save_and_load_custom_template(self):
        """Test saving and loading a custom template"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"templates_dir": tmpdir}
            manager = PromptTemplateManager(config)

            custom_content = """Custom template for ${tool_name}
Output File: ${output_file_path}
Command: ${command}
"""

            # Save custom template
            success = manager.save_custom_template("my_custom", custom_content)
            assert success is True
            assert "my_custom" in manager.custom_templates

            # Get the custom template
            output_file = Path("/tmp/custom.txt")
            rendered = manager.get_template(
                template_type="my_custom",
                tool_name="test",
                command="cmd",
                output_file_path=output_file,
            )

            assert "Custom template for test" in rendered
            assert "Output File: /tmp/custom.txt" in rendered

    def test_save_custom_template_no_overwrite(self):
        """Test that saving won't overwrite existing template by default"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"templates_dir": tmpdir}
            manager = PromptTemplateManager(config)

            manager.save_custom_template("test", "Original content")
            success = manager.save_custom_template(
                "test", "New content", overwrite=False
            )

            assert success is False
            assert manager.custom_templates["test"] == "Original content"

    def test_save_custom_template_with_overwrite(self):
        """Test that saving can overwrite existing template when specified"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"templates_dir": tmpdir}
            manager = PromptTemplateManager(config)

            manager.save_custom_template("test", "Original content")
            success = manager.save_custom_template(
                "test", "New content", overwrite=True
            )

            assert success is True
            assert manager.custom_templates["test"] == "New content"

    def test_delete_custom_template(self):
        """Test deleting a custom template"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"templates_dir": tmpdir}
            manager = PromptTemplateManager(config)

            manager.save_custom_template("to_delete", "Content to delete")
            assert "to_delete" in manager.custom_templates

            success = manager.delete_custom_template("to_delete")
            assert success is True
            assert "to_delete" not in manager.custom_templates

    def test_delete_nonexistent_template(self):
        """Test deleting a template that doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"templates_dir": tmpdir}
            manager = PromptTemplateManager(config)

            success = manager.delete_custom_template("nonexistent")
            assert success is False


class TestToolTypeDetection:
    """Tests for automatic tool type detection"""

    def test_detect_security_tools(self):
        """Test detection of security analysis tools"""
        manager = PromptTemplateManager()

        security_tools = [
            "bandit",
            "snyk",
            "npm audit",
            "safety",
            "trivy",
            "semgrep",
        ]

        for tool in security_tools:
            template_type = manager.get_template_for_tool(tool)
            assert template_type == "security", f"Expected 'security' for {tool}"

    def test_detect_coverage_tools(self):
        """Test detection of coverage tools"""
        manager = PromptTemplateManager()

        coverage_tools = [
            "coverage",
            "pytest-cov",
            "istanbul",
            "nyc",
            "codecov",
            "jacoco",
        ]

        for tool in coverage_tools:
            template_type = manager.get_template_for_tool(tool)
            assert template_type == "coverage", f"Expected 'coverage' for {tool}"

    def test_detect_lint_tools(self):
        """Test detection of linting tools"""
        manager = PromptTemplateManager()

        lint_tools = [
            "eslint",
            "pylint",
            "flake8",
            "ruff",
            "mypy",
            "prettier",
            "black",
        ]

        for tool in lint_tools:
            template_type = manager.get_template_for_tool(tool)
            assert template_type == "lint", f"Expected 'lint' for {tool}"

    def test_detect_unknown_tool_returns_default(self):
        """Test that unknown tools return default template"""
        manager = PromptTemplateManager()

        unknown_tools = [
            "custom-tool",
            "my-special-checker",
            "unknown-analyzer",
        ]

        for tool in unknown_tools:
            template_type = manager.get_template_for_tool(tool)
            assert template_type == "default", f"Expected 'default' for {tool}"


class TestCreateToolInterpretationPrompt:
    """Tests for the create_tool_interpretation_prompt convenience function"""

    def test_basic_prompt_creation(self):
        """Test basic prompt creation"""
        output_file = Path("/tmp/test_output.txt")
        prompt = create_tool_interpretation_prompt(
            tool_name="test-tool",
            command="test-command",
            output_file_path=output_file,
        )

        assert "test-tool" in prompt
        assert "test-command" in prompt
        assert "/tmp/test_output.txt" in prompt
        assert "sugar add" in prompt
        assert "Read the file at" in prompt

    def test_auto_detect_template_type(self):
        """Test automatic template type detection"""
        output_file = Path("/tmp/security_output.txt")
        # Security tool should get security template
        prompt = create_tool_interpretation_prompt(
            tool_name="bandit",
            command="bandit -r src/",
            output_file_path=output_file,
        )

        assert "CVSS Score" in prompt

    def test_explicit_template_type(self):
        """Test explicit template type override"""
        output_file = Path("/tmp/override_output.txt")
        # Even though tool name suggests default, we can override
        prompt = create_tool_interpretation_prompt(
            tool_name="unknown-tool",
            command="cmd",
            output_file_path=output_file,
            template_type="security",
        )

        assert "CVSS Score" in prompt

    def test_with_custom_config(self):
        """Test prompt creation with custom config"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a custom template file
            template_path = Path(tmpdir) / "custom.txt"
            template_path.write_text("Custom: ${tool_name} - ${output_file_path}")

            output_file = Path("/tmp/custom_output.txt")
            prompt = create_tool_interpretation_prompt(
                tool_name="my-tool",
                command="cmd",
                output_file_path=output_file,
                template_type="custom",
                config={"templates_dir": tmpdir},
            )

            assert "Custom: my-tool - /tmp/custom_output.txt" in prompt


class TestTemplateContent:
    """Tests for template content requirements"""

    def test_default_template_has_sugar_cli_reference(self):
        """Test that default template includes Sugar CLI reference"""
        assert "sugar add [OPTIONS] TITLE" in DEFAULT_TOOL_INTERPRETATION_TEMPLATE
        assert "--type TEXT" in DEFAULT_TOOL_INTERPRETATION_TEMPLATE
        assert "--priority INTEGER" in DEFAULT_TOOL_INTERPRETATION_TEMPLATE
        assert "--description TEXT" in DEFAULT_TOOL_INTERPRETATION_TEMPLATE
        assert "--urgent" in DEFAULT_TOOL_INTERPRETATION_TEMPLATE
        assert "--status [pending|hold]" in DEFAULT_TOOL_INTERPRETATION_TEMPLATE

    def test_default_template_has_grouping_instructions(self):
        """Test that default template has grouping instructions"""
        assert "Grouping Strategy" in DEFAULT_TOOL_INTERPRETATION_TEMPLATE
        assert (
            "NEVER create hundreds of individual tasks"
            in DEFAULT_TOOL_INTERPRETATION_TEMPLATE
        )
        assert "20-50 tasks max" in DEFAULT_TOOL_INTERPRETATION_TEMPLATE

    def test_default_template_has_priority_mapping(self):
        """Test that default template has priority mapping"""
        assert "Priority Mapping" in DEFAULT_TOOL_INTERPRETATION_TEMPLATE
        assert "Security vulnerability" in DEFAULT_TOOL_INTERPRETATION_TEMPLATE
        assert "Blocking error" in DEFAULT_TOOL_INTERPRETATION_TEMPLATE

    def test_default_template_has_output_format(self):
        """Test that default template specifies output format"""
        assert "Output Format" in DEFAULT_TOOL_INTERPRETATION_TEMPLATE
        assert "executable shell commands" in DEFAULT_TOOL_INTERPRETATION_TEMPLATE

    def test_default_template_has_file_read_instruction(self):
        """Test that default template instructs Claude to read from file"""
        assert "Output File:" in DEFAULT_TOOL_INTERPRETATION_TEMPLATE
        assert "Read the file at" in DEFAULT_TOOL_INTERPRETATION_TEMPLATE
        assert "${output_file_path}" in DEFAULT_TOOL_INTERPRETATION_TEMPLATE

    def test_security_template_has_cvss_mapping(self):
        """Test that security template has CVSS score mapping"""
        assert "CVSS Score" in SECURITY_ANALYSIS_TEMPLATE
        assert "Critical" in SECURITY_ANALYSIS_TEMPLATE
        assert "9.0-10.0" in SECURITY_ANALYSIS_TEMPLATE

    def test_security_template_has_file_read_instruction(self):
        """Test that security template instructs Claude to read from file"""
        assert "Output File:" in SECURITY_ANALYSIS_TEMPLATE
        assert "Read the file at" in SECURITY_ANALYSIS_TEMPLATE

    def test_coverage_template_has_coverage_levels(self):
        """Test that coverage template has coverage level mapping"""
        assert "Coverage Level" in TEST_COVERAGE_TEMPLATE
        assert "0-25%" in TEST_COVERAGE_TEMPLATE
        assert "76-100%" in TEST_COVERAGE_TEMPLATE

    def test_coverage_template_has_file_read_instruction(self):
        """Test that coverage template instructs Claude to read from file"""
        assert "Output File:" in TEST_COVERAGE_TEMPLATE
        assert "Read the file at" in TEST_COVERAGE_TEMPLATE

    def test_lint_template_has_aggressive_grouping(self):
        """Test that lint template emphasizes aggressive grouping"""
        assert "Aggressive Grouping Rules" in LINT_ANALYSIS_TEMPLATE
        assert "NEVER create more than 30 tasks" in LINT_ANALYSIS_TEMPLATE

    def test_lint_template_has_file_read_instruction(self):
        """Test that lint template instructs Claude to read from file"""
        assert "Output File:" in LINT_ANALYSIS_TEMPLATE
        assert "Read the file at" in LINT_ANALYSIS_TEMPLATE


class TestTemplateVariables:
    """Tests for template variable handling"""

    def test_all_templates_have_required_variables(self):
        """Test that all templates have the required variable placeholders"""
        templates = [
            DEFAULT_TOOL_INTERPRETATION_TEMPLATE,
            SECURITY_ANALYSIS_TEMPLATE,
            TEST_COVERAGE_TEMPLATE,
            LINT_ANALYSIS_TEMPLATE,
        ]

        for template in templates:
            assert "${tool_name}" in template
            assert "${command}" in template
            assert "${output_file_path}" in template

    def test_empty_values_handled_gracefully(self):
        """Test that empty values don't break template rendering"""
        manager = PromptTemplateManager()
        template = manager.get_template(
            template_type="default",
            tool_name="",
            command="",
            output_file_path=None,
        )

        # Should still render without errors
        assert "sugar add" in template

    def test_special_characters_in_path(self):
        """Test that special characters in file path are handled"""
        manager = PromptTemplateManager()
        output_file = Path('/tmp/output with "quotes" and spaces.txt')
        template = manager.get_template(
            template_type="default",
            tool_name="tool",
            command="cmd",
            output_file_path=output_file,
        )

        assert 'output with "quotes" and spaces.txt' in template

    def test_path_conversion_to_string(self):
        """Test that Path objects are properly converted to strings"""
        manager = PromptTemplateManager()
        output_file = Path("/tmp/nested/path/to/output.txt")

        template = manager.get_template(
            template_type="default",
            tool_name="tool",
            command="cmd",
            output_file_path=output_file,
        )

        assert "/tmp/nested/path/to/output.txt" in template
