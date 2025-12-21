# Billing and Pricing

Sugar offers flexible pricing tiers for both self-hosted and SaaS deployments.

## Self-Hosted (Free)

Run Sugar locally with your own Claude API key (BYOK - Bring Your Own Key):

```bash
pip install sugarai
cd your-project
sugar init
```

Self-hosted Sugar is **completely free**. You only pay for Claude API usage directly to Anthropic.

## SaaS Pricing Tiers

For managed Sugar services, choose a tier that fits your needs:

| Tier | Price | Issues/mo | Repos | Team Members |
|------|-------|-----------|-------|--------------|
| **Free** | $0 | 100 | 3 | 1 |
| **Starter** | $49/mo | 500 | 10 | 3 |
| **Pro** | $199/mo | 2,500 | 50 | 10 |
| **Team** | $499/mo | 10,000 | Unlimited | 50 |
| **Enterprise** | Custom | Unlimited | Unlimited | Unlimited |

Annual billing includes 2 months free.

## Tier Features

### Free Tier
- Issue analysis and response generation
- Public repositories only
- Community support
- 100 requests/hour rate limit

### Starter ($49/mo)
- Everything in Free
- Private repositories
- Custom prompts
- Email support
- 500 requests/hour rate limit

### Pro ($199/mo)
- Everything in Starter
- Advanced analytics
- Custom integrations
- Priority email support
- 1,000 requests/hour rate limit

### Team ($499/mo)
- Everything in Pro
- Unlimited repositories
- SSO integration
- Dedicated support
- 99.5% SLA uptime
- 5,000 requests/hour rate limit

### Enterprise (Custom)
- Everything in Team
- On-premise deployment
- Custom SLA (up to 99.99%)
- Dedicated account manager
- Training included
- Unlimited rate limits

## API Keys

SaaS usage requires an API key for authentication.

### Generating Keys

```bash
# Via CLI (coming soon)
sugar api-key create --name "Production Key" --scope "*"

# Via Dashboard
# Visit: https://app.sugar.dev/settings/api-keys
```

### Key Format

Sugar API keys follow this format:
```
sk_sugar_<random-token>
```

### Key Scopes

Control what each key can access:

| Scope | Description |
|-------|-------------|
| `*` | Full access (all operations) |
| `read` | Read tasks and status |
| `write` | Create and update tasks |
| `execute` | Run autonomous workflows |
| `admin` | Manage team and settings |

### Rate Limiting

Each key has rate limits based on tier:

```python
# Response headers include:
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 998
X-RateLimit-Reset: 2025-01-15T12:00:00Z
```

### Revoking Keys

```bash
# Revoke a compromised key immediately
sugar api-key revoke sk_sugar_abc123

# Via Dashboard
# Settings > API Keys > Revoke
```

## Usage Tracking

Monitor your usage to avoid overages:

```bash
# Check current usage
sugar billing status

# View detailed breakdown
sugar billing usage --month 2025-01
```

### Overage Pricing

If you exceed tier limits:

- Issues: $0.10 per issue over limit
- Tokens: $0.01 per 1,000 tokens over limit

Overage charges are billed at the end of each billing cycle.

## Upgrading

### When to Upgrade

Sugar will notify you when approaching limits:

- 80% usage: Upgrade suggestion
- 100% usage: Operations paused until upgrade or new billing cycle

### How to Upgrade

```bash
# Check upgrade options
sugar billing upgrade --list

# Upgrade to Pro
sugar billing upgrade pro

# Via Dashboard
# Settings > Billing > Upgrade
```

## Billing FAQ

**Q: Can I switch between tiers?**
A: Yes, you can upgrade anytime. Downgrades take effect at the next billing cycle.

**Q: What happens if I exceed my limits?**
A: You'll receive a warning at 80%. At 100%, new operations are paused. You can upgrade or wait for the next cycle.

**Q: Do unused issues roll over?**
A: No, usage limits reset monthly.

**Q: Can I get a refund?**
A: Pro-rated refunds are available for annual plans. Contact support.

**Q: Is there a trial period?**
A: The Free tier is always available. Starter and Pro tiers include a 14-day free trial.

## Enterprise Contact

For Enterprise pricing and features:

- Email: enterprise@roboticforce.io
- Schedule a demo: https://calendly.com/roboticforce/sugar-demo

## Next Steps

- [Quick Start](quick-start.md) - Get started with Sugar
- [Configuration](configuration.md) - Configure your deployment
- [API Reference](../dev/api-reference.md) - API documentation
