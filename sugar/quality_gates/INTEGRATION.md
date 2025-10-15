# Quality Gates Integration Guide

This guide explains how Quality Gates are integrated into Sugar's workflow and how to enable/configure them.

## Overview

Quality Gates are integrated into the **WorkflowOrchestrator** to validate work before commits are made. The gates run automatically as part of the commit workflow when enabled.

## Integration Points

### 1. Workflow Orchestrator

Located in `sugar/workflow/orchestrator.py`, the orchestrator now:

- Initializes `QualityGatesCoordinator` if quality gates are enabled in config
- Calls quality gate validation before every commit attempt
- Blocks commits that fail quality gate validation
- Appends quality gate evidence to commit messages
- Stores validation failures in the work queue database

### 2. Validation Flow

When `WorkflowOrchestrator.complete_work_execution()` is called:

```
1. Check if there are uncommitted changes
2. If quality gates enabled:
   a. Run pre-flight checks (Phase 2)
      - Verify environment is ready
      - Check ports, tools, services
      - Block if critical checks fail

   b. Get list of changed files

   c. Extract claims from execution result

   d. Run quality gate validation:
      - Phase 1: Mandatory testing, success criteria, truth enforcement
      - Phase 2: Functional verification (HTTP, port checks)
      - Phase 3: Diff validation

   e. If validation fails:
      - Phase 3: Retry with configurable logic
      - Log error
      - Create failure report (Phase 3)
      - Store failure in database
      - Return False (block commit)

   f. If validation passes:
      - Log success
      - Append evidence to commit message
      - Store evidence files

3. Commit changes with evidence
4. Complete workflow (push, PR creation, etc.)
```

## Configuration

### Enable Quality Gates

Add to your `.sugar.yaml`:

```yaml
quality_gates:
  enabled: true

  # Feature 1: Mandatory Test Execution
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
      allow_pending: true
    evidence:
      store_test_output: true
      path: ".sugar/test_evidence/{task_id}.txt"
      include_in_commit_message: true
    auto_detect_required_tests:
      enabled: true
      patterns:
        - pattern: "tests/**/*.py"
          required_tests: ["unit"]
        - pattern: "sugar/**/*.py"
          required_tests: ["unit", "integration"]

  # Feature 3: Success Criteria Verification
  # (Success criteria are defined per-task, not in global config)

  # Feature 8: Truth Enforcement
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

      - claim: "implementation complete"
        proof_required: "success_criteria_verification"
        must_show:
          all_criteria_verified: true
```

### Disable Quality Gates

Set `quality_gates.enabled: false` or omit the config entirely:

```yaml
quality_gates:
  enabled: false
```

## Task-Level Success Criteria

Define success criteria and verification requirements in your tasks:

```python
work_item = {
    "id": "task-123",
    "title": "Fix login bug",
    "type": "bug_fix",

    # Phase 1: Success criteria to verify
    "success_criteria": [
        {
            "type": "http_status",
            "url": "http://localhost:8000/login",
            "expected": 200
        },
        {
            "type": "test_suite",
            "command": "pytest tests/test_login.py",
            "expected_failures": 0,
            "expected_errors": 0
        },
        {
            "type": "file_exists",
            "file_path": "sugar/auth/login.py"
        }
    ],

    # Phase 2: Functional verifications
    "functional_verifications": [
        {
            "type": "http_request",
            "url": "http://localhost:8000/login",
            "method": "GET",
            "expected_status": 200
        },
        {
            "type": "port_listening",
            "port": 8000,
            "host": "localhost"
        }
    ],

    # Phase 3: Expected file changes (for diff validation)
    "files_to_modify": {
        "expected": [
            "sugar/auth/login.py",
            "tests/test_login.py"
        ]
    }
}
```

## Evidence Collection

Quality gates automatically collect evidence:

### Test Evidence
- Command executed
- Exit code
- Failures, errors, pending counts
- Test duration
- Full stdout/stderr captured

### Success Criteria Evidence
- Criterion type
- Expected vs actual values
- Verification status
- Timestamps

