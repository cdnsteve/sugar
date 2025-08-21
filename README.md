# Sugar - AI-Powered Autonomous Development System

A lightweight autonomous development system specifically designed for Claude Code CLI integration that can be installed as a library in any project.

## 🚀 Quick Start

### Installation

```bash
# Install from source (recommended for now)
pip install -e git+<repository-url>#egg=sugar

# Or clone and install locally
git clone <repository-url> sugar
cd sugar
pip install -e .
```

### Initialize in Your Project

```bash
cd /path/to/your/project
sugar init
```

### Add Some Work

```bash
sugar add "Implement user authentication" --type feature --priority 4
sugar add "Fix memory leak in auth module" --type bug_fix --urgent
sugar add "Add unit tests for payments" --type test --priority 3
```

### Start Autonomous Development

```bash
# Test with dry run first
sugar run --dry-run --once

# Start 24/7 autonomous operation
sugar run
```

## 🎯 What Sugar Does

Sugar continuously:
- 🔍 **Discovers work** from error logs, feedback, and GitHub issues
- ⚡ **Executes tasks** using Claude Code CLI
- 🧠 **Learns and adapts** from results
- 🔄 **Repeats autonomously** without human intervention

## 📁 Project Isolation

Each project gets its own isolated Sugar instance:

```
your-project/
├── src/                    # Your project source
├── .sugar/                  # Sugar-specific files (isolated)
│   ├── config.yaml         # Project-specific config
│   ├── sugar.db            # Project-specific database
│   ├── sugar.log           # Project-specific logs
│   └── context.json       # Claude context
└── logs/errors/           # Your error logs (monitored)
```

## 🔧 Configuration

Auto-generated `.sugar/config.yaml` with sensible defaults:

```yaml
sugar:
  # Core Loop Settings
  loop_interval: 300  # 5 minutes between cycles
  max_concurrent_work: 3  # Execute multiple tasks per cycle
  dry_run: true       # Start in safe mode - change to false when ready
  
  # Claude Code Integration
  claude:
    command: "/path/to/claude"  # Auto-detected Claude CLI path
    timeout: 1800       # 30 minutes max per task
    context_file: ".sugar/context.json"
    
  # Work Discovery
  discovery:
    error_logs:
      enabled: true
      paths: ["logs/errors/", "logs/feedback/", ".sugar/logs/"]
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
      excluded_dirs: ["node_modules", ".git", "__pycache__", "venv", ".venv", ".sugar"]
      max_files_per_scan: 50
      
    test_coverage:
      enabled: true
      root_path: "."
      source_dirs: ["src", "lib", "app", "api", "server"]
      test_dirs: ["tests", "test", "__tests__", "spec"]
      
  # Storage
  storage:
    database: ".sugar/sugar.db"  # Project-specific database
    backup_interval: 3600  # 1 hour
    
  # Safety
  safety:
    max_retries: 3
    excluded_paths:
      - "/System"
      - "/usr/bin"
      - "/etc"
      - ".sugar"
    
  # Logging
  logging:
    level: "INFO"
    file: ".sugar/sugar.log"  # Project-specific logs
```

## 📋 Command Reference

### Task Management
```bash
# Add tasks with different types and priorities
sugar add "Task title" [--type TYPE] [--priority 1-5] [--urgent] [--description DESC]

# Types: bug_fix, feature, test, refactor, documentation
# Priority: 1 (low) to 5 (urgent)

# List tasks
sugar list [--status STATUS] [--type TYPE] [--limit N]

# View specific task details
sugar view TASK_ID

# Update existing task
sugar update TASK_ID [--title TITLE] [--description DESC] [--priority 1-5] [--type TYPE] [--status STATUS]

# Remove task
sugar remove TASK_ID

# Check system status
sugar status
```

### System Operation
```bash
# Initialize Sugar in current directory
sugar init [--project-dir PATH]

# Run autonomous loop
sugar run [--dry-run] [--once] [--validate]

# Validate configuration
sugar run --validate
```

## 🔄 Multi-Project Usage

Run Sugar across multiple projects simultaneously:

```bash
# Project A
cd /path/to/project-a
sugar init && sugar run &

# Project B  
cd /path/to/project-b
sugar init && sugar run &

# Project C
cd /path/to/project-c
sugar init && sugar run &
```

Each project operates independently with isolated:
- Configuration and database
- Work queues and execution
- Discovery and learning

## 🛡️ Safety Features

- **Dry run mode** - Simulates execution without making changes (default)
- **Path exclusions** - Prevents system file modifications  
- **Project isolation** - Uses `.sugar/` directory to avoid conflicts
- **Timeout handling** - Prevents runaway processes
- **Auto-detection** - Finds Claude CLI automatically
- **Graceful shutdown** - Handles interrupts cleanly

## 💾 Storage & Context

Sugar maintains project-specific data isolation:

- **Project Database**: `.sugar/sugar.db` stores all task data, execution history, and learning
- **Context Management**: `.sugar/context.json` preserves Claude Code session context
- **Automated Backups**: Regular database backups with configurable intervals
- **Isolated Logs**: Project-specific logging in `.sugar/sugar.log`

Each Sugar instance is completely isolated - you can run multiple projects simultaneously without interference.

## 🔍 Work Discovery

Sugar automatically finds work from:

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

Track Sugar across all your projects:

```bash
# Check status
sugar status

# Monitor logs
tail -f .sugar/sugar.log

# List recent work
sugar list --status completed --limit 10

# Background operation
nohup sugar run > sugar-autonomous.log 2>&1 &
```

## 🎛️ Advanced Usage

### Custom Error Integration

Configure Sugar to monitor your application's error logs:

```yaml
discovery:
  error_logs:
    paths:
      - "logs/errors/"
      - "monitoring/alerts/"
      - "var/log/myapp/"
```

### Team Workflow

1. Each developer runs Sugar locally
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
# Edit .sugar/config.yaml if needed
```

**No work discovered:**
```bash
# Check paths exist
ls -la logs/errors/

# Validate configuration  
sugar run --validate

# Test with sample error
echo '{"error": "test"}' > logs/errors/test.json
```

**Tasks not executing:**
```bash
# Check dry_run setting
cat .sugar/config.yaml | grep dry_run

# Monitor logs
tail -f .sugar/sugar.log

# Test single cycle
sugar run --once
```

## 📚 Documentation

- [**Library Usage Guide**](LIBRARY_USAGE.md) - Comprehensive installation and usage
- [**CLI Documentation**](sugar-planning/Sugar_CLI_Documentation.md) - Complete command reference  
- [**Architecture Plan**](sugar-planning/Sugar_Architecture_Plan.md) - System design and components
- [**24/7 Strategy**](sugar-planning/24_7_Autonomous_Developer_Strategy.md) - Autonomous operation guide

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
3. Check logs in `.sugar/sugar.log`
4. Follow existing code patterns
5. Update documentation for new features

## 📄 License

MIT License - see LICENSE file for details.

---

**Claude Sugar v0.1.0** - Built for Claude Code CLI autonomous development across any project or codebase.

*Transform any project into an autonomous development environment with just `sugar init`.*