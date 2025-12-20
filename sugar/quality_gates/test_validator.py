"""
Test Execution Validator - Feature 1: Mandatory Test Execution

Ensures that tasks cannot complete without running and passing tests.
Blocks commits if tests haven't been executed or if they fail.
"""

import asyncio
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TestExecutionResult:
    """Result of a test execution"""

    def __init__(
        self,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        duration: float,
        failures: int = 0,
        errors: int = 0,
        pending: int = 0,
        examples: int = 0,
    ):
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration = duration
        self.failures = failures
        self.errors = errors
        self.pending = pending
        self.examples = examples
        self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def passed(self) -> bool:
        """Test passed if exit code is 0 and no failures/errors"""
        return self.exit_code == 0 and self.failures == 0 and self.errors == 0

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "duration": self.duration,
            "failures": self.failures,
            "errors": self.errors,
            "pending": self.pending,
            "examples": self.examples,
            "passed": self.passed,
            "timestamp": self.timestamp,
        }


class TestExecutionValidator:
    """
    Validates that tests are executed and pass before allowing task completion
    """

    def __init__(self, config: dict):
        """
        Initialize test validator with configuration

        Args:
            config: Quality gates configuration dictionary
        """
        self.config = config.get("quality_gates", {}).get("mandatory_testing", {})
        self.enabled = self.config.get("enabled", False)
        self.block_commits = self.config.get("block_commits", True)
        self.test_commands = self.config.get("test_commands", {})
        self.validation = self.config.get("validation", {})
        self.evidence_config = self.config.get("evidence", {})

    def is_enabled(self) -> bool:
        """Check if mandatory testing is enabled"""
        return self.enabled

    async def validate_tests_before_commit(
        self, task: dict, changed_files: List[str]
    ) -> Tuple[bool, Optional[TestExecutionResult], str]:
        """
        Validate that tests have been run before allowing a commit

        Args:
            task: Task dictionary with metadata
            changed_files: List of files that were changed

        Returns:
            Tuple of (can_commit, test_result, message)
        """
        if not self.is_enabled():
            return True, None, "Test validation disabled"

        # Determine which tests to run
        test_commands = self._determine_required_tests(changed_files)

        if not test_commands:
            # Use default test command
            test_commands = [self.test_commands.get("default", "pytest")]

        # Execute tests
        results = []
        for command in test_commands:
            result = await self._execute_test_command(command, task)
            results.append(result)

            # If any test fails and we're blocking commits, stop
            if not result.passed and self.block_commits:
                message = f"❌ Tests failed: {result.failures} failures, {result.errors} errors"
                return False, result, message

        # All tests passed
        if results:
            passed_result = results[0]  # Return first result for evidence
            message = (
                f"✅ All tests passed: {passed_result.examples} examples, 0 failures"
            )
            return True, passed_result, message

        return True, None, "No tests executed"

    def _determine_required_tests(self, changed_files: List[str]) -> List[str]:
        """
        Determine which test commands are required based on changed files

        Args:
            changed_files: List of file paths that were modified

        Returns:
            List of test commands to execute
        """
        auto_detect = self.config.get("auto_detect_required_tests", {})
        if not auto_detect.get("enabled", False):
            return []

        required_tests = set()
        patterns = auto_detect.get("patterns", [])

        for file_path in changed_files:
            for pattern_config in patterns:
                pattern = pattern_config.get("pattern", "")
                # Simple glob-style matching
                if self._matches_pattern(file_path, pattern):
                    test_types = pattern_config.get("required_tests", [])
                    for test_type in test_types:
                        if test_type in self.test_commands:
                            required_tests.add(self.test_commands[test_type])

        return list(required_tests)

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Simple glob pattern matching"""
        import fnmatch

        return fnmatch.fnmatch(file_path, pattern)

    async def _execute_test_command(
        self, command: str, task: dict
    ) -> TestExecutionResult:
        """
        Execute a test command and capture results

        Args:
            command: Test command to execute
            task: Task metadata

        Returns:
            TestExecutionResult with execution details
        """
        logger.info(f"Executing test command: {command}")
        start_time = datetime.now(timezone.utc)

        try:
            # Run the test command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path.cwd(),
            )

            stdout, stderr = await process.communicate()
            stdout_str = stdout.decode("utf-8")
            stderr_str = stderr.decode("utf-8")
            exit_code = process.returncode

            # Calculate duration
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            # Parse test output to extract stats
            failures, errors, pending, examples = self._parse_test_output(stdout_str)

            result = TestExecutionResult(
                command=command,
                exit_code=exit_code,
                stdout=stdout_str,
                stderr=stderr_str,
                duration=duration,
                failures=failures,
                errors=errors,
                pending=pending,
                examples=examples,
            )

            # Store evidence if configured
            if self.evidence_config.get("store_test_output", False):
                await self._store_test_evidence(task, result)

            return result

        except Exception as e:
            logger.error(f"Error executing test command: {e}")
            return TestExecutionResult(
                command=command,
                exit_code=1,
                stdout="",
                stderr=str(e),
                duration=0.0,
                failures=1,
                errors=1,
            )

    def _parse_test_output(self, output: str) -> Tuple[int, int, int, int]:
        """
        Parse test output to extract statistics

        Supports multiple test frameworks:
        - pytest: "5 passed, 2 failed"
        - rspec: "150 examples, 0 failures"
        - jest: "Tests: 10 passed, 10 total"

        Args:
            output: Test command stdout

        Returns:
            Tuple of (failures, errors, pending, examples)
        """
        failures = 0
        errors = 0
        pending = 0
        examples = 0

        # Pytest patterns
        pytest_match = re.search(r"(\d+) failed", output)
        if pytest_match:
            failures = int(pytest_match.group(1))

        pytest_passed = re.search(r"(\d+) passed", output)
        if pytest_passed:
            examples = int(pytest_passed.group(1))

        # RSpec patterns
        rspec_examples = re.search(r"(\d+) examples?", output)
        if rspec_examples:
            examples = int(rspec_examples.group(1))

        rspec_failures = re.search(r"(\d+) failures?", output)
        if rspec_failures:
            failures = int(rspec_failures.group(1))

        rspec_pending = re.search(r"(\d+) pending", output)
        if rspec_pending:
            pending = int(rspec_pending.group(1))

        # Jest patterns
        jest_failed = re.search(r"Tests:.*?(\d+) failed", output)
        if jest_failed:
            failures = int(jest_failed.group(1))

        jest_passed = re.search(r"Tests:.*?(\d+) passed", output)
        if jest_passed:
            examples = int(jest_passed.group(1))

        return failures, errors, pending, examples

    async def _store_test_evidence(
        self, task: dict, result: TestExecutionResult
    ) -> None:
        """
        Store test execution evidence to disk

        Args:
            task: Task metadata
            result: Test execution result
        """
        evidence_path_template = self.evidence_config.get(
            "path", ".sugar/test_evidence/{task_id}.txt"
        )
        task_id = task.get("id", "unknown")
        evidence_path = Path(evidence_path_template.format(task_id=task_id))

        # Create evidence directory
        evidence_path.parent.mkdir(parents=True, exist_ok=True)

        # Write evidence
        with open(evidence_path, "w") as f:
            f.write(f"Test Execution Evidence\n")
            f.write(f"{'=' * 60}\n\n")
            f.write(f"Task ID: {task_id}\n")
            f.write(f"Command: {result.command}\n")
            f.write(f"Timestamp: {result.timestamp}\n")
            f.write(f"Duration: {result.duration:.2f}s\n")
            f.write(f"Exit Code: {result.exit_code}\n")
            f.write(f"\nResults:\n")
            f.write(f"  Examples: {result.examples}\n")
            f.write(f"  Failures: {result.failures}\n")
            f.write(f"  Errors: {result.errors}\n")
            f.write(f"  Pending: {result.pending}\n")
            f.write(f"  Passed: {result.passed}\n")
            f.write(f"\n{'=' * 60}\n")
            f.write(f"STDOUT:\n{'=' * 60}\n")
            f.write(result.stdout)
            f.write(f"\n{'=' * 60}\n")
            f.write(f"STDERR:\n{'=' * 60}\n")
            f.write(result.stderr)

        logger.info(f"Stored test evidence: {evidence_path}")

    def get_commit_message_evidence(self, result: TestExecutionResult) -> str:
        """
        Generate commit message footer with test evidence

        Args:
            result: Test execution result

        Returns:
            String to append to commit message
        """
        if not self.evidence_config.get("include_in_commit_message", False):
            return ""

        return f"""
Test Evidence:
- Command: {result.command}
- Examples: {result.examples}, Failures: {result.failures}, Errors: {result.errors}
- Duration: {result.duration:.2f}s
- Status: {'✅ PASSED' if result.passed else '❌ FAILED'}
"""
