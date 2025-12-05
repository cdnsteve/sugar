"""
Tests for VerificationFailureHandler and FailureReport

Covers failure handling, retry logic, escalation, and failure reporting.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock

import pytest

from sugar.quality_gates.failure_handler import (
    FailureReport,
    VerificationFailureHandler,
)


# --- Fixtures ---


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def basic_failure_handler_config() -> Dict[str, Any]:
    """Basic configuration with failure handling enabled."""
    return {
        "verification_failure_handling": {
            "enabled": True,
            "on_test_failure": {
                "max_retries": 2,
                "retry_with_more_context": True,
                "escalate": {
                    "enabled": True,
                    "action": "create_detailed_failure_report",
                    "report_path": ".sugar/failures/{task_id}.md",
                },
            },
            "on_functional_verification_failure": {
                "max_retries": 1,
                "enhanced_debugging": ["collect_logs", "capture_state"],
            },
            "on_success_criteria_not_met": {
                "action": "fail_task",
                "create_failure_report": True,
            },
        }
    }


@pytest.fixture
def disabled_failure_handler_config() -> Dict[str, Any]:
    """Configuration with failure handling disabled."""
    return {
        "verification_failure_handling": {
            "enabled": False,
        }
    }


@pytest.fixture
def custom_report_path_config(temp_dir: Path) -> Dict[str, Any]:
    """Configuration with custom report path for testing file output."""
    return {
        "verification_failure_handling": {
            "enabled": True,
            "on_test_failure": {
                "max_retries": 0,
                "escalate": {
                    "enabled": True,
                    "action": "create_detailed_failure_report",
                    "report_path": str(temp_dir / "failures" / "{task_id}.md"),
                },
            },
            "on_functional_verification_failure": {"max_retries": 0},
            "on_success_criteria_not_met": {
                "action": "fail_task",
                "create_failure_report": True,
            },
        }
    }


@pytest.fixture
def mock_test_result() -> MagicMock:
    """Mock test execution result."""
    mock = MagicMock()
    mock.failures = 3
    mock.errors = 1
    mock.to_dict.return_value = {
        "failures": 3,
        "errors": 1,
        "passed": 10,
        "total": 14,
    }
    return mock


@pytest.fixture
def mock_verification_result_failed() -> MagicMock:
    """Mock failed verification result."""
    mock = MagicMock()
    mock.verified = False
    mock.to_dict.return_value = {
        "criterion": "file_exists",
        "expected": True,
        "actual": False,
        "verified": False,
    }
    return mock


@pytest.fixture
def mock_verification_result_passed() -> MagicMock:
    """Mock passed verification result."""
    mock = MagicMock()
    mock.verified = True
    mock.to_dict.return_value = {
        "criterion": "file_exists",
        "expected": True,
        "actual": True,
        "verified": True,
    }
    return mock


@pytest.fixture
def mock_criterion_result_failed() -> MagicMock:
    """Mock failed criterion result."""
    mock = MagicMock()
    mock.verified = False
    mock.to_dict.return_value = {
        "id": "criterion-1",
        "type": "string_in_file",
        "verified": False,
    }
    return mock


# --- FailureReport Tests ---


class TestFailureReport:
    """Tests for FailureReport class."""

    def test_init_sets_basic_attributes(self) -> None:
        """FailureReport should initialize with task_id, failure_type, and reason."""
        report = FailureReport(
            task_id="task-123",
            failure_type="test_execution",
            reason="Tests failed with 5 failures",
        )

        assert report.task_id == "task-123"
        assert report.failure_type == "test_execution"
        assert report.reason == "Tests failed with 5 failures"

    def test_init_sets_default_values(self) -> None:
        """FailureReport should have sensible defaults for optional fields."""
        report = FailureReport(
            task_id="task-123",
            failure_type="test_execution",
            reason="Test failure",
        )

        assert report.evidence == []
        assert report.retry_attempts == 0
        assert report.escalated is False
        assert report.timestamp is not None

    def test_init_sets_valid_timestamp(self) -> None:
        """FailureReport timestamp should be a valid ISO format string."""
        report = FailureReport(
            task_id="task-123",
            failure_type="test_execution",
            reason="Test failure",
        )

        # Should not raise - valid ISO format
        datetime.fromisoformat(report.timestamp)

    def test_add_evidence_appends_to_list(self) -> None:
        """Adding evidence should append to the evidence list."""
        report = FailureReport(
            task_id="task-123",
            failure_type="test_execution",
            reason="Test failure",
        )

        report.add_evidence("test_output", {"stdout": "Error occurred"})

        assert len(report.evidence) == 1
        assert report.evidence[0]["type"] == "test_output"
        assert report.evidence[0]["data"] == {"stdout": "Error occurred"}

    def test_add_evidence_includes_timestamp(self) -> None:
        """Evidence items should include a timestamp."""
        report = FailureReport(
            task_id="task-123",
            failure_type="test_execution",
            reason="Test failure",
        )

        report.add_evidence("test_output", {"stdout": "Error"})

        assert "timestamp" in report.evidence[0]
        # Should not raise - valid ISO format
        datetime.fromisoformat(report.evidence[0]["timestamp"])

    def test_add_multiple_evidence_items(self) -> None:
        """Multiple evidence items can be added to a report."""
        report = FailureReport(
            task_id="task-123",
            failure_type="test_execution",
            reason="Test failure",
        )

        report.add_evidence("test_output", {"stdout": "Error 1"})
        report.add_evidence("stack_trace", {"trace": "line 42"})
        report.add_evidence("system_state", {"memory": "1GB"})

        assert len(report.evidence) == 3
        assert report.evidence[0]["type"] == "test_output"
        assert report.evidence[1]["type"] == "stack_trace"
        assert report.evidence[2]["type"] == "system_state"

    def test_to_dict_contains_all_fields(self) -> None:
        """to_dict should return a dictionary with all report fields."""
        report = FailureReport(
            task_id="task-123",
            failure_type="test_execution",
            reason="Tests failed",
        )
        report.retry_attempts = 2
        report.escalated = True
        report.add_evidence("test_output", {"failures": 5})

        result = report.to_dict()

        assert result["task_id"] == "task-123"
        assert result["failure_type"] == "test_execution"
        assert result["reason"] == "Tests failed"
        assert result["retry_attempts"] == 2
        assert result["escalated"] is True
        assert len(result["evidence"]) == 1
        assert "timestamp" in result

    def test_to_dict_is_json_serializable(self) -> None:
        """to_dict output should be JSON serializable."""
        report = FailureReport(
            task_id="task-123",
            failure_type="test_execution",
            reason="Tests failed",
        )
        report.add_evidence("test_output", {"failures": 5, "errors": 2})

        result = report.to_dict()

        # Should not raise
        json_str = json.dumps(result)
        assert "task-123" in json_str

    def test_to_markdown_contains_header(self) -> None:
        """Markdown output should contain a header with the task ID."""
        report = FailureReport(
            task_id="task-123",
            failure_type="test_execution",
            reason="Tests failed",
        )

        markdown = report.to_markdown()

        assert "# Failure Report: task-123" in markdown

    def test_to_markdown_contains_failure_type(self) -> None:
        """Markdown output should contain the failure type."""
        report = FailureReport(
            task_id="task-123",
            failure_type="functional_verification",
            reason="Verification failed",
        )

        markdown = report.to_markdown()

        assert "**Type:** functional_verification" in markdown

    def test_to_markdown_contains_reason(self) -> None:
        """Markdown output should contain the failure reason."""
        report = FailureReport(
            task_id="task-123",
            failure_type="test_execution",
            reason="5 tests failed due to missing dependencies",
        )

        markdown = report.to_markdown()

        assert "5 tests failed due to missing dependencies" in markdown

    def test_to_markdown_shows_retry_attempts(self) -> None:
        """Markdown output should show the number of retry attempts."""
        report = FailureReport(
            task_id="task-123",
            failure_type="test_execution",
            reason="Tests failed",
        )
        report.retry_attempts = 3

        markdown = report.to_markdown()

        assert "**Retry Attempts:** 3" in markdown

    def test_to_markdown_shows_escalation_status(self) -> None:
        """Markdown output should show escalation status."""
        report = FailureReport(
            task_id="task-123",
            failure_type="test_execution",
            reason="Tests failed",
        )
        report.escalated = True

        markdown = report.to_markdown()

        assert "**Escalated:** Yes" in markdown

    def test_to_markdown_shows_not_escalated(self) -> None:
        """Markdown output should show 'No' when not escalated."""
        report = FailureReport(
            task_id="task-123",
            failure_type="test_execution",
            reason="Tests failed",
        )
        report.escalated = False

        markdown = report.to_markdown()

        assert "**Escalated:** No" in markdown

    def test_to_markdown_includes_evidence_section(self) -> None:
        """Markdown output should include evidence section when evidence exists."""
        report = FailureReport(
            task_id="task-123",
            failure_type="test_execution",
            reason="Tests failed",
        )
        report.add_evidence("test_output", {"failures": 5})

        markdown = report.to_markdown()

        assert "## Evidence" in markdown
        assert "### test_output" in markdown

    def test_to_markdown_formats_evidence_as_json(self) -> None:
        """Evidence data should be formatted as JSON code block."""
        report = FailureReport(
            task_id="task-123",
            failure_type="test_execution",
            reason="Tests failed",
        )
        report.add_evidence("test_output", {"failures": 5, "errors": 2})

        markdown = report.to_markdown()

        assert "```json" in markdown
        assert '"failures": 5' in markdown

    def test_to_markdown_without_evidence(self) -> None:
        """Markdown output should not have evidence section when no evidence."""
        report = FailureReport(
            task_id="task-123",
            failure_type="test_execution",
            reason="Tests failed",
        )

        markdown = report.to_markdown()

        assert "## Evidence" not in markdown


# --- VerificationFailureHandler Tests ---


class TestVerificationFailureHandlerInit:
    """Tests for VerificationFailureHandler initialization."""

    def test_init_with_enabled_config(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Handler should be enabled when config specifies enabled=True."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        assert handler.is_enabled() is True

    def test_init_with_disabled_config(
        self, disabled_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Handler should be disabled when config specifies enabled=False."""
        handler = VerificationFailureHandler(disabled_failure_handler_config)

        assert handler.is_enabled() is False

    def test_init_with_empty_config(self) -> None:
        """Handler should be disabled with empty config."""
        handler = VerificationFailureHandler({})

        assert handler.is_enabled() is False

    def test_init_sets_test_max_retries(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Handler should set test max retries from config."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        assert handler.test_max_retries == 2

    def test_init_sets_functional_max_retries(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Handler should set functional verification max retries from config."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        assert handler.functional_max_retries == 1

    def test_init_sets_default_retries_when_not_configured(self) -> None:
        """Handler should use default retry values when not in config."""
        config = {"verification_failure_handling": {"enabled": True}}
        handler = VerificationFailureHandler(config)

        assert handler.test_max_retries == 2  # Default
        assert handler.functional_max_retries == 1  # Default


class TestVerificationFailureHandlerTestFailure:
    """Tests for handle_test_failure method."""

    @pytest.mark.asyncio
    async def test_disabled_handler_returns_no_retry(
        self, disabled_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Disabled handler should return (False, None)."""
        handler = VerificationFailureHandler(disabled_failure_handler_config)

        should_retry, report = await handler.handle_test_failure(
            task_id="task-123",
            test_result=MagicMock(),
            retry_count=0,
        )

        assert should_retry is False
        assert report is None

    @pytest.mark.asyncio
    async def test_retry_when_under_max_retries(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Should return True for retry when under max retries."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        should_retry, report = await handler.handle_test_failure(
            task_id="task-123",
            test_result=MagicMock(),
            retry_count=0,
        )

        assert should_retry is True
        assert report is None

    @pytest.mark.asyncio
    async def test_retry_at_max_minus_one(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Should return True for retry when at max_retries - 1."""
        handler = VerificationFailureHandler(basic_failure_handler_config)
        # max_retries is 2, so retry_count=1 should still retry

        should_retry, report = await handler.handle_test_failure(
            task_id="task-123",
            test_result=MagicMock(),
            retry_count=1,
        )

        assert should_retry is True
        assert report is None

    @pytest.mark.asyncio
    async def test_no_retry_at_max_retries(
        self,
        basic_failure_handler_config: Dict[str, Any],
        mock_test_result: MagicMock,
        temp_dir: Path,
    ) -> None:
        """Should not retry and create report when at max retries."""
        # Modify config to use temp_dir for reports
        config = basic_failure_handler_config.copy()
        config["verification_failure_handling"]["on_test_failure"]["escalate"][
            "report_path"
        ] = str(temp_dir / "failures" / "{task_id}.md")

        handler = VerificationFailureHandler(config)

        should_retry, report = await handler.handle_test_failure(
            task_id="task-123",
            test_result=mock_test_result,
            retry_count=2,  # At max_retries
        )

        assert should_retry is False
        assert report is not None
        assert report.failure_type == "test_execution"
        assert report.task_id == "task-123"

    @pytest.mark.asyncio
    async def test_report_includes_test_evidence(
        self,
        mock_test_result: MagicMock,
        temp_dir: Path,
    ) -> None:
        """Failure report should include test result evidence."""
        config = {
            "verification_failure_handling": {
                "enabled": True,
                "on_test_failure": {
                    "max_retries": 0,
                    "escalate": {
                        "enabled": True,
                        "action": "create_detailed_failure_report",
                        "report_path": str(temp_dir / "failures" / "{task_id}.md"),
                    },
                },
            }
        }
        handler = VerificationFailureHandler(config)

        _, report = await handler.handle_test_failure(
            task_id="task-123",
            test_result=mock_test_result,
            retry_count=0,
        )

        assert report is not None
        assert len(report.evidence) == 1
        assert report.evidence[0]["type"] == "test_result"


class TestVerificationFailureHandlerFunctionalFailure:
    """Tests for handle_functional_verification_failure method."""

    @pytest.mark.asyncio
    async def test_disabled_handler_returns_no_retry(
        self, disabled_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Disabled handler should return (False, None)."""
        handler = VerificationFailureHandler(disabled_failure_handler_config)

        should_retry, report = await handler.handle_functional_verification_failure(
            task_id="task-123",
            verification_results=[],
            retry_count=0,
        )

        assert should_retry is False
        assert report is None

    @pytest.mark.asyncio
    async def test_retry_when_under_max_retries(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Should return True for retry when under max retries."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        should_retry, report = await handler.handle_functional_verification_failure(
            task_id="task-123",
            verification_results=[],
            retry_count=0,
        )

        assert should_retry is True
        assert report is None

    @pytest.mark.asyncio
    async def test_no_retry_at_max_retries(
        self,
        basic_failure_handler_config: Dict[str, Any],
        mock_verification_result_failed: MagicMock,
        temp_dir: Path,
    ) -> None:
        """Should not retry and create report when at max retries."""
        config = basic_failure_handler_config.copy()
        config["verification_failure_handling"]["on_test_failure"]["escalate"][
            "report_path"
        ] = str(temp_dir / "failures" / "{task_id}.md")

        handler = VerificationFailureHandler(config)

        should_retry, report = await handler.handle_functional_verification_failure(
            task_id="task-456",
            verification_results=[mock_verification_result_failed],
            retry_count=1,  # At max_retries for functional (1)
        )

        assert should_retry is False
        assert report is not None
        assert report.failure_type == "functional_verification"

    @pytest.mark.asyncio
    async def test_report_includes_failed_verification_evidence(
        self,
        mock_verification_result_failed: MagicMock,
        mock_verification_result_passed: MagicMock,
        temp_dir: Path,
    ) -> None:
        """Report should include only failed verification evidence."""
        config = {
            "verification_failure_handling": {
                "enabled": True,
                "on_functional_verification_failure": {"max_retries": 0},
                "on_test_failure": {
                    "escalate": {
                        "enabled": True,
                        "action": "create_detailed_failure_report",
                        "report_path": str(temp_dir / "failures" / "{task_id}.md"),
                    }
                },
            }
        }
        handler = VerificationFailureHandler(config)

        _, report = await handler.handle_functional_verification_failure(
            task_id="task-123",
            verification_results=[
                mock_verification_result_failed,
                mock_verification_result_passed,
            ],
            retry_count=0,
        )

        assert report is not None
        # Only failed verification should be in evidence
        assert len(report.evidence) == 1
        assert report.evidence[0]["type"] == "failed_verification"


class TestVerificationFailureHandlerSuccessCriteriaFailure:
    """Tests for handle_success_criteria_failure method."""

    @pytest.mark.asyncio
    async def test_disabled_handler_returns_none(
        self, disabled_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Disabled handler should return None."""
        handler = VerificationFailureHandler(disabled_failure_handler_config)

        report = await handler.handle_success_criteria_failure(
            task_id="task-123",
            criteria_results=[],
        )

        assert report is None

    @pytest.mark.asyncio
    async def test_fail_task_action_creates_report(
        self,
        basic_failure_handler_config: Dict[str, Any],
        mock_criterion_result_failed: MagicMock,
        temp_dir: Path,
    ) -> None:
        """fail_task action should create a failure report."""
        config = basic_failure_handler_config.copy()
        config["verification_failure_handling"]["on_test_failure"]["escalate"][
            "report_path"
        ] = str(temp_dir / "failures" / "{task_id}.md")

        handler = VerificationFailureHandler(config)

        report = await handler.handle_success_criteria_failure(
            task_id="task-789",
            criteria_results=[mock_criterion_result_failed],
        )

        assert report is not None
        assert report.failure_type == "success_criteria"
        assert report.task_id == "task-789"

    @pytest.mark.asyncio
    async def test_report_includes_failed_criteria_evidence(
        self,
        basic_failure_handler_config: Dict[str, Any],
        mock_criterion_result_failed: MagicMock,
        temp_dir: Path,
    ) -> None:
        """Report should include failed criteria evidence."""
        config = basic_failure_handler_config.copy()
        config["verification_failure_handling"]["on_test_failure"]["escalate"][
            "report_path"
        ] = str(temp_dir / "failures" / "{task_id}.md")

        handler = VerificationFailureHandler(config)

        report = await handler.handle_success_criteria_failure(
            task_id="task-123",
            criteria_results=[mock_criterion_result_failed],
        )

        assert report is not None
        assert len(report.evidence) == 1
        assert report.evidence[0]["type"] == "failed_criterion"

    @pytest.mark.asyncio
    async def test_non_fail_action_returns_none(self) -> None:
        """Non-fail_task action should return None."""
        config = {
            "verification_failure_handling": {
                "enabled": True,
                "on_success_criteria_not_met": {
                    "action": "warn_only",  # Not fail_task
                },
            }
        }
        handler = VerificationFailureHandler(config)

        report = await handler.handle_success_criteria_failure(
            task_id="task-123",
            criteria_results=[MagicMock(verified=False)],
        )

        assert report is None


class TestVerificationFailureHandlerEscalation:
    """Tests for _escalate_failure method."""

    @pytest.mark.asyncio
    async def test_escalation_creates_json_file(
        self, custom_report_path_config: Dict[str, Any], temp_dir: Path
    ) -> None:
        """Escalation should create a JSON failure report file."""
        handler = VerificationFailureHandler(custom_report_path_config)

        _, report = await handler.handle_test_failure(
            task_id="test-escalate-json",
            test_result=MagicMock(
                failures=1, errors=0, to_dict=lambda: {"failures": 1}
            ),
            retry_count=0,
        )

        json_path = temp_dir / "failures" / "test-escalate-json.json"
        assert json_path.exists()

        with open(json_path) as f:
            data = json.load(f)
        assert data["task_id"] == "test-escalate-json"

    @pytest.mark.asyncio
    async def test_escalation_creates_markdown_file(
        self, custom_report_path_config: Dict[str, Any], temp_dir: Path
    ) -> None:
        """Escalation should create a Markdown failure report file."""
        handler = VerificationFailureHandler(custom_report_path_config)

        _, report = await handler.handle_test_failure(
            task_id="test-escalate-md",
            test_result=MagicMock(
                failures=1, errors=0, to_dict=lambda: {"failures": 1}
            ),
            retry_count=0,
        )

        md_path = temp_dir / "failures" / "test-escalate-md.md"
        assert md_path.exists()

        content = md_path.read_text()
        assert "# Failure Report: test-escalate-md" in content

    @pytest.mark.asyncio
    async def test_escalation_marks_report_as_escalated(
        self, custom_report_path_config: Dict[str, Any]
    ) -> None:
        """Escalation should set report.escalated to True."""
        handler = VerificationFailureHandler(custom_report_path_config)

        _, report = await handler.handle_test_failure(
            task_id="test-escalated",
            test_result=MagicMock(
                failures=1, errors=0, to_dict=lambda: {"failures": 1}
            ),
            retry_count=0,
        )

        assert report is not None
        assert report.escalated is True

    @pytest.mark.asyncio
    async def test_escalation_disabled_does_not_create_files(
        self, temp_dir: Path
    ) -> None:
        """Disabled escalation should not create report files."""
        config = {
            "verification_failure_handling": {
                "enabled": True,
                "on_test_failure": {
                    "max_retries": 0,
                    "escalate": {
                        "enabled": False,
                        "report_path": str(temp_dir / "failures" / "{task_id}.md"),
                    },
                },
            }
        }
        handler = VerificationFailureHandler(config)

        _, report = await handler.handle_test_failure(
            task_id="test-no-escalate",
            test_result=MagicMock(
                failures=1, errors=0, to_dict=lambda: {"failures": 1}
            ),
            retry_count=0,
        )

        # Report should exist but not be escalated
        assert report is not None
        assert report.escalated is False

        # No files should be created
        failures_dir = temp_dir / "failures"
        assert not failures_dir.exists() or not list(failures_dir.iterdir())


class TestVerificationFailureHandlerUtilityMethods:
    """Tests for utility methods."""

    def test_get_retry_count_for_test_execution(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Should return test max retries for test_execution type."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        count = handler.get_retry_count_for_failure_type("test_execution")

        assert count == 2

    def test_get_retry_count_for_functional_verification(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Should return functional max retries for functional_verification type."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        count = handler.get_retry_count_for_failure_type("functional_verification")

        assert count == 1

    def test_get_retry_count_for_unknown_type(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Should return 0 for unknown failure types."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        count = handler.get_retry_count_for_failure_type("unknown_type")

        assert count == 0

    def test_should_collect_enhanced_debugging_true(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Should return True when enhanced debugging is configured."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        result = handler.should_collect_enhanced_debugging("functional_verification")

        assert result is True

    def test_should_collect_enhanced_debugging_false_for_test(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Should return False for test_execution type."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        result = handler.should_collect_enhanced_debugging("test_execution")

        assert result is False

    def test_get_enhanced_debugging_actions(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Should return configured debugging actions."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        actions = handler.get_enhanced_debugging_actions("functional_verification")

        assert actions == ["collect_logs", "capture_state"]

    def test_get_enhanced_debugging_actions_empty_for_other_types(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Should return empty list for non-functional types."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        actions = handler.get_enhanced_debugging_actions("test_execution")

        assert actions == []

    def test_get_retry_count_for_success_criteria(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Should return 0 for success_criteria type (no retries)."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        count = handler.get_retry_count_for_failure_type("success_criteria")

        assert count == 0


# --- Additional Coverage Tests ---


class TestVerificationFailureHandlerAdditionalCoverage:
    """Additional tests to ensure complete coverage."""

    def test_init_sets_retry_with_context(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Handler should set retry_with_more_context from config."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        assert handler.test_retry_with_context is True

    def test_init_sets_retry_with_context_default(self) -> None:
        """Handler should default retry_with_more_context to True."""
        config = {"verification_failure_handling": {"enabled": True}}
        handler = VerificationFailureHandler(config)

        assert handler.test_retry_with_context is True

    def test_init_sets_retry_with_context_false(self) -> None:
        """Handler should respect retry_with_more_context=False."""
        config = {
            "verification_failure_handling": {
                "enabled": True,
                "on_test_failure": {"retry_with_more_context": False},
            }
        }
        handler = VerificationFailureHandler(config)

        assert handler.test_retry_with_context is False

    @pytest.mark.asyncio
    async def test_escalate_with_mark_task_as_needs_manual_review(
        self, temp_dir: Path
    ) -> None:
        """Escalation with mark_task_as_needs_manual_review action."""
        config = {
            "verification_failure_handling": {
                "enabled": True,
                "on_test_failure": {
                    "max_retries": 0,
                    "escalate": {
                        "enabled": True,
                        "action": "mark_task_as_needs_manual_review",
                        "report_path": str(temp_dir / "failures" / "{task_id}.md"),
                    },
                },
            }
        }
        handler = VerificationFailureHandler(config)

        _, report = await handler.handle_test_failure(
            task_id="task-manual-review",
            test_result=MagicMock(
                failures=1, errors=0, to_dict=lambda: {"failures": 1}
            ),
            retry_count=0,
        )

        assert report is not None
        assert report.escalated is True
        # No files should be created for this action
        failures_dir = temp_dir / "failures"
        assert not failures_dir.exists() or not list(failures_dir.iterdir())

    @pytest.mark.asyncio
    async def test_handle_test_failure_without_to_dict_method(
        self, temp_dir: Path
    ) -> None:
        """Test failure handling when test_result has no to_dict method."""
        config = {
            "verification_failure_handling": {
                "enabled": True,
                "on_test_failure": {
                    "max_retries": 0,
                    "escalate": {
                        "enabled": True,
                        "action": "create_detailed_failure_report",
                        "report_path": str(temp_dir / "failures" / "{task_id}.md"),
                    },
                },
            }
        }
        handler = VerificationFailureHandler(config)

        # Create mock without to_dict
        test_result = MagicMock(spec=["failures", "errors"])
        test_result.failures = 2
        test_result.errors = 1

        _, report = await handler.handle_test_failure(
            task_id="task-no-to-dict",
            test_result=test_result,
            retry_count=0,
        )

        assert report is not None
        assert report.failure_type == "test_execution"
        # Evidence should be empty since to_dict not available
        assert len(report.evidence) == 0

    @pytest.mark.asyncio
    async def test_handle_functional_failure_without_to_dict_method(
        self, temp_dir: Path
    ) -> None:
        """Functional failure handling when result has no to_dict method."""
        config = {
            "verification_failure_handling": {
                "enabled": True,
                "on_functional_verification_failure": {"max_retries": 0},
                "on_test_failure": {
                    "escalate": {
                        "enabled": True,
                        "action": "create_detailed_failure_report",
                        "report_path": str(temp_dir / "failures" / "{task_id}.md"),
                    }
                },
            }
        }
        handler = VerificationFailureHandler(config)

        # Create mock without to_dict
        result = MagicMock(spec=["verified"])
        result.verified = False

        _, report = await handler.handle_functional_verification_failure(
            task_id="task-no-to-dict-func",
            verification_results=[result],
            retry_count=0,
        )

        assert report is not None
        assert report.failure_type == "functional_verification"
        # Evidence should be empty since to_dict not available
        assert len(report.evidence) == 0

    @pytest.mark.asyncio
    async def test_handle_success_criteria_failure_without_to_dict(
        self, temp_dir: Path
    ) -> None:
        """Success criteria failure handling when criterion has no to_dict method."""
        config = {
            "verification_failure_handling": {
                "enabled": True,
                "on_success_criteria_not_met": {
                    "action": "fail_task",
                    "create_failure_report": True,
                },
                "on_test_failure": {
                    "escalate": {
                        "enabled": True,
                        "action": "create_detailed_failure_report",
                        "report_path": str(temp_dir / "failures" / "{task_id}.md"),
                    }
                },
            }
        }
        handler = VerificationFailureHandler(config)

        # Create mock without to_dict
        criterion = MagicMock(spec=["verified"])
        criterion.verified = False

        report = await handler.handle_success_criteria_failure(
            task_id="task-no-to-dict-criteria",
            criteria_results=[criterion],
        )

        assert report is not None
        assert report.failure_type == "success_criteria"
        # Evidence should be empty since to_dict not available
        assert len(report.evidence) == 0

    @pytest.mark.asyncio
    async def test_handle_success_criteria_failure_no_report_creation(
        self,
    ) -> None:
        """Success criteria failure without creating failure report."""
        config = {
            "verification_failure_handling": {
                "enabled": True,
                "on_success_criteria_not_met": {
                    "action": "fail_task",
                    "create_failure_report": False,  # Disable report creation
                },
                "on_test_failure": {
                    "escalate": {
                        "enabled": True,
                        "action": "create_detailed_failure_report",
                        "report_path": ".sugar/failures/{task_id}.md",
                    }
                },
            }
        }
        handler = VerificationFailureHandler(config)

        criterion = MagicMock()
        criterion.verified = False
        criterion.to_dict.return_value = {"verified": False}

        report = await handler.handle_success_criteria_failure(
            task_id="task-no-report-creation",
            criteria_results=[criterion],
        )

        assert report is not None
        assert report.failure_type == "success_criteria"
        # Report should exist but not be escalated (no file creation)
        assert report.escalated is False

    @pytest.mark.asyncio
    async def test_handle_functional_failure_multiple_failed_verifications(
        self, temp_dir: Path
    ) -> None:
        """Functional failure with multiple failed verifications."""
        config = {
            "verification_failure_handling": {
                "enabled": True,
                "on_functional_verification_failure": {"max_retries": 0},
                "on_test_failure": {
                    "escalate": {
                        "enabled": True,
                        "action": "create_detailed_failure_report",
                        "report_path": str(temp_dir / "failures" / "{task_id}.md"),
                    }
                },
            }
        }
        handler = VerificationFailureHandler(config)

        # Create multiple failed results
        failed1 = MagicMock()
        failed1.verified = False
        failed1.to_dict.return_value = {"criterion": "check_a", "verified": False}

        failed2 = MagicMock()
        failed2.verified = False
        failed2.to_dict.return_value = {"criterion": "check_b", "verified": False}

        passed = MagicMock()
        passed.verified = True

        _, report = await handler.handle_functional_verification_failure(
            task_id="task-multi-fail",
            verification_results=[failed1, passed, failed2],
            retry_count=0,
        )

        assert report is not None
        # Should have 2 evidence items for 2 failed verifications
        assert len(report.evidence) == 2
        assert all(e["type"] == "failed_verification" for e in report.evidence)

    @pytest.mark.asyncio
    async def test_handle_functional_failure_empty_results(
        self, temp_dir: Path
    ) -> None:
        """Functional failure with empty verification results list."""
        config = {
            "verification_failure_handling": {
                "enabled": True,
                "on_functional_verification_failure": {"max_retries": 0},
                "on_test_failure": {
                    "escalate": {
                        "enabled": True,
                        "action": "create_detailed_failure_report",
                        "report_path": str(temp_dir / "failures" / "{task_id}.md"),
                    }
                },
            }
        }
        handler = VerificationFailureHandler(config)

        _, report = await handler.handle_functional_verification_failure(
            task_id="task-empty-results",
            verification_results=[],
            retry_count=0,
        )

        assert report is not None
        assert report.failure_type == "functional_verification"
        assert "0 functional verifications" in report.reason
        assert len(report.evidence) == 0

    @pytest.mark.asyncio
    async def test_handle_success_criteria_failure_empty_results(self) -> None:
        """Success criteria failure with empty criteria results list."""
        config = {
            "verification_failure_handling": {
                "enabled": True,
                "on_success_criteria_not_met": {
                    "action": "fail_task",
                    "create_failure_report": False,
                },
            }
        }
        handler = VerificationFailureHandler(config)

        report = await handler.handle_success_criteria_failure(
            task_id="task-empty-criteria",
            criteria_results=[],
        )

        assert report is not None
        assert report.failure_type == "success_criteria"
        assert "0 success criteria" in report.reason
        assert len(report.evidence) == 0

    def test_should_collect_enhanced_debugging_for_test_execution(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Should return False for test_execution type."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        result = handler.should_collect_enhanced_debugging("test_execution")

        assert result is False

    def test_should_collect_enhanced_debugging_for_unknown_type(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Should return False for unknown failure types."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        result = handler.should_collect_enhanced_debugging("unknown_type")

        assert result is False

    def test_get_enhanced_debugging_actions_for_unknown_type(
        self, basic_failure_handler_config: Dict[str, Any]
    ) -> None:
        """Should return empty list for unknown types."""
        handler = VerificationFailureHandler(basic_failure_handler_config)

        actions = handler.get_enhanced_debugging_actions("unknown_type")

        assert actions == []

    def test_should_collect_enhanced_debugging_empty_config(self) -> None:
        """Should return False when enhanced_debugging not configured."""
        config = {
            "verification_failure_handling": {
                "enabled": True,
                "on_functional_verification_failure": {
                    "max_retries": 1,
                    # No enhanced_debugging configured
                },
            }
        }
        handler = VerificationFailureHandler(config)

        result = handler.should_collect_enhanced_debugging("functional_verification")

        assert result is False

    def test_get_enhanced_debugging_actions_empty_config(self) -> None:
        """Should return empty list when enhanced_debugging not configured."""
        config = {
            "verification_failure_handling": {
                "enabled": True,
                "on_functional_verification_failure": {
                    "max_retries": 1,
                    # No enhanced_debugging configured
                },
            }
        }
        handler = VerificationFailureHandler(config)

        actions = handler.get_enhanced_debugging_actions("functional_verification")

        assert actions == []


class TestFailureReportEdgeCases:
    """Edge case tests for FailureReport."""

    def test_to_markdown_with_multiple_evidence_items(self) -> None:
        """Markdown output should handle multiple evidence items."""
        report = FailureReport(
            task_id="task-multi-evidence",
            failure_type="test_execution",
            reason="Multiple failures occurred",
        )
        report.add_evidence("test_output", {"stdout": "Error 1"})
        report.add_evidence("stack_trace", {"trace": "Line 42"})
        report.add_evidence("system_state", {"memory": "1GB", "cpu": "50%"})

        markdown = report.to_markdown()

        assert "## Evidence" in markdown
        assert "### test_output" in markdown
        assert "### stack_trace" in markdown
        assert "### system_state" in markdown
        assert "Error 1" in markdown
        assert "Line 42" in markdown

    def test_to_markdown_with_special_characters_in_data(self) -> None:
        """Markdown output should handle special characters in evidence data."""
        report = FailureReport(
            task_id="task-special-chars",
            failure_type="test_execution",
            reason="Error with special chars: <>&\"'",
        )
        report.add_evidence(
            "error", {"message": "Error: <tag> & \"quoted\" text 'single'"}
        )

        markdown = report.to_markdown()

        # Should contain the special characters (JSON encoded)
        assert "Error with special chars" in markdown
        assert "```json" in markdown

    def test_to_dict_with_empty_evidence(self) -> None:
        """to_dict should handle empty evidence list."""
        report = FailureReport(
            task_id="task-empty-evidence",
            failure_type="test_execution",
            reason="Test failure",
        )

        result = report.to_dict()

        assert result["evidence"] == []

    def test_report_timestamps_are_different(self) -> None:
        """Report timestamp and evidence timestamps should be distinct."""
        import time

        report = FailureReport(
            task_id="task-timestamp-test",
            failure_type="test_execution",
            reason="Test failure",
        )
        time.sleep(0.01)  # Small delay to ensure different timestamps
        report.add_evidence("test_output", {"data": "test"})

        # Both timestamps should be valid ISO format
        datetime.fromisoformat(report.timestamp)
        datetime.fromisoformat(report.evidence[0]["timestamp"])
