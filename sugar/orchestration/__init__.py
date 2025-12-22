"""
Task Orchestration System for Sugar

Provides intelligent decomposition and execution of complex features through:
- Staged workflows (research, planning, implementation, review)
- Specialist agent routing
- Parallel sub-task execution
- Context accumulation across stages
"""

from .task_orchestrator import (
    TaskOrchestrator,
    OrchestrationStage,
    StageResult,
    OrchestrationResult,
)
from .agent_router import AgentRouter

__all__ = [
    "TaskOrchestrator",
    "OrchestrationStage",
    "StageResult",
    "OrchestrationResult",
    "AgentRouter",
]
