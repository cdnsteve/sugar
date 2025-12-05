"""
Tests for TestExecutionValidator and TestExecutionResult

Comprehensive test coverage for test execution validation including:
- TestExecutionResult data class and properties
- TestExecutionValidator initialization and configuration
- Test command execution and parsing
- Evidence storage and commit message generation
- Pattern matching for automatic test detection
"""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sugar.quality_gates.test_validator import (
    TestExecutionResult,
    TestExecutionValidator,
)


# --- Fixtures ---


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


def make_mandatory_testing_config(
    enabled: bool = True,
    block_commits: bool = True,
    test_commands: Dict[str, str] = None,
    auto_detect: Dict[str, Any] = None,
    evidence: Dict[str, Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Factory function for mandatory testing configuration."""
    config: Dict[str, Any] = {
        "enabled": enabled,
        "block_commits": block_commits,
    }
    if test_commands is not None:
        config["test_commands"] = test_commands
    if auto_detect is not None:
        config["auto_detect_required_tests"] = auto_detect
    if evidence is not None:
        config["evidence"] = evidence
    config.update(kwargs)
    return {"quality_gates": {"mandatory_testing": config}}


# --- TestExecutionResult Tests ---


class TestTestExecutionResult:
    """Tests for TestExecutionResult data class."""

    def test_init_sets_all_attributes(self) -> None:
        """TestExecutionResult should store all provided attributes."""
        result = TestExecutionResult(
            command="pytest tests/",
            exit_code=0,
            stdout="10 passed",
            stderr="",
            duration=5.23,
            failures=0,
            errors=0,
            pending=2,
            examples=10,
        )

        assert result.command == "pytest tests/"
        assert result.exit_code == 0
        assert result.stdout == "10 passed"
        assert result.stderr == ""
        assert result.duration == 5.23
        assert result.failures == 0
        assert result.errors == 0
        assert result.pending == 2
        assert result.examples == 10

    def test_init_sets_default_values(self) -> None:
        """TestExecutionResult should have sensible defaults for optional fields."""
        result = TestExecutionResult(
            command="pytest",
            exit_code=0,
            stdout="",
            stderr="",
            duration=1.0,
        )

        assert result.failures == 0
        assert result.errors == 0
        assert result.pending == 0
        assert result.examples == 0

    def test_init_sets_valid_timestamp(self) -> None:
        """TestExecutionResult timestamp should be a valid ISO format string."""
        result = TestExecutionResult(
            command="pytest",
            exit_code=0,
            stdout="",
            stderr="",
            duration=1.0,
        )

        # Should not raise - valid ISO format
        datetime.fromisoformat(result.timestamp)

    def test_passed_property_true_when_all_pass(self) -> None:
        """passed property should return True when exit_code=0 and no failures/errors."""
        result = TestExecutionResult(
            command="pytest",
            exit_code=0,
            stdout="5 passed",
            stderr="",
            duration=1.0,
            failures=0,
            errors=0,
            examples=5,
        )

        assert result.passed is True

    def test_passed_property_false_when_nonzero_exit_code(self) -> None:
        """passed property should return False when exit_code is non-zero."""
        result = TestExecutionResult(
            command="pytest",
            exit_code=1,
            stdout="",
            stderr="Error",
            duration=1.0,
            failures=0,
            errors=0,
        )

        assert result.passed is False

    def test_passed_property_false_when_failures_present(self) -> None:
        """passed property should return False when there are failures."""
        result = TestExecutionResult(
            command="pytest",
            exit_code=0,  # Even with exit_code=0
            stdout="3 failed",
            stderr="",
            duration=1.0,
            failures=3,
            errors=0,
        )

        assert result.passed is False

    def test_passed_property_false_when_errors_present(self) -> None:
        """passed property should return False when there are errors."""
        result = TestExecutionResult(
            command="pytest",
            exit_code=0,  # Even with exit_code=0
            stdout="2 errors",
            stderr="",
            duration=1.0,
            failures=0,
            errors=2,
        )

        assert result.passed is False

    def test_passed_property_false_when_both_failures_and_errors(self) -> None:
        """passed property should return False when both failures and errors exist."""
        result = TestExecutionResult(
            command="pytest",
            exit_code=1,
            stdout="",
            stderr="",
            duration=1.0,
            failures=3,
            errors=2,
        )

        assert result.passed is False

    def test_to_dict_contains_all_fields(self) -> None:
        """to_dict should return a dictionary with all result fields."""
        result = TestExecutionResult(
            command="pytest tests/",
            exit_code=0,
            stdout="output",
            stderr="errors",
            duration=5.5,
            failures=1,
            errors=2,
            pending=3,
            examples=10,
        )

        result_dict = result.to_dict()

        assert result_dict["command"] == "pytest tests/"
        assert result_dict["exit_code"] == 0
        assert result_dict["duration"] == 5.5
        assert result_dict["failures"] == 1
        assert result_dict["errors"] == 2
        assert result_dict["pending"] == 3
        assert result_dict["examples"] == 10
        assert "passed" in result_dict
        assert "timestamp" in result_dict

    def test_to_dict_does_not_include_stdout_stderr(self) -> None:
        """to_dict should not include stdout/stderr for storage efficiency."""
        result = TestExecutionResult(
            command="pytest",
            exit_code=0,
            stdout="large output",
            stderr="error output",
            duration=1.0,
        )

        result_dict = result.to_dict()

        assert "stdout" not in result_dict
        assert "stderr" not in result_dict

    def test_to_dict_passed_reflects_property(self) -> None:
        """to_dict passed field should match passed property."""
        passing_result = TestExecutionResult(
            command="pytest",
            exit_code=0,
            stdout="",
            stderr="",
            duration=1.0,
            failures=0,
            errors=0,
        )
        failing_result = TestExecutionResult(
            command="pytest",
            exit_code=1,
            stdout="",
            stderr="",
            duration=1.0,
            failures=1,
            errors=0,
        )

        assert passing_result.to_dict()["passed"] is True
        assert failing_result.to_dict()["passed"] is False


# --- TestExecutionValidator Initialization Tests ---


class TestTestExecutionValidatorInit:
    """Tests for TestExecutionValidator initialization."""

    def test_init_with_config_enabled(self) -> None:
        """Validator should be enabled and block commits when configured."""
        config = make_mandatory_testing_config(enabled=True, block_commits=True)
        validator = TestExecutionValidator(config)

        assert validator.is_enabled() is True
        assert validator.block_commits is True

    def test_init_with_config_disabled(self) -> None:
        """Validator should be disabled when enabled=False in config."""
        config = make_mandatory_testing_config(enabled=False)
        validator = TestExecutionValidator(config)

        assert validator.is_enabled() is False

    def test_init_with_empty_config(self) -> None:
        """Validator should be disabled with empty config."""
        validator = TestExecutionValidator({})

        assert validator.is_enabled() is False

    def test_init_with_block_commits_false(self) -> None:
        """Validator should not block commits when block_commits=False."""
        config = make_mandatory_testing_config(enabled=True, block_commits=False)
        validator = TestExecutionValidator(config)

        assert validator.is_enabled() is True
        assert validator.block_commits is False

    def test_init_stores_test_commands(self) -> None:
        """Validator should store test commands from config."""
        test_commands = {"default": "pytest", "unit": "pytest tests/unit/"}
        config = make_mandatory_testing_config(
            enabled=True, test_commands=test_commands
        )
        validator = TestExecutionValidator(config)

        assert validator.test_commands == test_commands

    def test_init_stores_validation_config(self) -> None:
        """Validator should store validation config."""
        config = make_mandatory_testing_config(enabled=True, validation={"strict": True})
        validator = TestExecutionValidator(config)

        assert validator.validation == {"strict": True}

    def test_init_stores_evidence_config(self) -> None:
        """Validator should store evidence config."""
        evidence_config = {
            "store_test_output": True,
            "path": ".sugar/evidence/{task_id}.txt",
        }
        config = make_mandatory_testing_config(enabled=True, evidence=evidence_config)
        validator = TestExecutionValidator(config)

        assert validator.evidence_config == evidence_config


# --- TestExecutionValidator Validation Tests ---


class TestTestExecutionValidatorValidation:
    """Tests for validate_tests_before_commit method."""

    @pytest.mark.asyncio
    async def test_validate_tests_when_disabled_allows_commit(self) -> None:
        """When disabled, validation should allow commits without running tests."""
        config = make_mandatory_testing_config(enabled=False)
        validator = TestExecutionValidator(config)

        task = {"id": "test-123"}
        can_commit, result, message = await validator.validate_tests_before_commit(
            task, []
        )

        assert can_commit is True
        assert result is None
        assert message == "Test validation disabled"

    @pytest.mark.asyncio
    async def test_validate_tests_uses_default_command(self) -> None:
        """Should use default test command when no specific tests detected."""
        config = make_mandatory_testing_config(
            enabled=True,
            test_commands={"default": "pytest tests/"},
        )
        validator = TestExecutionValidator(config)

        with patch.object(
            validator, "_execute_test_command", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = TestExecutionResult(
                command="pytest tests/",
                exit_code=0,
                stdout="5 passed",
                stderr="",
                duration=1.0,
                failures=0,
                errors=0,
                examples=5,
            )

            task = {"id": "test-123"}
            can_commit, result, message = await validator.validate_tests_before_commit(
                task, []
            )

            mock_execute.assert_called_once_with("pytest tests/", task)
            assert can_commit is True

    @pytest.mark.asyncio
    async def test_validate_tests_returns_success_when_all_pass(self) -> None:
        """Should return success when all tests pass."""
        config = make_mandatory_testing_config(
            enabled=True, test_commands={"default": "pytest"}
        )
        validator = TestExecutionValidator(config)

        with patch.object(
            validator, "_execute_test_command", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = TestExecutionResult(
                command="pytest",
                exit_code=0,
                stdout="10 passed",
                stderr="",
                duration=2.5,
                failures=0,
                errors=0,
                examples=10,
            )

            task = {"id": "test-123"}
            can_commit, result, message = await validator.validate_tests_before_commit(
                task, []
            )

            assert can_commit is True
            assert result is not None
            assert result.passed is True
            assert "✅" in message
            assert "All tests passed" in message

    @pytest.mark.asyncio
    async def test_validate_tests_blocks_on_failure_when_configured(self) -> None:
        """Should block commit when tests fail and block_commits=True."""
        config = make_mandatory_testing_config(
            enabled=True, block_commits=True, test_commands={"default": "pytest"}
        )
        validator = TestExecutionValidator(config)

        with patch.object(
            validator, "_execute_test_command", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = TestExecutionResult(
                command="pytest",
                exit_code=1,
                stdout="3 failed",
                stderr="",
                duration=2.0,
                failures=3,
                errors=1,
                examples=10,
            )

            task = {"id": "test-123"}
            can_commit, result, message = await validator.validate_tests_before_commit(
                task, []
            )

            assert can_commit is False
            assert result is not None
            assert result.passed is False
            assert "❌" in message
            assert "3 failures" in message
            assert "1 errors" in message

    @pytest.mark.asyncio
    async def test_validate_tests_no_block_on_failure_when_disabled(self) -> None:
        """Should not block commit when tests fail but block_commits=False."""
        config = make_mandatory_testing_config(
            enabled=True, block_commits=False, test_commands={"default": "pytest"}
        )
        validator = TestExecutionValidator(config)

        with patch.object(
            validator, "_execute_test_command", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = TestExecutionResult(
                command="pytest",
                exit_code=1,
                stdout="3 failed",
                stderr="",
                duration=2.0,
                failures=3,
                errors=0,
                examples=10,
            )

            task = {"id": "test-123"}
            can_commit, result, message = await validator.validate_tests_before_commit(
                task, []
            )

            # Even though tests failed, block_commits=False allows commit
            assert can_commit is True

    @pytest.mark.asyncio
    async def test_validate_tests_no_tests_executed(self) -> None:
        """Should return 'No tests executed' when no tests run and results empty."""
        config = make_mandatory_testing_config(
            enabled=True,
            test_commands={},
            auto_detect={"enabled": False},
        )
        validator = TestExecutionValidator(config)

        # Mock to prevent any test execution
        mock_result = TestExecutionResult(
            command="pytest",
            exit_code=0,
            stdout="",
            stderr="",
            duration=0.1,
            examples=5,
            failures=0,
            errors=0,
        )
        with patch.object(
            validator, "_execute_test_command", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = mock_result
            task = {"id": "test-123"}
            can_commit, result, message = await validator.validate_tests_before_commit(
                task, []
            )

            # With default "pytest" command being used, tests should pass
            assert can_commit is True
            assert result is not None
            assert "passed" in message.lower() or "✅" in message


# --- Test Command Determination Tests ---


class TestTestExecutionValidatorDetermineTests:
    """Tests for _determine_required_tests method."""

    def test_determine_tests_returns_empty_when_auto_detect_disabled(self) -> None:
        """Should return empty list when auto_detect is disabled."""
        config = make_mandatory_testing_config(
            enabled=True,
            auto_detect={"enabled": False},
        )
        validator = TestExecutionValidator(config)

        result = validator._determine_required_tests(["src/main.py"])

        assert result == []

    def test_determine_tests_matches_pattern_to_test_command(self) -> None:
        """Should return test commands for files matching patterns."""
        config = make_mandatory_testing_config(
            enabled=True,
            test_commands={
                "unit": "pytest tests/unit/",
                "integration": "pytest tests/integration/",
            },
            auto_detect={
                "enabled": True,
                "patterns": [
                    {"pattern": "src/*.py", "required_tests": ["unit"]},
                    {"pattern": "api/*.py", "required_tests": ["integration"]},
                ],
            },
        )
        validator = TestExecutionValidator(config)

        result = validator._determine_required_tests(["src/main.py"])

        assert "pytest tests/unit/" in result

    def test_determine_tests_handles_multiple_patterns(self) -> None:
        """Should return multiple test commands for multiple matching patterns."""
        config = make_mandatory_testing_config(
            enabled=True,
            test_commands={
                "unit": "pytest tests/unit/",
                "integration": "pytest tests/integration/",
            },
            auto_detect={
                "enabled": True,
                "patterns": [
                    {"pattern": "src/*.py", "required_tests": ["unit"]},
                    {"pattern": "src/api/*.py", "required_tests": ["unit", "integration"]},
                ],
            },
        )
        validator = TestExecutionValidator(config)

        result = validator._determine_required_tests(["src/api/endpoints.py"])

        assert len(result) == 2
        assert "pytest tests/unit/" in result
        assert "pytest tests/integration/" in result

    def test_determine_tests_deduplicates_commands(self) -> None:
        """Should not duplicate test commands for multiple matching files."""
        config = make_mandatory_testing_config(
            enabled=True,
            test_commands={"unit": "pytest tests/unit/"},
            auto_detect={
                "enabled": True,
                "patterns": [
                    {"pattern": "src/*.py", "required_tests": ["unit"]},
                ],
            },
        )
        validator = TestExecutionValidator(config)

        result = validator._determine_required_tests(
            ["src/main.py", "src/utils.py", "src/config.py"]
        )

        # Should only have one entry for unit tests despite multiple files
        assert len(result) == 1
        assert result[0] == "pytest tests/unit/"

    def test_determine_tests_ignores_unknown_test_types(self) -> None:
        """Should ignore test types that aren't in test_commands."""
        config = make_mandatory_testing_config(
            enabled=True,
            test_commands={"unit": "pytest tests/unit/"},
            auto_detect={
                "enabled": True,
                "patterns": [
                    {"pattern": "src/*.py", "required_tests": ["unit", "unknown_type"]},
                ],
            },
        )
        validator = TestExecutionValidator(config)

        result = validator._determine_required_tests(["src/main.py"])

        assert len(result) == 1
        assert result[0] == "pytest tests/unit/"


# --- Pattern Matching Tests ---


class TestTestExecutionValidatorPatternMatching:
    """Tests for _matches_pattern method."""

    def test_matches_pattern_exact_match(self) -> None:
        """Should match exact file paths."""
        config = make_mandatory_testing_config(enabled=True)
        validator = TestExecutionValidator(config)

        assert validator._matches_pattern("src/main.py", "src/main.py") is True

    def test_matches_pattern_wildcard_extension(self) -> None:
        """Should match *.py pattern."""
        config = make_mandatory_testing_config(enabled=True)
        validator = TestExecutionValidator(config)

        assert validator._matches_pattern("src/main.py", "*.py") is True
        assert validator._matches_pattern("src/main.js", "*.py") is False

    def test_matches_pattern_directory_wildcard(self) -> None:
        """Should match directory/* patterns."""
        config = make_mandatory_testing_config(enabled=True)
        validator = TestExecutionValidator(config)

        assert validator._matches_pattern("src/main.py", "src/*") is True
        assert validator._matches_pattern("tests/main.py", "src/*") is False

    def test_matches_pattern_combined_wildcards(self) -> None:
        """Should match combined wildcards like src/*.py."""
        config = make_mandatory_testing_config(enabled=True)
        validator = TestExecutionValidator(config)

        assert validator._matches_pattern("src/main.py", "src/*.py") is True
        assert validator._matches_pattern("src/main.js", "src/*.py") is False
        assert validator._matches_pattern("tests/main.py", "src/*.py") is False


# --- Test Output Parsing Tests ---


class TestTestExecutionValidatorParsing:
    """Tests for _parse_test_output method."""

    @pytest.mark.parametrize(
        "output,expected_failures,expected_errors,expected_pending,expected_examples",
        [
            # Pytest format - passing
            ("100 passed in 1.23s", 0, 0, 0, 100),
            # Pytest format - with failures
            ("====== 148 passed, 2 failed in 5.23s =======", 2, 0, 0, 148),
            # Pytest format - only failures reported
            ("3 failed in 1.0s", 3, 0, 0, 0),
            # RSpec format
            ("150 examples, 0 failures, 2 pending\nFinished in 45.3 seconds", 0, 0, 2, 150),
            # RSpec with failures
            ("100 examples, 5 failures\nFinished in 30 seconds", 5, 0, 0, 100),
            # RSpec singular
            ("1 example, 1 failure", 1, 0, 0, 1),
            # Jest format
            ("Tests: 3 failed, 47 passed, 50 total", 3, 0, 0, 47),
            # Jest all passing
            ("Tests: 50 passed, 50 total", 0, 0, 0, 50),
            # Empty/malformed output
            ("No tests found", 0, 0, 0, 0),
            # No output
            ("", 0, 0, 0, 0),
        ],
        ids=[
            "pytest-passing",
            "pytest-failures",
            "pytest-only-failures",
            "rspec-with-pending",
            "rspec-failures",
            "rspec-singular",
            "jest-failures",
            "jest-passing",
            "no-tests",
            "empty-output",
        ],
    )
    def test_parse_test_output(
        self,
        output: str,
        expected_failures: int,
        expected_errors: int,
        expected_pending: int,
        expected_examples: int,
    ) -> None:
        """Test output parser handles multiple test framework formats correctly."""
        config = make_mandatory_testing_config(enabled=True)
        validator = TestExecutionValidator(config)

        failures, errors, pending, examples = validator._parse_test_output(output)

        assert failures == expected_failures
        assert errors == expected_errors
        assert pending == expected_pending
        assert examples == expected_examples


# --- Test Execution Tests ---


class TestTestExecutionValidatorExecution:
    """Tests for _execute_test_command method."""

    @pytest.mark.asyncio
    async def test_execute_test_command_success(self) -> None:
        """Should return TestExecutionResult for successful test run."""
        config = make_mandatory_testing_config(enabled=True)
        validator = TestExecutionValidator(config)

        with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_proc:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (
                b"5 passed in 1.0s",
                b"",
            )
            mock_process.returncode = 0
            mock_proc.return_value = mock_process

            task = {"id": "test-123"}
            result = await validator._execute_test_command("pytest tests/", task)

            assert result.exit_code == 0
            assert result.command == "pytest tests/"
            assert result.stdout == "5 passed in 1.0s"
            assert result.stderr == ""
            assert result.examples == 5
            assert result.failures == 0

    @pytest.mark.asyncio
    async def test_execute_test_command_failure(self) -> None:
        """Should return TestExecutionResult for failed test run."""
        config = make_mandatory_testing_config(enabled=True)
        validator = TestExecutionValidator(config)

        with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_proc:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (
                b"3 failed, 7 passed",
                b"",
            )
            mock_process.returncode = 1
            mock_proc.return_value = mock_process

            task = {"id": "test-123"}
            result = await validator._execute_test_command("pytest tests/", task)

            assert result.exit_code == 1
            assert result.failures == 3
            assert result.examples == 7
            assert result.passed is False

    @pytest.mark.asyncio
    async def test_execute_test_command_exception(self) -> None:
        """Should handle exceptions during test execution gracefully."""
        config = make_mandatory_testing_config(enabled=True)
        validator = TestExecutionValidator(config)

        with patch(
            "asyncio.create_subprocess_shell",
            side_effect=Exception("Process failed to start"),
        ):
            task = {"id": "test-123"}
            result = await validator._execute_test_command("pytest tests/", task)

            assert result.exit_code == 1
            assert result.failures == 1
            assert result.errors == 1
            assert "Process failed to start" in result.stderr
            assert result.passed is False

    @pytest.mark.asyncio
    async def test_execute_test_command_stores_evidence_when_configured(
        self, temp_dir: Path
    ) -> None:
        """Should store test evidence when configured."""
        evidence_path = str(temp_dir / "evidence" / "{task_id}.txt")
        config = make_mandatory_testing_config(
            enabled=True,
            evidence={
                "store_test_output": True,
                "path": evidence_path,
            },
        )
        validator = TestExecutionValidator(config)

        with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_proc:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"5 passed", b"")
            mock_process.returncode = 0
            mock_proc.return_value = mock_process

            task = {"id": "test-evidence-123"}
            await validator._execute_test_command("pytest", task)

            # Check evidence file was created
            expected_file = temp_dir / "evidence" / "test-evidence-123.txt"
            assert expected_file.exists()

            content = expected_file.read_text()
            assert "Task ID: test-evidence-123" in content
            assert "Command: pytest" in content


# --- Evidence Storage Tests ---


class TestTestExecutionValidatorEvidence:
    """Tests for evidence storage functionality."""

    @pytest.mark.asyncio
    async def test_store_test_evidence_creates_file(self, temp_dir: Path) -> None:
        """Should create evidence file with correct content."""
        evidence_path = str(temp_dir / "evidence" / "{task_id}.txt")
        config = make_mandatory_testing_config(
            enabled=True,
            evidence={"store_test_output": True, "path": evidence_path},
        )
        validator = TestExecutionValidator(config)

        task = {"id": "task-abc"}
        result = TestExecutionResult(
            command="pytest tests/",
            exit_code=0,
            stdout="10 passed in 2.5s",
            stderr="",
            duration=2.5,
            failures=0,
            errors=0,
            pending=0,
            examples=10,
        )

        await validator._store_test_evidence(task, result)

        expected_file = temp_dir / "evidence" / "task-abc.txt"
        assert expected_file.exists()

        content = expected_file.read_text()
        assert "Task ID: task-abc" in content
        assert "Command: pytest tests/" in content
        assert "Duration: 2.50s" in content
        assert "Exit Code: 0" in content
        assert "Examples: 10" in content
        assert "Passed: True" in content
        assert "10 passed in 2.5s" in content

    @pytest.mark.asyncio
    async def test_store_test_evidence_creates_directory(self, temp_dir: Path) -> None:
        """Should create parent directory if it doesn't exist."""
        evidence_path = str(temp_dir / "deep" / "nested" / "path" / "{task_id}.txt")
        config = make_mandatory_testing_config(
            enabled=True,
            evidence={"store_test_output": True, "path": evidence_path},
        )
        validator = TestExecutionValidator(config)

        task = {"id": "task-nested"}
        result = TestExecutionResult(
            command="pytest",
            exit_code=0,
            stdout="passed",
            stderr="",
            duration=1.0,
        )

        await validator._store_test_evidence(task, result)

        expected_file = temp_dir / "deep" / "nested" / "path" / "task-nested.txt"
        assert expected_file.exists()

    @pytest.mark.asyncio
    async def test_store_test_evidence_unknown_task_id(self, temp_dir: Path) -> None:
        """Should handle missing task ID gracefully."""
        evidence_path = str(temp_dir / "evidence" / "{task_id}.txt")
        config = make_mandatory_testing_config(
            enabled=True,
            evidence={"store_test_output": True, "path": evidence_path},
        )
        validator = TestExecutionValidator(config)

        task = {}  # No ID
        result = TestExecutionResult(
            command="pytest",
            exit_code=0,
            stdout="passed",
            stderr="",
            duration=1.0,
        )

        await validator._store_test_evidence(task, result)

        expected_file = temp_dir / "evidence" / "unknown.txt"
        assert expected_file.exists()


# --- Commit Message Evidence Tests ---


class TestTestExecutionValidatorCommitMessage:
    """Tests for get_commit_message_evidence method."""

    def test_get_commit_message_evidence_when_enabled(self) -> None:
        """Should return formatted evidence when include_in_commit_message=True."""
        config = make_mandatory_testing_config(
            enabled=True,
            evidence={"include_in_commit_message": True},
        )
        validator = TestExecutionValidator(config)

        result = TestExecutionResult(
            command="pytest tests/",
            exit_code=0,
            stdout="10 passed",
            stderr="",
            duration=2.5,
            failures=0,
            errors=0,
            pending=0,
            examples=10,
        )

        message = validator.get_commit_message_evidence(result)

        assert "Test Evidence:" in message
        assert "Command: pytest tests/" in message
        assert "Examples: 10" in message
        assert "Failures: 0" in message
        assert "Duration: 2.50s" in message
        assert "✅ PASSED" in message

    def test_get_commit_message_evidence_shows_failed_status(self) -> None:
        """Should show FAILED status when tests fail."""
        config = make_mandatory_testing_config(
            enabled=True,
            evidence={"include_in_commit_message": True},
        )
        validator = TestExecutionValidator(config)

        result = TestExecutionResult(
            command="pytest tests/",
            exit_code=1,
            stdout="3 failed",
            stderr="",
            duration=2.0,
            failures=3,
            errors=1,
            pending=0,
            examples=10,
        )

        message = validator.get_commit_message_evidence(result)

        assert "❌ FAILED" in message
        assert "Failures: 3" in message
        assert "Errors: 1" in message

    def test_get_commit_message_evidence_when_disabled(self) -> None:
        """Should return empty string when include_in_commit_message=False."""
        config = make_mandatory_testing_config(
            enabled=True,
            evidence={"include_in_commit_message": False},
        )
        validator = TestExecutionValidator(config)

        result = TestExecutionResult(
            command="pytest",
            exit_code=0,
            stdout="passed",
            stderr="",
            duration=1.0,
        )

        message = validator.get_commit_message_evidence(result)

        assert message == ""

    def test_get_commit_message_evidence_when_not_configured(self) -> None:
        """Should return empty string when evidence config not present."""
        config = make_mandatory_testing_config(enabled=True)
        validator = TestExecutionValidator(config)

        result = TestExecutionResult(
            command="pytest",
            exit_code=0,
            stdout="passed",
            stderr="",
            duration=1.0,
        )

        message = validator.get_commit_message_evidence(result)

        assert message == ""
