"""
Workflow Orchestrator - Apply consistent git/GitHub workflows to all Sugar work.

This module provides the central orchestration layer for managing git and GitHub
workflows across all Sugar work items. It ensures consistent workflow patterns
are applied regardless of how work items are discovered or sourced.

Key Concepts:
-------------
- **Workflow Profiles**: Three pre-configured workflow profiles (SOLO, BALANCED,
  ENTERPRISE) that define default behaviors for git operations, GitHub integration,
  and work discovery handling.

- **Work Item Workflows**: Each work item gets an appropriate workflow based on
  its source type, work type, and priority.

- **Quality Gates**: Optional integration with quality gate validation before
  commits are allowed.

Workflow Profiles:
------------------
- SOLO: Direct commits, no GitHub issue creation, internal work handling.
  Best for individual developers or small teams.

- BALANCED: Pull request workflow with selective GitHub issue creation based
  on priority. Good for teams wanting some structure without full overhead.

- ENTERPRISE: Pull request workflow with mandatory review, full GitHub
  integration, and issue templates. For teams requiring full traceability.

Example Usage:
--------------
    config = load_config()
    git_ops = GitOperations()
    orchestrator = WorkflowOrchestrator(config, git_ops)

    # Prepare work for execution
    workflow = await orchestrator.prepare_work_execution(work_item)

    # ... execute the work ...

    # Complete the workflow (commit, push, etc.)
    success = await orchestrator.complete_work_execution(
        work_item, workflow, execution_result
    )

See Also:
---------
- :mod:`sugar.git_ops`: Git operations used by this orchestrator
- :mod:`sugar.quality_gates`: Quality gate validation integration
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowProfile(Enum):
    """
    Pre-configured workflow profiles that define default behaviors.

    Each profile provides sensible defaults for git operations, GitHub
    integration, and work discovery handling based on team size and
    process requirements.

    Attributes:
        SOLO: Individual developer workflow with minimal overhead.
            Direct commits to main branch, no GitHub issue creation,
            all work handled internally.
        BALANCED: Team workflow with selective automation.
            Pull request workflow, creates GitHub issues for high-priority
            work only, suitable for small to medium teams.
        ENTERPRISE: Full enterprise workflow with mandatory processes.
            Pull request with required reviews, full GitHub integration,
            issue templates, and complete audit trail.
    """

    SOLO = "solo"
    BALANCED = "balanced"
    ENTERPRISE = "enterprise"


class WorkflowType(Enum):
    """
    Git workflow types supported by the orchestrator.

    Attributes:
        DIRECT_COMMIT: Changes are committed directly to the current branch.
            Best for solo developers or when working on feature branches.
        PULL_REQUEST: Changes are committed to a new branch and require
            a pull request for merging. Provides code review opportunity.
    """

    DIRECT_COMMIT = "direct_commit"
    PULL_REQUEST = "pull_request"


class WorkflowOrchestrator:
    """
    Manages consistent git and GitHub workflows for all Sugar work items.

    The orchestrator is the central coordination point for ensuring that
    all work items, regardless of their source, are processed through
    consistent and appropriate git/GitHub workflows.

    Key Responsibilities:
        - Determining appropriate workflow type based on work item characteristics
        - Managing git branch creation and commits
        - Integrating with quality gates for pre-commit validation
        - Formatting commit messages according to conventional commit standards
        - Handling workflow completion including push and PR creation

    Attributes:
        config (Dict[str, Any]): Full Sugar configuration dictionary.
        git_ops: Git operations handler for branch/commit/push operations.
        work_queue: Work queue for updating work item status and metadata.
        workflow_config (Dict[str, Any]): Merged workflow configuration with
            profile defaults applied.
        quality_gates (Optional[QualityGatesCoordinator]): Quality gate
            coordinator for pre-commit validation, if enabled.

    Example:
        >>> orchestrator = WorkflowOrchestrator(config, git_ops, work_queue)
        >>> workflow = await orchestrator.prepare_work_execution(work_item)
        >>> # ... execute work ...
        >>> success = await orchestrator.complete_work_execution(
        ...     work_item, workflow, result
        ... )
    """

    def __init__(self, config: Dict[str, Any], git_ops=None, work_queue=None):
        """
        Initialize the workflow orchestrator.

        Args:
            config: Full Sugar configuration dictionary. Expected to contain
                a 'sugar.workflow' section with workflow settings and optionally
                a 'quality_gates' section.
            git_ops: Optional git operations handler. If not provided, git
                operations like branch creation and committing will not be
                available, limiting the orchestrator to configuration-only mode.
            work_queue: Optional work queue for updating work item status,
                storing commit SHAs, and recording quality gate results.
        """
        self.config = config
        self.git_ops = git_ops
        self.work_queue = work_queue
        self.workflow_config = self._load_workflow_config()

        # Initialize quality gates coordinator if enabled in configuration.
        # Quality gates provide pre-commit validation to ensure work meets
        # defined quality standards before being committed.
        self.quality_gates = None
        if config.get("quality_gates", {}).get("enabled", False):
            from ..quality_gates import QualityGatesCoordinator

            self.quality_gates = QualityGatesCoordinator(config)
            logger.info("🔒 Quality Gates enabled for workflow validation")

    def _load_workflow_config(self) -> Dict[str, Any]:
        """
        Load and validate workflow configuration with profile-based defaults.

        Loads the workflow configuration from the 'sugar.workflow' section
        of the config and applies profile-specific defaults. User-specified
        values override the profile defaults.

        Returns:
            Dict[str, Any]: Merged workflow configuration containing:
                - profile: The WorkflowProfile enum value
                - git: Git-related settings (workflow_type, commit_style, auto_commit)
                - github: GitHub integration settings (auto_create_issues, etc.)
                - discovery: Work discovery settings (handle_internally, etc.)

        Note:
            The profile defaults are designed to provide sensible out-of-box
            behavior while allowing full customization through explicit config.
        """
        workflow_config = self.config.get("sugar", {}).get("workflow", {})

        # Determine the workflow profile from config, defaulting to SOLO
        # for individual developers who want minimal overhead
        profile = WorkflowProfile(workflow_config.get("profile", "solo"))

        # Each profile provides a complete set of defaults that represent
        # best practices for that workflow style. These can be overridden
        # by explicit configuration.
        if profile == WorkflowProfile.SOLO:
            defaults = {
                "git": {
                    "workflow_type": "direct_commit",
                    "commit_style": "conventional",
                    "auto_commit": True,
                },
                "github": {
                    "auto_create_issues": False,
                    "update_existing_issues": True,  # Still update if work comes from GitHub
                },
                "discovery": {"handle_internally": True},  # No external issue creation
            }
        elif profile == WorkflowProfile.BALANCED:
            defaults = {
                "git": {
                    "workflow_type": "pull_request",
                    "commit_style": "conventional",
                    "auto_commit": True,
                },
                "github": {
                    "auto_create_issues": True,
                    "selective_creation": True,
                    "min_priority": 3,
                },
                "discovery": {"handle_internally": False},
            }
        else:  # ENTERPRISE
            defaults = {
                "git": {
                    "workflow_type": "pull_request",
                    "commit_style": "conventional",
                    "auto_commit": False,
                    "require_review": True,
                },
                "github": {
                    "auto_create_issues": True,
                    "selective_creation": False,
                    "issue_templates": True,
                },
                "discovery": {"handle_internally": False},
            }

        # Merge user config with defaults - user values take precedence
        # This allows partial customization while keeping sensible defaults
        merged = {**defaults, **workflow_config}
        merged["profile"] = profile  # Always store the resolved profile enum

        logger.debug(f"🔧 Loaded workflow config for {profile.value} profile")
        return merged

    def get_workflow_for_work_item(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine the appropriate workflow settings for a work item.

        Analyzes the work item's source, type, and priority to determine
        the best workflow configuration. GitHub-sourced work items receive
        special handling to preserve their existing workflow settings.

        Args:
            work_item: Dictionary containing work item details including:
                - source_type: Origin of the work (e.g., 'github_watcher', 'error_logs')
                - work_type: Category of work (e.g., 'bug_fix', 'feature')
                - priority: Numeric priority level (1-5, higher = more urgent)

        Returns:
            Dict[str, Any]: Workflow configuration containing:
                - git_workflow: WorkflowType enum (DIRECT_COMMIT or PULL_REQUEST)
                - commit_style: Commit message style ('conventional' or 'simple')
                - auto_commit: Whether to automatically commit changes
                - create_github_issue: Whether to create a new GitHub issue
                - update_github_issue: Whether to update an existing GitHub issue
                - branch_name: Branch name if using PR workflow (set during prepare)
                - commit_message_template: Template string for commit messages
        """
        source_type = work_item.get("source_type", "unknown")
        work_type = work_item.get("work_type", "unknown")
        priority = work_item.get("priority", 3)

        workflow = {
            "git_workflow": WorkflowType(self.workflow_config["git"]["workflow_type"]),
            "commit_style": self.workflow_config["git"]["commit_style"],
            "auto_commit": self.workflow_config["git"].get("auto_commit", True),
            "create_github_issue": False,  # Default to internal handling
            "update_github_issue": False,
            "branch_name": None,
            "commit_message_template": self._get_commit_template(work_type),
        }

        # Handle GitHub-sourced work differently - preserve the workflow
        # settings that were configured specifically for GitHub integration.
        # This ensures issues created in GitHub continue to be updated there.
        if source_type == "github_watcher":
            workflow["update_github_issue"] = True
            # Respect the GitHub-specific workflow configuration rather than
            # the general workflow profile, as users may want different
            # behavior for externally-sourced work
            github_config = (
                self.config.get("sugar", {}).get("discovery", {}).get("github", {})
            )
            git_workflow = github_config.get("workflow", {}).get(
                "git_workflow", "direct_commit"
            )
            workflow["git_workflow"] = WorkflowType(git_workflow)

        # Apply source-specific overrides for solo profile. Even in solo mode,
        # certain work types may benefit from slightly different handling.
        elif self.workflow_config["profile"] == WorkflowProfile.SOLO:
            if source_type in ["error_logs"] and priority >= 4:
                # High priority errors might need different handling
                workflow["commit_message_template"] = "fix: {title}"

        logger.debug(
            f"🔄 Determined workflow for {source_type}/{work_type}: {workflow['git_workflow'].value}"
        )
        return workflow

    def _get_commit_template(self, work_type: str) -> str:
        """
        Get the conventional commit message template based on work type.

        Maps work types to conventional commit prefixes to ensure consistent
        and semantically meaningful commit messages across all Sugar work.

        Args:
            work_type: The type of work being performed (e.g., 'bug_fix',
                'feature', 'documentation').

        Returns:
            str: A format string template like 'fix: {title}' where {title}
                will be replaced with the work item's title.

        Note:
            Unknown work types default to 'chore: {title}' to ensure all
            commits follow the conventional commit format.
        """
        templates = {
            "bug_fix": "fix: {title}",
            "feature": "feat: {title}",
            "test": "test: {title}",
            "refactor": "refactor: {title}",
            "documentation": "docs: {title}",
            "code_quality": "refactor: {title}",
            "test_coverage": "test: {title}",
        }

        return templates.get(work_type, "chore: {title}")

    def format_commit_message(
        self, work_item: Dict[str, Any], workflow: Dict[str, Any]
    ) -> str:
        """
        Format a complete commit message for a work item.

        Creates a commit message following the configured style (conventional
        or simple), including traceability information like the work item ID
        and Sugar version attribution.

        Args:
            work_item: Dictionary containing work item details:
                - title: The work item title to include in the message
                - id: The work item ID for traceability
            workflow: Workflow configuration dictionary:
                - commit_message_template: Template with {title} placeholder
                - commit_style: 'conventional' or 'simple'

        Returns:
            str: Fully formatted commit message including:
                - Main message line (templated or plain title)
                - Work ID for traceability
                - Sugar version attribution
        """
        template = workflow["commit_message_template"]
        title = work_item.get("title", "Unknown work")
        work_id = work_item.get("id", "unknown")

        if workflow["commit_style"] == "conventional":
            # Use the template as-is (already conventional format)
            message = template.format(title=title)
        else:
            # Simple format
            message = title

        # Add work item ID for traceability
        message += f"\n\nWork ID: {work_id}"

        # Add Sugar attribution
        from ..__version__ import get_version_info

        message += f"\nGenerated with {get_version_info()}"

        return message

    async def prepare_work_execution(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare a work item for execution with the appropriate workflow.

        Sets up the necessary git infrastructure before work execution begins.
        For pull request workflows, this creates a new feature branch. If
        branch creation fails, the workflow gracefully falls back to direct
        commits.

        Args:
            work_item: Dictionary containing work item details. Must include
                at minimum the fields needed by get_workflow_for_work_item().

        Returns:
            Dict[str, Any]: The prepared workflow configuration, potentially
                modified from the initial determination:
                - If PR workflow, 'branch_name' is set to the created branch
                - If branch creation fails, 'git_workflow' is changed to DIRECT_COMMIT

        Note:
            This method should be called before the actual work execution
            begins to ensure the git environment is properly prepared.
        """
        workflow = self.get_workflow_for_work_item(work_item)

        # Create branch if using PR workflow
        if workflow["git_workflow"] == WorkflowType.PULL_REQUEST and self.git_ops:
            branch_name = self._generate_branch_name(work_item)
            workflow["branch_name"] = branch_name

            try:
                success = await self.git_ops.create_branch(branch_name)
                if success:
                    logger.info(f"🌿 Created workflow branch: {branch_name}")
                else:
                    logger.warning(
                        f"⚠️ Failed to create branch {branch_name}, using current branch"
                    )
                    workflow["git_workflow"] = WorkflowType.DIRECT_COMMIT
            except Exception as e:
                logger.warning(
                    f"⚠️ Branch creation failed, falling back to direct commit: {e}"
                )
                workflow["git_workflow"] = WorkflowType.DIRECT_COMMIT

        return workflow

    async def complete_work_execution(
        self,
        work_item: Dict[str, Any],
        workflow: Dict[str, Any],
        execution_result: Dict[str, Any],
    ) -> bool:
        """
        Complete the workflow after work execution by committing and pushing.

        Handles the full post-execution workflow including:
        1. Checking for uncommitted changes
        2. Running quality gate validation (if enabled)
        3. Formatting and creating the commit
        4. Linking the commit SHA to the work item
        5. Pushing branches and creating PRs (for PR workflows)

        Args:
            work_item: The original work item dictionary, used for commit
                message formatting and work queue updates.
            workflow: The workflow configuration returned by prepare_work_execution(),
                containing git_workflow type, branch_name, auto_commit setting, etc.
            execution_result: Dictionary containing execution outcomes:
                - summary: Text summary of what was done
                - actions_taken: List of actions performed
                - claims: Optional explicit claims for quality gate validation

        Returns:
            bool: True if the workflow completed successfully, False if:
                - Quality gates failed validation
                - Git commit failed
                - Branch push failed (for PR workflows)

        Note:
            If auto_commit is False in the workflow, this method returns True
            immediately without performing any git operations.
        """
        if not workflow.get("auto_commit", True):
            logger.info("🔧 Auto-commit disabled, skipping git operations")
            return True

        if not self.git_ops:
            logger.warning("⚠️ No git operations available")
            return False

        try:
            # Check if there are changes to commit
            has_changes = await self.git_ops.has_uncommitted_changes()
            if not has_changes:
                logger.info("📝 No changes to commit")
                return True

            # Run quality gate validation before committing
            if self.quality_gates and self.quality_gates.is_enabled():
                logger.info("🔒 Running quality gate validation before commit")

                # Get list of changed files
                changed_files = await self._get_changed_files()

                # Extract claims from execution result if available
                claims = self._extract_claims_from_result(execution_result)

                # Validate with quality gates
                can_commit, gate_result = (
                    await self.quality_gates.validate_before_commit(
                        task=work_item, changed_files=changed_files, claims=claims
                    )
                )

                if not can_commit:
                    logger.error(
                        f"❌ Quality gate validation failed: {gate_result.reason}"
                    )
                    logger.error("🚫 Blocking commit - quality requirements not met")

                    # Store failure information in work item
                    if self.work_queue:
                        await self.work_queue.update_work(
                            work_item["id"],
                            {
                                "quality_gate_status": "failed",
                                "quality_gate_reason": gate_result.reason,
                                "quality_gate_details": gate_result.to_dict(),
                            },
                        )

                    return False

                logger.info(f"✅ Quality gates passed: {gate_result.reason}")

                # Add quality gate evidence to commit message
                quality_footer = self.quality_gates.get_commit_message_footer(
                    gate_result
                )
            else:
                quality_footer = ""

            # Format commit message
            commit_message = self.format_commit_message(work_item, workflow)

            # Append quality gate evidence if available
            if quality_footer:
                commit_message += quality_footer

            # Commit changes
            success = await self.git_ops.commit_changes(commit_message)
            if not success:
                logger.error("❌ Failed to commit changes")
                return False

            # Capture commit SHA and store in database for traceability.
            # This creates a link between work items and their resulting commits,
            # enabling audit trails and change tracking across the system.
            if self.work_queue:
                commit_sha = await self.git_ops.get_latest_commit_sha()
                if commit_sha:
                    work_id = work_item.get("id")
                    if work_id:
                        await self.work_queue.update_commit_sha(work_id, commit_sha)
                        logger.debug(
                            f"🔗 Linked commit {commit_sha[:8]} to work item {work_id}"
                        )

            # Handle PR workflow - push to remote and prepare for PR creation.
            # In balanced/enterprise profiles, this would also create the PR.
            if workflow["git_workflow"] == WorkflowType.PULL_REQUEST:
                branch_name = workflow.get("branch_name")
                if branch_name:
                    # Push branch
                    push_success = await self.git_ops.push_branch(branch_name)
                    if push_success:
                        logger.info(f"📤 Pushed branch {branch_name}")
                        # Note: PR creation would happen here in balanced/enterprise profiles
                    else:
                        logger.error(f"❌ Failed to push branch {branch_name}")
                        return False

            logger.info(f"✅ Completed {workflow['git_workflow'].value} workflow")
            return True

        except Exception as e:
            logger.error(f"❌ Workflow completion failed: {e}")
            return False

    def _generate_branch_name(self, work_item: Dict[str, Any]) -> str:
        """
        Generate a descriptive branch name for a work item.

        Creates a branch name following the pattern:
        `sugar/{source_type}/{work_type}-{clean_title}-{short_id}`

        The title is sanitized to only include alphanumeric characters,
        hyphens, and underscores, and is truncated to 30 characters.

        Args:
            work_item: Dictionary containing:
                - source_type: Origin of the work (default: 'sugar')
                - id: Work item ID (first 8 characters used)
                - work_type: Category of work (default: 'work')
                - title: Work item title for the descriptive portion

        Returns:
            str: A git-compatible branch name like
                'sugar/github_watcher/bug_fix-fix-login-error-a1b2c3d4'
        """
        source_type = work_item.get("source_type", "sugar")
        work_id = work_item.get("id", "unknown")[:8]  # Short ID
        work_type = work_item.get("work_type", "work")

        # Clean title for branch name
        title = work_item.get("title", "unknown")
        clean_title = "".join(c for c in title.lower() if c.isalnum() or c in "-_")[:30]

        return f"sugar/{source_type}/{work_type}-{clean_title}-{work_id}"

    async def _get_changed_files(self) -> List[str]:
        """
        Get the list of changed files for quality gate validation.

        Retrieves all files that have been modified but not yet committed,
        which is used by quality gates to determine which validation rules
        apply.

        Returns:
            List[str]: List of file paths that have uncommitted changes.
                Returns an empty list if git_ops is not available or if
                an error occurs during retrieval.
        """
        if not self.git_ops:
            return []

        try:
            changed_files = await self.git_ops.get_changed_files()
            return changed_files if changed_files else []
        except Exception as e:
            logger.warning(f"Could not get changed files: {e}")
            return []

    def _extract_claims_from_result(
        self, execution_result: Dict[str, Any]
    ) -> List[str]:
        """
        Extract claims from execution result for truth enforcement.

        Analyzes the execution result to identify claims that should be
        validated by quality gates. Claims can be explicit (in a 'claims' key)
        or implicit (detected from summary text and action descriptions).

        This supports the "truth enforcement" feature of quality gates, which
        verifies that claims made about the work (e.g., "all tests pass") are
        actually true before allowing the commit.

        Args:
            execution_result: Dictionary containing execution outcomes:
                - claims: Optional list of explicit claim strings
                - summary: Text summary that may contain implicit claims
                - actions_taken: List of actions that may contain implicit claims

        Returns:
            List[str]: Deduplicated list of claims to validate, such as:
                - "all tests pass"
                - "functionality verified"
                - "no errors"
                - "implementation complete"
        """
        claims = []

        # Look for explicit claims in result
        if "claims" in execution_result:
            claims.extend(execution_result["claims"])

        # Extract implicit claims from summary/actions by pattern matching.
        # This allows quality gates to catch and verify claims that agents
        # make naturally in their output without requiring explicit declaration.
        summary = execution_result.get("summary", "").lower()
        actions = execution_result.get("actions_taken", [])

        # Common claim patterns mapped from natural language to claim identifiers
        claim_patterns = {
            "all tests pass": ["tests pass", "all tests passed", "tests successful"],
            "functionality verified": ["verified", "tested", "confirmed working"],
            "no errors": ["no errors", "error-free", "without errors"],
            "implementation complete": ["complete", "implemented", "finished"],
        }

        for claim, patterns in claim_patterns.items():
            if any(pattern in summary for pattern in patterns):
                claims.append(claim)
            for action in actions:
                if any(pattern in str(action).lower() for pattern in patterns):
                    if claim not in claims:
                        claims.append(claim)
                    break

        return claims
