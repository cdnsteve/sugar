"""
Sugar Workflow Profiles

Profiles define specialized agent behaviors for different use cases:
- default: General-purpose development assistance
- issue_responder: GitHub issue analysis and response
- code_reviewer: Code review and PR feedback (future)
"""

from .base import BaseProfile, ProfileConfig
from .default import DefaultProfile
from .issue_responder import IssueResponderProfile

__all__ = [
    "BaseProfile",
    "ProfileConfig",
    "DefaultProfile",
    "IssueResponderProfile",
]
