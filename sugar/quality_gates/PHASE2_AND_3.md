# Quality Gates Phase 2 & 3 Documentation

This document details Phase 2 and Phase 3 features of the Quality Gates system.

## Table of Contents

- [Phase 2 Features](#phase-2-features)
  - [Feature 2: Functional Verification Layer](#feature-2-functional-verification-layer)
  - [Feature 6: Task Pre-Flight Checks](#feature-6-task-pre-flight-checks)
- [Phase 3 Features](#phase-3-features)
  - [Feature 7: Verification Failure Handling](#feature-7-verification-failure-handling)
  - [Feature 10: Work Diff Validation](#feature-10-work-diff-validation)
- [Configuration Examples](#configuration-examples)
- [Usage Examples](#usage-examples)

---

## Phase 2 Features

### Feature 2: Functional Verification Layer

**Purpose:** Verify that fixes actually work in the running application, not just that tests pass.

**Module:** `functional_verifier.py`

#### Verification Types

1. **HTTP Request Verification**
   - Sends HTTP requests to URLs
   - Validates status codes
   - Measures response times
   - Uses curl (no external dependencies)

2. **Port Listening Checks**
   - Verifies services are running
   - Checks if ports are accessible
   - Uses lsof for verification

3. **Browser Element Verification** (Placeholder)
   - Will use MCP Chrome DevTools when integrated
   - Verifies DOM elements exist
   - Takes screenshots for evidence

4. **Database Query Verification** (Placeholder)
   - Will verify database state
   - Validates query results

#### Configuration

```yaml
quality_gates:
  functional_verification:
    enabled: true
    required: true  # Block completion without verification

    methods:
      http_requests:
        enabled: true
        tool: "curl"
        timeout: 10

      browser_automation:
        enabled: false  # Requires MCP integration
        tools: ["mcp__chrome-devtools"]
        screenshot_on_verification: true
        screenshot_path: ".sugar/verification/{task_id}/"

      database_queries:
        enabled: false  # Requires implementation
        require_evidence: true

    # Auto-detect verification needs
    auto_detect:
      enabled: true
      patterns:
        - pattern: "app/controllers/sessions_controller.rb"
          verification: "http_requests"
          test_urls: ["/login", "/logout"]
          expected_status: [200, 302]

        - pattern: "config/routes.rb"
          verification: "http_requests"
          action: "extract_new_routes_and_test"

        - pattern: "app/views/**/*.erb"
          verification: "browser_automation"
          action: "screenshot_and_validate"
```

#### Usage

**In task definition:**

```python
task = {
    "id": "fix-login",
    "title": "Fix login redirect",
    "functional_verifications": [
        {
            "type": "http_request",
            "url": "http://localhost:3000/login",
            "expected_status": 200
        },
        {
            "type": "port_listening",
            "port": 3000,
            "host": "localhost"
        }
    ]
}
```

**Auto-detection based on changed files:**

```python
# If you change app/controllers/sessions_controller.rb,
# functional verifier automatically tests /login and /logout routes
```

---

### Feature 6: Task Pre-Flight Checks

**Purpose:** Validate environment is ready before starting task execution.

**Module:** `preflight_checks.py`

#### Check Types

1. **Port Checks**
   - Verifies servers are running
   - Tests connectivity to required ports
   - Examples: Rails server, database, Redis

2. **Command Checks**
   - Runs commands to verify environment
   - Examples: `rails runner`, `bundle exec rspec --dry-run`

3. **Tool Checks**
   - Verifies required tools are available
   - Checks executables and MCP tools

4. **Git Status Checks**
   - Validates working directory state
   - Checks for untracked/unstaged files

5. **File Existence Checks**
   - Verifies required files exist
   - Examples: config files, dependencies

#### Configuration

```yaml
pre_flight_checks:
  enabled: true
  block_execution_if_failed: true

  checks:
    - name: "rails_server_running"
      type: "port_check"
      port: 3000
      host: "localhost"
      required_for: ["ui_changes", "route_changes"]

    - name: "database_accessible"
      type: "command"
      command: "rails runner 'ActiveRecord::Base.connection'"
      timeout: 10
      required_for: ["model_changes", "migration_changes"]

    - name: "test_suite_runnable"
      type: "command"
      command: "bundle exec rspec --dry-run"
      timeout: 30
      required_for: ["all_tasks"]

    - name: "mcp_tools_available"
      type: "tool_check"
      tools: ["mcp__chrome-devtools"]
      required_for: ["ui_changes"]

    - name: "git_working_directory_clean"
      type: "git_status"
      allow_untracked: true
      allow_unstaged: false
      required_for: ["all_tasks"]

    - name: "config_file_exists"
      type: "file_exists"
      file_path: ".sugar/config.yaml"
      required_for: ["all_tasks"]
```

#### Usage

Pre-flight checks run automatically before task execution:

```python
# Coordinator automatically runs pre-flight checks
preflight_passed, results = await preflight_checker.run_all_checks(task)

if not preflight_passed:
    logger.error("Pre-flight checks failed - cannot start task")
    # Block task execution
```

---

## Phase 3 Features

### Feature 7: Verification Failure Handling

**Purpose:** Handle verification failures gracefully with retry logic and escalation.

**Module:** `failure_handler.py`

#### Features

1. **Retry Logic**
   - Configurable max retries per failure type
   - Test failures: 2 retries by default
   - Functional verification failures: 1 retry by default

2. **Escalation Paths**
   - Creates detailed failure reports
   - Saves reports in JSON and Markdown
   - Marks tasks for manual review

3. **Enhanced Debugging**
   - Collects additional evidence on failures
   - Captures server logs, network requests
   - Database state snapshots

#### Configuration

```yaml
verification_failure_handling:
  enabled: true

  on_test_failure:
    action: "retry"
    max_retries: 2
    retry_with_more_context: true

    escalate:
      enabled: true
      action: "create_detailed_failure_report"
      report_path: ".sugar/failures/{task_id}.md"
      include_evidence: true

  on_functional_verification_failure:
    action: "retry"
    max_retries: 1

    enhanced_debugging:
      - "capture_server_logs"
      - "capture_network_requests"
      - "capture_database_state"

    escalate:
      action: "mark_task_as_needs_manual_review"
      notify_user: true

  on_success_criteria_not_met:
    action: "fail_task"
    do_not_commit: true
    create_failure_report: true
```

#### Usage

Failure handling is automatic:

```python
# On test failure
should_retry, report = await failure_handler.handle_test_failure(
    task_id, test_result, retry_count
)

if should_retry:
    # Retry the task with more context
    pass
else:
    # Escalate - create detailed report
    # Report saved to .sugar/failures/{task_id}.md
    pass
```

#### Failure Report Format

**Markdown Report:**

```markdown
# Failure Report: task-123

**Type:** test_execution
**Timestamp:** 2025-10-15T21:45:00Z
**Retry Attempts:** 2
**Escalated:** Yes

## Failure Reason

Tests failed with 3 failures and 1 error

## Evidence

### test_result
*Timestamp: 2025-10-15T21:45:00Z*

```json
{
  "command": "pytest tests/",
  "exit_code": 1,
  "failures": 3,
  "errors": 1,
  "examples": 150
}
```
```

---

### Feature 10: Work Diff Validation

**Purpose:** Validate git changes before committing to prevent unexpected modifications.

**Module:** `diff_validator.py`

#### Features

1. **File Change Validation**
   - Validates changed files match expectations
   - Detects unexpected file modifications
   - Requires justification for unexpected changes

2. **Change Size Validation**
   - Limits max lines changed
   - Warns on large changes
   - Prevents scope creep

3. **Pattern Validation**
   - Detects debug statements (debugger, console.log, binding.pry)
   - Checks for common mistakes
   - Validates against disallowed patterns

#### Configuration

```yaml
git_diff_validation:
  enabled: true

  before_commit:
    # Validate changed files
    validate_files_changed:
      enabled: true
      allowed_files: "from task.files_to_modify.expected"
      allow_additional_files: false

    # Validate size of changes
    max_lines_changed: 500
    warn_if_exceeds: 200

    # Validate patterns
    disallow_patterns:
      - pattern: "debugger"
        reason: "Debug statement left in code"
      - pattern: "console\\.log"
        reason: "Console.log left in code"
      - pattern: "binding\\.pry"
        reason: "Binding.pry left in code"
      - pattern: "TODO:"
        reason: "TODO comment left in code"

    # Handle unexpected changes
    if_unexpected_files_changed:
      action: "require_justification"
      prompt: "Why were these additional files changed?"
```

#### Usage

Diff validation runs automatically before commits:

```python
# Validate diff
is_valid, result = await diff_validator.validate_diff(
    task, changed_files
)

if not is_valid:
    logger.error(f"Diff validation failed: {result.metadata['issues']}")
    # Block commit
```

---

## Configuration Examples

### Minimal Configuration

```yaml
quality_gates:
  enabled: true

  mandatory_testing:
    enabled: true

  functional_verification:
    enabled: true

  truth_enforcement:
    enabled: true

pre_flight_checks:
  enabled: true

verification_failure_handling:
  enabled: true

git_diff_validation:
  enabled: true
```

### Full Configuration

```yaml
quality_gates:
  enabled: true

  mandatory_testing:
    enabled: true
    block_commits: true
    test_commands:
      default: "pytest"
      unit: "pytest tests/unit/"
      integration: "pytest tests/integration/"
    validation:
      require_zero_failures: true
      require_zero_errors: true
    evidence:
      store_test_output: true
      path: ".sugar/test_evidence/{task_id}.txt"

  functional_verification:
    enabled: true
    required: true
    methods:
      http_requests:
        enabled: true
        timeout: 10
    auto_detect:
      enabled: true
      patterns:
        - pattern: "**/*_controller.py"
          verification: "http_requests"
          test_urls: ["/"]

  truth_enforcement:
    enabled: true
    mode: "strict"
    block_unproven_success: true

pre_flight_checks:
  enabled: true
  block_execution_if_failed: true
  checks:
    - name: "server_running"
      type: "port_check"
      port: 8000
      required_for: ["all_tasks"]
    - name: "tests_runnable"
      type: "command"
      command: "pytest --collect-only"
      required_for: ["all_tasks"]

verification_failure_handling:
  enabled: true
  on_test_failure:
    max_retries: 2
    escalate:
      action: "create_detailed_failure_report"
  on_functional_verification_failure:
    max_retries: 1
    escalate:
      action: "mark_task_as_needs_manual_review"

git_diff_validation:
  enabled: true
  before_commit:
    max_lines_changed: 500
    warn_if_exceeds: 200
    disallow_patterns:
      - pattern: "debugger"
        reason: "Debug statement"
```

---

## Usage Examples

### Example 1: API Endpoint Fix

```python
task = {
    "id": "fix-api-endpoint",
    "title": "Fix /api/users endpoint",
    "type": "bug_fix",
    "files_to_modify": {
        "expected": [
            "app/api/users.py",
            "tests/test_users.py"
        ]
    },
    "success_criteria": [
        {
            "type": "http_status",
            "url": "http://localhost:8000/api/users",
            "expected": 200
        },
        {
            "type": "test_suite",
            "command": "pytest tests/test_users.py",
            "expected_failures": 0
        }
    ],
    "functional_verifications": [
        {
            "type": "http_request",
            "url": "http://localhost:8000/api/users",
            "method": "GET",
            "expected_status": 200
        }
    ]
}
```

**Workflow:**
1. Pre-flight checks verify server is running
2. Task execution modifies files
3. Tests run and must pass
4. HTTP request verifies endpoint works
5. Success criteria validated
6. Diff validated (only expected files changed)
7. Commit allowed

### Example 2: UI Component Change

```python
task = {
    "id": "update-login-form",
    "title": "Update login form styling",
    "type": "feature",
    "files_to_modify": {
        "expected": [
            "app/templates/login.html",
            "app/static/css/login.css"
        ]
    },
    "success_criteria": [
        {
            "type": "browser_element_exists",
            "url": "http://localhost:8000/login",
            "selector": "form.login-form"
        }
    ],
    "functional_verifications": [
        {
            "type": "http_request",
            "url": "http://localhost:8000/login",
            "expected_status": 200
        },
        {
            "type": "browser_screenshot",
            "url": "http://localhost:8000/login",
            "screenshot_path": ".sugar/verification/login-form.png"
        }
    ]
}
```

**Workflow:**
1. Pre-flight checks verify server and browser tools
2. Task execution modifies UI files
3. Tests run (if applicable)
4. HTTP request verifies page loads
5. Browser element verified (when MCP integrated)
6. Screenshot taken for evidence
7. Diff validated
8. Commit allowed

---

## Benefits

### Phase 2 Benefits

1. **Confidence in Deployments**
   - Actual functionality verified, not just tests
   - Catches issues tests miss

2. **Environment Validation**
   - No wasted work on broken environments
   - Early failure detection

3. **Better Evidence**
   - HTTP response codes captured
   - Server state verified

### Phase 3 Benefits

1. **Resilience**
   - Automatic retries for transient failures
   - Reduces false negatives

2. **Better Debugging**
   - Detailed failure reports
   - Rich evidence collection

3. **Change Control**
   - Prevents unintended modifications
   - Enforces scope boundaries

4. **Code Quality**
   - No debug statements in commits
   - Change size limits prevent huge PRs

---

## Troubleshooting

### Pre-Flight Checks Failing

**Problem:** "Port 3000 not listening"

**Solutions:**
1. Start the server: `rails server` or `python manage.py runserver`
2. Disable the check if not needed: `required_for: []`
3. Change the port in config

### Functional Verification Failing

**Problem:** "HTTP request returned 404"

**Solutions:**
1. Verify URL is correct
2. Check server is running
3. Verify routes are configured
4. Look at server logs

### Diff Validation Failing

**Problem:** "Unexpected files changed"

**Solutions:**
1. Add files to `task.files_to_modify.expected`
2. Enable `allow_additional_files: true`
3. Provide justification for changes

### Retry Logic Not Working

**Problem:** "Task failed without retry"

**Solutions:**
1. Check `verification_failure_handling.enabled: true`
2. Verify `max_retries` is set correctly
3. Check failure type matches configuration

---

## See Also

- [Phase 1 Documentation](README.md)
- [Integration Guide](INTEGRATION.md)
- [Configuration Examples](config_example.yaml)
- [Test Suite](../../tests/test_quality_gates.py)
