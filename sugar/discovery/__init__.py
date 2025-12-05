"""
Discovery Module - Work Discovery Sources for Sugar's Autonomous Development.

This module provides the discovery layer that identifies potential work items from
various sources. Discovery components analyze the codebase and external integrations
to find actionable development tasks that Sugar can process autonomously.

Architecture Overview
---------------------
The discovery system operates through four specialized analyzers, each targeting
a different source of potential work:

**Error Log Monitoring** (``ErrorLogMonitor``):
    - Scans log files for errors, warnings, and feedback patterns
    - Generates maintenance tasks from file modifications
    - Supports both JSON and plain text log formats
    - Configurable error pattern detection and age filtering

**GitHub Issue Watching** (``GitHubWatcher``):
    - Monitors GitHub repository for assigned or labeled issues
    - Supports both ``gh`` CLI and PyGitHub authentication methods
    - Handles issue comments, assignments, and PR creation
    - Configurable label-based filtering for issue inclusion/exclusion

**Code Quality Scanning** (``CodeQualityScanner``):
    - Analyzes source files for code quality issues
    - Detects common problems: long functions, TODO comments, complexity issues
    - Supports Python, JavaScript, and TypeScript files
    - Prioritizes issues by severity and provides actionable work items

**Test Coverage Analysis** (``TestCoverageAnalyzer``):
    - Identifies source files missing corresponding test files
    - Analyzes test quality: assertion counts, edge cases, docstrings
    - Detects complex functions that need additional testing
    - Prioritizes based on file importance and complexity metrics

**Prompt Templates** (``PromptTemplateManager``):
    - Manages templates for external tool output interpretation
    - Supports security analysis, test coverage, and lint analysis templates
    - Enables consistent AI-powered interpretation of tool outputs

**External Tool Configuration** (``ExternalToolConfig``):
    - Manages configuration for external analysis tools
    - Validates tool configuration schemas
    - Supports environment variable expansion in tool configurations

Usage Example
-------------
Basic discovery operations::

    from sugar.discovery import (
        ErrorLogMonitor,
        GitHubWatcher,
        CodeQualityScanner,
        TestCoverageAnalyzer,
    )

    # Initialize with configuration
    config = load_config()

    # Discover work from error logs
    error_monitor = ErrorLogMonitor(config)
    error_items = await error_monitor.discover()

    # Watch for GitHub issues
    github_watcher = GitHubWatcher(config)
    github_items = await github_watcher.discover()

    # Scan for code quality issues
    quality_scanner = CodeQualityScanner(config)
    quality_items = await quality_scanner.discover()

    # Analyze test coverage gaps
    coverage_analyzer = TestCoverageAnalyzer(config)
    coverage_items = await coverage_analyzer.discover()

    # Each component also supports health checks
    health = await error_monitor.health_check()

Integration Points
------------------
The discovery module integrates with several other Sugar components:

- **Core Loop** (``sugar.core.loop``): Main orchestrator that invokes discovery sources
- **Work Queue** (``sugar.storage.work_queue``): Stores discovered work items
- **Learning System** (``sugar.learning``): Provides feedback on discovery effectiveness

Common Interface
----------------
All discovery components share a common interface:

- ``discover() -> List[WorkItem]``: Async method returning discovered work items
- ``health_check() -> Dict``: Async method returning component health status

See Also
--------
- ``sugar.core.loop``: Main execution loop that uses these discovery sources
- ``sugar.storage.work_queue``: Work item storage and retrieval
- ``sugar.learning``: Adaptive learning from discovery outcomes
"""

from .code_quality import CodeQualityScanner
from .error_monitor import ErrorLogMonitor
from .github_watcher import GitHubWatcher
from .test_coverage import TestCoverageAnalyzer
from .prompt_templates import (
    PromptTemplateManager,
    create_tool_interpretation_prompt,
    DEFAULT_TOOL_INTERPRETATION_TEMPLATE,
    SECURITY_ANALYSIS_TEMPLATE,
    TEST_COVERAGE_TEMPLATE,
    LINT_ANALYSIS_TEMPLATE,
)
from .external_tool_config import (
    ExternalToolConfig,
    ExternalToolConfigError,
    validate_external_tools_config,
    parse_external_tools_from_discovery_config,
    expand_env_vars,
    get_external_tools_config_schema,
)
from .orchestrator import (
    ToolOrchestrator,
    ToolResult,
    DEFAULT_TIMEOUT_SECONDS,
)

__all__ = [
    # Error and log monitoring
    "ErrorLogMonitor",  # Scans log files for errors and generates maintenance tasks
    # GitHub integration
    "GitHubWatcher",  # Monitors GitHub issues and integrates with repository
    # Code quality analysis
    "CodeQualityScanner",  # Scans source files for code quality issues
    # Test coverage analysis
    "TestCoverageAnalyzer",  # Identifies test coverage gaps and quality issues
    # Prompt templates for external tool interpretation
    "PromptTemplateManager",
    "create_tool_interpretation_prompt",
    "DEFAULT_TOOL_INTERPRETATION_TEMPLATE",
    "SECURITY_ANALYSIS_TEMPLATE",
    "TEST_COVERAGE_TEMPLATE",
    "LINT_ANALYSIS_TEMPLATE",
    # External tool configuration
    "ExternalToolConfig",
    "ExternalToolConfigError",
    "validate_external_tools_config",
    "parse_external_tools_from_discovery_config",
    "expand_env_vars",
    "get_external_tools_config_schema",
    # Tool orchestration
    "ToolOrchestrator",
    "ToolResult",
    "DEFAULT_TIMEOUT_SECONDS",
]
