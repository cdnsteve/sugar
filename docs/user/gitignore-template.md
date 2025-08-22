# Git Ignore Template for Sugar Projects

Sugar is designed to keep all its files contained within the `.sugar/` directory to avoid cluttering your project. Here's the minimal `.gitignore` addition you need:

## Minimal .gitignore Addition

```gitignore
# Sugar AI - Autonomous Development System
.sugar/
```

That's it! All Sugar files are contained within the `.sugar/` directory:

- `.sugar/config.yaml` - Configuration (may want to commit this)
- `.sugar/sugar.db` - Work queue database  
- `.sugar/sugar.log` - Application logs
- `.sugar/context.json` - Claude AI context
- `.sugar/backups/` - Database backups
- `.sugar/logs/` - Additional log files

## Optional: Commit Configuration

If you want to share Sugar configuration with your team:

```gitignore
# Sugar AI - Autonomous Development System  
.sugar/
!.sugar/config.yaml  # Keep configuration in git
```

## Complete Example

Here's a complete `.gitignore` example for a typical project with Sugar:

```gitignore
# Dependencies
node_modules/
venv/
env/
.venv/

# Build outputs  
dist/
build/
*.pyc
__pycache__/

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Environment variables
.env
.env.local

# Sugar AI - Autonomous Development System
.sugar/

# Optional: Keep Sugar config for team sharing
# !.sugar/config.yaml
```

## Why This Works

Sugar's design philosophy prioritizes clean project structure:

- ✅ **Single directory**: Everything Sugar-related goes in `.sugar/`
- ✅ **No root-level files**: No `sugar.log`, `sugar.db`, etc. in your project root
- ✅ **Isolated configuration**: Each project has its own Sugar instance
- ✅ **Easy cleanup**: Just delete `.sugar/` directory to completely remove Sugar

This makes Sugar much more friendly for existing projects and teams!