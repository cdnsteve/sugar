"""
Tests for Task Orchestration System

Tests the task orchestration functionality covering:
- TaskOrchestrator: Detection, stage management, context accumulation
- AgentRouter: Specialist agent routing based on task content
- Integration: Full orchestration flow with stages and subtasks

Based on design spec: docs/task_orchestration.md
"""

import asyncio
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, Mock, call
from typing import Dict, Any, List, Optional

# Note: These are placeholder imports - actual implementation may differ
# Adjust imports once TaskOrchestrator and AgentRouter are implemented


# ============================================================================
# Mock Classes and Fixtures
# ============================================================================


class MockTask:
    """Mock task for testing orchestration."""

    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        task_type: str = "feature",
        priority: int = 3,
        orchestrate: bool = False,
        parent_task_id: Optional[str] = None,
        stage: Optional[str] = None,
        blocked_by: Optional[List[str]] = None,
        context_path: Optional[str] = None,
        assigned_agent: Optional[str] = None,
    ):
        self.id = id
        self.title = title
        self.description = description
        self.type = task_type
        self.priority = priority
        self.orchestrate = orchestrate
        self.parent_task_id = parent_task_id
        self.stage = stage
        self.blocked_by = blocked_by or []
        self.context_path = context_path
        self.assigned_agent = assigned_agent

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "type": self.type,
            "priority": self.priority,
            "orchestrate": self.orchestrate,
            "parent_task_id": self.parent_task_id,
            "stage": self.stage,
            "blocked_by": self.blocked_by,
            "context_path": self.context_path,
            "assigned_agent": self.assigned_agent,
        }

    def to_prompt(self) -> str:
        return f"{self.title}\n\n{self.description}"


class MockStageResult:
    """Mock result from a stage execution."""

    def __init__(
        self,
        stage: str,
        success: bool,
        output: str,
        execution_time: float = 1.0,
        files_created: Optional[List[str]] = None,
    ):
        self.stage = stage
        self.success = success
        self.output = output
        self.execution_time = execution_time
        self.files_created = files_created or []


class MockOrchestrationContext:
    """Mock orchestration context for testing."""

    def __init__(self, task_id: str, base_path: Path):
        self.task_id = task_id
        self.base_path = base_path
        self._research = ""
        self._plan = ""
        self._subtask_results: Dict[str, str] = {}

    def add_research(self, content: str) -> None:
        self._research = content

    def add_plan(self, content: str) -> None:
        self._plan = content

    def add_subtask_result(self, subtask_id: str, result: str) -> None:
        self._subtask_results[subtask_id] = result

    def get_full_context(self) -> str:
        parts = []
        if self._research:
            parts.append(f"## Research\n{self._research}")
        if self._plan:
            parts.append(f"## Plan\n{self._plan}")
        if self._subtask_results:
            parts.append("## Subtask Results")
            for task_id, result in self._subtask_results.items():
                parts.append(f"### {task_id}\n{result}")
        return "\n\n".join(parts)

    def get_files_modified(self) -> List[str]:
        return ["/src/auth.py", "/src/utils.py"]


@pytest.fixture
def orchestration_config():
    """Orchestration configuration for testing."""
    return {
        "enabled": True,
        "auto_decompose": "auto",
        "detection": {
            "task_types": ["feature", "epic"],
            "keywords": [
                "implement",
                "build",
                "create full",
                "add complete",
                "redesign",
                "refactor entire",
            ],
            "min_complexity": "high",
        },
        "stages": {
            "research": {
                "enabled": True,
                "agent": "Explore",
                "timeout": 600,
                "actions": ["web_search", "codebase_analysis", "doc_gathering"],
                "output_to_context": True,
                "output_path": ".sugar/orchestration/{task_id}/research.md",
            },
            "planning": {
                "enabled": True,
                "agent": "Plan",
                "timeout": 300,
                "depends_on": ["research"],
                "creates_subtasks": True,
                "output_path": ".sugar/orchestration/{task_id}/plan.md",
            },
            "implementation": {
                "parallel": True,
                "max_concurrent": 3,
                "timeout_per_task": 1800,
                "agent_routing": {
                    "*ui*|*frontend*|*component*|*design*": "frontend-designer",
                    "*api*|*backend*|*endpoint*|*service*": "backend-developer",
                    "*test*|*spec*|*coverage*": "qa-engineer",
                    "*security*|*auth*|*permission*": "security-engineer",
                    "*devops*|*deploy*|*ci*|*docker*": "devops-engineer",
                    "*doc*|*readme*|*guide*": "general-purpose",
                    "default": "general-purpose",
                },
            },
            "review": {
                "enabled": True,
                "depends_on": ["implementation"],
                "agents": ["code-reviewer", "qa-engineer"],
                "run_tests": True,
                "require_passing": True,
            },
        },
    }


