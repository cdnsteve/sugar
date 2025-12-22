"""
Tests for prompt configuration system
"""

import json
import pytest
from pathlib import Path

from sugar.config.prompt_config import PersonaConfig, PromptConfig


class TestPersonaConfig:
    """Test PersonaConfig dataclass"""

    def test_default_values(self):
        """Test default values for PersonaConfig"""
        persona = PersonaConfig()

        assert persona.role is None
        assert persona.goal is None
        assert persona.expertise == []

    def test_from_dict_with_full_data(self):
        """Test from_dict with all fields populated"""
        data = {
            "role": "Senior QA Engineer",
            "goal": "Ensure high-quality test coverage",
            "expertise": ["pytest", "playwright", "test automation"],
        }

        persona = PersonaConfig.from_dict(data)

        assert persona.role == "Senior QA Engineer"
        assert persona.goal == "Ensure high-quality test coverage"
        assert persona.expertise == ["pytest", "playwright", "test automation"]

    def test_from_dict_with_partial_data(self):
        """Test from_dict with only some fields"""
        data = {"role": "QA Engineer"}

        persona = PersonaConfig.from_dict(data)

        assert persona.role == "QA Engineer"
        assert persona.goal is None
        assert persona.expertise == []

    def test_from_dict_with_empty_dict(self):
        """Test from_dict with empty dictionary"""
        persona = PersonaConfig.from_dict({})

        assert persona.role is None
        assert persona.goal is None
        assert persona.expertise == []


class TestPromptConfig:
    """Test PromptConfig dataclass"""

    def test_default_values(self):
        """Test default values for PromptConfig with required instructions"""
        config = PromptConfig(instructions="Always write tests first")

        assert config.instructions == "Always write tests first"
        assert config.name is None
        assert config.description is None
        assert config.persona is None
        assert config.guidelines == []
        assert config.constraints == []

    def test_from_dict_with_full_data(self):
        """Test from_dict with all fields populated"""
        data = {
            "name": "Test-First Development",
            "description": "TDD approach for all features",
            "instructions": "Write tests before implementation",
            "persona": {
                "role": "Senior QA Engineer",
                "goal": "Ensure code quality",
                "expertise": ["pytest", "TDD"],
            },
            "guidelines": ["Use descriptive test names", "Follow AAA pattern"],
            "constraints": ["Minimum 80% coverage", "No skipped tests"],
        }

        config = PromptConfig.from_dict(data)

        assert config.name == "Test-First Development"
        assert config.description == "TDD approach for all features"
        assert config.instructions == "Write tests before implementation"
        assert config.persona is not None
        assert config.persona.role == "Senior QA Engineer"
        assert config.persona.goal == "Ensure code quality"
        assert config.persona.expertise == ["pytest", "TDD"]
        assert config.guidelines == ["Use descriptive test names", "Follow AAA pattern"]
        assert config.constraints == ["Minimum 80% coverage", "No skipped tests"]

    def test_from_dict_with_partial_data(self):
        """Test from_dict with only required fields"""
        data = {"instructions": "Follow project coding standards"}

        config = PromptConfig.from_dict(data)

        assert config.instructions == "Follow project coding standards"
        assert config.name is None
        assert config.description is None
        assert config.persona is None
        assert config.guidelines == []
        assert config.constraints == []

    def test_from_dict_without_persona(self):
        """Test from_dict when persona is not provided"""
        data = {
            "instructions": "Use black for formatting",
            "guidelines": ["Follow PEP 8"],
        }

        config = PromptConfig.from_dict(data)

        assert config.instructions == "Use black for formatting"
        assert config.persona is None
        assert config.guidelines == ["Follow PEP 8"]

    def test_validation_missing_instructions(self):
        """Test validation fails when instructions is missing"""
        config = PromptConfig(instructions="")

        errors = config.validate()

        assert len(errors) == 1
        assert "instructions is required and cannot be empty" in errors[0]

    def test_validation_empty_instructions(self):
        """Test validation fails when instructions is whitespace only"""
        config = PromptConfig(instructions="   ")

        errors = config.validate()

        assert len(errors) == 1
        assert "instructions is required and cannot be empty" in errors[0]

    def test_validation_valid_config(self):
        """Test validation passes for valid config"""
        config = PromptConfig(
            instructions="Follow coding standards",
            guidelines=["Use type hints", "Write docstrings"],
        )

        errors = config.validate()

        assert len(errors) == 0


