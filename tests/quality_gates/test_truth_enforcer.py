"""
Tests for TruthEnforcer - Feature 8: Truth Enforcement

Tests verification of claims with evidence, blocking behavior, and report generation.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from sugar.quality_gates.truth_enforcer import TruthEnforcer, Claim
from sugar.quality_gates.evidence import Evidence, EvidenceCollector


class TestClaim:
    """Tests for the Claim class"""

    def test_claim_initialization(self):
        """Test Claim initializes with correct attributes"""
        claim = Claim(
            claim_text="all tests pass",
            proof_required="test_execution_evidence",
            must_show={"failures": 0, "errors": 0},
        )

        assert claim.claim_text == "all tests pass"
        assert claim.proof_required == "test_execution_evidence"
        assert claim.must_show == {"failures": 0, "errors": 0}
        assert claim.has_proof is False
        assert claim.proof_details == {}

    def test_claim_proof_can_be_set(self):
        """Test that claim proof status can be updated"""
        claim = Claim(
            claim_text="tests pass",
            proof_required="test_execution_evidence",
            must_show={},
        )

        claim.has_proof = True
        claim.proof_details = {"exit_code": 0, "failures": 0}

        assert claim.has_proof is True
        assert claim.proof_details == {"exit_code": 0, "failures": 0}


class TestTruthEnforcerInit:
    """Tests for TruthEnforcer initialization"""

    def test_init_with_full_config(self):
        """Test initialization with complete configuration"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "strict",
                    "block_unproven_success": True,
                    "rules": [
                        {
                            "claim": "tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0},
                        }
                    ],
                }
            }
        }

        enforcer = TruthEnforcer(config)

        assert enforcer.enabled is True
        assert enforcer.mode == "strict"
        assert enforcer.block_unproven is True
        assert len(enforcer.rules) == 1

    def test_init_with_empty_config(self):
        """Test initialization with empty configuration uses defaults"""
        config = {}

        enforcer = TruthEnforcer(config)

        assert enforcer.enabled is False
        assert enforcer.mode == "strict"
        assert enforcer.block_unproven is True
        assert enforcer.rules == []

    def test_init_with_partial_config(self):
        """Test initialization with partial configuration"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "permissive",
                }
            }
        }

        enforcer = TruthEnforcer(config)

        assert enforcer.enabled is True
        assert enforcer.mode == "permissive"
        assert enforcer.block_unproven is True  # default
        assert enforcer.rules == []  # default

    def test_init_with_missing_quality_gates(self):
        """Test initialization when quality_gates key is missing"""
        config = {"other_config": {}}

        enforcer = TruthEnforcer(config)

        assert enforcer.enabled is False
        assert enforcer.mode == "strict"


class TestTruthEnforcerIsEnabled:
    """Tests for is_enabled method"""

    def test_is_enabled_when_true(self):
        """Test is_enabled returns True when enabled"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        assert enforcer.is_enabled() is True

    def test_is_enabled_when_false(self):
        """Test is_enabled returns False when disabled"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": False}}}
        enforcer = TruthEnforcer(config)

        assert enforcer.is_enabled() is False


class TestFindMatchingRule:
    """Tests for _find_matching_rule method"""

    def test_find_matching_rule_exact_match(self):
        """Test finding rule with exact claim match"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "rules": [
                        {
                            "claim": "all tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0},
                        }
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        rule = enforcer._find_matching_rule("all tests pass")

        assert rule is not None
        assert rule["claim"] == "all tests pass"

    def test_find_matching_rule_partial_match(self):
        """Test finding rule with partial claim match"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "rules": [
                        {
                            "claim": "tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {},
                        }
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        rule = enforcer._find_matching_rule("all tests pass successfully")

        assert rule is not None
        assert rule["claim"] == "tests pass"

    def test_find_matching_rule_case_insensitive(self):
        """Test rule matching is case insensitive"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "rules": [
                        {
                            "claim": "Tests Pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {},
                        }
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        rule = enforcer._find_matching_rule("TESTS PASS")

        assert rule is not None

    def test_find_matching_rule_no_match(self):
        """Test returns None when no rule matches"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "rules": [
                        {
                            "claim": "tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {},
                        }
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        rule = enforcer._find_matching_rule("functionality verified")

        assert rule is None

    def test_find_matching_rule_empty_rules(self):
        """Test returns None when rules list is empty"""
        config = {
            "quality_gates": {"truth_enforcement": {"enabled": True, "rules": []}}
        }
        enforcer = TruthEnforcer(config)

        rule = enforcer._find_matching_rule("tests pass")

        assert rule is None


class TestVerifyTestExecutionProof:
    """Tests for _verify_test_execution_proof method"""

    def test_verify_test_execution_proof_success(self):
        """Test verification succeeds with matching evidence"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/path/to/stdout",
            failures=0,
            errors=0,
            pending=0,
            examples=10,
            duration=5.0,
        )

        must_show = {"failures": 0, "errors": 0}
        claim = Claim("tests pass", "test_execution_evidence", must_show)

        result = enforcer._verify_test_execution_proof(
            must_show, evidence_collector, claim
        )

        assert result is True
        assert claim.proof_details.get("failures") == 0
        assert claim.proof_details.get("errors") == 0

    def test_verify_test_execution_proof_failure_mismatch(self):
        """Test verification fails when evidence doesn't match requirements"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=1,
            stdout_path="/path/to/stdout",
            failures=2,
            errors=0,
            pending=0,
            examples=10,
            duration=5.0,
        )

        must_show = {"failures": 0}
        claim = Claim("tests pass", "test_execution_evidence", must_show)

        result = enforcer._verify_test_execution_proof(
            must_show, evidence_collector, claim
        )

        assert result is False
        assert "failures" in claim.proof_details
        assert claim.proof_details["failures"]["expected"] == 0
        assert claim.proof_details["failures"]["actual"] == 2

    def test_verify_test_execution_proof_no_evidence(self):
        """Test verification fails when no test evidence exists"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        # No evidence added

        must_show = {"failures": 0}
        claim = Claim("tests pass", "test_execution_evidence", must_show)

        result = enforcer._verify_test_execution_proof(
            must_show, evidence_collector, claim
        )

        assert result is False

    def test_verify_test_execution_proof_uses_latest(self):
        """Test verification uses the latest test evidence"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        # Add first evidence with failures
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=1,
            stdout_path="/path/to/stdout1",
            failures=3,
            errors=0,
            pending=0,
            examples=10,
            duration=5.0,
        )
        # Add second evidence without failures (should be used)
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/path/to/stdout2",
            failures=0,
            errors=0,
            pending=0,
            examples=10,
            duration=5.0,
        )

        must_show = {"failures": 0}
        claim = Claim("tests pass", "test_execution_evidence", must_show)

        result = enforcer._verify_test_execution_proof(
            must_show, evidence_collector, claim
        )

        assert result is True


class TestVerifyFunctionalVerificationProof:
    """Tests for _verify_functional_verification_proof method"""

    def test_verify_functional_proof_success(self):
        """Test verification succeeds with verified functional evidence"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_functional_verification_evidence(
            verification_type="http_request",
            details={"url": "http://example.com", "status_code": 200},
            verified=True,
        )

        must_show = {"http_request_results": True}
        claim = Claim(
            "functionality verified", "functional_verification_evidence", must_show
        )

        result = enforcer._verify_functional_verification_proof(
            must_show, evidence_collector, claim
        )

        assert result is True
        assert claim.proof_details.get("functional_verifications") == 1

    def test_verify_functional_proof_http_failure(self):
        """Test verification fails when HTTP requests fail"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_functional_verification_evidence(
            verification_type="http_request",
            details={"url": "http://example.com", "status_code": 500},
            verified=False,
        )

        must_show = {"http_request_results": True}
        claim = Claim(
            "functionality verified", "functional_verification_evidence", must_show
        )

        result = enforcer._verify_functional_verification_proof(
            must_show, evidence_collector, claim
        )

        assert result is False

    def test_verify_functional_proof_screenshot_required(self):
        """Test verification requires screenshot when specified"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_functional_verification_evidence(
            verification_type="browser",
            details={"action": "click button"},
            verified=True,
        )
        evidence_collector.add_screenshot_evidence(
            url="http://example.com",
            screenshot_path="/path/to/screenshot.png",
            verified=True,
        )

        must_show = {"screenshot_evidence": True}
        claim = Claim(
            "functionality verified", "functional_verification_evidence", must_show
        )

        result = enforcer._verify_functional_verification_proof(
            must_show, evidence_collector, claim
        )

        assert result is True

    def test_verify_functional_proof_missing_screenshot(self):
        """Test verification fails when screenshot required but missing"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_functional_verification_evidence(
            verification_type="browser",
            details={"action": "click button"},
            verified=True,
        )
        # No screenshot added

        must_show = {"screenshot_evidence": True}
        claim = Claim(
            "functionality verified", "functional_verification_evidence", must_show
        )

        result = enforcer._verify_functional_verification_proof(
            must_show, evidence_collector, claim
        )

        assert result is False

    def test_verify_functional_proof_no_evidence(self):
        """Test verification fails when no functional evidence exists"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        # No evidence added

        must_show = {}
        claim = Claim(
            "functionality verified", "functional_verification_evidence", must_show
        )

        result = enforcer._verify_functional_verification_proof(
            must_show, evidence_collector, claim
        )

        assert result is False


