# Sugar Claude Code Plugin - Example Usage

This example demonstrates how to use Sugar as a Claude Code plugin for autonomous development.

## Setup

### 1. Install Sugar CLI

```bash
pip install sugarai
```

### 2. Install the Plugin

In Claude Code:

```
/plugin install sugar@roboticforce
```

Or manually:
```bash
# Clone Sugar repository
git clone https://github.com/roboticforce/sugar.git

# Link plugin (from your project directory)
ln -s /path/to/sugar/.claude-plugin ./.claude-plugins/sugar
```

### 3. Initialize Sugar in Your Project

```bash
cd your-project
sugar init
```

## Example Workflows

### Workflow 1: Simple Task Creation

```
User: I need to add user authentication to my app

Claude: I'll help you create a comprehensive Sugar task for this feature.

/sugar-task "Implement user authentication" --type feature --priority 4

Task created! This includes:
- Email/password authentication
- Session management
- Security best practices

You can view the task queue with /sugar-status
```

### Workflow 2: Rich Task with Context

```
User: Create a task for redesigning the dashboard with full context

Claude: Let me create a comprehensive task with rich metadata.

/sugar-task "User Dashboard Redesign" --json --description '{
  "priority": 5,
  "type": "feature",
  "context": "Complete overhaul of user dashboard for better UX and engagement",
  "business_context": "Current dashboard has low engagement (30% DAU). Redesign aims for 60%+ engagement and 50% reduction in support tickets",
  "technical_requirements": [
    "Responsive design (mobile-first)",
    "Accessibility WCAG 2.1 AA compliance",
    "Performance budget: <2s load time",
    "Real-time data updates"
  ],
  "agent_assignments": {
    "ux_design_specialist": "Lead UI/UX design and mockups",
    "frontend_developer": "Implementation and optimization",
    "backend_developer": "API endpoints for real-time data",
    "qa_test_engineer": "Comprehensive testing across devices"
  },
  "success_criteria": [
    "Mobile responsive on iOS/Android",
    "Lighthouse accessibility score >90",
    "Load time <2s on 3G",
    "User satisfaction >4.5/5",
    "Zero critical bugs"
  ]
}'

Task created with full context! Sugar's agents will coordinate:
- UX Designer creates mockups
- Frontend implements responsive UI
- Backend builds real-time APIs
- QA validates across platforms
```

### Workflow 3: Automatic Task Discovery

```
User: Analyze my codebase for potential work

Claude: I'll scan for errors, code quality issues, and missing tests.

/sugar-analyze

Found 28 potential tasks:
🚨 3 critical errors in logs
🔧 12 code quality improvements
🧪 15 files without tests
📝 5 open GitHub issues

Create all as tasks? [y/N]: y

Created 28 tasks with appropriate priorities. Use /sugar-review to manage the queue.
```

### Workflow 4: Queue Review and Prioritization

```
User: Show me pending tasks

Claude: Let me show your current queue.

/sugar-review

📋 Sugar Task Queue (18 tasks)

🔴 Priority 5 (Urgent) - 2 tasks
━━━━━━━━━━━━━━━━━━━━━━━━━
1. Critical: Auth vulnerability (CVE-2024-XXXX)
   Status: pending | Type: bug_fix
   Created: 2h ago

2. Database connection pool exhausted
   Status: pending | Type: hotfix
   Created: 1h ago

🟡 Priority 4 (High) - 8 tasks
━━━━━━━━━━━━━━━━━━━━━━━━━
[... more tasks ...]

Actions:
- [E]xecute high priority now
- [A]djust priorities
- [R]emove stale tasks
- [V]iew details
```

### Workflow 5: Autonomous Execution

```
User: Start autonomous development mode

Claude: I'll start Sugar's autonomous execution safely.

First, let's validate configuration:
/sugar-run --validate

✅ Configuration valid
✅ Claude CLI found
✅ Database accessible
✅ 18 tasks ready

Ready to start. Test with dry run first?

User: Yes, dry run first

Claude: Running test cycle...

/sugar-run --dry-run --once

Dry Run Results:
- Would execute: Fix auth vulnerability (priority 5)
- Approach: Update authentication library, add tests
- Estimated time: 2-3 hours
- Safety: No breaking changes

Everything looks good! Start real execution?

User: Yes, start it

Claude: Starting autonomous mode...

/sugar-run

🤖 Autonomous mode started
📊 Processing queue: 18 tasks
⚡ Current: Fixing authentication vulnerability
🕐 Estimated completion: 2.5 hours

Monitor progress: /sugar-status
View logs: tail -f .sugar/sugar.log
```

