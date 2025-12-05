"""
Tests for Quality Gates - Phase 1 Features

Tests mandatory test execution, success criteria verification, and truth enforcement.
"""

import tempfile
from pathlib import Path
from typing import Dict, Any, Generator

import pytest

from sugar.quality_gates import (
    TestExecutionValidator,
    TestExecutionResult,
    SuccessCriteriaVerifier,
    SuccessCriterion,
    TruthEnforcer,
    EvidenceCollector,
    QualityGatesCoordinator,
)


# --- Fixtures ---


@pytest.fixture
def temp_file() -> Generator[str, None, None]:
    """Create a temporary file with default content for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Test Content\nHello World\n")
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def temp_file_empty() -> Generator[str, None, None]:
    """Create an empty temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


def make_mandatory_testing_config(
    enabled: bool = True, block_commits: bool = True, **kwargs: Any
) -> Dict[str, Any]:
    """Factory function for mandatory testing configuration."""
    config = {"enabled": enabled, "block_commits": block_commits}
    config.update(kwargs)
    return {"quality_gates": {"mandatory_testing": config}}


def make_truth_enforcement_config(
    enabled: bool = True,
    mode: str = "strict",
    block_unproven_success: bool = True,
    rules: list = None,
) -> Dict[str, Any]:
    """Factory function for truth enforcement configuration."""
    return {
        "quality_gates": {
            "truth_enforcement": {
                "enabled": enabled,
                "mode": mode,
                "block_unproven_success": block_unproven_success,
                "rules": rules or [],
            }
        }
    }


def make_quality_gates_config(enabled: bool = True, **kwargs: Any) -> Dict[str, Any]:
    """Factory function for quality gates configuration."""
    config = {"enabled": enabled}
    config.update(kwargs)
    return {"quality_gates": config}


class TestTestExecutionValidator:
    """Tests for TestExecutionValidator - mandatory test execution validation."""

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

    @pytest.mark.parametrize(
        "output,expected_failures,expected_examples,expected_pending",
        [
            # Pytest format
            (
                "====== 148 passed, 2 failed in 5.23s =======",
                2,
                148,
                0,
            ),
            # RSpec format
            (
                "150 examples, 0 failures, 2 pending\nFinished in 45.3 seconds",
                0,
                150,
                2,
            ),
            # Jest format
            (
                "Tests: 3 failed, 47 passed, 50 total",
                3,
                47,
                0,
            ),
            # All passing pytest
            (
                "100 passed in 1.23s",
                0,
                100,
                0,
            ),
            # Empty/malformed output
            (
                "No tests found",
                0,
                0,
                0,
            ),
        ],
        ids=["pytest", "rspec", "jest", "pytest-passing", "empty-output"],
    )
    def test_parse_test_output_parametrized(
        self,
        output: str,
        expected_failures: int,
        expected_examples: int,
        expected_pending: int,
    ) -> None:
        """Test output parser handles multiple test framework formats correctly."""
        config = make_mandatory_testing_config(enabled=True)
        validator = TestExecutionValidator(config)

        failures, errors, pending, examples = validator._parse_test_output(output)

        assert failures == expected_failures
        assert examples == expected_examples
        assert pending == expected_pending


