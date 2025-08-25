# Sugar Examples

Real-world examples of using Sugar in different development scenarios.

## 🚀 Basic Usage Examples

### Example 1: Web Application Development

```bash
# Initialize Sugar in your web project
cd /path/to/my-webapp
sugar init

# Add specific feature tasks
sugar add "Add user registration form" --type feature --priority 4
sugar add "Implement OAuth login" --type feature --priority 3
sugar add "Add input validation" --type feature --priority 2

# Add bug fixes
sugar add "Fix memory leak in session handling" --type bug_fix --urgent
sugar add "Resolve CSS layout issues on mobile" --type bug_fix --priority 4

# Add testing tasks
sugar add "Write unit tests for auth module" --type test --priority 3
sugar add "Add integration tests for API" --type test --priority 2

# Check what's queued
sugar list

# Test run first
sugar run --dry-run --once

# Start autonomous development
sugar run
```

### Example 2: API Development

```bash
# Initialize in API project
cd /path/to/my-api
sugar init

# Configure for API development
# Edit .sugar/config.yaml to monitor API logs
```

**Configuration for API project:**
```yaml
sugar:
  discovery:
    error_logs:
      enabled: true
      paths: ["logs/api/", "logs/errors/", "/var/log/myapi/"]
      patterns: ["ERROR", "EXCEPTION", "500", "timeout"]
    
    code_quality:
      enabled: true
      source_dirs: ["src", "api", "handlers"]
      file_extensions: [".py", ".js", ".ts"]
    
    test_coverage:
      enabled: true
      source_dirs: ["src", "api"]
      test_dirs: ["tests", "spec"]
```

```bash
# Add API-specific tasks
sugar add "Implement rate limiting" --type feature --priority 4
sugar add "Add API documentation" --type documentation --priority 2
sugar add "Optimize database queries" --type refactor --priority 3

# Start with discovery enabled
sugar run
```

### Example 3: Python Library Development

```bash
cd /path/to/my-python-lib
sugar init

# Configure for Python library
```

**Python library configuration:**
```yaml
sugar:
  discovery:
    code_quality:
      enabled: true
      file_extensions: [".py"]
      excluded_dirs: [
        "node_modules", "venv", ".venv", "env", ".env", 
        "build", "dist", ".tox", ".nox", "coverage",
        ".sugar", ".claude", "__pycache__"
      ]
      max_files_per_scan: 30
    
    test_coverage:
      enabled: true
      source_dirs: ["src", "mylib"]
      test_dirs: ["tests"]
  
  claude:
    timeout: 900  # 15 minutes for complex refactoring
```

```bash
# Add library maintenance tasks
sugar add "Refactor core module for better performance" --type refactor --priority 3
sugar add "Add type hints throughout codebase" --type refactor --priority 2
sugar add "Create comprehensive docstrings" --type documentation --priority 2
sugar add "Add property-based tests" --type test --priority 3

# Let Sugar discover code quality issues
sugar run --dry-run --once  # See what it would find
sugar run
```

## 🔧 Configuration Examples

### Small Project Configuration

```yaml
# .sugar/config.yaml for small projects
sugar:
  loop_interval: 600  # 10 minutes between cycles
  max_concurrent_work: 1  # One task at a time
  dry_run: false
  
  discovery:
    error_logs:
      enabled: true
      paths: ["logs/"]
      max_age_hours: 24
    
    code_quality:
      enabled: true
      max_files_per_scan: 20
      
  claude:
    timeout: 1200  # 20 minutes
```

### Large Project Configuration

```yaml
# .sugar/config.yaml for large projects
sugar:
  loop_interval: 1800  # 30 minutes between cycles
  max_concurrent_work: 2  # More parallel work
  
  discovery:
    error_logs:
      enabled: true
      paths: ["logs/errors/", "logs/critical/", "monitoring/alerts/"]
      patterns: ["CRITICAL", "ERROR", "FATAL"]
      max_age_hours: 12
    
    code_quality:
      enabled: true
      max_files_per_scan: 50
      excluded_dirs: [
        "node_modules", "venv", ".venv", "env", ".env",
        "dist", "build", ".tox", ".nox", "coverage", 
        "docs", "examples", ".git", ".sugar", ".claude"
      ]
      
    github:
      enabled: true
      repo: "myorg/myproject"
      auth_method: "auto"  # Try gh CLI first, fallback to token
      token: "${GITHUB_TOKEN}"
      issue_labels: ["bug", "enhancement", "good-first-issue"]
    
  claude:
    timeout: 2400  # 40 minutes for complex tasks
```

## 📊 Workflow Examples

### Example 1: Bug Triage Workflow

**Scenario:** Your application logs errors that need immediate attention.

