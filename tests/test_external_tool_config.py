"""
Tests for external tool configuration schema validation

Tests the external_tools configuration under code_quality section including:
- Schema validation for required fields (name, command)
- Environment variable expansion
- Error messages for invalid configurations
- Integration with CodeQualityScanner
"""

import os
import pytest
from unittest.mock import patch

from sugar.discovery.external_tool_config import (
    ExternalToolConfig,
    ExternalToolConfigError,
    validate_external_tool,
    validate_external_tools_config,
    parse_external_tools_from_code_quality_config,
    expand_env_vars,
    get_external_tools_config_schema,
)
from sugar.discovery.code_quality import CodeQualityScanner


class TestExternalToolConfig:
    """Tests for the ExternalToolConfig dataclass"""

    def test_external_tool_config_creation(self):
        """Test basic ExternalToolConfig creation"""
        tool = ExternalToolConfig(name="eslint", command="npx eslint .")
        assert tool.name == "eslint"
        assert tool.command == "npx eslint ."

    def test_get_expanded_command_no_vars(self):
        """Test command expansion with no environment variables"""
        tool = ExternalToolConfig(name="eslint", command="npx eslint . --format json")
        assert tool.get_expanded_command() == "npx eslint . --format json"

    def test_get_expanded_command_with_vars(self):
        """Test command expansion with environment variables"""
        with patch.dict(os.environ, {"SONAR_TOKEN": "secret123"}):
            tool = ExternalToolConfig(
                name="sonar", command="sonar-scanner -Dsonar.token=$SONAR_TOKEN"
            )
            assert (
                tool.get_expanded_command() == "sonar-scanner -Dsonar.token=secret123"
            )


class TestExpandEnvVars:
    """Tests for environment variable expansion"""

    def test_expand_dollar_var_syntax(self):
        """Test $VAR syntax expansion"""
        with patch.dict(os.environ, {"MY_VAR": "value1"}):
            result = expand_env_vars("command --arg=$MY_VAR")
            assert result == "command --arg=value1"

    def test_expand_brace_var_syntax(self):
        """Test ${VAR} syntax expansion"""
        with patch.dict(os.environ, {"MY_VAR": "value2"}):
            result = expand_env_vars("command --arg=${MY_VAR}")
            assert result == "command --arg=value2"

    def test_expand_multiple_vars(self):
        """Test expansion of multiple variables"""
        with patch.dict(os.environ, {"VAR1": "first", "VAR2": "second"}):
            result = expand_env_vars("cmd $VAR1 ${VAR2}")
            assert result == "cmd first second"

    def test_undefined_var_left_as_is(self):
        """Test that undefined variables are left unexpanded"""
        # Clear the variable if it exists
        with patch.dict(os.environ, {}, clear=True):
            result = expand_env_vars("cmd --token=$UNDEFINED_VAR")
            assert result == "cmd --token=$UNDEFINED_VAR"

    def test_no_vars_in_string(self):
        """Test string with no environment variables"""
        result = expand_env_vars("simple command without vars")
        assert result == "simple command without vars"

    def test_mixed_defined_undefined_vars(self):
        """Test mixed defined and undefined variables"""
        with patch.dict(os.environ, {"DEFINED": "yes"}, clear=True):
            result = expand_env_vars("$DEFINED $UNDEFINED")
            assert result == "yes $UNDEFINED"


