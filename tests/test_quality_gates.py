"""
Tests for Quality Gates - Phase 1 Features

Tests mandatory test execution, success criteria verification, and truth enforcement.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from sugar.quality_gates import (
    TestExecutionValidator,
    TestExecutionResult,
    SuccessCriteriaVerifier,
    SuccessCriterion,
    TruthEnforcer,
    EvidenceCollector,
    QualityGatesCoordinator,
)


class TestTestExecutionValidator:
    """Test the test execution validator"""

    def test_init_with_config(self):
        """Test validator initialization with config"""
        config = {
            "quality_gates": {
                "mandatory_testing": {
                    "enabled": True,
                    "block_commits": True,
                }
            }
        }

        validator = TestExecutionValidator(config)

        assert validator.is_enabled() is True
        assert validator.block_commits is True

    def test_init_disabled(self):
        """Test validator when disabled"""
        config = {"quality_gates": {"mandatory_testing": {"enabled": False}}}

        validator = TestExecutionValidator(config)

        assert validator.is_enabled() is False

    @pytest.mark.asyncio
    async def test_validate_tests_disabled(self):
        """Test validation when disabled"""
        config = {"quality_gates": {"mandatory_testing": {"enabled": False}}}
        validator = TestExecutionValidator(config)

        task = {"id": "test-123"}
        can_commit, result, message = await validator.validate_tests_before_commit(
            task, []
        )

        assert can_commit is True
        assert message == "Test validation disabled"

    def test_parse_pytest_output(self):
        """Test parsing pytest output"""
        config = {"quality_gates": {"mandatory_testing": {"enabled": True}}}
        validator = TestExecutionValidator(config)

        output = """
        ============================= test session starts ==============================
        collected 150 items

        tests/test_foo.py::test_bar PASSED
        tests/test_foo.py::test_baz PASSED

        ============================== 148 passed, 2 failed in 5.23s =================
        """

        failures, errors, pending, examples = validator._parse_test_output(output)

        assert failures == 2
        assert examples == 148

    def test_parse_rspec_output(self):
        """Test parsing rspec output"""
        config = {"quality_gates": {"mandatory_testing": {"enabled": True}}}
        validator = TestExecutionValidator(config)

        output = """
        150 examples, 0 failures, 2 pending
        Finished in 45.3 seconds
        """

        failures, errors, pending, examples = validator._parse_test_output(output)

        assert failures == 0
        assert examples == 150
        assert pending == 2


class TestSuccessCriteriaVerifier:
    """Test success criteria verification"""

    @pytest.mark.asyncio
    async def test_verify_file_exists_criterion(self):
        """Test verifying file existence"""
        config = {}
        verifier = SuccessCriteriaVerifier(config)

        # Create a temp file
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            criterion_def = {"type": "file_exists", "file_path": temp_path}

            criterion = await verifier._verify_file_exists(criterion_def)

            assert criterion.verified is True
            assert criterion.actual is True

        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_verify_file_not_exists(self):
        """Test verifying file that doesn't exist"""
        config = {}
        verifier = SuccessCriteriaVerifier(config)

        criterion_def = {"type": "file_exists", "file_path": "/nonexistent/file.txt"}

        criterion = await verifier._verify_file_exists(criterion_def)

        assert criterion.verified is False
        assert criterion.actual is False

    @pytest.mark.asyncio
    async def test_verify_string_in_file(self):
        """Test verifying string exists in file"""
        config = {}
        verifier = SuccessCriteriaVerifier(config)

        # Create a temp file with content
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("Hello World\nTest Content\n")
            temp_path = f.name

        try:
            criterion_def = {
                "type": "string_in_file",
                "file_path": temp_path,
                "search_string": "Test Content",
            }

            criterion = await verifier._verify_string_in_file(criterion_def)

            assert criterion.verified is True
            assert criterion.actual is True

        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_verify_all_criteria_success(self):
        """Test verifying all criteria when all pass"""
        config = {}
        verifier = SuccessCriteriaVerifier(config)

        # Create temp file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("Test")
            temp_path = f.name

        try:
            criteria = [
                {"type": "file_exists", "file_path": temp_path},
                {
                    "type": "string_in_file",
                    "file_path": temp_path,
                    "search_string": "Test",
                },
            ]

            all_verified, verified_criteria = await verifier.verify_all_criteria(
                criteria
            )

            assert all_verified is True
            assert len(verified_criteria) == 2
            assert all(c.verified for c in verified_criteria)

        finally:
            Path(temp_path).unlink()