class TestLoadFromFile:
    """Test file loading functionality"""

    def test_load_from_file_missing_file(self, tmp_path):
        """Test load_from_file returns None for missing file"""
        config_path = tmp_path / "nonexistent.json"

        config = PromptConfig.load_from_file(config_path)

        assert config is None

    def test_load_from_file_invalid_json(self, tmp_path):
        """Test load_from_file returns None for invalid JSON"""
        config_path = tmp_path / "invalid.json"
        config_path.write_text("{ invalid json }")

        config = PromptConfig.load_from_file(config_path)

        assert config is None

    def test_load_from_file_valid_json(self, tmp_path):
        """Test load_from_file returns config for valid JSON"""
        config_path = tmp_path / "config.json"
        data = {
            "name": "Project Config",
            "instructions": "Follow project guidelines",
            "persona": {"role": "Developer", "goal": "Build quality software"},
            "guidelines": ["Write clean code"],
            "constraints": ["No magic numbers"],
        }
        config_path.write_text(json.dumps(data))

        config = PromptConfig.load_from_file(config_path)

        assert config is not None
        assert config.name == "Project Config"
        assert config.instructions == "Follow project guidelines"
        assert config.persona is not None
        assert config.persona.role == "Developer"
        assert config.guidelines == ["Write clean code"]
        assert config.constraints == ["No magic numbers"]

    def test_load_from_file_minimal_valid_json(self, tmp_path):
        """Test load_from_file with minimal valid JSON"""
        config_path = tmp_path / "minimal.json"
        data = {"instructions": "Minimal config"}
        config_path.write_text(json.dumps(data))

        config = PromptConfig.load_from_file(config_path)

        assert config is not None
        assert config.instructions == "Minimal config"
        assert config.persona is None
        assert config.guidelines == []
        assert config.constraints == []

    def test_load_from_file_default_path(self, tmp_path, monkeypatch):
        """Test load_from_file uses default path when not specified"""
        # Change to tmp_path directory
        monkeypatch.chdir(tmp_path)

        # Create default path
        default_dir = tmp_path / ".sugar" / "prompts"
        default_dir.mkdir(parents=True)
        config_path = default_dir / "issue_responder.json"
        data = {"instructions": "Default config"}
        config_path.write_text(json.dumps(data))

        config = PromptConfig.load_from_file()

        assert config is not None
        assert config.instructions == "Default config"


class TestBuildSystemPromptAdditions:
    """Test build_system_prompt_additions functionality"""

    def test_minimal_config_with_only_instructions(self):
        """Test returns formatted instructions for minimal config"""
        config = PromptConfig(instructions="Follow coding standards")

        result = config.build_system_prompt_additions()

        assert "## Project-Specific Instructions\nFollow coding standards" in result
        assert "## Your Persona" not in result
        assert "## Guidelines" not in result
        assert "## Constraints" not in result

    def test_includes_persona_section(self):
        """Test includes persona section when persona provided"""
        config = PromptConfig(
            instructions="Write tests",
            persona=PersonaConfig(
                role="QA Engineer",
                goal="Ensure quality",
                expertise=["pytest", "testing"],
            ),
        )

        result = config.build_system_prompt_additions()

        assert "## Your Persona" in result
        assert "**Role**: QA Engineer" in result
        assert "**Goal**: Ensure quality" in result
        assert "**Expertise**: pytest, testing" in result

    def test_includes_guidelines_when_provided(self):
        """Test includes guidelines section when provided"""
        config = PromptConfig(
            instructions="Write clean code",
            guidelines=["Use type hints", "Write docstrings", "Follow PEP 8"],
        )

        result = config.build_system_prompt_additions()

        assert "## Guidelines" in result
        assert "- Use type hints" in result
        assert "- Write docstrings" in result
        assert "- Follow PEP 8" in result

    def test_includes_constraints_when_provided(self):
        """Test includes constraints section when provided"""
        config = PromptConfig(
            instructions="Follow rules",
            constraints=[
                "No TODO comments",
                "Max line length 88",
                "Type all functions",
            ],
        )

        result = config.build_system_prompt_additions()

        assert "## Constraints" in result
        assert "- No TODO comments" in result
        assert "- Max line length 88" in result
        assert "- Type all functions" in result

    def test_combines_all_sections_properly(self):
        """Test combines all sections in correct order"""
        config = PromptConfig(
            instructions="Main instructions here",
            persona=PersonaConfig(role="Developer", goal="Build features"),
            guidelines=["Guideline 1", "Guideline 2"],
            constraints=["Constraint 1"],
        )

        result = config.build_system_prompt_additions()

        # Check all sections are present
        assert "## Your Persona" in result
        assert "## Project-Specific Instructions" in result
        assert "## Guidelines" in result
        assert "## Constraints" in result

        # Check order (persona, instructions, guidelines, constraints)
        persona_idx = result.index("## Your Persona")
        instructions_idx = result.index("## Project-Specific Instructions")
        guidelines_idx = result.index("## Guidelines")
        constraints_idx = result.index("## Constraints")

        assert persona_idx < instructions_idx < guidelines_idx < constraints_idx

        # Check sections are separated by double newlines
        assert "\n\n" in result

    def test_persona_with_partial_fields(self):
        """Test persona section with only some fields populated"""
        config = PromptConfig(
            instructions="Instructions",
            persona=PersonaConfig(role="Developer"),  # Only role, no goal/expertise
        )

        result = config.build_system_prompt_additions()

        assert "## Your Persona" in result
        assert "**Role**: Developer" in result
        assert "**Goal**:" not in result
        assert "**Expertise**:" not in result

    def test_empty_persona_not_included(self):
        """Test persona section not included if all fields are None/empty"""
        config = PromptConfig(
            instructions="Instructions",
            persona=PersonaConfig(),  # All fields None/empty
        )

        result = config.build_system_prompt_additions()

        # Persona section should not be included if no fields are populated
        assert "## Your Persona" not in result

    def test_section_formatting(self):
        """Test proper markdown formatting of sections"""
        config = PromptConfig(
            instructions="These are the instructions.\nMultiline instructions work.",
            guidelines=["First guideline", "Second guideline"],
        )

        result = config.build_system_prompt_additions()

        # Check instructions preserve newlines
        assert "These are the instructions.\nMultiline instructions work." in result

        # Check guidelines are bulleted
        assert "- First guideline" in result
        assert "- Second guideline" in result