### Truth Enforcement Evidence
- Claims made
- Proof required
- Proof found
- Verification status

### Storage

Evidence is stored in:
- `.sugar/test_evidence/{task_id}.txt` - Test execution logs (Phase 1)
- `.sugar/evidence/{task_id}.json` - Complete evidence report (Phase 1)
- `.sugar/verification/{task_id}/` - Functional verification screenshots (Phase 2, when MCP integrated)
- `.sugar/failures/{task_id}.md` - Detailed failure reports (Phase 3)
- `.sugar/failures/{task_id}.json` - Failure report JSON (Phase 3)

Evidence URLs are included in commit messages for traceability.

## Commit Message Enhancement

When quality gates pass, commit messages are automatically enhanced:

```
feat: Implement new feature

Work ID: abc123
Generated with Sugar v2.0.0

Quality Gates:
- Tests: ✅ PASSED
- Success Criteria: ✅ VERIFIED
- Claims Proven: ✅ YES
- Total Evidence: 5 items

Evidence:
- file:///path/to/.sugar/test_evidence/abc123.txt
- file:///path/to/.sugar/evidence/abc123.json
```

## Validation Failure Handling

When quality gates fail:

1. **Commit is blocked** - No changes are committed
2. **Error is logged** with detailed reason
3. **Work item is updated** in database with failure details:
   ```json
   {
     "quality_gate_status": "failed",
     "quality_gate_reason": "Tests failed: 2 failures, 1 error",
     "quality_gate_details": {
       "can_complete": false,
       "tests_passed": false,
       "criteria_verified": false,
       "claims_proven": false,
       "evidence_summary": {...}
     }
   }
   ```
4. **Workflow returns false** - Task remains incomplete

## Modes of Operation

### Strict Mode (Default)
- All validation requirements must pass
- Unproven claims block commits
- No flexibility for exceptions

```yaml
truth_enforcement:
  mode: "strict"
  block_unproven_success: true
```

### Permissive Mode
- Logs warnings for unproven claims
- Allows commits despite unverified claims
- Still blocks on test failures

```yaml
truth_enforcement:
  mode: "permissive"
  block_unproven_success: false
```

## Testing Integration

Run tests to verify integration:

```bash
# All tests including quality gates
pytest tests/ -v

# Only quality gates tests
pytest tests/test_quality_gates.py -v

# With coverage
pytest tests/test_quality_gates.py --cov=sugar/quality_gates
```

## Monitoring and Debugging

### Enable Debug Logging

```yaml
sugar:
  logging:
    level: "DEBUG"
```

Look for these log messages:
- `🔒 Quality Gates enabled for workflow validation`
- `🔒 Running quality gate validation before commit`
- `✅ Quality gates passed: {reason}`
- `❌ Quality gate validation failed: {reason}`

### Evidence Reports

Check evidence reports for validation details:

```bash
# View test evidence
cat .sugar/test_evidence/task-123.txt

# View complete evidence report
cat .sugar/evidence/task-123.json
```

## Troubleshooting

### Quality gates not running

**Symptom**: Commits succeed without validation

**Solutions**:
1. Check `quality_gates.enabled: true` in config
2. Verify config file is loaded correctly
3. Check logs for initialization message
4. Ensure you're using `WorkflowOrchestrator`

### Tests not being executed

**Symptom**: Quality gates pass without running tests

**Solutions**:
1. Check `mandatory_testing.enabled: true`
2. Verify test command is correct
3. Check `auto_detect_required_tests` configuration
4. Manually specify test commands per task type

### Claims not being proven

**Symptom**: Truth enforcement blocks commits

**Solutions**:
1. Ensure tests are actually running
2. Check that evidence is being collected
3. Verify claim patterns match your execution results
4. Use permissive mode temporarily to debug
5. Check evidence reports for details

### Success criteria failing

**Symptom**: Criteria verification blocks commits

