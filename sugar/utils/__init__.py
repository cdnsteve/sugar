"""
Utility Functions and Classes for Sugar.

This module provides supporting utilities for Sugar's autonomous development system.
It contains common operations that are used across multiple Sugar components,
centralizing shared functionality for consistency and maintainability.

Key Components
--------------
- ``GitOperations``: Asynchronous Git operations handler for automated workflows

GitOperations Overview
----------------------
The ``GitOperations`` class provides an async interface to common Git operations
used in Sugar's automated development pipelines. It wraps git CLI commands and
executes them asynchronously using asyncio subprocesses.

Capabilities include:
    - Branch creation and management
    - Staging, committing, and pushing changes
    - Repository state queries (current branch, changed files, uncommitted changes)
    - String formatting utilities for commit messages, PR titles, and branch names

Usage Example
-------------
Basic Git operations::

    from sugar.utils import GitOperations

    # Initialize with repository path (defaults to current directory)
    git_ops = GitOperations("/path/to/repo")

    # Create a feature branch from main
    await git_ops.create_branch("feature/new-feature", base_branch="main")

    # Commit changes with a message
    await git_ops.commit_changes("feat: implement new feature")

    # Push the branch to remote
    await git_ops.push_branch("feature/new-feature")

    # Query repository state
    branch = await git_ops.get_current_branch()
    has_changes = await git_ops.has_uncommitted_changes()
    changed_files = await git_ops.get_changed_files()

Integration Points
------------------
The utils module integrates with several other Sugar components:

- **Workflow Orchestration** (``sugar.workflow``): Uses GitOperations for branch
  creation, commits, and pushes during work execution
- **Core Loop** (``sugar.core``): Uses GitOperations for repository state management
- **Quality Gates** (``sugar.quality_gates``): May use Git state for validation

Note
----
All Git operations require git to be installed and available in the system PATH.
Operations are executed via subprocess and are suitable for integration with
asyncio-based orchestration systems.

See Also
--------
- ``sugar.workflow``: Workflow orchestration that uses these utilities
- ``sugar.core.loop``: Main execution loop that uses Git operations

"""

from .git_operations import GitOperations

__all__ = [
    # Git Operations
    "GitOperations",  # Async Git operations handler for Sugar workflows
]
