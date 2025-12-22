# Contributing to Sugar Issue Responder

Thank you for your interest in improving the Sugar Issue Responder action!

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/sugar.git
   cd sugar
   ```

2. **Install dependencies**
   ```bash
   # Using uv (recommended)
   uv pip install -e ".[dev,test,github]"

   # Or using pip
   pip install -e ".[dev,test,github]"
   ```

3. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

## Action Structure

```
action/
├── Dockerfile          # Docker container definition
├── entrypoint.py       # Main action entrypoint
├── action.yml          # Action metadata (copied to root)
├── README.md           # Action documentation
├── CONTRIBUTING.md     # This file
└── examples/           # Example workflows
    ├── basic.yml
    ├── advanced.yml
    ├── dry-run.yml
    └── cost-optimized.yml
```

## Testing the Action

### Local Testing

1. **Build the Docker image**
   ```bash
   cd action
   docker build -t sugar-action:dev .
   ```

2. **Test with a mock event**
   ```bash
   # Create a test event
   cat > /tmp/event.json << 'EOF'
   {
     "action": "opened",
     "issue": {
       "number": 1,
       "title": "Test Issue",
       "body": "Test body",
       "state": "open",
       "user": {"login": "testuser"},
       "labels": []
     },
     "repository": {"full_name": "test/repo"}
   }
   EOF

   # Run the action
   docker run --rm \
     -e ANTHROPIC_API_KEY=your-key \
     -e GITHUB_TOKEN=your-token \
     -e GITHUB_EVENT_PATH=/tmp/event.json \
     -e SUGAR_DRY_RUN=true \
     -v /tmp:/tmp \
     sugar-action:dev
   ```

### CI Testing

The action is tested automatically via `.github/workflows/test-action.yml`:
- **Validation** - Checks action.yml syntax and structure
- **Docker Build** - Ensures the Docker image builds successfully
- **Dry Run** - Tests action logic without posting
- **Linting** - Code quality checks

## Making Changes

### Modifying the Action Logic

1. Edit `action/entrypoint.py`
2. Update tests if needed
3. Test locally with Docker
4. Submit a PR

### Updating the Profile

The core issue analysis logic is in `sugar/profiles/issue_responder.py`:

1. Edit the profile
2. Add tests in `tests/profiles/test_issue_responder.py`
3. Run tests: `pytest tests/profiles/`

### Adding New Features

For new inputs/outputs:

1. Update `action.yml` (and copy to root)
2. Update `action/entrypoint.py` to read the new inputs
3. Update `action/README.md` documentation
4. Add example workflows in `action/examples/`

## Code Quality

### Formatting

```bash
# Format code
black action/entrypoint.py sugar/profiles/issue_responder.py

# Check formatting
black --check .
```

### Linting

```bash
# Lint code
flake8 action/entrypoint.py --max-line-length=88
flake8 sugar/profiles/issue_responder.py --max-line-length=88
```

### Type Checking

```bash
mypy action/entrypoint.py
```

## Testing

### Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/profiles/test_issue_responder.py -v

# Run with coverage
pytest tests/ --cov=sugar --cov-report=html
```

### Integration Tests

```bash
# Test the full action workflow
pytest tests/integration/test_action.py -v
```

## Documentation

Update documentation when making changes:

- `action/README.md` - Action usage and configuration
- `MARKETPLACE.md` - Marketplace description
- `action/examples/` - Example workflows
- Code comments and docstrings

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, tested code
   - Follow existing code style
   - Add/update documentation

3. **Test thoroughly**
   ```bash
   # Run all checks
   black --check .
   flake8 .
   pytest tests/ -v
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add feature: description"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a PR on GitHub.

## PR Checklist

- [ ] Code follows project style guidelines
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] Example workflows added/updated (if applicable)
- [ ] Changelog updated (for significant changes)
- [ ] PR description explains what and why

## Release Process

Maintainers handle releases:

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Tag release: `git tag v1.2.3`
4. Push tag: `git push origin v1.2.3`
5. GitHub Actions publishes to PyPI and Docker registry

## Questions?

- [Open an issue](https://github.com/roboticforce/sugar/issues)
- [Discussion forum](https://github.com/roboticforce/sugar/discussions)
- Read the [main contributing guide](../docs/dev/contributing.md)

---

Thank you for contributing to Sugar! 🍰