class TestVerifySuccessCriteriaProof:
    """Tests for _verify_success_criteria_proof method"""

    def test_verify_success_criteria_success(self):
        """Test verification succeeds when all criteria verified"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_success_criteria_evidence(
            criterion_id="crit-1",
            criterion_type="http_status",
            expected=200,
            actual=200,
        )
        evidence_collector.add_success_criteria_evidence(
            criterion_id="crit-2",
            criterion_type="test_suite",
            expected="pass",
            actual="pass",
        )

        must_show = {"all_criteria_verified": True}
        claim = Claim(
            "success criteria met", "success_criteria_verification", must_show
        )

        result = enforcer._verify_success_criteria_proof(
            must_show, evidence_collector, claim
        )

        assert result is True
        assert claim.proof_details.get("total_criteria") == 2
        assert claim.proof_details.get("verified") == 2

    def test_verify_success_criteria_partial_failure(self):
        """Test verification fails when some criteria not verified"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_success_criteria_evidence(
            criterion_id="crit-1",
            criterion_type="http_status",
            expected=200,
            actual=200,
        )
        evidence_collector.add_success_criteria_evidence(
            criterion_id="crit-2",
            criterion_type="test_suite",
            expected="pass",
            actual="fail",  # This one fails
        )

        must_show = {"all_criteria_verified": True}
        claim = Claim(
            "success criteria met", "success_criteria_verification", must_show
        )

        result = enforcer._verify_success_criteria_proof(
            must_show, evidence_collector, claim
        )

        assert result is False

    def test_verify_success_criteria_no_evidence(self):
        """Test verification fails when no criteria evidence exists"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        # No evidence added

        must_show = {"all_criteria_verified": True}
        claim = Claim(
            "success criteria met", "success_criteria_verification", must_show
        )

        result = enforcer._verify_success_criteria_proof(
            must_show, evidence_collector, claim
        )

        assert result is False


class TestVerifyClaims:
    """Tests for verify_claims method"""

    def test_verify_claims_disabled(self):
        """Test verify_claims returns success when disabled"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": False}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        claims = ["tests pass", "functionality verified"]

        all_proven, verified_claims = enforcer.verify_claims(claims, evidence_collector)

        assert all_proven is True
        assert verified_claims == []

    def test_verify_claims_all_proven(self):
        """Test verify_claims when all claims have proof"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "strict",
                    "rules": [
                        {
                            "claim": "tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0},
                        }
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/path/to/stdout",
            failures=0,
            errors=0,
            pending=0,
            examples=10,
            duration=5.0,
        )

        claims = ["tests pass"]

        all_proven, verified_claims = enforcer.verify_claims(claims, evidence_collector)

        assert all_proven is True
        assert len(verified_claims) == 1
        assert verified_claims[0].has_proof is True

    def test_verify_claims_some_unproven(self):
        """Test verify_claims when some claims lack proof"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "strict",
                    "rules": [
                        {
                            "claim": "tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0},
                        }
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=1,
            stdout_path="/path/to/stdout",
            failures=2,  # Fails requirement
            errors=0,
            pending=0,
            examples=10,
            duration=5.0,
        )

        claims = ["tests pass"]

        all_proven, verified_claims = enforcer.verify_claims(claims, evidence_collector)

        assert all_proven is False
        assert len(verified_claims) == 1
        assert verified_claims[0].has_proof is False

    def test_verify_claims_no_matching_rule_strict(self):
        """Test claims without matching rules in strict mode"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "strict",
                    "rules": [],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        claims = ["unknown claim"]

        all_proven, verified_claims = enforcer.verify_claims(claims, evidence_collector)

        assert all_proven is False
        assert verified_claims[0].proof_required == "unknown"
        assert verified_claims[0].has_proof is False

    def test_verify_claims_no_matching_rule_permissive(self):
        """Test claims without matching rules in permissive mode"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "permissive",
                    "rules": [],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        claims = ["unknown claim"]

        all_proven, verified_claims = enforcer.verify_claims(claims, evidence_collector)

        # In permissive mode, claims without rules are considered proven
        # because the claim object doesn't get proof set but has_proof stays False
        assert verified_claims[0].proof_required == "none"


