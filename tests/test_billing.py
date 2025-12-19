"""
Tests for Sugar billing module (P1 - highest priority)

Tests usage tracking, API key management, and pricing tiers.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
import json
import os

from sugar.billing import UsageTracker, UsageRecord, APIKeyManager, APIKey, TierManager
from sugar.billing.tiers import TierName, PricingTier


class TestUsageRecord:
    """Tests for UsageRecord dataclass"""

    def test_usage_record_creation(self):
        record = UsageRecord(
            customer_id="cust_123",
            action="issue_response",
            timestamp=datetime.now(timezone.utc),
            tokens_input=1000,
            tokens_output=500,
        )
        assert record.customer_id == "cust_123"
        assert record.action == "issue_response"
        assert record.tokens_input == 1000
        assert record.tokens_output == 500

    def test_usage_record_to_dict(self):
        now = datetime.now(timezone.utc)
        record = UsageRecord(
            customer_id="cust_123",
            action="issue_response",
            timestamp=now,
            tokens_input=1000,
            tokens_output=500,
            issue_number=42,
            repo="owner/repo",
        )
        d = record.to_dict()
        assert d["customer_id"] == "cust_123"
        assert d["action"] == "issue_response"
        assert d["tokens_input"] == 1000
        assert d["tokens_output"] == 500
        assert d["issue_number"] == 42
        assert d["repo"] == "owner/repo"

    def test_usage_record_from_dict(self):
        data = {
            "customer_id": "cust_456",
            "action": "search",
            "timestamp": "2025-01-01T12:00:00",
            "tokens_input": 100,
            "tokens_output": 200,
        }
        record = UsageRecord.from_dict(data)
        assert record.customer_id == "cust_456"
        assert record.action == "search"
        assert record.tokens_input == 100


class TestUsageTracker:
    """Tests for UsageTracker"""

    @pytest.mark.asyncio
    async def test_usage_tracker_init_creates_directory(self, billing_storage_path):
        path = str(billing_storage_path / "new_usage")
        tracker = UsageTracker(storage_path=path)
        assert os.path.exists(path)

    @pytest.mark.asyncio
    async def test_usage_tracker_record(self, usage_tracker):
        record = await usage_tracker.record(
            customer_id="test_customer",
            action="issue_response",
            tokens_input=500,
            tokens_output=250,
        )
        assert record.customer_id == "test_customer"
        assert record.action == "issue_response"
        assert record.tokens_input == 500

    @pytest.mark.asyncio
    async def test_usage_tracker_flush_writes_file(self, usage_tracker):
        # Record some usage
        for i in range(5):
            await usage_tracker.record(
                customer_id="test_customer",
                action="test_action",
                tokens_input=100 * i,
            )

        # Force flush
        await usage_tracker._flush()

        # Check file was written
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        file_path = os.path.join(usage_tracker.storage_path, f"{today}.jsonl")
        assert os.path.exists(file_path)

    @pytest.mark.asyncio
    async def test_usage_tracker_get_customer_usage(self, usage_tracker):
        # Record some usage
        await usage_tracker.record(
            customer_id="test_customer",
            action="issue_response",
            tokens_input=1000,
            tokens_output=500,
        )
        await usage_tracker.record(
            customer_id="test_customer",
            action="search",
            tokens_input=100,
            tokens_output=50,
        )
        await usage_tracker.record(
            customer_id="other_customer",
            action="issue_response",
            tokens_input=200,
            tokens_output=100,
        )

        summary = await usage_tracker.get_customer_usage("test_customer")

        assert summary.customer_id == "test_customer"
        assert summary.total_actions == 2
        assert summary.total_tokens_input == 1100
        assert summary.total_tokens_output == 550

    @pytest.mark.asyncio
    async def test_usage_tracker_check_quota_within_limit(self, usage_tracker):
        await usage_tracker.record(
            customer_id="test_customer",
            action="issue_response",
        )

        has_quota, remaining = await usage_tracker.check_quota(
            customer_id="test_customer",
            action="issue_response",
            quota_limit=100,
        )

        assert has_quota is True
        assert remaining == 99

    @pytest.mark.asyncio
    async def test_usage_tracker_check_quota_exceeded(self, usage_tracker):
        # Use up the quota
        for i in range(5):
            await usage_tracker.record(
                customer_id="test_customer",
                action="issue_response",
            )

        has_quota, remaining = await usage_tracker.check_quota(
            customer_id="test_customer",
            action="issue_response",
            quota_limit=3,
        )

        assert has_quota is False
        assert remaining == 0


class TestAPIKey:
    """Tests for APIKey dataclass"""

    def test_api_key_creation(self):
        key = APIKey(
            key_id="sk_sugar_abc123",
            key_hash="hash123",
            customer_id="cust_123",
            name="Test Key",
            created_at=datetime.now(timezone.utc),
        )
        assert key.key_id == "sk_sugar_abc123"
        assert key.is_active is True
        assert key.rate_limit == 1000

    def test_api_key_is_expired_false(self):
        key = APIKey(
            key_id="sk_sugar_abc123",
            key_hash="hash123",
            customer_id="cust_123",
            name="Test Key",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        assert key.is_expired() is False

    def test_api_key_is_expired_true(self):
        key = APIKey(
            key_id="sk_sugar_abc123",
            key_hash="hash123",
            customer_id="cust_123",
            name="Test Key",
            created_at=datetime.now(timezone.utc) - timedelta(days=60),
            expires_at=datetime.now(timezone.utc) - timedelta(days=30),
        )
        assert key.is_expired() is True

    def test_api_key_has_scope_wildcard(self):
        key = APIKey(
            key_id="sk_sugar_abc123",
            key_hash="hash123",
            customer_id="cust_123",
            name="Test Key",
            created_at=datetime.now(timezone.utc),
            scopes=["*"],
        )
        assert key.has_scope("any_scope") is True
        assert key.has_scope("another_scope") is True

    def test_api_key_has_scope_specific(self):
        key = APIKey(
            key_id="sk_sugar_abc123",
            key_hash="hash123",
            customer_id="cust_123",
            name="Test Key",
            created_at=datetime.now(timezone.utc),
            scopes=["read", "write"],
        )
        assert key.has_scope("read") is True
        assert key.has_scope("delete") is False


class TestAPIKeyManager:
    """Tests for APIKeyManager"""

    def test_api_key_manager_generate_key(self, api_key_manager):
        api_key, key_string = api_key_manager.generate_key(
            customer_id="cust_123",
            name="Test Key",
        )

        assert api_key.customer_id == "cust_123"
        assert api_key.name == "Test Key"
        assert key_string.startswith("sk_sugar_")
        assert api_key.key_id.startswith("sk_sugar_")

    def test_api_key_manager_validate_key_success(self, api_key_manager):
        api_key, key_string = api_key_manager.generate_key(
            customer_id="cust_123",
            name="Test Key",
        )

        validated = api_key_manager.validate_key(key_string)

        assert validated is not None
        assert validated.customer_id == "cust_123"

    def test_api_key_manager_validate_key_invalid(self, api_key_manager):
        validated = api_key_manager.validate_key("sk_sugar_invalid_key")
        assert validated is None

    def test_api_key_manager_validate_key_wrong_prefix(self, api_key_manager):
        validated = api_key_manager.validate_key("wrong_prefix_key")
        assert validated is None

    def test_api_key_manager_revoke_key(self, api_key_manager):
        api_key, key_string = api_key_manager.generate_key(
            customer_id="cust_123",
            name="Test Key",
        )

        # Revoke the key
        result = api_key_manager.revoke_key(api_key.key_id)
        assert result is True

        # Key should no longer validate
        validated = api_key_manager.validate_key(key_string)
        assert validated is None

    def test_api_key_manager_rate_limit_within(self, api_key_manager):
        api_key, _ = api_key_manager.generate_key(
            customer_id="cust_123",
            name="Test Key",
            rate_limit=100,
        )

        info = api_key_manager.check_rate_limit(api_key)

        assert info.limit == 100
        assert info.remaining == 99  # One call made

    def test_api_key_manager_rate_limit_exceeded(self, api_key_manager):
        api_key, _ = api_key_manager.generate_key(
            customer_id="cust_123",
            name="Test Key",
            rate_limit=3,
        )

        # Exhaust rate limit
        for _ in range(5):
            api_key_manager.check_rate_limit(api_key)

        assert api_key_manager.is_rate_limited(api_key) is True

    def test_api_key_manager_list_keys(self, api_key_manager):
        api_key_manager.generate_key(customer_id="cust_1", name="Key 1")
        api_key_manager.generate_key(customer_id="cust_1", name="Key 2")
        api_key_manager.generate_key(customer_id="cust_2", name="Key 3")

        # List all
        all_keys = api_key_manager.list_keys()
        assert len(all_keys) == 3

        # Filter by customer
        cust1_keys = api_key_manager.list_keys(customer_id="cust_1")
        assert len(cust1_keys) == 2


class TestPricingTier:
    """Tests for PricingTier"""

    def test_pricing_tier_to_dict(self):
        tier = PricingTier(
            name=TierName.STARTER,
            display_name="Starter",
            price_monthly=4900,
            price_yearly=47000,
            issues_per_month=500,
            tokens_per_month=500000,
            repos_limit=10,
            team_members=3,
        )
        d = tier.to_dict()
        assert d["name"] == "starter"
        assert d["price_monthly"] == 4900
        assert d["price_monthly_display"] == "$49/mo"


class TestTierManager:
    """Tests for TierManager"""

    def test_tier_manager_get_tier_by_name(self, tier_manager):
        tier = tier_manager.get_tier(TierName.PRO)
        assert tier.name == TierName.PRO
        assert tier.display_name == "Pro"
        assert tier.price_monthly == 19900

    def test_tier_manager_get_tier_by_string(self, tier_manager):
        tier = tier_manager.get_tier_by_string("team")
        assert tier.name == TierName.TEAM
        assert tier.issues_per_month == 10000

    def test_tier_manager_get_tier_unknown_defaults_free(self, tier_manager):
        tier = tier_manager.get_tier_by_string("unknown_tier")
        assert tier.name == TierName.FREE

    def test_tier_manager_list_tiers(self, tier_manager):
        tiers = tier_manager.list_tiers()
        assert len(tiers) == 5
        tier_names = [t.name for t in tiers]
        assert TierName.FREE in tier_names
        assert TierName.ENTERPRISE in tier_names

    def test_tier_check_limit_within(self, tier_manager):
        tier = tier_manager.get_tier(TierName.STARTER)
        within, remaining = tier_manager.check_limit(tier, 100, "issues")
        assert within is True
        assert remaining == 400  # 500 - 100

    def test_tier_check_limit_exceeded(self, tier_manager):
        tier = tier_manager.get_tier(TierName.FREE)
        within, remaining = tier_manager.check_limit(tier, 150, "issues")
        assert within is False
        assert remaining == 0

    def test_tier_check_limit_unlimited(self, tier_manager):
        tier = tier_manager.get_tier(TierName.ENTERPRISE)
        within, remaining = tier_manager.check_limit(tier, 1000000, "issues")
        assert within is True
        assert remaining == -1  # Unlimited

    def test_calculate_overage_cost_issues(self, tier_manager):
        tier = tier_manager.get_tier(TierName.STARTER)
        cost = tier_manager.calculate_overage_cost(tier, 100, "issues")
        assert cost == 1000  # 100 * 10 cents = $10 = 1000 cents

    def test_calculate_overage_cost_tokens(self, tier_manager):
        tier = tier_manager.get_tier(TierName.STARTER)
        cost = tier_manager.calculate_overage_cost(tier, 10000, "tokens")
        assert cost == 10  # 10000 / 1000 * 1 cent = 10 cents

    def test_enterprise_no_overage(self, tier_manager):
        tier = tier_manager.get_tier(TierName.ENTERPRISE)
        cost = tier_manager.calculate_overage_cost(tier, 1000000, "issues")
        assert cost == 0

    def test_free_tier_limits(self, tier_manager):
        tier = tier_manager.get_tier(TierName.FREE)
        assert tier.issues_per_month == 100
        assert tier.tokens_per_month == 100000
        assert tier.private_repos is False
        assert tier.rate_limit_per_hour == 100

    def test_team_tier_features(self, tier_manager):
        tier = tier_manager.get_tier(TierName.TEAM)
        assert tier.repos_limit == 0  # Unlimited
        assert tier.priority_support is True
        assert tier.sla_uptime == 99.5
        assert "SSO integration" in tier.features
