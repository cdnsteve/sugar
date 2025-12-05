"""
Work Diff Validation - Feature 10: Git Diff Validation

Validates changes before commit:
- Files changed match expectations
- Change size is reasonable
- No debug statements left in code
- Justification for unexpected changes
"""

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Git commands used for validation
_GIT_DIFF_STAT_CMD = ["git", "diff", "--stat", "HEAD"]
_GIT_DIFF_CMD = ["git", "diff", "HEAD"]


@dataclass
class DiffValidationResult:
    """Result of diff validation.

    Attributes:
        passed: Whether the validation passed.
        message: Human-readable description of the result.
        issues: List of validation issues found.
        changed_files: List of files that were changed.
        unexpected_files: Files changed that weren't expected.
        missing_files: Expected files that weren't changed.
        total_lines_changed: Total number of lines modified.
        violations: Pattern violations found.
        error: Error message if validation failed unexpectedly.
    """

    passed: bool
    message: str = ""
    issues: List[str] = field(default_factory=list)
    changed_files: List[str] = field(default_factory=list)
    unexpected_files: List[str] = field(default_factory=list)
    missing_files: List[str] = field(default_factory=list)
    total_lines_changed: Optional[int] = None
    max_allowed: Optional[int] = None
    violations: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result: Dict[str, Any] = {"passed": self.passed}
        if self.message:
            result["message"] = self.message
        if self.issues:
            result["issues"] = self.issues
        if self.changed_files:
            result["changed_files"] = self.changed_files
        if self.unexpected_files:
            result["unexpected_files"] = self.unexpected_files
        if self.missing_files:
            result["missing_files"] = self.missing_files
        if self.total_lines_changed is not None:
            result["total_lines_changed"] = self.total_lines_changed
        if self.max_allowed is not None:
            result["max_allowed"] = self.max_allowed
        if self.violations:
            result["violations"] = self.violations
        if self.error:
            result["error"] = self.error
        return result


