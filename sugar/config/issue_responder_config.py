"""Configuration loader for the Issue Responder feature."""

from dataclasses import dataclass, field
from typing import List, Optional
import yaml
from pathlib import Path


@dataclass
class IssueResponderConfig:
    """Configuration for AI-powered automatic issue responses.

    Attributes:
        enabled: Enable automatic issue responses
        auto_post_threshold: Minimum confidence score (0.0-1.0) to auto-post responses
        max_response_length: Maximum characters per response
        response_delay_seconds: Delay before posting (0 = immediate)
        rate_limit_per_hour: Maximum responses per hour (0 = unlimited)
        respond_to_labels: Only respond to issues with these labels (empty = all)
        skip_labels: Never respond to issues with these labels
        skip_bot_issues: Skip issues created by bots
        handle_follow_ups: How to handle follow-up comments - "ignore" | "queue" | "auto"
        model: Claude model to use for generating responses
    """

    enabled: bool = False
    auto_post_threshold: float = 0.8
    max_response_length: int = 2000
    response_delay_seconds: int = 0
    rate_limit_per_hour: int = 10
    respond_to_labels: List[str] = field(default_factory=list)
    skip_labels: List[str] = field(
        default_factory=lambda: ["wontfix", "duplicate", "stale"]
    )
    skip_bot_issues: bool = True
    handle_follow_ups: str = "ignore"  # "ignore" | "queue" | "auto"
    model: str = "claude-sonnet-4-20250514"

    @classmethod
    def from_dict(cls, data: dict) -> "IssueResponderConfig":
        """Create IssueResponderConfig from a dictionary.

        Args:
            data: Dictionary containing configuration values

        Returns:
            IssueResponderConfig instance

        Example:
            >>> config_data = {
            ...     "enabled": True,
            ...     "auto_post_threshold": 0.9,
            ...     "respond_to_labels": ["question", "help-wanted"]
            ... }
            >>> config = IssueResponderConfig.from_dict(config_data)
        """
        # Filter to only include known fields
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)

    @classmethod
    def load_from_file(cls, config_path: str) -> "IssueResponderConfig":
        """Load IssueResponderConfig from a YAML configuration file.

        Args:
            config_path: Path to the YAML configuration file

        Returns:
            IssueResponderConfig instance with values from the file

        Raises:
            FileNotFoundError: If the config file doesn't exist
            KeyError: If the 'issue_responder' section is missing
            yaml.YAMLError: If the YAML file is malformed

        Example:
            >>> config = IssueResponderConfig.load_from_file(".sugar/config.yaml")
        """
        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f)

        # Navigate to the issue_responder section
        if "sugar" not in config_data:
            raise KeyError("Configuration file missing 'sugar' section")

        if "issue_responder" not in config_data["sugar"]:
            raise KeyError("Configuration file missing 'sugar.issue_responder' section")

        issue_responder_data = config_data["sugar"]["issue_responder"]
        return cls.from_dict(issue_responder_data)

    def validate(self) -> List[str]:
        """Validate configuration values and return list of errors.

        Returns:
            List of validation error messages (empty if valid)

        Example:
            >>> config = IssueResponderConfig(auto_post_threshold=1.5)
            >>> errors = config.validate()
            >>> if errors:
            ...     print("Invalid configuration:", errors)
        """
        errors = []

        # Validate auto_post_threshold
        if not 0.0 <= self.auto_post_threshold <= 1.0:
            errors.append(
                f"auto_post_threshold must be between 0.0 and 1.0, got {self.auto_post_threshold}"
            )

        # Validate max_response_length
        if self.max_response_length <= 0:
            errors.append(
                f"max_response_length must be positive, got {self.max_response_length}"
            )

        # Validate response_delay_seconds
        if self.response_delay_seconds < 0:
            errors.append(
                f"response_delay_seconds must be non-negative, got {self.response_delay_seconds}"
            )

        # Validate rate_limit_per_hour
        if self.rate_limit_per_hour < 0:
            errors.append(
                f"rate_limit_per_hour must be non-negative, got {self.rate_limit_per_hour}"
            )

        # Validate handle_follow_ups
        valid_follow_up_values = {"ignore", "queue", "auto"}
        if self.handle_follow_ups not in valid_follow_up_values:
            errors.append(
                f"handle_follow_ups must be one of {valid_follow_up_values}, got '{self.handle_follow_ups}'"
            )

        return errors