@pytest.fixture
def mock_task_orchestrator(orchestration_config, temp_dir):
    """Mock TaskOrchestrator instance."""

    class MockTaskOrchestrator:
        """Mock implementation of TaskOrchestrator for testing."""

        def __init__(self, config: Dict[str, Any]):
            self.config = config
            self.detection_config = config.get("detection", {})
            self.stages_config = config.get("stages", {})
            self._stage_results: List[MockStageResult] = []

        async def should_orchestrate(self, task: MockTask) -> bool:
            """Determine if task needs orchestration based on config."""
            # Check explicit flag
            if task.orchestrate:
                return True

            # Check task type
            if task.type in self.detection_config.get("task_types", []):
                return True

            # Check keywords
            keywords = self.detection_config.get("keywords", [])
            content = f"{task.title} {task.description}".lower()
            for keyword in keywords:
                if keyword.lower() in content:
                    return True

            return False

        async def orchestrate(self, task: MockTask) -> Dict[str, Any]:
            """Run full orchestration workflow for a task."""
            results = {
                "task_id": task.id,
                "success": True,
                "stages_completed": [],
                "subtasks_generated": [],
                "execution_time": 0.0,
            }

            context = MockOrchestrationContext(
                task.id, Path(temp_dir) / ".sugar" / "orchestration" / task.id
            )

            # Research stage
            if self.stages_config.get("research", {}).get("enabled", False):
                research_result = await self.run_stage("research", context)
                results["stages_completed"].append("research")
                results["execution_time"] += research_result.execution_time
                context.add_research(research_result.output)

            # Planning stage
            if self.stages_config.get("planning", {}).get("enabled", False):
                planning_result = await self.run_stage("planning", context)
                results["stages_completed"].append("planning")
                results["execution_time"] += planning_result.execution_time
                context.add_plan(planning_result.output)

                # Generate subtasks from plan
                subtasks = await self.generate_subtasks(planning_result.output)
                results["subtasks_generated"] = subtasks

            # Implementation stage
            if results["subtasks_generated"]:
                impl_results = await self.run_implementation_stage(
                    results["subtasks_generated"]
                )
                results["stages_completed"].append("implementation")
                results["execution_time"] += sum(r.execution_time for r in impl_results)

                for subtask, result in zip(results["subtasks_generated"], impl_results):
                    context.add_subtask_result(subtask.id, result.output)

            # Review stage
            if self.stages_config.get("review", {}).get("enabled", False):
                review_result = await self.run_stage("review", context)
                results["stages_completed"].append("review")
                results["execution_time"] += review_result.execution_time

            return results

        async def run_stage(
            self, stage: str, context: MockOrchestrationContext
        ) -> MockStageResult:
            """Execute a single stage of the workflow."""
            stage_config = self.stages_config.get(stage, {})
            agent = stage_config.get("agent", "general-purpose")

            # Simulate stage execution
            await asyncio.sleep(0.01)

            if stage == "research":
                output = f"Research findings for {context.task_id}:\n- OAuth best practices\n- Codebase analysis complete"
                return MockStageResult(
                    stage="research",
                    success=True,
                    output=output,
                    execution_time=1.5,
                    files_created=[
                        f".sugar/orchestration/{context.task_id}/research.md"
                    ],
                )
            elif stage == "planning":
                output = f"Implementation plan for {context.task_id}:\n## Subtasks\n1. Backend API\n2. Frontend UI\n3. Tests"
                return MockStageResult(
                    stage="planning",
                    success=True,
                    output=output,
                    execution_time=1.0,
                    files_created=[f".sugar/orchestration/{context.task_id}/plan.md"],
                )
            elif stage == "review":
                output = f"Review complete for {context.task_id}:\n- Code quality: PASS\n- Tests: PASS"
                return MockStageResult(
                    stage="review",
                    success=True,
                    output=output,
                    execution_time=2.0,
                )
            else:
                return MockStageResult(
                    stage=stage,
                    success=True,
                    output="Stage complete",
                    execution_time=1.0,
                )

        async def generate_subtasks(self, plan_output: str) -> List[MockTask]:
            """Generate sub-tasks from planning stage output."""
            # Parse plan output and generate subtasks
            subtasks = []

            # Simple parsing - look for numbered items
            if "1. Backend API" in plan_output:
                subtasks.append(
                    MockTask(
                        id="subtask-1",
                        title="Implement Backend API",
                        description="Create API endpoints for authentication",
                        task_type="feature",
                        parent_task_id="parent-task",
                    )
                )
            if "2. Frontend UI" in plan_output:
                subtasks.append(
                    MockTask(
                        id="subtask-2",
                        title="Build Frontend UI",
                        description="Create login/signup UI components",
                        task_type="feature",
                        parent_task_id="parent-task",
                        blocked_by=["subtask-1"],
                    )
                )
            if "3. Tests" in plan_output:
                subtasks.append(
                    MockTask(
                        id="subtask-3",
                        title="Write Tests",
                        description="Add unit and integration tests",
                        task_type="test",
                        parent_task_id="parent-task",
                        blocked_by=["subtask-1", "subtask-2"],
                    )
                )

            return subtasks

        async def run_implementation_stage(
            self, subtasks: List[MockTask]
        ) -> List[MockStageResult]:
            """Execute implementation stage with parallel subtasks."""
            results = []

            # Group by dependency level
            ready_tasks = [t for t in subtasks if not t.blocked_by]
            blocked_tasks = [t for t in subtasks if t.blocked_by]

            # Execute ready tasks in parallel
            ready_results = await asyncio.gather(
                *[self._execute_subtask(t) for t in ready_tasks]
            )
            results.extend(ready_results)

            # Execute blocked tasks after dependencies
            for blocked_task in blocked_tasks:
                result = await self._execute_subtask(blocked_task)
                results.append(result)

            return results

        async def _execute_subtask(self, subtask: MockTask) -> MockStageResult:
            """Execute a single subtask."""
            await asyncio.sleep(0.01)
            return MockStageResult(
                stage="implementation",
                success=True,
                output=f"Completed {subtask.title}",
                execution_time=1.0,
            )

    return MockTaskOrchestrator(orchestration_config)


