# Configuration Best Practices

Essential configuration patterns and best practices for Sugar.

## 🛡️ Global Directory Exclusions

### The Problem

By default, Sugar's discovery modules (`code_quality`, `test_coverage`) might scan directories that should be ignored:
- Virtual environments (`venv`, `.venv`, `env`)
- Build artifacts (`build`, `dist`, `coverage`)
- Development tools (`.tox`, `.nox`, `.pytest_cache`)
- Dependencies (`node_modules`)

### The Solution: Global Exclusions

Configure global exclusions that apply to ALL discovery modules:

```yaml
# .sugar/config.yaml
sugar:
  discovery:
    # Global exclusions for all discovery modules
    global_excluded_dirs: [
      "node_modules", ".git", "__pycache__", 
      "venv", ".venv", "env", ".env", "ENV", 
      "env.bak", "venv.bak", "virtualenv",
      "build", "dist", ".tox", ".nox",
      "coverage", "htmlcov", ".pytest_cache",
      ".sugar", ".claude"
    ]
    
    code_quality:
      enabled: true
      excluded_dirs: [
        "node_modules", ".git", "__pycache__", 
        "venv", ".venv", "env", ".env", "ENV", 
        "env.bak", "venv.bak", "virtualenv",
        "build", "dist", ".tox", ".nox",
        "coverage", "htmlcov", ".pytest_cache",
        ".sugar", ".claude"
      ]
      
    test_coverage:
      enabled: true
      source_dirs: ["src", "lib", "app"]
      test_dirs: ["tests", "test", "__tests__"]
      excluded_dirs: [
        "node_modules", ".git", "__pycache__", 
        "venv", ".venv", "env", ".env", "ENV", 
        "env.bak", "venv.bak", "virtualenv",
        "build", "dist", ".tox", ".nox",
        "coverage", "htmlcov", ".pytest_cache",
        ".sugar", ".claude"
      ]
```

### Why Each Discovery Module Needs Exclusions

**Current Architecture:** Each discovery module (`code_quality`, `test_coverage`) operates independently and needs its own exclusion configuration.

**Future Enhancement:** The `global_excluded_dirs` will be implemented to automatically apply to all modules.

## 🎯 Virtual Environment Patterns

### All Virtual Environment Variations

```yaml
excluded_dirs: [
  # Python virtual environments
  "venv",           # python -m venv venv
  ".venv",          # python -m venv .venv
  "env",            # python -m venv env
  ".env",           # python -m venv .env (not environment files)
  "ENV",            # python -m venv ENV
  "env.bak",        # backup environments
  "venv.bak",       # backup environments
  "virtualenv",     # older virtualenv tool
  
  # Node.js
  "node_modules",   # npm/yarn dependencies
  
  # Build and test artifacts
  "build",          # Build output
  "dist",           # Distribution files
  ".tox",           # Tox testing environments
  ".nox",           # Nox testing environments
  "coverage",       # Coverage reports
  "htmlcov",        # HTML coverage reports
  ".pytest_cache",  # Pytest cache
  
  # Development tools
  "__pycache__",    # Python bytecode cache
  ".mypy_cache",    # MyPy cache
  ".ruff_cache",    # Ruff cache
  
  # Version control and configs
  ".git",           # Git repository data
  ".sugar",         # Sugar configuration directory
  ".claude",        # Claude CLI session data
]
```

## 📂 Project-Specific Exclusions

### Web Application Project

```yaml
sugar:
  discovery:
    code_quality:
      excluded_dirs: [
        # Standard exclusions
        "node_modules", "venv", ".venv", "build", "dist",
        
        # Web-specific
        "static/vendor",     # Third-party CSS/JS
        "assets/libs",       # Library assets
        "public/uploads",    # User uploads
        "media",            # Media files
        "logs",             # Application logs
        
        # Framework-specific
        ".next",            # Next.js
        ".nuxt",            # Nuxt.js
        "dist",             # Vue/React builds
        "coverage",         # Test coverage
      ]
```

### Python Package Project

```yaml
sugar:
  discovery:
    code_quality:
      excluded_dirs: [
        # Standard exclusions
        "venv", ".venv", "build", "dist",
        
        # Python packaging
        "*.egg-info",       # Package metadata
        ".eggs",            # Setuptools eggs
        "wheelhouse",       # Wheel cache
        
        # Documentation
        "docs/_build",      # Sphinx builds
        "site",             # MkDocs builds
        
        # Testing
        ".tox",             # Tox environments
        ".nox",             # Nox environments
        ".pytest_cache",    # Pytest cache
        "htmlcov",          # Coverage HTML
      ]
```

### Monorepo Project

