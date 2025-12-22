"""
GitHub Integration - Issue and PR management

Provides a clean interface for GitHub API operations:
- Reading issues and comments
- Posting comments
- Managing labels
- Searching similar issues
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GitHubUser:
    """GitHub user information"""

    login: str
    id: int = 0
    type: str = "User"  # User, Bot, Organization

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitHubUser":
        return cls(
            login=data.get("login", "unknown"),
            id=data.get("id", 0),
            type=data.get("type", "User"),
        )


@dataclass
class GitHubLabel:
    """GitHub label"""

    name: str
    color: str = ""
    description: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitHubLabel":
        return cls(
            name=data.get("name", ""),
            color=data.get("color", ""),
            description=data.get("description", ""),
        )


@dataclass
class GitHubComment:
    """GitHub issue/PR comment"""

    id: int
    body: str
    user: GitHubUser
    created_at: str
    updated_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitHubComment":
        return cls(
            id=data.get("id", 0),
            body=data.get("body", ""),
            user=GitHubUser.from_dict(data.get("user", {})),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class GitHubIssue:
    """GitHub issue"""

    number: int
    title: str
    body: str
    state: str
    user: GitHubUser
    labels: List[GitHubLabel]
    created_at: str
    updated_at: str
    comments_count: int = 0
    comments: List[GitHubComment] = field(default_factory=list)
    is_pull_request: bool = False
    html_url: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitHubIssue":
        return cls(
            number=data.get("number", 0),
            title=data.get("title", ""),
            body=data.get("body", "") or "",
            state=data.get("state", "open"),
            user=GitHubUser.from_dict(data.get("user", {})),
            labels=[GitHubLabel.from_dict(l) for l in data.get("labels", [])],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            comments_count=data.get("comments", 0),
            is_pull_request="pull_request" in data,
            html_url=data.get("html_url", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for processing"""
        return {
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "state": self.state,
            "user": {"login": self.user.login, "type": self.user.type},
            "labels": [l.name for l in self.labels],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "comments_count": self.comments_count,
            "is_pull_request": self.is_pull_request,
            "html_url": self.html_url,
        }