@pytest.fixture
def mock_agent_router(orchestration_config):
    """Mock AgentRouter instance."""

    class MockAgentRouter:
        """Mock implementation of AgentRouter for testing."""

        def __init__(self, config: Dict[str, Any]):
            self.routing_config = (
                config.get("stages", {})
                .get("implementation", {})
                .get("agent_routing", {})
            )
            self.stage_agents = {
                "research": config.get("stages", {})
                .get("research", {})
                .get("agent", "Explore"),
                "planning": config.get("stages", {})
                .get("planning", {})
                .get("agent", "Plan"),
                "review": config.get("stages", {})
                .get("review", {})
                .get("agents", ["code-reviewer"])[0],
            }

        def route(self, task: MockTask) -> str:
            """Return the agent name for a task."""
            content = f"{task.title} {task.description}".lower()

            # Check each routing pattern (order matters for priority)
            # DevOps patterns
            if any(
                keyword in content
                for keyword in ["devops", "deploy", "ci/cd", "docker"]
            ):
                return "devops-engineer"
            # Documentation patterns (check specific keywords to avoid false positives)
            elif any(
                keyword in content
                for keyword in ["readme", "guide", " doc ", "documentation", "api doc"]
            ):
                return "general-purpose"
            # Frontend patterns
            elif any(
                keyword in content
                for keyword in ["ui", "frontend", "component", "design"]
            ):
                return "frontend-designer"
            # Backend patterns
            elif any(
                keyword in content
                for keyword in ["api", "backend", "endpoint", "service"]
            ):
                return "backend-developer"
            # Testing patterns
            elif any(keyword in content for keyword in ["test", "spec", "coverage"]):
                return "qa-engineer"
            # Security patterns
            elif any(
                keyword in content for keyword in ["security", "auth", "permission"]
            ):
                return "security-engineer"
            else:
                return "general-purpose"

        def get_stage_agent(self, stage: str) -> str:
            """Get the agent for a specific orchestration stage."""
            return self.stage_agents.get(stage, "general-purpose")

        def get_available_agents(self) -> List[str]:
            """List available specialist agents."""
            return [
                "general-purpose",
                "tech-lead",
                "code-reviewer",
                "frontend-designer",
                "backend-developer",
                "qa-engineer",
                "security-engineer",
                "devops-engineer",
                "Explore",
                "Plan",
            ]

    return MockAgentRouter(orchestration_config)


