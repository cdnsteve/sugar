# Quality Gates User Guide

**Complete Guide to Quality Gates in Sugar**

Quality Gates enforce mandatory verification before allowing task completion. This guide covers all implemented features across Phase 1, 2, and 3.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Overview](#overview)
- [Phase 1: Critical Features](#phase-1-critical-features)
- [Phase 2: High Priority Features](#phase-2-high-priority-features)
- [Phase 3: Enhancement Features](#phase-3-enhancement-features)
- [Configuration Guide](#configuration-guide)
- [Task Examples](#task-examples)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Quick Start

### 1. Enable Quality Gates

Add to your `.sugar/config.yaml`:

```yaml
quality_gates:
  enabled: true

  mandatory_testing:
    enabled: true
    block_commits: true
    test_commands:
      default: "pytest"
    validation:
      require_zero_failures: true
      require_zero_errors: true

  truth_enforcement:
    enabled: true
    mode: "strict"
```

### 2. Add a Task with Verification

```python
task = {
    "id": "fix-api-endpoint",
    "title": "Fix /api/users endpoint",
    "type": "bug_fix",

    # What needs to be verified
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
    ]
}
```

### 3. Sugar Automatically Verifies

When Sugar completes the task:
1. ✅ Runs tests and verifies they pass
2. ✅ Verifies the HTTP endpoint returns 200
3. ✅ Checks all success criteria are met
4. ✅ Ensures claims have proof
5. ✅ Only commits if all gates pass

---

## Overview

### What Are Quality Gates?

Quality Gates are **mandatory verification checkpoints** that prevent Sugar from claiming success without proof.

**Problem it solves:** Sugar previously could claim "all tests pass" or "functionality verified" without actually running tests or verifying functionality.

**Solution:** Quality Gates enforce verification at multiple levels:
- Test execution is mandatory
- Success criteria must be verified
- Claims require proof
- Functional verification ensures it actually works
- Pre-flight checks validate environment
- Diff validation prevents unexpected changes

### Architecture

```
QualityGatesCoordinator
│
├── Phase 1: Critical Features
│   ├── TestExecutionValidator - Mandatory test execution
│   ├── SuccessCriteriaVerifier - Verify success criteria
│   ├── TruthEnforcer - Require proof for claims
│   └── EvidenceCollector - Store all evidence
│
├── Phase 2: High Priority
│   ├── FunctionalVerifier - Verify actual functionality
│   └── PreFlightChecker - Validate environment
│
└── Phase 3: Enhancements
    ├── VerificationFailureHandler - Retry & escalation
    └── DiffValidator - Validate git changes
```

---

## Phase 1: Critical Features

### Feature 1: Mandatory Test Execution

**Purpose:** Block commits unless tests run and pass.

#### How It Works

1. Before `git commit`, Sugar runs configured test commands
2. Test output is parsed for failures/errors
3. Evidence is stored in `.sugar/test_evidence/{task_id}.txt`
4. Commit is **blocked** if:
   - Tests fail
   - Tests have errors
   - Tests weren't run

#### Configuration

```yaml
quality_gates:
  mandatory_testing:
    enabled: true
    block_commits: true

    # Test commands for different scenarios
    test_commands:
      default: "pytest"
      unit: "pytest tests/unit"
      integration: "pytest tests/integration"
      system: "pytest tests/system"

    # Auto-detect which tests to run
    auto_detect_required_tests:
      enabled: true
      patterns:
        - pattern: "app/controllers/**/*.py"
          required_tests: ["integration", "system"]
        - pattern: "app/models/**/*.py"
          required_tests: ["unit", "integration"]

    # Validation rules
    validation:
      require_zero_failures: true
      require_zero_errors: true
      allow_pending: true
      max_warnings: 10

    # Evidence storage
    evidence:
      store_test_output: true
      path: ".sugar/test_evidence/{task_id}.txt"
      include_in_commit_message: true
```

#### Supported Test Frameworks

- **pytest** (Python)
- **rspec** (Ruby)
- **jest** (JavaScript)

#### Example Output

```
✅ Tests passed: 150 examples, 0 failures, 0 errors
📄 Evidence: .sugar/test_evidence/task-123.txt
```

---

### Feature 3: Success Criteria Verification

**Purpose:** Make success criteria testable and automatically verifiable.

#### How It Works

1. Tasks include structured `success_criteria` with expected outcomes
2. Each criterion is automatically verified
3. Task cannot complete until **all** criteria pass
4. Evidence is collected for each verification

#### Supported Criterion Types

**1. HTTP Status**
```yaml
type: "http_status"
url: "http://localhost:3000/login"
expected: 200
```

**2. HTTP No Redirect**
```yaml
type: "http_no_redirect"
url: "http://localhost:3000/login"
disallowed_status: [301, 302, 303, 307, 308]
```

**3. Test Suite**
```yaml
type: "test_suite"
command: "pytest tests/test_login.py"
expected_failures: 0
expected_errors: 0
```

**4. File Exists**
```yaml
type: "file_exists"
file_path: "app/controllers/sessions_controller.rb"
```

**5. String in File**
```yaml
type: "string_in_file"
file_path: "config/routes.rb"
search_string: "get '/login'"
```

**6. Browser Element Exists** (Placeholder for MCP integration)
```yaml
type: "browser_element_exists"
url: "http://localhost:3000/login"
selector: "form.login-form"
```

#### Example

```python
task = {
    "title": "Fix /login redirect",
    "success_criteria": [
        {
            "type": "http_status",
            "url": "http://localhost:3000/login",
            "expected": 200
        },
        {
            "type": "http_no_redirect",
            "url": "http://localhost:3000/login",
            "disallowed_status": [301, 302]
        },
        {
            "type": "test_suite",
            "command": "pytest tests/test_login.py",
            "expected_failures": 0
        }
    ]
}
```

**Output:**
```
✅ Success Criteria: VERIFIED (3/3)
  ✅ http_status: 200 (expected 200)
  ✅ http_no_redirect: no redirect detected
  ✅ test_suite: 0 failures, 0 errors
```

---

### Feature 8: Truth Enforcement

**Purpose:** Require proof for all claims of success.

#### How It Works

1. Sugar makes claims like "all tests pass" or "functionality verified"
2. Truth Enforcer checks evidence collector for matching proof
3. **Claims without proof cause task to fail** (in strict mode)
4. Unproven claims report is generated

#### Configuration

```yaml
quality_gates:
  truth_enforcement:
    enabled: true
    mode: "strict"  # strict | permissive
    block_unproven_success: true

    rules:
      - claim: "all tests pass"
        proof_required: "test_execution_evidence"
        must_show:
          exit_code: 0
          failures: 0
          errors: 0

      - claim: "functionality verified"
        proof_required: "functional_verification_evidence"
        must_show:
          http_request_results: "all_success"

      - claim: "success criteria met"
        proof_required: "success_criteria_verification"
        must_show:
          all_criteria_verified: true
```

#### Example

**Claim:** "All tests pass and functionality is verified"

**Proof Required:**
- Test execution evidence showing 0 failures
- Functional verification evidence showing HTTP success
- Success criteria all verified

**If proof is missing:**
```
❌ Unproven claims detected:
  - "all tests pass": MISSING test_execution_evidence

⚠️ Task blocked in strict mode
```

---

## Phase 2: High Priority Features

### Feature 2: Functional Verification Layer

**Purpose:** Verify that fixes **actually work** in the running application, not just that tests pass.

#### Why This Matters

Tests can pass while the application is broken:
- Tests might not cover the real scenario
- Mocking can hide integration issues
- Configuration issues not caught by tests

Functional verification checks the **actual running application**.

#### Verification Types

**1. HTTP Request Verification**

Sends HTTP requests and validates responses:

```yaml
functional_verification:
  enabled: true
  methods:
    http_requests:
      enabled: true
      tool: "curl"
      timeout: 10
```

**Usage in task:**
```python
"functional_verifications": [
    {
        "type": "http_request",
        "url": "http://localhost:3000/login",
        "method": "GET",
        "expected_status": 200
    }
]
```

**2. Port Listening Checks**

Verifies services are running:

```python
"functional_verifications": [
    {
        "type": "port_listening",
        "port": 3000,
        "host": "localhost"
    }
]
```

**3. Browser Automation** (Placeholder - requires MCP Chrome DevTools)

```yaml
methods:
  browser_automation:
    enabled: false  # Requires MCP integration
    tools: ["mcp__chrome-devtools"]
    screenshot_on_verification: true
```

**4. Database Queries** (Placeholder)

```yaml
methods:
  database_queries:
    enabled: false
    require_evidence: true
```

#### Auto-Detection

Functional verifications can be auto-detected based on changed files:

```yaml
functional_verification:
  auto_detect:
    enabled: true
    patterns:
      # If you change a controller, test the routes
      - pattern: "app/controllers/**/*.py"
        verification: "http_requests"
        test_urls: ["/"]
        expected_status: [200, 302]

      # If you change routes, extract and test new routes
      - pattern: "config/routes.py"
        verification: "http_requests"
        action: "extract_new_routes_and_test"

      # If you change templates, take screenshots
      - pattern: "app/templates/**/*.html"
        verification: "browser_automation"
        action: "screenshot_and_validate"
```

#### Example

```python
task = {
    "title": "Fix API endpoint",
    "functional_verifications": [
        {
            "type": "http_request",
            "url": "http://localhost:8000/api/users",
            "method": "GET",
            "expected_status": 200,
            "headers": {
                "Authorization": "Bearer test-token"
            }
        },
        {
            "type": "port_listening",
            "port": 8000,
            "host": "localhost"
        }
    ]
}
```

**Output:**
```
✅ Functional Verifications: PASSED (2/2)
  ✅ http_request: 200 (0.123s)
  ✅ port_listening: port 8000 listening
```

---

### Feature 6: Task Pre-Flight Checks

**Purpose:** Validate environment is ready **before** starting task execution.

#### Why This Matters

Without pre-flight checks, Sugar might:
- Start work when the server isn't running
- Make changes when tests can't run
- Waste time on a broken environment

Pre-flight checks **fail fast** and save time.

#### Check Types

**1. Port Checks**

Verify servers are running:

```yaml
pre_flight_checks:
  enabled: true
  checks:
    - name: "dev_server_running"
      type: "port_check"
      port: 8000
      host: "localhost"
      required_for: ["ui_changes", "api_changes"]
```

**2. Command Checks**

Run commands to verify environment:

```yaml
- name: "database_accessible"
  type: "command"
  command: "python manage.py check --database default"
  timeout: 10
  required_for: ["model_changes", "migration_changes"]
```

**3. Tool Checks**

Verify required tools are available:

```yaml
- name: "required_tools_available"
  type: "tool_check"
  tools: ["python", "pytest", "curl"]
  required_for: ["all_tasks"]
```

**4. Git Status Checks**

Validate working directory state:

```yaml
- name: "git_clean_state"
  type: "git_status"
  allow_untracked: true
  allow_unstaged: false
  required_for: ["all_tasks"]
```

**5. File Existence Checks**

Verify required files exist:

```yaml
- name: "config_files_exist"
  type: "file_exists"
  file_path: ".sugar/config.yaml"
  required_for: ["all_tasks"]
```

#### Example Configuration

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

    - name: "test_suite_runnable"
      type: "command"
      command: "bundle exec rspec --dry-run"
      timeout: 30
      required_for: ["all_tasks"]

    - name: "mcp_tools_available"
      type: "tool_check"
      tools: ["mcp__chrome-devtools"]
      required_for: ["ui_changes"]
```

#### Example Output

```
🔍 Running pre-flight checks...
  ✅ rails_server_running: port 3000 listening
  ✅ test_suite_runnable: command succeeded
  ⚠️ mcp_tools_available: tool not found (optional)

✅ Pre-flight checks passed (2/2 required)
```

---

## Phase 3: Enhancement Features

### Feature 7: Verification Failure Handling

**Purpose:** Handle verification failures gracefully with retry logic and escalation.

#### Features

**1. Retry Logic**

Configurable retries for transient failures:

```yaml
verification_failure_handling:
  enabled: true

  on_test_failure:
    action: "retry"
    max_retries: 2
    retry_with_more_context: true

  on_functional_verification_failure:
    action: "retry"
    max_retries: 1
```

**2. Escalation Paths**

Create detailed failure reports when retries exhausted:

```yaml
on_test_failure:
  escalate:
    enabled: true
    action: "create_detailed_failure_report"
    report_path: ".sugar/failures/{task_id}.md"
    include_evidence: true
```

**3. Enhanced Debugging**

Collect additional evidence on failures:

```yaml
on_functional_verification_failure:
  enhanced_debugging:
    - "capture_server_logs"
    - "capture_network_requests"
    - "capture_database_state"
```

#### Example Flow

**First Failure:**
```
❌ Tests failed (3 failures)
♻️ Retrying with more context (attempt 1/2)
```

**Second Failure:**
```
❌ Tests failed (3 failures)
♻️ Retrying with more context (attempt 2/2)
```

**Third Failure (retries exhausted):**
```
❌ Tests failed (3 failures)
📄 Creating detailed failure report...
📄 Report saved: .sugar/failures/task-123.md
⚠️ Task failed after 2 retry attempts
```

#### Failure Report Format

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

\`\`\`json
{
  "command": "pytest tests/",
  "exit_code": 1,
  "failures": 3,
  "errors": 1,
  "examples": 150
}
\`\`\`
```

---

### Feature 10: Work Diff Validation

**Purpose:** Validate git changes before committing to prevent unexpected modifications.

#### Features

**1. File Change Validation**

Ensures only expected files are changed:

```yaml
git_diff_validation:
  enabled: true
  before_commit:
    validate_files_changed:
      enabled: true
      allowed_files: "from task.files_to_modify.expected"
      allow_additional_files: false
```

**Usage in task:**
```python
task = {
    "title": "Fix user model",
    "files_to_modify": {
        "expected": [
            "app/models/user.py",
            "tests/test_user.py"
        ]
    }
}
```

**2. Change Size Validation**

Limits size of changes to prevent massive commits:

```yaml
before_commit:
  max_lines_changed: 500
  warn_if_exceeds: 200
```

**3. Pattern Validation**

Detects debug statements and common mistakes:

```yaml
before_commit:
  disallow_patterns:
    - pattern: "debugger"
      reason: "Debug statement left in code"
    - pattern: "console\\.log"
      reason: "Console.log left in code"
    - pattern: "binding\\.pry"
      reason: "Binding.pry left in code"
    - pattern: "import pdb"
      reason: "pdb import left in code"
    - pattern: "TODO:"
      reason: "TODO comment left in code"
```

**4. Unexpected File Handling**

Requires justification for unexpected changes:

```yaml
before_commit:
  if_unexpected_files_changed:
    action: "require_justification"
    prompt: "Why were these additional files changed?"
```

#### Example Output

**Valid diff:**
```
✅ Diff validation passed
  ✅ File changes match expectations (2 files)
  ✅ Change size acceptable: 127 lines
  ✅ No disallowed patterns found
```

**Invalid diff:**
```
❌ Diff validation failed (3 issues)
  ❌ Unexpected files changed: config/database.yml
  ⚠️ Large change detected: 412 lines (threshold: 200)
  ❌ Debug statement left in code: found 'debugger' in changes
```

---

## Configuration Guide

### Minimal Configuration

Start with this basic configuration:

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

See `sugar/quality_gates/config_example.yaml` for a complete configuration with all options.

### Configuration by Use Case

**Use Case 1: Python/Django Project**

```yaml
quality_gates:
  enabled: true

  mandatory_testing:
    enabled: true
    test_commands:
      default: "pytest"
      unit: "pytest tests/unit/"
      integration: "pytest tests/integration/"
    auto_detect_required_tests:
      enabled: true
      patterns:
        - pattern: "**/*_controller.py"
          required_tests: ["integration"]
        - pattern: "**/models/*.py"
          required_tests: ["unit", "integration"]

  functional_verification:
    enabled: true
    methods:
      http_requests:
        enabled: true
    auto_detect:
      enabled: true
      patterns:
        - pattern: "**/views/*.py"
          verification: "http_requests"
          test_urls: ["/"]

pre_flight_checks:
  enabled: true
  checks:
    - name: "django_server"
      type: "port_check"
      port: 8000
    - name: "database"
      type: "command"
      command: "python manage.py check --database default"
```

**Use Case 2: Ruby on Rails Project**

```yaml
quality_gates:
  enabled: true

  mandatory_testing:
    enabled: true
    test_commands:
      default: "bundle exec rspec"
      unit: "bundle exec rspec spec/models"
      integration: "bundle exec rspec spec/requests"

  functional_verification:
    enabled: true
    auto_detect:
      patterns:
        - pattern: "app/controllers/**/*.rb"
          verification: "http_requests"
          test_urls: ["/"]

pre_flight_checks:
  enabled: true
  checks:
    - name: "rails_server"
      type: "port_check"
      port: 3000
    - name: "database"
      type: "command"
      command: "rails runner 'ActiveRecord::Base.connection'"
```

---

## Task Examples

### Example 1: Bug Fix with Full Verification

```python
task = {
    "id": "fix-login-redirect",
    "title": "Fix /login redirect to homepage",
    "type": "bug_fix",
    "priority": 5,

    # Expected file changes
    "files_to_modify": {
        "expected": [
            "app/controllers/sessions_controller.rb",
            "spec/requests/sessions_spec.rb"
        ]
    },

    # Success criteria - what must be verified
    "success_criteria": [
        {
            "type": "http_status",
            "url": "http://localhost:3000/login",
            "expected": 200
        },
        {
            "type": "http_no_redirect",
            "url": "http://localhost:3000/login",
            "disallowed_status": [301, 302, 303, 307, 308]
        },
        {
            "type": "test_suite",
            "command": "bundle exec rspec spec/requests/sessions_spec.rb",
            "expected_failures": 0,
            "expected_errors": 0
        }
    ],

    # Functional verifications - verify it actually works
    "functional_verifications": [
        {
            "type": "http_request",
            "url": "http://localhost:3000/login",
            "method": "GET",
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

**Workflow:**
1. ✅ Pre-flight checks verify Rails server is running
2. ✅ Sugar makes code changes
3. ✅ Tests run and must pass (mandatory)
4. ✅ HTTP request verifies /login returns 200
5. ✅ HTTP request verifies no redirect occurs
6. ✅ Success criteria all verified
7. ✅ Diff validated (only expected files changed)
8. ✅ Commit allowed with evidence

---

### Example 2: Feature Implementation

```python
task = {
    "id": "add-user-profile",
    "title": "Add user profile page",
    "type": "feature",
    "priority": 3,

    "files_to_modify": {
        "expected": [
            "app/controllers/users_controller.rb",
            "app/views/users/profile.html.erb",
            "config/routes.rb",
            "spec/requests/users_spec.rb"
        ]
    },

    "success_criteria": [
        {
            "type": "http_status",
            "url": "http://localhost:3000/users/1/profile",
            "expected": 200
        },
        {
            "type": "string_in_file",
            "file_path": "config/routes.rb",
            "search_string": "get '/users/:id/profile'"
        },
        {
            "type": "test_suite",
            "command": "bundle exec rspec spec/requests/users_spec.rb",
            "expected_failures": 0
        }
    ],

    "functional_verifications": [
        {
            "type": "http_request",
            "url": "http://localhost:3000/users/1/profile",
            "expected_status": 200
        }
    ]
}
```

---

### Example 3: Refactoring with No Functional Changes

```python
task = {
    "id": "refactor-user-model",
    "title": "Refactor user model to use concerns",
    "type": "refactoring",
    "priority": 2,

    "files_to_modify": {
        "expected": [
            "app/models/user.rb",
            "app/models/concerns/authenticatable.rb",
            "spec/models/user_spec.rb"
        ]
    },

    # For refactoring, focus on tests
    "success_criteria": [
        {
            "type": "test_suite",
            "command": "bundle exec rspec spec/models/user_spec.rb",
            "expected_failures": 0
        },
        {
            "type": "file_exists",
            "file_path": "app/models/concerns/authenticatable.rb"
        }
    ]
}
```

---

## Troubleshooting

### Common Issues

**1. "Pre-flight check failed: Port 3000 not listening"**

**Solution:**
- Start the development server: `rails server` or `python manage.py runserver`
- Or disable the check if not needed:
  ```yaml
  required_for: []  # Empty list = not required for any tasks
  ```

**2. "Tests failed with 0 failures but quality gate blocked commit"**

**Cause:** Tests might have errors (not failures)

**Solution:** Check the test evidence file:
```bash
cat .sugar/test_evidence/task-123.txt
```

Look for errors vs failures. Both must be zero.

**3. "HTTP request verification failed with 404"**

**Solution:**
- Verify the URL is correct
- Check the development server is running
- Check routes are configured: `rails routes | grep login`
- Look at server logs for errors

**4. "Unexpected files changed: config/database.yml"**

**Solution:**
- Add file to `task.files_to_modify.expected`
- Or enable `allow_additional_files: true` in config
- Or provide justification if prompted

**5. "Diff validation failed: Debug statement left in code"**

**Solution:**
- Remove the debug statement (e.g., `debugger`, `console.log`, `binding.pry`)
- Or temporarily disable pattern validation if intentional:
  ```yaml
  git_diff_validation:
    enabled: false
  ```

**6. "Retry logic not working - task failed immediately"**

**Solution:**
- Check `verification_failure_handling.enabled: true`
- Verify `max_retries` is set correctly
- Check that failure type matches configuration

### Debug Mode

Enable detailed logging:

```yaml
quality_gates:
  debug: true  # Enables verbose logging
```

### Evidence Files

All evidence is stored for debugging:

- **Test evidence:** `.sugar/test_evidence/{task_id}.txt`
- **Evidence report:** `.sugar/evidence/{task_id}_evidence.json`
- **Failure reports:** `.sugar/failures/{task_id}.md`

---

## Best Practices

### 1. Start Simple, Add Gradually

**Phase 1: Start with basics**
```yaml
quality_gates:
  enabled: true
  mandatory_testing:
    enabled: true
```

**Phase 2: Add functional verification**
```yaml
functional_verification:
  enabled: true
```

**Phase 3: Add all features**
```yaml
pre_flight_checks:
  enabled: true
git_diff_validation:
  enabled: true
```

### 2. Define Clear Success Criteria

**Good:**
```python
"success_criteria": [
    {
        "type": "http_status",
        "url": "http://localhost:3000/login",
        "expected": 200
    },
    {
        "type": "test_suite",
        "command": "pytest tests/test_login.py",
        "expected_failures": 0
    }
]
```

**Bad (too vague):**
```python
"success_criteria": [
    {
        "type": "manual",
        "description": "verify login works"
    }
]
```

### 3. Use Auto-Detection

Let Sugar detect verification needs based on file changes:

```yaml
functional_verification:
  auto_detect:
    enabled: true
    patterns:
      - pattern: "app/controllers/**/*.rb"
        verification: "http_requests"
        test_urls: ["/"]
```

### 4. Include Pre-Flight Checks

Fail fast if environment isn't ready:

```yaml
pre_flight_checks:
  enabled: true
  block_execution_if_failed: true
  checks:
    - name: "server_running"
      type: "port_check"
      port: 3000
    - name: "tests_runnable"
      type: "command"
      command: "bundle exec rspec --dry-run"
```

### 5. Enable Retry Logic

Reduce false negatives from transient failures:

```yaml
verification_failure_handling:
  enabled: true
  on_test_failure:
    max_retries: 2
```

### 6. Validate Diffs

Prevent scope creep and debug statements:

```yaml
git_diff_validation:
  enabled: true
  before_commit:
    max_lines_changed: 500
    disallow_patterns:
      - pattern: "debugger"
        reason: "Debug statement"
```

### 7. Review Evidence Files

After task completion, review evidence:

```bash
# Test evidence
cat .sugar/test_evidence/task-123.txt

# Full evidence report
cat .sugar/evidence/task-123_evidence.json

# Commit message includes evidence links
git log -1
```

### 8. Use Strict Mode for Truth Enforcement

Require proof for all claims:

```yaml
truth_enforcement:
  enabled: true
  mode: "strict"  # Blocks unproven claims
  block_unproven_success: true
```

### 9. Configure Expected Files

Define which files should change:

```python
task = {
    "files_to_modify": {
        "expected": [
            "app/models/user.rb",
            "spec/models/user_spec.rb"
        ]
    }
}
```

### 10. Monitor Failure Reports

Review failures to improve quality:

```bash
# List recent failures
ls -lt .sugar/failures/

# Read failure report
cat .sugar/failures/task-123.md
```

---

## Benefits

### Trust & Reliability
- ✅ No more false positives
- ✅ Sugar's reports become trustworthy
- ✅ Evidence trail for every claim
- ✅ Verifiable success criteria

### Quality Enforcement
- ✅ Tests must run and pass
- ✅ Functionality must be verified
- ✅ No bypassing quality requirements
- ✅ Debug statements caught before commit

### Time Savings
- ✅ Fail fast with pre-flight checks
- ✅ Auto-detection reduces manual work
- ✅ Retry logic reduces false negatives
- ✅ Detailed failure reports speed debugging

### Confidence
- ✅ Know that claims have proof
- ✅ Actual functionality verified
- ✅ Environment validated before work starts
- ✅ Changes match expectations

---

## Breaking Changes

Quality Gates may cause tasks to **fail** that previously would have been marked "completed".

**This is intentional.**

It's better to:
- Fail tasks correctly
- Identify real issues
- Build trust in the system

Than to:
- Claim false success
- Ship broken code
- Lose trust in automation

**Quality > Speed**

---

## Implementation Status

**Phase 1 (Critical):** ✅ Complete
- Feature 1: Mandatory Test Execution
- Feature 3: Success Criteria Verification
- Feature 8: Truth Enforcement

**Phase 2 (High Priority):** ✅ Complete
- Feature 2: Functional Verification Layer
- Feature 6: Task Pre-Flight Checks

**Phase 3 (Enhancement):** ✅ Complete
- Feature 7: Verification Failure Handling
- Feature 10: Work Diff Validation

**Total:** 7 of 10 features implemented (70%)

**Not Yet Implemented:**
- Feature 4: Evidence-Based Reporting (enhancement)
- Feature 5: Claude Code Integration (MCP inheritance)
- Feature 9: Task Definition Improvements (schema validation)

---

## See Also

- [Phase 1 README](README.md) - Phase 1 feature documentation
- [Phase 2 & 3 Documentation](PHASE2_AND_3.md) - Phase 2 & 3 feature documentation
- [Configuration Examples](config_example.yaml) - Complete configuration reference
- [Integration Guide](INTEGRATION.md) - How to integrate quality gates
- [Test Suite](../../tests/test_quality_gates.py) - Quality gates tests

---

**Created:** 2025-10-15
**Version:** 2.1.0
**Response to:** Sugar claiming fixes without verification incident
**Status:** 7 of 10 features complete, all critical features implemented
