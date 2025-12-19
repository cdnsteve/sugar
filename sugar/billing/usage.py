"""
Usage Tracking for Sugar SaaS

Tracks API usage per customer for billing purposes:
- Issue responses generated
- API calls made
- Tokens consumed
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """A single usage record"""

    customer_id: str
    action: str  # issue_response, search, similar_issues, etc.
    timestamp: datetime
    tokens_input: int = 0
    tokens_output: int = 0
    issue_number: Optional[int] = None
    repo: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "action": self.action,
            "timestamp": self.timestamp.isoformat(),
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "issue_number": self.issue_number,
            "repo": self.repo,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UsageRecord":
        return cls(
            customer_id=data["customer_id"],
            action=data["action"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tokens_input=data.get("tokens_input", 0),
            tokens_output=data.get("tokens_output", 0),
            issue_number=data.get("issue_number"),
            repo=data.get("repo"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class UsageSummary:
    """Usage summary for a customer"""

    customer_id: str
    period_start: datetime
    period_end: datetime
    total_actions: int
    total_tokens_input: int
    total_tokens_output: int
    actions_by_type: Dict[str, int]
    repos_used: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_actions": self.total_actions,
            "total_tokens_input": self.total_tokens_input,
            "total_tokens_output": self.total_tokens_output,
            "total_tokens": self.total_tokens_input + self.total_tokens_output,
            "actions_by_type": self.actions_by_type,
            "repos_used": self.repos_used,
        }


class UsageTracker:
    """
    Track usage for billing purposes.

    Stores usage records and provides aggregation for billing cycles.
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        flush_interval: int = 60,
    ):
        """
        Initialize the usage tracker.

        Args:
            storage_path: Path to store usage data (defaults to .sugar/usage/)
            flush_interval: How often to flush records to storage (seconds)
        """
        self.storage_path = storage_path or os.path.join(
            os.path.expanduser("~"), ".sugar", "usage"
        )
        self.flush_interval = flush_interval

        # In-memory buffer for batch writes
        self._buffer: List[UsageRecord] = []
        self._buffer_lock = asyncio.Lock()

        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)

    async def record(
        self,
        customer_id: str,
        action: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        issue_number: Optional[int] = None,
        repo: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageRecord:
        """
        Record a usage event.

        Args:
            customer_id: Customer identifier
            action: Type of action performed
            tokens_input: Input tokens consumed
            tokens_output: Output tokens generated
            issue_number: Related issue number (optional)
            repo: Repository (optional)
            metadata: Additional metadata (optional)

        Returns:
            The created usage record
        """
        record = UsageRecord(
            customer_id=customer_id,
            action=action,
            timestamp=datetime.now(timezone.utc),
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            issue_number=issue_number,
            repo=repo,
            metadata=metadata or {},
        )

        async with self._buffer_lock:
            self._buffer.append(record)

            # Flush if buffer is large enough
            if len(self._buffer) >= 100:
                await self._flush()

        logger.debug(f"Recorded usage: {customer_id} - {action}")
        return record

    async def _flush(self) -> None:
        """Flush buffered records to storage"""
        if not self._buffer:
            return

        records = self._buffer.copy()
        self._buffer.clear()

        # Group by date for file organization
        by_date: Dict[str, List[UsageRecord]] = {}
        for record in records:
            date_key = record.timestamp.strftime("%Y-%m-%d")
            if date_key not in by_date:
                by_date[date_key] = []
            by_date[date_key].append(record)

        # Write to files
        for date_key, day_records in by_date.items():
            file_path = os.path.join(self.storage_path, f"{date_key}.jsonl")

            with open(file_path, "a") as f:
                for record in day_records:
                    f.write(json.dumps(record.to_dict()) + "\n")

        logger.debug(f"Flushed {len(records)} usage records")

    async def get_customer_usage(
        self,
        customer_id: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> UsageSummary:
        """
        Get usage summary for a customer.

        Args:
            customer_id: Customer identifier
            period_start: Start of period (defaults to 30 days ago)
            period_end: End of period (defaults to now)

        Returns:
            Usage summary for the period
        """
        if period_end is None:
            period_end = datetime.now(timezone.utc)
        if period_start is None:
            period_start = period_end - timedelta(days=30)

        # Flush current buffer first
        async with self._buffer_lock:
            await self._flush()

        # Read records from files
        records: List[UsageRecord] = []
        current_date = period_start.date()

        while current_date <= period_end.date():
            file_path = os.path.join(
                self.storage_path,
                f"{current_date.strftime('%Y-%m-%d')}.jsonl"
            )

            if os.path.exists(file_path):
                with open(file_path) as f:
                    for line in f:
                        record = UsageRecord.from_dict(json.loads(line))
                        if (
                            record.customer_id == customer_id
                            and period_start <= record.timestamp <= period_end
                        ):
                            records.append(record)

            current_date += timedelta(days=1)

        # Aggregate
        total_tokens_input = sum(r.tokens_input for r in records)
        total_tokens_output = sum(r.tokens_output for r in records)

        actions_by_type: Dict[str, int] = {}
        repos: set = set()

        for record in records:
            actions_by_type[record.action] = actions_by_type.get(record.action, 0) + 1
            if record.repo:
                repos.add(record.repo)

        return UsageSummary(
            customer_id=customer_id,
            period_start=period_start,
            period_end=period_end,
            total_actions=len(records),
            total_tokens_input=total_tokens_input,
            total_tokens_output=total_tokens_output,
            actions_by_type=actions_by_type,
            repos_used=sorted(repos),
        )

    async def check_quota(
        self,
        customer_id: str,
        action: str,
        quota_limit: int,
    ) -> tuple[bool, int]:
        """
        Check if a customer has quota remaining.

        Args:
            customer_id: Customer identifier
            action: Action type to check
            quota_limit: Maximum allowed actions per period

        Returns:
            Tuple of (has_quota, remaining_quota)
        """
        # Get current month's usage
        now = datetime.now(timezone.utc)
        period_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        summary = await self.get_customer_usage(
            customer_id,
            period_start=period_start,
            period_end=now,
        )

        action_count = summary.actions_by_type.get(action, 0)
        remaining = quota_limit - action_count

        return remaining > 0, max(0, remaining)

    async def close(self) -> None:
        """Flush remaining records and close"""
        async with self._buffer_lock:
            await self._flush()
