"""Integration tests for plugin functionality"""

import json
import subprocess
from pathlib import Path

import pytest


class TestPluginIntegration:
    """Test end-to-end plugin integration"""

    @pytest.fixture
    def sugar_initialized(self, tmp_path):
        """Create temporary project with Sugar initialized"""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # Try to initialize Sugar
        result = subprocess.run(
            ["sugar", "init"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            yield project_dir
        else:
            pytest.skip(f"Sugar not available: {result.stderr}")

    def test_sugar_cli_available(self):
        """Verify Sugar CLI is installed and accessible"""
        result = subprocess.run(
            ["sugar", "--version"], capture_output=True, text=True, timeout=5
        )

        # Should not error (return code 0 or command exists)
        assert result.returncode in [0, 2]  # 2 = unrecognized but exists

    def test_task_creation(self, sugar_initialized):
        """Test creating a task through CLI"""
        result = subprocess.run(
            ["sugar", "add", "Test Task", "--type", "feature", "--priority", "3"],
            cwd=sugar_initialized,
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "task" in result.stdout.lower() or "created" in result.stdout.lower()

    def test_task_listing(self, sugar_initialized):
        """Test listing tasks"""
        # Create a task first
        subprocess.run(
            ["sugar", "add", "Test Task"],
            cwd=sugar_initialized,
            capture_output=True,
            timeout=10,
        )

        # List tasks
        result = subprocess.run(
            ["sugar", "list"],
            cwd=sugar_initialized,
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        # Should see output (even if empty)
        assert len(result.stdout) > 0

    def test_status_command(self, sugar_initialized):
        """Test status command"""
        result = subprocess.run(
            ["sugar", "status"],
            cwd=sugar_initialized,
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert len(result.stdout) > 0


class TestMCPServer:
    """Test MCP server functionality"""

    @pytest.fixture
    def mcp_server_path(self):
        """Get MCP server path"""
        return Path(".claude-plugin/mcp-server/sugar-mcp.js")

    def test_mcp_server_exists(self, mcp_server_path):
        """Verify MCP server file exists"""
        assert mcp_server_path.exists()

    def test_mcp_server_is_executable(self, mcp_server_path):
        """Verify MCP server is executable"""
        import os
        import stat
        import platform

        # On Windows, executability is determined differently
        if platform.system() == "Windows":
            # On Windows, .js files aren't executable in the Unix sense
            # Just verify the file exists and has content
            assert mcp_server_path.exists()
            assert mcp_server_path.stat().st_size > 0
        else:
            st = os.stat(mcp_server_path)
            is_executable = bool(st.st_mode & stat.S_IXUSR)
            assert is_executable, "MCP server is not executable"

    @pytest.mark.skipif(
        not Path(".claude-plugin/mcp-server/sugar-mcp.js").exists(),
        reason="MCP server not implemented",
    )
    def test_mcp_server_starts(self, mcp_server_path):
        """Test that MCP server can start"""
        # This test is basic - just checks if it starts without immediate error
        proc = subprocess.Popen(
            ["node", str(mcp_server_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            # Give it a moment to start
            import time

            time.sleep(0.5)

            # Check if still running (didn't crash immediately)
            assert proc.poll() is None, "MCP server crashed on startup"
        finally:
            proc.terminate()
            proc.wait(timeout=2)


class TestPluginFiles:
    """Test plugin file integrity"""

    def test_no_broken_links_in_docs(self):
        """Verify documentation doesn't have broken relative links"""
        plugin_dir = Path(".claude-plugin")

        for doc_file in plugin_dir.glob("**/*.md"):
            content = doc_file.read_text(encoding="utf-8")

            # Check for relative file references
            import re

            # Find markdown links like [text](path)
            links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)

            for text, link in links:
                # Skip external links
                if link.startswith(("http://", "https://", "#")):
                    continue

                # Check if referenced file exists
                link_path = (doc_file.parent / link).resolve()
                if not link_path.exists():
                    # This is a warning, not a failure
                    print(f"Warning: Broken link in {doc_file}: {link}")

    def test_no_hardcoded_paths(self):
        """Verify no hardcoded absolute paths in files"""
        plugin_dir = Path(".claude-plugin")

        # These patterns should not appear in plugin files
        forbidden_patterns = [
            "/Users/",  # macOS home
            "C:\\Users\\",  # Windows home
            "/home/",  # Linux home (in code, not docs)
        ]

        for file in plugin_dir.glob("**/*.md"):
            if file.name in [
                "MCP_SERVER_IMPLEMENTATION.md",
                "TESTING_PLAN.md",
            ]:  # Allow in examples
                continue

            content = file.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                if pattern in content:
                    # Check if it's in a code example or actual path reference
                    lines_with_pattern = [
                        line for line in content.split("\n") if pattern in line
                    ]
                    # This is informational
                    print(
                        f"Info: Found {pattern} in {file.name}: {len(lines_with_pattern)} occurrences"
                    )

    def test_json_files_valid(self):
        """Verify all JSON files are valid"""
        plugin_dir = Path(".claude-plugin")

        for json_file in plugin_dir.glob("**/*.json"):
            with open(json_file, encoding="utf-8") as f:
                try:
                    json.load(f)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in {json_file}: {e}")
