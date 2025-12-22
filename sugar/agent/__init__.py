"""
Sugar Agent Module - Claude Agent SDK integration for Sugar 3.0

This module provides the native SDK-based agent execution layer,
replacing the subprocess-based ClaudeWrapper approach.
"""

from .base import SugarAgent, SugarAgentConfig
from .hooks import (
    QualityGateHooks,
    create_preflight_hook,
    create_audit_hook,
    create_security_hook,
)
from .subagent_manager import SubAgentManager, SubAgentResult
from .context_manager import ContextManager, Message, ContextSummary

__all__ = [
    "SugarAgent",
    "SugarAgentConfig",
    "QualityGateHooks",
    "create_preflight_hook",
    "create_audit_hook",
    "create_security_hook",
    "SubAgentManager",
    "SubAgentResult",
    "ContextManager",
    "Message",
    "ContextSummary",
]
