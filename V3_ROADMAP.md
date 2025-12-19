# Sugar 3.0 Roadmap

**Status:** Testing Complete - Ready for v3.0.0 Release
**Branch:** `feature/agent-sdk-foundation`
**Last Updated:** December 2025

---

## Overview

Sugar 3.0 is a major re-platform from CLI subprocess wrapper to **Claude Agent SDK** native implementation.

**Detailed planning docs:** `~/Dev/roboticforce/r-d/sugar/`

---

## Completed

### Setup
- [x] Transfer repo: cdnsteve/sugar → roboticforce/sugar
- [x] Create develop branch for v3
- [x] Update all internal references to roboticforce/sugar
- [x] Create feature/agent-sdk-foundation branch

### Phase 1: Agent SDK Foundation
- [x] Add `claude-agent-sdk` dependency to pyproject.toml
- [x] Create `sugar/agent/` module structure
  - [x] `sugar/agent/__init__.py` - Module exports
  - [x] `sugar/agent/base.py` - SugarAgent class with SDK integration
  - [x] `sugar/agent/hooks.py` - Quality gate hooks (PreToolUse/PostToolUse)
  - [x] `sugar/agent/tools.py` - Custom Sugar tools
- [x] Create `sugar/executor/base.py` - Abstract executor interface
- [x] Create `sugar/executor/agent_sdk_executor.py` - SDK-based executor

### Phase 2: Issue Responder Profile
- [x] Create `sugar/profiles/` module structure
  - [x] `sugar/profiles/base.py` - BaseProfile abstract class
  - [x] `sugar/profiles/default.py` - Default development profile
  - [x] `sugar/profiles/issue_responder.py` - GitHub issue responder
- [x] Create `sugar/integrations/` module
  - [x] `sugar/integrations/github.py` - GitHub API client (using gh CLI)
- [x] Issue classification (bug, feature, question)
- [x] Response generation with confidence scoring
- [x] Auto-post threshold logic

### Phase 3: Distribution
- [x] GitHub Action (`action/`)
  - [x] `action/action.yml` - Action definition
  - [x] `action/Dockerfile` - Action container
  - [x] `action/entrypoint.py` - Action entry point
- [x] MCP Server (`mcp/`)
  - [x] `mcp/server.py` - MCP server implementation
  - [x] `mcp/Dockerfile` - Server container
  - [x] Tools: analyze_issue, generate_response, search_codebase, find_similar_issues, suggest_labels, validate_response
- [x] Update `requirements.txt` with new dependencies

### Phase 4: Billing & SaaS
- [x] Create `sugar/billing/` module
  - [x] `sugar/billing/usage.py` - Usage tracking (per customer, per action)
  - [x] `sugar/billing/api_keys.py` - API key management (generation, validation, rate limiting)
  - [x] `sugar/billing/tiers.py` - Pricing tiers (Free, Starter, Pro, Team, Enterprise)

### Phase 5: Documentation
- [x] Update V3_ROADMAP.md
- [x] Update README.md for v3.0
- [x] Update docs/README.md version

### Phase 6: Testing
- [x] Create test fixtures in conftest.py
- [x] Test billing module (35 tests)
  - [x] UsageRecord, UsageTracker
  - [x] APIKey, APIKeyManager
  - [x] PricingTier, TierManager
- [x] Test profiles module (37 tests)
  - [x] ProfileConfig, BaseProfile
  - [x] DefaultProfile
  - [x] IssueResponderProfile, IssueAnalysis, IssueResponse
- [x] Test agent hooks (43 tests)
  - [x] QualityGateHooks security checks
  - [x] Hook factories (preflight, audit, security)
- [x] Fix datetime.utcnow() deprecation warnings
- [x] All 115 new tests passing

---

## Next Steps (Post-v3.0.0)

- [ ] Wire up new executor in CLI
- [ ] Publish to PyPI as v3.0.0
- [ ] Publish GitHub Action to Marketplace
- [ ] Deploy MCP SaaS infrastructure
- [ ] Beta testing on target repos

---

## Project Structure (v3.0)

```
sugar/
├── sugar/
│   ├── agent/                     # ✅ Claude Agent SDK integration
│   │   ├── __init__.py
│   │   ├── base.py                # SugarAgent class
│   │   ├── hooks.py               # Quality gate hooks
│   │   └── tools.py               # Custom tools
│   ├── executor/
│   │   ├── __init__.py            # ✅ Updated exports
│   │   ├── base.py                # ✅ Abstract executor interface
│   │   ├── agent_sdk_executor.py  # ✅ SDK-based executor
│   │   ├── claude_wrapper.py      # Legacy (deprecated)
│   │   └── structured_request.py  # Existing
│   ├── profiles/                  # ✅ Workflow profiles
│   │   ├── __init__.py
│   │   ├── base.py                # BaseProfile
│   │   ├── default.py             # General purpose
│   │   └── issue_responder.py     # GitHub issues
│   ├── integrations/              # ✅ External integrations
│   │   ├── __init__.py
│   │   └── github.py              # GitHub API (gh CLI)
│   ├── billing/                   # ✅ SaaS billing
│   │   ├── __init__.py
│   │   ├── usage.py               # Usage tracking
│   │   ├── api_keys.py            # API key management
│   │   └── tiers.py               # Pricing tiers
│   ├── quality_gates/             # Existing
│   ├── discovery/                 # Existing
│   ├── learning/                  # Existing
│   └── storage/                   # Existing
│   ├── mcp/                       # ✅ MCP Server module
│   │   ├── __init__.py
│   │   └── server.py
├── action/                        # ✅ GitHub Action
│   ├── action.yml
│   ├── Dockerfile
│   └── entrypoint.py
├── tests/                         # ✅ Test suite
│   ├── test_billing.py            # 35 billing tests
│   ├── test_profiles.py           # 37 profile tests
│   ├── test_hooks.py              # 43 hook tests
│   └── conftest.py                # Test fixtures
├── mcp.Dockerfile                 # ✅ MCP Server container
├── pyproject.toml                 # ✅ Updated deps
├── requirements.txt               # ✅ Updated deps
└── V3_ROADMAP.md                  # ✅ This file
```

---

## Distribution Models

| Model | Description | Status |
|-------|-------------|--------|
| **GitHub Action** | BYOK, event-driven | ✅ Ready |
| **MCP Server** | Self-hosted or SaaS | ✅ Ready |
| **Python Package** | Library usage | ✅ Ready |
| **CLI** | Local development | Existing |

---

## Pricing Tiers (SaaS)

| Tier | Price | Issues/mo | Use Case |
|------|-------|-----------|----------|
| Free | $0 | 100 | OSS, testing |
| Starter | $49/mo | 500 | Small teams |
| Pro | $199/mo | 2,500 | Growing teams |
| Team | $499/mo | 10,000 | Organizations |
| Enterprise | Custom | Unlimited | Large orgs |

---

## References

- [Sugar 3.0 Re-platform Plan](../roboticforce/r-d/sugar/sugar-3.0-replatform-plan.md)
- [Sugar MCP Infrastructure](../roboticforce/r-d/sugar/sugar-mcp-infrastructure.md)
- [Sugar Billing Model](../roboticforce/r-d/sugar/sugar-billing-and-distribution.md)
- [Claude Agent SDK Docs](https://docs.anthropic.com/en/docs/agents-and-tools/claude-agent-sdk)
