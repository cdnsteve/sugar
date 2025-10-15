"""
Quality Gates - Verification and Truth Enforcement

This module provides mandatory verification layers for Sugar tasks:
- Test execution verification
- Success criteria validation
- Truth enforcement (proof required for claims)
- Evidence collection and storage
"""

from .test_validator import TestExecutionValidator, TestExecutionResult
from .success_criteria import SuccessCriteriaVerifier, SuccessCriterion
from .truth_enforcer import TruthEnforcer
from .evidence import EvidenceCollector, Evidence
from .coordinator import QualityGatesCoordinator, QualityGateResult

__all__ = [
    "TestExecutionValidator",
    "TestExecutionResult",
    "SuccessCriteriaVerifier",
    "SuccessCriterion",
    "TruthEnforcer",
    "EvidenceCollector",
    "Evidence",
    "QualityGatesCoordinator",
    "QualityGateResult",
]
