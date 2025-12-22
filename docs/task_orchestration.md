# Task Orchestration System

Sugar's Task Orchestration system enables intelligent decomposition and execution of complex features through staged workflows and specialist agent routing.

## Overview

When Sugar encounters a large feature request, the orchestration system:

1. **Detects** that the task requires decomposition
2. **Researches** context via web search and codebase analysis
3. **Plans** the implementation and generates sub-tasks
4. **Routes** each sub-task to the appropriate specialist agent
5. **Executes** sub-tasks with parallelism where possible
6. **Reviews** the completed work before marking done

```
Large Feature Task
        ↓
┌───────────────────────────────────────────────────────┐
│ Stage 1: RESEARCH                                     │
│ • Web search for best practices                       │
│ • Gather relevant documentation                       │
│ • Analyze existing codebase patterns                  │
│ Agent: tech-lead / Explore                            │
│ Output: context.md, research_findings.md              │
└───────────────────────────────────────────────────────┘
        ↓ (context passes forward)
┌───────────────────────────────────────────────────────┐
│ Stage 2: PLANNING                                     │
│ • Create implementation plan                          │
│ • Break into sub-tasks                                │
│ • Identify specialist agents needed                   │
│ Agent: tech-lead / Plan                               │
│ Output: plan.md, sub-tasks[]                          │
└───────────────────────────────────────────────────────┘
        ↓ (sub-tasks added to queue)
┌───────────────────────────────────────────────────────┐
│ Stage 3: IMPLEMENTATION (parallel where possible)     │
│ • Sub-task A: Auth UI       → frontend-designer       │
│ • Sub-task B: Auth API      → backend-developer       │
│ • Sub-task C: Auth tests    → qa-engineer             │
│ • Sub-task D: Auth docs     → general-purpose         │
└───────────────────────────────────────────────────────┘
        ↓ (all sub-tasks complete)
┌───────────────────────────────────────────────────────┐
│ Stage 4: REVIEW & INTEGRATION                         │
│ • Code review all changes                             │
│ • Run full test suite                                 │
│ • Verify feature works end-to-end                     │
│ Agent: code-reviewer, qa-engineer                     │
└───────────────────────────────────────────────────────┘
```

## Architecture

```
┌─────────────────────────────────────────┐
│           TaskOrchestrator              │  ← High-level workflow
│  - Stage management                     │
│  - Context accumulation                 │
│  - Sub-task generation                  │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│            AgentRouter                  │  ← Specialist selection
│  - Pattern matching on task content     │
│  - Maps to specialist agents            │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│          SubAgentManager                │  ← Parallel execution
│  - Concurrency control                  │
│  - Isolated execution                   │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│         AgentSDKExecutor                │  ← Task execution
│  - Agent SDK integration                │
└─────────────────────────────────────────┘
```

## Configuration

```yaml
# .sugar/config.yaml
orchestration:
  enabled: true

  # When to trigger orchestration
  # - auto: System detects complex tasks automatically
  # - explicit: Only when task has orchestrate: true flag
  # - disabled: Never orchestrate, run tasks directly
  auto_decompose: "auto"

  # Detection rules for auto mode
  detection:
    # Task types that always trigger orchestration
    task_types: ["feature", "epic"]

    # Keywords in title/description that trigger orchestration
    keywords:
      - "implement"
      - "build"
      - "create full"
      - "add complete"
      - "redesign"
      - "refactor entire"

    # Minimum estimated complexity (future: AI-based estimation)
    min_complexity: "high"  # low, medium, high

  # Stage definitions
  stages:
    research:
      enabled: true
      agent: "Explore"
      timeout: 600  # 10 minutes
      actions:
        - web_search
        - codebase_analysis
        - doc_gathering
      output_to_context: true
      output_path: ".sugar/orchestration/{task_id}/research.md"

    planning:
      enabled: true
      agent: "Plan"
      timeout: 300  # 5 minutes
      depends_on: ["research"]
      creates_subtasks: true
      output_path: ".sugar/orchestration/{task_id}/plan.md"

    implementation:
      parallel: true
      max_concurrent: 3
      timeout_per_task: 1800  # 30 minutes per sub-task
      agent_routing:
        # Pattern → Agent mapping
        "*ui*|*frontend*|*component*|*design*": "frontend-designer"
        "*api*|*backend*|*endpoint*|*service*": "backend-developer"
        "*test*|*spec*|*coverage*": "qa-engineer"
        "*security*|*auth*|*permission*": "security-engineer"
        "*devops*|*deploy*|*ci*|*docker*": "devops-engineer"
        "*doc*|*readme*|*guide*": "general-purpose"
        "default": "general-purpose"

    review:
      enabled: true
      depends_on: ["implementation"]
      agents:
        - "code-reviewer"
        - "qa-engineer"
      run_tests: true
      require_passing: true
```

