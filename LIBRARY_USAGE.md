# Claude CCAL - Library Installation and Usage Guide

## Overview

Claude CCAL (Claude Code Autonomous Loop) is now packaged as a reusable Python library that can be installed in any project to provide 24/7 autonomous development capabilities. Each project gets its own isolated CCAL instance with project-specific configuration, database, and logs.

## Installation

### Option 1: Install from Source (Recommended for now)

```bash
# Clone or download the claude-ccal package
git clone <repository-url> claude-ccal

# Install in development mode (allows for easy updates)
cd claude-ccal
pip install -e .

# Or install directly without cloning
pip install -e git+<repository-url>#egg=claude-ccal
```

### Option 2: Future PyPI Installation (Coming Soon)

```bash
pip install claude-ccal
```

## Quick Start

### 1. Initialize CCAL in Your Project

Navigate to any project directory and initialize CCAL:

```bash
cd /path/to/your/project
ccal init
```

This creates:
- `.ccal/` directory with project-specific configuration and database
- `.ccal/config.yaml` - customizable configuration file
- `logs/errors/` directory with sample error log for testing
- Auto-detects Claude CLI location

### 2. Customize Configuration (Optional)

Edit `.ccal/config.yaml` to match your project:

```yaml
ccal:
  dry_run: true  # Set to false when ready for real execution
  
  claude:
    command: "/path/to/claude"  # Auto-detected, but can be customized
    
  discovery:
    error_logs:
      paths:
        - "logs/errors/"      # Your error log directories
        - "logs/feedback/"
        - "app/logs/"
    
    code_quality:
      root_path: "."          # Project root to analyze
      source_dirs: ["src", "lib", "app"]  # Your source directories
      
    github:
      enabled: false          # Enable for GitHub integration
      repo: "owner/repo"      # Your repository
      token: "ghp_..."        # GitHub token
```

### 3. Add Tasks

```bash
# Add various types of tasks
ccal add "Implement user authentication" --type feature --priority 4
ccal add "Fix memory leak in auth module" --type bug_fix --urgent
ccal add "Add unit tests for payments" --type test --priority 3
ccal add "Update API documentation" --type documentation --priority 2
ccal add "Refactor user service" --type refactor --priority 3
```

### 4. Monitor Status

```bash
# Check system status
ccal status

# List pending tasks
ccal list --status pending

# List completed work
ccal list --status completed

# List all tasks
ccal list --status all --limit 20
```

### 5. Start Autonomous Operation

```bash
# Test with dry run first
ccal run --dry-run --once

# Start 24/7 autonomous operation
ccal run

# Run in background
nohup ccal run > ccal-autonomous.log 2>&1 &
```

## Multi-Project Usage

CCAL can be used across multiple projects simultaneously. Each project maintains complete isolation:

### Project A
```bash
cd /path/to/project-a
ccal init
ccal add "Build user dashboard" --type feature
ccal run &  # Start background operation
```

### Project B  
```bash
cd /path/to/project-b  
ccal init
ccal add "Fix payment processing bug" --type bug_fix --urgent
ccal run &  # Independent operation
```

### Project C
```bash
cd /path/to/project-c
ccal init  
ccal add "Add integration tests" --type test
ccal run &  # Separate autonomous loop
```

Each project will have:
- **Isolated configuration**: `.ccal/config.yaml`
- **Separate database**: `.ccal/ccal.db`
- **Independent logs**: `.ccal/ccal.log`
- **Project-specific discovery**: Scans only that project's files

## Directory Structure (Per Project)

```
your-project/
├── src/                    # Your project source
├── tests/                  # Your project tests  
├── logs/                   # Error/feedback logs (optional)
│   └── errors/
├── .ccal/                  # CCAL-specific files (isolated)
│   ├── config.yaml         # Project-specific config
│   ├── ccal.db            # Project-specific database
│   ├── ccal.log           # Project-specific logs
│   ├── context.json       # Claude context (auto-managed)
│   └── backups/           # Database backups
└── .gitignore             # Add .ccal/ to ignore CCAL files
```

## Configuration Best Practices

### Exclude CCAL from Version Control

Add to your `.gitignore`:
```gitignore
# CCAL autonomous development system
.ccal/
```

### Project-Specific Settings

Customize `.ccal/config.yaml` for each project:

**Python Project:**
```yaml
discovery:
  code_quality:
    file_extensions: [".py"]
    excluded_dirs: ["venv", ".venv", "__pycache__", ".pytest_cache"]
  test_coverage:
    source_dirs: ["src", "app"]
    test_dirs: ["tests", "test"]
```

**JavaScript/Node Project:**
```yaml
discovery:
  code_quality:
    file_extensions: [".js", ".ts", ".jsx", ".tsx"]
    excluded_dirs: ["node_modules", "dist", "build"]
  test_coverage:
    source_dirs: ["src", "lib"]
    test_dirs: ["tests", "__tests__", "spec"]
```

**Full-Stack Project:**
```yaml
discovery:
  code_quality:
    file_extensions: [".py", ".js", ".ts", ".jsx", ".tsx"]
    excluded_dirs: ["node_modules", "venv", "dist", "build"]
  test_coverage:
    source_dirs: ["backend", "frontend/src", "api"]
    test_dirs: ["tests", "frontend/tests", "e2e"]
```

## Advanced Usage

### Custom Error Log Integration

