"""
Base Executor Interface

Abstract base class that defines the interface for task executors in Sugar.
Both the legacy ClaudeWrapper and new AgentSDKExecutor implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionResult:
    """Standard result from any executor"""

    success: bool
    output: str
    files_changed: List[str] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "output": self.output,
            "files_changed": self.files_changed,
            "actions_taken": self.actions_taken,
            "execution_time": self.execution_time,
            "error": self.error,
            "metadata": self.metadata,
        }


class BaseExecutor(ABC):
    """
    Abstract base class for task executors.

    All executors (ClaudeWrapper, AgentSDKExecutor) should implement this interface
    to ensure consistent behavior across execution strategies.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the executor.

        Args:
            config: Executor configuration dictionary
        """
        self.config = config
        self.dry_run = config.get("dry_run", True)

    @abstractmethod
    async def execute_work(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a work item.

        Args:
            work_item: Work item dictionary containing:
                - id: Unique identifier
                - type: Task type (bug_fix, feature, refactor, etc.)
                - title: Task title
                - description: Task description
                - priority: Priority level (1-5)
                - context: Optional additional context
                - source: Where the task came from

        Returns:
            Result dictionary containing:
                - success: Whether execution succeeded
                - result: Raw execution result
                - timestamp: When execution completed
                - work_item_id: ID of the work item
                - execution_time: How long execution took
                - output: Executor output
                - files_changed: List of modified files
                - summary: Summary of what was done
                - actions_taken: List of actions performed
        """
        pass

    @abstractmethod
    async def validate(self) -> bool:
        """
        Validate that the executor is properly configured and ready.

        Returns:
            True if executor is ready, False otherwise
        """
        pass

    def get_executor_type(self) -> str:
        """
        Get the type of this executor.

        Returns:
            Executor type string (e.g., 'claude_wrapper', 'agent_sdk')
        """
        return self.__class__.__name__

    async def _simulate_execution(self, work_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate execution for dry run mode.

        Args:
            work_item: Work item to simulate

        Returns:
            Simulated result dictionary
        """
        import asyncio

        # Simulate some execution time
        await asyncio.sleep(1.0)

        return {
            "success": True,
            "simulated": True,
            "result": {
                "stdout": f"SIMULATION: Completed {work_item.get('type', 'task')}",
                "actions_taken": [
                    "Analyzed task requirements",
                    "Simulated implementation",
                ],
                "files_modified": [],
                "summary": f"Simulated completion of: {work_item.get('title', 'task')}",
            },
            "timestamp": datetime.utcnow().isoformat(),
            "work_item_id": work_item.get("id"),
            "execution_time": 1.0,
            "output": "Simulation completed",
            "files_changed": [],
            "summary": "Simulated execution",
            "actions_taken": ["Simulation only - no actual changes made"],
        }
