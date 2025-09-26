# Sugar 🍰 - AI-Powered Autonomous Development System

**Think of it as having an AI development team that works independently on substantial features while you focus on planning and strategic decisions.**

## Overview

Sugar is an autonomous AI development system that integrates with Claude Code to handle complex, multi-step development tasks. Instead of manually implementing every feature and fix, you create comprehensive task specifications, and Sugar executes them autonomously using specialized AI agents.

## How It Works

**Claude Code → Sugar Workflow:**

1. **User identifies need** → 2. **Claude analyzes & plans** → 3. **Claude creates Sugar task** → 4. **Sugar executes autonomously** → 5. **Results delivered**

## Task Creation Strategy

Sugar works best with **rich task context** that includes comprehensive metadata:

```bash
./venv/bin/sugar add "Feature Title" --json --description '{
  "priority": 1-5,
  "type": "feature|bug_fix|test|refactor",
  "context": "Detailed description of what needs to be done and why",
  "business_context": "Strategic importance and business value",
  "technical_requirements": ["specific technical constraints"],
  "agent_assignments": {
    "ux_design_specialist": "UI/UX design leadership",
    "backend_developer": "Server architecture",
    "qa_test_engineer": "Testing and validation"
  },
  "success_criteria": ["measurable outcomes"],
  "requirements": ["specific deliverables"]
}'
```

## Specialized Agent Assignments

Sugar leverages different Claude agents for different aspects of complex development work:

- **ux-design-specialist** → UI/UX design, customer experience
- **backend-developer** → Server architecture, database design
- **frontend-developer** → User-facing applications, customer portals
- **qa-test-engineer** → Testing, quality assurance, validation
- **tech-lead** → Architecture decisions, strategic analysis

## Why This Approach Works

1. **Comprehensive Planning** - Rich context ensures Sugar understands business and technical requirements
2. **Agent Specialization** - Different experts handle different aspects (UX, backend, QA)
3. **Quality Assurance** - Every task includes mandatory testing and code review
4. **Strategic Focus** - Handle enterprise-level features while maintaining professional quality

## Benefits

**For Development Teams:**
- **Autonomous Execution** - Sugar handles complex implementation while you focus on strategy
- **Consistent Quality** - QA agents ensure comprehensive testing
- **Specialized Expertise** - UX, backend, frontend agents provide domain expertise

**For Complex Projects:**
- **Multi-step Features** - Handle substantial development work across weeks
- **Professional Polish** - Specialized agents ensure production-ready quality
- **Enterprise Capabilities** - Support complex business requirements and technical constraints

## Key Features

- 🧠 **Rich Task Context** - Business and technical requirements with success criteria
- 🎯 **Agent Specialization** - UX, backend, frontend, QA experts for different aspects
- 🤖 **Autonomous Execution** - Handles complex, multi-step development work
- 📊 **Quality Assurance** - Built-in testing and code review workflows
- 🔧 **Enterprise Ready** - Production-quality results for substantial features

## 🚀 Quick Start

### Prerequisites

**Required:** Sugar requires Claude Code CLI to be installed and accessible.

