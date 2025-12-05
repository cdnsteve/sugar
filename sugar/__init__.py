"""
Sugar - Autonomous Development Assistant.

Sugar is an AI-powered development system that runs continuously in the
background, executing development tasks autonomously. It functions as a
persistent Claude Code integration that discovers work, executes tasks,
and commits working code.

Key Capabilities
----------------
- **Continuous Execution**: Runs 24/7, working through task queues
- **Task Delegation**: Accepts tasks from interactive sessions or queues
- **Feature Development**: Takes specifications, implements, tests, commits
- **Bug Fixing**: Reads error logs, investigates, implements fixes
- **GitHub Integration**: Creates PRs, updates issues, tracks progress
- **Smart Discovery**: Finds work from errors, issues, and code analysis

Package Architecture
--------------------
Sugar is organized into specialized modules:

- **core**: Main orchestration loop (``SugarLoop``) that coordinates
  discovery, execution, and feedback processing
- **discovery**: Work item sources - error logs, GitHub issues, code
  quality analysis, and test coverage gaps
- **executor**: Claude Code CLI integration with structured request/response
  handling and context persistence
- **storage**: Work queue management and persistence layer
- **learning**: Adaptive scheduling and feedback processing
- **workflow**: Git operations and workflow orchestration
- **quality_gates**: Task verification and validation

Quick Start
-----------
Sugar is primarily used as a CLI tool::

    # Initialize in your project
    sugar init

    # Add tasks
    sugar add "Fix authentication timeout" --type bug_fix

    # Run the autonomous loop
    sugar run

For programmatic access::

    from sugar.core import SugarLoop
    from sugar.executor import StructuredRequest, ClaudeWrapper
    from sugar.discovery import ErrorLogMonitor, CodeQualityScanner

    # Start the autonomous loop
    loop = SugarLoop(".sugar/config.yaml")
    await loop.start()

Version Info
------------
Version information is available via::

    from sugar import __version__
    print(__version__)  # e.g., "2.1.0"

See Also
--------
- CLI documentation: ``sugar --help``
- Project repository: https://github.com/cdnsteve/sugar
- Configuration: ``.sugar/config.yaml``
"""

from sugar.__version__ import (
    __version__,
    __title__,
    __description__,
    __author__,
    __author_email__,
    __url__,
    get_version_info,
)

__all__ = [
    # Version information
    "__version__",
    "__title__",
    "__description__",
    "__author__",
    "__author_email__",
    "__url__",
    "get_version_info",
]
