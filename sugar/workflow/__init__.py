"""
Workflow Management - Unified Git and GitHub Workflow Handling for Sugar.

This module provides the central orchestration layer for managing git and GitHub
workflows across all Sugar work items. It ensures consistent workflow patterns
are applied regardless of how work items are discovered or sourced.

Architecture Overview
---------------------
The workflow system supports three pre-configured profiles, each designed for
different team sizes and process requirements:

**SOLO Profile** (Individual Developers):
    - Direct commits to the current branch
    - No automatic GitHub issue creation
    - All work handled internally with minimal overhead
    - Best for solo developers or small teams

**BALANCED Profile** (Small to Medium Teams):
    - Pull request workflow for code review opportunities
    - Selective GitHub issue creation based on priority
    - Good balance between structure and agility

**ENTERPRISE Profile** (Large Teams/Regulated Environments):
    - Pull request workflow with mandatory code review
    - Full GitHub integration with issue templates
    - Complete audit trail for compliance requirements

Key Components
--------------
- ``WorkflowOrchestrator``: Central coordinator managing work execution workflows
- ``WorkflowProfile``: Enum defining the three profile types (SOLO, BALANCED, ENTERPRISE)
- ``WorkflowType``: Enum for git workflow types (DIRECT_COMMIT, PULL_REQUEST)

Usage Example
-------------
Basic workflow orchestration::

    from sugar.workflow import WorkflowOrchestrator, WorkflowProfile, WorkflowType

    # Initialize the orchestrator with configuration
    config = load_config()
    git_ops = GitOperations()
    orchestrator = WorkflowOrchestrator(config, git_ops)

    # Prepare work for execution (creates branch if using PR workflow)
    workflow = await orchestrator.prepare_work_execution(work_item)

    # ... execute the work ...

    # Complete the workflow (commit, push, etc.)
    success = await orchestrator.complete_work_execution(
        work_item, workflow, execution_result
    )

Integration Points
------------------
The workflow module integrates with several other Sugar components:

- **Git Operations** (``sugar.utils.git_operations``): Branch creation, commits, pushes
- **Quality Gates** (``sugar.quality_gates``): Pre-commit validation and verification
- **Work Queue** (``sugar.storage``): Work item status updates and commit tracking
- **Core Loop** (``sugar.core``): Main execution loop that invokes workflows

See Also
--------
- ``sugar.utils.git_operations``: Git operations used by the orchestrator
- ``sugar.quality_gates``: Quality gate validation integration
- ``sugar.core.loop``: Main execution loop that uses this module
"""

from .orchestrator import WorkflowOrchestrator, WorkflowProfile, WorkflowType

__all__ = [
    # Core orchestrator class
    "WorkflowOrchestrator",  # Central coordinator for work execution workflows
    # Profile and type enums
    "WorkflowProfile",  # SOLO, BALANCED, ENTERPRISE profile definitions
    "WorkflowType",  # DIRECT_COMMIT, PULL_REQUEST workflow types
]
