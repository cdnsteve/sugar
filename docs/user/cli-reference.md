# CLI Reference

Complete reference for all Sugar command-line interface commands.

## Global Options

```bash
sugar [OPTIONS] COMMAND [ARGS]...
```

### Global Options

- `--config TEXT` - Configuration file path (default: `.sugar/config.yaml`)
- `--help` - Show help message and exit

## Commands

### `sugar init`

Initialize Sugar in a project directory.

```bash
sugar init [OPTIONS]
```

**Options:**
- `--project-dir PATH` - Project directory to initialize (default: current directory)

**Examples:**
```bash
# Initialize in current directory
sugar init

# Initialize in specific directory
sugar init --project-dir /path/to/my/project
```

**What it creates:**
- `.sugar/` directory with configuration and database
- `.sugar/config.yaml` - project configuration
- `.sugar/sugar.db` - SQLite task database
- `.sugar/logs/` - Sugar-specific logs
- `logs/errors/` - Error log monitoring directory

---

### `sugar add`

Add a new task to the Sugar work queue.

```bash
sugar add TITLE [OPTIONS]
```

**Arguments:**
- `TITLE` - Task title (required)

**Options:**
- `--type TYPE` - Task type: `bug_fix`, `feature`, `test`, `refactor`, `documentation` (default: `feature`)
- `--priority INTEGER` - Priority level 1-5 (1=low, 5=urgent, default: 3)
- `--description TEXT` - Detailed task description
- `--urgent` - Mark as urgent (sets priority to 5)

**Examples:**
```bash
# Basic task
sugar add "Implement user login"

# Feature with priority
sugar add "Add search functionality" --type feature --priority 4

# Urgent bug fix
sugar add "Fix authentication crash" --type bug_fix --urgent

# With detailed description
sugar add "Refactor API endpoints" --type refactor --priority 3 --description "Clean up REST API structure and improve error handling"
```

---

### `sugar list`

List tasks in the Sugar work queue.

```bash
sugar list [OPTIONS]
```

**Options:**
- `--status TYPE` - Filter by status: `pending`, `active`, `completed`, `failed`, `all` (default: `all`)
- `--type TYPE` - Filter by type: `bug_fix`, `feature`, `test`, `refactor`, `documentation`, `all` (default: `all`)
- `--limit INTEGER` - Number of tasks to show (default: 10)

**Examples:**
```bash
# List all tasks
sugar list

# List only pending tasks
sugar list --status pending

# List only bug fixes
sugar list --type bug_fix

# List last 5 completed tasks
sugar list --status completed --limit 5

# List pending features
sugar list --status pending --type feature
```

---

### `sugar view`

View detailed information about a specific task.

```bash
sugar view TASK_ID
```

**Arguments:**
- `TASK_ID` - Task ID to view (required)

**Examples:**
```bash
sugar view task-abc123
```

**Shows:**
- Complete task details
- Execution history
- Context and metadata
- Results or error information

---

### `sugar update`

Update an existing task.

```bash
sugar update TASK_ID [OPTIONS]
```

**Arguments:**
- `TASK_ID` - Task ID to update (required)

**Options:**
- `--title TEXT` - Update task title
- `--description TEXT` - Update task description
- `--priority INTEGER` - Update priority (1-5)
- `--type TYPE` - Update task type
- `--status STATUS` - Update status: `pending`, `active`, `completed`, `failed`

**Examples:**
```bash
# Update priority
sugar update task-abc123 --priority 5

# Update title and description
sugar update task-abc123 --title "New title" --description "Updated description"

# Mark as completed
sugar update task-abc123 --status completed
```

---

### `sugar remove`

Remove a task from the work queue.

```bash
sugar remove TASK_ID
```

**Arguments:**
- `TASK_ID` - Task ID to remove (required)

**Examples:**
```bash
sugar remove task-abc123
```

---

### `sugar status`

Show Sugar system status and queue statistics.

```bash
sugar status
```

**Shows:**
- Total tasks count
- Tasks by status (pending, active, completed, failed)
- Recent activity (24 hours)
- Next few pending tasks

**Example output:**
```
🤖 Sugar System Status
========================================
📊 Total Tasks: 15
⏳ Pending: 5
⚡ Active: 1
✅ Completed: 8
❌ Failed: 1
📈 Recent (24h): 12

🔜 Next Tasks:
--------------------
🚨 [bug_fix] Fix critical auth bug
P4 [feature] Add user dashboard
P3 [test] Add integration tests
```

---

### `sugar run`

Start the Sugar autonomous development system.

```bash
sugar run [OPTIONS]
```

**Options:**
- `--dry-run` - Run in simulation mode (override config setting)
- `--once` - Run one cycle and exit
- `--validate` - Validate configuration and exit

**Examples:**
```bash
# Test run (safe mode)
sugar run --dry-run --once

# Validate configuration
sugar run --validate

# Start continuous operation
sugar run

# Force dry run mode
sugar run --dry-run
```

**Modes:**
- **Dry Run**: Shows what would be done without making changes
- **Once**: Runs one discovery/execution cycle then exits
- **Continuous**: Runs forever until interrupted (Ctrl+C)
- **Validate**: Checks configuration and Claude CLI setup

## Task Status Lifecycle

```
pending → active → completed
            ↓
         failed
```

- **pending** - Task added but not yet started
- **active** - Task currently being executed by Claude
- **completed** - Task finished successfully
- **failed** - Task execution failed (can be retried)

## Task Types

- **`bug_fix`** - Fixing bugs, errors, or issues
- **`feature`** - Adding new functionality
- **`test`** - Writing or updating tests
- **`refactor`** - Improving code structure without changing functionality
- **`documentation`** - Writing or updating documentation

## Priority Levels

- **1** - Low priority (nice to have)
- **2** - Below normal priority
- **3** - Normal priority (default)
- **4** - High priority (important)
- **5** - Urgent priority (critical, shown with 🚨)

## Exit Codes

- **0** - Success
- **1** - General error
- **2** - Configuration error
- **3** - Claude CLI not found

## Environment Variables

- `SUGAR_CONFIG` - Override default config file path
- `SUGAR_LOG_LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR)

## Tips

💡 Use `--dry-run --once` to safely test Sugar behavior  
💡 Check `.sugar/sugar.log` for detailed execution logs  
💡 Tasks are isolated per project - each project needs its own `sugar init`  
💡 Use `sugar status` to monitor progress and queue health