### Workflow 6: Status Monitoring

```
User: What's the status?

Claude: Let me check Sugar's current state.

/sugar-status

📊 Sugar System Status
━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️  System: Active
📋 Total Tasks: 18
   ⏳ Pending: 15
   ⚡ Active: 1
   ✅ Completed: 2
   ❌ Failed: 0

🤖 Autonomous Mode: Running
⏰ Last Cycle: 3 minutes ago
📈 Completion Rate: 100% (2/2)

⚡ Currently Executing:
"Fix authentication vulnerability" (task-157)
Agent: tech-lead
Started: 45 minutes ago
Progress: 60% (code complete, testing in progress)

✅ Recently Completed:
1. "Add API documentation" (task-155) - 2h ago
2. "Fix database connection leak" (task-156) - 1h ago
```

## Advanced Features

### Custom Task Types

```
User: Create a custom task type for security audits

Claude: I'll create a specialized task type.

sugar task-type add security_audit \
  --name "Security Audit" \
  --description "Security vulnerability scanning and remediation" \
  --agent "tech-lead" \
  --commit-template "security: {title}" \
  --emoji "🔒"

Now you can use:
sugar add "Audit authentication system" --type security_audit --priority 5
```

### GitHub Integration

Enable automatic issue sync:

```yaml
# .sugar/config.yaml
discovery:
  github:
    enabled: true
    repo: "your-org/your-repo"
    workflow:
      auto_close_issues: true
      git_workflow: "pull_request"
```

Then: `/sugar-analyze --github` to sync issues as tasks.

### Team Collaboration

Multiple developers can run Sugar on the same project:

```bash
# Developer A
cd project
sugar init
sugar run &

# Developer B (same project, different machine)
cd project
sugar init  # Uses same .sugar/ via git
sugar list  # Sees shared task queue
```

## Best Practices

### 1. Start with Validation

Always validate before running:
```
/sugar-run --validate
/sugar-run --dry-run --once
/sugar-run --once
/sugar-run
```

### 2. Use Rich Context for Complex Tasks

For substantial features, provide comprehensive context:
- Business value and impact
- Technical requirements and constraints
- Success criteria (measurable)
- Agent assignments for specialized work

### 3. Regular Queue Review

Review pending tasks regularly:
```
/sugar-review
# Adjust priorities
# Remove stale tasks
# Add missing context
```

### 4. Monitor Autonomous Execution

When running autonomously:
- Check status regularly: `/sugar-status`
- Review logs: `.sugar/sugar.log`
- Validate completed work
- Maintain git commits

### 5. Leverage Hooks

Sugar's hooks automatically enhance your workflow:
- Error detection → task creation suggestions
- Test failures → automatic tracking
- Security code → audit reminders
- Commits → task status updates

## Troubleshooting

### Plugin Not Loading

```bash
# Verify plugin structure
ls -la .claude-plugins/sugar/.claude-plugin/

# Check manifest
cat .claude-plugins/sugar/.claude-plugin/plugin.json

# Reinstall
/plugin uninstall sugar
/plugin install sugar@roboticforce
```

### MCP Server Issues

```bash
# Test MCP server directly
cd .claude-plugin/mcp-server
node sugar-mcp.js

# Check for errors
SUGAR_DEBUG=true node sugar-mcp.js
```

### Sugar CLI Not Found

```bash
# Verify installation
sugar --version

# Reinstall if needed
pip install --upgrade sugarai

# Check PATH
which sugar
```

## Resources

- **Plugin Documentation**: [.claude-plugin/README.md](../../.claude-plugin/README.md)
- **Sugar Documentation**: [docs/](../../docs/)
- **Issues**: [GitHub Issues](https://github.com/roboticforce/sugar/issues)
- **Discussions**: [GitHub Discussions](https://github.com/roboticforce/sugar/discussions)

## Learn More

- **Implementation Roadmap**: [.claude-plugin/IMPLEMENTATION_ROADMAP.md](../../.claude-plugin/IMPLEMENTATION_ROADMAP.md)
- **Testing Guide**: [.claude-plugin/TESTING_PLAN.md](../../.claude-plugin/TESTING_PLAN.md)
- **MCP Server**: [.claude-plugin/MCP_SERVER_IMPLEMENTATION.md](../../.claude-plugin/MCP_SERVER_IMPLEMENTATION.md)

---

**Transform your Claude Code workflow with autonomous AI development!** 🍰✨