class GitHubClient:
    """
    GitHub API client using the gh CLI.

    Uses the gh CLI for authentication and API access, which:
    - Handles authentication automatically
    - Works in GitHub Actions with GITHUB_TOKEN
    - Supports both user and app authentication
    """

    def __init__(
        self,
        repo: Optional[str] = None,
        token: Optional[str] = None,
    ):
        """
        Initialize the GitHub client.

        Args:
            repo: Repository in owner/repo format (optional, uses current repo)
            token: GitHub token (optional, uses gh auth or GITHUB_TOKEN)
        """
        self.repo = repo
        self.token = token or os.environ.get("GITHUB_TOKEN")

    def _run_gh(
        self,
        args: List[str],
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a gh CLI command"""
        cmd = ["gh"] + args

        if self.repo:
            cmd.extend(["-R", self.repo])

        env = os.environ.copy()
        if self.token:
            env["GH_TOKEN"] = self.token

        logger.debug(f"Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

        if check and result.returncode != 0:
            logger.error(f"gh command failed: {result.stderr}")
            raise RuntimeError(f"gh command failed: {result.stderr}")

        return result

    def _gh_api(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make a GitHub API request via gh"""
        args = ["api", endpoint, "-X", method]

        if data:
            args.extend(["-f", json.dumps(data)])

        result = self._run_gh(args)
        if result.stdout:
            return json.loads(result.stdout)
        return None

    def get_issue(self, issue_number: int) -> GitHubIssue:
        """Get a single issue by number"""
        result = self._run_gh(
            [
                "issue",
                "view",
                str(issue_number),
                "--json",
                "number,title,body,state,author,labels,createdAt,updatedAt,comments,url",
            ]
        )

        data = json.loads(result.stdout)

        # Map gh output format to our format
        issue_data = {
            "number": data.get("number"),
            "title": data.get("title"),
            "body": data.get("body"),
            "state": data.get("state"),
            "user": {"login": data.get("author", {}).get("login", "unknown")},
            "labels": data.get("labels", []),
            "created_at": data.get("createdAt"),
            "updated_at": data.get("updatedAt"),
            "comments": len(data.get("comments", [])),
            "html_url": data.get("url"),
        }

        issue = GitHubIssue.from_dict(issue_data)

        # Add comments
        for comment_data in data.get("comments", []):
            comment = GitHubComment(
                id=comment_data.get("id", 0),
                body=comment_data.get("body", ""),
                user=GitHubUser(
                    login=comment_data.get("author", {}).get("login", "unknown")
                ),
                created_at=comment_data.get("createdAt", ""),
                updated_at=comment_data.get("updatedAt", ""),
            )
            issue.comments.append(comment)

        return issue

    def list_issues(
        self,
        state: str = "open",
        labels: Optional[List[str]] = None,
        limit: int = 30,
    ) -> List[GitHubIssue]:
        """List issues with optional filters"""
        args = [
            "issue",
            "list",
            "--state",
            state,
            "--limit",
            str(limit),
            "--json",
            "number,title,body,state,author,labels,createdAt,updatedAt,comments,url",
        ]

        if labels:
            args.extend(["--label", ",".join(labels)])

        result = self._run_gh(args)
        issues_data = json.loads(result.stdout)

        issues = []
        for data in issues_data:
            issue_data = {
                "number": data.get("number"),
                "title": data.get("title"),
                "body": data.get("body"),
                "state": data.get("state"),
                "user": {"login": data.get("author", {}).get("login", "unknown")},
                "labels": data.get("labels", []),
                "created_at": data.get("createdAt"),
                "updated_at": data.get("updatedAt"),
                "comments": len(data.get("comments", [])),
                "html_url": data.get("url"),
            }
            issues.append(GitHubIssue.from_dict(issue_data))

        return issues

    def post_comment(self, issue_number: int, body: str) -> GitHubComment:
        """Post a comment on an issue"""
        result = self._run_gh(
            [
                "issue",
                "comment",
                str(issue_number),
                "--body",
                body,
            ]
        )

        logger.info(f"Posted comment on issue #{issue_number}")

        # Return a minimal comment object (gh doesn't return the created comment)
        return GitHubComment(
            id=0,
            body=body,
            user=GitHubUser(login="sugar[bot]"),
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def add_labels(self, issue_number: int, labels: List[str]) -> None:
        """Add labels to an issue"""
        if not labels:
            return

        self._run_gh(
            [
                "issue",
                "edit",
                str(issue_number),
                "--add-label",
                ",".join(labels),
            ]
        )

        logger.info(f"Added labels {labels} to issue #{issue_number}")

    def remove_labels(self, issue_number: int, labels: List[str]) -> None:
        """Remove labels from an issue"""
        if not labels:
            return

        self._run_gh(
            [
                "issue",
                "edit",
                str(issue_number),
                "--remove-label",
                ",".join(labels),
            ]
        )

        logger.info(f"Removed labels {labels} from issue #{issue_number}")

    def search_issues(
        self,
        query: str,
        limit: int = 10,
    ) -> List[GitHubIssue]:
        """Search for issues matching a query"""
        # Build search query
        search_query = query
        if self.repo:
            search_query = f"repo:{self.repo} {query}"

        args = [
            "search",
            "issues",
            search_query,
            "--limit",
            str(limit),
            "--json",
            "number,title,body,state,author,labels,createdAt,updatedAt,url",
        ]

        result = self._run_gh(args)
        issues_data = json.loads(result.stdout)

        issues = []
        for data in issues_data:
            issue_data = {
                "number": data.get("number"),
                "title": data.get("title"),
                "body": data.get("body"),
                "state": data.get("state"),
                "user": {"login": data.get("author", {}).get("login", "unknown")},
                "labels": data.get("labels", []),
                "created_at": data.get("createdAt"),
                "updated_at": data.get("updatedAt"),
                "html_url": data.get("url"),
            }
            issues.append(GitHubIssue.from_dict(issue_data))

        return issues

    def find_similar_issues(
        self,
        issue: GitHubIssue,
        limit: int = 5,
    ) -> List[GitHubIssue]:
        """Find issues similar to the given issue"""
        import re

        # Build search query from issue title keywords
        # Remove special characters that break GitHub search
        clean_title = re.sub(r"[\[\]\(\)\{\}:\"'`]", " ", issue.title)
        keywords = [w for w in clean_title.split() if len(w) > 2][:5]

        if not keywords:
            return []

        query = " ".join(keywords)

        similar = self.search_issues(f"{query} is:issue", limit=limit + 1)

        # Filter out the current issue
        return [i for i in similar if i.number != issue.number][:limit]

    def has_maintainer_response(self, issue: GitHubIssue) -> bool:
        """Check if a maintainer has already responded"""
        # This is a heuristic - would need CODEOWNERS or team info for accuracy
        issue_author = issue.user.login

        for comment in issue.comments:
            if comment.user.login != issue_author:
                # Someone other than the author commented
                # Could be a maintainer
                return True

        return False

    def is_bot_author(self, issue: GitHubIssue) -> bool:
        """Check if the issue was created by a bot"""
        return issue.user.type == "Bot" or issue.user.login.endswith("[bot]")