class TestVerifyClaimSingleClaim:
    """Tests for _verify_claim method"""

    def test_verify_claim_unknown_proof_type(self):
        """Test _verify_claim handles unknown proof types"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "rules": [
                        {
                            "claim": "custom claim",
                            "proof_required": "unknown_proof_type",
                            "must_show": {},
                        }
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")

        claim = enforcer._verify_claim("custom claim", evidence_collector)

        assert claim.has_proof is False
        assert claim.proof_required == "unknown_proof_type"


class TestCanCompleteTask:
    """Tests for can_complete_task method"""

    def test_can_complete_when_disabled(self):
        """Test task can complete when enforcement disabled"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": False}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        claims = ["tests pass", "functionality verified"]

        can_complete, reason = enforcer.can_complete_task(claims, evidence_collector)

        assert can_complete is True
        assert "disabled" in reason.lower()

    def test_can_complete_all_proven(self):
        """Test task can complete when all claims proven"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "strict",
                    "rules": [
                        {
                            "claim": "tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0},
                        }
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/path/to/stdout",
            failures=0,
            errors=0,
            pending=0,
            examples=10,
            duration=5.0,
        )

        claims = ["tests pass"]

        can_complete, reason = enforcer.can_complete_task(claims, evidence_collector)

        assert can_complete is True
        assert "proven" in reason.lower()

    def test_cannot_complete_strict_unproven(self):
        """Test task cannot complete in strict mode with unproven claims"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "strict",
                    "block_unproven_success": True,
                    "rules": [
                        {
                            "claim": "tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0},
                        }
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=1,
            stdout_path="/path/to/stdout",
            failures=2,
            errors=0,
            pending=0,
            examples=10,
            duration=5.0,
        )

        claims = ["tests pass"]

        can_complete, reason = enforcer.can_complete_task(claims, evidence_collector)

        assert can_complete is False
        assert "lack proof" in reason.lower()

    def test_can_complete_permissive_unproven(self):
        """Test task can complete in permissive mode with unproven claims"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "permissive",
                    "rules": [
                        {
                            "claim": "tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0},
                        }
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=1,
            stdout_path="/path/to/stdout",
            failures=2,
            errors=0,
            pending=0,
            examples=10,
            duration=5.0,
        )

        claims = ["tests pass"]

        can_complete, reason = enforcer.can_complete_task(claims, evidence_collector)

        assert can_complete is True
        assert "permissive" in reason.lower()

    def test_can_complete_strict_but_not_blocking(self):
        """Test task can complete in strict mode when block_unproven is False"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "strict",
                    "block_unproven_success": False,
                    "rules": [
                        {
                            "claim": "tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0},
                        }
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=1,
            stdout_path="/path/to/stdout",
            failures=2,
            errors=0,
            pending=0,
            examples=10,
            duration=5.0,
        )

        claims = ["tests pass"]

        can_complete, reason = enforcer.can_complete_task(claims, evidence_collector)

        assert can_complete is True
        assert "allowing" in reason.lower()


