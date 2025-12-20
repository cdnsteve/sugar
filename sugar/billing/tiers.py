"""
Pricing Tiers for Sugar SaaS

Defines subscription tiers and their limits:
- Free: BYOK, limited usage
- Starter: $49/mo, 500 issues
- Pro: $199/mo, 2,500 issues
- Team: $499/mo, 10,000 issues
- Enterprise: Custom
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TierName(str, Enum):
    """Available pricing tiers"""

    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


@dataclass
class PricingTier:
    """A pricing tier definition"""

    name: TierName
    display_name: str
    price_monthly: int  # In cents
    price_yearly: int  # In cents (annual discount)

    # Usage limits
    issues_per_month: int
    tokens_per_month: int
    repos_limit: int  # 0 = unlimited
    team_members: int  # 0 = unlimited

    # Features
    features: List[str] = field(default_factory=list)
    private_repos: bool = True
    priority_support: bool = False
    sla_uptime: Optional[float] = None  # e.g., 99.9

    # API limits
    rate_limit_per_hour: int = 1000
    concurrent_requests: int = 10

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name.value,
            "display_name": self.display_name,
            "price_monthly": self.price_monthly,
            "price_yearly": self.price_yearly,
            "price_monthly_display": f"${self.price_monthly / 100:.0f}/mo",
            "price_yearly_display": f"${self.price_yearly / 100:.0f}/yr",
            "issues_per_month": self.issues_per_month,
            "tokens_per_month": self.tokens_per_month,
            "repos_limit": self.repos_limit,
            "team_members": self.team_members,
            "features": self.features,
            "private_repos": self.private_repos,
            "priority_support": self.priority_support,
            "sla_uptime": self.sla_uptime,
            "rate_limit_per_hour": self.rate_limit_per_hour,
            "concurrent_requests": self.concurrent_requests,
        }


# Pre-defined tiers
TIERS = {
    TierName.FREE: PricingTier(
        name=TierName.FREE,
        display_name="Free",
        price_monthly=0,
        price_yearly=0,
        issues_per_month=100,
        tokens_per_month=100_000,
        repos_limit=3,
        team_members=1,
        features=[
            "Issue analysis",
            "Response generation",
            "Public repos only",
            "Community support",
        ],
        private_repos=False,
        rate_limit_per_hour=100,
        concurrent_requests=2,
    ),
    TierName.STARTER: PricingTier(
        name=TierName.STARTER,
        display_name="Starter",
        price_monthly=4900,  # $49
        price_yearly=47000,  # $470 (2 months free)
        issues_per_month=500,
        tokens_per_month=500_000,
        repos_limit=10,
        team_members=3,
        features=[
            "Everything in Free",
            "Private repos",
            "Custom prompts",
            "Email support",
        ],
        private_repos=True,
        rate_limit_per_hour=500,
        concurrent_requests=5,
    ),
    TierName.PRO: PricingTier(
        name=TierName.PRO,
        display_name="Pro",
        price_monthly=19900,  # $199
        price_yearly=190000,  # $1,900 (2 months free)
        issues_per_month=2500,
        tokens_per_month=2_500_000,
        repos_limit=50,
        team_members=10,
        features=[
            "Everything in Starter",
            "Advanced analytics",
            "Custom integrations",
            "Priority email support",
        ],
        private_repos=True,
        rate_limit_per_hour=1000,
        concurrent_requests=10,
    ),
    TierName.TEAM: PricingTier(
        name=TierName.TEAM,
        display_name="Team",
        price_monthly=49900,  # $499
        price_yearly=479000,  # $4,790 (2 months free)
        issues_per_month=10000,
        tokens_per_month=10_000_000,
        repos_limit=0,  # Unlimited
        team_members=50,
        features=[
            "Everything in Pro",
            "Unlimited repos",
            "SSO integration",
            "Dedicated support",
            "99.5% SLA",
        ],
        private_repos=True,
        priority_support=True,
        sla_uptime=99.5,
        rate_limit_per_hour=5000,
        concurrent_requests=50,
    ),
    TierName.ENTERPRISE: PricingTier(
        name=TierName.ENTERPRISE,
        display_name="Enterprise",
        price_monthly=0,  # Custom
        price_yearly=0,  # Custom
        issues_per_month=0,  # Unlimited
        tokens_per_month=0,  # Unlimited
        repos_limit=0,  # Unlimited
        team_members=0,  # Unlimited
        features=[
            "Everything in Team",
            "Unlimited everything",
            "On-premise deployment",
            "Custom SLA",
            "Dedicated account manager",
            "Training included",
        ],
        private_repos=True,
        priority_support=True,
        sla_uptime=99.99,
        rate_limit_per_hour=0,  # Unlimited
        concurrent_requests=0,  # Unlimited
    ),
}


class TierManager:
    """
    Manage pricing tiers and customer subscriptions.
    """

    def __init__(self):
        """Initialize the tier manager"""
        self.tiers = TIERS

    def get_tier(self, tier_name: TierName) -> PricingTier:
        """Get a tier by name"""
        return self.tiers.get(tier_name, self.tiers[TierName.FREE])

    def get_tier_by_string(self, name: str) -> PricingTier:
        """Get a tier by string name"""
        try:
            tier_name = TierName(name.lower())
            return self.get_tier(tier_name)
        except ValueError:
            return self.tiers[TierName.FREE]

    def list_tiers(self) -> List[PricingTier]:
        """List all available tiers"""
        return list(self.tiers.values())

    def check_limit(
        self,
        tier: PricingTier,
        current_usage: int,
        limit_type: str = "issues",
    ) -> tuple[bool, int]:
        """
        Check if usage is within tier limits.

        Args:
            tier: The customer's tier
            current_usage: Current usage count
            limit_type: Type of limit to check (issues, tokens, repos)

        Returns:
            Tuple of (within_limit, remaining)
        """
        if limit_type == "issues":
            limit = tier.issues_per_month
        elif limit_type == "tokens":
            limit = tier.tokens_per_month
        elif limit_type == "repos":
            limit = tier.repos_limit
        else:
            return True, 0

        # 0 means unlimited
        if limit == 0:
            return True, -1  # -1 indicates unlimited

        remaining = limit - current_usage
        return remaining > 0, max(0, remaining)

    def get_upgrade_suggestions(
        self,
        current_tier: PricingTier,
        usage: Dict[str, int],
    ) -> List[Dict[str, Any]]:
        """
        Suggest tier upgrades based on usage.

        Args:
            current_tier: Customer's current tier
            usage: Dictionary of usage metrics

        Returns:
            List of upgrade suggestions
        """
        suggestions = []
        tier_order = [TierName.FREE, TierName.STARTER, TierName.PRO, TierName.TEAM]

        try:
            current_index = tier_order.index(current_tier.name)
        except ValueError:
            return suggestions  # Enterprise has no upgrades

        # Check if approaching limits
        issues_used = usage.get("issues", 0)
        issues_percent = (
            issues_used / current_tier.issues_per_month * 100
            if current_tier.issues_per_month > 0
            else 0
        )

        if issues_percent >= 80:
            # Suggest next tier
            if current_index < len(tier_order) - 1:
                next_tier = self.get_tier(tier_order[current_index + 1])
                suggestions.append(
                    {
                        "reason": f"You've used {issues_percent:.0f}% of your monthly issues",
                        "suggested_tier": next_tier.to_dict(),
                        "savings": f"Upgrading unlocks {next_tier.issues_per_month - current_tier.issues_per_month} more issues/month",
                    }
                )

        return suggestions

    def calculate_overage_cost(
        self,
        tier: PricingTier,
        overage_amount: int,
        overage_type: str = "issues",
    ) -> int:
        """
        Calculate overage costs.

        Args:
            tier: Customer's tier
            overage_amount: Amount over the limit
            overage_type: Type of overage

        Returns:
            Overage cost in cents
        """
        if tier.name == TierName.ENTERPRISE:
            return 0  # Enterprise has no overages

        # Overage pricing (per unit)
        overage_rates = {
            "issues": 10,  # $0.10 per issue
            "tokens": 1,  # $0.01 per 1000 tokens (calculated per 1000)
        }

        rate = overage_rates.get(overage_type, 0)

        if overage_type == "tokens":
            # Tokens are billed per 1000
            overage_amount = overage_amount // 1000

        return overage_amount * rate