CCAL monitors your error logs. Configure paths where your application writes errors:

```yaml
discovery:
  error_logs:
    paths:
      - "logs/errors/"           # Application error logs
      - "logs/feedback/"         # User feedback logs  
      - "monitoring/alerts/"     # Monitoring system alerts
      - "var/log/app/"          # System logs
    patterns:
      - "*.json"                # JSON error files
      - "*.log"                 # Plain text logs
      - "error_*.txt"           # Custom error formats
```

### GitHub Integration

Enable GitHub integration to discover issues and PRs:

```yaml
discovery:
  github:
    enabled: true
    repo: "yourorg/yourproject"
    token: "ghp_your_github_token"  # Create at github.com/settings/tokens
```

CCAL will:
- Monitor open issues for new development tasks
- Check PR feedback for improvement opportunities  
- Prioritize work based on issue labels and urgency

### Background Operation Management

```bash
# Start CCAL as a service
nohup ccal run > ccal.log 2>&1 &
echo $! > ccal.pid

# Stop CCAL
kill $(cat ccal.pid)

# Check if running
ps aux | grep "ccal run"

# Monitor real-time
tail -f .ccal/ccal.log
```

### Multiple Project Monitoring

```bash
#!/bin/bash
# monitor_all_ccal.sh - Monitor all CCAL instances

echo "=== CCAL Status Across All Projects ==="

for project in ~/projects/*; do
  if [ -d "$project/.ccal" ]; then
    echo "📂 Project: $(basename $project)"
    cd "$project"
    ccal status | grep -E "(Total Tasks|Pending|Active|Completed)"
    echo
  fi
done
```

## Troubleshooting

### Common Issues

**CCAL not finding Claude CLI:**
```bash
# Check if Claude CLI is accessible
claude --version

# If not found, install Claude CLI or update config
# Edit .ccal/config.yaml to set correct path:
claude:
  command: "/full/path/to/claude"
```

**No work being discovered:**
```bash
# Check discovery paths exist
ls -la logs/errors/

# Verify configuration
ccal run --validate

# Test with sample error
echo '{"error": "test", "message": "sample error"}' > logs/errors/test.json
ccal run --once --dry-run
```

**Tasks not executing:**
```bash
# Verify dry_run setting in .ccal/config.yaml
ccal run --validate

# Check logs for errors
tail -f .ccal/ccal.log

# Test with single cycle
ccal run --once
```

### Performance Optimization

**For large projects:**
```yaml
discovery:
  code_quality:
    max_files_per_scan: 25  # Reduce for faster scans
    excluded_dirs: [        # Exclude more directories
      "node_modules", "venv", "dist", "build", 
      "coverage", "docs", "examples"
    ]
```

**For projects with many logs:**
```yaml
discovery:
  error_logs:
    max_age_hours: 12       # Only process recent errors
    patterns: ["*.json"]    # Limit to structured logs only
```

## Security Considerations

### Safe Defaults

CCAL starts in **dry-run mode** by default:
- Simulates execution without making real changes
- Safe to test and configure
- Set `dry_run: false` when ready for autonomous operation

### Path Safety

CCAL excludes system paths by default:
```yaml
safety:
  excluded_paths:
    - "/System"      # macOS system files
    - "/usr/bin"     # System binaries  
    - "/etc"         # System configuration
    - ".ccal"        # CCAL's own files
```

### Access Control

- CCAL database and logs are project-local
- No network access except GitHub API (if enabled)
- Uses your existing Claude CLI authentication
- Add `.ccal/` to `.gitignore` to avoid committing sensitive data

## Best Practices

### Development Workflow

1. **Start with dry-run**: Always test CCAL behavior before enabling real execution
2. **Monitor initially**: Watch the first few cycles to ensure proper task discovery
3. **Gradual enablement**: Enable discovery sources one at a time
4. **Regular status checks**: Monitor queue depth and task success rates
5. **Customize priorities**: Adjust task types and priorities for your workflow

### Team Usage

- **Individual instances**: Each team member can run CCAL on their local environment
- **Shared configuration**: Version control the template `.ccal/config.yaml` (without tokens)
- **Different priorities**: Each developer can prioritize different types of work
- **Coordination**: Use GitHub integration to avoid duplicate work

### Production Considerations

- **Staging first**: Test CCAL on staging/dev environments before production
- **Resource limits**: Configure appropriate timeouts and concurrency limits
- **Monitoring**: Set up log monitoring for CCAL operations  
- **Rollback plans**: Ensure you can quickly disable autonomous operation if needed

---

## Summary

Claude CCAL as a library provides:

✅ **Project Isolation** - Each project gets independent CCAL instance  
✅ **Easy Installation** - Simple `ccal init` setup in any project  
✅ **Auto-Configuration** - Detects Claude CLI and sets sensible defaults  
✅ **Cross-Platform** - Works on any system with Python 3.11+ and Claude CLI  
✅ **Safe Defaults** - Starts in dry-run mode for testing  
✅ **Flexible Discovery** - Configurable error logs, code analysis, GitHub integration  
✅ **No Conflicts** - Uses `.ccal/` directory to avoid naming conflicts  
✅ **Multi-Project** - Run autonomous development across multiple projects simultaneously  

This enables truly autonomous development at scale - install once, configure per project, and let Claude Code work 24/7 across your entire development portfolio.