```yaml
sugar:
  discovery:
    code_quality:
      excluded_dirs: [
        # Standard exclusions
        "node_modules", "venv", ".venv",
        
        # Monorepo-specific
        "*/node_modules",   # Per-package dependencies
        "*/build",          # Per-package builds
        "*/dist",           # Per-package distributions
        "packages/*/coverage", # Per-package coverage
        
        # Workspace tools
        ".yarn",            # Yarn cache
        ".pnpm-store",      # PNPM store
        "lerna-debug.log",  # Lerna logs
      ]
```

## ⚡ Performance Optimization

### Large Project Configuration

```yaml
sugar:
  discovery:
    code_quality:
      max_files_per_scan: 25  # Reduce from default 50
      excluded_dirs: [
        # Add more aggressive exclusions
        "examples", "samples", "demo", "playground",
        "docs", "documentation", ".github",
        "scripts", "tools", "utilities",
        "vendor", "third_party", "external"
      ]
      
    test_coverage:
      # Focus on core source directories only
      source_dirs: ["src"]  # Remove "lib", "app", etc.
      excluded_dirs: [
        # Same as code_quality exclusions
        "examples", "samples", "demo", "playground",
        "docs", "documentation", ".github"
      ]
```

### High-Frequency Development

```yaml
sugar:
  loop_interval: 300  # 5 minutes - shorter cycles
  discovery:
    code_quality:
      max_files_per_scan: 15  # Quick scans
      excluded_dirs: [
        # Include standard exclusions + temporary directories
        "tmp", "temp", "cache", ".cache",
        "logs", "log", ".logs"
      ]
```

## 🧪 Testing Configuration

### Test Environment Setup

```yaml
# .sugar/config.yaml for testing
sugar:
  dry_run: true  # Safe for testing
  
  discovery:
    code_quality:
      enabled: true
      max_files_per_scan: 10  # Small batches for testing
      excluded_dirs: [
        # Minimal exclusions for testing
        "venv", ".venv", "node_modules", 
        ".git", "__pycache__", ".sugar"
      ]
      
    test_coverage:
      enabled: false  # Disable to focus on code_quality testing
```

## 🔍 Debugging Discovery Issues

### Enable Debug Logging

```yaml
sugar:
  logging:
    level: "DEBUG"
    file: ".sugar/sugar.log"
    
  discovery:
    code_quality:
      # Temporarily reduce scope for debugging
      max_files_per_scan: 5
      excluded_dirs: ["venv", ".venv", "node_modules"]
```

### Test Discovery Manually

```bash
# Create test structure
mkdir -p test-project/{src,venv/lib,node_modules}
touch test-project/src/main.py
touch test-project/venv/lib/package.py

# Initialize Sugar
cd test-project
sugar init

# Run discovery in debug mode
SUGAR_LOG_LEVEL=DEBUG sugar run --dry-run --once

# Check what files were discovered
grep -i "scanning\|discovered\|excluding" .sugar/sugar.log
```

## 📋 Checklist: Proper Exclusions

- [ ] **Virtual environments**: `venv`, `.venv`, `env`, `.env`
- [ ] **Dependencies**: `node_modules`, `vendor`
- [ ] **Build artifacts**: `build`, `dist`, `target`
- [ ] **Test artifacts**: `.tox`, `.nox`, `coverage`, `htmlcov`
- [ ] **Caches**: `__pycache__`, `.pytest_cache`, `.mypy_cache`
- [ ] **VCS**: `.git`, `.svn`, `.hg`
- [ ] **Sugar**: `.sugar`, `.claude`
- [ ] **Project-specific**: Add any custom build/temp directories

## 🚀 Quick Setup Script

```bash
#!/bin/bash
# setup-sugar-exclusions.sh

cat >> .sugar/config.yaml << 'EOF'
sugar:
  discovery:
    global_excluded_dirs: [
      "node_modules", ".git", "__pycache__", 
      "venv", ".venv", "env", ".env", "ENV", 
      "env.bak", "venv.bak", "virtualenv",
      "build", "dist", ".tox", ".nox",
      "coverage", "htmlcov", ".pytest_cache",
      ".sugar", ".claude"
    ]
    
    code_quality:
      excluded_dirs: [
        "node_modules", ".git", "__pycache__", 
        "venv", ".venv", "env", ".env", "ENV", 
        "env.bak", "venv.bak", "virtualenv",
        "build", "dist", ".tox", ".nox",
        "coverage", "htmlcov", ".pytest_cache",
        ".sugar", ".claude"
      ]
      
    test_coverage:
      excluded_dirs: [
        "node_modules", ".git", "__pycache__", 
        "venv", ".venv", "env", ".env", "ENV", 
        "env.bak", "venv.bak", "virtualenv",
        "build", "dist", ".tox", ".nox",
        "coverage", "htmlcov", ".pytest_cache",
        ".sugar", ".claude"
      ]
EOF

echo "✅ Sugar exclusions configured!"
```

---

**Remember:** Proper exclusions improve Sugar's performance and ensure it focuses on your actual project code, not dependencies or build artifacts.