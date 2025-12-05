"""
Evidence Collector - Store and manage verification evidence

Collects and stores proof for all quality gate verifications:
- Test execution results
- Functional verification results
- Success criteria verification
- Screenshots and artifacts
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Evidence:
    """A single piece of evidence."""

    type: str
    data: dict[str, Any]
    verified: bool
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "data": self.data,
            "verified": self.verified,
            "timestamp": self.timestamp,
        }


class EvidenceCollector:
    """
    Collects and manages evidence for task verification
    """

    def __init__(self, task_id: str, evidence_dir: str = ".sugar/evidence"):
        """
        Initialize evidence collector

        Args:
            task_id: Unique task identifier
            evidence_dir: Directory to store evidence
        """
        self.task_id = task_id
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_items: list[Evidence] = []

    def add_test_evidence(
        self,
        command: str,
        exit_code: int,
        stdout_path: str,
        failures: int,
        errors: int,
        pending: int,
        examples: int,
        duration: float,
    ) -> Evidence:
        """
        Add test execution evidence

        Args:
            command: Test command executed
            exit_code: Exit code from test
            stdout_path: Path to stored stdout
            failures: Number of test failures
            errors: Number of test errors
            pending: Number of pending tests
            examples: Total number of examples
            duration: Test duration in seconds

        Returns:
            Evidence object
        """
        verified = exit_code == 0 and failures == 0 and errors == 0

        evidence = Evidence(
            type="test_execution",
            data={
                "command": command,
                "exit_code": exit_code,
                "stdout_path": stdout_path,
                "failures": failures,
                "errors": errors,
                "pending": pending,
                "examples": examples,
                "duration": duration,
            },
            verified=verified,
        )

        self.evidence_items.append(evidence)
        logger.info(
            f"Added test evidence for task {self.task_id}: {'PASSED' if verified else 'FAILED'}"
        )
        return evidence

    def add_functional_verification_evidence(
        self, verification_type: str, details: dict[str, Any], verified: bool
    ) -> Evidence:
        """
        Add functional verification evidence

        Args:
            verification_type: Type of verification (http_request, browser, db_query)
            details: Verification details
            verified: Whether verification passed

        Returns:
            Evidence object
        """
        evidence = Evidence(
            type="functional_verification",
            data={"verification_type": verification_type, **details},
            verified=verified,
        )

        self.evidence_items.append(evidence)
        logger.info(
            f"Added functional verification evidence for task {self.task_id}: "
            f"{verification_type} {'PASSED' if verified else 'FAILED'}"
        )
        return evidence

    def add_success_criteria_evidence(
        self, criterion_id: str, criterion_type: str, expected: Any, actual: Any
    ) -> Evidence:
        """
        Add success criteria verification evidence

        Args:
            criterion_id: Unique identifier for this criterion
            criterion_type: Type of criterion (http_status, test_suite, etc)
            expected: Expected value/outcome
            actual: Actual value/outcome

        Returns:
            Evidence object
        """
        verified = expected == actual

        evidence = Evidence(
            type="success_criteria",
            data={
                "criterion_id": criterion_id,
                "criterion_type": criterion_type,
                "expected": expected,
                "actual": actual,
            },
            verified=verified,
        )

        self.evidence_items.append(evidence)
        logger.info(
            f"Added success criteria evidence for task {self.task_id}: "
            f"{criterion_id} {'PASSED' if verified else 'FAILED'}"
        )
        return evidence

    def add_screenshot_evidence(
        self, url: str, screenshot_path: str, verified: bool
    ) -> Evidence:
        """
        Add screenshot evidence

        Args:
            url: URL that was captured
            screenshot_path: Path to screenshot file
            verified: Whether screenshot shows expected state

        Returns:
            Evidence object
        """
        evidence = Evidence(
            type="screenshot",
            data={"url": url, "screenshot_path": screenshot_path},
            verified=verified,
        )

        self.evidence_items.append(evidence)
        logger.info(
            f"Added screenshot evidence for task {self.task_id}: {screenshot_path}"
        )
        return evidence

    def has_all_evidence_verified(self) -> bool:
        """
        Check if all collected evidence is verified

        Returns:
            True if all evidence passed verification
        """
        if not self.evidence_items:
            return False

        return all(evidence.verified for evidence in self.evidence_items)

    def get_evidence_summary(self) -> dict[str, Any]:
        """
        Get summary of all evidence

        Returns:
            Dictionary with evidence summary
        """
        total = len(self.evidence_items)
        verified = sum(1 for e in self.evidence_items if e.verified)

        evidence_by_type = {}
        for evidence in self.evidence_items:
            if evidence.type not in evidence_by_type:
                evidence_by_type[evidence.type] = {"total": 0, "verified": 0}
            evidence_by_type[evidence.type]["total"] += 1
            if evidence.verified:
                evidence_by_type[evidence.type]["verified"] += 1

        return {
            "total_evidence_items": total,
            "verified_items": verified,
            "failed_items": total - verified,
            "all_verified": self.has_all_evidence_verified(),
            "evidence_by_type": evidence_by_type,
        }

    def save_evidence_report(self) -> str:
        """
        Save evidence report to disk.

        Returns:
            Path to saved report

        Raises:
            OSError: If the report cannot be written to disk
        """
        report_path = self.evidence_dir / f"{self.task_id}_evidence.json"

        report = {
            "task_id": self.task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": self.get_evidence_summary(),
            "evidence": [e.to_dict() for e in self.evidence_items],
        }

        try:
            # Write to temp file first, then rename for atomicity
            temp_path = report_path.with_suffix(".json.tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            temp_path.replace(report_path)
        except OSError as e:
            logger.error(f"Failed to save evidence report {report_path}: {e}")
            raise

        logger.info(f"Saved evidence report: {report_path}")
        return str(report_path)

    def get_failed_evidence(self) -> list[Evidence]:
        """
        Get all evidence items that failed verification

        Returns:
            List of failed evidence items
        """
        return [e for e in self.evidence_items if not e.verified]

    def get_evidence_file_paths(self) -> list[str]:
        """
        Get list of file paths containing evidence.

        Returns:
            List of evidence file paths
        """
        urls = []

        for evidence in self.evidence_items:
            if evidence.type == "test_execution":
                stdout_path = evidence.data.get("stdout_path")
                if stdout_path:
                    urls.append(stdout_path)

            elif evidence.type == "screenshot":
                screenshot_path = evidence.data.get("screenshot_path")
                if screenshot_path:
                    urls.append(screenshot_path)

        # Always include the evidence report
        report_path = str(self.evidence_dir / f"{self.task_id}_evidence.json")
        urls.append(report_path)

        return urls
