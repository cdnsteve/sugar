# Troubleshooting Guide

Common issues and solutions for Sugar users.

## 🚨 Common Issues

### Claude CLI Not Found

**Problem:** Sugar reports "Claude CLI not found" during initialization.

**Solutions:**

1. **Install Claude CLI:**
   ```bash
   npm install -g @anthropic-ai/claude-code-cli
   claude --version  # Verify installation
   ```

2. **Check PATH:**
   ```bash
   which claude  # Should return path to claude
   echo $PATH    # Verify PATH includes claude location
   ```

3. **Manual Configuration:**
   Edit `.sugar/config.yaml`:
   ```yaml
   sugar:
     claude:
       command: "/full/path/to/claude"  # Specify exact path
   ```

**Common Claude CLI Locations:**
- `/usr/local/bin/claude`
- `/opt/homebrew/bin/claude` (macOS with Homebrew)
- `~/.local/bin/claude`
- `~/.claude/local/claude`

---

### No Work Discovered

**Problem:** Sugar doesn't find any tasks to work on.

**Solutions:**

1. **Check Discovery Paths:**
   ```bash
   # Verify error log directories exist
   ls -la logs/errors/
   
   # Create if missing
   mkdir -p logs/errors/
   ```

2. **Test with Sample Error:**
   ```bash
   echo '{"error": "test", "message": "sample error"}' > logs/errors/test.json
   sugar run --dry-run --once
   ```

3. **Enable Discovery Sources:**
   Edit `.sugar/config.yaml`:
   ```yaml
   sugar:
     discovery:
       error_logs:
         enabled: true
         paths: ["logs/errors/", "logs/feedback/"]
       code_quality:
         enabled: true
       test_coverage:
         enabled: true
   ```

4. **Validate Configuration:**
   ```bash
   sugar run --validate
   ```

---

### Tasks Not Executing

**Problem:** Tasks remain pending and never execute.

**Solutions:**

1. **Check Dry Run Mode:**
   Edit `.sugar/config.yaml`:
   ```yaml
   sugar:
     dry_run: false  # Must be false for real execution
   ```

2. **Check Claude CLI Access:**
   ```bash
   claude --version  # Should work without error
   ```

3. **Monitor Logs:**
   ```bash
   tail -f .sugar/sugar.log
   ```

4. **Test Single Task:**
   ```bash
   sugar add "test task" --type feature
   sugar run --once --dry-run  # Test in safe mode first
   ```

---

### Permission Errors

**Problem:** Sugar can't write to directories or access files.

**Solutions:**

1. **Check File Permissions:**
   ```bash
   ls -la .sugar/
   chmod 755 .sugar/
   chmod 644 .sugar/config.yaml
   ```

2. **Check Directory Ownership:**
   ```bash
   ls -la | grep .sugar
   # Should be owned by your user
   ```

3. **Verify Write Access:**
   ```bash
   touch .sugar/test_file
   rm .sugar/test_file
   ```

---

### Database Errors

**Problem:** SQLite database errors or corruption.

**Solutions:**

1. **Check Database File:**
   ```bash
   ls -la .sugar/sugar.db
   file .sugar/sugar.db  # Should show "SQLite 3.x database"
   ```

2. **Reset Database:**
   ```bash
   # Backup first
   cp .sugar/sugar.db .sugar/sugar.db.backup
   
   # Remove and reinitialize
   rm .sugar/sugar.db
   sugar status  # Will recreate database
   ```

3. **Check Disk Space:**
   ```bash
   df -h .  # Ensure sufficient disk space
   ```

---

### High Memory/CPU Usage

**Problem:** Sugar consumes too many resources.

**Solutions:**

1. **Reduce Concurrency:**
   Edit `.sugar/config.yaml`:
   ```yaml
   sugar:
     max_concurrent_work: 1  # Reduce from default 3
   ```

2. **Increase Loop Interval:**
   ```yaml
   sugar:
     loop_interval: 600  # 10 minutes instead of 5
   ```

3. **Limit File Scanning:**
   ```yaml
   sugar:
     discovery:
       code_quality:
         max_files_per_scan: 25  # Reduce from 50
   ```

4. **Monitor Resource Usage:**
   ```bash
   top -p $(pgrep -f sugar)
   ```

---

## 🔍 Diagnostic Commands

### Check Sugar Status
```bash
sugar status  # System overview
sugar list    # Task queue
```

### Validate Configuration
```bash
sugar run --validate  # Check all settings
```

### Test Discovery
```bash
sugar run --dry-run --once  # Safe test run
```

### Check Logs
```bash
# Sugar logs
tail -f .sugar/sugar.log

# System logs (macOS)
log show --predicate 'process == "sugar"' --last 1h

# System logs (Linux)
journalctl -f -u sugar
```

### Database Inspection
```bash
# Install sqlite3 if needed
sqlite3 .sugar/sugar.db

# In SQLite prompt:
.tables                    # List tables
.schema work_items         # Show table structure
SELECT * FROM work_items;  # Show all tasks
.quit                      # Exit
```

---

## 📊 Performance Optimization

### For Large Projects
```yaml
sugar:
  discovery:
    code_quality:
      max_files_per_scan: 25
      excluded_dirs: [
        "node_modules", "venv", "dist", "build", 
        "coverage", "docs", "examples", ".git"
      ]
```

### For Many Log Files
```yaml
sugar:
  discovery:
    error_logs:
      max_age_hours: 12    # Only recent errors
      patterns: ["*.json"] # Limit to structured logs
```

### For Slow Systems
```yaml
sugar:
  loop_interval: 900       # 15 minutes between cycles
  max_concurrent_work: 1   # Single task at a time
  
  claude:
    timeout: 3600          # Allow longer execution time
```

---

## 🛡️ Safety Checks

Sugar has built-in safety measures:

- **Dry run by default** - No changes until you set `dry_run: false`
- **Path exclusions** - Won't modify system directories
- **Timeout protection** - Tasks have maximum execution time
- **Retry limits** - Failed tasks won't retry infinitely

### Emergency Stop
```bash
# Stop running Sugar
pkill -f "sugar run"

# Or use Ctrl+C in the terminal running Sugar
```

---

## 🆘 Getting Help

If you can't resolve the issue:

1. **Search Issues:** Check [GitHub Issues](https://github.com/cdnsteve/sugar/issues)
2. **Create Issue:** Include:
   - Sugar version (`sugar --version`)
   - Operating system
   - Python version
   - Claude CLI version
   - Configuration file (remove sensitive data)
   - Log files
   - Steps to reproduce

3. **Emergency Contact:** [contact@roboticforce.io](mailto:contact@roboticforce.io)

---

## 🔧 Debug Mode

Enable detailed logging:

```bash
export SUGAR_LOG_LEVEL=DEBUG
sugar run --dry-run --once
```

Or edit `.sugar/config.yaml`:
```yaml
sugar:
  logging:
    level: "DEBUG"
```