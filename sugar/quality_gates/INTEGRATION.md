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
   a. Get list of changed files
   b. Extract claims from execution result
   c. Run quality gate validation
   d. If validation fails:
      - Log error
      - Store failure in database
      - Return False (block commit)
   e. If validation passes:
      - Log success
      - Append evidence to commit message
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

Define success criteria in your tasks:

```python
work_item = {
    "id": "task-123",
    "title": "Fix login bug",
    "type": "bug_fix",
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
    ]
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
- `.sugar/test_evidence/{task_id}.txt` - Test execution logs
- `.sugar/evidence/{task_id}.json` - Complete evidence report

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
┌─────────────────────────────────────────────────────────┐
│                  WorkflowOrchestrator                    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  complete_work_execution()                      │    │
│  │                                                  │    │
│  │  1. Check uncommitted changes                   │    │
│  │  2. Get changed files                           │    │
│  │  3. Extract claims                              │    │
│  │  4. Call QualityGatesCoordinator               │    │
│  │     ├─ TestExecutionValidator                   │    │
│  │     ├─ SuccessCriteriaVerifier                 │    │
│  │     └─ TruthEnforcer                           │    │
│  │  5. Block or allow commit                       │    │
│  │  6. Append evidence to message                  │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Future Enhancements (Phase 2 & 3)

Coming in future phases:
- HTTP request verification (Phase 2)
- Browser automation verification (Phase 2)
- Claude Code MCP integration (Phase 3)
- Retry logic for flaky tests (Phase 3)
- Advanced evidence reporting (Phase 2)

## See Also

- [Quality Gates README](README.md) - Feature overview and benefits
- [Configuration Example](config_example.yaml) - Complete configuration
- [Test Suite](../../tests/test_quality_gates.py) - Integration tests
