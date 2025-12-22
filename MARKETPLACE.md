# Sugar Issue Responder

**AI-powered GitHub issue assistant that automatically analyzes issues and posts helpful responses**

Sugar uses Claude AI to understand your issues, search your codebase for relevant context, and generate helpful responses with specific code references.

## Quick Setup

1. **Add API Key**: Add `ANTHROPIC_API_KEY` to your repository secrets
2. **Create Workflow**: Add this to `.github/workflows/issue-responder.yml`

```yaml
name: Issue Responder
on:
  issues:
    types: [opened]

permissions:
  issues: write
  contents: read

jobs:
  respond:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: roboticforce/sugar@main
        with:
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

3. **Done!** Open a new issue and watch Sugar respond

## What It Does

- **Analyzes issues** - Classifies type (bug/feature/question), sentiment, key topics
- **Searches codebase** - Finds relevant files, functions, and error patterns
- **Finds similar issues** - References related past issues for context
- **Generates responses** - Creates helpful replies with code references
- **Auto-posts** - Only posts responses with confidence above threshold
- **Adds labels** - Suggests and applies relevant labels

## Key Features

### Intelligent Analysis
Uses Claude 4 to deeply understand issue context, technical requirements, and user intent.

### Codebase-Aware
Searches your repository to provide responses grounded in your actual implementation.

### Confidence-Based
Only auto-posts responses it's confident about (configurable threshold).

### Customizable
Full control over models, thresholds, response length, and behavior.

## Usage Modes

**Auto Mode** - Responds to all new issues automatically
```yaml
with:
  mode: auto
  confidence-threshold: '0.7'
```

**Mention Mode** - Only responds when `@sugar` is mentioned
```yaml
with:
  mode: mention
```

**Triage Mode** - Analyzes and labels without posting comments
```yaml
with:
  mode: triage
```

## Configuration Options

| Input | Description | Default |
|-------|-------------|---------|
| `anthropic-api-key` | Your Anthropic API key | Required |
| `mode` | `auto`, `mention`, or `triage` | `auto` |
| `model` | Claude model to use | `claude-sonnet-4-5` |
| `confidence-threshold` | Min confidence to post (0.0-1.0) | `0.7` |
| `skip-labels` | Labels to skip (comma-separated) | `''` |

[Full documentation](https://github.com/roboticforce/sugar/blob/main/action/README.md)

## Example Response

```markdown
Thanks for reporting this! I found the relevant code in `src/auth/login.py`.

The timeout you're experiencing is likely due to the session expiration logic
on line 45. The default timeout is set to 5 minutes:

```python
SESSION_TIMEOUT = 300  # 5 minutes
```

You can increase this by setting the `SESSION_TIMEOUT` environment variable.
For example, to set it to 30 minutes:

```bash
export SESSION_TIMEOUT=1800
```

Related: See issue #123 where we discussed similar timeout concerns.
```

## Requirements

- Anthropic API key ([get one here](https://console.anthropic.com/))
- GitHub Actions enabled
- Public or private repository with read access

## Pricing

Sugar is **free and open source**. You only pay for:
- Anthropic API usage (~$0.01-0.05 per response)
- GitHub Actions minutes (free tier available)

## Support

- [Full Documentation](https://github.com/roboticforce/sugar)
- [Report Issues](https://github.com/roboticforce/sugar/issues)
- [View Source](https://github.com/roboticforce/sugar)

## About

Built with the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk) by [RoboticForce](https://github.com/roboticforce).

Part of the [Sugar project](https://github.com/roboticforce/sugar) - a complete autonomous development system.

---

**License**: MIT | **Language**: Python 3.11+ | **Status**: Production Ready
