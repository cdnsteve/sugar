"""
Truth Enforcer - Feature 8: Truth Enforcement

Requires proof for all claims of success.
Blocks task completion if claims lack evidence.
"""

from typing import Any, Dict, List, Optional, Tuple
import logging

from .evidence import Evidence, EvidenceCollector

logger = logging.getLogger(__name__)


class Claim:
    """A claim that requires proof"""

    def __init__(self, claim_text: str, proof_required: str, must_show: Dict[str, Any]):
        self.claim_text = claim_text
        self.proof_required = proof_required
        self.must_show = must_show
        self.has_proof = False
        self.proof_details = {}


class TruthEnforcer:
    """
    Enforces that all claims of success are backed by evidence
    """

    def __init__(self, config: dict):
        """
        Initialize truth enforcer

        Args:
            config: Configuration dictionary
        """
        enforcement_config = config.get("quality_gates", {}).get(
            "truth_enforcement", {}
        )
        self.enabled = enforcement_config.get("enabled", False)
        self.mode = enforcement_config.get("mode", "strict")  # strict | permissive
        self.rules = enforcement_config.get("rules", [])
        self.block_unproven = enforcement_config.get("block_unproven_success", True)

    def is_enabled(self) -> bool:
        """Check if truth enforcement is enabled"""
        return self.enabled

    def verify_claims(
        self, claims: List[str], evidence_collector: EvidenceCollector
    ) -> Tuple[bool, List[Claim]]:
        """
        Verify that all claims have corresponding proof

        Args:
            claims: List of claim strings (e.g., "all tests pass", "functionality verified")
            evidence_collector: Evidence collector with collected evidence

        Returns:
            Tuple of (all_proven, list of claims with proof status)
        """
        if not self.is_enabled():
            return True, []

        verified_claims = []

        for claim_text in claims:
            claim = self._verify_claim(claim_text, evidence_collector)
            verified_claims.append(claim)

        all_proven = all(c.has_proof for c in verified_claims)

        if all_proven:
            logger.info(f"✅ All {len(verified_claims)} claims verified with proof")
        else:
            unproven = [c for c in verified_claims if not c.has_proof]
            logger.warning(
                f"❌ {len(unproven)} claims lack proof: {[c.claim_text for c in unproven]}"
            )

            if self.block_unproven and self.mode == "strict":
                logger.error(
                    "BLOCKING task completion - unproven claims in strict mode"
                )

        return all_proven, verified_claims

    def _verify_claim(
        self, claim_text: str, evidence_collector: EvidenceCollector
    ) -> Claim:
        """
        Verify a single claim has required proof

        Args:
            claim_text: The claim being made
            evidence_collector: Evidence collector

        Returns:
            Claim object with proof status
        """
        # Find matching rule for this claim
        rule = self._find_matching_rule(claim_text)

        if not rule:
            logger.warning(f"No rule found for claim: '{claim_text}'")
            # In permissive mode, allow claims without rules
            if self.mode == "permissive":
                return Claim(
                    claim_text=claim_text,
                    proof_required="none",
                    must_show={},
                )
            else:
                return Claim(
                    claim_text=claim_text,
                    proof_required="unknown",
                    must_show={},
                )

        # Verify proof requirements
        proof_type = rule["proof_required"]
        must_show = rule["must_show"]

        claim_obj = Claim(
            claim_text=claim_text, proof_required=proof_type, must_show=must_show
        )

        # Check evidence for proof
        if proof_type == "test_execution_evidence":
            claim_obj.has_proof = self._verify_test_execution_proof(
                must_show, evidence_collector, claim_obj
            )

        elif proof_type == "functional_verification_evidence":
            claim_obj.has_proof = self._verify_functional_verification_proof(
                must_show, evidence_collector, claim_obj
            )

        elif proof_type == "success_criteria_verification":
            claim_obj.has_proof = self._verify_success_criteria_proof(
                must_show, evidence_collector, claim_obj
            )

        else:
            logger.error(f"Unknown proof type: {proof_type}")
            claim_obj.has_proof = False

        return claim_obj

    def _find_matching_rule(self, claim_text: str) -> Optional[Dict[str, Any]]:
        """Find rule that matches this claim"""
        claim_lower = claim_text.lower()

        for rule in self.rules:
            rule_claim = rule.get("claim", "").lower()
            if rule_claim in claim_lower or claim_lower in rule_claim:
                return rule

        return None

    def _verify_test_execution_proof(
        self, must_show: Dict[str, Any], evidence: EvidenceCollector, claim: Claim
    ) -> bool:
        """Verify test execution proof exists and meets requirements"""
        test_evidence = [
            e for e in evidence.evidence_items if e.type == "test_execution"
        ]

        if not test_evidence:
            logger.warning("No test execution evidence found")
            return False

        # Check the latest test evidence
        latest_test = test_evidence[-1]

        # Verify all "must_show" requirements
        for key, expected_value in must_show.items():
            actual_value = latest_test.data.get(key)

            if actual_value != expected_value:
                logger.warning(
                    f"Test evidence mismatch: {key} = {actual_value}, expected {expected_value}"
                )
                claim.proof_details[key] = {
                    "expected": expected_value,
                    "actual": actual_value,
                }
                return False

        # All requirements met
        claim.proof_details = latest_test.data
        return True

    def _verify_functional_verification_proof(
        self, must_show: Dict[str, Any], evidence: EvidenceCollector, claim: Claim
    ) -> bool:
        """Verify functional verification proof exists"""
        func_evidence = [
            e for e in evidence.evidence_items if e.type == "functional_verification"
        ]

        if not func_evidence:
            logger.warning("No functional verification evidence found")
            return False

        # Check requirements
        for key, expected_value in must_show.items():
            if key == "http_request_results":
                # Check if all HTTP requests succeeded
                all_success = all(
                    e.verified
                    for e in func_evidence
                    if e.data.get("verification_type") == "http_request"
                )
                if not all_success:
                    return False

            elif key == "screenshot_evidence":
                # Check if screenshots exist
                screenshot_evidence = [
                    e for e in evidence.evidence_items if e.type == "screenshot"
                ]
                if not screenshot_evidence:
                    return False

        claim.proof_details = {"functional_verifications": len(func_evidence)}
        return True

    def _verify_success_criteria_proof(
        self, must_show: Dict[str, Any], evidence: EvidenceCollector, claim: Claim
    ) -> bool:
        """Verify success criteria proof exists"""
        criteria_evidence = [
            e for e in evidence.evidence_items if e.type == "success_criteria"
        ]

        if not criteria_evidence:
            logger.warning("No success criteria evidence found")
            return False

        # Check if all criteria verified
        all_verified = must_show.get("all_criteria_verified", True)

        if all_verified:
            if not all(e.verified for e in criteria_evidence):
                failed = [e for e in criteria_evidence if not e.verified]
                logger.warning(f"{len(failed)} success criteria not verified")
                return False

        claim.proof_details = {
            "total_criteria": len(criteria_evidence),
            "verified": sum(1 for e in criteria_evidence if e.verified),
        }
        return True

    def can_complete_task(
        self, claims: List[str], evidence_collector: EvidenceCollector
    ) -> Tuple[bool, str]:
        """
        Determine if task can be completed based on claims and evidence

        Args:
            claims: List of claims being made
            evidence_collector: Evidence collector

        Returns:
            Tuple of (can_complete, reason)
        """
        if not self.is_enabled():
            return True, "Truth enforcement disabled"

        all_proven, verified_claims = self.verify_claims(claims, evidence_collector)

        if all_proven:
            return True, "All claims proven with evidence"

        if self.mode == "permissive":
            unproven = [c for c in verified_claims if not c.has_proof]
            return (
                True,
                f"Permissive mode: allowing {len(unproven)} unproven claims",
            )

        # Strict mode
        if self.block_unproven:
            unproven = [c for c in verified_claims if not c.has_proof]
            return (
                False,
                f"Cannot complete: {len(unproven)} claims lack proof: {[c.claim_text for c in unproven]}",
            )

        return True, "Allowing completion despite unproven claims"

    def get_unproven_claims_report(
        self, claims: List[str], evidence_collector: EvidenceCollector
    ) -> str:
        """
        Generate a report of unproven claims

        Args:
            claims: List of claims
            evidence_collector: Evidence collector

        Returns:
            Markdown report of unproven claims
        """
        _, verified_claims = self.verify_claims(claims, evidence_collector)
        unproven = [c for c in verified_claims if not c.has_proof]

        if not unproven:
            return "✅ All claims verified with proof"

        report = "# Unproven Claims Report\n\n"
        report += f"**Total Claims:** {len(verified_claims)}\n"
        report += f"**Proven:** {len(verified_claims) - len(unproven)}\n"
        report += f"**Unproven:** {len(unproven)}\n\n"

        report += "## Claims Lacking Proof\n\n"
        for claim in unproven:
            report += f'### ❌ "{claim.claim_text}"\n'
            report += f"- **Proof Required:** {claim.proof_required}\n"
            report += f"- **Must Show:** {claim.must_show}\n"
            if claim.proof_details:
                report += f"- **Found:** {claim.proof_details}\n"
            report += "\n"

        return report
