# GitHub Label Filtering Options

Sugar provides flexible label filtering options to control which GitHub issues it works on.

## Configuration Options

### 1. Work on ALL Issues (No Filtering)
```yaml
github:
  issue_labels: []  # Empty list = no filtering
```
**Behavior**: Sugar will work on ALL open issues regardless of labels.

### 2. Work on Issues with ANY Labels
```yaml
github:
  issue_labels: ["*"]  # Wildcard
```
**Behavior**: Sugar will work on issues that have at least one label, but skip unlabeled issues.

### 3. Work on UNLABELED Issues Only
```yaml
github:
  issue_labels: ["unlabeled"]  # Special keyword
```
**Behavior**: Sugar will only work on issues that have no labels.

### 4. Work on Specific Labels
```yaml
github:
  issue_labels: ["bug", "enhancement", "good-first-issue"]
```
**Behavior**: Sugar will work on issues that have at least one of the specified labels.

## Default Configuration

By default, `sugar init` sets up no label filtering:
```yaml
issue_labels: []  # Work on ALL open issues
```

This ensures Sugar can work on any open issue without requiring specific labeling practices.

## Examples

### High-Activity Repository
For repositories with many issues, you might want to focus on specific types:
```yaml
issue_labels: ["bug", "critical", "good-first-issue"]
```

### Personal Projects
For personal projects where you want Sugar to help with everything:
```yaml
issue_labels: []  # Work on all issues
```

### Organized Workflow
If you use labels to organize work priority:
```yaml
issue_labels: ["high-priority", "urgent", "next-release"]
```

### Focus on Maintenance
To have Sugar focus only on maintenance tasks:
```yaml
issue_labels: ["bug", "performance", "security"]
```

## Debug Information

When running Sugar with `--debug`, you'll see which label filtering mode is active:
```
🏷️ Label filtering: ALL open issues (no label restrictions)
🏷️ Label filtering: Issues with ANY labels (excluding unlabeled)
🏷️ Label filtering: Only UNLABELED issues
🏷️ Label filtering: Issues with labels: ['bug', 'enhancement']
```

## Migration from Previous Versions

If you have an existing Sugar configuration with the old default labels, you can:

1. **Keep current behavior**: Leave your existing label configuration
2. **Work on all issues**: Change to `issue_labels: []`
3. **Focus further**: Add more specific labels to your list

The label filtering is applied with OR logic - issues need to match at least one label in your list.