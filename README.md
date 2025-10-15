# Sugar 🍰

A dev team that never stops.

Delegate full tasks to AI in the background. Sugar builds features, fixes bugs, and ships code while you focus on what matters.

## What It Does

Think of Sugar as **Claude Code with persistence**. Instead of one-off interactions:

- **Continuous execution** - Runs 24/7, working through your task queue
- **Delegate from Claude** - Hand off tasks during interactive sessions
- **Builds features** - Takes specs, implements, tests, commits working code
- **Fixes bugs** - Reads error logs, investigates, implements fixes
- **GitHub integration** - Creates PRs, updates issues, tracks progress
- **Smart discovery** - Finds work from errors, issues, and code analysis

You plan the work. Sugar executes it.

## Install

```bash
pip install sugarai
```

Or use uv (much faster):
```bash
uv pip install sugarai
```

## Quick Start

```bash
# Initialize in your project
cd your-project
sugar init

# Add tasks to the queue
sugar add "Fix authentication timeout" --type bug_fix --urgent
sugar add "Add user profile settings" --type feature

# Start the loop
sugar run
```

Sugar will:
1. Pick up tasks from the queue
2. Execute them using Claude Code
3. Run tests and verify changes
4. Commit working code
5. Move to the next task

It keeps going until the queue is empty (or you stop it).

**Or delegate from Claude Code:**
```
/sugar-task "Fix login timeout" --type bug_fix --urgent
```
Sugar picks it up and works on it while you keep coding.

## Real Example

**Simple tasks:**
```bash
# Quick task creation
sugar add "Fix authentication timeout" --type bug_fix --urgent
sugar add "Add user profile settings" --type feature --priority 4
```

**Complex tasks with rich context** (recommended for best results):
```bash
sugar add "User Dashboard Redesign" --json --description '{
  "priority": 5,
  "type": "feature",
  "context": "Complete overhaul of user dashboard with modern UI/UX patterns",
  "business_context": "User feedback shows dashboard is confusing. Goal: reduce support tickets by 40%",
  "technical_requirements": [
    "React 18 with TypeScript",
    "Responsive design (mobile-first)",
    "Real-time data updates via WebSocket",
    "Accessibility compliance (WCAG 2.1 AA)"
  ],
  "agent_assignments": {
    "ux_design_specialist": "Design system and user flows",
    "frontend_developer": "Implementation and optimization",
    "qa_test_engineer": "Testing and validation"
  },
  "success_criteria": [
    "Dashboard loads in < 2 seconds",
    "Mobile responsive on all breakpoints",
    "Passes accessibility audit",
    "User testing shows 90%+ satisfaction"
  ],
  "requirements": [
    "Dark mode support",
    "Customizable widget layout",
    "Export dashboard data to PDF"
  ]
}'
```

**Why JSON format?** Rich context gives Claude Code everything it needs to build production-quality features autonomously. The more detail you provide, the better the results.

```bash
# Start autonomous mode
sugar run

# Check progress anytime
sugar status
sugar list --status completed

# Sugar handles:
# - Writing the code
# - Running tests
# - Making commits
# - Creating PRs (if configured)
# - Updating GitHub issues
```

## Features

**Task Management**
- Rich task context with priorities and metadata
- Custom task types for your workflow
- Queue management and filtering

**Autonomous Execution**
- Specialized Claude agents (UX, backend, QA)
- Automatic retries on failures
- Quality checks and testing

**GitHub Integration**
- Reads issues, creates PRs
- Updates issue status automatically
- Commits with proper messages

**Smart Discovery**
- Monitors error logs
- Analyzes code quality
- Identifies missing tests
- Auto-creates tasks from findings

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    The Sugar Loop                       │
└─────────────────────────────────────────────────────────┘

  You                    Priority Queue               Sugar
   │                          │                         │
   │  sugar add "task"        │                         │
   ├─────────────────────────>│                         │
   │                          │                         │
   │                          │  Picks highest priority │
   │                          │<────────────────────────┤
   │                          │                         │
   │                          │                         │
   │                     Claude Code                    │
   │                          │                         │
   │                          │  Executes in background │
   │                          │  (uses agents, tests)   │
   │                          │                         │
   │                          ▼                         │
   │                     Completes Work                 │
   │                          │                         │
   │                          │  Commits, updates       │
   │                          │                         │
   │                          │  Back to queue ────────>│
   │                          │                         │
   └──────────────────────────┴─────────────────────────┘
                              ↻ Repeat
```

**The continuous execution loop:**

1. **You assign** - Add tasks with priorities and context
2. **Sugar picks up** - Grabs highest priority work from the queue
3. **Claude Code executes** - Runs in background, uses specialized agents as needed
4. **Completes work** - Tests, commits, moves to next task
5. **Repeat** - Continuous execution until queue is empty

## Configuration

`.sugar/config.yaml` is auto-generated on `sugar init`. Key settings:

```yaml
sugar:
  dry_run: false              # Set to true for testing
  loop_interval: 300          # 5 minutes between cycles
  max_concurrent_work: 3      # Parallel task execution

