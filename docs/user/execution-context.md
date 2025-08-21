# Sugar Execution Context

Understanding where and how to run Sugar for optimal performance and safety.

## 🎯 Correct Execution Pattern

Sugar is designed to run as a **standalone autonomous system** that calls Claude Code CLI when needed:

```
Terminal/Shell → Sugar → Claude Code CLI (for task execution)
```

## ✅ Correct Usage

### Run Sugar in Regular Terminal

```bash
# Open terminal/shell in your project directory
cd /path/to/your/project

# Initialize Sugar
sugar init

# Add tasks
sugar add "Implement feature" --type feature --priority 4

# Run Sugar autonomously
sugar run
```

### Architecture Overview

```
┌─────────────────┐
│  Your Terminal  │
│   (your-proj)   │
└─────────────────┘
         │
         ▼ runs sugar
┌─────────────────┐      ┌──────────────────┐
│     Sugar       │ ──── │ Claude Code CLI  │
│  (autonomous)   │calls │ (task execution) │
└─────────────────┘      └──────────────────┘
         │                         │
         ▼ manages                 ▼ executes on
┌─────────────────┐      ┌──────────────────┐
│   .sugar/       │      │   Your Project   │
│ config.yaml     │      │     Files        │
│ sugar.db        │      │                  │
│ sugar.log       │      │                  │
└─────────────────┘      └──────────────────┘
```

## ❌ Incorrect Usage Patterns

### Don't Run Sugar Inside Claude Code

```bash
# WRONG: Inside Claude Code session
claude> sugar init  # ❌ Recursive execution
claude> sugar run   # ❌ Context conflicts
```

**Problems with this approach:**
- **Recursive calls**: Sugar trying to call Claude Code from within Claude Code
- **Context confusion**: Mixed session states between Sugar and Claude Code
- **Authentication issues**: Nested authentication contexts
- **Resource conflicts**: Both systems trying to manage the same files
- **State corruption**: Sugar's persistent state mixing with Claude Code's session state

### Don't Mix Session Management

```bash
# WRONG: Manual Claude Code session + Sugar
claude --session                # Manual Claude session
# Then in another terminal:
sugar run                       # ❌ Potential conflicts
```

**Better approach:**
```bash
# CORRECT: Let Sugar manage Claude Code calls
sugar run  # Sugar will handle Claude Code sessions internally
```

## 🔍 How to Verify Correct Execution

### Check Your Environment

```bash
# Verify you're in a regular terminal (not Claude Code)
echo $CLAUDE_SESSION    # Should be empty or undefined
echo $PWD              # Should show your project directory
which sugar            # Should show Sugar installation path
```

### Test Sugar Setup

```bash
# Verify Sugar can find Claude Code CLI
sugar run --validate   # Validates configuration and dependencies

# Test with dry-run
sugar run --dry-run --once  # Safe test of one cycle
```

### Monitor Execution

```bash
# Check Sugar logs for proper Claude Code calls
tail -f .sugar/sugar.log

# Should see entries like:
# "Calling Claude Code CLI for task: ..."
# "Claude Code execution completed: ..."
```

## 🏗️ Integration Scenarios

### Scenario 1: Solo Development

**Setup:**
```bash
# Your terminal session
cd ~/projects/my-app
sugar init
sugar add "Add user registration" --type feature
sugar run &  # Run in background

# Continue regular development
git add .
git commit -m "Working on features"
# Sugar autonomously handles additional tasks
```

### Scenario 2: CI/CD Integration

**In CI pipeline:**
```yaml
# .github/workflows/autonomous-dev.yml
- name: Run Sugar for maintenance tasks
  run: |
    sugar init
    sugar add "Update dependencies" --type maintenance --priority 2
    sugar run --once  # Single cycle for CI
```

### Scenario 3: Development Team

**Each developer:**
```bash
# Developer workstation
cd /their/local/copy/project
sugar init  # Each dev gets own Sugar instance
sugar run   # Project-specific autonomous development
```

## 🛡️ Safety and Best Practices

### Environment Separation

```bash
# Good: Separate environments
Terminal 1: sugar run                    # Sugar autonomous system
Terminal 2: git status; npm test        # Manual development
Terminal 3: tail -f .sugar/sugar.log    # Monitor Sugar activity
```

### Configuration Management

```yaml
# .sugar/config.yaml - Configure for your environment
sugar:
  claude:
    command: "/usr/local/bin/claude"  # Explicit path if needed
    timeout: 1800                     # Adjust for your needs
  
  safety:
    excluded_paths:                     # Protect important directories
      - ".git"
      - ".sugar"
      - "node_modules"
```

### Resource Management

```bash
# Monitor Sugar resource usage
ps aux | grep sugar                # Check Sugar process
top -p $(pgrep -f sugar)          # Monitor CPU/memory

# Control Sugar execution
pkill -f "sugar run"              # Stop Sugar if needed
sugar status                      # Check system status
```

## 💡 Troubleshooting Execution Issues

### Issue: "Claude Code CLI not found"

```bash
# Check Claude Code CLI installation
which claude
claude --version

# Update Sugar config if needed
# Edit .sugar/config.yaml with correct claude path
```

### Issue: "Permission denied" or "Session conflicts"

```bash
# Ensure running outside Claude Code
echo $CLAUDE_SESSION  # Should be empty

# Check file permissions
ls -la .sugar/
chmod 755 .sugar/
chmod 644 .sugar/config.yaml
```

### Issue: "Recursive execution detected"

This suggests Sugar was started from within Claude Code:

1. Exit Claude Code session
2. Open regular terminal
3. Navigate to project directory
4. Run Sugar directly

## 📋 Quick Reference

### Correct Execution Checklist

- [ ] Running in regular terminal/shell (not Claude Code)
- [ ] Project directory contains `.sugar/` configuration
- [ ] Claude Code CLI is installed and accessible
- [ ] Sugar config points to correct Claude Code CLI path
- [ ] No conflicting Claude Code sessions running
- [ ] Proper file permissions on `.sugar/` directory

### Command Quick Reference

```bash
sugar help           # Complete help and context guidance
sugar init           # Initialize in current project
sugar run --validate # Verify setup and dependencies
sugar run --dry-run --once  # Safe test execution
sugar run            # Start autonomous system
sugar status         # Monitor system health
```

---

**Remember:** Sugar is designed to be your autonomous development assistant that works alongside your regular development workflow, not from within other development tools.