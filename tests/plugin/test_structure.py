"""Test plugin structure and manifest validity"""

import json
from pathlib import Path

import pytest


# Module-level constant for plugin path to avoid hardcoding in multiple places
PLUGIN_DIR = Path(".claude-plugin")


@pytest.fixture(scope="module")
def plugin_dir():
    """Get plugin directory path (module-scoped for performance)"""
    return PLUGIN_DIR


@pytest.fixture(scope="module")
def plugin_manifest(plugin_dir):
    """Load plugin manifest once for all tests that need it"""
    manifest_path = plugin_dir / "plugin.json"
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def commands_dir(plugin_dir):
    """Get commands directory"""
    return plugin_dir / "commands"


@pytest.fixture(scope="module")
def agents_dir(plugin_dir):
    """Get agents directory"""
    return plugin_dir / "agents"


@pytest.fixture(scope="module")
def hooks_config(plugin_dir):
    """Load hooks configuration"""
    hooks_path = plugin_dir / "hooks" / "hooks.json"
    with open(hooks_path, encoding="utf-8") as f:
        return json.load(f)


class TestPluginStructure:
    """Test plugin directory structure and files"""

    def test_plugin_directory_exists(self, plugin_dir):
        """Verify plugin directory exists"""
        assert plugin_dir.exists(), f"Plugin directory not found: {plugin_dir}"
        assert plugin_dir.is_dir(), f"Plugin path is not a directory: {plugin_dir}"

    def test_plugin_json_exists(self, plugin_dir, plugin_manifest):
        """Verify plugin.json exists and is valid JSON"""
        manifest_path = plugin_dir / "plugin.json"
        assert manifest_path.exists(), f"plugin.json not found at {manifest_path}"
        assert isinstance(
            plugin_manifest, dict
        ), "plugin.json should contain a JSON object"

    def test_plugin_manifest_required_fields(self, plugin_manifest):
        """Verify plugin manifest has all required fields"""
        required_fields = ["name", "version", "description", "author", "license"]
        for field in required_fields:
            assert field in plugin_manifest, f"Missing required field: {field}"

        # Verify expected values
        assert (
            plugin_manifest["name"] == "sugar"
        ), f"Expected name 'sugar', got '{plugin_manifest['name']}'"

    def test_plugin_manifest_version_format(self, plugin_manifest):
        """Verify plugin version follows semver format"""
        version = plugin_manifest.get("version", "")
        parts = version.split(".")
        assert len(parts) >= 2, f"Version '{version}' should follow semver format"
        assert all(
            part.isdigit() for part in parts[:3] if part
        ), f"Version parts should be numeric: {version}"

    def test_commands_directory_exists(self, plugin_dir, commands_dir):
        """Verify commands directory exists"""
        assert commands_dir.exists(), f"Commands directory not found: {commands_dir}"
        assert (
            commands_dir.is_dir()
        ), f"Commands path is not a directory: {commands_dir}"

    def test_required_commands_exist(self, commands_dir):
        """Verify all required commands exist"""
        required_commands = [
            "sugar-task.md",
            "sugar-status.md",
            "sugar-run.md",
            "sugar-review.md",
            "sugar-analyze.md",
        ]

        for command in required_commands:
            command_path = commands_dir / command
            assert command_path.exists(), f"Missing required command: {command}"

    def test_agents_directory_exists(self, plugin_dir, agents_dir):
        """Verify agents directory exists"""
        assert agents_dir.exists(), f"Agents directory not found: {agents_dir}"
        assert agents_dir.is_dir(), f"Agents path is not a directory: {agents_dir}"

    def test_required_agents_exist(self, agents_dir):
        """Verify all required agents exist"""
        required_agents = [
            "sugar-orchestrator.md",
            "task-planner.md",
            "quality-guardian.md",
        ]

        for agent in required_agents:
            agent_path = agents_dir / agent
            assert agent_path.exists(), f"Missing required agent: {agent}"

    def test_hooks_configuration_exists(self, plugin_dir, hooks_config):
        """Verify hooks configuration exists and is valid"""
        hooks_path = plugin_dir / "hooks" / "hooks.json"
        assert hooks_path.exists(), f"Hooks configuration not found: {hooks_path}"

        assert "hooks" in hooks_config, "hooks.json missing 'hooks' key"
        assert isinstance(
            hooks_config["hooks"], list
        ), "hooks.json 'hooks' should be a list"
        assert (
            len(hooks_config["hooks"]) > 0
        ), "hooks.json should contain at least one hook"

    def test_mcp_configuration_exists(self, plugin_dir):
        """Verify MCP configuration exists"""
        mcp_path = plugin_dir / ".mcp.json"
        assert mcp_path.exists(), f"MCP configuration not found: {mcp_path}"

        with open(mcp_path, encoding="utf-8") as f:
            mcp_config = json.load(f)

        assert "mcpServers" in mcp_config, "MCP config missing 'mcpServers' key"
        assert (
            "sugar" in mcp_config["mcpServers"]
        ), "MCP config missing 'sugar' server definition"

    def test_mcp_server_exists(self, plugin_dir):
        """Verify MCP server file exists"""
        mcp_server = plugin_dir / "mcp-server" / "sugar-mcp.js"
        assert mcp_server.exists(), f"MCP server file not found: {mcp_server}"

    def test_documentation_exists(self, plugin_dir):
        """Verify key documentation files exist"""
        required_docs = [
            "README.md",
            "IMPLEMENTATION_ROADMAP.md",
            "TESTING_PLAN.md",
            "MARKETPLACE_SUBMISSION.md",
            "MCP_SERVER_IMPLEMENTATION.md",
            "PLUGIN_OVERVIEW.md",
        ]

        for doc in required_docs:
            doc_path = plugin_dir / doc
            assert doc_path.exists(), f"Missing required documentation: {doc}"