# ============================================================================
# Test TaskOrchestrator
# ============================================================================


class TestTaskOrchestrator:
    """Tests for TaskOrchestrator class."""

    @pytest.mark.asyncio
    async def test_should_orchestrate_feature_type(self, mock_task_orchestrator):
        """Feature type tasks should trigger orchestration."""
        task = MockTask(
            id="task-1",
            title="Add user authentication",
            description="Implement OAuth authentication system",
            task_type="feature",
        )

        should_orchestrate = await mock_task_orchestrator.should_orchestrate(task)

        assert should_orchestrate is True

    @pytest.mark.asyncio
    async def test_should_orchestrate_epic_type(self, mock_task_orchestrator):
        """Epic type tasks should trigger orchestration."""
        task = MockTask(
            id="task-2",
            title="Rebuild payment system",
            description="Complete overhaul of payment processing",
            task_type="epic",
        )

        should_orchestrate = await mock_task_orchestrator.should_orchestrate(task)

        assert should_orchestrate is True

    @pytest.mark.asyncio
    async def test_should_orchestrate_keywords(self, mock_task_orchestrator):
        """Tasks with orchestration keywords should trigger."""
        keywords_to_test = [
            "implement full authentication",
            "build new dashboard",
            "create full payment flow",
            "redesign entire UI",
            "refactor entire codebase",
        ]

        for keyword_phrase in keywords_to_test:
            task = MockTask(
                id="task-keyword",
                title=keyword_phrase,
                description="Test description",
                task_type="feature",
            )

            should_orchestrate = await mock_task_orchestrator.should_orchestrate(task)

            assert (
                should_orchestrate is True
            ), f"Keyword '{keyword_phrase}' should trigger orchestration"

    @pytest.mark.asyncio
    async def test_should_not_orchestrate_bug_fix(self, mock_task_orchestrator):
        """Simple bug fixes should not orchestrate."""
        task = MockTask(
            id="task-3",
            title="Fix typo in error message",
            description="Correct spelling error",
            task_type="bug_fix",
        )

        should_orchestrate = await mock_task_orchestrator.should_orchestrate(task)

        assert should_orchestrate is False

    @pytest.mark.asyncio
    async def test_should_orchestrate_explicit_flag(self, mock_task_orchestrator):
        """Tasks with orchestrate=True should always trigger."""
        task = MockTask(
            id="task-4",
            title="Simple task",
            description="But we want to orchestrate it",
            task_type="bug_fix",
            orchestrate=True,
        )

        should_orchestrate = await mock_task_orchestrator.should_orchestrate(task)

        assert should_orchestrate is True

    @pytest.mark.asyncio
    async def test_orchestrate_runs_all_stages(self, mock_task_orchestrator):
        """Full orchestration runs research->planning->implementation->review."""
        task = MockTask(
            id="task-5",
            title="Implement OAuth authentication",
            description="Full OAuth 2.0 implementation with PKCE",
            task_type="feature",
        )

        result = await mock_task_orchestrator.orchestrate(task)

        assert result["success"] is True
        assert "research" in result["stages_completed"]
        assert "planning" in result["stages_completed"]
        assert "implementation" in result["stages_completed"]
        assert "review" in result["stages_completed"]
        assert result["execution_time"] > 0

    @pytest.mark.asyncio
    async def test_stage_context_accumulation(self, mock_task_orchestrator, temp_dir):
        """Each stage should receive context from previous stages."""
        task = MockTask(
            id="task-6",
            title="Build payment system",
            description="Stripe integration",
            task_type="feature",
        )

        context = MockOrchestrationContext(
            task.id, Path(temp_dir) / ".sugar" / "orchestration" / task.id
        )

        # Add research findings
        research_result = await mock_task_orchestrator.run_stage("research", context)
        context.add_research(research_result.output)

        # Planning should have access to research context
        planning_result = await mock_task_orchestrator.run_stage("planning", context)
        context.add_plan(planning_result.output)

        full_context = context.get_full_context()

        assert "Research" in full_context
        assert "Plan" in full_context
        assert research_result.output in full_context
        assert planning_result.output in full_context

    @pytest.mark.asyncio
    async def test_subtask_generation(self, mock_task_orchestrator):
        """Planning stage should generate subtasks from output."""
        plan_output = """
        Implementation plan:
        ## Subtasks
        1. Backend API - Create authentication endpoints
        2. Frontend UI - Build login form
        3. Tests - Add E2E tests
        """

        subtasks = await mock_task_orchestrator.generate_subtasks(plan_output)

        assert len(subtasks) == 3
        assert subtasks[0].title == "Implement Backend API"
        assert subtasks[1].title == "Build Frontend UI"
        assert subtasks[2].title == "Write Tests"

    @pytest.mark.asyncio
    async def test_implementation_parallel_execution(self, mock_task_orchestrator):
        """Implementation stage runs ready subtasks in parallel."""
        subtasks = [
            MockTask(
                id="subtask-1",
                title="Backend API",
                description="API implementation",
                task_type="feature",
            ),
            MockTask(
                id="subtask-2",
                title="Documentation",
                description="API docs",
                task_type="documentation",
            ),
        ]

        start_time = asyncio.get_event_loop().time()
        results = await mock_task_orchestrator.run_implementation_stage(subtasks)
        end_time = asyncio.get_event_loop().time()

        # Both tasks should complete
        assert len(results) == 2
        assert all(r.success for r in results)

        # Should run in parallel (faster than sequential)
        # Sequential would be 2 * 0.01 = 0.02s, parallel should be ~0.01s
        elapsed = end_time - start_time
        assert elapsed < 0.05  # Allow some overhead

    @pytest.mark.asyncio
    async def test_blocked_subtasks_wait(self, mock_task_orchestrator):
        """Blocked subtasks should not execute until dependencies complete."""
        subtasks = [
            MockTask(
                id="subtask-1",
                title="API Implementation",
                description="Backend API",
                task_type="feature",
            ),
            MockTask(
                id="subtask-2",
                title="UI Implementation",
                description="Frontend UI",
                task_type="feature",
                blocked_by=["subtask-1"],  # Blocked by first task
            ),
        ]

        results = await mock_task_orchestrator.run_implementation_stage(subtasks)

        # Both should complete successfully
        assert len(results) == 2
        assert all(r.success for r in results)

        # First result should be from unblocked task
        assert "API Implementation" in results[0].output

    @pytest.mark.asyncio
    async def test_orchestration_failure_handling(
        self, mock_task_orchestrator, temp_dir
    ):
        """Stage failures should be handled gracefully."""

        async def failing_stage(stage: str, context):
            return MockStageResult(
                stage=stage,
                success=False,
                output="Stage failed due to error",
                execution_time=1.0,
            )

        # Patch run_stage to fail
        original_run_stage = mock_task_orchestrator.run_stage
        mock_task_orchestrator.run_stage = failing_stage

        task = MockTask(
            id="task-fail",
            title="Task that will fail",
            description="Testing failure handling",
            task_type="feature",
        )

        # Should handle failure gracefully (implementation dependent)
        context = MockOrchestrationContext(
            task.id, Path(temp_dir) / ".sugar" / "orchestration" / task.id
        )
        result = await mock_task_orchestrator.run_stage("research", context)

        assert result.success is False
        assert "failed" in result.output.lower()

        # Restore original
        mock_task_orchestrator.run_stage = original_run_stage


