"""
Git Operations Utility Module

This module provides asynchronous Git operations for Sugar's automated development workflows.
It handles common Git tasks such as branch creation, committing changes, pushing to remotes,
and querying repository state.

The GitOperations class wraps git CLI commands with async execution, making it suitable
for integration with asyncio-based orchestration systems.

Example usage:
    git_ops = GitOperations("/path/to/repo")

    # Create a feature branch
    await git_ops.create_branch("feature/new-feature", base_branch="main")

    # Commit changes
    await git_ops.commit_changes("feat: implement new feature")

    # Push to remote
    await git_ops.push_branch("feature/new-feature")

Note:
    All Git operations are executed via subprocess and require git to be installed
    and available in the system PATH.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class GitOperations:
    """
    Asynchronous Git operations handler for Sugar workflows.

    This class provides an async interface to common Git operations used in
    Sugar's automated development pipelines. It wraps git CLI commands and
    executes them asynchronously using asyncio subprocesses.

    Attributes:
        repo_path (Path): Absolute path to the Git repository root directory.

    Example:
        >>> git_ops = GitOperations(".")
        >>> branch = await git_ops.get_current_branch()
        >>> print(f"Currently on branch: {branch}")
    """

    def __init__(self, repo_path: str = ".") -> None:
        """
        Initialize GitOperations with a repository path.

        Args:
            repo_path: Path to the Git repository. Defaults to current directory.
                      Will be resolved to an absolute path.
        """
        self.repo_path = Path(repo_path).resolve()

    async def create_branch(self, branch_name: str, base_branch: str = "main") -> bool:
        """
        Create and checkout a new Git branch.

        This method performs the following steps:
        1. Checks out the base branch
        2. Pulls latest changes from origin
        3. Creates and checks out the new branch

        Args:
            branch_name: Name of the new branch to create.
            base_branch: Branch to base the new branch on. Defaults to "main".

        Returns:
            True if the branch was created and checked out successfully, False otherwise.

        Note:
            This method assumes a remote named "origin" exists. If the pull fails
            (e.g., no remote configured), branch creation may still succeed but
            won't have the latest remote changes.
        """
        try:
            # Ensure we're on the base branch and it's up to date
            await self._run_git_command(["checkout", base_branch])
            await self._run_git_command(["pull", "origin", base_branch])

            # Create and checkout new branch
            result = await self._run_git_command(["checkout", "-b", branch_name])

            if result["returncode"] == 0:
                logger.info(f"🌿 Created and checked out branch: {branch_name}")
                return True
            else:
                logger.error(
                    f"Failed to create branch {branch_name}: {result['stderr']}"
                )
                return False

        except Exception as e:
            logger.error(f"Error creating branch {branch_name}: {e}")
            return False

    async def commit_changes(self, commit_message: str, add_all: bool = True) -> bool:
        """
        Stage and commit changes to the repository.

        Args:
            commit_message: The commit message. Should be pre-formatted by the caller
                           (e.g., by WorkflowOrchestrator using format_commit_message).
            add_all: If True, stages all changes (git add .) before committing.
                    If False, only commits already-staged changes. Defaults to True.

        Returns:
            True if commit succeeded or if there were no changes to commit.
            False if the commit operation failed.

        Note:
            Returns True (not False) when there are no changes to commit, since
            this is not considered an error condition in automated workflows.
        """
        try:
            # Stage changes
            if add_all:
                await self._run_git_command(["add", "."])

            # Check if there are changes to commit
            status_result = await self._run_git_command(["status", "--porcelain"])
            if not status_result["stdout"].strip():
                logger.info("No changes to commit")
                return True

            # Commit changes (message already formatted by WorkflowOrchestrator)
            result = await self._run_git_command(["commit", "-m", commit_message])

            if result["returncode"] == 0:
                logger.info(f"📝 Committed changes: {commit_message}")
                return True
            else:
                logger.error(f"Failed to commit changes: {result['stderr']}")
                return False

        except Exception as e:
            logger.error(f"Error committing changes: {e}")
            return False

    async def push_branch(self, branch_name: str, set_upstream: bool = True) -> bool:
        """
        Push a branch to the remote repository.

        Args:
            branch_name: Name of the branch to push.
            set_upstream: If True, sets up tracking with -u flag (git push -u origin).
                         Useful for newly created branches. Defaults to True.

        Returns:
            True if the push succeeded, False otherwise.

        Note:
            Assumes the remote is named "origin". Will fail if the remote doesn't
            exist or if there are authentication issues.
        """
        try:
            if set_upstream:
                cmd = ["push", "-u", "origin", branch_name]
            else:
                cmd = ["push", "origin", branch_name]

            result = await self._run_git_command(cmd)

            if result["returncode"] == 0:
                logger.info(f"📤 Pushed branch: {branch_name}")
                return True
            else:
                logger.error(f"Failed to push branch {branch_name}: {result['stderr']}")
                return False

        except Exception as e:
            logger.error(f"Error pushing branch {branch_name}: {e}")
            return False

    async def get_current_branch(self) -> Optional[str]:
        """
        Get the name of the currently checked out branch.

        Returns:
            The branch name as a string, or None if the operation failed
            (e.g., in a detached HEAD state or not in a Git repository).
        """
        try:
            result = await self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])

            if result["returncode"] == 0:
                return result["stdout"].strip()
            else:
                logger.error(f"Failed to get current branch: {result['stderr']}")
                return None

        except Exception as e:
            logger.error(f"Error getting current branch: {e}")
            return None

    async def get_changed_files(self) -> list:
        """
        Get a list of files that have changed since the last commit.

        Returns:
            A list of file paths (relative to repo root) that have been modified.
            Returns an empty list if no files changed or if an error occurred.

        Note:
            This compares against HEAD, so it shows uncommitted changes only.
            Staged and unstaged changes are both included.
        """
        try:
            result = await self._run_git_command(["diff", "--name-only", "HEAD"])

            if result["returncode"] == 0:
                files = [f.strip() for f in result["stdout"].split("\n") if f.strip()]
                return files
            else:
                return []

        except Exception as e:
            logger.error(f"Error getting changed files: {e}")
            return []

    async def has_uncommitted_changes(self) -> bool:
        """
        Check if the repository has uncommitted changes.

        This includes both staged and unstaged changes, as well as untracked files.

        Returns:
            True if there are any uncommitted changes, False if the working
            directory is clean. Returns False on error (fails safe).
        """
        try:
            result = await self._run_git_command(["status", "--porcelain"])
            return bool(result["stdout"].strip())

        except Exception as e:
            logger.error(f"Error checking for uncommitted changes: {e}")
            return False

    async def get_latest_commit_sha(self) -> Optional[str]:
        """
        Get the full SHA hash of the latest commit (HEAD).

        Returns:
            The 40-character SHA hash of HEAD, or None if the operation failed
            (e.g., repository has no commits or not in a Git repository).
        """
        try:
            result = await self._run_git_command(["rev-parse", "HEAD"])

            if result["returncode"] == 0:
                return result["stdout"].strip()
            else:
                logger.error(f"Failed to get latest commit SHA: {result['stderr']}")
                return None

        except Exception as e:
            logger.error(f"Error getting latest commit SHA: {e}")
            return None

    def slugify_title(self, title: str) -> str:
        """
        Convert an issue title to a URL-safe slug suitable for branch names.

        Performs the following transformations:
        1. Removes "Address GitHub issue: " prefix if present
        2. Converts to lowercase
        3. Removes special characters (keeps alphanumeric, spaces, hyphens)
        4. Replaces spaces and multiple hyphens with single hyphens
        5. Strips leading/trailing hyphens
        6. Truncates to 50 characters maximum

        Args:
            title: The issue title or text to slugify.

        Returns:
            A lowercase, hyphen-separated slug safe for use in branch names.

        Example:
            >>> git_ops.slugify_title("Fix: User authentication bug!")
            'fix-user-authentication-bug'
        """
        # Remove "Address GitHub issue: " prefix if present
        if title.startswith("Address GitHub issue: "):
            title = title[22:]

        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[-\s]+", "-", slug)
        slug = slug.strip("-")

        # Limit length for practical branch names
        if len(slug) > 50:
            slug = slug[:50].rstrip("-")

        return slug

    def format_commit_message(self, pattern: str, variables: Dict[str, Any]) -> str:
        """
        Format a commit message by substituting variables into a pattern.

        Args:
            pattern: A format string with placeholders, e.g.,
                    "fix(#{issue_number}): {work_summary}"
            variables: Dictionary of values to substitute into the pattern.
                      Common keys: issue_number, work_summary, issue_title.

        Returns:
            The formatted commit message. Falls back to a generic message
            if required variables are missing from the pattern.

        Example:
            >>> git_ops.format_commit_message(
            ...     "fix(#{issue_number}): {work_summary}",
            ...     {"issue_number": 42, "work_summary": "resolve auth bug"}
            ... )
            'fix(#42): resolve auth bug'
        """
        try:
            return pattern.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing variable {e} in commit message pattern")
            return f"Sugar AI: {variables.get('work_summary', 'Completed work')}"

    def format_pr_title(self, pattern: str, variables: Dict[str, Any]) -> str:
        """
        Format a pull request title by substituting variables into a pattern.

        Args:
            pattern: A format string with placeholders, e.g.,
                    "Fix #{issue_number}: {issue_title}"
            variables: Dictionary of values to substitute into the pattern.
                      Common keys: issue_number, issue_title.

        Returns:
            The formatted PR title. Falls back to a generic title format
            if required variables are missing from the pattern.

        Example:
            >>> git_ops.format_pr_title(
            ...     "Fix #{issue_number}: {issue_title}",
            ...     {"issue_number": 42, "issue_title": "Login fails on mobile"}
            ... )
            'Fix #42: Login fails on mobile'
        """
        try:
            return pattern.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing variable {e} in PR title pattern")
            return f"Fix #{variables.get('issue_number', 'unknown')}: {variables.get('issue_title', 'Unknown')}"

    def format_branch_name(self, pattern: str, variables: Dict[str, Any]) -> str:
        """
        Format a branch name by substituting variables into a pattern.

        Args:
            pattern: A format string with placeholders, e.g.,
                    "sugar/issue-{issue_number}-{title_slug}"
            variables: Dictionary of values to substitute into the pattern.
                      Common keys: issue_number, title_slug.

        Returns:
            The formatted branch name. Falls back to "sugar/issue-{number}"
            if required variables are missing from the pattern.

        Example:
            >>> git_ops.format_branch_name(
            ...     "feature/{issue_number}-{title_slug}",
            ...     {"issue_number": 42, "title_slug": "add-login"}
            ... )
            'feature/42-add-login'
        """
        try:
            return pattern.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing variable {e} in branch name pattern")
            return f"sugar/issue-{variables.get('issue_number', 'unknown')}"

    async def _run_git_command(self, args: list) -> Dict[str, Any]:
        """
        Execute a git command asynchronously and return the result.

        This is the internal helper method used by all public Git operations.
        It runs commands via asyncio subprocess for non-blocking execution.

        Args:
            args: List of arguments to pass to git (without the 'git' prefix).
                  Example: ["checkout", "-b", "feature-branch"]

        Returns:
            A dictionary containing:
            - returncode (int): The process exit code (0 = success).
            - stdout (str): Standard output from the command.
            - stderr (str): Standard error from the command.
            - command (str): The full command that was executed (for debugging).

        Note:
            On error, returns returncode=1 with stderr containing the exception message.
            Commands are executed in the repository directory specified at init time.
        """
        cmd = ["git"] + args

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.repo_path,
            )

            stdout, stderr = await process.communicate()

            return {
                "returncode": process.returncode,
                "stdout": stdout.decode("utf-8") if stdout else "",
                "stderr": stderr.decode("utf-8") if stderr else "",
                "command": " ".join(cmd),
            }

        except Exception as e:
            logger.error(f"Error running git command {' '.join(cmd)}: {e}")
            return {
                "returncode": 1,
                "stdout": "",
                "stderr": str(e),
                "command": " ".join(cmd),
            }