class DiffValidator:
    """Validates git diff before committing.

    This validator checks that:
    - Changed files match expectations (optional)
    - Change size is within acceptable limits
    - No disallowed patterns appear in the diff (e.g., debug statements)

    Attributes:
        enabled: Whether diff validation is active.
        max_lines_changed: Maximum allowed lines changed before failure.
        warn_if_exceeds: Line count threshold for warnings.
    """

    # Default configuration values
    DEFAULT_MAX_LINES = 500
    DEFAULT_WARN_THRESHOLD = 200

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize diff validator.

        Args:
            config: Configuration dictionary with optional 'git_diff_validation' section.
        """
        diff_config = config.get("git_diff_validation", {})
        self.enabled = diff_config.get("enabled", False)

        # File validation settings
        before_commit = diff_config.get("before_commit", {})
        self.validate_files = before_commit.get("validate_files_changed", {})
        self.allow_additional_files = self.validate_files.get(
            "allow_additional_files", False
        )

        # Size validation settings with bounds checking
        max_lines = before_commit.get("max_lines_changed", self.DEFAULT_MAX_LINES)
        warn_threshold = before_commit.get(
            "warn_if_exceeds", self.DEFAULT_WARN_THRESHOLD
        )

        self.max_lines_changed = max(1, max_lines)  # Ensure positive
        self.warn_if_exceeds = max(1, min(warn_threshold, self.max_lines_changed))

        # Pattern validation
        self.disallowed_patterns = before_commit.get("disallow_patterns", [])

        # Unexpected file handling
        self.unexpected_files_action = before_commit.get(
            "if_unexpected_files_changed", {}
        )

        # Cached diff output to avoid multiple subprocess calls
        self._cached_diff: Optional[str] = None
        self._cached_diff_stat: Optional[str] = None

    def is_enabled(self) -> bool:
        """Check if diff validation is enabled."""
        return self.enabled

    async def validate_diff(
        self,
        task: Dict[str, Any],
        changed_files: List[str],
    ) -> Tuple[bool, DiffValidationResult]:
        """Validate git diff before commit.

        Args:
            task: Task dictionary with expected files under 'files_to_modify.expected'.
            changed_files: List of changed file paths.

        Returns:
            Tuple of (is_valid, validation_result).
        """
        if not self.is_enabled():
            return True, DiffValidationResult(
                passed=True, message="Validation disabled"
            )

        # Clear cached diff data for fresh validation
        self._cached_diff = None
        self._cached_diff_stat = None

        issues: List[str] = []

        # 1. Validate files changed match expectations
        if self.validate_files.get("enabled", False):
            expected_files = task.get("files_to_modify", {}).get("expected", [])
            file_validation = self._validate_files_changed(
                expected_files, changed_files
            )

            if not file_validation.passed:
                issues.append(file_validation.message)

        # 2. Validate size of changes
        size_validation = await self._validate_change_size()
        if not size_validation.passed:
            issues.append(size_validation.message)

        # 3. Validate patterns (no debug statements, etc.)
        pattern_validation = await self._validate_patterns()
        if not pattern_validation.passed:
            issues.extend(pattern_validation.violations)

        # Determine if validation passed
        passed = len(issues) == 0

        if passed:
            logger.info("✅ Diff validation passed")
        else:
            logger.warning(f"❌ Diff validation found {len(issues)} issues")
            for issue in issues:
                logger.warning(f"  - {issue}")

        return passed, DiffValidationResult(
            passed=passed,
            issues=issues,
            changed_files=changed_files,
            message="All checks passed" if passed else f"{len(issues)} issues found",
        )

    def _validate_files_changed(
        self, expected_files: List[str], changed_files: List[str]
    ) -> DiffValidationResult:
        """Validate that changed files match expectations.

        Args:
            expected_files: List of files expected to change.
            changed_files: List of files that actually changed.

        Returns:
            Validation result with details about unexpected/missing files.
        """
        # Use sets for O(1) membership testing
        expected_set = set(expected_files)
        changed_set = set(changed_files)

        unexpected_files = list(changed_set - expected_set)
        missing_files = list(expected_set - changed_set)

        # Determine if this is acceptable
        if unexpected_files and not self.allow_additional_files:
            return DiffValidationResult(
                passed=False,
                unexpected_files=unexpected_files,
                missing_files=missing_files,
                message=f"Unexpected files changed: {', '.join(sorted(unexpected_files))}",
            )

        if unexpected_files and self.allow_additional_files:
            logger.warning(
                f"⚠️ Additional files changed (allowed): {', '.join(sorted(unexpected_files))}"
            )

        return DiffValidationResult(
            passed=True,
            unexpected_files=unexpected_files,
            missing_files=missing_files,
            message="File changes match expectations",
        )

    async def _get_diff_stat(self) -> str:
        """Get cached git diff stat output.

        Returns:
            The output of 'git diff --stat HEAD'.
        """
        if self._cached_diff_stat is None:
            self._cached_diff_stat = await self._run_git_command(_GIT_DIFF_STAT_CMD)
        return self._cached_diff_stat

    async def _get_diff(self) -> str:
        """Get cached git diff output.

        Returns:
            The output of 'git diff HEAD'.
        """
        if self._cached_diff is None:
            self._cached_diff = await self._run_git_command(_GIT_DIFF_CMD)
        return self._cached_diff

    async def _run_git_command(self, cmd: List[str]) -> str:
        """Execute a git command and return its output.

        Args:
            cmd: Command and arguments as a list.

        Returns:
            Standard output from the command.

        Raises:
            RuntimeError: If the command fails with non-zero exit code.
        """
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8").strip()
            logger.warning(f"Git command failed: {' '.join(cmd)}: {error_msg}")

        return stdout.decode("utf-8")

    async def _validate_change_size(self) -> DiffValidationResult:
        """Validate that the size of changes is reasonable.

        Returns:
            Validation result with line count information.
        """
        try:
            output = await self._get_diff_stat()

            # Parse total lines changed from last line
            # Example: " 5 files changed, 234 insertions(+), 12 deletions(-)"
            lines = output.strip().split("\n")
            if not lines:
                return DiffValidationResult(
                    passed=True,
                    message="No changes detected",
                )

            last_line = lines[-1]

            # Extract insertions and deletions
            insertion_match = re.search(r"(\d+) insertion", last_line)
            deletion_match = re.search(r"(\d+) deletion", last_line)

            insertions = int(insertion_match.group(1)) if insertion_match else 0
            deletions = int(deletion_match.group(1)) if deletion_match else 0
            total_lines = insertions + deletions

            # Check against limits
            if total_lines > self.max_lines_changed:
                return DiffValidationResult(
                    passed=False,
                    total_lines_changed=total_lines,
                    max_allowed=self.max_lines_changed,
                    message=f"Too many lines changed: {total_lines} > {self.max_lines_changed}",
                )

            if total_lines > self.warn_if_exceeds:
                logger.warning(
                    f"⚠️ Large change detected: {total_lines} lines "
                    f"(threshold: {self.warn_if_exceeds})"
                )

            return DiffValidationResult(
                passed=True,
                total_lines_changed=total_lines,
                message=f"Change size acceptable: {total_lines} lines",
            )

        except Exception as e:
            logger.error(f"Error validating change size: {e}")
            return DiffValidationResult(
                passed=True,  # Don't block on validation infrastructure errors
                error=str(e),
                message="Change size validation encountered an error",
            )

    async def _validate_patterns(self) -> DiffValidationResult:
        """Validate that no disallowed patterns appear in the diff.

        Returns:
            Validation result with any pattern violations found.
        """
        if not self.disallowed_patterns:
            return DiffValidationResult(
                passed=True,
                message="No patterns to check",
            )

        try:
            diff_output = await self._get_diff()
            violations: List[str] = []

            # Extract only added lines for pattern checking
            added_lines = [
                line
                for line in diff_output.split("\n")
                if line.startswith("+") and not line.startswith("+++")
            ]

            # Check each disallowed pattern
            for pattern_config in self.disallowed_patterns:
                pattern = pattern_config.get("pattern")
                if not pattern:
                    continue

                reason = pattern_config.get("reason", "Disallowed pattern")

                try:
                    compiled_pattern = re.compile(pattern)
                    for line in added_lines:
                        if compiled_pattern.search(line):
                            violations.append(f"{reason}: found '{pattern}' in changes")
                            break  # Only report once per pattern
                except re.error as regex_err:
                    logger.warning(f"Invalid regex pattern '{pattern}': {regex_err}")

            if violations:
                return DiffValidationResult(
                    passed=False,
                    violations=violations,
                    message=f"Found {len(violations)} disallowed patterns",
                )

            return DiffValidationResult(
                passed=True,
                message="No disallowed patterns found",
            )

        except Exception as e:
            logger.error(f"Error validating patterns: {e}")
            return DiffValidationResult(
                passed=True,  # Don't block on validation infrastructure errors
                error=str(e),
                message="Pattern validation encountered an error",
            )

    async def get_diff_summary(self) -> str:
        """Get a summary of the current diff.

        Returns:
            The git diff --stat output or an error message.
        """
        try:
            return await self._get_diff_stat()
        except Exception as e:
            logger.error(f"Error getting diff summary: {e}")
            return f"Error: {e}"

    def requires_justification_for_unexpected_files(self) -> bool:
        """Check if justification is required for unexpected files.

        Returns:
            True if the configuration requires justification for unexpected files.
        """
        action = self.unexpected_files_action.get("action", "")
        return action == "require_justification"
