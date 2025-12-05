"""
Tests for QualityGatesCoordinator - comprehensive test coverage for coordinator.py

Tests for the quality gate orchestration module, covering:
- QualityGateResult dataclass and to_dict serialization
- QualityGatesCoordinator initialization and configuration
- validate_before_commit with all phases (test validation, success criteria, truth enforcement)
- get_commit_message_footer generation
"""

import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import AsyncMock, Mock, patch, MagicMock

import pytest

from sugar.quality_gates.coordinator import QualityGateResult, QualityGatesCoordinator
from sugar.quality_gates.evidence import EvidenceCollector


# --- Fixtures ---


@pytest.fixture
def temp_file() -> Generator[str, None, None]:
    """Create a temporary file with default content for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Test Content\nHello World\n")
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


def make_quality_gates_config(enabled: bool = True, **kwargs: Any) -> Dict[str, Any]:
    """Factory function for quality gates configuration."""
    config = {"enabled": enabled}
    config.update(kwargs)
    return {"quality_gates": config}


def make_mandatory_testing_config(
    enabled: bool = True, block_commits: bool = True, **kwargs: Any
) -> Dict[str, Any]:
    """Factory function for mandatory testing configuration."""
    config = {"enabled": enabled, "block_commits": block_commits}
    config.update(kwargs)
    return {"quality_gates": {"enabled": True, "mandatory_testing": config}}


def make_truth_enforcement_config(
    enabled: bool = True,
    mode: str = "strict",
    block_unproven_success: bool = True,
    rules: list = None,
) -> Dict[str, Any]:
    """Factory function for truth enforcement configuration."""
    return {
        "quality_gates": {
            "enabled": True,
            "truth_enforcement": {
                "enabled": enabled,
                "mode": mode,
                "block_unproven_success": block_unproven_success,
                "rules": rules or [],
            },
        }
    }


# --- QualityGateResult Tests ---


class TestQualityGateResult:
    """Tests for QualityGateResult dataclass."""

    def test_init_with_minimal_params(self) -> None:
        """Result should initialize with only required parameters."""
        result = QualityGateResult(can_complete=True, reason="Test passed")

        assert result.can_complete is True
        assert result.reason == "Test passed"
        assert result.tests_passed is False
        assert result.criteria_verified is False
        assert result.claims_proven is False
        assert result.preflight_passed is True
        assert result.functional_verified is True
        assert result.diff_validated is True
        assert result.evidence_collector is None
        assert result.failure_report is None

    def test_init_with_all_params(self) -> None:
        """Result should initialize with all parameters."""
        evidence_collector = EvidenceCollector("test-123")
        failure_report = Mock()

        result = QualityGateResult(
            can_complete=False,
            reason="Test failed",
            tests_passed=True,
            criteria_verified=True,
            claims_proven=False,
            preflight_passed=False,
            functional_verified=False,
            diff_validated=False,
            evidence_collector=evidence_collector,
            failure_report=failure_report,
        )

        assert result.can_complete is False
        assert result.reason == "Test failed"
        assert result.tests_passed is True
        assert result.criteria_verified is True
        assert result.claims_proven is False
        assert result.preflight_passed is False
        assert result.functional_verified is False
        assert result.diff_validated is False
        assert result.evidence_collector is evidence_collector
        assert result.failure_report is failure_report

    def test_to_dict_basic_fields(self) -> None:
        """to_dict should include all basic result fields."""
        result = QualityGateResult(
            can_complete=True,
            reason="All gates passed",
            tests_passed=True,
            criteria_verified=True,
            claims_proven=True,
            preflight_passed=True,
            functional_verified=True,
            diff_validated=True,
        )

        result_dict = result.to_dict()

        assert result_dict["can_complete"] is True
        assert result_dict["reason"] == "All gates passed"
        assert result_dict["tests_passed"] is True
        assert result_dict["criteria_verified"] is True
        assert result_dict["claims_proven"] is True
        assert result_dict["preflight_passed"] is True
        assert result_dict["functional_verified"] is True
        assert result_dict["diff_validated"] is True

    def test_to_dict_without_evidence_collector(self) -> None:
        """to_dict should not include evidence fields when collector is None."""
        result = QualityGateResult(
            can_complete=True, reason="Test", evidence_collector=None
        )

        result_dict = result.to_dict()

        assert "evidence_summary" not in result_dict
        assert "evidence_urls" not in result_dict

    def test_to_dict_with_evidence_collector(self) -> None:
        """to_dict should include evidence summary and URLs when collector exists."""
        evidence_collector = EvidenceCollector("test-123")
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/tmp/test.txt",
            failures=0,
            errors=0,
            pending=0,
            examples=10,
            duration=1.0,
        )

        result = QualityGateResult(
            can_complete=True,
            reason="Test passed",
            evidence_collector=evidence_collector,
        )

        result_dict = result.to_dict()

        assert "evidence_summary" in result_dict
        assert "evidence_urls" in result_dict
        assert result_dict["evidence_summary"]["total_evidence_items"] == 1

    def test_to_dict_with_failure_report_having_to_dict(self) -> None:
        """to_dict should call failure_report.to_dict() when available."""
        failure_report = Mock()
        failure_report.to_dict.return_value = {"error": "test error", "code": 1}

        result = QualityGateResult(
            can_complete=False, reason="Failed", failure_report=failure_report
        )

        result_dict = result.to_dict()

        assert "failure_report" in result_dict
        assert result_dict["failure_report"] == {"error": "test error", "code": 1}
        failure_report.to_dict.assert_called_once()

    def test_to_dict_with_failure_report_without_to_dict(self) -> None:
        """to_dict should convert failure_report to string when no to_dict method."""
        failure_report = "Simple string error"

        result = QualityGateResult(
            can_complete=False, reason="Failed", failure_report=failure_report
        )

        result_dict = result.to_dict()

        assert "failure_report" in result_dict
        assert result_dict["failure_report"] == "Simple string error"

    def test_to_dict_without_failure_report(self) -> None:
        """to_dict should not include failure_report field when None."""
        result = QualityGateResult(
            can_complete=True, reason="Passed", failure_report=None
        )

        result_dict = result.to_dict()

        assert "failure_report" not in result_dict


# --- QualityGatesCoordinator Initialization Tests ---


class TestQualityGatesCoordinatorInit:
    """Tests for QualityGatesCoordinator initialization."""

    def test_init_enabled(self) -> None:
        """Coordinator should be enabled when config specifies enabled=True."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        assert coordinator.is_enabled() is True

    def test_init_disabled(self) -> None:
        """Coordinator should be disabled when config specifies enabled=False."""
        config = make_quality_gates_config(enabled=False)
        coordinator = QualityGatesCoordinator(config)

        assert coordinator.is_enabled() is False

    def test_init_default_disabled(self) -> None:
        """Coordinator should be disabled when quality_gates config is empty."""
        coordinator = QualityGatesCoordinator({})

        assert coordinator.is_enabled() is False

    def test_init_creates_all_components(self) -> None:
        """Coordinator should initialize all component verifiers."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        assert coordinator.test_validator is not None
        assert coordinator.criteria_verifier is not None
        assert coordinator.truth_enforcer is not None
        assert coordinator.functional_verifier is not None
        assert coordinator.preflight_checker is not None
        assert coordinator.failure_handler is not None
        assert coordinator.diff_validator is not None

    def test_init_stores_config(self) -> None:
        """Coordinator should store the full configuration."""
        config = make_quality_gates_config(enabled=True, custom_setting="value")
        coordinator = QualityGatesCoordinator(config)

        assert coordinator.config == config
        assert coordinator.gates_config == config["quality_gates"]


# --- QualityGatesCoordinator validate_before_commit Tests ---


class TestQualityGatesCoordinatorValidation:
    """Tests for QualityGatesCoordinator.validate_before_commit method."""

    @pytest.mark.asyncio
    async def test_validate_when_disabled_allows_commit(self) -> None:
        """When disabled, coordinator should allow commits without validation."""
        config = make_quality_gates_config(enabled=False)
        coordinator = QualityGatesCoordinator(config)

        can_commit, result = await coordinator.validate_before_commit(
            task={"id": "test-123"}, changed_files=[]
        )

        assert can_commit is True
        assert result.can_complete is True
        assert result.reason == "Quality gates disabled"

    @pytest.mark.asyncio
    async def test_validate_without_success_criteria_passes(self) -> None:
        """Validation should pass when no success criteria are defined."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        can_commit, result = await coordinator.validate_before_commit(
            task={"id": "test-123"}, changed_files=[], claims=[]
        )

        assert can_commit is True
        assert result.can_complete is True

    @pytest.mark.asyncio
    async def test_validate_with_passing_success_criteria(self, temp_file: str) -> None:
        """Validation should pass when all success criteria are met."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        task = {
            "id": "test-123",
            "success_criteria": [
                {"type": "file_exists", "file_path": temp_file},
            ],
        }

        can_commit, result = await coordinator.validate_before_commit(
            task=task, changed_files=[], claims=[]
        )

        assert can_commit is True
        assert result.criteria_verified is True

    @pytest.mark.asyncio
    async def test_validate_with_failing_success_criteria(self) -> None:
        """Validation should fail when success criteria are not met."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        task = {
            "id": "test-123",
            "success_criteria": [
                {"type": "file_exists", "file_path": "/nonexistent/path.txt"},
            ],
        }

        can_commit, result = await coordinator.validate_before_commit(
            task=task, changed_files=[], claims=[]
        )

        assert can_commit is False
        assert result.criteria_verified is False
        assert "criteria" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_validate_creates_evidence_collector(self) -> None:
        """Validation should create an evidence collector for the task."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        task = {"id": "test-456"}

        can_commit, result = await coordinator.validate_before_commit(
            task=task, changed_files=[], claims=[]
        )

        assert result.evidence_collector is not None
        assert result.evidence_collector.task_id == "test-456"

    @pytest.mark.asyncio
    async def test_validate_uses_unknown_task_id_when_missing(self) -> None:
        """Validation should use 'unknown' when task ID is missing."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        can_commit, result = await coordinator.validate_before_commit(
            task={}, changed_files=[], claims=[]
        )

        assert result.evidence_collector.task_id == "unknown"