class TestSuccessCriteriaVerifier:
    """Tests for SuccessCriteriaVerifier - success criteria validation."""

    @pytest.mark.asyncio
    async def test_verify_file_exists_when_file_present(self, temp_file: str) -> None:
        """File exists criterion should verify True when file is present."""
        verifier = SuccessCriteriaVerifier({})
        criterion_def = {"type": "file_exists", "file_path": temp_file}

        criterion = await verifier._verify_file_exists(criterion_def)

        assert criterion.verified is True
        assert criterion.actual is True

    @pytest.mark.asyncio
    async def test_verify_file_exists_when_file_missing(self) -> None:
        """File exists criterion should verify False when file is missing."""
        verifier = SuccessCriteriaVerifier({})
        criterion_def = {"type": "file_exists", "file_path": "/nonexistent/file.txt"}

        criterion = await verifier._verify_file_exists(criterion_def)

        assert criterion.verified is False
        assert criterion.actual is False

    @pytest.mark.asyncio
    async def test_verify_string_in_file_when_string_present(
        self, temp_file: str
    ) -> None:
        """String in file criterion should verify True when string is found."""
        verifier = SuccessCriteriaVerifier({})
        criterion_def = {
            "type": "string_in_file",
            "file_path": temp_file,
            "search_string": "Test Content",
        }

        criterion = await verifier._verify_string_in_file(criterion_def)

        assert criterion.verified is True
        assert criterion.actual is True

    @pytest.mark.asyncio
    async def test_verify_string_in_file_when_string_missing(
        self, temp_file: str
    ) -> None:
        """String in file criterion should verify False when string not found."""
        verifier = SuccessCriteriaVerifier({})
        criterion_def = {
            "type": "string_in_file",
            "file_path": temp_file,
            "search_string": "Nonexistent String",
        }

        criterion = await verifier._verify_string_in_file(criterion_def)

        assert criterion.verified is False
        assert criterion.actual is False

    @pytest.mark.asyncio
    async def test_verify_all_criteria_all_passing(self, temp_file: str) -> None:
        """All criteria verification should return True when all pass."""
        verifier = SuccessCriteriaVerifier({})
        criteria = [
            {"type": "file_exists", "file_path": temp_file},
            {
                "type": "string_in_file",
                "file_path": temp_file,
                "search_string": "Test Content",
            },
        ]

        all_verified, verified_criteria = await verifier.verify_all_criteria(criteria)

        assert all_verified is True
        assert len(verified_criteria) == 2
        assert all(c.verified for c in verified_criteria)

    @pytest.mark.asyncio
    async def test_verify_all_criteria_with_failure(self, temp_file: str) -> None:
        """All criteria verification should return False when any fails."""
        verifier = SuccessCriteriaVerifier({})
        criteria = [
            {"type": "file_exists", "file_path": temp_file},
            {"type": "file_exists", "file_path": "/nonexistent/file.txt"},
        ]

        all_verified, verified_criteria = await verifier.verify_all_criteria(criteria)

        assert all_verified is False
        assert len(verified_criteria) == 2
        assert sum(c.verified for c in verified_criteria) == 1

    @pytest.mark.asyncio
    async def test_verify_all_criteria_empty_list(self) -> None:
        """All criteria verification should return False for empty criteria list."""
        verifier = SuccessCriteriaVerifier({})

        all_verified, verified_criteria = await verifier.verify_all_criteria([])

        assert all_verified is False
        assert len(verified_criteria) == 0