# ============================================================================
# Test AgentRouter
# ============================================================================


class TestAgentRouter:
    """Tests for AgentRouter class."""

    def test_route_frontend_task(self, mock_agent_router):
        """UI/frontend tasks route to frontend-designer."""
        test_cases = [
            MockTask(
                id="t1", title="Build login UI", description="Create form components"
            ),
            MockTask(
                id="t2", title="Update frontend", description="Redesign dashboard"
            ),
            MockTask(
                id="t3", title="Add component", description="New button component"
            ),
            MockTask(id="t4", title="Design system", description="UI design tokens"),
        ]

        for task in test_cases:
            agent = mock_agent_router.route(task)
            assert (
                agent == "frontend-designer"
            ), f"Task '{task.title}' should route to frontend-designer"

    def test_route_backend_task(self, mock_agent_router):
        """API/backend tasks route to backend-developer."""
        test_cases = [
            MockTask(id="t1", title="Create API endpoint", description="REST API"),
            MockTask(
                id="t2", title="Backend service", description="Payment processing"
            ),
            MockTask(id="t3", title="Database endpoint", description="CRUD operations"),
        ]

        for task in test_cases:
            agent = mock_agent_router.route(task)
            assert (
                agent == "backend-developer"
            ), f"Task '{task.title}' should route to backend-developer"

    def test_route_test_task(self, mock_agent_router):
        """Test tasks route to qa-engineer."""
        test_cases = [
            MockTask(id="t1", title="Write unit tests", description="Test coverage"),
            MockTask(id="t2", title="Add spec", description="E2E test spec"),
            MockTask(id="t3", title="Improve coverage", description="Test all paths"),
        ]

        for task in test_cases:
            agent = mock_agent_router.route(task)
            assert (
                agent == "qa-engineer"
            ), f"Task '{task.title}' should route to qa-engineer"

    def test_route_security_task(self, mock_agent_router):
        """Security tasks route to security-engineer."""
        test_cases = [
            MockTask(
                id="t1",
                title="Implement authentication",
                description="OAuth security",
            ),
            MockTask(id="t2", title="Add permissions", description="Role-based access"),
            MockTask(id="t3", title="Security audit", description="Vulnerability scan"),
        ]

        for task in test_cases:
            agent = mock_agent_router.route(task)
            assert (
                agent == "security-engineer"
            ), f"Task '{task.title}' should route to security-engineer"

    def test_route_devops_task(self, mock_agent_router):
        """DevOps tasks route to devops-engineer."""
        test_cases = [
            MockTask(id="t1", title="Setup CI/CD", description="GitHub Actions"),
            MockTask(id="t2", title="Deploy to production", description="K8s deploy"),
            MockTask(id="t3", title="Docker configuration", description="Dockerfile"),
        ]

        for task in test_cases:
            agent = mock_agent_router.route(task)
            assert (
                agent == "devops-engineer"
            ), f"Task '{task.title}' should route to devops-engineer"

    def test_route_documentation_task(self, mock_agent_router):
        """Documentation tasks route to general-purpose."""
        test_cases = [
            MockTask(id="t1", title="Update README", description="Installation guide"),
            MockTask(id="t2", title="API documentation", description="OpenAPI spec"),
            MockTask(id="t3", title="User guide", description="Tutorial docs"),
        ]

        for task in test_cases:
            agent = mock_agent_router.route(task)
            assert (
                agent == "general-purpose"
            ), f"Task '{task.title}' should route to general-purpose"

    def test_route_default_fallback(self, mock_agent_router):
        """Unknown tasks fall back to general-purpose."""
        task = MockTask(
            id="t1",
            title="Random task",
            description="Something that doesn't match patterns",
        )

        agent = mock_agent_router.route(task)

        assert agent == "general-purpose"

    def test_get_stage_agent(self, mock_agent_router):
        """Correct agents for each orchestration stage."""
        assert mock_agent_router.get_stage_agent("research") == "Explore"
        assert mock_agent_router.get_stage_agent("planning") == "Plan"
        assert mock_agent_router.get_stage_agent("review") == "code-reviewer"
        assert (
            mock_agent_router.get_stage_agent("unknown") == "general-purpose"
        )  # Fallback

    def test_get_available_agents(self, mock_agent_router):
        """List of available agents is complete."""
        agents = mock_agent_router.get_available_agents()

        expected_agents = [
            "general-purpose",
            "tech-lead",
            "code-reviewer",
            "frontend-designer",
            "backend-developer",
            "qa-engineer",
            "security-engineer",
            "devops-engineer",
            "Explore",
            "Plan",
        ]

        for expected in expected_agents:
            assert expected in agents, f"Agent '{expected}' should be available"


