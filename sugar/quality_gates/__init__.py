"""
Quality Gates - Verification and Truth Enforcement for Sugar Tasks.

This module provides mandatory verification layers that ensure Sugar's autonomous
development system produces correct, tested, and reliable code. Quality gates
enforce a "trust but verify" approach where all claims must be backed by evidence.

Architecture Overview
---------------------
The quality gates system is built in three phases, each adding verification layers:

**Phase 1 - Core Verification**:
    - ``TestExecutionValidator``: Runs and validates test suites
    - ``SuccessCriteriaVerifier``: Validates task completion against defined criteria
    - ``TruthEnforcer``: Requires proof for all claims (no unverified assertions)
    - ``EvidenceCollector``: Captures and stores verification artifacts
    - ``QualityGatesCoordinator``: Orchestrates all verification components

**Phase 2 - Functional Verification**:
    - ``FunctionalVerifier``: HTTP, browser, and database verification
    - ``PreFlightChecker``: Pre-execution environment validation

**Phase 3 - Advanced Verification**:
    - ``VerificationFailureHandler``: Failure analysis and retry logic
    - ``DiffValidator``: Git diff validation for code changes

Usage Example
-------------
Basic quality gate verification::

    from sugar.quality_gates import (
        QualityGatesCoordinator,
        SuccessCriterion,
        Evidence
    )

    # Initialize the coordinator
    coordinator = QualityGatesCoordinator()

    # Define success criteria for a task
    criteria = [
        SuccessCriterion(
            description="All tests pass",
            verification_method="test_execution"
        )
    ]

    # Run verification
    result = await coordinator.verify_task(task_id="task-123", criteria=criteria)

    if result.passed:
        print("Quality gates passed!")
    else:
        print(f"Failed: {result.failures}")

Key Concepts
------------
- **Evidence**: Proof artifacts (logs, screenshots, test results) backing claims
- **Claims**: Assertions that require verification before acceptance
- **Success Criteria**: Measurable conditions that define task completion
- **Pre-flight Checks**: Environment validation before task execution
- **Functional Verification**: Runtime validation (HTTP responses, UI state, etc.)

See Also
--------
- ``sugar.core.executor``: Task execution that uses quality gates
- ``sugar.core.work_items``: Work item definitions with success criteria
"""

# Phase 1: Core Verification Components
# These provide the foundational verification layer for all Sugar tasks
from .test_validator import TestExecutionValidator, TestExecutionResult
from .success_criteria import SuccessCriteriaVerifier, SuccessCriterion
from .truth_enforcer import TruthEnforcer, Claim
from .evidence import EvidenceCollector, Evidence
from .coordinator import QualityGatesCoordinator, QualityGateResult

# Phase 2: Functional Verification
# Runtime verification for HTTP endpoints, browser state, and databases
from .functional_verifier import FunctionalVerifier, FunctionalVerificationResult
from .preflight_checks import PreFlightChecker, PreFlightCheckResult

# Phase 3: Advanced Verification
# Failure handling, retry logic, and code diff validation
from .failure_handler import VerificationFailureHandler, FailureReport
from .diff_validator import DiffValidator, DiffValidationResult

__all__ = [
    # Phase 1: Core Verification
    "TestExecutionValidator",  # Runs test suites and captures results
    "TestExecutionResult",  # Test run outcome with pass/fail details
    "SuccessCriteriaVerifier",  # Validates task against completion criteria
    "SuccessCriterion",  # Single criterion definition
    "TruthEnforcer",  # Ensures claims have evidence
    "Claim",  # An assertion requiring verification
    "EvidenceCollector",  # Gathers and stores proof artifacts
    "Evidence",  # Single piece of verification evidence
    "QualityGatesCoordinator",  # Orchestrates all verification components
    "QualityGateResult",  # Overall verification outcome
    # Phase 2: Functional Verification
    "FunctionalVerifier",  # HTTP, browser, database verification
    "FunctionalVerificationResult",  # Functional check outcome
    "PreFlightChecker",  # Pre-execution environment validation
    "PreFlightCheckResult",  # Pre-flight check outcome
    # Phase 3: Advanced Verification
    "VerificationFailureHandler",  # Analyzes failures and manages retries
    "FailureReport",  # Detailed failure analysis
    "DiffValidator",  # Validates git diffs for correctness
    "DiffValidationResult",  # Diff validation outcome
]
