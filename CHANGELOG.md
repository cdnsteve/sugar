# Sugar Changelog

All notable changes to the Sugar autonomous development system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.1] - 2025-08-25

### Fixed
- **sugar view**: Display full commit SHA instead of truncated version (first 8...last 8)
- **Configuration Comments**: Updated agent integration comments to reflect completed implementation
- **Config Template**: Removed outdated "Phase 1" and "Phase 2" references from sugar init template

### Changed
- **Commit Display**: `🔗 Commit: 179a30c4...6ea6fa61` → `🔗 Commit: 179a30c4f1e2a3b4c5d6e7f8g9h0i1j2k3l4m5n6ea6fa61`

---

## [1.3.0] - 2025-08-25

### 🎯 MAJOR RELEASE: Bidirectional Traceability & Enhanced User Experience

This release delivers a developer experience breakthrough with complete traceability between Sugar work items and git commits, plus dramatically improved JSON readability in CLI output.

### Added

#### Bidirectional Traceability System
- **Git → Sugar Traceability**: Work item IDs automatically included in all git commit messages
- **Sugar → Git Traceability**: Commit SHAs captured and stored in work item database
- **Complete Audit Trail**: Full visibility between autonomous work and git changes
- **Database Schema Enhancement**: New `commit_sha` column with automatic migration support
- **CLI Integration**: `sugar view` command displays associated commit SHAs
- **Automatic Capture**: Commit SHAs recorded after successful git operations

#### Enhanced User Experience  
- **Pretty JSON Formatting**: Human-readable JSON display in `sugar view` command
- **Flexible Output Options**: New `--format` flag with `pretty` (default) and `compact` modes
- **Dramatically Improved Readability**: Context and Result fields now scannable and structured
- **Developer-Friendly Output**: Eliminates walls of unreadable JSON text
- **Data Integrity**: Complete information preservation with superior presentation

### Changed
- **sugar view**: Now defaults to pretty JSON formatting for improved readability
- **Commit Messages**: Now include Work ID for complete traceability
- **Database Schema**: Enhanced with commit_sha tracking field

### Technical Details
- Added `get_latest_commit_sha()` method to GitOperations
- Extended `get_work_by_id()` to include commit_sha and timing fields
- Updated WorkflowOrchestrator to capture and store commit SHAs
- Created `format_json_pretty()` utility for terminal JSON display
- Enhanced database migration system for commit_sha column

---

## [1.2.0] - 2025-08-22

### 🎯 MAJOR RELEASE: Structured Claude Agent Integration

This release introduces advanced Claude agent integration with dynamic agent discovery, making Sugar the most sophisticated autonomous development system for Claude.

### Added

#### Structured Claude Agent Integration
- **Dynamic Agent Discovery**: Works with any Claude agents configured locally
- **Intelligent Agent Selection**: Analyzes work characteristics for optimal agent matching
- **Built-in Agent Support**: tech-lead, code-reviewer, social-media-growth-strategist, general-purpose
- **Custom Agent Support**: Users can configure any agent names they prefer
- **Structured Request System**: JSON-based communication with enhanced response parsing
- **Quality Assessment**: 0.0-1.0 quality scores with confidence levels (high/medium/low)
- **Enhanced File Detection**: Tracks changes across 15+ file types
- **Robust Fallback System**: Agent → Basic Claude → Legacy execution paths
- **Performance Analytics**: Execution time, agent success rates, response quality tracking

#### Agent Configuration System
- **Flexible Agent Mapping**: Map work types to specific agents via configuration
- **Agent Selection Priority**: User configuration overrides keyword-based selection
- **Dynamic Agent Types**: Support for any user-configured agent names
- **Comprehensive Agent Analytics**: Track success rates and performance per agent

### Changed
- **Claude Executor**: Now supports both structured agent mode and legacy execution
- **Work Execution**: Enhanced with agent selection logic and structured responses
- **Configuration**: Extended agent section with selection mappings and discovery options
- **Response Processing**: Improved parsing and quality assessment for agent responses

### Technical Details
- Added `StructuredRequest` and `StructuredResponse` dataclasses
- Implemented `AgentType` enum with dynamic agent type support
- Enhanced `ClaudeWrapper` with dual execution paths (structured/legacy)
- Added agent selection algorithms with priority-based keyword matching
- Comprehensive agent performance tracking and analytics

---

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

## [1.2.0] - 2025-08-22

### 🚀 MAJOR RELEASE: Structured Claude Agent Integration

This release introduces comprehensive Claude agent integration capabilities, preparing Sugar for the future of AI-powered development workflows.

### Added

#### Structured Request Foundation (Phase 1)
- **StructuredRequest/StructuredResponse System**: Complete dataclass architecture with JSON serialization
- **RequestBuilder Factory**: Helper methods for creating different request types (basic, agent, continuation)
- **TaskContext System**: Rich context information including work item metadata, file involvement, and session history
- **ExecutionMode/AgentType Enums**: Type-safe agent selection and execution mode management
- **Dual Execution Paths**: Structured and legacy modes for backward compatibility