# --- Phase 1: Test Validation Tests ---


class TestQualityGatesPhase1TestValidation:
    """Tests for Phase 1 - Test Execution Validation."""

    @pytest.mark.asyncio
    async def test_phase1_skipped_when_test_validator_disabled(self) -> None:
        """Phase 1 should be skipped when test_validator is disabled."""
        config = {
            "quality_gates": {
                "enabled": True,
                "mandatory_testing": {"enabled": False},
            }
        }
        coordinator = QualityGatesCoordinator(config)

        can_commit, result = await coordinator.validate_before_commit(
            task={"id": "test-123"}, changed_files=[], claims=[]
        )

        assert can_commit is True
        # tests_passed defaults to False when not run
        assert result.tests_passed is False

    @pytest.mark.asyncio
    async def test_phase1_fails_when_tests_fail(self) -> None:
        """Phase 1 should fail when test execution fails."""
        config = make_mandatory_testing_config(enabled=True, block_commits=True)
        coordinator = QualityGatesCoordinator(config)

        # Mock the test validator to return failure
        mock_result = Mock()
        mock_result.passed = False
        mock_result.command = "pytest"
        mock_result.exit_code = 1
        mock_result.failures = 2
        mock_result.errors = 0
        mock_result.pending = 0
        mock_result.examples = 10
        mock_result.duration = 5.0

        coordinator.test_validator.validate_tests_before_commit = AsyncMock(
            return_value=(False, mock_result, "Tests failed: 2 failures")
        )

        can_commit, result = await coordinator.validate_before_commit(
            task={"id": "test-123"}, changed_files=["test.py"], claims=[]
        )

        assert can_commit is False
        assert result.tests_passed is False
        assert "Tests failed" in result.reason

    @pytest.mark.asyncio
    async def test_phase1_passes_when_tests_pass(self) -> None:
        """Phase 1 should pass when test execution succeeds."""
        config = make_mandatory_testing_config(enabled=True, block_commits=True)
        coordinator = QualityGatesCoordinator(config)

        # Mock the test validator to return success
        mock_result = Mock()
        mock_result.passed = True
        mock_result.command = "pytest"
        mock_result.exit_code = 0
        mock_result.failures = 0
        mock_result.errors = 0
        mock_result.pending = 0
        mock_result.examples = 10
        mock_result.duration = 5.0

        coordinator.test_validator.validate_tests_before_commit = AsyncMock(
            return_value=(True, mock_result, "All tests passed")
        )

        can_commit, result = await coordinator.validate_before_commit(
            task={"id": "test-123"}, changed_files=["test.py"], claims=[]
        )

        assert can_commit is True
        assert result.tests_passed is True


