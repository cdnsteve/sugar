"""
Verification Failure Handler - Feature 7: Failure Handling & Retry Logic

Handles verification failures with:
- Retry logic for flaky tests
- Escalation paths
- Detailed failure reports
- Enhanced debugging
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class FailureReport:
    """Detailed failure report"""

    def __init__(self, task_id: str, failure_type: str, reason: str):
        self.task_id = task_id
        self.failure_type = failure_type
        self.reason = reason
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.evidence = []
        self.retry_attempts = 0
        self.escalated = False

    def add_evidence(self, evidence_type: str, data: Dict[str, Any]):
        """Add evidence to report"""
        self.evidence.append(
            {
                "type": evidence_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "failure_type": self.failure_type,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "evidence": self.evidence,
            "retry_attempts": self.retry_attempts,
            "escalated": self.escalated,
        }

    def to_markdown(self) -> str:
        """Generate markdown report"""
        report = f"# Failure Report: {self.task_id}\n\n"
        report += f"**Type:** {self.failure_type}\n"
        report += f"**Timestamp:** {self.timestamp}\n"
        report += f"**Retry Attempts:** {self.retry_attempts}\n"
        report += f"**Escalated:** {'Yes' if self.escalated else 'No'}\n\n"

        report += f"## Failure Reason\n\n{self.reason}\n\n"

        if self.evidence:
            report += "## Evidence\n\n"
            for item in self.evidence:
                report += f"### {item['type']}\n"
                report += f"*Timestamp: {item['timestamp']}*\n\n"
                report += "```json\n"
                report += json.dumps(item["data"], indent=2)
                report += "\n```\n\n"

        return report


class VerificationFailureHandler:
    """
    Handles verification failures with retry and escalation logic
    """

    def __init__(self, config: dict):
        """
        Initialize failure handler

        Args:
            config: Configuration dictionary
        """
        handler_config = config.get("verification_failure_handling", {})
        self.enabled = handler_config.get("enabled", False)

        # Test failure handling
        self.test_failure_config = handler_config.get("on_test_failure", {})
        self.test_max_retries = self.test_failure_config.get("max_retries", 2)
        self.test_retry_with_context = self.test_failure_config.get(
            "retry_with_more_context", True
        )

        # Functional verification failure handling
        self.functional_failure_config = handler_config.get(
            "on_functional_verification_failure", {}
        )
        self.functional_max_retries = self.functional_failure_config.get(
            "max_retries", 1
        )

        # Success criteria failure handling
        self.criteria_failure_config = handler_config.get(
            "on_success_criteria_not_met", {}
        )

        # Escalation config
        self.escalate_config = self.test_failure_config.get("escalate", {})
        self.report_path_template = self.escalate_config.get(
            "report_path", ".sugar/failures/{task_id}.md"
        )

    def is_enabled(self) -> bool:
        """Check if failure handling is enabled"""
        return self.enabled

    async def handle_test_failure(
        self,
        task_id: str,
        test_result: Any,
        retry_count: int,
    ) -> tuple[bool, Optional[FailureReport]]:
        """
        Handle test execution failure

        Args:
            task_id: Task ID
            test_result: Test execution result
            retry_count: Number of retries already attempted

        Returns:
            Tuple of (should_retry, failure_report)
        """
        if not self.is_enabled():
            return False, None

        # Check if we should retry
        should_retry = retry_count < self.test_max_retries

        if should_retry:
            logger.info(
                f"♻️ Test failure - will retry (attempt {retry_count + 1}/{self.test_max_retries})"
            )
            return True, None

        # Retries exhausted - create failure report
        logger.error(
            f"❌ Test failures persist after {retry_count} retries - escalating"
        )

        report = FailureReport(
            task_id=task_id,
            failure_type="test_execution",
            reason=f"Tests failed with {getattr(test_result, 'failures', 0)} failures and {getattr(test_result, 'errors', 0)} errors",
        )
        report.retry_attempts = retry_count

        # Add test evidence
        if hasattr(test_result, "to_dict"):
            report.add_evidence("test_result", test_result.to_dict())

        # Escalate
        await self._escalate_failure(report)

        return False, report

    async def handle_functional_verification_failure(
        self,
        task_id: str,
        verification_results: List[Any],
        retry_count: int,
    ) -> tuple[bool, Optional[FailureReport]]:
        """
        Handle functional verification failure

        Args:
            task_id: Task ID
            verification_results: List of verification results
            retry_count: Number of retries already attempted

        Returns:
            Tuple of (should_retry, failure_report)
        """
        if not self.is_enabled():
            return False, None

        # Check if we should retry
        should_retry = retry_count < self.functional_max_retries

        if should_retry:
            logger.info(
                f"♻️ Functional verification failed - will retry (attempt {retry_count + 1}/{self.functional_max_retries})"
            )
            return True, None

        # Retries exhausted - create failure report
        failed_verifications = [r for r in verification_results if not r.verified]
        logger.error(
            f"❌ {len(failed_verifications)} functional verifications failed - escalating"
        )

        report = FailureReport(
            task_id=task_id,
            failure_type="functional_verification",
            reason=f"{len(failed_verifications)} functional verifications did not pass",
        )
        report.retry_attempts = retry_count

        # Add verification evidence
        for result in failed_verifications:
            if hasattr(result, "to_dict"):
                report.add_evidence("failed_verification", result.to_dict())

        # Escalate
        await self._escalate_failure(report)

        return False, report

    async def handle_success_criteria_failure(
        self,
        task_id: str,
        criteria_results: List[Any],
    ) -> Optional[FailureReport]:
        """
        Handle success criteria not being met

        Args:
            task_id: Task ID
            criteria_results: List of criterion results

        Returns:
            Optional failure report
        """
        if not self.is_enabled():
            return None

        action = self.criteria_failure_config.get("action", "fail_task")

        if action == "fail_task":
            failed_criteria = [c for c in criteria_results if not c.verified]
            logger.error(
                f"❌ {len(failed_criteria)} success criteria not met - failing task"
            )

            report = FailureReport(
                task_id=task_id,
                failure_type="success_criteria",
                reason=f"{len(failed_criteria)} success criteria were not met",
            )

            # Add criteria evidence
            for criterion in failed_criteria:
                if hasattr(criterion, "to_dict"):
                    report.add_evidence("failed_criterion", criterion.to_dict())

            # Create failure report
            if self.criteria_failure_config.get("create_failure_report", True):
                await self._escalate_failure(report)

            return report

        return None

    async def _escalate_failure(self, report: FailureReport):
        """
        Escalate failure by creating detailed report

        Args:
            report: Failure report
        """
        if not self.escalate_config.get("enabled", True):
            return

        action = self.escalate_config.get("action", "create_detailed_failure_report")

        if action == "create_detailed_failure_report":
            # Save report to disk
            report_path = Path(self.report_path_template.format(task_id=report.task_id))
            report_path.parent.mkdir(parents=True, exist_ok=True)

            # Save as JSON
            json_path = report_path.with_suffix(".json")
            with open(json_path, "w") as f:
                json.dump(report.to_dict(), f, indent=2)

            # Save as Markdown
            md_path = report_path.with_suffix(".md")
            with open(md_path, "w") as f:
                f.write(report.to_markdown())

            logger.info(f"📄 Failure report saved: {md_path}")
            report.escalated = True

        elif action == "mark_task_as_needs_manual_review":
            logger.warning(f"⚠️ Task {report.task_id} marked as needs manual review")
            report.escalated = True

    def get_retry_count_for_failure_type(self, failure_type: str) -> int:
        """
        Get max retry count for a failure type

        Args:
            failure_type: Type of failure

        Returns:
            Max retry count
        """
        if failure_type == "test_execution":
            return self.test_max_retries
        elif failure_type == "functional_verification":
            return self.functional_max_retries
        else:
            return 0

    def should_collect_enhanced_debugging(self, failure_type: str) -> bool:
        """
        Check if enhanced debugging should be collected

        Args:
            failure_type: Type of failure

        Returns:
            True if enhanced debugging should be collected
        """
        if failure_type == "functional_verification":
            return bool(self.functional_failure_config.get("enhanced_debugging", []))
        return False

    def get_enhanced_debugging_actions(self, failure_type: str) -> List[str]:
        """
        Get enhanced debugging actions for failure type

        Args:
            failure_type: Type of failure

        Returns:
            List of debugging actions
        """
        if failure_type == "functional_verification":
            return self.functional_failure_config.get("enhanced_debugging", [])
        return []
