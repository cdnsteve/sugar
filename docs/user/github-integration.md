# GitHub Integration

How to configure Sugar to discover work from GitHub issues and pull requests.

## 🔧 Authentication Methods

Sugar supports **three authentication methods** for GitHub integration:

### Method 1: GitHub CLI (Recommended)

Uses your existing `gh` CLI authentication - easiest if you already use GitHub CLI.

**Prerequisites:**
```bash
# Install GitHub CLI
# macOS: brew install gh
# Windows: winget install GitHub.cli
# Linux: See https://github.com/cli/cli#installation

# Authenticate with GitHub
gh auth login

# Verify authentication
gh auth status
```

**Configuration:**
```yaml
# .sugar/config.yaml
sugar:
  discovery:
    github:
      enabled: true
      repo: "username/repository"  # Your repository
      auth_method: "gh_cli"        # Use GitHub CLI
      
      gh_cli:
        command: "gh"              # Path to gh command
        use_default_auth: true     # Use existing gh auth
        
      issue_labels: ["bug", "enhancement", "sugar-task"]
      check_interval_minutes: 30
```

**Benefits:**
- ✅ Uses existing `gh` authentication
- ✅ No need to create personal access tokens
- ✅ Supports all GitHub CLI features
- ✅ Easy setup if you already use `gh`

### Method 2: Personal Access Token

Uses a GitHub Personal Access Token for authentication.

**Setup Token:**
1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic) with scopes:
   - `repo` (for private repos) or `public_repo` (for public repos)
   - `read:org` (if accessing organization repos)
3. Copy the token

**Configuration:**
```yaml
# .sugar/config.yaml  
sugar:
  discovery:
    github:
      enabled: true
      repo: "username/repository"
      auth_method: "token"
      token: "ghp_your_token_here"  # Or use environment variable
      
      issue_labels: ["bug", "enhancement"]
      check_interval_minutes: 30
```

**Environment Variable (Recommended):**
```bash
# Set environment variable
export GITHUB_TOKEN="ghp_your_token_here"

# In config, leave token empty - Sugar will use environment variable
token: ""  # Will use $GITHUB_TOKEN
```

**Benefits:**
- ✅ Works without GitHub CLI
- ✅ Fine-grained access control
- ✅ Works in CI/CD environments
- ✅ Can be stored in environment variables

### Method 3: Auto-Detection (Best of Both)

Tries GitHub CLI first, falls back to token if CLI isn't available.

**Configuration:**
```yaml
# .sugar/config.yaml
sugar:
  discovery:
    github:
      enabled: true
      repo: "username/repository"
      auth_method: "auto"  # Try gh CLI first, fallback to token
      
      # Token fallback (optional)
      token: ""  # Or set GITHUB_TOKEN environment variable
      
      gh_cli:
        command: "gh"
        use_default_auth: true
        
      issue_labels: ["bug", "enhancement", "sugar-task"]
```

**Benefits:**
- ✅ Most flexible approach
- ✅ Works with or without GitHub CLI
- ✅ Automatic fallback handling
- ✅ Single configuration for different environments

## 📋 Configuration Options

### Complete GitHub Configuration

```yaml
# .sugar/config.yaml
sugar:
  discovery:
    github:
      enabled: true
      repo: "username/repository"
      auth_method: "auto"  # "token", "gh_cli", or "auto"
      
      # Token authentication (if needed)
      token: ""  # Personal access token or ${GITHUB_TOKEN}
      
      # GitHub CLI authentication
      gh_cli:
        command: "gh"               # Path to gh command
        use_default_auth: true      # Use existing gh authentication
        timeout_seconds: 30         # Command timeout
        
      # Discovery settings
      issue_labels: [               # Labels to monitor
        "bug", 
        "enhancement", 
        "good-first-issue",
        "sugar-task"
      ]
      
      pull_request_labels: [        # PR labels to monitor
        "needs-review",
        "sugar-automation"
      ]
      
      check_interval_minutes: 30    # How often to check GitHub
      max_issues_per_check: 10      # Limit issues processed per cycle
      
      # Issue filtering
      issue_states: ["open"]        # "open", "closed", "all"
      exclude_pull_requests: false  # Whether to ignore PRs
      
      # Assignment handling
      only_unassigned: false        # Only process unassigned issues
      auto_assign: false            # Auto-assign to Sugar when processing
```

### Repository Formats

```yaml
# Public repository
repo: "username/repository"

# Organization repository  
repo: "organization/repository"

# GitHub Enterprise (if supported)
repo: "enterprise.github.com/org/repo"
```

## 🚀 Quick Setup Examples

### Example 1: Simple Setup with GitHub CLI

```bash
# 1. Authenticate with GitHub CLI
gh auth login

# 2. Enable in Sugar config
cat >> .sugar/config.yaml << 'EOF'
sugar:
  discovery:
    github:
      enabled: true
      repo: "myusername/myproject"
      auth_method: "gh_cli"
      issue_labels: ["bug", "enhancement"]
EOF

# 3. Test
sugar run --dry-run --once
```

### Example 2: Token-Based Setup