class TestCommandStructure:
    """Test command file structure"""

    def test_all_commands_have_frontmatter(self, commands_dir):
        """Verify all commands have valid frontmatter"""
        command_files = list(commands_dir.glob("*.md"))
        assert command_files, f"No command files found in {commands_dir}"

        for command_file in command_files:
            content = command_file.read_text(encoding="utf-8")
            assert content.startswith(
                "---"
            ), f"{command_file.name} missing frontmatter header"
            assert (
                "name:" in content
            ), f"{command_file.name} missing 'name' in frontmatter"
            assert (
                "description:" in content
            ), f"{command_file.name} missing 'description' in frontmatter"

    def test_all_commands_have_usage(self, commands_dir):
        """Verify all commands document usage"""
        for command_file in commands_dir.glob("*.md"):
            content = command_file.read_text(encoding="utf-8")
            content_lower = content.lower()
            has_usage = "usage:" in content_lower or "## usage" in content_lower
            assert has_usage, f"{command_file.name} missing usage documentation"

    def test_all_commands_have_examples(self, commands_dir):
        """Verify all commands include examples"""
        for command_file in commands_dir.glob("*.md"):
            content = command_file.read_text(encoding="utf-8")
            content_lower = content.lower()
            has_examples = "examples:" in content_lower or "## example" in content_lower
            assert has_examples, f"{command_file.name} missing examples"


class TestAgentStructure:
    """Test agent file structure"""

    def test_all_agents_have_frontmatter(self, agents_dir):
        """Verify all agents have valid frontmatter"""
        agent_files = list(agents_dir.glob("*.md"))
        assert agent_files, f"No agent files found in {agents_dir}"

        for agent_file in agent_files:
            content = agent_file.read_text(encoding="utf-8")
            assert content.startswith(
                "---"
            ), f"{agent_file.name} missing frontmatter header"
            assert (
                "name:" in content
            ), f"{agent_file.name} missing 'name' in frontmatter"
            assert (
                "description:" in content
            ), f"{agent_file.name} missing 'description' in frontmatter"

    def test_all_agents_define_expertise(self, agents_dir):
        """Verify all agents define their expertise"""
        for agent_file in agents_dir.glob("*.md"):
            content = agent_file.read_text(encoding="utf-8")
            content_lower = content.lower()
            has_expertise = (
                "expertise:" in content_lower or "## expertise" in content_lower
            )
            assert has_expertise, f"{agent_file.name} missing expertise definition"


class TestHooksConfiguration:
    """Test hooks configuration"""

    def test_hooks_have_required_fields(self, hooks_config):
        """Verify each hook has required fields"""
        required_fields = ["name", "event", "action"]

        for hook in hooks_config["hooks"]:
            hook_name = hook.get("name", "<unnamed>")
            for field in required_fields:
                assert (
                    field in hook
                ), f"Hook '{hook_name}' missing required field: {field}"

    def test_hook_events_are_valid(self, hooks_config):
        """Verify hook events are valid Claude Code events"""
        valid_events = frozenset(
            [
                "tool-use",
                "session-start",
                "session-end",
                "user-prompt-submit",
                "file-change",
            ]
        )

        for hook in hooks_config["hooks"]:
            hook_name = hook.get("name", "<unnamed>")
            event = hook.get("event")
            assert (
                event in valid_events
            ), f"Hook '{hook_name}' has invalid event: {event}. Valid events: {sorted(valid_events)}"

    def test_hooks_have_descriptions(self, hooks_config):
        """Verify hooks have meaningful descriptions"""
        min_description_length = 10

        for hook in hooks_config["hooks"]:
            hook_name = hook.get("name", "<unnamed>")
            assert "description" in hook, f"Hook '{hook_name}' missing description"
            description = hook.get("description", "")
            assert len(description) >= min_description_length, (
                f"Hook '{hook_name}' has too short description "
                f"(min {min_description_length} chars): '{description}'"
            )