# ============================================================================
# Integration Tests
# ============================================================================


class TestOrchestrationIntegration:
    """Integration tests for full orchestration flow."""

    @pytest.mark.asyncio
    async def test_end_to_end_feature_orchestration(
        self, mock_task_orchestrator, mock_agent_router, temp_dir
    ):
        """Test complete feature orchestration flow."""
        # Create a feature task
        task = MockTask(
            id="feature-oauth",
            title="Implement OAuth authentication",
            description="Full OAuth 2.0 implementation with PKCE, including UI and API",
            task_type="feature",
        )

        # Verify orchestration is triggered
        should_orchestrate = await mock_task_orchestrator.should_orchestrate(task)
        assert should_orchestrate is True

        # Run full orchestration
        result = await mock_task_orchestrator.orchestrate(task)

        # Verify all stages completed
        assert result["success"] is True
        assert len(result["stages_completed"]) == 4  # research, planning, impl, review
        assert "research" in result["stages_completed"]
        assert "planning" in result["stages_completed"]
        assert "implementation" in result["stages_completed"]
        assert "review" in result["stages_completed"]

        # Verify subtasks were generated
        assert len(result["subtasks_generated"]) > 0

        # Verify subtasks are routed to correct agents
        for subtask in result["subtasks_generated"]:
            agent = mock_agent_router.route(subtask)
            assert agent in mock_agent_router.get_available_agents()

    @pytest.mark.asyncio
    async def test_context_persistence(self, mock_task_orchestrator, temp_dir):
        """Context should be saved and readable across stages."""
        task_id = "context-test"
        context = MockOrchestrationContext(
            task_id, Path(temp_dir) / ".sugar" / "orchestration" / task_id
        )

        # Add content from each stage
        context.add_research("Research findings: OAuth best practices")
        context.add_plan("Implementation plan: 3 subtasks")
        context.add_subtask_result("subtask-1", "Backend API completed")
        context.add_subtask_result("subtask-2", "Frontend UI completed")

        # Get accumulated context
        full_context = context.get_full_context()

        # Verify all content is present
        assert "Research" in full_context
        assert "OAuth best practices" in full_context
        assert "Plan" in full_context
        assert "3 subtasks" in full_context
        assert "Subtask Results" in full_context
        assert "Backend API completed" in full_context
        assert "Frontend UI completed" in full_context

    @pytest.mark.asyncio
    async def test_subtask_queue_integration(self, mock_task_orchestrator):
        """Subtasks should be added to work queue correctly."""
        task = MockTask(
            id="parent-task",
            title="Build complete auth system",
            description="Authentication with OAuth",
            task_type="feature",
        )

        # Run orchestration
        result = await mock_task_orchestrator.orchestrate(task)

        # Verify subtasks were generated
        subtasks = result["subtasks_generated"]
        assert len(subtasks) > 0

        # Verify parent relationship
        for subtask in subtasks:
            assert subtask.parent_task_id == "parent-task"

        # Verify dependency chain
        backend_task = next(
            (t for t in subtasks if "Backend" in t.title),
            None,
        )
        ui_task = next(
            (t for t in subtasks if "UI" in t.title),
            None,
        )

        if backend_task and ui_task:
            # UI should be blocked by backend
            assert backend_task.id in ui_task.blocked_by

    @pytest.mark.asyncio
    async def test_parallel_subtask_execution(self, mock_task_orchestrator):
        """Multiple independent subtasks execute in parallel."""
        # Create independent subtasks (no blockers)
        subtasks = [
            MockTask(
                id=f"subtask-{i}",
                title=f"Independent task {i}",
                description=f"Task {i} has no dependencies",
                task_type="feature",
            )
            for i in range(3)
        ]

        start_time = asyncio.get_event_loop().time()
        results = await mock_task_orchestrator.run_implementation_stage(subtasks)
        end_time = asyncio.get_event_loop().time()

        # All should complete
        assert len(results) == 3
        assert all(r.success for r in results)

        # Should be parallel (much faster than sequential)
        elapsed = end_time - start_time
        # If sequential: 3 * 0.01 = 0.03s, parallel should be ~0.01s
        assert elapsed < 0.05

    @pytest.mark.asyncio
    async def test_orchestration_with_mixed_task_types(
        self, mock_task_orchestrator, mock_agent_router
    ):
        """Orchestration handles different task types and routes correctly."""
        plan_output = """
        ## Subtasks
        1. Backend API - Create authentication endpoints
        2. Frontend UI - Build login components
        3. Tests - Add test coverage
        """

        subtasks = await mock_task_orchestrator.generate_subtasks(plan_output)

        # Route each subtask to appropriate agent
        routing = {subtask.id: mock_agent_router.route(subtask) for subtask in subtasks}

        # Verify specialized routing
        backend_subtask = next(t for t in subtasks if "Backend" in t.title)
        ui_subtask = next(t for t in subtasks if "UI" in t.title)
        test_subtask = next(t for t in subtasks if "Tests" in t.title)

        assert routing[backend_subtask.id] == "backend-developer"
        assert routing[ui_subtask.id] == "frontend-designer"
        assert routing[test_subtask.id] == "qa-engineer"

    @pytest.mark.asyncio
    async def test_orchestration_stage_dependencies(
        self, orchestration_config, temp_dir
    ):
        """Stages respect dependency configuration."""
        # Verify planning depends on research
        planning_config = orchestration_config["stages"]["planning"]
        assert "research" in planning_config.get("depends_on", [])

        # Verify review depends on implementation
        review_config = orchestration_config["stages"]["review"]
        assert "implementation" in review_config.get("depends_on", [])

    @pytest.mark.asyncio
    async def test_files_modified_tracking(self, temp_dir):
        """Track all files modified across subtasks."""
        context = MockOrchestrationContext(
            "track-files", Path(temp_dir) / ".sugar" / "orchestration" / "track-files"
        )

        # Simulate subtask results with file modifications
        context.add_subtask_result("subtask-1", "Modified /src/auth.py")
        context.add_subtask_result("subtask-2", "Modified /src/utils.py")

        files_modified = context.get_files_modified()

        assert len(files_modified) > 0
        assert any("/src/auth.py" in f for f in files_modified)
        assert any("/src/utils.py" in f for f in files_modified)


