"""
Prompt configuration for Issue Responder

Loads custom prompt configuration from .sugar/prompts/issue_responder.json
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PersonaConfig:
    """Agent persona configuration"""

    role: Optional[str] = None
    goal: Optional[str] = None
    expertise: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "PersonaConfig":
        """Create PersonaConfig from a dictionary.

        Args:
            data: Dictionary containing persona configuration

        Returns:
            PersonaConfig instance
        """
        return cls(
            role=data.get("role"),
            goal=data.get("goal"),
            expertise=data.get("expertise", []),
        )


@dataclass
class PromptConfig:
    """Custom prompt configuration for Issue Responder"""

    instructions: str
    name: Optional[str] = None
    description: Optional[str] = None
    persona: Optional[PersonaConfig] = None
    guidelines: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "PromptConfig":
        """Load from dictionary"""
        persona_data = data.get("persona")
        persona = PersonaConfig.from_dict(persona_data) if persona_data else None

        return cls(
            instructions=data.get("instructions", ""),
            name=data.get("name"),
            description=data.get("description"),
            persona=persona,
            guidelines=data.get("guidelines", []),
            constraints=data.get("constraints", []),
        )

    @classmethod
    def load_from_file(cls, config_path: Path = None) -> Optional["PromptConfig"]:
        """
        Load from JSON file.

        Default path: .sugar/prompts/issue_responder.json
        Returns None if file doesn't exist (use defaults)
        """
        if config_path is None:
            config_path = Path(".sugar/prompts/issue_responder.json")

        if not config_path.exists():
            logger.debug(f"No custom prompt config at {config_path}")
            return None

        try:
            with open(config_path) as f:
                data = json.load(f)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {config_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading prompt config: {e}")
            return None

    def validate(self) -> List[str]:
        """Validate configuration, return list of errors"""
        errors = []
        if not self.instructions or not self.instructions.strip():
            errors.append("instructions is required and cannot be empty")
        return errors

    def build_system_prompt_additions(self) -> str:
        """
        Build the system prompt additions from this config.
        Returns a string to be added to the base system prompt.
        """
        parts = []

        # Add persona section
        if self.persona:
            persona_parts = []
            if self.persona.role:
                persona_parts.append(f"**Role**: {self.persona.role}")
            if self.persona.goal:
                persona_parts.append(f"**Goal**: {self.persona.goal}")
            if self.persona.expertise:
                persona_parts.append(
                    f"**Expertise**: {', '.join(self.persona.expertise)}"
                )
            if persona_parts:
                parts.append("## Your Persona\n" + "\n".join(persona_parts))

        # Add instructions
        if self.instructions:
            parts.append(f"## Project-Specific Instructions\n{self.instructions}")

        # Add guidelines
        if self.guidelines:
            guidelines_text = "\n".join(f"- {g}" for g in self.guidelines)
            parts.append(f"## Guidelines\n{guidelines_text}")

        # Add constraints
        if self.constraints:
            constraints_text = "\n".join(f"- {c}" for c in self.constraints)
            parts.append(f"## Constraints\n{constraints_text}")

        return "\n\n".join(parts)
