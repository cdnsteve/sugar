# GitHub Marketplace Deployment Guide

This guide covers publishing the Sugar Issue Responder to the GitHub Marketplace.

## Pre-Deployment Checklist

### Required Files (✓ All Present)

- [x] `/action.yml` - Action metadata at repository root
- [x] `/action/Dockerfile` - Docker container definition
- [x] `/action/entrypoint.py` - Action entrypoint script
- [x] `/action/README.md` - Comprehensive action documentation
- [x] `/MARKETPLACE.md` - Marketplace description
- [x] `/LICENSE` - Open source license (MIT)
- [x] `/action/examples/*.yml` - Example workflows

### Action Metadata Requirements

The `action.yml` file must include:
- [x] Name and description
- [x] Author
- [x] Branding (icon and color)
- [x] Inputs with descriptions
- [x] Outputs with descriptions
- [x] Runs configuration

### Documentation Requirements

- [x] Clear description of what the action does
- [x] Setup instructions
- [x] Configuration options documented
- [x] Example workflows
- [x] Troubleshooting guide
- [x] Support/contact information

## Publishing to GitHub Marketplace

### 1. Repository Setup

Ensure your repository is:
- [x] Public
- [x] Has a clear README
- [x] Has a LICENSE file
- [x] Has releases/tags

### 2. Tag a Release

```bash
# Ensure you're on main/master branch
git checkout main
git pull origin main

# Create and push a tag
git tag -a v1.0.0 -m "Release v1.0.0 - Initial GitHub Marketplace release"
git push origin v1.0.0
```

### 3. Publish to Marketplace

1. Go to your repository on GitHub
2. Click "Releases" → "Draft a new release"
3. Choose the tag you just created (v1.0.0)
4. Fill in release notes:

```markdown
## Sugar Issue Responder v1.0.0

AI-powered GitHub issue assistant that automatically analyzes issues and posts helpful responses.

### Features

- 🔍 Intelligent issue analysis using Claude 4
- 📚 Searches codebase for relevant context
- 💬 Auto-posts helpful responses with code references
- 🏷️ Suggests and applies labels
- ⚙️ Fully configurable thresholds and behavior

### Quick Start

```yaml
- uses: roboticforce/sugar@v1
  with:
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

See [action/README.md](action/README.md) for full documentation.

### Requirements

- Anthropic API key
- GitHub Actions enabled

### What's New

- Initial release
- Auto/mention/triage modes
- Confidence-based auto-posting
- Docker-based for consistency
```

4. Check "Publish this Action to the GitHub Marketplace"
5. Choose primary category: **Utilities**
6. Choose additional categories:
   - **Code quality**
   - **Project management**
7. Agree to marketplace terms
8. Click "Publish release"

### 4. Verify Marketplace Listing

After publishing:
1. Go to https://github.com/marketplace
2. Search for "Sugar Issue Responder"
3. Verify listing appears correctly
4. Test installation in a test repository

## Versioning Strategy

Use semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR** - Breaking changes (e.g., 2.0.0)
- **MINOR** - New features, backward compatible (e.g., 1.1.0)
- **PATCH** - Bug fixes, backward compatible (e.g., 1.0.1)

### Version Tags

Users can reference versions:
```yaml
# Specific version (recommended for production)
uses: roboticforce/sugar@v1.0.0

# Major version (gets patches/features automatically)
uses: roboticforce/sugar@v1

# Latest (not recommended)
uses: roboticforce/sugar@main
```

## Post-Publication

### 1. Update Documentation

Add marketplace badge to README.md:
```markdown
[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-Sugar%20Issue%20Responder-blue?logo=github)](https://github.com/marketplace/actions/sugar-issue-responder)
```

### 2. Announce Release

- Blog post
- Twitter/social media
- Reddit (r/github, r/devops)
- Dev.to article
- Product Hunt

### 3. Monitor Usage

Track:
- GitHub Stars
- Marketplace installs
- Issues/feedback
- Feature requests

## Updating the Action

### For Patches (1.0.0 → 1.0.1)

```bash
# Make bug fixes
git commit -am "Fix: description of fix"

# Tag and push
git tag v1.0.1
git push origin v1.0.1

# Create release on GitHub
# Users on @v1 will automatically get the update
```

### For Minor Versions (1.0.0 → 1.1.0)

```bash
# Add new features
git commit -am "Add: description of feature"

# Tag and push
git tag v1.1.0
git push origin v1.1.0

# Create release on GitHub with changelog
```

### For Major Versions (1.0.0 → 2.0.0)

```bash
# Make breaking changes
git commit -am "BREAKING: description of change"

# Tag and push
git tag v2.0.0
git push origin v2.0.0

# Create release with migration guide
# Update major version tag
git tag -f v2
git push -f origin v2
```

## Marketplace Best Practices

### 1. Clear Description

- First sentence explains what it does
- Use keywords (AI, Claude, GitHub, issues, automation)
- Highlight key benefits

### 2. Quality Documentation

- Quick start guide (< 5 minutes)
- Multiple examples
- Troubleshooting section
- Clear input/output documentation

### 3. Responsive Maintenance

- Monitor issues
- Respond to questions quickly
- Fix bugs promptly
- Release updates regularly

### 4. Security

- Never hardcode secrets
- Use BYOK (Bring Your Own Key) model
- Document security considerations
- Keep dependencies updated

### 5. Performance

- Optimize Docker image size
- Cache layers properly
- Minimize API calls
- Document costs

## Testing Before Release

Run through this checklist:

```bash
# 1. Build Docker image
cd action
docker build -t sugar-action:test .

# 2. Run action locally
docker run --rm \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  -e SUGAR_DRY_RUN=true \
  sugar-action:test

# 3. Test in a workflow
# Push to a test branch and trigger workflow

# 4. Verify all examples work
# Test each example workflow in action/examples/

# 5. Run full test suite
cd ..
pytest tests/ -v
black --check .
flake8 .
```

## Support Channels

Set up:
- GitHub Issues for bugs
- GitHub Discussions for questions
- Documentation site
- Email support (optional)

## Metrics to Track

- **Adoption**: Stars, forks, marketplace installs
- **Engagement**: Issues, PRs, discussions
- **Quality**: Test coverage, bug rate
- **Performance**: Action runtime, success rate

## Troubleshooting Publication

### "Action validation failed"

Check:
- action.yml is valid YAML
- All required fields present
- Branding icon/color valid
- Dockerfile paths correct

### "Marketplace agreement needed"

- Ensure you've accepted marketplace terms
- Verify repository is public
- Check organization permissions

### "Tag already exists"

```bash
# Delete and recreate tag
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
git tag v1.0.0
git push origin v1.0.0
```

---

## Ready to Publish?

When ready, run:
```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

Then follow the "Publish to Marketplace" steps above.

Good luck! 🚀