**Setup:**
```bash
# Create error log directory
mkdir -p logs/errors/

# Configure Sugar to monitor it
cat > .sugar/config.yaml << EOF
sugar:
  discovery:
    error_logs:
      enabled: true
      paths: ["logs/errors/"]
      patterns: ["ERROR", "CRITICAL", "Exception"]
      scan_interval_minutes: 5
EOF
```

**Simulate error discovery:**
```bash
# Application logs an error
echo '{"level": "CRITICAL", "message": "Database connection failed", "timestamp": "2024-01-15T10:30:00Z"}' > logs/errors/db_error.json

# Sugar will discover this automatically on next cycle
sugar run --once  # Process immediately

# Check what Sugar found
sugar list --type bug_fix --status pending
```

### Example 2: Code Quality Improvement

**Scenario:** Continuous code quality improvements during development.

```bash
# Enable code quality discovery
sugar add "Enable code quality analysis" --type refactor

# Sugar will automatically find:
# - Functions that are too complex
# - Missing docstrings
# - Code duplication
# - Style inconsistencies

# Manual code quality task
sugar add "Refactor authentication module for better testability" --type refactor --priority 3

# Let Sugar run and improve code quality
sugar run
```

### Example 3: Test Coverage Improvement

**Configure test coverage monitoring:**
```yaml
sugar:
  discovery:
    test_coverage:
      enabled: true
      source_dirs: ["src", "app"]
      test_dirs: ["tests", "test"]
      min_coverage_threshold: 80
```

```bash
# Sugar will automatically create tasks for:
# - Files with low test coverage
# - New functions without tests
# - Integration test gaps

# Add manual testing tasks
sugar add "Add end-to-end tests for checkout flow" --type test --priority 4
sugar add "Implement performance tests" --type test --priority 2

sugar run
```

## 🌐 Multi-Project Examples

### Example: Managing Multiple Microservices

```bash
# Service 1: User Authentication
cd /projects/auth-service
sugar init
sugar add "Implement JWT refresh tokens" --type feature --priority 4
nohup sugar run > sugar-auth.log 2>&1 &

# Service 2: Payment Processing  
cd /projects/payment-service
sugar init
sugar add "Add fraud detection" --type feature --priority 5
nohup sugar run > sugar-payment.log 2>&1 &

# Service 3: Notification Service
cd /projects/notification-service
sugar init
sugar add "Implement email templates" --type feature --priority 3
nohup sugar run > sugar-notification.log 2>&1 &

# Monitor all services
function check_all_sugar() {
  for service in auth-service payment-service notification-service; do
    echo "📂 $service"
    cd "/projects/$service"
    sugar status | grep -E "(Total Tasks|Pending|Active|Completed)"
    echo
  done
}

check_all_sugar
```

## 🔍 Monitoring and Debugging Examples

### Example 1: Debug Sugar Behavior

```bash
# Enable debug logging
export SUGAR_LOG_LEVEL=DEBUG
sugar run --dry-run --once

# Or in config
cat > .sugar/config.yaml << EOF
sugar:
  logging:
    level: "DEBUG"
    file: ".sugar/sugar.log"
EOF

# Monitor logs
tail -f .sugar/sugar.log

# Validate configuration
sugar run --validate
```

### Example 2: Monitor Sugar Across Projects

**Multi-project status script:**
```bash
#!/bin/bash
# monitor-sugar.sh

echo "🤖 Sugar Status Across All Projects"
echo "=================================="

for project in ~/projects/*/; do
  if [ -d "$project/.sugar" ]; then
    project_name=$(basename "$project")
    echo "📂 $project_name"
    cd "$project"
    
    # Check if Sugar is running
    if pgrep -f "sugar run" > /dev/null; then
      echo "   Status: 🟢 Running"
    else
      echo "   Status: 🔴 Stopped"
    fi
    
    # Show task counts
    sugar status 2>/dev/null | grep -E "(Total Tasks|Pending|Active|Completed)" | sed 's/^/   /'
    echo
  fi
done
```

## 📈 Performance Optimization Examples

### Example 1: Optimize for Large Codebase

```yaml
# .sugar/config.yaml - Optimized for large projects
sugar:
  loop_interval: 3600  # 1 hour between full scans
  max_concurrent_work: 1
  
  discovery:
    code_quality:
      max_files_per_scan: 25  # Process fewer files per cycle
      excluded_dirs: [
        "node_modules", "venv", ".venv", "env", ".env",
        "dist", "build", ".tox", ".nox", "coverage", 
        "docs", "examples", ".git", ".sugar", ".claude",
        "logs", "tmp", "cache"
      ]
      
    error_logs:
      max_age_hours: 6  # Only recent errors
      patterns: ["CRITICAL", "FATAL"]  # Only severe errors
  
  claude:
    timeout: 1800  # 30 minutes max
```