# --- Phase 3: Truth Enforcement Tests ---


class TestQualityGatesPhase3TruthEnforcement:
    """Tests for Phase 3 - Truth Enforcement."""

    @pytest.mark.asyncio
    async def test_phase3_skipped_when_no_claims(self) -> None:
        """Phase 3 should be skipped when no claims are provided."""
        config = make_truth_enforcement_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        can_commit, result = await coordinator.validate_before_commit(
            task={"id": "test-123"}, changed_files=[], claims=None
        )

        assert can_commit is True
        # claims_proven defaults to False when not evaluated
        assert result.claims_proven is False

    @pytest.mark.asyncio
    async def test_phase3_skipped_when_empty_claims(self) -> None:
        """Phase 3 should be skipped when claims list is empty."""
        config = make_truth_enforcement_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        can_commit, result = await coordinator.validate_before_commit(
            task={"id": "test-123"}, changed_files=[], claims=[]
        )

        assert can_commit is True
        assert result.claims_proven is False

    @pytest.mark.asyncio
    async def test_phase3_skipped_when_truth_enforcer_disabled(self) -> None:
        """Phase 3 should be skipped when truth enforcer is disabled."""
        config = make_truth_enforcement_config(enabled=False)
        coordinator = QualityGatesCoordinator(config)

        can_commit, result = await coordinator.validate_before_commit(
            task={"id": "test-123"},
            changed_files=[],
            claims=["all tests pass"],
        )

        assert can_commit is True
        assert result.claims_proven is False

    @pytest.mark.asyncio
    async def test_phase3_fails_when_claims_unproven(self) -> None:
        """Phase 3 should fail when claims cannot be proven."""
        rules = [
            {
                "claim": "all tests pass",
                "proof_required": "test_execution_evidence",
                "must_show": {"exit_code": 0, "failures": 0, "errors": 0},
            }
        ]
        config = make_truth_enforcement_config(enabled=True, mode="strict", rules=rules)
        coordinator = QualityGatesCoordinator(config)

        can_commit, result = await coordinator.validate_before_commit(
            task={"id": "test-123"},
            changed_files=[],
            claims=["all tests pass"],
        )

        assert can_commit is False
        assert result.claims_proven is False


