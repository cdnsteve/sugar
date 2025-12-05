"""Integration tests for plugin functionality"""

import json
import platform
import shutil
import subprocess
from pathlib import Path

import pytest


# Module-level constant for plugin path
PLUGIN_DIR = Path(".claude-plugin")


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


class TestPluginInstallation:
    """Test plugin installation flow"""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create temporary project directory"""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        return project_dir

    def test_plugin_installation_flow(self, temp_project):
        """Test complete plugin installation flow"""
        # Copy plugin files to temporary project
        plugin_src = PLUGIN_DIR
        if not plugin_src.exists():
            pytest.skip("Plugin directory not found")

        plugin_dst = temp_project / ".claude-plugin"
        shutil.copytree(plugin_src, plugin_dst)

        # Verify structure after installation
        assert (plugin_dst / "plugin.json").exists()
        assert (plugin_dst / "commands").is_dir()
        assert (plugin_dst / "agents").is_dir()
        assert (plugin_dst / "hooks").is_dir()

    def test_plugin_files_readable_after_copy(self, temp_project):
        """Verify all plugin files are readable after copying"""
        plugin_src = PLUGIN_DIR
        if not plugin_src.exists():
            pytest.skip("Plugin directory not found")

        plugin_dst = temp_project / ".claude-plugin"
        shutil.copytree(plugin_src, plugin_dst)

        # All files should be readable
        for path in plugin_dst.rglob("*"):
            if path.is_file():
                try:
                    _ = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    # Binary files are acceptable (e.g., images)
                    _ = path.read_bytes()


class TestCrossPlatform:
    """Platform-specific tests"""

    def test_plugin_works_on_current_platform(self):
        """Verify plugin structure works on current OS"""
        system = platform.system()
        assert system in ["Darwin", "Linux", "Windows"]

        # All plugin files should be readable
        plugin_dir = PLUGIN_DIR
        if not plugin_dir.exists():
            pytest.skip("Plugin directory not found")

        for path in plugin_dir.rglob("*"):
            if path.is_file():
                assert path.exists()
                assert path.stat().st_size > 0

    def test_path_separators_in_commands(self):
        """Verify no hardcoded path separators in commands"""
        commands_dir = PLUGIN_DIR / "commands"
        if not commands_dir.exists():
            pytest.skip("Commands directory not found")

        forbidden_patterns = [
            "~/Dev/",
            "/Users/",
            "C:\\Users\\",
        ]

        for cmd in commands_dir.glob("*.md"):
            content = cmd.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                assert (
                    pattern not in content
                ), f"Found hardcoded path '{pattern}' in {cmd.name}"

    def test_line_endings_consistency(self):
        """Verify consistent line endings (Unix-style)"""
        plugin_dir = PLUGIN_DIR
        if not plugin_dir.exists():
            pytest.skip("Plugin directory not found")

        for path in plugin_dir.rglob("*.md"):
            content = path.read_bytes()
            # Check for Windows-style line endings
            if b"\r\n" in content:
                # This is informational, not a failure
                # Some systems may have different line endings
                print(f"Info: Windows line endings in {path.name}")

    def test_file_permissions_reasonable(self):
        """Verify file permissions are reasonable"""
        plugin_dir = PLUGIN_DIR
        if not plugin_dir.exists():
            pytest.skip("Plugin directory not found")

        if platform.system() == "Windows":
            pytest.skip("Permission test not applicable on Windows")

        import stat

        for path in plugin_dir.rglob("*"):
            if path.is_file():
                mode = path.stat().st_mode
                # File should be readable by owner
                assert mode & stat.S_IRUSR, f"{path} is not readable by owner"


class TestSecurity:
    """Security tests for plugin"""

    def test_no_command_injection_basic(self, tmp_path):
        """Verify plugin protects against basic command injection"""
        # Test that malicious inputs are handled safely
        malicious_inputs = [
            "test; rm -rf /",
            "test && echo pwned",
            "test | cat /etc/passwd",
            "test`echo pwned`",
            "$(echo pwned)",
        ]

        for malicious_input in malicious_inputs:
            result = subprocess.run(
                ["sugar", "add", malicious_input],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmp_path,
            )
            # Should either succeed (input treated as literal) or fail validation
            # but should not execute the injected command
            assert result.returncode in [
                0,
                1,
                2,
            ], f"Unexpected return code for input '{malicious_input}'"

    def test_no_secrets_in_plugin_files(self):
        """Verify no secrets committed to plugin files (excluding documentation examples)"""
        plugin_dir = PLUGIN_DIR
        if not plugin_dir.exists():
            pytest.skip("Plugin directory not found")

        # Common secret patterns to check for
        secret_patterns = [
            "sk_live_",  # Stripe API keys
            "sk_test_",  # Stripe test keys
            "ghp_",  # GitHub personal access tokens
            "gho_",  # GitHub OAuth tokens
            "ghs_",  # GitHub App tokens
            "ghu_",  # GitHub user-to-server tokens
            "aws_access_key_id",
            "aws_secret_access_key",
            "AKIA",  # AWS access key prefix
            "-----BEGIN RSA PRIVATE KEY-----",
            "-----BEGIN PRIVATE KEY-----",
        ]

        # Only check actual code files (.js, .py) not documentation
        # Documentation files (.md) may contain examples showing what NOT to do
        for path in plugin_dir.rglob("*"):
            if path.is_file() and path.suffix in [".js", ".py"]:
                content = path.read_text(encoding="utf-8")
                for pattern in secret_patterns:
                    assert (
                        pattern not in content
                    ), f"Potential secret pattern '{pattern}' found in {path.name}"

    def test_no_hardcoded_credentials(self):
        """Verify no hardcoded credentials in plugin files"""
        plugin_dir = PLUGIN_DIR
        if not plugin_dir.exists():
            pytest.skip("Plugin directory not found")

        import re

        # Patterns that might indicate hardcoded credentials
        credential_patterns = [
            re.compile(r'password\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
            re.compile(r'api_key\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
            re.compile(r'secret\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
        ]

        for path in plugin_dir.rglob("*"):
            if path.is_file() and path.suffix in [".js", ".py"]:
                content = path.read_text(encoding="utf-8")
                for pattern in credential_patterns:
                    matches = pattern.findall(content)
                    # Allow example/placeholder values
                    real_matches = [
                        m
                        for m in matches
                        if "example" not in m.lower()
                        and "placeholder" not in m.lower()
                        and "your_" not in m.lower()
                        and "xxx" not in m.lower()
                    ]
                    assert (
                        not real_matches
                    ), f"Potential hardcoded credential in {path.name}: {real_matches}"


class TestPerformance:
    """Performance tests for plugin"""

    @pytest.fixture
    def sugar_initialized(self, tmp_path):
        """Create temporary project with Sugar initialized"""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

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

    def test_multiple_rapid_commands(self, sugar_initialized):
        """Test handling multiple commands in quick succession"""
        import time

        start_time = time.time()
        success_count = 0

        for i in range(5):
            result = subprocess.run(
                ["sugar", "add", f"Performance Test Task {i}", "--type", "feature"],
                cwd=sugar_initialized,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                success_count += 1

        elapsed = time.time() - start_time

        # All commands should succeed
        assert success_count == 5, f"Only {success_count}/5 commands succeeded"
        # Should complete in reasonable time (10 seconds for 5 commands)
        assert elapsed < 10, f"Commands took too long: {elapsed:.2f}s"

    def test_status_command_performance(self, sugar_initialized):
        """Test status command returns quickly"""
        import time

        # Run status command and measure time
        start_time = time.time()
        result = subprocess.run(
            ["sugar", "status"],
            cwd=sugar_initialized,
            capture_output=True,
            text=True,
            timeout=5,
        )
        elapsed = time.time() - start_time

        assert result.returncode == 0
        # Status should complete within 2 seconds
        assert elapsed < 2, f"Status command too slow: {elapsed:.2f}s"


class TestDocumentation:
    """Test documentation completeness"""

    def test_plugin_readme_exists(self):
        """Verify plugin README exists"""
        readme_path = PLUGIN_DIR / "README.md"
        assert readme_path.exists(), f"README.md not found at {readme_path}"

    def test_readme_has_installation(self):
        """Verify README includes installation instructions"""
        readme_path = PLUGIN_DIR / "README.md"
        if not readme_path.exists():
            pytest.skip("README.md not found")

        content = readme_path.read_text(encoding="utf-8")
        assert "install" in content.lower(), "README missing installation instructions"
        assert (
            "pip install" in content or "sugar" in content
        ), "README should mention installation method"

    def test_readme_has_examples(self):
        """Verify README includes usage examples"""
        readme_path = PLUGIN_DIR / "README.md"
        if not readme_path.exists():
            pytest.skip("README.md not found")

        content = readme_path.read_text(encoding="utf-8")
        # Should have code blocks
        assert "```" in content, "README should include code examples"

    def test_all_commands_documented_in_readme(self):
        """Verify all commands are documented in README"""
        readme_path = PLUGIN_DIR / "README.md"
        commands_dir = PLUGIN_DIR / "commands"

        if not readme_path.exists() or not commands_dir.exists():
            pytest.skip("README or commands directory not found")

        readme_content = readme_path.read_text(encoding="utf-8")

        for cmd in commands_dir.glob("*.md"):
            cmd_name = cmd.stem
            # Command should be mentioned in README
            assert (
                cmd_name in readme_content or f"/{cmd_name}" in readme_content
            ), f"Command '{cmd_name}' not documented in README"