claude:
  enable_agents: true         # Use specialized Claude agents

discovery:
  github:
    enabled: true
    repo: "user/repository"
  error_logs:
    enabled: true
    paths: ["logs/errors/"]
  code_quality:
    enabled: true
```

## Use Sugar from Claude Code

**Sugar has native Claude Code integration!** Delegate work to Sugar directly from your Claude sessions.

### Install the Plugin

```
/plugin install sugar@cdnsteve
```

### Delegate Work from Claude

**Inside a Claude Code session:**

```
You: "I'm working on authentication but need to fix these test failures.
Can you handle the test fixes while I finish the auth flow?"

Claude: "I'll create a Sugar task for the test fixes so you can keep coding."

/sugar-task "Fix authentication test failures" --type test --urgent
```

**Why this is powerful:** Claude Code handles your interactive work while Sugar autonomously fixes the tests in the background. No context switching.

### Example Workflow

```
You: "Found a memory leak in the cache module. Add it to the queue."

Claude:
/sugar-task "Fix memory leak in cache module" --json --description '{
  "priority": 5,
  "type": "bug_fix",
  "context": "Memory usage grows unbounded in production",
  "technical_requirements": ["Profile memory usage", "Add cleanup cycle"],
  "agent_assignments": {
    "tech_lead": "Investigate root cause and fix"
  }
}'

Task created! You can check progress with /sugar-status
```

### Available Slash Commands

- `/sugar-task` - Create tasks with rich context
- `/sugar-status` - Check queue and progress
- `/sugar-run` - Start autonomous mode
- `/sugar-review` - Review pending tasks
- `/sugar-analyze` - Analyze code for potential work

### MCP Server Integration

Sugar includes an MCP server for advanced integration:

```json
// In your Claude Code MCP settings
{
  "mcpServers": {
    "sugar": {
      "command": "sugar",
      "args": ["mcp"]
    }
  }
}
```

Enables:
- Real-time task queue access
- Direct task manipulation from prompts
- System status monitoring
- Seamless tool integration

## Requirements

- Python 3.11+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)

## Documentation

- **[Quick Start](docs/user/quick-start.md)** - Get running in 5 minutes
- **[CLI Reference](docs/user/cli-reference.md)** - All commands
- **[GitHub Integration](docs/user/github-integration.md)** - Connect to GitHub
- **[Configuration Guide](docs/user/configuration-best-practices.md)** - Best practices
- **[Claude Code Plugin](.claude-plugin/README.md)** - Native integration

## Advanced Usage

**Custom Task Types**
```bash
sugar task-type add deployment --name "Deployment" --emoji "🚀"
sugar add "Deploy to staging" --type deployment
```

**Complex Tasks with Context**
```bash
sugar add "User Dashboard" --json --description '{
  "priority": 5,
  "context": "Complete dashboard redesign",
  "agent_assignments": {
    "ux_design_specialist": "UI/UX design",
    "frontend_developer": "Implementation",
    "qa_test_engineer": "Testing"
  }
}'
```

**Multiple Projects**
```bash
# Run Sugar on multiple projects simultaneously
cd /path/to/project-a && sugar run &
cd /path/to/project-b && sugar run &
cd /path/to/project-c && sugar run &
```

## Troubleshooting

**Sugar not finding Claude CLI?**
```bash
# Specify Claude path in .sugar/config.yaml
claude:
  command: "/full/path/to/claude"
```

**Tasks not executing?**
```bash
# Check dry_run is disabled
cat .sugar/config.yaml | grep dry_run

# Monitor logs
tail -f .sugar/sugar.log

# Test single cycle
sugar run --once
```

**Need help?**
- [Troubleshooting Guide](docs/user/troubleshooting.md)
- [GitHub Issues](https://github.com/cdnsteve/sugar/issues)

## Contributing

Contributions welcome! See [CONTRIBUTING.md](docs/dev/contributing.md) for guidelines.

```bash
# Development setup
git clone https://github.com/cdnsteve/sugar.git
cd sugar

# Install with uv (recommended)
uv pip install -e ".[dev,test,github]"

# Or with pip
pip install -e ".[dev,test,github]"

# Run tests
pytest tests/ -v

# Format code
black .
```

## License

MIT - see [LICENSE](LICENSE) and [TERMS.md](TERMS.md)

---

**Sugar v2.0.1** - Autonomous development for any project

> ⚠️ Sugar is provided "AS IS" without warranty. Review all AI-generated code before use. See [TERMS.md](TERMS.md) for details.