class TestTruthEnforcer:
    """Tests for TruthEnforcer - proof-based claim verification."""

    @pytest.fixture
    def test_pass_rule(self) -> list:
        """Standard rule requiring test execution evidence."""
        return [
            {
                "claim": "all tests pass",
                "proof_required": "test_execution_evidence",
                "must_show": {"exit_code": 0, "failures": 0, "errors": 0},
            }
        ]

    def test_init_with_config_strict_mode(self, test_pass_rule: list) -> None:
        """Enforcer should initialize with strict mode and rules from config."""
        config = make_truth_enforcement_config(
            enabled=True, mode="strict", rules=test_pass_rule
        )
        enforcer = TruthEnforcer(config)

        assert enforcer.is_enabled() is True
        assert enforcer.mode == "strict"
        assert len(enforcer.rules) == 1

    def test_init_disabled(self) -> None:
        """Enforcer should be disabled when enabled=False in config."""
        config = make_truth_enforcement_config(enabled=False)
        enforcer = TruthEnforcer(config)

        assert enforcer.is_enabled() is False

    def test_verify_claim_with_matching_evidence(self, test_pass_rule: list) -> None:
        """Claim should be proven when matching evidence exists."""
        config = make_truth_enforcement_config(enabled=True, rules=test_pass_rule)
        enforcer = TruthEnforcer(config)
        evidence_collector = EvidenceCollector("test-123")

        # Add passing test evidence
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/tmp/test.txt",
            failures=0,
            errors=0,
            pending=0,
            examples=150,
            duration=45.3,
        )

        all_proven, claims = enforcer.verify_claims(
            ["all tests pass"], evidence_collector
        )

        assert all_proven is True
        assert len(claims) == 1
        assert claims[0].has_proof is True

    def test_verify_claim_without_evidence(self, test_pass_rule: list) -> None:
        """Claim should not be proven when no evidence exists."""
        config = make_truth_enforcement_config(
            enabled=True, mode="strict", rules=test_pass_rule
        )
        enforcer = TruthEnforcer(config)
        evidence_collector = EvidenceCollector("test-123")
        # No evidence added

        all_proven, claims = enforcer.verify_claims(
            ["all tests pass"], evidence_collector
        )

        assert all_proven is False
        assert len(claims) == 1
        assert claims[0].has_proof is False

    def test_verify_claim_with_failing_evidence(self, test_pass_rule: list) -> None:
        """Claim should not be proven when evidence shows failures."""
        config = make_truth_enforcement_config(enabled=True, rules=test_pass_rule)
        enforcer = TruthEnforcer(config)
        evidence_collector = EvidenceCollector("test-123")

        # Add failing test evidence
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=1,
            stdout_path="/tmp/test.txt",
            failures=5,
            errors=0,
            pending=0,
            examples=150,
            duration=45.3,
        )

        all_proven, claims = enforcer.verify_claims(
            ["all tests pass"], evidence_collector
        )

        assert all_proven is False

    def test_can_complete_task_strict_mode_blocks_unproven(
        self, test_pass_rule: list
    ) -> None:
        """Strict mode should block task completion without proof."""
        config = make_truth_enforcement_config(
            enabled=True,
            mode="strict",
            block_unproven_success=True,
            rules=test_pass_rule,
        )
        enforcer = TruthEnforcer(config)
        evidence_collector = EvidenceCollector("test-123")
        # No evidence

        can_complete, reason = enforcer.can_complete_task(
            ["all tests pass"], evidence_collector
        )

        assert can_complete is False
        assert "lack proof" in reason.lower()

    def test_can_complete_task_with_proof(self, test_pass_rule: list) -> None:
        """Task should be completable when all claims have proof."""
        config = make_truth_enforcement_config(enabled=True, rules=test_pass_rule)
        enforcer = TruthEnforcer(config)
        evidence_collector = EvidenceCollector("test-123")

        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/tmp/test.txt",
            failures=0,
            errors=0,
            pending=0,
            examples=150,
            duration=45.3,
        )

        can_complete, reason = enforcer.can_complete_task(
            ["all tests pass"], evidence_collector
        )

        assert can_complete is True
        assert "proven" in reason.lower()