class TestGetUnprovenClaimsReport:
    """Tests for get_unproven_claims_report method"""

    def test_report_all_proven(self):
        """Test report when all claims are proven"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "rules": [
                        {
                            "claim": "tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0},
                        }
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/path/to/stdout",
            failures=0,
            errors=0,
            pending=0,
            examples=10,
            duration=5.0,
        )

        claims = ["tests pass"]

        report = enforcer.get_unproven_claims_report(claims, evidence_collector)

        assert "✅ All claims verified" in report

    def test_report_unproven_claims(self):
        """Test report contains details of unproven claims"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "rules": [
                        {
                            "claim": "tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0},
                        }
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=1,
            stdout_path="/path/to/stdout",
            failures=2,
            errors=0,
            pending=0,
            examples=10,
            duration=5.0,
        )

        claims = ["tests pass"]

        report = enforcer.get_unproven_claims_report(claims, evidence_collector)

        assert "Unproven Claims Report" in report
        assert "tests pass" in report
        assert "test_execution_evidence" in report
        assert "failures" in report

    def test_report_multiple_claims(self):
        """Test report with multiple claims some proven some not"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "rules": [
                        {
                            "claim": "tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0},
                        },
                        {
                            "claim": "functionality verified",
                            "proof_required": "functional_verification_evidence",
                            "must_show": {},
                        },
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        # Add passing test evidence
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/path/to/stdout",
            failures=0,
            errors=0,
            pending=0,
            examples=10,
            duration=5.0,
        )
        # No functional verification evidence added

        claims = ["tests pass", "functionality verified"]

        report = enforcer.get_unproven_claims_report(claims, evidence_collector)

        assert "Total Claims:** 2" in report
        assert "Proven:** 1" in report
        assert "Unproven:** 1" in report
        assert "functionality verified" in report


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_verify_claims_empty_claims_list(self):
        """Test verify_claims with an empty claims list"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "strict",
                    "rules": [
                        {
                            "claim": "tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0},
                        }
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        claims = []

        all_proven, verified_claims = enforcer.verify_claims(claims, evidence_collector)

        assert all_proven is True  # No claims means all (zero) are proven
        assert verified_claims == []

    def test_verify_test_execution_proof_empty_must_show(self):
        """Test verification with empty must_show requirements passes"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=1,  # Even with failure, should pass if no requirements
            stdout_path="/path/to/stdout",
            failures=5,
            errors=3,
            pending=0,
            examples=10,
            duration=5.0,
        )

        must_show = {}  # Empty requirements
        claim = Claim("tests run", "test_execution_evidence", must_show)

        result = enforcer._verify_test_execution_proof(
            must_show, evidence_collector, claim
        )

        assert result is True  # No requirements means success

    def test_verify_success_criteria_all_criteria_verified_false(self):
        """Test verification when all_criteria_verified is False in must_show"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        # Add mixed verified/unverified criteria
        evidence_collector.add_success_criteria_evidence(
            criterion_id="crit-1",
            criterion_type="http_status",
            expected=200,
            actual=200,
        )
        evidence_collector.add_success_criteria_evidence(
            criterion_id="crit-2",
            criterion_type="test_suite",
            expected="pass",
            actual="fail",  # This one fails
        )

        must_show = {"all_criteria_verified": False}  # Don't require all to pass
        claim = Claim("some criteria met", "success_criteria_verification", must_show)

        result = enforcer._verify_success_criteria_proof(
            must_show, evidence_collector, claim
        )

        assert result is True  # Should pass since we don't require all

    def test_multiple_rules_first_match_wins(self):
        """Test that first matching rule is used when multiple could match"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "rules": [
                        {
                            "claim": "all tests",  # Broader match
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0},
                        },
                        {
                            "claim": "all tests pass",  # More specific
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0, "errors": 0},
                        },
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        rule = enforcer._find_matching_rule("all tests pass successfully")

        # First matching rule should win
        assert rule["claim"] == "all tests"
        assert rule["must_show"] == {"failures": 0}

    def test_verify_functional_proof_unknown_must_show_key_ignored(self):
        """Test that unknown must_show keys are safely ignored"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_functional_verification_evidence(
            verification_type="http_request",
            details={"url": "http://example.com", "status_code": 200},
            verified=True,
        )

        must_show = {"unknown_key": True}  # Unknown key
        claim = Claim(
            "functionality verified", "functional_verification_evidence", must_show
        )

        result = enforcer._verify_functional_verification_proof(
            must_show, evidence_collector, claim
        )

        # Should pass because unknown keys are ignored (loop doesn't match)
        assert result is True

    def test_get_unproven_claims_report_when_disabled(self):
        """Test report when enforcement is disabled"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": False}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        claims = ["tests pass", "functionality verified"]

        report = enforcer.get_unproven_claims_report(claims, evidence_collector)

        # When disabled, verify_claims returns empty list, so all proven
        assert "✅ All claims verified" in report

    def test_can_complete_task_empty_claims(self):
        """Test can_complete_task with empty claims list"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "strict",
                    "block_unproven_success": True,
                }
            }
        }
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        claims = []

        can_complete, reason = enforcer.can_complete_task(claims, evidence_collector)

        assert can_complete is True
        assert "proven" in reason.lower()

    def test_verify_functional_proof_http_request_not_required(self):
        """Test functional verification without http_request_results requirement"""
        config = {"quality_gates": {"truth_enforcement": {"enabled": True}}}
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")
        evidence_collector.add_functional_verification_evidence(
            verification_type="browser",
            details={"action": "click button"},
            verified=True,
        )

        must_show = {}  # No specific requirements
        claim = Claim(
            "functionality verified", "functional_verification_evidence", must_show
        )

        result = enforcer._verify_functional_verification_proof(
            must_show, evidence_collector, claim
        )

        assert result is True
        assert claim.proof_details.get("functional_verifications") == 1

    def test_claim_with_special_characters(self):
        """Test claim text with special characters is handled correctly"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "rules": [
                        {
                            "claim": "tests pass (100%)",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0},
                        }
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        rule = enforcer._find_matching_rule("tests pass (100%)")

        assert rule is not None
        assert rule["claim"] == "tests pass (100%)"


class TestIntegration:
    """Integration tests for TruthEnforcer"""

    def test_full_workflow_success(self):
        """Test complete workflow with all claims proven"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "strict",
                    "block_unproven_success": True,
                    "rules": [
                        {
                            "claim": "tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0, "errors": 0},
                        },
                        {
                            "claim": "functionality verified",
                            "proof_required": "functional_verification_evidence",
                            "must_show": {"http_request_results": True},
                        },
                        {
                            "claim": "success criteria met",
                            "proof_required": "success_criteria_verification",
                            "must_show": {"all_criteria_verified": True},
                        },
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")

        # Add all evidence
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=0,
            stdout_path="/path/to/stdout",
            failures=0,
            errors=0,
            pending=0,
            examples=10,
            duration=5.0,
        )

        evidence_collector.add_functional_verification_evidence(
            verification_type="http_request",
            details={"url": "http://example.com", "status_code": 200},
            verified=True,
        )

        evidence_collector.add_success_criteria_evidence(
            criterion_id="crit-1",
            criterion_type="http_status",
            expected=200,
            actual=200,
        )

        claims = ["tests pass", "functionality verified", "success criteria met"]

        # Verify claims
        all_proven, verified_claims = enforcer.verify_claims(claims, evidence_collector)
        assert all_proven is True

        # Check can complete
        can_complete, reason = enforcer.can_complete_task(claims, evidence_collector)
        assert can_complete is True

        # Check report
        report = enforcer.get_unproven_claims_report(claims, evidence_collector)
        assert "✅ All claims verified" in report

    def test_full_workflow_blocking_failure(self):
        """Test complete workflow where task is blocked"""
        config = {
            "quality_gates": {
                "truth_enforcement": {
                    "enabled": True,
                    "mode": "strict",
                    "block_unproven_success": True,
                    "rules": [
                        {
                            "claim": "tests pass",
                            "proof_required": "test_execution_evidence",
                            "must_show": {"failures": 0, "errors": 0},
                        },
                    ],
                }
            }
        }
        enforcer = TruthEnforcer(config)

        evidence_collector = EvidenceCollector(task_id="test-task")

        # Add failing test evidence
        evidence_collector.add_test_evidence(
            command="pytest",
            exit_code=1,
            stdout_path="/path/to/stdout",
            failures=3,
            errors=1,
            pending=0,
            examples=10,
            duration=5.0,
        )

        claims = ["tests pass"]

        # Verify claims fail
        all_proven, verified_claims = enforcer.verify_claims(claims, evidence_collector)
        assert all_proven is False

        # Check cannot complete
        can_complete, reason = enforcer.can_complete_task(claims, evidence_collector)
        assert can_complete is False
        assert "lack proof" in reason.lower()

        # Check report shows failure
        report = enforcer.get_unproven_claims_report(claims, evidence_collector)
        assert "Unproven Claims Report" in report
        assert "tests pass" in report