### Example 2: High-Frequency Development

```yaml
# .sugar/config.yaml - For active development
sugar:
  loop_interval: 300  # 5 minutes
  max_concurrent_work: 2
  
  discovery:
    error_logs:
      scan_interval_minutes: 2  # Quick error detection
      
    code_quality:
      enabled: true
      max_files_per_scan: 15  # Quick scans
      
  claude:
    timeout: 900  # 15 minutes for quick tasks
```

## 🛡️ Safety Examples

### Example 1: Production-Safe Configuration

```yaml
# .sugar/config.yaml - Production environment
sugar:
  dry_run: false  # Only after thorough testing
  max_concurrent_work: 1  # Conservative approach
  
  safety:
    max_retries: 2
    excluded_paths:
      - "/prod"
      - "/var/www"
      - "/etc"
      - ".sugar"
      - ".git"
    max_file_operations: 10
    max_execution_time_minutes: 20
    
  # Only trusted discovery sources
  discovery:
    error_logs:
      enabled: true
      paths: ["logs/application/"]  # Specific log path
    code_quality:
      enabled: false  # Disable for production
    github:
      enabled: false  # Manual review only
```

### Example 2: Development Safety

```bash
# Always test with dry-run first
sugar run --dry-run --once

# Test specific scenarios
echo '{"error": "test error"}' > logs/errors/test.json
sugar run --dry-run --once
rm logs/errors/test.json

# Start with safety enabled
sugar add "Test task" --type test --priority 1
sugar run --dry-run --once  # Verify behavior
# Only then: sugar run
```

## 🎯 Use Case Examples

### Example 1: Solo Developer

**Setup:**
```bash
sugar init
sugar add "Implement user dashboard" --type feature --priority 4
sugar add "Fix responsive layout" --type bug_fix --priority 3
sugar add "Add integration tests" --type test --priority 2

# Configure for solo development
cat > .sugar/config.yaml << EOF
sugar:
  loop_interval: 600  # 10 minutes
  max_concurrent_work: 1
  
  discovery:
    error_logs:
      enabled: true
    code_quality:
      enabled: true
    test_coverage:
      enabled: true
EOF

# Work alongside Sugar
sugar run &  # Run in background
# Continue normal development - Sugar handles maintenance tasks
```

### Example 2: Development Team

**Team coordination:**
```bash
# Each developer runs Sugar on their components
# Shared configuration template (without secrets)

# Developer 1: Frontend
cd frontend/
sugar init
sugar add "Implement new UI components" --type feature --priority 4

# Developer 2: Backend  
cd backend/
sugar init
sugar add "Optimize API performance" --type refactor --priority 3

# Developer 3: Testing
cd testing/
sugar init  
sugar add "Create automated test suite" --type test --priority 4

# Shared GitHub integration prevents duplicate work
```

## 🎯 Priority Management Examples

### Dynamic Priority Adjustments

```bash
# Initial task setup with default priorities
sugar add "Implement search feature" --type feature --priority 3
sugar add "Fix login bug" --type bug_fix --priority 2
sugar add "Update documentation" --type documentation --priority 4

# Production incident - need to reprioritize immediately
sugar priority search-task-id --urgent         # 🔥 Make search urgent
sugar priority login-bug-id --high            # ⚡ Elevate login bug

# After crisis - adjust back to normal workflow  
sugar priority search-task-id --normal        # 📋 Back to normal priority
sugar priority docs-task-id --low             # 📝 Lower priority for docs

# View updated queue
sugar list

# Shows tasks now ordered by new priorities:
# 🔥 P1 [bug_fix] Fix login bug
# 📋 P3 [feature] Implement search feature  
# 📝 P4 [documentation] Update documentation
```

### Sprint Planning Workflow

```bash
# Start of sprint - set priorities based on sprint goals
sugar add "User profile page" --type feature
sugar add "Payment integration" --type feature  
sugar add "Database migration" --type refactor

# Sprint planning meeting decisions
sugar priority profile-id --high              # ⚡ Sprint priority
sugar priority payment-id --urgent            # 🔥 Critical for release
sugar priority migration-id --low             # 📝 Nice to have

# Mid-sprint reprioritization due to customer feedback
sugar priority profile-id --urgent            # 🔥 Customer requested
sugar priority payment-id --normal            # 📋 Can wait

# Shows visual feedback:
# ✅ Priority changed: ⚡ high → 🔥 urgent
#    Task: User profile page
```

These examples show Sugar's flexibility across different project types, team sizes, and development workflows. The key is configuring Sugar appropriately for your specific needs and gradually increasing automation as you gain confidence.