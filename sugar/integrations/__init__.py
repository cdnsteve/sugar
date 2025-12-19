"""
Sugar Integrations

External service integrations:
- GitHub: Issue and PR management
"""

from .github import GitHubClient, GitHubIssue, GitHubComment

__all__ = [
    "GitHubClient",
    "GitHubIssue",
    "GitHubComment",
]
