# Sugar - AI-Powered Autonomous Development System

**An intelligent autonomous development assistant that works 24/7 to improve your codebase using Claude AI.**

Sugar is a lightweight autonomous development system specifically designed for Claude Code CLI integration that can be installed as a library in any project. It continuously discovers work from GitHub issues, error logs, and code quality analysis, then automatically implements fixes and improvements using Claude's advanced reasoning capabilities.

## ✨ What Makes Sugar Special

- 🤖 **Truly Autonomous**: Runs 24/7 discovering and fixing issues without human intervention
- 🧠 **Claude AI Integration**: Leverages Claude's advanced reasoning for high-quality code changes  
- 🔍 **Smart Discovery**: Automatically finds work from GitHub issues, error logs, and code analysis
- 🎯 **Project-Focused**: Each project gets isolated Sugar instance with custom configuration
- 🔧 **Battle-Tested**: Handles real development workflows with git, GitHub, testing, and deployment
- 📈 **Learning System**: Adapts and improves based on success/failure patterns

## 🚀 Quick Start

### Prerequisites

**Required:** Sugar requires Claude Code CLI to be installed and accessible.

1. **Install Claude Code CLI** (if not already installed):
   - Visit [Claude Code CLI documentation](https://docs.anthropic.com/en/docs/claude-code) for installation instructions
   - Or install via npm: `npm install -g @anthropic-ai/claude-code-cli`
   - Verify installation: `claude --version`

2. **Ensure Claude CLI is in your PATH** or note its location for configuration

⚠️ **Important:** Sugar is designed to run **outside** of Claude Code sessions. Run Sugar directly in your terminal/shell, not within a Claude Code session. Sugar will call Claude Code CLI as needed to execute tasks.

### Installation

**Currently in development - install from source:**

```bash
# Method 1: Clone and install (recommended)
git clone https://github.com/cdnsteve/sugar.git
cd sugar
pip install -e .

# Method 2: Direct from Git (SSH)
pip install -e git+ssh://git@github.com/cdnsteve/sugar.git#egg=sugar
```

📖 **Detailed setup instructions:** [Local Development Setup](docs/dev/local-development.md)

### Initialize in Your Project

```bash
cd /path/to/your/project
sugar init
```

**Note:** Sugar will auto-detect your Claude CLI installation. If it's not in your PATH, you can specify the location in `.sugar/config.yaml` after initialization.

### Add Some Work

```bash
sugar add "Implement user authentication" --type feature --priority 4
sugar add "Fix memory leak in auth module" --type bug_fix --urgent
sugar add "Add unit tests for payments" --type test --priority 3
```

### Get Help Anytime

```bash
# Comprehensive help and quick reference
sugar help

# Command-specific help
sugar add --help
sugar run --help
```

### Start Autonomous Development

```bash
# Test with dry run first
sugar run --dry-run --once

# Start 24/7 autonomous operation
sugar run
```

## 🎯 What Sugar Does

Sugar operates in **two modes**:

### 🤖 Autonomous Discovery
Sugar continuously:
- 🔍 **Discovers work** from error logs, feedback, and GitHub issues
- 📊 **Analyzes code quality** and identifies improvements  
- 🧪 **Detects missing tests** and coverage gaps
- ⚡ **Executes tasks** using Claude Code CLI with full context
- 🌿 **Creates branches & PRs** or commits directly to main (configurable)
- 💬 **Updates GitHub issues** with detailed progress and completion status
- 🧠 **Learns and adapts** from results to improve future performance
- 🔄 **Repeats autonomously** 24/7 without human intervention

### 👤 Manual Task Management
You can also directly add tasks:
- 📝 **Add specific tasks** via `sugar add "task description"`
- 🎯 **Set priorities** and task types (bug_fix, feature, test, etc.)
- 📋 **Manage work queue** with full CLI control
- 🔄 **Combined workflow** - manual tasks + autonomous discovery

## 📁 Clean Project Structure 

Sugar keeps everything contained in `.sugar/` directory - no clutter in your project root!

```
your-project/
├── src/                    # Your project source
├── .sugar/                  # Sugar-specific files (isolated)
│   ├── config.yaml         # Project-specific config
│   ├── sugar.db            # Project-specific database
│   ├── sugar.log           # Project-specific logs
│   └── context.json       # Claude context
├── .gitignore             # Just add: .sugar/
└── logs/errors/           # Your error logs (monitored)
```

**Simple .gitignore:** Just add `.sugar/` to your `.gitignore` - that's it! 
📖 [Complete .gitignore template](docs/user/gitignore-template.md)

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
      issue_labels: []  # No filtering - work on ALL open issues
      workflow:
        auto_close_issues: true
        git_workflow: "direct_commit"  # direct_commit|pull_request
      
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

## 🔍 Work Input Methods

Sugar accepts work from **multiple sources**:

### 📝 Manual CLI Input
Direct task management via command line:
```bash
sugar add "Implement user registration" --type feature --priority 4
sugar add "Fix authentication bug" --type bug_fix --urgent
sugar add "Add API tests" --type test --priority 3
```

### 🤖 Autonomous Discovery
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

### Per-Project Monitoring

Each project has its own isolated Sugar instance. Commands are project-specific:

```bash
# Check status for current project
sugar status

# Monitor logs for current project
tail -f .sugar/sugar.log

# List recent work for current project
sugar list --status completed --limit 10

# Background operation for current project
nohup sugar run > sugar-autonomous.log 2>&1 &
```

### Multi-Project Monitoring

To monitor Sugar across multiple projects, you need to check each project directory:

```bash
# Example script to check all projects
for project in ~/projects/*; do
  if [ -d "$project/.sugar" ]; then
    echo "📂 Project: $(basename $project)"
    cd "$project"
    sugar status | grep -E "(Total Tasks|Pending|Active|Completed)"
    echo
  fi
done
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
# First, check if Claude CLI is installed
claude --version

# If not installed, install it:
npm install -g @anthropic-ai/claude-code-cli

# If installed but not found by Sugar, edit .sugar/config.yaml:
claude:
  command: "/full/path/to/claude"  # Specify exact path
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

- **[Complete Documentation Hub](docs/README.md)** - All Sugar documentation
- **[Quick Start Guide](docs/user/quick-start.md)** - Get up and running in 5 minutes
- **[Local Development Setup](docs/dev/local-development.md)** - Install and test Sugar locally (before PyPI)
- **[GitHub Integration](docs/user/github-integration.md)** - Connect Sugar to GitHub issues and PRs
- **[Installation Guide](docs/user/installation-guide.md)** - Comprehensive installation and usage
- **[CLI Reference](docs/user/cli-reference.md)** - Complete command reference  
- **[Contributing Guide](docs/dev/contributing.md)** - How to contribute to Sugar

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