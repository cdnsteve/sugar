"""
Sugar Core Module - Main Orchestration Loop.

This module provides the central orchestration layer for Sugar's autonomous
development system. It contains the SugarLoop class which coordinates:

- Work discovery from multiple sources (error logs, code quality, test coverage)
- Task execution via Claude Code CLI
- Feedback processing and adaptive learning
- Git workflow management

Key Components
--------------
- ``SugarLoop``: Main orchestrator that runs the autonomous development loop

Usage Example
-------------
Basic loop initialization and execution::

    from sugar.core import SugarLoop

    # Initialize with config file path
    loop = SugarLoop(".sugar/config.yaml")

    # Run the autonomous development loop
    await loop.start()

    # Or run a single cycle
    await loop.run_once()

Integration Points
------------------
The core module integrates with several other Sugar components:

- **Discovery** (``sugar.discovery``): Work item sources (errors, code quality, etc.)
- **Executor** (``sugar.executor``): Claude CLI integration for task execution
- **Storage** (``sugar.storage``): Work queue and persistence
- **Learning** (``sugar.learning``): Feedback processing and adaptive scheduling
- **Workflow** (``sugar.workflow``): Git operations and workflow orchestration
- **Quality Gates** (``sugar.quality_gates``): Task verification and validation

See Also
--------
- ``sugar.main``: CLI entry point that uses SugarLoop
- ``sugar.executor``: Task execution layer
"""

from .loop import SugarLoop

__all__ = [
    "SugarLoop",  # Main orchestration loop for autonomous development
]
