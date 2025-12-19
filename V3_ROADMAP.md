# Sugar 3.0 Roadmap

**Status:** In Progress
**Branch:** `feature/agent-sdk-foundation`
**Last Updated:** December 2025

---

## Overview

Sugar 3.0 is a major re-platform from CLI subprocess wrapper to **Claude Agent SDK** native implementation.

**Detailed planning docs:** `~/Dev/roboticforce/r-d/sugar/`

---

## Completed

- [x] Transfer repo: cdnsteve/sugar → roboticforce/sugar
- [x] Create develop branch for v3
- [x] Update all internal references to roboticforce/sugar
- [x] Create feature/agent-sdk-foundation branch

---

## Next Steps

### Phase 1: Agent SDK Foundation
- [x] Add `claude-agent-sdk` dependency to pyproject.toml
- [x] Create new `sugar/agent/` module structure
  - [x] `sugar/agent/__init__.py` - Module exports
  - [x] `sugar/agent/base.py` - SugarAgent class with SDK integration
  - [x] `sugar/agent/hooks.py` - Quality gate hooks (PreToolUse/PostToolUse)
  - [x] `sugar/agent/tools.py` - Custom Sugar tools
- [x] Create `sugar/executor/base.py` - Abstract executor interface
- [x] Create `sugar/executor/agent_sdk_executor.py` - SDK-based executor
- [ ] Basic CLI integration (wire up new executor)

### Phase 2: Issue Responder Profile
- [ ] Create `sugar/profiles/issue_responder.py`
- [ ] GitHub API integration (read issues, post comments)
- [ ] Codebase search tools (grep, file read)
- [ ] Response generation with quality gates
- [ ] Confidence thresholds

### Phase 3: Distribution
- [ ] GitHub Action (`action/`)
- [ ] MCP Server (`mcp/`)
- [ ] Docker image updates

---

## Key Files Created/To Create

```
sugar/
├── agent/                     # CREATED
│   ├── __init__.py            # ✅ Module exports
│   ├── base.py                # ✅ SugarAgent class with SDK
│   ├── hooks.py               # ✅ Quality gate hooks
│   └── tools.py               # ✅ Custom agent tools
├── executor/
│   ├── base.py                # ✅ Abstract executor interface
│   ├── agent_sdk_executor.py  # ✅ SDK-based executor
│   └── claude_wrapper.py      # Existing (legacy)
├── profiles/                  # TO CREATE
│   ├── __init__.py
│   ├── default.py             # General purpose
│   └── issue_responder.py     # GitHub issues
```

---

## References

- [Sugar 3.0 Re-platform Plan](../roboticforce/r-d/sugar/sugar-3.0-replatform-plan.md)
- [Sugar MCP Infrastructure](../roboticforce/r-d/sugar/sugar-mcp-infrastructure.md)
- [Sugar Billing Model](../roboticforce/r-d/sugar/sugar-billing-and-distribution.md)
- [Claude Agent SDK Docs](https://docs.anthropic.com/en/docs/agents-and-tools/claude-agent-sdk)

---

## Resume Development

```bash
cd ~/Dev/sugar
git checkout feature/agent-sdk-foundation
# Pick up from "Phase 1: Agent SDK Foundation"
```
