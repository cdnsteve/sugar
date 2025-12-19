"""
Tests for Sugar agent hooks module (P3 priority - security critical)

Tests security hooks, quality gates, and audit logging.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any

from sugar.agent.hooks import (
    QualityGateHooks,
    HookContext,
    create_preflight_hook,
    create_audit_hook,
    create_security_hook,
)


class TestQualityGateHooksInit:
    """Tests for QualityGateHooks initialization"""

    def test_init_defaults(self, quality_gate_hooks):
        assert quality_gate_hooks.enabled is True
        assert len(quality_gate_hooks._protected_paths) > 0
        assert ".env" in quality_gate_hooks._protected_paths
        assert len(quality_gate_hooks._dangerous_commands) > 0

    def test_init_disabled(self, quality_gate_hooks_disabled):
        assert quality_gate_hooks_disabled.enabled is False

    def test_init_custom_config(self):
        config = {
            "enabled": True,
            "protected_paths": [".secrets", "api_keys.json"],
            "dangerous_commands": ["format c:"],
        }
        hooks = QualityGateHooks(config=config)
        assert hooks._protected_paths == [".secrets", "api_keys.json"]
        assert hooks._dangerous_commands == ["format c:"]


class TestPreToolSecurityCheck:
    """Tests for pre_tool_security_check hook"""

    @pytest.mark.asyncio
    async def test_allows_normal_file_read(self, quality_gate_hooks):
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/src/main.py"},
        }
        result = await quality_gate_hooks.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )
        assert result == {}  # Empty dict means allowed

    @pytest.mark.asyncio
    async def test_blocks_env_file_access(self, quality_gate_hooks):
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/project/.env"},
        }
        result = await quality_gate_hooks.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "protected file" in result["hookSpecificOutput"]["permissionDecisionReason"]

    @pytest.mark.asyncio
    async def test_blocks_env_local_file(self, quality_gate_hooks):
        input_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": "/app/.env.local"},
        }
        result = await quality_gate_hooks.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_blocks_credentials_file(self, quality_gate_hooks):
        input_data = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "/config/credentials.json"},
        }
        result = await quality_gate_hooks.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_blocks_secrets_yaml(self, quality_gate_hooks):
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/deploy/secrets.yaml"},
        }
        result = await quality_gate_hooks.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_blocks_git_config(self, quality_gate_hooks):
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/repo/.git/config"},
        }
        result = await quality_gate_hooks.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_allows_normal_bash_command(self, quality_gate_hooks):
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la /src"},
        }
        result = await quality_gate_hooks.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )
        assert result == {}  # Empty dict means allowed

    @pytest.mark.asyncio
    async def test_blocks_rm_rf_root(self, quality_gate_hooks):
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /"},
        }
        result = await quality_gate_hooks.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "safety reasons" in result["hookSpecificOutput"]["permissionDecisionReason"]

    @pytest.mark.asyncio
    async def test_blocks_rm_rf_home(self, quality_gate_hooks):
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf ~"},
        }
        result = await quality_gate_hooks.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_blocks_fork_bomb(self, quality_gate_hooks):
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": ":(){:|:&};:"},
        }
        result = await quality_gate_hooks.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_blocks_disk_wipe(self, quality_gate_hooks):
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "> /dev/sda"},
        }
        result = await quality_gate_hooks.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_blocks_mkfs(self, quality_gate_hooks):
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "mkfs.ext4 /dev/sda1"},
        }
        result = await quality_gate_hooks.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_blocks_chmod_777_root(self, quality_gate_hooks):
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "chmod -R 777 /"},
        }
        result = await quality_gate_hooks.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_disabled_hooks_allow_everything(self, quality_gate_hooks_disabled):
        # Should allow protected file access when disabled
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/project/.env"},
        }
        result = await quality_gate_hooks_disabled.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )
        assert result == {}

        # Should allow dangerous commands when disabled
        input_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /"},
        }
        result = await quality_gate_hooks_disabled.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_tracks_tool_execution(self, quality_gate_hooks):
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/src/main.py"},
        }
        await quality_gate_hooks.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )

        assert len(quality_gate_hooks._tool_executions) == 1
        execution = quality_gate_hooks._tool_executions[0]
        assert execution["tool_name"] == "Read"
        assert execution["tool_use_id"] == "tool_123"
        assert execution["completed"] is False

    @pytest.mark.asyncio
    async def test_tracks_security_violations(self, quality_gate_hooks):
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/project/.env"},
        }
        await quality_gate_hooks.pre_tool_security_check(
            input_data, "tool_123", HookContext()
        )

        assert len(quality_gate_hooks._security_violations) == 1
        violation = quality_gate_hooks._security_violations[0]
        assert violation["tool"] == "Read"
        assert violation["file"] == "/project/.env"


class TestPostToolAudit:
    """Tests for post_tool_audit hook"""

    @pytest.mark.asyncio
    async def test_completes_tool_execution(self, quality_gate_hooks):
        # First, simulate pre-hook
        pre_input = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/src/main.py"},
        }
        await quality_gate_hooks.pre_tool_security_check(
            pre_input, "tool_123", HookContext()
        )

        # Then post-hook
        post_input = {
            "tool_name": "Read",
            "tool_response": {"content": "file contents"},
        }
        await quality_gate_hooks.post_tool_audit(
            post_input, "tool_123", HookContext()
        )

        execution = quality_gate_hooks._tool_executions[0]
        assert execution["completed"] is True
        assert "completed_at" in execution

    @pytest.mark.asyncio
    async def test_tracks_file_modifications(self, quality_gate_hooks):
        # Simulate Write tool
        pre_input = {
            "tool_name": "Write",
            "tool_input": {"file_path": "/src/new_file.py"},
        }
        await quality_gate_hooks.pre_tool_security_check(
            pre_input, "tool_123", HookContext()
        )

        post_input = {
            "tool_name": "Write",
            "tool_input": {"file_path": "/src/new_file.py"},
            "tool_response": {"success": True},
        }
        await quality_gate_hooks.post_tool_audit(
            post_input, "tool_123", HookContext()
        )

        assert "/src/new_file.py" in quality_gate_hooks._files_modified

    @pytest.mark.asyncio
    async def test_tracks_edit_modifications(self, quality_gate_hooks):
        pre_input = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "/src/existing.py"},
        }
        await quality_gate_hooks.pre_tool_security_check(
            pre_input, "tool_123", HookContext()
        )

        post_input = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "/src/existing.py"},
            "tool_response": {"success": True},
        }
        await quality_gate_hooks.post_tool_audit(
            post_input, "tool_123", HookContext()
        )

        assert "/src/existing.py" in quality_gate_hooks._files_modified

    @pytest.mark.asyncio
    async def test_disabled_hooks_skip_tracking(self, quality_gate_hooks_disabled):
        post_input = {
            "tool_name": "Write",
            "tool_input": {"file_path": "/src/file.py"},
            "tool_response": {"success": True},
        }
        await quality_gate_hooks_disabled.post_tool_audit(
            post_input, "tool_123", HookContext()
        )

        assert len(quality_gate_hooks_disabled._files_modified) == 0


class TestHelperMethods:
    """Tests for helper methods"""

    def test_is_protected_file_env(self, quality_gate_hooks):
        assert quality_gate_hooks._is_protected_file(".env") is True
        assert quality_gate_hooks._is_protected_file("/path/to/.env") is True
        assert quality_gate_hooks._is_protected_file("/path/.env.local") is True

    def test_is_protected_file_credentials(self, quality_gate_hooks):
        assert quality_gate_hooks._is_protected_file("credentials.json") is True
        assert quality_gate_hooks._is_protected_file("/config/credentials.json") is True

    def test_is_protected_file_safe_path(self, quality_gate_hooks):
        assert quality_gate_hooks._is_protected_file("/src/main.py") is False
        assert quality_gate_hooks._is_protected_file("config.yaml") is False
        assert quality_gate_hooks._is_protected_file("environment.py") is False

    def test_is_protected_file_empty(self, quality_gate_hooks):
        assert quality_gate_hooks._is_protected_file("") is False
        assert quality_gate_hooks._is_protected_file(None) is False

    def test_is_dangerous_command_rm_rf(self, quality_gate_hooks):
        assert quality_gate_hooks._is_dangerous_command("rm -rf /") is True
        assert quality_gate_hooks._is_dangerous_command("rm -rf ~") is True

    def test_is_dangerous_command_safe(self, quality_gate_hooks):
        # Note: "rm -rf /tmp/test" is flagged because it contains "rm -rf /"
        # This is intentional - the check is conservative
        assert quality_gate_hooks._is_dangerous_command("rm file.txt") is False
        assert quality_gate_hooks._is_dangerous_command("ls -la") is False
        assert quality_gate_hooks._is_dangerous_command("git status") is False
        assert quality_gate_hooks._is_dangerous_command("python script.py") is False

    def test_is_dangerous_command_empty(self, quality_gate_hooks):
        assert quality_gate_hooks._is_dangerous_command("") is False
        assert quality_gate_hooks._is_dangerous_command(None) is False


class TestExecutionSummary:
    """Tests for get_execution_summary"""

    @pytest.mark.asyncio
    async def test_empty_summary(self, quality_gate_hooks):
        summary = quality_gate_hooks.get_execution_summary()
        assert summary["total_tool_executions"] == 0
        assert summary["completed_executions"] == 0
        assert summary["blocked_operations"] == 0
        assert summary["security_violations"] == 0
        assert summary["files_modified"] == []
        assert summary["violations"] == []

    @pytest.mark.asyncio
    async def test_summary_with_executions(self, quality_gate_hooks):
        # Simulate some tool executions
        await quality_gate_hooks.pre_tool_security_check(
            {"tool_name": "Read", "tool_input": {"file_path": "/src/a.py"}},
            "tool_1", HookContext()
        )
        await quality_gate_hooks.post_tool_audit(
            {"tool_name": "Read", "tool_response": {}},
            "tool_1", HookContext()
        )

        await quality_gate_hooks.pre_tool_security_check(
            {"tool_name": "Write", "tool_input": {"file_path": "/src/b.py"}},
            "tool_2", HookContext()
        )
        await quality_gate_hooks.post_tool_audit(
            {"tool_name": "Write", "tool_input": {"file_path": "/src/b.py"}, "tool_response": {}},
            "tool_2", HookContext()
        )

        summary = quality_gate_hooks.get_execution_summary()
        assert summary["total_tool_executions"] == 2
        assert summary["completed_executions"] == 2
        assert summary["files_modified"] == ["/src/b.py"]

    @pytest.mark.asyncio
    async def test_summary_with_violations(self, quality_gate_hooks):
        await quality_gate_hooks.pre_tool_security_check(
            {"tool_name": "Read", "tool_input": {"file_path": "/project/.env"}},
            "tool_1", HookContext()
        )

        summary = quality_gate_hooks.get_execution_summary()
        assert summary["blocked_operations"] == 1
        assert summary["security_violations"] == 1
        assert len(summary["violations"]) == 1


class TestReset:
    """Tests for reset method"""

    @pytest.mark.asyncio
    async def test_reset_clears_state(self, quality_gate_hooks):
        # Populate state
        await quality_gate_hooks.pre_tool_security_check(
            {"tool_name": "Read", "tool_input": {"file_path": "/src/a.py"}},
            "tool_1", HookContext()
        )
        await quality_gate_hooks.pre_tool_security_check(
            {"tool_name": "Read", "tool_input": {"file_path": "/.env"}},
            "tool_2", HookContext()
        )

        # Verify state is populated
        assert len(quality_gate_hooks._tool_executions) == 1
        assert len(quality_gate_hooks._security_violations) == 1

        # Reset
        quality_gate_hooks.reset()

        # Verify cleared
        assert quality_gate_hooks._tool_executions == []
        assert quality_gate_hooks._blocked_operations == []
        assert quality_gate_hooks._files_modified == []
        assert quality_gate_hooks._security_violations == []


class TestCreatePreflightHook:
    """Tests for create_preflight_hook factory"""

    @pytest.mark.asyncio
    async def test_all_checks_pass(self):
        def always_allow(data: Dict[str, Any]) -> bool:
            return True

        hook = create_preflight_hook([always_allow, always_allow])
        result = await hook({"tool_name": "Read"}, "tool_1", HookContext())
        assert result == {}

    @pytest.mark.asyncio
    async def test_one_check_fails(self):
        def always_allow(data: Dict[str, Any]) -> bool:
            return True

        def always_deny(data: Dict[str, Any]) -> bool:
            return False

        hook = create_preflight_hook([always_allow, always_deny])
        result = await hook({"tool_name": "Read"}, "tool_1", HookContext())
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_custom_check_logic(self):
        def only_allow_read(data: Dict[str, Any]) -> bool:
            return data.get("tool_name") == "Read"

        hook = create_preflight_hook([only_allow_read])

        # Should allow Read
        result = await hook({"tool_name": "Read"}, "tool_1", HookContext())
        assert result == {}

        # Should deny Write
        result = await hook({"tool_name": "Write"}, "tool_2", HookContext())
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


class TestCreateAuditHook:
    """Tests for create_audit_hook factory"""

    @pytest.mark.asyncio
    async def test_default_logging(self):
        hook = create_audit_hook()
        result = await hook({"tool_name": "Read"}, "tool_1", HookContext())
        assert result == {}  # Audit hooks always return empty dict

    @pytest.mark.asyncio
    async def test_custom_log_function(self):
        logged_messages = []

        def custom_log(msg: str):
            logged_messages.append(msg)

        hook = create_audit_hook(log_func=custom_log)
        await hook({"tool_name": "Write"}, "tool_1", HookContext())

        assert len(logged_messages) == 1
        assert "Write" in logged_messages[0]
        assert "AUDIT" in logged_messages[0]


class TestCreateSecurityHook:
    """Tests for create_security_hook factory"""

    @pytest.mark.asyncio
    async def test_default_protected_paths(self):
        hook = create_security_hook()

        # Should block .env
        result = await hook(
            {"tool_name": "Read", "tool_input": {"file_path": "/.env"}},
            "tool_1", HookContext()
        )
        assert "hookSpecificOutput" in result

        # Should allow normal files
        result = await hook(
            {"tool_name": "Read", "tool_input": {"file_path": "/src/main.py"}},
            "tool_2", HookContext()
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_custom_protected_paths(self):
        hook = create_security_hook(protected_paths=[".secret", "private.key"])

        # Should block custom paths
        result = await hook(
            {"tool_name": "Read", "tool_input": {"file_path": "/.secret"}},
            "tool_1", HookContext()
        )
        assert "hookSpecificOutput" in result

        # Should allow .env (not in custom list)
        result = await hook(
            {"tool_name": "Read", "tool_input": {"file_path": "/.env"}},
            "tool_2", HookContext()
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_default_dangerous_commands(self):
        hook = create_security_hook()

        # Should block rm -rf /
        result = await hook(
            {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}},
            "tool_1", HookContext()
        )
        assert "hookSpecificOutput" in result

        # Should allow safe commands
        result = await hook(
            {"tool_name": "Bash", "tool_input": {"command": "ls -la"}},
            "tool_2", HookContext()
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_custom_dangerous_commands(self):
        hook = create_security_hook(dangerous_commands=["drop database"])

        # Should block custom command
        result = await hook(
            {"tool_name": "Bash", "tool_input": {"command": "drop database users"}},
            "tool_1", HookContext()
        )
        assert "hookSpecificOutput" in result

        # Should allow rm -rf (not in custom list)
        result = await hook(
            {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}},
            "tool_2", HookContext()
        )
        assert result == {}
