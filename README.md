# Claude CCAL - Claude Code Autonomous Loop

A lightweight autonomous development system specifically designed for Claude Code CLI integration that can be installed as a library in any project.

## 🚀 Quick Start

### Installation

```bash
# Install from source (recommended for now)
pip install -e git+<repository-url>#egg=claude-ccal

# Or clone and install locally
git clone <repository-url> claude-ccal
cd claude-ccal
pip install -e .
```

### Initialize in Your Project

```bash
cd /path/to/your/project
ccal init
```

### Add Some Work

```bash
ccal add "Implement user authentication" --type feature --priority 4
ccal add "Fix memory leak in auth module" --type bug_fix --urgent
ccal add "Add unit tests for payments" --type test --priority 3
```

### Start Autonomous Development

```bash
# Test with dry run first
ccal run --dry-run --once

# Start 24/7 autonomous operation
ccal run
```

## 🎯 What CCAL Does

CCAL continuously:
- 🔍 **Discovers work** from error logs, feedback, and GitHub issues
- ⚡ **Executes tasks** using Claude Code CLI
- 🧠 **Learns and adapts** from results
- 🔄 **Repeats autonomously** without human intervention

## 📁 Project Isolation

Each project gets its own isolated CCAL instance:

```
your-project/
├── src/                    # Your project source
├── .ccal/                  # CCAL-specific files (isolated)
│   ├── config.yaml         # Project-specific config
│   ├── ccal.db            # Project-specific database
│   ├── ccal.log           # Project-specific logs
│   └── context.json       # Claude context
└── logs/errors/           # Your error logs (monitored)
```

## 🔧 Configuration

Auto-generated `.ccal/config.yaml` with sensible defaults:

```yaml
ccal:
  # Core Loop Settings
  loop_interval: 300  # 5 minutes between cycles
  max_concurrent_work: 3  # Execute multiple tasks per cycle
  dry_run: true       # Start in safe mode - change to false when ready
  
  # Claude Code Integration
  claude:
    command: "/path/to/claude"  # Auto-detected Claude CLI path
    timeout: 1800       # 30 minutes max per task
    context_file: ".ccal/context.json"
    
  # Work Discovery
  discovery:
    error_logs:
      enabled: true
      paths: ["logs/errors/", "logs/feedback/", ".ccal/logs/"]
      patterns: ["*.json", "*.log"]
      max_age_hours: 24
    
    github:
      enabled: false  # Set to true and configure to enable
      repo: ""  # e.g., "user/repository"
      token: ""  # GitHub token for API access
      
    code_quality:
      enabled: true
      root_path: "."
      file_extensions: [".py", ".js", ".ts", ".jsx", ".tsx"]
      excluded_dirs: ["node_modules", ".git", "__pycache__", "venv", ".venv", ".ccal"]
      max_files_per_scan: 50
      
    test_coverage:
      enabled: true
      root_path: "."
      source_dirs: ["src", "lib", "app", "api", "server"]
      test_dirs: ["tests", "test", "__tests__", "spec"]
      
  # Storage
  storage:
    database: ".ccal/ccal.db"  # Project-specific database
    backup_interval: 3600  # 1 hour
    
  # Safety
  safety:
    max_retries: 3
    excluded_paths:
      - "/System"
      - "/usr/bin"
      - "/etc"
      - ".ccal"
    
  # Logging
  logging:
    level: "INFO"
    file: ".ccal/ccal.log"  # Project-specific logs
```

## 📋 Command Reference

### Task Management
```bash
# Add tasks with different types and priorities
ccal add "Task title" [--type TYPE] [--priority 1-5] [--urgent] [--description DESC]

# Types: bug_fix, feature, test, refactor, documentation
# Priority: 1 (low) to 5 (urgent)

# List tasks
ccal list [--status STATUS] [--type TYPE] [--limit N]

# View specific task details
ccal view TASK_ID

# Update existing task
ccal update TASK_ID [--title TITLE] [--description DESC] [--priority 1-5] [--type TYPE] [--status STATUS]

# Remove task
ccal remove TASK_ID

# Check system status
ccal status
```

### System Operation
```bash
# Initialize CCAL in current directory
ccal init [--project-dir PATH]

# Run autonomous loop
ccal run [--dry-run] [--once] [--validate]

# Validate configuration
ccal run --validate
```

## 🔄 Multi-Project Usage

Run CCAL across multiple projects simultaneously:

```bash
# Project A
cd /path/to/project-a
ccal init && ccal run &

# Project B  
cd /path/to/project-b
ccal init && ccal run &

# Project C
cd /path/to/project-c
ccal init && ccal run &
```

Each project operates independently with isolated:
- Configuration and database
- Work queues and execution
- Discovery and learning

## 🛡️ Safety Features