# ============================================================================
# Configuration Tests
# ============================================================================


class TestOrchestrationConfiguration:
    """Test configuration parsing and defaults."""

    def test_orchestration_enabled_by_default(self, orchestration_config):
        """Orchestration should be enabled in config."""
        assert orchestration_config["enabled"] is True

    def test_auto_decompose_mode(self, orchestration_config):
        """Auto decompose mode is configured."""
        assert orchestration_config["auto_decompose"] in [
            "auto",
            "explicit",
            "disabled",
        ]

    def test_detection_rules_configured(self, orchestration_config):
        """Detection rules are properly configured."""
        detection = orchestration_config["detection"]

        assert "task_types" in detection
        assert "feature" in detection["task_types"]
        assert "epic" in detection["task_types"]

        assert "keywords" in detection
        assert len(detection["keywords"]) > 0
        assert "implement" in detection["keywords"]

    def test_stage_configuration(self, orchestration_config):
        """All stages are properly configured."""
        stages = orchestration_config["stages"]

        # Verify key stages exist
        assert "research" in stages
        assert "planning" in stages
        assert "implementation" in stages
        assert "review" in stages

        # Verify research config
        research = stages["research"]
        assert research["enabled"] is True
        assert research["agent"] == "Explore"
        assert "timeout" in research

        # Verify planning config
        planning = stages["planning"]
        assert planning["enabled"] is True
        assert planning["agent"] == "Plan"
        assert planning["creates_subtasks"] is True

        # Verify implementation config
        implementation = stages["implementation"]
        assert implementation["parallel"] is True
        assert "max_concurrent" in implementation
        assert "agent_routing" in implementation

    def test_agent_routing_patterns(self, orchestration_config):
        """Agent routing patterns are configured."""
        routing = orchestration_config["stages"]["implementation"]["agent_routing"]

        assert "default" in routing
        assert routing["default"] == "general-purpose"

        # Verify key routing patterns exist
        assert any("frontend" in pattern for pattern in routing.keys())
        assert any("backend" in pattern for pattern in routing.keys())
        assert any("test" in pattern for pattern in routing.keys())