# --- get_commit_message_footer Tests ---


class TestQualityGatesCommitFooter:
    """Tests for QualityGatesCoordinator.get_commit_message_footer method."""

    def test_footer_empty_without_evidence_collector(self) -> None:
        """Footer should be empty when result has no evidence collector."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        result = QualityGateResult(
            can_complete=True, reason="Test", evidence_collector=None
        )

        footer = coordinator.get_commit_message_footer(result)

        assert footer == ""

    def test_footer_includes_test_status_passed(self) -> None:
        """Footer should show passed status for tests."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        evidence_collector = EvidenceCollector("test-123")
        result = QualityGateResult(
            can_complete=True,
            reason="Test",
            tests_passed=True,
            evidence_collector=evidence_collector,
        )

        footer = coordinator.get_commit_message_footer(result)

        assert "Tests: ✅ PASSED" in footer

    def test_footer_includes_test_status_skipped(self) -> None:
        """Footer should show skipped status for tests when not passed."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        evidence_collector = EvidenceCollector("test-123")
        result = QualityGateResult(
            can_complete=True,
            reason="Test",
            tests_passed=False,
            evidence_collector=evidence_collector,
        )

        footer = coordinator.get_commit_message_footer(result)

        assert "Tests: ❌ SKIPPED" in footer

    def test_footer_includes_criteria_verified(self) -> None:
        """Footer should show verified status for criteria."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        evidence_collector = EvidenceCollector("test-123")
        result = QualityGateResult(
            can_complete=True,
            reason="Test",
            criteria_verified=True,
            evidence_collector=evidence_collector,
        )

        footer = coordinator.get_commit_message_footer(result)

        assert "Success Criteria: ✅ VERIFIED" in footer

    def test_footer_includes_criteria_none(self) -> None:
        """Footer should show NONE status when criteria not verified."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        evidence_collector = EvidenceCollector("test-123")
        result = QualityGateResult(
            can_complete=True,
            reason="Test",
            criteria_verified=False,
            evidence_collector=evidence_collector,
        )

        footer = coordinator.get_commit_message_footer(result)

        assert "Success Criteria: ⏭️ NONE" in footer

    def test_footer_includes_claims_proven(self) -> None:
        """Footer should show YES status when claims proven."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        evidence_collector = EvidenceCollector("test-123")
        result = QualityGateResult(
            can_complete=True,
            reason="Test",
            claims_proven=True,
            evidence_collector=evidence_collector,
        )

        footer = coordinator.get_commit_message_footer(result)

        assert "Claims Proven: ✅ YES" in footer

    def test_footer_includes_claims_none(self) -> None:
        """Footer should show NONE status when claims not proven."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        evidence_collector = EvidenceCollector("test-123")
        result = QualityGateResult(
            can_complete=True,
            reason="Test",
            claims_proven=False,
            evidence_collector=evidence_collector,
        )

        footer = coordinator.get_commit_message_footer(result)

        assert "Claims Proven: ⏭️ NONE" in footer

    def test_footer_includes_evidence_count(self) -> None:
        """Footer should include total evidence items count."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        evidence_collector = EvidenceCollector("test-123")
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/tmp/test.txt",
            failures=0,
            errors=0,
            pending=0,
            examples=10,
            duration=1.0,
        )
        result = QualityGateResult(
            can_complete=True,
            reason="Test",
            evidence_collector=evidence_collector,
        )

        footer = coordinator.get_commit_message_footer(result)

        assert "Total Evidence: 1 items" in footer

    def test_footer_includes_evidence_urls(self) -> None:
        """Footer should include evidence file paths when available."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        evidence_collector = EvidenceCollector("test-123")
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/tmp/test_output.txt",
            failures=0,
            errors=0,
            pending=0,
            examples=10,
            duration=1.0,
        )
        result = QualityGateResult(
            can_complete=True,
            reason="Test",
            evidence_collector=evidence_collector,
        )

        footer = coordinator.get_commit_message_footer(result)

        assert "Evidence:" in footer

    def test_footer_limits_evidence_urls_to_three(self) -> None:
        """Footer should only include first 3 evidence URLs."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        evidence_collector = EvidenceCollector("test-123")
        # Add 5 pieces of evidence
        for i in range(5):
            evidence_collector.add_test_evidence(
                command=f"pytest_{i}",
                exit_code=0,
                stdout_path=f"/tmp/test_{i}.txt",
                failures=0,
                errors=0,
                pending=0,
                examples=10,
                duration=1.0,
            )
        result = QualityGateResult(
            can_complete=True,
            reason="Test",
            evidence_collector=evidence_collector,
        )

        footer = coordinator.get_commit_message_footer(result)

        # Count URL lines in footer - should be at most 3
        url_lines = [
            line
            for line in footer.split("\n")
            if line.strip().startswith("-") and "/" in line
        ]
        assert len(url_lines) <= 3


