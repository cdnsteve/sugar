# Sugar Changelog

All notable changes to the Sugar autonomous development system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-08-22

### 🎯 MAJOR RELEASE: Unified Workflow System

This release marks Sugar's first major stable version with comprehensive workflow management for autonomous development.

### Added

#### Unified Workflow System
- **WorkflowOrchestrator**: New centralized workflow management system
- **Workflow Profiles**: Three preconfigured workflow patterns:
  - `solo`: Fast development with direct commits, minimal overhead
  - `balanced`: Small team collaboration with PR workflow and selective issue creation
  - `enterprise`: Full governance with comprehensive tracking and review requirements

#### Configuration System
- **Profile-based configuration** in `.sugar/config.yaml`
- **Conventional commit automation** with work type detection
- **Flexible workflow overrides** for custom team requirements
- **Backward compatibility** with existing Sugar installations

#### Workflow Features
- **Consistent git operations** across all work types (tests, quality, errors, GitHub issues)
- **Smart issue handling**: Internal processing for tests/quality, GitHub integration for issue-sourced work
- **Branch management**: Automatic feature branch creation for PR workflows
- **Commit message automation**: Work type detection with conventional commit formatting

### Changed

#### Core Architecture
- **Replaced GitHub-specific workflows** with unified workflow orchestrator
- **Centralized git operations** through workflow profiles
- **Standardized work execution pipeline** for all discovery modules
- **Enhanced error handling** and workflow cleanup on failures

#### Discovery Integration
- **Test coverage analyzer**: Now handles discovered work through unified workflow
- **Code quality scanner**: Integrated with workflow system for consistent git operations
- **Error monitor**: Uses workflow profiles for commit behavior
- **GitHub watcher**: Maintains issue updates while using unified git workflow

### Technical Details

#### New Components
```
sugar/workflow/
├── __init__.py
└── orchestrator.py     # WorkflowOrchestrator class
```

#### Configuration Schema
```yaml
workflow:
  profile: "solo"  # solo | balanced | enterprise
  custom:          # Optional profile overrides
    git:
      workflow_type: "direct_commit"  # direct_commit | pull_request
      commit_style: "conventional"    # conventional | simple
      auto_commit: true
    github:
      auto_create_issues: false       # Create issues for discovered work
      update_existing_issues: true    # Update GitHub-sourced issues
    discovery:
      handle_internally: true         # Process tests/quality without external tracking
```

#### Workflow Behavior Matrix
| Profile | Git Workflow | GitHub Issues | Commit Style | Target Use Case |
|---------|-------------|---------------|--------------|----------------|
| solo | direct_commit | Internal only | conventional | Individual developers |
| balanced | pull_request | Selective (priority 3+) | conventional | Small teams |
| enterprise | pull_request | All work tracked | conventional | Large teams/compliance |

### Fixed
- **Logging configuration**: Fixed hardcoded log paths, now respects config settings
- **Directory creation**: Automatic creation of log directories during initialization
- **Version reporting**: Fixed --version flag requiring subcommands
- **Path security**: Resolved directory traversal vulnerabilities in discovery modules

### Infrastructure
- **Semantic versioning**: Established version management practices
- **Automated testing**: Workflow system tested across all profiles
- **Documentation**: Comprehensive workflow documentation and examples

---

## [0.2.0] - 2025-08-22

### Added
- **Logging Configuration Fix**: Sugar now writes logs to configured path instead of hardcoded location
- **Automatic Log Directory Creation**: Log directories created automatically during initialization
- **Config-based Logging**: Logging respects `.sugar/config.yaml` settings

### Fixed  
- **Log File Location**: Fixed Sugar writing to wrong log file location
- **sugar logs -f**: Now works correctly out of the box without manual setup

---

## [1.0.1] - 2025-08-22

### Fixed
- **Initialization Experience**: Removed unnecessary "Sugar has been successfully initialized" work item
- **Clean First Run**: Sugar no longer creates bogus work items during project initialization
- **Directory Structure**: Use `.gitkeep` instead of sample files to preserve log directory structure
- **Cleanup Enhancement**: Added pattern to remove existing initialization work items

### Changed
- **Cleaner Setup**: First-time Sugar users see only real work, no confusing initialization tasks

---

## [1.1.0] - 2025-08-22

### Added

#### Comprehensive Timing Tracking System
- **Database Schema**: Added timing columns to work_items table
  - `total_execution_time`: Cumulative Claude processing time across retries
  - `started_at`: Timestamp when work first began
  - `total_elapsed_time`: Wall clock time from start to completion
- **Automatic Migration**: Existing Sugar databases get timing columns automatically
- **CLI Display Enhancements**: 
  - `sugar list`: Shows timing for completed/failed tasks (⏱️ 5.2s | 🕐 2m 15s)
  - `sugar view`: Detailed timing information with human-readable durations
- **Core Integration**: Timing tracked automatically during work execution
- **Cumulative Tracking**: Execution time accumulates across failed retries
- **Duration Formatting**: Smart formatting (5.2s, 2m 15s, 1h 30m)

#### Performance Insights
- **Work Complexity Analysis**: See which tasks take longest to complete
- **Retry Impact Tracking**: Understand cumulative cost of failed attempts  
- **Productivity Metrics**: Track actual vs. wall clock time for work items
- **Bottleneck Identification**: Identify slow work types and patterns

### Technical Details
- **Database Migration**: Automatic column addition with backwards compatibility
- **Timing Calculation**: Uses SQLite julianday functions for precise elapsed time
- **Error Handling**: Graceful fallbacks for missing timing data
- **Test Coverage**: Comprehensive test suite for all timing scenarios

---

## [Unreleased]

### Planned Features
- CI/CD pipeline with GitHub Actions  
- Docker support for containerized deployment
- Pre-commit hooks for code quality
- Security scanning with bandit and safety
- Type checking with mypy
- Automated release workflow
- Performance metrics and monitoring
- Enhanced team collaboration features

## [0.1.0] - 2024-01-01

### Added
- Initial release of Sugar (formerly Claude CCAL)
- AI-powered autonomous development system
- Claude Code CLI integration
- Project-specific task management
- Error log discovery and processing
- Code quality analysis
- Test coverage analysis
- GitHub integration support
- SQLite-based task storage
- Configurable discovery modules
- Dry-run mode for safe testing
- Comprehensive CLI interface
- Project isolation with `.sugar/` directories

### Features
- `sugar init` - Initialize Sugar in any project
- `sugar add` - Add tasks manually
- `sugar list` - List and filter tasks
- `sugar status` - Show system status
- `sugar run` - Start autonomous development
- `sugar view` - View task details
- `sugar update` - Update existing tasks
- `sugar remove` - Remove tasks

### Documentation
- Complete README with installation instructions
- Library usage guide
- Configuration examples
- Troubleshooting guide
- Multi-project setup instructions