class TestEvidenceCollector:
    """Tests for EvidenceCollector - evidence storage and management."""

    def test_init_creates_empty_collector(self) -> None:
        """New collector should have task ID and empty evidence list."""
        collector = EvidenceCollector("task-123")

        assert collector.task_id == "task-123"
        assert len(collector.evidence_items) == 0

    def test_add_test_evidence_passing_marks_verified(self) -> None:
        """Passing test evidence should be marked as verified."""
        collector = EvidenceCollector("task-123")

        evidence = collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/tmp/test.txt",
            failures=0,
            errors=0,
            pending=2,
            examples=150,
            duration=45.3,
        )

        assert evidence.verified is True
        assert len(collector.evidence_items) == 1

    def test_add_test_evidence_failing_marks_unverified(self) -> None:
        """Failing test evidence should be marked as unverified."""
        collector = EvidenceCollector("task-123")

        evidence = collector.add_test_evidence(
            command="pytest",
            exit_code=1,
            stdout_path="/tmp/test.txt",
            failures=5,
            errors=2,
            pending=0,
            examples=150,
            duration=45.3,
        )

        assert evidence.verified is False
        assert len(collector.evidence_items) == 1

    def test_has_all_evidence_verified_returns_true_when_all_pass(self) -> None:
        """Should return True when all evidence items are verified."""
        collector = EvidenceCollector("task-123")

        collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/tmp/test.txt",
            failures=0,
            errors=0,
            pending=0,
            examples=150,
            duration=45.3,
        )
        collector.add_success_criteria_evidence(
            criterion_id="crit-1",
            criterion_type="file_exists",
            expected=True,
            actual=True,
        )

        assert collector.has_all_evidence_verified() is True

    def test_has_all_evidence_verified_returns_false_when_any_fail(self) -> None:
        """Should return False when any evidence item is unverified."""
        collector = EvidenceCollector("task-123")

        collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/tmp/test.txt",
            failures=0,
            errors=0,
            pending=0,
            examples=150,
            duration=45.3,
        )
        collector.add_success_criteria_evidence(
            criterion_id="crit-1",
            criterion_type="file_exists",
            expected=True,
            actual=False,  # Mismatch - should mark as unverified
        )

        assert collector.has_all_evidence_verified() is False

    def test_has_all_evidence_verified_returns_false_when_empty(self) -> None:
        """Should return False when no evidence has been collected."""
        collector = EvidenceCollector("task-123")

        assert collector.has_all_evidence_verified() is False

    def test_get_evidence_summary_aggregates_correctly(self) -> None:
        """Summary should correctly aggregate evidence counts."""
        collector = EvidenceCollector("task-123")

        collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/tmp/test.txt",
            failures=0,
            errors=0,
            pending=0,
            examples=150,
            duration=45.3,
        )
        collector.add_success_criteria_evidence(
            criterion_id="crit-1",
            criterion_type="file_exists",
            expected=True,
            actual=True,
        )

        summary = collector.get_evidence_summary()

        assert summary["total_evidence_items"] == 2
        assert summary["verified_items"] == 2
        assert summary["failed_items"] == 0
        assert summary["all_verified"] is True

    def test_get_failed_evidence_returns_only_failures(self) -> None:
        """Should return only unverified evidence items."""
        collector = EvidenceCollector("task-123")

        collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/tmp/test.txt",
            failures=0,
            errors=0,
            pending=0,
            examples=150,
            duration=45.3,
        )
        collector.add_test_evidence(
            command="pytest",
            exit_code=1,
            stdout_path="/tmp/test2.txt",
            failures=3,
            errors=0,
            pending=0,
            examples=100,
            duration=30.0,
        )

        failed = collector.get_failed_evidence()

        assert len(failed) == 1
        assert failed[0].verified is False


class TestQualityGatesCoordinator:
    """Tests for QualityGatesCoordinator - quality gate orchestration."""

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

    @pytest.mark.asyncio
    async def test_validate_when_disabled_allows_commit(self) -> None:
        """When disabled, coordinator should allow commits without validation."""
        config = make_quality_gates_config(enabled=False)
        coordinator = QualityGatesCoordinator(config)

        can_commit, result = await coordinator.validate_before_commit(
            task={"id": "test-123"}, changed_files=[]
        )

        assert can_commit is True
        assert result.reason == "Quality gates disabled"

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
    async def test_validate_without_success_criteria(self) -> None:
        """Validation should pass when no success criteria are defined."""
        config = make_quality_gates_config(enabled=True)
        coordinator = QualityGatesCoordinator(config)

        task = {"id": "test-123"}  # No success_criteria

        can_commit, result = await coordinator.validate_before_commit(
            task=task, changed_files=[], claims=[]
        )

        assert can_commit is True

    def test_to_dict_includes_all_fields(self) -> None:
        """QualityGateResult.to_dict should include all result fields."""
        from sugar.quality_gates import QualityGateResult

        result = QualityGateResult(
            can_complete=True,
            reason="All gates passed",
            tests_passed=True,
            criteria_verified=True,
            claims_proven=True,
        )

        result_dict = result.to_dict()

        assert result_dict["can_complete"] is True
        assert result_dict["reason"] == "All gates passed"
        assert result_dict["tests_passed"] is True
        assert result_dict["criteria_verified"] is True
        assert result_dict["claims_proven"] is True
