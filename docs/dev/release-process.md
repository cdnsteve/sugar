# Release Process

Guide for creating releases of Sugar.

## Version Numbering

Sugar follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (0.X.0): New features, backward compatible
- **PATCH** (0.0.X): Bug fixes, backward compatible

## Quick Reference

### Patch Release (e.g., v2.1.0 → v2.1.1)

```bash
# 1. Update versions
# - pyproject.toml: version = "2.1.1"
# - .claude-plugin/plugin.json: "version": "2.1.1"

# 2. Update CHANGELOG.md with release notes

# 3. Commit version bump
git add pyproject.toml .claude-plugin/plugin.json CHANGELOG.md
git commit -m "chore: Release v2.1.1"

# 4. Create and push tag
git tag v2.1.1
git push && git push --tags

# 5. Create GitHub release
gh release create v2.1.1 --title "v2.1.1" --notes-file - <<EOF
## Bug Fixes
- Fix 1 description
- Fix 2 description
EOF
```

### Minor Release (e.g., v2.1.0 → v2.2.0)

Same process as patch, but include new features in changelog.

### Major Release (e.g., v2.1.0 → v3.0.0)

Same process, but:
- Document breaking changes prominently
- Include migration guide if needed
- Consider release candidate (v3.0.0-rc.1) first

## Detailed Steps

### 1. Pre-Release Checklist

- [ ] All tests pass: `pytest tests/`
- [ ] Code formatted: `black sugar/ tests/`
- [ ] No uncommitted changes on main
- [ ] Main branch is up to date: `git pull`

### 2. Update Version Numbers

**pyproject.toml:**
```toml
[project]
version = "X.Y.Z"
```

**.claude-plugin/plugin.json:**
```json
{
  "version": "X.Y.Z"
}
```

**.claude-plugin/marketplace.json** (if version listed):
```json
{
  "plugins": [{
    "version": "X.Y.Z"
  }]
}
```

### 3. Update CHANGELOG.md

Add entry at the top following the existing format:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New feature descriptions

### Changed
- Change descriptions

### Fixed
- Bug fix descriptions

### Removed
- Removed feature descriptions
```

### 4. Commit the Release

```bash
git add pyproject.toml .claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md
git commit -m "chore: Release vX.Y.Z"
```

### 5. Create Git Tag

```bash
git tag vX.Y.Z
```

### 6. Push to GitHub

```bash
git push origin main
git push origin vX.Y.Z
# Or push all tags: git push --tags
```

### 7. Create GitHub Release

```bash
gh release create vX.Y.Z \
  --title "vX.Y.Z" \
  --notes "Release notes here"
```

Or use `--notes-file` for longer notes:

```bash
gh release create vX.Y.Z \
  --title "vX.Y.Z - Release Title" \
  --notes-file release-notes.md
```

### 8. Verify Release

- [ ] Check GitHub releases page
- [ ] Verify tag appears in repository
- [ ] Test installation: `pip install sugarai==X.Y.Z` (after PyPI publish)

## PyPI Publishing (if applicable)

If publishing to PyPI:

```bash
# Build package
python -m build

# Upload to PyPI
python -m twine upload dist/*
```

## Rollback

If a release needs to be rolled back:

```bash
# Delete the tag locally and remotely
git tag -d vX.Y.Z
git push origin --delete vX.Y.Z

# Delete the GitHub release via web UI or:
gh release delete vX.Y.Z --yes
```

## Release Notes Template

```markdown
## What's New

Brief summary of the release.

### New Features
- Feature 1
- Feature 2

### Bug Fixes
- Fix 1 (#issue-number)
- Fix 2 (#issue-number)

### Breaking Changes
- Change 1 (if any)

### Upgrade Notes
- Any special upgrade instructions
```