## Components

### TaskOrchestrator

The main orchestration engine that manages the workflow.

```python
class TaskOrchestrator:
    """
    Orchestrates complex tasks through staged execution.

    Responsibilities:
    - Detect if task requires orchestration
    - Manage stage transitions
    - Accumulate context between stages
    - Track sub-task completion
    - Trigger review stage when implementation complete
    """

    async def should_orchestrate(self, task: Task) -> bool:
        """Determine if task needs orchestration based on config."""

    async def orchestrate(self, task: Task) -> OrchestrationResult:
        """Run full orchestration workflow for a task."""

    async def run_stage(self, stage: Stage, context: Context) -> StageResult:
        """Execute a single stage of the workflow."""

    async def generate_subtasks(self, plan: Plan) -> List[Task]:
        """Generate sub-tasks from planning stage output."""
```

### AgentRouter

Routes tasks to appropriate specialist agents.

```python
class AgentRouter:
    """
    Routes tasks to specialist agents based on content analysis.

    Supports:
    - Pattern matching on task title/description
    - Task type based routing
    - Fallback to default agent
    """

    def route(self, task: Task) -> str:
        """Return the agent name for a task."""

    def get_available_agents(self) -> List[str]:
        """List available specialist agents."""
```

### Available Specialist Agents

These map to Claude Code's built-in agent types:

| Agent | Use Case |
|-------|----------|
| `general-purpose` | Default for most tasks |
| `tech-lead` | Architecture, planning, complex decisions |
| `code-reviewer` | Code review, refactoring feedback |
| `frontend-designer` | UI/UX, components, styling |
| `backend-developer` | APIs, databases, server logic |
| `qa-engineer` | Testing, test strategies, coverage |
| `security-engineer` | Security audits, auth, vulnerabilities |
| `devops-engineer` | CI/CD, infrastructure, deployment |
| `Explore` | Codebase exploration, research |
| `Plan` | Implementation planning |

## Workflow Example

### Input Task

```bash
sugar add "Add user authentication with OAuth support" --type feature
```

### Stage 1: Research

The Explore agent:
- Searches web for "OAuth 2.0 best practices 2025"
- Analyzes codebase for existing auth patterns
- Checks for existing user models
- Reviews dependencies (existing auth libraries)

Output saved to `.sugar/orchestration/{task_id}/research.md`:

```markdown
# Research: OAuth Authentication

## Web Research
- OAuth 2.0 recommended flow: Authorization Code with PKCE
- Popular libraries: authlib (Python), passport (Node)
- Security considerations: token storage, CSRF protection

## Codebase Analysis
- Existing User model in `app/models/user.py`
- No current auth implementation
- Using FastAPI framework
- SQLAlchemy for ORM

## Recommendations
- Use authlib for OAuth implementation
- Add OAuth provider configuration
- Implement token refresh mechanism
```

### Stage 2: Planning

The Plan agent reads research context and creates:

```markdown
# Implementation Plan: OAuth Authentication

## Sub-tasks

1. **Create OAuth Configuration**
   - Add OAuth provider settings
   - Environment variables for client ID/secret
   - Agent: backend-developer

2. **Implement OAuth Routes**
   - /auth/login - Initiate OAuth flow
   - /auth/callback - Handle OAuth callback
   - /auth/logout - Clear session
   - Agent: backend-developer

3. **Create Login UI**
   - Login page with OAuth buttons
   - Loading states
   - Error handling
   - Agent: frontend-designer

4. **Add Session Management**
   - JWT token generation
   - Token refresh logic
   - Session storage
   - Agent: security-engineer

5. **Write Tests**
   - Unit tests for OAuth flow
   - Integration tests for routes
   - E2E login flow test
   - Agent: qa-engineer

6. **Update Documentation**
   - Auth setup guide
   - Environment variables
   - API documentation
   - Agent: general-purpose

## Dependencies
- Tasks 1 must complete before 2, 3, 4
- Tasks 2, 3, 4 can run in parallel
- Task 5 depends on 2, 3, 4
- Task 6 can run anytime
```

### Stage 3: Implementation

Sub-tasks added to queue with relationships:

```
Parent: "Add user authentication with OAuth support" (orchestrating)
  ├── Sub-task 1: "Create OAuth Configuration" (pending)
  ├── Sub-task 2: "Implement OAuth Routes" (blocked by 1)
  ├── Sub-task 3: "Create Login UI" (blocked by 1)
  ├── Sub-task 4: "Add Session Management" (blocked by 1)
  ├── Sub-task 5: "Write Tests" (blocked by 2,3,4)
  └── Sub-task 6: "Update Documentation" (pending)
```

