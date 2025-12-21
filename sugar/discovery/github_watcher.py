"""
GitHub Issue Watcher - Discover work from GitHub issues and PRs
Supports both GitHub CLI (gh) and PyGithub authentication
"""

import asyncio
import logging
import subprocess
import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

# Optional PyGithub import
try:
    from github import Github, GithubException

    PYGITHUB_AVAILABLE = True
except ImportError:
    PYGITHUB_AVAILABLE = False

logger = logging.getLogger(__name__)


class GitHubWatcher:
    """Monitor GitHub repository for issues and pull requests"""

    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get("enabled", False)
        self.repo_name = config.get("repo", "")
        self.auth_method = config.get("auth_method", "auto")

        if not self.enabled:
            return

        if not self.repo_name:
            logger.warning("GitHub repo not configured - GitHub watching disabled")
            self.enabled = False
            return

        # Check authentication methods
        self.gh_cli_available = False
        self.pygithub_available = False

        # Try GitHub CLI first if specified
        if self.auth_method in ["gh_cli", "auto"]:
            self.gh_cli_available = self._check_gh_cli()

        # Try PyGithub if CLI not available or method is token/auto
        if self.auth_method in ["token", "auto"] and not self.gh_cli_available:
            self.pygithub_available = self._init_pygithub()

        # Determine if we can proceed
        if self.auth_method == "gh_cli" and not self.gh_cli_available:
            logger.warning(
                "GitHub CLI specified but not available - GitHub watching disabled"
            )
            self.enabled = False
        elif self.auth_method == "token" and not self.pygithub_available:
            logger.warning(
                "Token auth specified but PyGithub not available - GitHub watching disabled"
            )
            self.enabled = False
        elif self.auth_method == "auto" and not (
            self.gh_cli_available or self.pygithub_available
        ):
            logger.warning(
                "Neither GitHub CLI nor PyGithub available - GitHub watching disabled"
            )
            self.enabled = False

        if self.enabled:
            method = "GitHub CLI" if self.gh_cli_available else "PyGithub"
            logger.info(
                f"✅ GitHub watcher initialized for {self.repo_name} using {method}"
            )

    def _check_gh_cli(self) -> bool:
        """Check if GitHub CLI is available and authenticated"""
        try:
            gh_command = self.config.get("gh_cli", {}).get("command", "gh")

            # Check if gh CLI is available
            result = subprocess.run(
                [gh_command, "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                logger.debug("GitHub CLI not found")
                return False

            # Check if authenticated
            result = subprocess.run(
                [gh_command, "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.debug("GitHub CLI not authenticated")
                return False

            logger.info("🔑 GitHub CLI available and authenticated")
            return True

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"GitHub CLI check failed: {e}")
            return False

    def _init_pygithub(self) -> bool:
        """Initialize PyGithub if available"""
        if not PYGITHUB_AVAILABLE:
            logger.debug("PyGithub not available")
            return False

        token = self.config.get("token", "") or os.getenv("GITHUB_TOKEN", "")
        if not token:
            logger.debug("No GitHub token configured")
            return False

        try:
            self.github = Github(token)
            # Test the connection
            repo = self.github.get_repo(self.repo_name)
            logger.info("🔑 PyGithub initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize PyGithub: {e}")
            return False

    async def discover(self) -> List[Dict[str, Any]]:
        """Discover work items from GitHub issues and PRs"""
        if not self.enabled:
            return []

        work_items = []

        try:
            if self.gh_cli_available:
                # Use GitHub CLI
                issues_work = await self._discover_issues_gh_cli()
                work_items.extend(issues_work)
            elif self.pygithub_available:
                # Use PyGithub
                issues_work = await self._discover_issues_pygithub()
                work_items.extend(issues_work)

        except Exception as e:
            logger.error(f"Error discovering GitHub work: {e}")

        logger.debug(f"🔍 GitHubWatcher discovered {len(work_items)} work items")
        return work_items

    async def _discover_issues_gh_cli(self) -> List[Dict[str, Any]]:
        """Discover work from GitHub issues using GitHub CLI"""
        work_items = []

        try:
            gh_command = self.config.get("gh_cli", {}).get("command", "gh")
            issue_labels = self.config.get("issue_labels", ["bug", "enhancement"])

            # Log the label filtering mode being used
            self._log_label_filtering_mode(issue_labels)

            # Get all open issues first (we'll filter by labels after)
            cmd = [
                gh_command,
                "issue",
                "list",
                "--repo",
                self.repo_name,
                "--state",
                "open",
                "--limit",
                "50",  # Get more issues to filter from
                "--json",
                "number,title,body,labels,assignees,comments,createdAt,updatedAt,url",
            ]

            # Note: We don't use --label flag here because it uses AND logic
            # Instead we'll filter by labels after getting the results

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.error(f"GitHub CLI issue command failed: {result.stderr}")
                return []

            issues = json.loads(result.stdout)

            # Filter issues by labels with flexible filtering modes
            filtered_issues = []
            for issue in issues:
                issue_label_names = [
                    label["name"].lower() for label in issue.get("labels", [])
                ]
                config_labels = [label.lower() for label in issue_labels]

                # Determine if this issue should be included based on label filtering mode
                should_include = self._should_include_issue_by_labels(
                    issue_label_names, config_labels, issue_labels
                )

                if should_include:
                    filtered_issues.append(issue)

            # Limit to 10 issues after filtering
            filtered_issues = filtered_issues[:10]

            logger.debug(
                f"Found {len(issues)} total issues, {len(filtered_issues)} match filtering criteria"
            )

            for issue in filtered_issues:
                work_item = self._create_work_item_from_issue_data(issue)
                if work_item:
                    work_items.append(work_item)

        except Exception as e:
            logger.error(f"Error getting issues via GitHub CLI: {e}")

        return work_items

    async def _discover_issues_pygithub(self) -> List[Dict[str, Any]]:
        """Discover work from GitHub issues using PyGithub"""
        work_items = []

        try:
            # Get recent issues
            since = datetime.now(timezone.utc) - timedelta(days=7)
            repo = self.github.get_repo(self.repo_name)
            issues = repo.get_issues(state="open", since=since, sort="created")

            issue_labels = self.config.get("issue_labels", ["bug", "enhancement"])

            # Log the label filtering mode being used
            self._log_label_filtering_mode(issue_labels)

            processed_count = 0
            for issue in issues:
                # Skip pull requests (they show up in issues)
                if issue.pull_request:
                    continue

                # Apply label filtering
                issue_label_names = [label.name.lower() for label in issue.labels]
                config_labels = [label.lower() for label in issue_labels]

                if not self._should_include_issue_by_labels(
                    issue_label_names, config_labels, issue_labels
                ):
                    continue

                # Convert PyGithub issue to dict format
                issue_data = {
                    "number": issue.number,
                    "title": issue.title,
                    "body": issue.body,
                    "labels": [{"name": label.name} for label in issue.labels],
                    "assignees": (
                        [{"login": issue.assignee.login}] if issue.assignee else []
                    ),
                    "comments": issue.comments,
                    "createdAt": issue.created_at.isoformat(),
                    "updatedAt": issue.updated_at.isoformat(),
                    "url": issue.html_url,
                }

                work_item = self._create_work_item_from_issue_data(issue_data)
                if work_item:
                    work_items.append(work_item)
                    processed_count += 1

                # Limit to 10 issues after filtering
                if processed_count >= 10:
                    break

        except Exception as e:
            logger.error(f"GitHub API error getting issues: {e}")

        return work_items

    def _create_work_item_from_issue_data(
        self, issue: dict
    ) -> Optional[Dict[str, Any]]:
        """Create work item from GitHub issue data (works with both CLI and PyGithub)"""

        # Determine work type from labels
        work_type = "feature"  # default
        priority = 3  # default

        labels = [label["name"].lower() for label in issue.get("labels", [])]

        if any(label in labels for label in ["bug", "error", "critical"]):
            work_type = "bug_fix"
            priority = 4
        elif any(label in labels for label in ["enhancement", "feature"]):
            work_type = "feature"
            priority = 3
        elif any(label in labels for label in ["documentation", "docs"]):
            work_type = "documentation"
            priority = 2
        elif any(label in labels for label in ["test", "testing"]):
            work_type = "test"
            priority = 3

        # Increase priority for urgent labels
        if any(label in labels for label in ["urgent", "high priority", "critical"]):
            priority = min(5, priority + 1)

        # Skip if assigned to someone else (optional)
        assignees = issue.get("assignees", [])
        if self.config.get("only_unassigned", False) and assignees:
            return None

        work_item = {
            "type": work_type,
            "title": f"Address GitHub issue: {issue['title']}",
            "description": self._format_issue_description(issue),
            "priority": priority,
            "source": "github_watcher",
            "source_file": f"github://issues/{issue['number']}",
            "context": {
                "github_issue": {
                    "number": issue["number"],
                    "url": issue["url"],
                    "labels": labels,
                    "assignees": [a.get("login") for a in issue.get("assignees", [])],
                    "comments": issue.get("comments", 0),
                    "created_at": issue["createdAt"],
                    "updated_at": issue["updatedAt"],
                },
                "discovered_at": datetime.now(timezone.utc).isoformat(),
                "source_type": "github_issue",
            },
        }

        return work_item

    def _format_issue_description(self, issue: dict) -> str:
        """Format GitHub issue into work description"""
        description_parts = [
            f"**GitHub Issue #{issue['number']}**",
            f"URL: {issue['url']}",
            f"Created: {issue['createdAt']}",
            f"Comments: {issue.get('comments', 0)}",
            "",
        ]

        if issue.get("labels"):
            label_names = [label["name"] for label in issue["labels"]]
            description_parts.append(f"Labels: {', '.join(label_names)}")
            description_parts.append("")

        assignees = issue.get("assignees", [])
        if assignees:
            assignee_names = [a.get("login", "unknown") for a in assignees]
            description_parts.append(f"Assigned to: {', '.join(assignee_names)}")
            description_parts.append("")

        description_parts.append("**Issue Description:**")
        description_parts.append(issue.get("body") or "No description provided.")

        return "\n".join(description_parts)

    async def health_check(self) -> dict:
        """Return health status of GitHub watcher"""
        if not self.enabled:
            return {
                "enabled": False,
                "reason": "GitHub integration disabled or not configured",
            }

        method = "GitHub CLI" if self.gh_cli_available else "PyGithub"

        try:
            if self.gh_cli_available:
                # Test GitHub CLI
                gh_command = self.config.get("gh_cli", {}).get("command", "gh")
                result = subprocess.run(
                    [gh_command, "auth", "status"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                auth_ok = result.returncode == 0

                return {
                    "enabled": True,
                    "method": method,
                    "repository": self.repo_name,
                    "authenticated": auth_ok,
                    "last_check": datetime.now(timezone.utc).isoformat(),
                }
            elif self.pygithub_available:
                # Test PyGithub API access
                rate_limit = self.github.get_rate_limit()

                return {
                    "enabled": True,
                    "method": method,
                    "repository": self.repo_name,
                    "api_rate_limit": {
                        "remaining": rate_limit.core.remaining,
                        "limit": rate_limit.core.limit,
                        "reset": rate_limit.core.reset.isoformat(),
                    },
                    "last_check": datetime.now(timezone.utc).isoformat(),
                }

        except Exception as e:
            return {
                "enabled": True,
                "method": method,
                "error": str(e),
                "last_check": datetime.now(timezone.utc).isoformat(),
            }

    async def comment_on_issue(self, issue_number: int, comment_body: str) -> bool:
        """Add a comment to a GitHub issue"""
        if not self.enabled:
            return False

        try:
            if self.gh_cli_available:
                return await self._comment_via_gh_cli(issue_number, comment_body)
            elif self.pygithub_available:
                return await self._comment_via_pygithub(issue_number, comment_body)
            else:
                logger.warning(
                    "No GitHub authentication method available for commenting"
                )
                return False

        except Exception as e:
            logger.error(f"Error commenting on GitHub issue #{issue_number}: {e}")
            return False

    async def assign_issue(self, issue_number: int) -> bool:
        """Assign a GitHub issue to the authenticated user"""
        if not self.enabled:
            return False

        try:
            if self.gh_cli_available:
                return await self._assign_via_gh_cli(issue_number)
            elif self.pygithub_available:
                return await self._assign_via_pygithub(issue_number)
            else:
                logger.warning(
                    "No GitHub authentication method available for assignment"
                )
                return False

        except Exception as e:
            logger.error(f"Error assigning GitHub issue #{issue_number}: {e}")
            return False

    async def _comment_via_gh_cli(self, issue_number: int, comment_body: str) -> bool:
        """Add comment using GitHub CLI"""
        try:
            gh_command = self.config.get("gh_cli", {}).get("command", "gh")

            cmd = [
                gh_command,
                "issue",
                "comment",
                str(issue_number),
                "--repo",
                self.repo_name,
                "--body",
                comment_body,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info(f"✅ Added comment to GitHub issue #{issue_number}")
                return True
            else:
                logger.error(f"GitHub CLI comment failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error using GitHub CLI to comment: {e}")
            return False

    async def _comment_via_pygithub(self, issue_number: int, comment_body: str) -> bool:
        """Add comment using PyGithub"""
        try:
            repo = self.github.get_repo(self.repo_name)
            issue = repo.get_issue(issue_number)
            issue.create_comment(comment_body)
            logger.info(f"✅ Added comment to GitHub issue #{issue_number}")
            return True

        except Exception as e:
            logger.error(f"Error using PyGithub to comment: {e}")
            return False

    async def _assign_via_gh_cli(self, issue_number: int) -> bool:
        """Assign issue using GitHub CLI"""
        try:
            gh_command = self.config.get("gh_cli", {}).get("command", "gh")

            cmd = [
                gh_command,
                "issue",
                "edit",
                str(issue_number),
                "--repo",
                self.repo_name,
                "--add-assignee",
                "@me",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info(
                    f"✅ Assigned GitHub issue #{issue_number} to authenticated user"
                )
                return True
            else:
                logger.error(f"GitHub CLI assignment failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error using GitHub CLI to assign: {e}")
            return False

    async def _assign_via_pygithub(self, issue_number: int) -> bool:
        """Assign issue using PyGithub"""
        try:
            repo = self.github.get_repo(self.repo_name)
            issue = repo.get_issue(issue_number)

            # Get current user
            user = self.github.get_user()

            # Add current user to assignees (preserving existing ones)
            current_assignees = [assignee.login for assignee in issue.assignees]
            if user.login not in current_assignees:
                current_assignees.append(user.login)
                issue.edit(assignees=current_assignees)
                logger.info(f"✅ Assigned GitHub issue #{issue_number} to {user.login}")
            else:
                logger.debug(
                    f"GitHub issue #{issue_number} already assigned to {user.login}"
                )

            return True

        except Exception as e:
            logger.error(f"Error using PyGithub to assign: {e}")
            return False

    def _should_include_issue_by_labels(
        self, issue_labels: list, config_labels: list, original_config: list
    ) -> bool:
        """Determine if an issue should be included based on label filtering configuration"""

        # Mode 1: Empty list [] - No filtering, include ALL issues
        if not original_config:
            return True

        # Mode 2: Wildcard ["*"] - Include issues that have ANY labels (exclude unlabeled)
        if len(original_config) == 1 and original_config[0] == "*":
            return len(issue_labels) > 0

        # Mode 3: Unlabeled ["unlabeled"] - Include only issues WITHOUT labels
        if len(original_config) == 1 and original_config[0].lower() == "unlabeled":
            return len(issue_labels) == 0

        # Mode 4: Specific labels - Include issues that have at least one matching label
        return any(label in issue_labels for label in config_labels)

    def _log_label_filtering_mode(self, issue_labels: list):
        """Log what label filtering mode is being used"""
        if not issue_labels:
            logger.debug("🏷️ Label filtering: ALL open issues (no label restrictions)")
        elif len(issue_labels) == 1 and issue_labels[0] == "*":
            logger.debug(
                "🏷️ Label filtering: Issues with ANY labels (excluding unlabeled)"
            )
        elif len(issue_labels) == 1 and issue_labels[0].lower() == "unlabeled":
            logger.debug("🏷️ Label filtering: Only UNLABELED issues")
        else:
            logger.debug(f"🏷️ Label filtering: Issues with labels: {issue_labels}")

    async def close_issue(
        self, issue_number: int, completion_comment: str = None
    ) -> bool:
        """Close a GitHub issue after successful completion"""
        if not self.enabled:
            return False

        try:
            if self.gh_cli_available:
                return await self._close_issue_via_gh_cli(
                    issue_number, completion_comment
                )
            elif self.pygithub_available:
                return await self._close_issue_via_pygithub(
                    issue_number, completion_comment
                )
            else:
                logger.warning(
                    "No GitHub authentication method available for closing issues"
                )
                return False

        except Exception as e:
            logger.error(f"Error closing GitHub issue #{issue_number}: {e}")
            return False

    async def create_pull_request(
        self, branch_name: str, title: str, body: str, base_branch: str = "main"
    ) -> Optional[str]:
        """Create a pull request from a branch"""
        if not self.enabled:
            return None

        try:
            if self.gh_cli_available:
                return await self._create_pr_via_gh_cli(
                    branch_name, title, body, base_branch
                )
            elif self.pygithub_available:
                return await self._create_pr_via_pygithub(
                    branch_name, title, body, base_branch
                )
            else:
                logger.warning(
                    "No GitHub authentication method available for creating PRs"
                )
                return None

        except Exception as e:
            logger.error(f"Error creating pull request: {e}")
            return None

    async def _close_issue_via_gh_cli(
        self, issue_number: int, completion_comment: str = None
    ) -> bool:
        """Close issue using GitHub CLI"""
        try:
            gh_command = self.config.get("gh_cli", {}).get("command", "gh")

            # Add final comment if provided
            if completion_comment:
                comment_success = await self._comment_via_gh_cli(
                    issue_number, completion_comment
                )
                if not comment_success:
                    logger.warning(
                        f"Could not add final comment to issue #{issue_number}"
                    )

            # Close the issue
            cmd = [
                gh_command,
                "issue",
                "close",
                str(issue_number),
                "--repo",
                self.repo_name,
                "--comment",
                "Completed by Sugar AI - closing issue.",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info(f"🔒 Closed GitHub issue #{issue_number}")
                return True
            else:
                logger.error(f"GitHub CLI close failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error using GitHub CLI to close issue: {e}")
            return False

    async def _close_issue_via_pygithub(
        self, issue_number: int, completion_comment: str = None
    ) -> bool:
        """Close issue using PyGithub"""
        try:
            repo = self.github.get_repo(self.repo_name)
            issue = repo.get_issue(issue_number)

            # Add final comment if provided
            if completion_comment:
                try:
                    issue.create_comment(completion_comment)
                except Exception as e:
                    logger.warning(
                        f"Could not add final comment to issue #{issue_number}: {e}"
                    )

            # Close the issue
            issue.edit(state="closed")
            logger.info(f"🔒 Closed GitHub issue #{issue_number}")
            return True

        except Exception as e:
            logger.error(f"Error using PyGithub to close issue: {e}")
            return False

    async def _create_pr_via_gh_cli(
        self, branch_name: str, title: str, body: str, base_branch: str = "main"
    ) -> Optional[str]:
        """Create PR using GitHub CLI"""
        try:
            gh_command = self.config.get("gh_cli", {}).get("command", "gh")

            cmd = [
                gh_command,
                "pr",
                "create",
                "--repo",
                self.repo_name,
                "--title",
                title,
                "--body",
                body,
                "--base",
                base_branch,
                "--head",
                branch_name,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                pr_url = result.stdout.strip()
                logger.info(f"🔀 Created pull request: {pr_url}")
                return pr_url
            else:
                logger.error(f"GitHub CLI PR creation failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Error using GitHub CLI to create PR: {e}")
            return None

    async def _create_pr_via_pygithub(
        self, branch_name: str, title: str, body: str, base_branch: str = "main"
    ) -> Optional[str]:
        """Create PR using PyGithub"""
        try:
            repo = self.github.get_repo(self.repo_name)

            pr = repo.create_pull(
                title=title, body=body, head=branch_name, base=base_branch
            )

            logger.info(f"🔀 Created pull request #{pr.number}: {pr.html_url}")
            return pr.html_url

        except Exception as e:
            logger.error(f"Error using PyGithub to create PR: {e}")
            return None
