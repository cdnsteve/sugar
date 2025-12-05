"""
Executor Module - Claude Code CLI Integration

This module provides the execution layer for Sugar's autonomous development system:

- StructuredRequest/Response: Unified request/response format for Claude interactions
- ClaudeWrapper: Wrapper for Claude Code CLI execution with context persistence
- RequestBuilder: Helper class for building structured requests
- AgentType/DynamicAgentType: Agent type definitions for task routing
"""

from .structured_request import (
    StructuredRequest,
    StructuredResponse,
    RequestBuilder,
    ExecutionMode,
    AgentType,
    DynamicAgentType,
    TaskContext,
)
from .claude_wrapper import ClaudeWrapper

__all__ = [
    # Core classes
    "StructuredRequest",
    "StructuredResponse",
    "RequestBuilder",
    "ClaudeWrapper",
    # Enums and types
    "ExecutionMode",
    "AgentType",
    "DynamicAgentType",
    "TaskContext",
]