#### Agent Selection Engine (Phase 2)
- **Intelligent Agent Selection Algorithm**: Analyzes work items (type, title, description, priority) for optimal agent matching
- **5 Supported Agent Types**:
  - `tech-lead`: Strategic analysis, architecture, complex bugs, high-priority work
  - `code-reviewer`: Code quality, refactoring, optimization, best practices
  - `social-media-growth-strategist`: Content strategy, engagement, audience growth
  - `statusline-setup`: Claude Code status line configuration
  - `output-style-setup`: Claude Code output styling and themes
- **Priority-Based Matching**: Specific keywords override general patterns for precise agent selection
- **Configurable Agent Mapping**: Users can customize agent selection rules via config.yaml
- **Triple-Layer Fallback Strategy**: Agent mode → Basic Claude → Legacy execution with graceful degradation

#### Enhanced Response Processing (Phase 3)
- **Agent-Specific Parsing**: Tailored extraction patterns for each agent type's output characteristics
- **Quality Assessment System**: 0.0-1.0 quality scores with confidence levels (high/medium/low)
- **Advanced File Detection**: Regex-based extraction supporting 15+ file types with intelligent path cleaning
- **Enhanced Action Extraction**: Deduplication and intelligent prioritization of action items
- **Multi-Layered Parsing**: JSON → Enhanced → Fallback parsing with comprehensive error handling
- **Performance Analysis**: Execution time optimization detection and workflow efficiency metrics

### Configuration

#### New Config.yaml Sections
```yaml
claude:
  # Structured Request System (Phase 1 of Agent Integration)
  use_structured_requests: true  # Enable structured JSON communication
  structured_input_file: ".sugar/claude_input.json"  # Temp file for complex inputs
  
  # Agent Selection System (Phase 2 of Agent Integration)
  enable_agents: true        # Enable Claude agent mode selection
  agent_fallback: true       # Fall back to basic Claude if agent fails
  agent_selection:           # Map work types to specific agents
    bug_fix: "tech-lead"           # Strategic analysis for bug fixes
    feature: "general-purpose"     # General development for features
    refactor: "code-reviewer"      # Code review expertise for refactoring
    test: "general-purpose"        # General development for tests
    documentation: "general-purpose"  # General development for docs
```

### Technical Implementation

#### Core Architecture Changes
- **Unified Data Flow**: Work items → Structured requests → Enhanced responses → Quality metrics
- **Type-Safe System**: Full enum-based type system preventing configuration errors
- **Zero Breaking Changes**: Existing Sugar installations continue working unchanged
- **Gradual Migration Support**: Users can enable/disable features independently

#### Performance & Monitoring
- **Response Quality Scoring**: Automated assessment of Claude output quality and confidence
- **Agent Selection Logging**: Detailed tracking of agent selection decisions and rationale
- **Execution Analytics**: Performance metrics including timing, fallback usage, and success rates
- **File Operation Tracking**: Comprehensive detection of modified files across different output formats

#### Error Handling & Reliability
- **Robust Fallback System**: Multiple layers of graceful degradation
- **Comprehensive Logging**: Detailed debug information for troubleshooting agent issues
- **Configuration Validation**: Input validation for agent types and execution modes
- **Session State Management**: Proper cleanup and state tracking across execution modes

### Enhanced Features

#### Work Item Processing
- **Context-Aware Execution**: Agent selection considers work item history and previous attempts
- **Session Continuity**: Structured requests maintain context across related tasks
- **Priority-Based Routing**: High-priority work automatically routed to tech-lead agent
- **Intelligent Retry Logic**: Failed agent executions fallback to appropriate alternatives

#### Response Analysis
- **Multi-Pattern File Detection**: Supports tool usage patterns, bullet lists, and direct file mentions
- **Agent-Specific Summaries**: Extraction patterns tailored to each agent's communication style
- **Action Categorization**: Intelligent classification of actions by agent type and work category
- **Content Quality Assessment**: Multi-factor analysis including structure, completeness, and relevance

### Future Compatibility

This release establishes the foundation for native Claude agent mode integration. When Claude CLI officially supports agent modes, Sugar will seamlessly transition from enhanced prompt engineering to direct agent communication.

### Developer Experience

- **Self-Documenting Configuration**: Comprehensive inline documentation in config templates
- **Extensible Architecture**: Easy addition of new agent types and parsing patterns
- **Debug-Friendly Logging**: Detailed execution traces for development and troubleshooting
- **Test Coverage**: Comprehensive test suite covering all three implementation phases

---

## [Unreleased]

### Planned Features
- Native Claude agent mode integration (when Claude CLI supports it)
- CI/CD pipeline with GitHub Actions  
- Docker support for containerized deployment
- Pre-commit hooks for code quality
- Security scanning with bandit and safety
- Type checking with mypy
- Automated release workflow
- Performance metrics dashboard
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