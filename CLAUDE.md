## Development Environment

This project supports both **uv** (recommended) and **venv** workflows:

### Using uv (Recommended - Much Faster!)
```bash
# Install dependencies
uv pip install -e ".[dev,test,github]"

# Run commands
uv run python -m sugar ...
uv run pytest tests/
uv run black .
```

### Using venv (Traditional)
```bash
# Activate venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[dev,test,github]"

# Run commands
python -m sugar ...
pytest tests/
black .
```

## Code Quality

- Make sure to run Black formatting tests before committing work
- Both uv and venv workflows are supported - use whichever you prefer

## Release Process

See [docs/dev/release-process.md](docs/dev/release-process.md) for full details.

**Quick Patch Release (e.g., v2.1.0 → v2.1.1):**
```bash
# 1. Update versions in: pyproject.toml, .claude-plugin/plugin.json
# 2. Update CHANGELOG.md
# 3. Commit, tag, push:
git add -A && git commit -m "chore: Release vX.Y.Z"
git tag vX.Y.Z && git push && git push --tags
# 4. Create GitHub release:
gh release create vX.Y.Z --title "vX.Y.Z" --notes "Release notes"
```

**MCP Server (npm):** If MCP server changed, also publish:
```bash
cd packages/mcp-server && npm login && npm publish
```