- **Dry run mode** - Simulates execution without making changes (default)
- **Path exclusions** - Prevents system file modifications  
- **Project isolation** - Uses `.ccal/` directory to avoid conflicts
- **Timeout handling** - Prevents runaway processes
- **Auto-detection** - Finds Claude CLI automatically
- **Graceful shutdown** - Handles interrupts cleanly

## 💾 Storage & Context

CCAL maintains project-specific data isolation:

- **Project Database**: `.ccal/ccal.db` stores all task data, execution history, and learning
- **Context Management**: `.ccal/context.json` preserves Claude Code session context
- **Automated Backups**: Regular database backups with configurable intervals
- **Isolated Logs**: Project-specific logging in `.ccal/ccal.log`

Each CCAL instance is completely isolated - you can run multiple projects simultaneously without interference.

## 🔍 Work Discovery

CCAL automatically finds work from:

### Error Logs
Monitors specified directories for error files:
```yaml
discovery:
  error_logs:
    paths: ["logs/errors/", "app/logs/"]
    patterns: ["*.json", "*.log"]
```

### Code Quality Analysis
Scans source code for improvements:
```yaml
discovery:
  code_quality:
    file_extensions: [".py", ".js", ".ts"]
    excluded_dirs: ["node_modules", "venv"]
```

### Test Coverage Analysis
Identifies missing tests:
```yaml
discovery:
  test_coverage:
    source_dirs: ["src", "lib"]
    test_dirs: ["tests", "spec"]
```

### GitHub Integration (Optional)
Monitors repository issues and PRs:
```yaml
discovery:
  github:
    enabled: true
    repo: "owner/repository"
    token: "ghp_your_token"
```

## 📊 Monitoring

Track CCAL across all your projects:

```bash
# Check status
ccal status

# Monitor logs
tail -f .ccal/ccal.log

# List recent work
ccal list --status completed --limit 10

# Background operation
nohup ccal run > ccal-autonomous.log 2>&1 &
```

## 🎛️ Advanced Usage

### Custom Error Integration

Configure CCAL to monitor your application's error logs:

```yaml
discovery:
  error_logs:
    paths:
      - "logs/errors/"
      - "monitoring/alerts/"
      - "var/log/myapp/"
```

### Team Workflow

1. Each developer runs CCAL locally
2. Share configuration templates (without tokens)
3. Different priorities for different team members
4. GitHub integration prevents duplicate work

### Production Deployment

- Test thoroughly in staging environments
- Monitor resource usage and performance
- Set appropriate concurrency and timeout limits
- Ensure rollback procedures are in place

## 🚨 Troubleshooting

### Common Issues

**Claude CLI not found:**
```bash
claude --version  # Verify installation
# Edit .ccal/config.yaml if needed
```

**No work discovered:**
```bash
# Check paths exist
ls -la logs/errors/

# Validate configuration  
ccal run --validate

# Test with sample error
echo '{"error": "test"}' > logs/errors/test.json
```

**Tasks not executing:**
```bash
# Check dry_run setting
cat .ccal/config.yaml | grep dry_run

# Monitor logs
tail -f .ccal/ccal.log

# Test single cycle
ccal run --once
```

## 📚 Documentation

- [**Library Usage Guide**](LIBRARY_USAGE.md) - Comprehensive installation and usage
- [**CLI Documentation**](ccal-planning/CCAL_CLI_Documentation.md) - Complete command reference  
- [**Architecture Plan**](ccal-planning/CCAL_Architecture_Plan.md) - System design and components
- [**24/7 Strategy**](ccal-planning/24_7_Autonomous_Developer_Strategy.md) - Autonomous operation guide

## 🎯 Use Cases

### Individual Developer
- Continuous bug fixing from error logs
- Automated test creation for uncovered code
- Documentation updates when code changes
- Code quality improvements during idle time

### Development Team
- Shared work discovery across team projects
- Automated issue processing from GitHub
- Continuous integration of feedback loops
- 24/7 development progress across multiple repos

### Product Teams
- Autonomous handling of user feedback
- Automated response to monitoring alerts
- Continuous improvement of code quality metrics
- Proactive maintenance and technical debt reduction

## 🔮 Roadmap

- ✅ **Phase 1**: Core loop, error discovery, basic execution
- ✅ **Phase 2**: Smart discovery (GitHub, code quality, test coverage)  
- ✅ **Phase 3**: Learning and adaptation system
- 🚧 **Phase 4**: PyPI package distribution
- 📋 **Phase 5**: Enhanced integrations (Slack, Jira, monitoring systems)
- 📋 **Phase 6**: Team coordination and conflict resolution

## 🤝 Contributing

1. Test changes with `--dry-run` and `--once`
2. Validate configuration with `--validate`
3. Check logs in `.ccal/ccal.log`
4. Follow existing code patterns
5. Update documentation for new features

## 📄 License

MIT License - see LICENSE file for details.

---

**Claude CCAL v0.1.0** - Built for Claude Code CLI autonomous development across any project or codebase.

*Transform any project into an autonomous development environment with just `ccal init`.*