# --- Integration Tests ---


class TestQualityGatesIntegration:
    """Integration tests for full quality gate validation flow."""

    @pytest.mark.asyncio
    async def test_full_flow_all_gates_pass(self, temp_file: str) -> None:
        """Full validation should pass when all gates succeed."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        task = {
            "id": "integration-test",
            "success_criteria": [
                {"type": "file_exists", "file_path": temp_file},
            ],
        }

        can_commit, result = await coordinator.validate_before_commit(
            task=task, changed_files=[], claims=[]
        )

        assert can_commit is True
        assert result.can_complete is True
        assert result.criteria_verified is True
        assert result.evidence_collector is not None

    @pytest.mark.asyncio
    async def test_full_flow_result_dict_complete(self, temp_file: str) -> None:
        """Full validation result should have complete to_dict output."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        task = {
            "id": "dict-test",
            "success_criteria": [
                {"type": "file_exists", "file_path": temp_file},
            ],
        }

        can_commit, result = await coordinator.validate_before_commit(
            task=task, changed_files=[], claims=[]
        )

        result_dict = result.to_dict()

        assert "can_complete" in result_dict
        assert "reason" in result_dict
        assert "tests_passed" in result_dict
        assert "criteria_verified" in result_dict
        assert "claims_proven" in result_dict
        assert "preflight_passed" in result_dict
        assert "functional_verified" in result_dict
        assert "diff_validated" in result_dict
        assert "evidence_summary" in result_dict