Execution order:
1. Tasks 1 and 6 start (no blockers)
2. When 1 completes → Tasks 2, 3, 4 start in parallel
3. When 2, 3, 4 complete → Task 5 starts
4. When all complete → Stage 4 triggers

### Stage 4: Review

The code-reviewer agent:
- Reviews all file changes from sub-tasks
- Checks for code quality issues
- Verifies patterns are consistent

The qa-engineer agent:
- Runs full test suite
- Verifies OAuth flow works end-to-end
- Reports any failures

If review passes → Parent task marked complete
If review fails → Issues added as new tasks

## Task Schema Extensions

```python
@dataclass
class Task:
    id: str
    title: str
    description: str
    type: str  # bug_fix, feature, epic, etc.
    priority: int

    # Orchestration fields
    orchestrate: bool = False  # Explicit orchestration flag
    parent_task_id: Optional[str] = None  # Link to parent
    stage: Optional[str] = None  # Current stage
    blocked_by: List[str] = field(default_factory=list)  # Task IDs

    # Context accumulation
    context_path: Optional[str] = None  # Path to accumulated context

    # Routing
    assigned_agent: Optional[str] = None  # Specialist agent
```

## Context Accumulation

Each stage can read context from previous stages:

```python
class OrchestrationContext:
    """Accumulated context across orchestration stages."""

    task_id: str
    base_path: Path  # .sugar/orchestration/{task_id}/

    def add_research(self, content: str) -> None:
        """Add research findings."""

    def add_plan(self, content: str) -> None:
        """Add implementation plan."""

    def add_subtask_result(self, subtask_id: str, result: str) -> None:
        """Add result from completed sub-task."""

    def get_full_context(self) -> str:
        """Get accumulated context for current stage."""

    def get_files_modified(self) -> List[str]:
        """Get all files modified across sub-tasks."""
```

## CLI Commands

```bash
# Add task with explicit orchestration
sugar add "Build payment system" --type feature --orchestrate

# View orchestration status
sugar status --orchestration

# View specific task's orchestration
sugar show <task_id> --stages

# Skip to implementation (bypass research/planning)
sugar add "Add logout button" --type feature --skip-stages research,planning

# Re-run a stage
sugar orchestrate <task_id> --stage planning

# View orchestration context
sugar context <task_id>
```

## Future Enhancements

### AI-Based Complexity Detection

Instead of keyword matching, use AI to estimate task complexity:

```python
async def estimate_complexity(task: Task) -> ComplexityScore:
    """Use AI to estimate if task needs orchestration."""
    prompt = f"""
    Analyze this task and estimate complexity:
    Title: {task.title}
    Description: {task.description}

    Consider:
    - Number of files likely affected
    - Number of different concerns (UI, API, DB, etc.)
    - Integration complexity
    - Testing requirements

    Return: low, medium, or high
    """
```

### Learning from History

Track orchestration outcomes to improve:
- Which task types benefit most from orchestration
- Optimal stage configurations
- Agent routing accuracy
- Time savings from parallelization

### Custom Stage Definitions

Allow users to define custom stages:

```yaml
orchestration:
  custom_stages:
    security_audit:
      enabled: true
      agent: "security-engineer"
      after: "implementation"
      before: "review"
      actions:
        - security_scan
        - vulnerability_check
```

## Relationship to SubAgentManager

SubAgentManager is the **low-level execution primitive** used by the orchestration system:

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| High | TaskOrchestrator | Workflow stages, context |
| Mid | AgentRouter | Specialist selection |
| Low | SubAgentManager | Parallel execution |
| Base | AgentSDKExecutor | Individual task execution |

The orchestration system uses SubAgentManager when:
- Running multiple sub-tasks in parallel during implementation stage
- Executing parallel research queries
- Running multiple review checks simultaneously

```python
# Orchestrator using SubAgentManager for parallel execution
async def run_implementation_stage(self, subtasks: List[Task]) -> List[Result]:
    manager = SubAgentManager(
        parent_config=self.config,
        max_concurrent=self.stages["implementation"]["max_concurrent"]
    )

    # Group subtasks by dependency level
    ready_tasks = [t for t in subtasks if not t.blocked_by]

    # Execute ready tasks in parallel
    results = await manager.spawn_parallel([
        {
            "task_id": t.id,
            "prompt": t.to_prompt(),
            "agent": self.router.route(t)
        }
        for t in ready_tasks
    ])

    return results
```