class TestValidateExternalTool:
    """Tests for single tool validation"""

    def test_valid_tool(self):
        """Test validation of valid tool configuration"""
        config = {"name": "eslint", "command": "npx eslint ."}
        tool = validate_external_tool(config, 0)
        assert tool.name == "eslint"
        assert tool.command == "npx eslint ."

    def test_missing_name(self):
        """Test error for missing name field"""
        config = {"command": "npx eslint ."}
        with pytest.raises(ExternalToolConfigError) as exc_info:
            validate_external_tool(config, 0)
        assert "Missing required field 'name'" in str(exc_info.value)
        assert "external_tools[0]" in str(exc_info.value)

    def test_missing_command(self):
        """Test error for missing command field"""
        config = {"name": "eslint"}
        with pytest.raises(ExternalToolConfigError) as exc_info:
            validate_external_tool(config, 1)
        assert "Missing required field 'command'" in str(exc_info.value)
        assert "external_tools[1]" in str(exc_info.value)
        assert "eslint" in str(exc_info.value)  # Tool name should be in error

    def test_empty_name(self):
        """Test error for empty name"""
        config = {"name": "", "command": "npx eslint ."}
        with pytest.raises(ExternalToolConfigError) as exc_info:
            validate_external_tool(config, 0)
        assert "cannot be empty" in str(exc_info.value)

    def test_empty_command(self):
        """Test error for empty command"""
        config = {"name": "eslint", "command": ""}
        with pytest.raises(ExternalToolConfigError) as exc_info:
            validate_external_tool(config, 0)
        assert "cannot be empty" in str(exc_info.value)

    def test_whitespace_only_name(self):
        """Test error for whitespace-only name"""
        config = {"name": "   ", "command": "npx eslint ."}
        with pytest.raises(ExternalToolConfigError) as exc_info:
            validate_external_tool(config, 0)
        assert "cannot be empty" in str(exc_info.value)

    def test_whitespace_only_command(self):
        """Test error for whitespace-only command"""
        config = {"name": "eslint", "command": "   "}
        with pytest.raises(ExternalToolConfigError) as exc_info:
            validate_external_tool(config, 0)
        assert "cannot be empty" in str(exc_info.value)

    def test_name_not_string(self):
        """Test error for non-string name"""
        config = {"name": 123, "command": "npx eslint ."}
        with pytest.raises(ExternalToolConfigError) as exc_info:
            validate_external_tool(config, 0)
        assert "must be a string" in str(exc_info.value)

    def test_command_not_string(self):
        """Test error for non-string command"""
        config = {"name": "eslint", "command": ["npx", "eslint"]}
        with pytest.raises(ExternalToolConfigError) as exc_info:
            validate_external_tool(config, 0)
        assert "must be a string" in str(exc_info.value)

    def test_not_dict(self):
        """Test error for non-dict tool config"""
        with pytest.raises(ExternalToolConfigError) as exc_info:
            validate_external_tool("not a dict", 0)
        assert "Expected dictionary" in str(exc_info.value)

    def test_name_is_stripped(self):
        """Test that name whitespace is stripped"""
        config = {"name": "  eslint  ", "command": "npx eslint ."}
        tool = validate_external_tool(config, 0)
        assert tool.name == "eslint"

    def test_command_is_stripped(self):
        """Test that command whitespace is stripped"""
        config = {"name": "eslint", "command": "  npx eslint .  "}
        tool = validate_external_tool(config, 0)
        assert tool.command == "npx eslint ."


class TestValidateExternalToolsConfig:
    """Tests for external_tools list validation"""

    def test_empty_list(self):
        """Test empty external_tools list"""
        result = validate_external_tools_config([])
        assert result == []

    def test_none_config(self):
        """Test None external_tools config"""
        result = validate_external_tools_config(None)
        assert result == []

    def test_valid_single_tool(self):
        """Test single valid tool"""
        config = [{"name": "eslint", "command": "npx eslint ."}]
        result = validate_external_tools_config(config)
        assert len(result) == 1
        assert result[0].name == "eslint"

    def test_valid_multiple_tools(self):
        """Test multiple valid tools"""
        config = [
            {"name": "eslint", "command": "npx eslint . --format json"},
            {"name": "ruff", "command": "ruff check . --output-format json"},
            {"name": "phpstan", "command": "vendor/bin/phpstan analyse"},
        ]
        result = validate_external_tools_config(config)
        assert len(result) == 3
        assert result[0].name == "eslint"
        assert result[1].name == "ruff"
        assert result[2].name == "phpstan"

    def test_duplicate_names_error(self):
        """Test error for duplicate tool names"""
        config = [
            {"name": "eslint", "command": "npx eslint ."},
            {"name": "eslint", "command": "npx eslint src/"},
        ]
        with pytest.raises(ExternalToolConfigError) as exc_info:
            validate_external_tools_config(config)
        assert "Duplicate tool name" in str(exc_info.value)

    def test_duplicate_names_case_insensitive(self):
        """Test that duplicate name check is case-insensitive"""
        config = [
            {"name": "ESLint", "command": "npx eslint ."},
            {"name": "eslint", "command": "npx eslint src/"},
        ]
        with pytest.raises(ExternalToolConfigError) as exc_info:
            validate_external_tools_config(config)
        assert "Duplicate tool name" in str(exc_info.value)

    def test_not_list_error(self):
        """Test error when external_tools is not a list"""
        with pytest.raises(ExternalToolConfigError) as exc_info:
            validate_external_tools_config({"name": "eslint"})
        assert "Expected list" in str(exc_info.value)

    def test_mixed_valid_invalid_stops_at_first_error(self):
        """Test that validation stops at first invalid entry"""
        config = [
            {"name": "eslint", "command": "npx eslint ."},
            {"name": "broken"},  # Missing command
            {"name": "ruff", "command": "ruff check ."},
        ]
        with pytest.raises(ExternalToolConfigError) as exc_info:
            validate_external_tools_config(config)
        assert "external_tools[1]" in str(exc_info.value)


class TestParseExternalToolsFromCodeQualityConfig:
    """Tests for parsing from code_quality section"""

    def test_parse_from_code_quality_config(self):
        """Test parsing external_tools from code_quality config"""
        config = {
            "enabled": True,
            "root_path": ".",
            "external_tools": [{"name": "eslint", "command": "npx eslint ."}],
        }
        result = parse_external_tools_from_code_quality_config(config)
        assert len(result) == 1
        assert result[0].name == "eslint"

    def test_missing_external_tools_returns_empty(self):
        """Test that missing external_tools returns empty list"""
        config = {"enabled": True, "root_path": "."}
        result = parse_external_tools_from_code_quality_config(config)
        assert result == []

    def test_null_external_tools_returns_empty(self):
        """Test that null external_tools returns empty list"""
        config = {"enabled": True, "external_tools": None}
        result = parse_external_tools_from_code_quality_config(config)
        assert result == []


