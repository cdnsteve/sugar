"""
Workflow Orchestrator - Apply consistent git/GitHub workflows to all Sugar work
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowProfile(Enum):
    SOLO = "solo"
    BALANCED = "balanced"
    ENTERPRISE = "enterprise"


class WorkflowType(Enum):
    DIRECT_COMMIT = "direct_commit"
    PULL_REQUEST = "pull_request"


class WorkflowOrchestrator:
    """Manages consistent workflows for all Sugar work items"""

    def __init__(self, config: Dict[str, Any], git_ops=None, work_queue=None):
        self.config = config
        self.git_ops = git_ops
        self.work_queue = work_queue
        self.workflow_config = self._load_workflow_config()

    def _load_workflow_config(self) -> Dict[str, Any]:
        """Load and validate workflow configuration"""
        workflow_config = self.config.get("sugar", {}).get("workflow", {})

        # Set defaults based on profile
        profile = WorkflowProfile(workflow_config.get("profile", "solo"))

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

        # Merge user config with defaults
        merged = {**defaults, **workflow_config}
        merged["profile"] = profile

        logger.debug(f"🔧 Loaded workflow config for {profile.value} profile")
        return merged

    def get_workflow_for_work_item(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
        """Determine appropriate workflow for a work item"""
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

        # Handle GitHub-sourced work differently
        if source_type == "github_watcher":
            workflow["update_github_issue"] = True
            # Use existing GitHub workflow settings
            github_config = (
                self.config.get("sugar", {}).get("discovery", {}).get("github", {})
            )
            git_workflow = github_config.get("workflow", {}).get(
                "git_workflow", "direct_commit"
            )
            workflow["git_workflow"] = WorkflowType(git_workflow)

        # Apply source-specific overrides for solo profile
        elif self.workflow_config["profile"] == WorkflowProfile.SOLO:
            if source_type in ["error_logs"] and priority >= 4:
                # High priority errors might need different handling
                workflow["commit_message_template"] = "fix: {title}"

        logger.debug(
            f"🔄 Determined workflow for {source_type}/{work_type}: {workflow['git_workflow'].value}"
        )
        return workflow

    def _get_commit_template(self, work_type: str) -> str:
        """Get conventional commit message template based on work type"""
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
        """Format commit message according to workflow style"""
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

        message += f"\n🤖 Generated with {get_version_info()}"

        return message

    async def prepare_work_execution(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare work item for execution with proper workflow"""
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
        """Complete workflow after work execution"""
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

            # Format commit message
            commit_message = self.format_commit_message(work_item, workflow)

            # Commit changes
            success = await self.git_ops.commit_changes(commit_message)
            if not success:
                logger.error("❌ Failed to commit changes")
                return False

            # Capture commit SHA and store in database for traceability
            if self.work_queue:
                commit_sha = await self.git_ops.get_latest_commit_sha()
                if commit_sha:
                    work_id = work_item.get("id")
                    if work_id:
                        await self.work_queue.update_commit_sha(work_id, commit_sha)
                        logger.debug(
                            f"🔗 Linked commit {commit_sha[:8]} to work item {work_id}"
                        )

            # Handle PR workflow
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
        """Generate branch name for work item"""
        source_type = work_item.get("source_type", "sugar")
        work_id = work_item.get("id", "unknown")[:8]  # Short ID
        work_type = work_item.get("work_type", "work")

        # Clean title for branch name
        title = work_item.get("title", "unknown")
        clean_title = "".join(c for c in title.lower() if c.isalnum() or c in "-_")[:30]

        return f"sugar/{source_type}/{work_type}-{clean_title}-{work_id}"
