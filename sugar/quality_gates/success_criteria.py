"""
Success Criteria Verifier - Feature 3: Success Criteria Verification

Makes success criteria testable and verifiable.
Tasks cannot complete until all success criteria are verified.
"""

import asyncio
import subprocess
from typing import Any, Dict, List, Optional, Tuple
import logging
import re

logger = logging.getLogger(__name__)


class SuccessCriterion:
    """A single success criterion that must be verified"""

    def __init__(
        self,
        criterion_type: str,
        expected: Any,
        actual: Optional[Any] = None,
        verified: bool = False,
        **kwargs,
    ):
        self.type = criterion_type
        self.expected = expected
        self.actual = actual
        self.verified = verified
        self.metadata = kwargs

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "type": self.type,
            "expected": self.expected,
            "actual": self.actual,
            "verified": self.verified,
            **self.metadata,
        }


class SuccessCriteriaVerifier:
    """
    Verifies that all task success criteria are met before completion
    """

    def __init__(self, config: dict):
        """
        Initialize success criteria verifier

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.block_completion = True  # Always block until verified

    async def verify_all_criteria(
        self, criteria: List[Dict[str, Any]]
    ) -> Tuple[bool, List[SuccessCriterion]]:
        """
        Verify all success criteria for a task

        Args:
            criteria: List of success criterion definitions

        Returns:
            Tuple of (all_verified, list of verified criteria)
        """
        if not criteria:
            logger.warning("No success criteria defined for task")
            return False, []

        verified_criteria = []

        for criterion_def in criteria:
            criterion = await self._verify_criterion(criterion_def)
            verified_criteria.append(criterion)

        all_verified = all(c.verified for c in verified_criteria)

        if all_verified:
            logger.info(f"✅ All {len(verified_criteria)} success criteria verified")
        else:
            failed = [c for c in verified_criteria if not c.verified]
            logger.warning(f"❌ {len(failed)} success criteria failed verification")

        return all_verified, verified_criteria

    async def _verify_criterion(
        self, criterion_def: Dict[str, Any]
    ) -> SuccessCriterion:
        """
        Verify a single success criterion

        Args:
            criterion_def: Criterion definition dictionary

        Returns:
            SuccessCriterion with verification result
        """
        criterion_type = criterion_def.get("type")

        if criterion_type == "http_status":
            return await self._verify_http_status(criterion_def)

        elif criterion_type == "http_no_redirect":
            return await self._verify_http_no_redirect(criterion_def)

        elif criterion_type == "test_suite":
            return await self._verify_test_suite(criterion_def)

        elif criterion_type == "browser_element_exists":
            return await self._verify_browser_element(criterion_def)

        elif criterion_type == "file_exists":
            return await self._verify_file_exists(criterion_def)

        elif criterion_type == "string_in_file":
            return await self._verify_string_in_file(criterion_def)

        else:
            logger.error(f"Unknown criterion type: {criterion_type}")
            return SuccessCriterion(
                criterion_type=criterion_type,
                expected=criterion_def.get("expected"),
                actual=None,
                verified=False,
                error=f"Unsupported criterion type: {criterion_type}",
            )

    async def _verify_http_status(
        self, criterion_def: Dict[str, Any]
    ) -> SuccessCriterion:
        """Verify HTTP status code"""
        url = criterion_def.get("url")
        expected = criterion_def.get("expected")

        try:
            # Use curl to check HTTP status
            process = await asyncio.create_subprocess_exec(
                "curl",
                "-s",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            actual = int(stdout.decode("utf-8").strip())

            verified = actual == expected

            return SuccessCriterion(
                criterion_type="http_status",
                expected=expected,
                actual=actual,
                verified=verified,
                url=url,
            )

        except Exception as e:
            logger.error(f"Error verifying HTTP status for {url}: {e}")
            return SuccessCriterion(
                criterion_type="http_status",
                expected=expected,
                actual=None,
                verified=False,
                url=url,
                error=str(e),
            )

    async def _verify_http_no_redirect(
        self, criterion_def: Dict[str, Any]
    ) -> SuccessCriterion:
        """Verify that URL does not redirect"""
        url = criterion_def.get("url")
        disallowed_status = criterion_def.get(
            "disallowed_status", [301, 302, 303, 307, 308]
        )

        try:
            # Use curl to check if there's a redirect
            process = await asyncio.create_subprocess_exec(
                "curl",
                "-s",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                "-L",  # Don't follow redirects, just report status
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            status_code = int(stdout.decode("utf-8").strip())

            verified = status_code not in disallowed_status

            return SuccessCriterion(
                criterion_type="http_no_redirect",
                expected=f"not in {disallowed_status}",
                actual=status_code,
                verified=verified,
                url=url,
            )

        except Exception as e:
            logger.error(f"Error verifying no redirect for {url}: {e}")
            return SuccessCriterion(
                criterion_type="http_no_redirect",
                expected=f"not in {disallowed_status}",
                actual=None,
                verified=False,
                url=url,
                error=str(e),
            )

    async def _verify_test_suite(
        self, criterion_def: Dict[str, Any]
    ) -> SuccessCriterion:
        """Verify test suite passes"""
        command = criterion_def.get("command")
        expected_failures = criterion_def.get("expected_failures", 0)
        expected_errors = criterion_def.get("expected_errors", 0)

        try:
            # Run the test command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            stdout_str = stdout.decode("utf-8")
            exit_code = process.returncode

            # Parse test output
            failures, errors = self._parse_test_failures(stdout_str)

            verified = (
                exit_code == 0
                and failures == expected_failures
                and errors == expected_errors
            )

            return SuccessCriterion(
                criterion_type="test_suite",
                expected={"failures": expected_failures, "errors": expected_errors},
                actual={"failures": failures, "errors": errors, "exit_code": exit_code},
                verified=verified,
                command=command,
            )

        except Exception as e:
            logger.error(f"Error running test suite {command}: {e}")
            return SuccessCriterion(
                criterion_type="test_suite",
                expected={"failures": expected_failures, "errors": expected_errors},
                actual=None,
                verified=False,
                command=command,
                error=str(e),
            )

    def _parse_test_failures(self, output: str) -> Tuple[int, int]:
        """Parse test output for failures and errors"""
        failures = 0
        errors = 0

        # Pytest patterns
        pytest_failed = re.search(r"(\d+) failed", output)
        if pytest_failed:
            failures = int(pytest_failed.group(1))

        # RSpec patterns
        rspec_failures = re.search(r"(\d+) failures?", output)
        if rspec_failures:
            failures = int(rspec_failures.group(1))

        # Jest patterns
        jest_failed = re.search(r"Tests:.*?(\d+) failed", output)
        if jest_failed:
            failures = int(jest_failed.group(1))

        return failures, errors

    async def _verify_browser_element(
        self, criterion_def: Dict[str, Any]
    ) -> SuccessCriterion:
        """
        Verify browser element exists (placeholder for MCP integration)

        In the future, this will use Chrome DevTools MCP to verify elements.
        For now, this is a placeholder that always returns unverified.
        """
        url = criterion_def.get("url")
        selector = criterion_def.get("selector")

        # TODO: Integrate with Chrome DevTools MCP when available
        # For now, return unverified with a note
        return SuccessCriterion(
            criterion_type="browser_element_exists",
            expected=f"element exists: {selector}",
            actual=None,
            verified=False,
            url=url,
            selector=selector,
            note="Browser automation not yet implemented - requires MCP integration",
        )

    async def _verify_file_exists(
        self, criterion_def: Dict[str, Any]
    ) -> SuccessCriterion:
        """Verify file exists"""
        from pathlib import Path

        file_path = criterion_def.get("file_path")
        expected = True

        try:
            actual = Path(file_path).exists()
            verified = actual == expected

            return SuccessCriterion(
                criterion_type="file_exists",
                expected=expected,
                actual=actual,
                verified=verified,
                file_path=file_path,
            )

        except Exception as e:
            logger.error(f"Error checking file exists {file_path}: {e}")
            return SuccessCriterion(
                criterion_type="file_exists",
                expected=expected,
                actual=None,
                verified=False,
                file_path=file_path,
                error=str(e),
            )

    async def _verify_string_in_file(
        self, criterion_def: Dict[str, Any]
    ) -> SuccessCriterion:
        """Verify string exists in file"""
        from pathlib import Path

        file_path = criterion_def.get("file_path")
        search_string = criterion_def.get("search_string")

        try:
            content = Path(file_path).read_text()
            actual = search_string in content
            expected = True

            verified = actual == expected

            return SuccessCriterion(
                criterion_type="string_in_file",
                expected=expected,
                actual=actual,
                verified=verified,
                file_path=file_path,
                search_string=search_string,
            )

        except Exception as e:
            logger.error(f"Error checking string in file {file_path}: {e}")
            return SuccessCriterion(
                criterion_type="string_in_file",
                expected=True,
                actual=None,
                verified=False,
                file_path=file_path,
                search_string=search_string,
                error=str(e),
            )
