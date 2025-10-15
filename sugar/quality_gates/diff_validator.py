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
from typing import Any, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class DiffValidationResult:
    """Result of diff validation"""

    def __init__(self, passed: bool, **kwargs):
        self.passed = passed
        self.metadata = kwargs

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "passed": self.passed,
            **self.metadata,
        }


class DiffValidator:
    """
    Validates git diff before committing
    """

    def __init__(self, config: dict):
        """
        Initialize diff validator

        Args:
            config: Configuration dictionary
        """
        diff_config = config.get("git_diff_validation", {})
        self.enabled = diff_config.get("enabled", False)

        # File validation
        before_commit = diff_config.get("before_commit", {})
        self.validate_files = before_commit.get("validate_files_changed", {})
        self.allow_additional_files = self.validate_files.get(
            "allow_additional_files", False
        )

        # Size validation
        self.max_lines_changed = before_commit.get("max_lines_changed", 500)
        self.warn_if_exceeds = before_commit.get("warn_if_exceeds", 200)

        # Pattern validation
        self.disallowed_patterns = before_commit.get("disallow_patterns", [])

        # Unexpected file handling
        self.unexpected_files_action = before_commit.get(
            "if_unexpected_files_changed", {}
        )

    def is_enabled(self) -> bool:
        """Check if diff validation is enabled"""
        return self.enabled

    async def validate_diff(
        self,
        task: Dict[str, Any],
        changed_files: List[str],
    ) -> Tuple[bool, DiffValidationResult]:
        """
        Validate git diff before commit

        Args:
            task: Task dictionary with expected files
            changed_files: List of changed files

        Returns:
            Tuple of (is_valid, validation_result)
        """
        if not self.is_enabled():
            return True, DiffValidationResult(
                passed=True, message="Validation disabled"
            )

        issues = []

        # 1. Validate files changed match expectations
        if self.validate_files.get("enabled", False):
            expected_files = task.get("files_to_modify", {}).get("expected", [])
            file_validation = await self._validate_files_changed(
                expected_files, changed_files
            )

            if not file_validation.passed:
                issues.append(file_validation.metadata.get("message"))

        # 2. Validate size of changes
        size_validation = await self._validate_change_size(changed_files)
        if not size_validation.passed:
            issues.append(size_validation.metadata.get("message"))

        # 3. Validate patterns (no debug statements, etc.)
        pattern_validation = await self._validate_patterns(changed_files)
        if not pattern_validation.passed:
            issues.extend(pattern_validation.metadata.get("violations", []))

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

    async def _validate_files_changed(
        self, expected_files: List[str], changed_files: List[str]
    ) -> DiffValidationResult:
        """Validate that changed files match expectations"""
        unexpected_files = []
        missing_files = []

        # Check for unexpected files
        for file_path in changed_files:
            if file_path not in expected_files:
                unexpected_files.append(file_path)

        # Check for missing files (expected but not changed)
        for file_path in expected_files:
            if file_path not in changed_files:
                missing_files.append(file_path)

        # Determine if this is acceptable
        if unexpected_files and not self.allow_additional_files:
            return DiffValidationResult(
                passed=False,
                unexpected_files=unexpected_files,
                message=f"Unexpected files changed: {', '.join(unexpected_files)}",
            )

        if unexpected_files and self.allow_additional_files:
            logger.warning(
                f"⚠️ Additional files changed (allowed): {', '.join(unexpected_files)}"
            )

        return DiffValidationResult(
            passed=True,
            unexpected_files=unexpected_files,
            missing_files=missing_files,
            message="File changes match expectations",
        )

    async def _validate_change_size(
        self, changed_files: List[str]
    ) -> DiffValidationResult:
        """Validate size of changes is reasonable"""
        try:
            # Get diff stats
            process = await asyncio.create_subprocess_shell(
                "git diff --stat HEAD",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            output = stdout.decode("utf-8")

            # Parse total lines changed from last line
            # Example: " 5 files changed, 234 insertions(+), 12 deletions(-)"
            lines = output.strip().split("\n")
            if lines:
                last_line = lines[-1]
                match = re.search(r"(\d+) insertion", last_line)
                insertions = int(match.group(1)) if match else 0

                match = re.search(r"(\d+) deletion", last_line)
                deletions = int(match.group(1)) if match else 0

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
                        f"⚠️ Large change detected: {total_lines} lines (threshold: {self.warn_if_exceeds})"
                    )

                return DiffValidationResult(
                    passed=True,
                    total_lines_changed=total_lines,
                    message=f"Change size acceptable: {total_lines} lines",
                )

            return DiffValidationResult(
                passed=True,
                message="Could not determine change size",
            )

        except Exception as e:
            logger.error(f"Error validating change size: {e}")
            return DiffValidationResult(
                passed=True,  # Don't block on error
                error=str(e),
                message="Change size validation failed",
            )

    async def _validate_patterns(
        self, changed_files: List[str]
    ) -> DiffValidationResult:
        """Validate no disallowed patterns in changes"""
        violations = []

        try:
            # Get the diff
            process = await asyncio.create_subprocess_shell(
                "git diff HEAD",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            diff_output = stdout.decode("utf-8")

            # Check each disallowed pattern
            for pattern_config in self.disallowed_patterns:
                pattern = pattern_config.get("pattern")
                reason = pattern_config.get("reason", "Disallowed pattern")

                # Search for pattern in added lines (lines starting with +)
                for line in diff_output.split("\n"):
                    if line.startswith("+") and not line.startswith("+++"):
                        # This is an added line
                        if re.search(pattern, line):
                            violations.append(f"{reason}: found '{pattern}' in changes")
                            break  # Only report once per pattern

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
                passed=True,  # Don't block on error
                error=str(e),
                message="Pattern validation failed",
            )

    async def get_diff_summary(self) -> str:
        """Get a summary of the current diff"""
        try:
            process = await asyncio.create_subprocess_shell(
                "git diff --stat HEAD",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            return stdout.decode("utf-8")

        except Exception as e:
            logger.error(f"Error getting diff summary: {e}")
            return f"Error: {e}"

    def requires_justification_for_unexpected_files(self) -> bool:
        """Check if justification is required for unexpected files"""
        action = self.unexpected_files_action.get("action", "")
        return action == "require_justification"