**Solutions**:
1. Verify criterion definitions are correct
2. Check if services/URLs are accessible
3. Review criterion actual vs expected values
4. Test criteria manually first
5. Check criterion implementation for type

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    WorkflowOrchestrator                          │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  complete_work_execution()                              │    │
│  │                                                          │    │
│  │  1. Check uncommitted changes                           │    │
│  │  2. Get changed files                                   │    │
│  │  3. Extract claims                                      │    │
│  │  4. Call QualityGatesCoordinator                       │    │
│  │     │                                                    │    │
│  │     ├─ Phase 1: Critical Features                      │    │
│  │     │  ├─ TestExecutionValidator                        │    │
│  │     │  ├─ SuccessCriteriaVerifier                      │    │
│  │     │  ├─ TruthEnforcer                                │    │
│  │     │  └─ EvidenceCollector                            │    │
│  │     │                                                    │    │
│  │     ├─ Phase 2: High Priority                          │    │
│  │     │  ├─ FunctionalVerifier (HTTP, port checks)       │    │
│  │     │  └─ PreFlightChecker (env validation)            │    │
│  │     │                                                    │    │
│  │     └─ Phase 3: Enhancements                           │    │
│  │        ├─ VerificationFailureHandler (retry/escalate)  │    │
│  │        └─ DiffValidator (change validation)            │    │
│  │                                                          │    │
│  │  5. Block or allow commit based on all validations     │    │
│  │  6. Append evidence to message                          │    │
│  └────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

## Phase 2 & 3 Features (Now Available)

### Phase 2: Functional Verification & Pre-Flight Checks

**Feature 2: Functional Verification Layer**

Verifies actual functionality works in the running application:

```yaml
quality_gates:
  functional_verification:
    enabled: true
    required: true

    methods:
      http_requests:
        enabled: true
        tool: "curl"
        timeout: 10

      browser_automation:
        enabled: false  # Requires MCP Chrome DevTools
        tools: ["mcp__chrome-devtools"]
        screenshot_on_verification: true

      database_queries:
        enabled: false  # Future implementation
        require_evidence: true

    auto_detect:
      enabled: true
      patterns:
        - pattern: "app/controllers/**/*.py"
          verification: "http_requests"
          test_urls: ["/"]
          expected_status: [200, 302]
```

**Feature 6: Task Pre-Flight Checks**

Validates environment before starting work:

```yaml
pre_flight_checks:
  enabled: true
  block_execution_if_failed: true

  checks:
    - name: "dev_server_running"
      type: "port_check"
      port: 8000
      host: "localhost"
      required_for: ["ui_changes", "api_changes"]

    - name: "database_accessible"
      type: "command"
      command: "python manage.py check --database default"
      timeout: 10
      required_for: ["model_changes"]

    - name: "test_suite_runnable"
      type: "command"
      command: "pytest --collect-only"
      timeout: 30
      required_for: ["all_tasks"]

    - name: "required_tools_available"
      type: "tool_check"
      tools: ["python", "pytest", "curl"]
      required_for: ["all_tasks"]
```

### Phase 3: Failure Handling & Diff Validation

**Feature 7: Verification Failure Handling**

Retry logic and escalation for failures:

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

**Feature 10: Work Diff Validation**

Validates git changes before commit:

```yaml
git_diff_validation:
  enabled: true

  before_commit:
    validate_files_changed:
      enabled: true
      allowed_files: "from task.files_to_modify.expected"
      allow_additional_files: false

    max_lines_changed: 500
    warn_if_exceeds: 200

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

    if_unexpected_files_changed:
      action: "require_justification"
      prompt: "Why were these additional files changed?"
```

## See Also

- [Quality Gates README](README.md) - Phase 1 feature overview
- [Phase 2 & 3 Documentation](PHASE2_AND_3.md) - Complete Phase 2 & 3 documentation
- [User Guide](USER_GUIDE.md) - Comprehensive user guide for all phases
- [Configuration Example](config_example.yaml) - Complete configuration reference
- [Test Suite](../../tests/test_quality_gates.py) - Integration tests
