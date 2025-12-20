"""
Base Profile - Abstract interface for workflow profiles
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProfileConfig:
    """Configuration for a workflow profile"""

    name: str
    description: str = ""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 8192
    temperature: float = 0.7

    # Profile-specific settings
    settings: Dict[str, Any] = field(default_factory=dict)

    # Tools this profile can use
    allowed_tools: List[str] = field(default_factory=list)

    # Quality gate settings
    quality_gates_enabled: bool = True
    confidence_threshold: float = 0.7


class BaseProfile(ABC):
    """
    Abstract base class for workflow profiles.

    Profiles define specialized agent behaviors for different use cases.
    Each profile provides:
    - A tailored system prompt
    - Profile-specific tools
    - Quality gate configuration
    - Pre/post processing hooks
    """

    def __init__(self, config: ProfileConfig):
        """
        Initialize the profile.

        Args:
            config: Profile configuration
        """
        self.config = config

    @property
    def name(self) -> str:
        """Profile name"""
        return self.config.name

    @abstractmethod
    def get_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Get the system prompt for this profile.

        Args:
            context: Optional context to customize the prompt

        Returns:
            System prompt string
        """
        pass

    @abstractmethod
    async def process_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pre-process input before agent execution.

        Args:
            input_data: Raw input data

        Returns:
            Processed input ready for the agent
        """
        pass

    @abstractmethod
    async def process_output(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-process agent output.

        Args:
            output_data: Raw agent output

        Returns:
            Processed output
        """
        pass

    def get_tools(self) -> List[str]:
        """Get the list of tools this profile can use"""
        return self.config.allowed_tools

    def get_quality_gate_config(self) -> Dict[str, Any]:
        """Get quality gate configuration for this profile"""
        return {
            "enabled": self.config.quality_gates_enabled,
            "confidence_threshold": self.config.confidence_threshold,
        }

    def validate_output(self, output: Dict[str, Any]) -> bool:
        """
        Validate that output meets profile requirements.

        Args:
            output: Output to validate

        Returns:
            True if valid, False otherwise
        """
        # Default: check confidence threshold
        confidence = output.get("confidence", 1.0)
        return confidence >= self.config.confidence_threshold
