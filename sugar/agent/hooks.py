"""
Quality Gate Hooks for Claude Agent SDK

These hooks integrate Sugar's quality gates system with the Agent SDK's
PreToolUse and PostToolUse hook points.
"""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HookContext:
    """Context passed to hook callbacks (placeholder for SDK's HookContext)"""
    pass


class QualityGateHooks:
    """
    Quality gate hooks for the Claude Agent SDK.

    Provides PreToolUse and PostToolUse hooks that enforce Sugar's
    quality gates during agent execution.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize quality gate hooks.

        Args:
            config: Quality gates configuration
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)

        # Tracking state
        self._tool_executions: List[Dict[str, Any]] = []
        self._blocked_operations: List[Dict[str, Any]] = []
        self._files_modified: List[str] = []
        self._security_violations: List[Dict[str, Any]] = []

        # Configuration
        self._protected_paths = self.config.get("protected_paths", [
            ".env",
            ".env.local",
            "credentials.json",
            "secrets.yaml",
            ".git/config",
        ])
        self._dangerous_commands = self.config.get("dangerous_commands", [
            "rm -rf /",
            "rm -rf ~",
            "> /dev/sda",
            "mkfs.",
            ":(){:|:&};:",
            "chmod -R 777 /",
        ])

    async def pre_tool_security_check(
        self,
        input_data: Dict[str, Any],
        tool_use_id: Optional[str],
        context: HookContext,
    ) -> Dict[str, Any]:
        """
        PreToolUse hook: Security check before tool execution.

        Checks for:
        - Protected file access (.env, credentials, etc.)
        - Dangerous bash commands
        - Unauthorized modifications

        Args:
            input_data: Tool input data with 'tool_name' and 'tool_input'
            tool_use_id: Unique ID for correlating with PostToolUse
            context: Hook context (reserved for future use)

        Returns:
            Empty dict to allow, or dict with hookSpecificOutput to block
        """
        if not self.enabled:
            return {}

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Check for protected file access
        if tool_name in ("Write", "Edit", "Read"):
            file_path = tool_input.get("file_path", "")
            if self._is_protected_file(file_path):
                violation = {
                    "tool": tool_name,
                    "file": file_path,
                    "reason": "Protected file access blocked",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                self._security_violations.append(violation)
                self._blocked_operations.append(violation)

                logger.warning(f"Blocked access to protected file: {file_path}")

                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            f"Access to protected file '{file_path}' is not allowed. "
                            "This file may contain sensitive information."
                        ),
                    }
                }

        # Check for dangerous bash commands
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            if self._is_dangerous_command(command):
                violation = {
                    "tool": tool_name,
                    "command": command,
                    "reason": "Dangerous command blocked",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                self._security_violations.append(violation)
                self._blocked_operations.append(violation)

                logger.warning(f"Blocked dangerous command: {command}")

                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            "This command has been blocked for safety reasons. "
                            "It could potentially cause harm to the system."
                        ),
                    }
                }

        # Track the tool execution (will be completed in post hook)
        self._tool_executions.append({
            "tool_use_id": tool_use_id,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "started_at": datetime.utcnow().isoformat(),
            "completed": False,
        })

        return {}

    async def post_tool_audit(
        self,
        input_data: Dict[str, Any],
        tool_use_id: Optional[str],
        context: HookContext,
    ) -> Dict[str, Any]:
        """
        PostToolUse hook: Audit after tool execution.

        Logs tool usage and tracks file modifications for quality gate reporting.

        Args:
            input_data: Tool result data
            tool_use_id: Unique ID for correlating with PreToolUse
            context: Hook context (reserved for future use)

        Returns:
            Empty dict (audit-only, no blocking)
        """
        if not self.enabled:
            return {}

        tool_name = input_data.get("tool_name", "")
        tool_response = input_data.get("tool_response", {})

        # Find and update the matching execution record
        for execution in self._tool_executions:
            if execution.get("tool_use_id") == tool_use_id and not execution.get("completed"):
                execution["completed"] = True
                execution["completed_at"] = datetime.utcnow().isoformat()
                execution["response"] = tool_response
                break

        # Track file modifications
        if tool_name in ("Write", "Edit"):
            tool_input = input_data.get("tool_input", {})
            file_path = tool_input.get("file_path", "")
            if file_path and file_path not in self._files_modified:
                self._files_modified.append(file_path)
                logger.debug(f"File modified: {file_path}")

        logger.debug(f"Tool executed: {tool_name} (id: {tool_use_id})")

        return {}

    def _is_protected_file(self, file_path: str) -> bool:
        """Check if a file path is protected"""
        if not file_path:
            return False

        # Normalize path
        file_name = file_path.split("/")[-1]
        normalized_path = file_path.lower()

        for protected in self._protected_paths:
            protected_lower = protected.lower()
            if file_name.lower() == protected_lower:
                return True
            if normalized_path.endswith(protected_lower):
                return True
            if protected_lower in normalized_path:
                return True

        return False

    def _is_dangerous_command(self, command: str) -> bool:
        """Check if a bash command is dangerous"""
        if not command:
            return False

        command_lower = command.lower().strip()

        for dangerous in self._dangerous_commands:
            if dangerous.lower() in command_lower:
                return True

        return False

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of all executions during this session"""
        return {
            "total_tool_executions": len(self._tool_executions),
            "completed_executions": sum(
                1 for e in self._tool_executions if e.get("completed")
            ),
            "blocked_operations": len(self._blocked_operations),
            "security_violations": len(self._security_violations),
            "files_modified": self._files_modified.copy(),
            "violations": self._security_violations.copy(),
        }

    def reset(self) -> None:
        """Reset tracking state for a new session"""
        self._tool_executions = []
        self._blocked_operations = []
        self._files_modified = []
        self._security_violations = []