1. **Install Claude Code CLI** (if not already installed):
   - Visit [Claude Code CLI documentation](https://docs.anthropic.com/en/docs/claude-code) for installation instructions
   - Or install via npm: `npm install -g @anthropic-ai/claude-code-cli`
   - Verify installation: `claude --version`

2. **Ensure Claude CLI is in your PATH** or note its location for configuration

⚠️ **Important:** Sugar task management (add, list, view) works perfectly **within** Claude Code sessions. However, the autonomous execution (`sugar run`) should be started separately in your terminal, not from within Claude Code.

### Installation

**Install from PyPI (recommended):**

```bash
pip install sugarai
```

**Or install from source for latest development version:**

```bash
# Method 1: Clone and install (recommended for development)
git clone https://github.com/cdnsteve/sugar.git
cd sugar
pip install -e .

# Method 2: Direct from Git (SSH) - Always use main branch
pip install -e git+ssh://git@github.com/cdnsteve/sugar.git@main#egg=sugar
```

📖 **Detailed setup instructions:** [Local Development Setup](docs/dev/local-development.md)

### Initialize in Your Project

```bash
cd /path/to/your/project
sugar init
```

**Note:** Sugar will auto-detect your Claude CLI installation. If it's not in your PATH, you can specify the location in `.sugar/config.yaml` after initialization.

### Create Tasks

**Simple tasks:**
```bash
sugar add "Implement user authentication" --type feature --priority 4
sugar add "Fix memory leak in auth module" --type bug_fix --urgent
```

**Complex features with rich context:**
```bash
sugar add "User Dashboard Redesign" --json --description '{
  "priority": 5,
  "type": "feature",
  "context": "Complete overhaul of user dashboard for better UX",
  "business_context": "Improve user engagement and reduce support tickets",
  "technical_requirements": ["responsive design", "accessibility compliance"],
  "agent_assignments": {
    "ux_design_specialist": "UI/UX design leadership",
    "frontend_developer": "Implementation and optimization",
    "qa_test_engineer": "Testing and validation"
  },
  "success_criteria": ["mobile responsive", "passes accessibility audit"]
}'
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

## What Sugar Does

**Manual Task Creation (Primary Use):**
- Create comprehensive tasks with business context and technical requirements
- Assign specialized agents for different aspects (UX, backend, QA)
- Define success criteria and deliverables
- Execute complex, multi-step development work autonomously

**Autonomous Discovery (Secondary):**
- Discover work from GitHub issues and error logs
- Analyze code quality and identify improvements
- Create and execute tasks automatically
- Update GitHub issues with progress and completion status

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
    
    # Agent Integration (v1.2.0+)
    use_structured_requests: true  # Enable structured JSON communication
    enable_agents: true        # Enable Claude agent mode selection
    agent_fallback: true       # Fall back to basic Claude if agent fails
    agent_selection:           # Map work types to specific agents
      bug_fix: "tech-lead"           # Strategic analysis for bug fixes
      feature: "general-purpose"     # General development for features
      refactor: "code-reviewer"      # Code review expertise for refactoring
      test: "general-purpose"        # General development for tests
      documentation: "general-purpose"  # General development for docs
    # available_agents: []       # Optional: specify which agents are available
                                # If empty, Sugar accepts any agent name
    
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

## 🤖 Claude Agent Integration

**Sugar v1.2.0+ includes advanced Claude agent integration with dynamic agent discovery!**

Sugar intelligently selects the best Claude agent for each task based on work characteristics, and supports **any agents you have configured locally** - not just built-in ones.

### 🎯 Intelligent Agent Selection

Sugar automatically analyzes your work items and selects the optimal agent:

```bash
# High-priority security bug → tech-lead agent
sugar add --type bug_fix --priority 5 --title "Critical auth vulnerability"

# Code refactoring → code-reviewer agent  
sugar add --type refactor --title "Clean up legacy payment code"

# Social media content → social-media-growth-strategist agent
sugar add --type documentation --title "Create LinkedIn content for developer audience"

# Standard feature → general-purpose agent
sugar add --type feature --title "Add user profile settings"
```

### 🔧 Agent Configuration

Configure agents in `.sugar/config.yaml`:

```yaml
claude:
  # Structured Request System
  use_structured_requests: true
  
  # Agent Selection System
  enable_agents: true        # Enable agent mode selection
  agent_fallback: true       # Fall back to basic Claude if agent fails
  
  # Map work types to specific agents (built-in or custom)
  agent_selection:
    bug_fix: "tech-lead"                    # Built-in agent
    feature: "my-frontend-specialist"       # Your custom agent
    refactor: "code-reviewer"               # Built-in agent  
    test: "general-purpose"                 # Built-in agent
    documentation: "technical-writer"       # Your custom agent
  
  # Dynamic Agent Discovery - specify your available agents
  available_agents: [
    "tech-lead",                 # Built-in agents
    "code-reviewer", 
    "general-purpose",
    "my-frontend-specialist",    # Your custom agents
    "technical-writer",
    "database-expert",
    "security-specialist"
  ]
  
  # If available_agents is empty/unspecified, Sugar accepts any agent name
```

### 🌟 Built-in Agent Types

Sugar includes intelligent selection for these built-in agents:

| Agent | Best For | Keywords |
|-------|----------|----------|
| **tech-lead** | Strategic analysis, architecture, complex bugs, high-priority work | architecture, design, strategy, security, critical |
| **code-reviewer** | Code quality, refactoring, optimization, best practices | review, refactor, cleanup, optimize, code quality |
| **social-media-growth-strategist** | Content strategy, engagement, audience growth | social media, content, engagement, followers |
| **general-purpose** | Standard development work (features, tests, docs) | Default for most tasks |
| **statusline-setup** | Claude Code status line configuration | statusline, status line |
| **output-style-setup** | Claude Code output styling and themes | output style, styling, theme |

### 🚀 Custom Agent Support

**Sugar supports ANY agents you have configured locally!** Examples:

```yaml
claude:
  agent_selection:
    bug_fix: "my-security-expert"      # Your custom security agent
    feature: "frontend-guru"           # Your custom frontend agent
    refactor: "performance-wizard"     # Your custom performance agent
    database: "sql-specialist"        # Your custom database agent
```

### 🧠 How Agent Selection Works

1. **User Configuration First**: Checks your `agent_selection` mapping
2. **Keyword Analysis**: Uses intelligent keyword matching as fallback
3. **Availability Validation**: Ensures selected agent is in your `available_agents` list  
4. **Graceful Fallback**: Falls back to available alternatives if needed
5. **Quality Assessment**: Tracks agent performance with 0.0-1.0 quality scores

### 📊 Agent Performance Tracking

Sugar provides detailed analytics for agent performance:

```bash
# View work with timing and agent information
sugar list
# 📋 20 Tasks (16 pending ⏳, 2 completed ✅, 1 active ⚡, 1 failed ❌):
# ⏱️ 45.2s | 🕐 2m 15s | 🤖 tech-lead | Critical auth fix

sugar view TASK_ID
# Shows: agent used, quality score, confidence level, execution time
```

### 🔄 Fallback Strategy

Sugar uses a robust multi-layer fallback system:

1. **Selected Agent** (from configuration or keyword analysis)
2. **Basic Claude** (if agent fails)  
3. **Legacy Mode** (if structured requests fail)

This ensures your work **never fails** due to agent issues.

### ⚙️ Migration from v1.1.x

Existing Sugar installations automatically get agent support with **zero breaking changes**:

- All existing configurations continue working unchanged
- Agents are **opt-in** - set `enable_agents: false` to disable
- Without agent configuration, Sugar uses intelligent defaults

## 📋 Command Reference

### Task Management
```bash
# Add tasks with different types and priorities
sugar add "Task title" [--type TYPE] [--priority 1-5] [--urgent] [--description DESC]

# Default Types: bug_fix, feature, test, refactor, documentation
# Custom types can be added - see Task Type Management section below
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

### 🎯 Task Type Management (v1.8.0+)

Sugar now supports **custom configurable task types**! Create your own types beyond the defaults:

```bash
# List all task types (default + custom)
sugar task-type list

# Add custom task type
sugar task-type add database_migration \
  --name "Database Migration" \
  --description "Schema and data migration tasks" \
  --agent "tech-lead" \
  --commit-template "migrate: {title}" \
  --emoji "🗃️"

# Show task type details
sugar task-type show database_migration

# Edit existing task type
sugar task-type edit database_migration --emoji "🗄️"

# Use custom type in tasks
sugar add "Migrate user schema" --type database_migration --priority 4

# Export/import for version control
sugar task-type export > my-task-types.json
sugar task-type import < my-task-types.json

# Remove custom types (safety: can't delete defaults or types with active tasks)
sugar task-type remove database_migration --force
```

**Popular Custom Task Types:**
- `security_audit` - Security vulnerability scanning
- `hotfix` - Critical production fixes
- `deployment` - Deployment and infrastructure tasks
- `performance` - Performance optimization work
- `maintenance` - System maintenance and cleanup

### 🆕 Complex Data Input (v1.7.6+)

Sugar now supports **rich JSON task data** for seamless Claude Code integration:

```bash
# 📁 JSON file input - perfect for complex tasks
sugar add "API Implementation" --input-file /path/to/task.json

# 📥 Stdin input - ideal for Claude Code slash commands
echo '{"priority": 5, "context": {"complexity": "high"}}' | sugar add "Critical Fix" --stdin

# 🔧 JSON description parsing - structured task descriptions
sugar add "Database Migration" --json --description '{"tables": ["users"], "rollback": true}'
```

**Benefits for external tool integration:**
- 🚫 **No shell escaping issues** - complex strings, quotes, and special characters work perfectly
- 📊 **Full data preservation** - nested objects, arrays, and metadata maintain structure
- 🤖 **Claude Code ready** - slash commands can pass rich task data without fragility
- 🔗 **Programmatic integration** - scripts and tools can create detailed tasks effortlessly

📖 **Complete examples and documentation:** [CLI Reference - Complex Data Input](docs/user/cli-reference.md#complex-data-examples)

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

# List recent work for current project (shows status summary)
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
- ✅ **Phase 4**: PyPI package distribution (available as `sugarai`)
- 📋 **Phase 5**: Enhanced integrations (Slack, Jira, monitoring systems)
- 📋 **Phase 6**: Team coordination and conflict resolution

## 🤝 Contributing

### 🧪 Testing & Quality Assurance

Sugar has comprehensive test suites to ensure reliability:

```bash
# Install development dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest tests/ -v

# Run specific test suites
pytest tests/test_task_types.py -v              # Task type system tests
pytest tests/test_cli.py -v                     # CLI command tests
pytest tests/test_storage.py -v                 # Database tests

# Run with coverage
pytest tests/ --cov=sugar --cov-report=html

# Performance and integration tests
pytest tests/ -m "not slow"                     # Skip slow tests
pytest tests/test_task_types.py::TestTaskTypeCLI -v  # CLI integration tests
```

**Test Categories:**
- **Unit Tests**: Core functionality and business logic
- **Integration Tests**: CLI commands and database operations
- **Migration Tests**: Database schema changes and backwards compatibility
- **Performance Tests**: CLI response times and memory usage
- **End-to-End Tests**: Full workflow validation

### 📝 Development Guidelines

1. **Functional Testing**: Test changes with `--dry-run` and `--once`
2. **Configuration**: Validate configuration with `--validate`
3. **Debugging**: Check logs in `.sugar/sugar.log`
4. **Code Style**: Follow existing patterns and run Black formatting
5. **Test Coverage**: Write tests for new features (aim for >80% coverage)
6. **Documentation**: Update docs and examples for new features
7. **CI Validation**: All tests must pass before merging

### 🚀 Continuous Integration

Sugar uses GitHub Actions for automated testing:
- **Multi-platform**: Tests on Ubuntu, macOS, Windows
- **Python versions**: 3.8, 3.9, 3.10, 3.11, 3.12
- **CLI Regression Tests**: Smoke tests for critical workflows
- **Performance Monitoring**: Track command response times

## ⚖️ Legal and Disclaimers

### Terms of Service
By using Sugar, you agree to our [Terms of Service and Disclaimer](TERMS.md), which includes:
- **No Warranty**: Software provided "AS IS" without warranties of any kind
- **Limitation of Liability**: No responsibility for code damage, data loss, or system issues
- **User Responsibility**: Users must review all AI-generated code before use
- **Security**: Never use on production systems without proper testing and safeguards

### Trademark Notice
Sugar is an independent third-party tool. "Claude," "Claude Code," and related marks are trademarks of Anthropic, Inc. Sugar is not affiliated with, endorsed by, or sponsored by Anthropic, Inc.

### Risk Acknowledgment
- AI-generated code may contain errors or security vulnerabilities
- Always review and test generated code in safe environments
- Maintain proper backups of your projects
- Use appropriate security measures for your development environment

## 📄 License

MIT License with additional disclaimers - see [LICENSE](LICENSE) and [TERMS.md](TERMS.md) for complete details.

---

**Sugar 🍰 v1.9.1** - Built for Claude Code CLI autonomous development across any project or codebase.

*Transform any project into an autonomous development environment with just `sugar init`. ✨ 🍰 ✨*

---

> ⚠️ **IMPORTANT DISCLAIMER**: By installing and using Sugar, you agree to the [Terms of Service and Disclaimer](TERMS.md). Sugar is provided "AS IS" without warranty. Users are solely responsible for reviewing AI-generated code and ensuring appropriate safeguards. Sugar is not affiliated with or endorsed by Anthropic, Inc. "Claude" and "Claude Code" are trademarks of Anthropic, Inc.