class TestTruthEnforcer:
    """Test truth enforcement"""

    def test_init_with_config(self):
        """Test enforcer initialization"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "strict",
                    "block_unproven_success": True,
                    "rules": [
                        {
                            "claim": "all tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"exit_code": 0, "failures": 0, "errors": 0},
                        }
                    ],
                }
            }
        }

        enforcer = TruthEnforcer(config)

        assert enforcer.is_enabled() is True
        assert enforcer.mode == "strict"
        assert len(enforcer.rules) == 1

    def test_verify_test_execution_proof(self):
        """Test verifying test execution proof"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "rules": [
                        {
                            "claim": "all tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"exit_code": 0, "failures": 0, "errors": 0},
                        }
                    ],
                }
            }
        }

        enforcer = TruthEnforcer(config)
        evidence_collector = EvidenceCollector("test-123")

        # Add test evidence
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

        # Verify claim
        all_proven, claims = enforcer.verify_claims(
            ["all tests pass"], evidence_collector
        )

        assert all_proven is True
        assert len(claims) == 1
        assert claims[0].has_proof is True

    def test_verify_claim_without_proof(self):
        """Test verifying claim without proof"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "strict",
                    "block_unproven_success": True,
                    "rules": [
                        {
                            "claim": "all tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"exit_code": 0, "failures": 0, "errors": 0},
                        }
                    ],
                }
            }
        }

        enforcer = TruthEnforcer(config)
        evidence_collector = EvidenceCollector("test-123")

        # No evidence added

        # Verify claim
        all_proven, claims = enforcer.verify_claims(
            ["all tests pass"], evidence_collector
        )

        assert all_proven is False
        assert len(claims) == 1
        assert claims[0].has_proof is False

    def test_can_complete_task_strict_mode(self):
        """Test task completion blocking in strict mode"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "strict",
                    "block_unproven_success": True,
                    "rules": [
                        {
                            "claim": "all tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"exit_code": 0},
                        }
                    ],
                }
            }
        }

        enforcer = TruthEnforcer(config)
        evidence_collector = EvidenceCollector("test-123")

        # No evidence

        can_complete, reason = enforcer.can_complete_task(
            ["all tests pass"], evidence_collector
        )

        assert can_complete is False
        assert "lack proof" in reason.lower()


class TestEvidenceCollector:
    """Test evidence collection"""

    def test_init(self):
        """Test evidence collector initialization"""
        collector = EvidenceCollector("task-123")

        assert collector.task_id == "task-123"
        assert len(collector.evidence_items) == 0

    def test_add_test_evidence(self):
        """Test adding test evidence"""
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

    def test_add_failed_test_evidence(self):
        """Test adding failed test evidence"""
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

    def test_has_all_evidence_verified(self):
        """Test checking if all evidence is verified"""
        collector = EvidenceCollector("task-123")

        # Add passing test
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

        # Add success criterion
        collector.add_success_criteria_evidence(
            criterion_id="crit-1",
            criterion_type="file_exists",
            expected=True,
            actual=True,
        )

        assert collector.has_all_evidence_verified() is True

    def test_get_evidence_summary(self):
        """Test getting evidence summary"""
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


class TestQualityGatesCoordinator:
    """Test quality gates coordinator"""

    def test_init(self):
        """Test coordinator initialization"""
        config = {"quality_gates": {"enabled": True}}

        coordinator = QualityGatesCoordinator(config)

        assert coordinator.is_enabled() is True

    @pytest.mark.asyncio
    async def test_validate_disabled(self):
        """Test validation when disabled"""
        config = {"quality_gates": {"enabled": False}}

        coordinator = QualityGatesCoordinator(config)

        can_commit, result = await coordinator.validate_before_commit(
            task={"id": "test-123"}, changed_files=[]
        )

        assert can_commit is True
        assert result.reason == "Quality gates disabled"

    @pytest.mark.asyncio
    async def test_validate_with_success_criteria(self):
        """Test validation with success criteria"""
        config = {"quality_gates": {"enabled": True}}

        coordinator = QualityGatesCoordinator(config)

        # Create temp file for criterion
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("Test")
            temp_path = f.name

        try:
            task = {
                "id": "test-123",
                "success_criteria": [
                    {"type": "file_exists", "file_path": temp_path},
                ],
            }

            can_commit, result = await coordinator.validate_before_commit(
                task=task, changed_files=[], claims=[]
            )

            assert can_commit is True
            assert result.criteria_verified is True

        finally:
            Path(temp_path).unlink()