class TestCodeQualityScannerExternalTools:
    """Integration tests for external tools in CodeQualityScanner"""

    def test_scanner_loads_external_tools(self, temp_dir):
        """Test that CodeQualityScanner loads external tools from config"""
        config = {
            "root_path": str(temp_dir),
            "external_tools": [
                {"name": "eslint", "command": "npx eslint ."},
                {"name": "ruff", "command": "ruff check ."},
            ],
        }
        scanner = CodeQualityScanner(config)
        assert len(scanner.external_tools) == 2
        assert scanner.external_tools[0].name == "eslint"
        assert scanner.external_tools[1].name == "ruff"

    def test_scanner_handles_invalid_config_gracefully(self, temp_dir, caplog):
        """Test that scanner handles invalid external tools config gracefully"""
        config = {
            "root_path": str(temp_dir),
            "external_tools": [{"name": "eslint"}],  # Missing command
        }
        # Should not raise, but should log error
        scanner = CodeQualityScanner(config)
        assert scanner.external_tools == []
        assert "configuration error" in caplog.text.lower()

    def test_scanner_health_check_includes_external_tools(self, temp_dir):
        """Test that health_check includes external tools info"""
        config = {
            "root_path": str(temp_dir),
            "external_tools": [{"name": "eslint", "command": "npx eslint ."}],
        }
        scanner = CodeQualityScanner(config)
        import asyncio

        health = asyncio.run(scanner.health_check())
        assert "external_tools" in health
        assert len(health["external_tools"]) == 1
        assert health["external_tools"][0]["name"] == "eslint"
        assert health["external_tools"][0]["command"] == "npx eslint ."

    def test_scanner_empty_external_tools(self, temp_dir):
        """Test scanner with empty external_tools list"""
        config = {"root_path": str(temp_dir), "external_tools": []}
        scanner = CodeQualityScanner(config)
        assert scanner.external_tools == []

    def test_scanner_no_external_tools_key(self, temp_dir):
        """Test scanner without external_tools in config"""
        config = {"root_path": str(temp_dir)}
        scanner = CodeQualityScanner(config)
        assert scanner.external_tools == []


class TestGetExternalToolsConfigSchema:
    """Tests for schema documentation"""

    def test_schema_contains_required_info(self):
        """Test that schema documentation contains required information"""
        schema = get_external_tools_config_schema()
        assert "name" in schema
        assert "command" in schema
        assert "required" in schema.lower()
        assert "external_tools" in schema
        assert "code_quality" in schema

    def test_schema_contains_example(self):
        """Test that schema documentation contains example"""
        schema = get_external_tools_config_schema()
        assert "eslint" in schema
        assert "Example" in schema


class TestRealWorldConfigurations:
    """Test real-world configuration scenarios"""

    def test_eslint_configuration(self):
        """Test eslint configuration"""
        config = [
            {
                "name": "eslint",
                "command": "npx eslint . --format json --ext .js,.jsx,.ts,.tsx",
            }
        ]
        result = validate_external_tools_config(config)
        assert result[0].name == "eslint"

    def test_phpstan_configuration(self):
        """Test PHPStan configuration"""
        config = [
            {
                "name": "phpstan",
                "command": "vendor/bin/phpstan analyse --error-format=json --level=max",
            }
        ]
        result = validate_external_tools_config(config)
        assert result[0].name == "phpstan"

    def test_ruff_configuration(self):
        """Test Ruff configuration"""
        config = [{"name": "ruff", "command": "ruff check . --output-format json"}]
        result = validate_external_tools_config(config)
        assert result[0].name == "ruff"

    def test_sonarqube_with_env_var(self):
        """Test SonarQube configuration with environment variable"""
        with patch.dict(os.environ, {"SONAR_TOKEN": "sqp_abc123"}):
            config = [
                {
                    "name": "sonarqube",
                    "command": "sonar-scanner -Dsonar.token=$SONAR_TOKEN -Dsonar.host.url=https://sonar.example.com",
                }
            ]
            result = validate_external_tools_config(config)
            expanded = result[0].get_expanded_command()
            assert "sqp_abc123" in expanded
            assert "$SONAR_TOKEN" not in expanded

    def test_complex_multi_tool_configuration(self):
        """Test complex multi-tool setup"""
        config = [
            {"name": "eslint", "command": "npx eslint . --format json"},
            {"name": "prettier", "command": "npx prettier --check ."},
            {"name": "ruff", "command": "ruff check . --output-format json"},
            {"name": "mypy", "command": "mypy . --output json"},
            {"name": "phpstan", "command": "vendor/bin/phpstan analyse"},
        ]
        result = validate_external_tools_config(config)
        assert len(result) == 5
        names = [t.name for t in result]
        assert names == ["eslint", "prettier", "ruff", "mypy", "phpstan"]
