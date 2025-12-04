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
        manager = PromptTemplateManager()
        template = manager.get_template(
            template_type="default",
            tool_name="test-tool",
            command="test-cmd",
            raw_output="test output",
        )

        assert "test-tool" in template
        assert "test-cmd" in template
        assert "test output" in template
        assert "sugar add" in template

    def test_get_builtin_security_template(self):
        """Test getting the security template"""
        manager = PromptTemplateManager()
        template = manager.get_template(
            template_type="security",
            tool_name="bandit",
            command="bandit -r src/",
            raw_output="High: SQL Injection in db.py",
        )

        assert "bandit" in template
        assert "Security Priority Mapping" in template
        assert "CVSS Score" in template

    def test_get_builtin_coverage_template(self):
        """Test getting the coverage template"""
        manager = PromptTemplateManager()
        template = manager.get_template(
            template_type="coverage",
            tool_name="pytest-cov",
            command="pytest --cov=src",
            raw_output="TOTAL 75%",
        )

        assert "pytest-cov" in template
        assert "Coverage Priority Mapping" in template

    def test_get_builtin_lint_template(self):
        """Test getting the lint template"""
        manager = PromptTemplateManager()
        template = manager.get_template(
            template_type="lint",
            tool_name="eslint",
            command="eslint src/",
            raw_output="100 problems",
        )

        assert "eslint" in template
        assert "Aggressive Grouping Rules" in template

    def test_get_unknown_template_falls_back_to_default(self):
        """Test that unknown template type falls back to default"""
        manager = PromptTemplateManager()
        template = manager.get_template(
            template_type="nonexistent",
            tool_name="test",
            command="test",
            raw_output="test",
        )

        # Should contain default template content
        assert "sugar add" in template
        assert "Grouping Strategy" in template

    def test_template_variable_substitution(self):
        """Test that template variables are properly substituted"""
        manager = PromptTemplateManager()
        template = manager.get_template(
            template_type="default",
            tool_name="my-custom-tool",
            command="my-custom-command --verbose",
            raw_output="Custom output line 1\nCustom output line 2",
        )

        assert "my-custom-tool" in template
        assert "my-custom-command --verbose" in template
        assert "Custom output line 1" in template
        assert "Custom output line 2" in template

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
Output: ${raw_output}
Command: ${command}
"""

            # Save custom template
            success = manager.save_custom_template("my_custom", custom_content)
            assert success is True
            assert "my_custom" in manager.custom_templates

            # Get the custom template
            rendered = manager.get_template(
                template_type="my_custom",
                tool_name="test",
                command="cmd",
                raw_output="output",
            )

            assert "Custom template for test" in rendered
            assert "Output: output" in rendered

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
        prompt = create_tool_interpretation_prompt(
            tool_name="test-tool",
            command="test-command",
            raw_output="test output",
        )

        assert "test-tool" in prompt
        assert "test-command" in prompt
        assert "test output" in prompt
        assert "sugar add" in prompt

    def test_auto_detect_template_type(self):
        """Test automatic template type detection"""
        # Security tool should get security template
        prompt = create_tool_interpretation_prompt(
            tool_name="bandit",
            command="bandit -r src/",
            raw_output="Security issues found",
        )

        assert "CVSS Score" in prompt

    def test_explicit_template_type(self):
        """Test explicit template type override"""
        # Even though tool name suggests default, we can override
        prompt = create_tool_interpretation_prompt(
            tool_name="unknown-tool",
            command="cmd",
            raw_output="output",
            template_type="security",
        )

        assert "CVSS Score" in prompt

    def test_with_custom_config(self):
        """Test prompt creation with custom config"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a custom template file
            template_path = Path(tmpdir) / "custom.txt"
            template_path.write_text("Custom: ${tool_name} - ${raw_output}")

            prompt = create_tool_interpretation_prompt(
                tool_name="my-tool",
                command="cmd",
                raw_output="my output",
                template_type="custom",
                config={"templates_dir": tmpdir},
            )

            assert "Custom: my-tool - my output" in prompt


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

    def test_security_template_has_cvss_mapping(self):
        """Test that security template has CVSS score mapping"""
        assert "CVSS Score" in SECURITY_ANALYSIS_TEMPLATE
        assert "Critical" in SECURITY_ANALYSIS_TEMPLATE
        assert "9.0-10.0" in SECURITY_ANALYSIS_TEMPLATE

    def test_coverage_template_has_coverage_levels(self):
        """Test that coverage template has coverage level mapping"""
        assert "Coverage Level" in TEST_COVERAGE_TEMPLATE
        assert "0-25%" in TEST_COVERAGE_TEMPLATE
        assert "76-100%" in TEST_COVERAGE_TEMPLATE

    def test_lint_template_has_aggressive_grouping(self):
        """Test that lint template emphasizes aggressive grouping"""
        assert "Aggressive Grouping Rules" in LINT_ANALYSIS_TEMPLATE
        assert "NEVER create more than 30 tasks" in LINT_ANALYSIS_TEMPLATE


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
            assert "${raw_output}" in template

    def test_empty_values_handled_gracefully(self):
        """Test that empty values don't break template rendering"""
        manager = PromptTemplateManager()
        template = manager.get_template(
            template_type="default",
            tool_name="",
            command="",
            raw_output="",
        )

        # Should still render without errors
        assert "sugar add" in template

    def test_special_characters_in_output(self):
        """Test that special characters in output are handled"""
        manager = PromptTemplateManager()
        template = manager.get_template(
            template_type="default",
            tool_name="tool",
            command="cmd",
            raw_output='Output with "quotes" and $pecial chars',
        )

        assert '"quotes"' in template
        assert "$pecial" in template

    def test_multiline_output(self):
        """Test that multiline output is preserved"""
        manager = PromptTemplateManager()
        multiline_output = """Line 1
Line 2
Line 3
    Indented line"""

        template = manager.get_template(
            template_type="default",
            tool_name="tool",
            command="cmd",
            raw_output=multiline_output,
        )

        assert "Line 1" in template
        assert "Line 2" in template
        assert "Indented line" in template