```bash
# 1. Set environment variable
export GITHUB_TOKEN="ghp_your_token_here"

# 2. Configure Sugar
cat >> .sugar/config.yaml << 'EOF'
sugar:
  discovery:
    github:
      enabled: true
      repo: "myusername/myproject"
      auth_method: "token"
      token: ""  # Uses $GITHUB_TOKEN
      issue_labels: ["bug", "feature-request", "sugar"]
EOF

# 3. Test
sugar run --validate
sugar run --dry-run --once
```

### Example 3: Team/Organization Setup

```yaml
# .sugar/config.yaml for team projects
sugar:
  discovery:
    github:
      enabled: true
      repo: "myorg/backend-services"
      auth_method: "auto"
      
      issue_labels: [
        "bug",
        "tech-debt", 
        "maintenance",
        "sugar-automation"
      ]
      
      # Filter for better team coordination
      only_unassigned: true         # Don't interfere with assigned work
      max_issues_per_check: 5       # Conservative approach
      check_interval_minutes: 60    # Less frequent checks
```

## 🔍 What Sugar Discovers

### From GitHub Issues

Sugar automatically creates tasks from:

- **Open issues** with specified labels
- **Issue descriptions** become task descriptions
- **Issue labels** map to task types:
  - `bug` → `bug_fix` tasks
  - `enhancement`, `feature` → `feature` tasks
  - `documentation` → `documentation` tasks
  - `test`, `testing` → `test` tasks

### From Pull Requests

- **PRs needing review** (configurable labels)
- **Failed CI checks** that need attention
- **Merge conflicts** requiring resolution

### Task Mapping

```
GitHub Issue → Sugar Task
=======================
Title: "Fix login bug"         → Title: "Fix login bug"
Label: "bug"                   → Type: "bug_fix"
Label: "high-priority"         → Priority: 4
Body: "Users can't login..."   → Description: "Users can't login..."
```

## 🛠️ Testing GitHub Integration

### Test Authentication

```bash
# Test GitHub CLI
gh auth status
gh repo view username/repository

# Test token
curl -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/repos/username/repository/issues

# Test Sugar configuration
sugar run --validate
```

### Create Test Issues

```bash
# Create test issue with GitHub CLI
gh issue create \
  --title "Test Sugar Integration" \
  --body "Testing Sugar's GitHub discovery" \
  --label "bug,sugar-task"

# Or via web interface with appropriate labels
```

### Monitor Discovery

```bash
# Run Sugar discovery
sugar run --dry-run --once

# Check logs
tail -f .sugar/sugar.log | grep -i github

# Check discovered tasks
sugar list --type bug_fix
```

## 🚨 Troubleshooting

### "GitHub CLI not found"

```bash
# Check gh installation
which gh
gh --version

# Install GitHub CLI
# macOS: brew install gh
# Windows: winget install GitHub.cli
# Linux: See https://github.com/cli/cli#installation

# Update config with full path if needed
gh_cli:
  command: "/usr/local/bin/gh"
```

### "Authentication failed"

```bash
# Re-authenticate GitHub CLI
gh auth logout
gh auth login

# Or check token
echo $GITHUB_TOKEN
curl -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/user
```

### "Repository not found"

```bash
# Verify repository access
gh repo view username/repository

# Check repository format in config
repo: "username/repository"  # Not: github.com/username/repository
```

### "No issues discovered"

```bash
# Check issue labels
gh issue list --label "bug,enhancement"

# Verify label configuration matches actual labels
issue_labels: ["bug", "enhancement"]  # Must match exactly

# Check issue states
gh issue list --state open
```

### Rate Limiting

```bash
# Check GitHub API rate limits
gh api rate_limit

# Reduce check frequency in config
check_interval_minutes: 60  # Instead of 30
max_issues_per_check: 5     # Instead of 10
```

## 💡 Best Practices

### Security

- **Use environment variables** for tokens
- **Use GitHub CLI** when possible (inherits security)
- **Limit token scopes** to minimum required
- **Rotate tokens** regularly

### Performance

- **Use specific labels** to filter relevant issues
- **Set appropriate intervals** to avoid rate limiting
- **Limit issues per check** for large repositories
- **Monitor API usage** with `gh api rate_limit`

### Team Coordination

- **Use dedicated labels** for Sugar automation
- **Coordinate with team** on which issues Sugar should handle
- **Use `only_unassigned`** to avoid conflicts
- **Set up notifications** for Sugar's GitHub activity

### Example Team Labels

```yaml
issue_labels: [
  "sugar-automation",  # Dedicated Sugar label
  "maintenance",       # Maintenance tasks Sugar can handle
  "tech-debt",        # Technical debt cleanup
  "documentation"     # Documentation updates
]
```

## 🔄 Advanced Usage

### Multi-Repository Setup

```yaml
# Monitor multiple repositories (future feature)
github:
  repositories: [
    {
      repo: "myorg/frontend",
      labels: ["bug", "ui-issue"]
    },
    {
      repo: "myorg/backend", 
      labels: ["bug", "api-issue"]
    }
  ]
```

### Custom Label Mapping

```yaml
# Map GitHub labels to Sugar task types
github:
  label_mapping:
    "bug": "bug_fix"
    "feature": "feature"
    "docs": "documentation"
    "test": "test"
    "refactor": "refactor"
    "urgent": { "type": "bug_fix", "priority": 5 }
```

---

GitHub integration makes Sugar truly autonomous by connecting your development workflow with issue tracking and project management. Choose the authentication method that best fits your setup and team workflow.