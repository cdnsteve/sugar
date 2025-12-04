"""
Quality module for Sugar AI - Tool output interpretation and task generation

This module provides Claude Code-powered interpretation of external tool outputs
and automatic task creation based on the analysis.
"""

from .claude_invoker import ToolOutputInterpreter

__all__ = ["ToolOutputInterpreter"]