def create_preflight_hook(
    checks: List[Callable[[Dict[str, Any]], bool]],
) -> Callable:
    """
    Factory to create a preflight check hook.

    Args:
        checks: List of check functions that return True if the operation is allowed

    Returns:
        Hook callback function
    """

    async def preflight_hook(
        input_data: Dict[str, Any],
        tool_use_id: Optional[str],
        context: HookContext,
    ) -> Dict[str, Any]:
        for check in checks:
            if not check(input_data):
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": "Preflight check failed",
                    }
                }
        return {}

    return preflight_hook


def create_audit_hook(
    log_func: Optional[Callable[[str], None]] = None,
) -> Callable:
    """
    Factory to create an audit logging hook.

    Args:
        log_func: Optional custom logging function

    Returns:
        Hook callback function
    """
    log = log_func or logger.info

    async def audit_hook(
        input_data: Dict[str, Any],
        tool_use_id: Optional[str],
        context: HookContext,
    ) -> Dict[str, Any]:
        tool_name = input_data.get("tool_name", "unknown")
        log(f"[AUDIT] Tool executed: {tool_name}")
        return {}

    return audit_hook


def create_security_hook(
    protected_paths: Optional[List[str]] = None,
    dangerous_commands: Optional[List[str]] = None,
) -> Callable:
    """
    Factory to create a security check hook.

    Args:
        protected_paths: List of file paths/patterns to protect
        dangerous_commands: List of dangerous command patterns to block

    Returns:
        Hook callback function
    """
    paths = protected_paths or [".env", "credentials.json", "secrets.yaml"]
    commands = dangerous_commands or ["rm -rf /", "rm -rf ~"]

    async def security_hook(
        input_data: Dict[str, Any],
        tool_use_id: Optional[str],
        context: HookContext,
    ) -> Dict[str, Any]:
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Check file access
        if tool_name in ("Write", "Edit", "Read"):
            file_path = tool_input.get("file_path", "")
            for protected in paths:
                if protected.lower() in file_path.lower():
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": f"Access to {protected} is blocked",
                        }
                    }

        # Check bash commands
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            for dangerous in commands:
                if dangerous.lower() in command.lower():
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": "Dangerous command blocked",
                        }
                    }

        return {}

    return security_hook
