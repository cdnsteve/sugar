"""
Git Operations Utility - Handle git branching, committing, and workflow operations
"""

import asyncio
import logging
import subprocess
import re
from typing import Optional, Dict, Any
from pathlib import Path
from ..__version__ import get_version_info, __version__

logger = logging.getLogger(__name__)


class GitOperations:
    """Handle git operations for Sugar workflows"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()

    async def create_branch(self, branch_name: str, base_branch: str = "main") -> bool:
        """Create and checkout a new branch"""
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
        """Stage and commit changes"""
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
        """Push branch to remote"""
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
        """Get the name of the current branch"""
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
        """Get list of changed files"""
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
        """Check if there are uncommitted changes"""
        try:
            result = await self._run_git_command(["status", "--porcelain"])
            return bool(result["stdout"].strip())

        except Exception as e:
            logger.error(f"Error checking for uncommitted changes: {e}")
            return False

    async def get_latest_commit_sha(self) -> Optional[str]:
        """Get the SHA of the latest commit"""
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
        """Convert issue title to a slug suitable for branch names"""
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
        """Format commit message using pattern and variables"""
        try:
            return pattern.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing variable {e} in commit message pattern")
            return f"Sugar AI: {variables.get('work_summary', 'Completed work')}"

    def format_pr_title(self, pattern: str, variables: Dict[str, Any]) -> str:
        """Format PR title using pattern and variables"""
        try:
            return pattern.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing variable {e} in PR title pattern")
            return f"Fix #{variables.get('issue_number', 'unknown')}: {variables.get('issue_title', 'Unknown')}"

    def format_branch_name(self, pattern: str, variables: Dict[str, Any]) -> str:
        """Format branch name using pattern and variables"""
        try:
            return pattern.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing variable {e} in branch name pattern")
            return f"sugar/issue-{variables.get('issue_number', 'unknown')}"

    async def _run_git_command(self, args: list) -> Dict[str, Any]:
        """Run a git command and return the result"""
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
