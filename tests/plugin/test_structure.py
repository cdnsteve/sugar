"""Test plugin structure and manifest validity"""

import json
from pathlib import Path

import pytest


class TestPluginStructure:
    """Test plugin directory structure and files"""

    @pytest.fixture
    def plugin_dir(self):
        """Get plugin directory path"""
        return Path(".claude-plugin")

    def test_plugin_directory_exists(self, plugin_dir):
        """Verify plugin directory exists"""
        assert plugin_dir.exists()
        assert plugin_dir.is_dir()

    def test_plugin_json_exists(self, plugin_dir):
        """Verify plugin.json exists and is valid JSON"""
        manifest_path = plugin_dir / "plugin.json"
        assert manifest_path.exists()

        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        assert isinstance(manifest, dict)

    def test_plugin_manifest_required_fields(self, plugin_dir):
        """Verify plugin manifest has all required fields"""
        with open(plugin_dir / "plugin.json", encoding="utf-8") as f:
            manifest = json.load(f)

        # Required fields
        assert "name" in manifest
        assert "version" in manifest
        assert "description" in manifest
        assert "author" in manifest

        # Verify values
        assert manifest["name"] == "sugar"
        assert manifest["version"] == "2.0.0"
        assert "license" in manifest

    def test_commands_directory_exists(self, plugin_dir):
        """Verify commands directory exists"""
        commands_dir = plugin_dir / "commands"
        assert commands_dir.exists()
        assert commands_dir.is_dir()

    def test_required_commands_exist(self, plugin_dir):
        """Verify all required commands exist"""
        commands_dir = plugin_dir / "commands"
        required_commands = [
            "sugar-task.md",
            "sugar-status.md",
            "sugar-run.md",
            "sugar-review.md",
            "sugar-analyze.md",
        ]

        for command in required_commands:
            command_path = commands_dir / command
            assert command_path.exists(), f"Missing command: {command}"

    def test_agents_directory_exists(self, plugin_dir):
        """Verify agents directory exists"""
        agents_dir = plugin_dir / "agents"
        assert agents_dir.exists()
        assert agents_dir.is_dir()

    def test_required_agents_exist(self, plugin_dir):
        """Verify all required agents exist"""
        agents_dir = plugin_dir / "agents"
        required_agents = [
            "sugar-orchestrator.md",
            "task-planner.md",
            "quality-guardian.md",
        ]

        for agent in required_agents:
            agent_path = agents_dir / agent
            assert agent_path.exists(), f"Missing agent: {agent}"

    def test_hooks_configuration_exists(self, plugin_dir):
        """Verify hooks configuration exists and is valid"""
        hooks_path = plugin_dir / "hooks" / "hooks.json"
        assert hooks_path.exists()

        with open(hooks_path, encoding="utf-8") as f:
            hooks = json.load(f)

        assert "hooks" in hooks
        assert isinstance(hooks["hooks"], list)
        assert len(hooks["hooks"]) > 0

    def test_mcp_configuration_exists(self, plugin_dir):
        """Verify MCP configuration exists"""
        mcp_path = plugin_dir / ".mcp.json"
        assert mcp_path.exists()

        with open(mcp_path) as f:
            mcp_config = json.load(f)

        assert "mcpServers" in mcp_config
        assert "sugar" in mcp_config["mcpServers"]

    def test_mcp_server_exists(self, plugin_dir):
        """Verify MCP server file exists"""
        mcp_server = plugin_dir / "mcp-server" / "sugar-mcp.js"
        assert mcp_server.exists()

    def test_documentation_exists(self, plugin_dir):
        """Verify key documentation files exist"""
        docs = [
            "README.md",
            "IMPLEMENTATION_ROADMAP.md",
            "TESTING_PLAN.md",
            "MARKETPLACE_SUBMISSION.md",
            "MCP_SERVER_IMPLEMENTATION.md",
            "PLUGIN_OVERVIEW.md",
        ]

        for doc in docs:
            doc_path = plugin_dir / doc
            assert doc_path.exists(), f"Missing documentation: {doc}"


class TestCommandStructure:
    """Test command file structure"""

    @pytest.fixture
    def commands_dir(self):
        """Get commands directory"""
        return Path(".claude-plugin/commands")

    def test_all_commands_have_frontmatter(self, commands_dir):
        """Verify all commands have valid frontmatter"""
        for command_file in commands_dir.glob("*.md"):
            content = command_file.read_text(encoding="utf-8")
            assert content.startswith("---"), f"{command_file.name} missing frontmatter"
            assert "name:" in content
            assert "description:" in content

    def test_all_commands_have_usage(self, commands_dir):
        """Verify all commands document usage"""
        for command_file in commands_dir.glob("*.md"):
            content = command_file.read_text(encoding="utf-8")
            assert (
                "usage:" in content.lower() or "## usage" in content.lower()
            ), f"{command_file.name} missing usage documentation"

    def test_all_commands_have_examples(self, commands_dir):
        """Verify all commands include examples"""
        for command_file in commands_dir.glob("*.md"):
            content = command_file.read_text(encoding="utf-8")
            assert (
                "examples:" in content.lower() or "## example" in content.lower()
            ), f"{command_file.name} missing examples"


class TestAgentStructure:
    """Test agent file structure"""

    @pytest.fixture
    def agents_dir(self):
        """Get agents directory"""
        return Path(".claude-plugin/agents")

    def test_all_agents_have_frontmatter(self, agents_dir):
        """Verify all agents have valid frontmatter"""
        for agent_file in agents_dir.glob("*.md"):
            content = agent_file.read_text(encoding="utf-8")
            assert content.startswith("---"), f"{agent_file.name} missing frontmatter"
            assert "name:" in content
            assert "description:" in content

    def test_all_agents_define_expertise(self, agents_dir):
        """Verify all agents define their expertise"""
        for agent_file in agents_dir.glob("*.md"):
            content = agent_file.read_text(encoding="utf-8")
            assert (
                "expertise:" in content.lower() or "## expertise" in content.lower()
            ), f"{agent_file.name} missing expertise definition"


class TestHooksConfiguration:
    """Test hooks configuration"""

    @pytest.fixture
    def hooks_config(self):
        """Load hooks configuration"""
        with open(".claude-plugin/hooks/hooks.json", encoding="utf-8") as f:
            return json.load(f)

    def test_hooks_have_required_fields(self, hooks_config):
        """Verify each hook has required fields"""
        for hook in hooks_config["hooks"]:
            assert "name" in hook, "Hook missing name"
            assert "event" in hook, f"Hook {hook.get('name')} missing event"
            assert "action" in hook, f"Hook {hook.get('name')} missing action"

    def test_hook_events_are_valid(self, hooks_config):
        """Verify hook events are valid Claude Code events"""
        valid_events = [
            "tool-use",
            "session-start",
            "session-end",
            "user-prompt-submit",
            "file-change",
        ]

        for hook in hooks_config["hooks"]:
            assert (
                hook["event"] in valid_events
            ), f"Hook {hook['name']} has invalid event: {hook['event']}"

    def test_hooks_have_descriptions(self, hooks_config):
        """Verify hooks have descriptions"""
        for hook in hooks_config["hooks"]:
            assert "description" in hook, f"Hook {hook['name']} missing description"
            assert (
                len(hook["description"]) > 10
            ), f"Hook {hook['name']} has too short description"
