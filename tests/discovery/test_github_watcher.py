"""
Tests for GitHubWatcher - GitHub issue and PR discovery

Tests cover:
- Initialization with various configurations
- Authentication method selection (GH CLI vs PyGithub)
- Issue discovery from both backends
- Label filtering modes
- Work item creation and type mapping
- GitHub interaction methods (comment, assign, close, PR creation)
- Health check functionality
"""

import pytest
import pytest_asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import subprocess


class TestGitHubWatcherInitialization:
    """Test GitHubWatcher initialization and configuration"""

    def test_disabled_when_enabled_is_false(self):
        """Watcher should be disabled when enabled=False in config"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": False, "repo": "owner/repo"}
        watcher = GitHubWatcher(config)

        assert watcher.enabled is False

    def test_disabled_when_repo_not_configured(self):
        """Watcher should be disabled when repo is not configured"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=False):
            with patch.object(GitHubWatcher, "_init_pygithub", return_value=False):
                config = {"enabled": True, "repo": ""}
                watcher = GitHubWatcher(config)

                assert watcher.enabled is False

    def test_gh_cli_auth_method_selected_when_available(self):
        """Should use GH CLI when auth_method=gh_cli and CLI is available"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            watcher = GitHubWatcher(config)

            assert watcher.enabled is True
            assert watcher.gh_cli_available is True

    def test_disabled_when_gh_cli_specified_but_unavailable(self):
        """Should disable when gh_cli auth specified but CLI not available"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=False):
            watcher = GitHubWatcher(config)

            assert watcher.enabled is False

    def test_token_auth_method_with_pygithub(self):
        """Should use PyGithub when auth_method=token"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {
            "enabled": True,
            "repo": "owner/repo",
            "auth_method": "token",
            "token": "test_token",
        }

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=False):
            with patch.object(GitHubWatcher, "_init_pygithub", return_value=True):
                watcher = GitHubWatcher(config)

                assert watcher.enabled is True
                assert watcher.pygithub_available is True

    def test_auto_auth_method_tries_gh_cli_first(self):
        """Auto auth should try GH CLI first, then PyGithub"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": True, "repo": "owner/repo", "auth_method": "auto"}

        with patch.object(
            GitHubWatcher, "_check_gh_cli", return_value=True
        ) as mock_cli:
            with patch.object(
                GitHubWatcher, "_init_pygithub", return_value=False
            ) as mock_pygithub:
                watcher = GitHubWatcher(config)

                mock_cli.assert_called_once()
                # PyGithub should not be tried when GH CLI is available
                mock_pygithub.assert_not_called()
                assert watcher.gh_cli_available is True

    def test_auto_auth_method_falls_back_to_pygithub(self):
        """Auto auth should fall back to PyGithub when GH CLI unavailable"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": True, "repo": "owner/repo", "auth_method": "auto"}

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=False):
            with patch.object(GitHubWatcher, "_init_pygithub", return_value=True):
                watcher = GitHubWatcher(config)

                assert watcher.gh_cli_available is False
                assert watcher.pygithub_available is True
                assert watcher.enabled is True

    def test_disabled_when_no_auth_method_available(self):
        """Should disable when neither auth method is available in auto mode"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": True, "repo": "owner/repo", "auth_method": "auto"}

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=False):
            with patch.object(GitHubWatcher, "_init_pygithub", return_value=False):
                watcher = GitHubWatcher(config)

                assert watcher.enabled is False


class TestGitHubCLIChecks:
    """Test GitHub CLI availability and authentication checks"""

    def test_check_gh_cli_returns_true_when_available_and_authenticated(self):
        """Should return True when GH CLI is available and authenticated"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}

        with patch("subprocess.run") as mock_run:
            # First call: version check, Second call: auth status
            mock_run.side_effect = [
                Mock(returncode=0),  # version check
                Mock(returncode=0),  # auth status
            ]

            watcher = GitHubWatcher(config)
            assert watcher.gh_cli_available is True

    def test_check_gh_cli_returns_false_when_not_installed(self):
        """Should return False when GH CLI is not installed"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1)  # CLI not found

            watcher = GitHubWatcher(config)
            assert watcher.gh_cli_available is False

    def test_check_gh_cli_returns_false_when_not_authenticated(self):
        """Should return False when GH CLI is not authenticated"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0),  # version check passes
                Mock(returncode=1),  # auth status fails
            ]

            watcher = GitHubWatcher(config)
            assert watcher.gh_cli_available is False

    def test_check_gh_cli_handles_timeout(self):
        """Should handle subprocess timeout gracefully"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="gh", timeout=10)

            watcher = GitHubWatcher(config)
            assert watcher.gh_cli_available is False

    def test_check_gh_cli_handles_file_not_found(self):
        """Should handle FileNotFoundError gracefully"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("gh not found")

            watcher = GitHubWatcher(config)
            assert watcher.gh_cli_available is False

    def test_custom_gh_command_is_used(self):
        """Should use custom gh command from config"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {
            "enabled": True,
            "repo": "owner/repo",
            "auth_method": "gh_cli",
            "gh_cli": {"command": "/custom/path/gh"},
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            watcher = GitHubWatcher(config)

            # Verify custom command was used
            calls = mock_run.call_args_list
            assert calls[0][0][0][0] == "/custom/path/gh"


class TestPyGithubInitialization:
    """Test PyGithub initialization"""

    def test_init_pygithub_returns_false_when_not_available(self):
        """Should return False when PyGithub is not available"""
        from sugar.discovery import github_watcher

        # Temporarily set PYGITHUB_AVAILABLE to False
        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = False

        try:
            config = {
                "enabled": True,
                "repo": "owner/repo",
                "auth_method": "token",
                "token": "test_token",
            }

            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                watcher = github_watcher.GitHubWatcher(config)
                assert watcher.pygithub_available is False
        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    def test_init_pygithub_returns_false_without_token(self):
        """Should return False when no token is configured"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            config = {"enabled": True, "repo": "owner/repo", "auth_method": "token"}

            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.dict("os.environ", {}, clear=True):
                    watcher = github_watcher.GitHubWatcher(config)
                    assert watcher.pygithub_available is False
        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value


class TestLabelFiltering:
    """Test label filtering logic"""

    def setup_method(self):
        """Create a watcher instance for testing"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            self.watcher = GitHubWatcher(
                {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}
            )

    def test_empty_config_includes_all_issues(self):
        """Empty label list should include all issues"""
        assert (
            self.watcher._should_include_issue_by_labels(
                issue_labels=["bug", "urgent"],
                config_labels=[],
                original_config=[],
            )
            is True
        )

        assert (
            self.watcher._should_include_issue_by_labels(
                issue_labels=[],
                config_labels=[],
                original_config=[],
            )
            is True
        )

    def test_wildcard_includes_labeled_issues_only(self):
        """Wildcard ['*'] should include only issues with labels"""
        assert (
            self.watcher._should_include_issue_by_labels(
                issue_labels=["bug"],
                config_labels=["*"],
                original_config=["*"],
            )
            is True
        )

        assert (
            self.watcher._should_include_issue_by_labels(
                issue_labels=[],
                config_labels=["*"],
                original_config=["*"],
            )
            is False
        )

    def test_unlabeled_config_includes_only_unlabeled_issues(self):
        """['unlabeled'] should include only issues without labels"""
        assert (
            self.watcher._should_include_issue_by_labels(
                issue_labels=[],
                config_labels=["unlabeled"],
                original_config=["unlabeled"],
            )
            is True
        )

        assert (
            self.watcher._should_include_issue_by_labels(
                issue_labels=["bug"],
                config_labels=["unlabeled"],
                original_config=["unlabeled"],
            )
            is False
        )

    def test_specific_labels_filter_correctly(self):
        """Specific labels should use OR logic (any match includes)"""
        # Issue has matching label
        assert (
            self.watcher._should_include_issue_by_labels(
                issue_labels=["bug", "urgent"],
                config_labels=["bug", "enhancement"],
                original_config=["bug", "enhancement"],
            )
            is True
        )

        # Issue has no matching labels
        assert (
            self.watcher._should_include_issue_by_labels(
                issue_labels=["documentation"],
                config_labels=["bug", "enhancement"],
                original_config=["bug", "enhancement"],
            )
            is False
        )

    def test_label_comparison_with_lowercase_conversion(self):
        """Labels should be converted to lowercase before comparison by the caller

        Note: The _should_include_issue_by_labels method expects labels to already
        be lowercased. The lowercasing happens in the calling methods
        (_discover_issues_gh_cli and _discover_issues_pygithub).
        """
        # Simulate what the calling code does - lowercase before calling
        issue_labels_original = ["BUG"]  # uppercase from GitHub API
        config_labels_original = ["bug"]  # lowercase from config

        # This is how the actual implementation works - caller lowercases first
        issue_labels = [label.lower() for label in issue_labels_original]
        config_labels = [label.lower() for label in config_labels_original]

        assert (
            self.watcher._should_include_issue_by_labels(
                issue_labels=issue_labels,
                config_labels=config_labels,
                original_config=config_labels_original,
            )
            is True
        )


class TestWorkItemCreation:
    """Test work item creation from issue data"""

    def setup_method(self):
        """Create a watcher instance for testing"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            self.watcher = GitHubWatcher(
                {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}
            )

    def test_bug_label_creates_bug_fix_work_type(self):
        """Bug labels should create bug_fix work type with priority 4"""
        issue = {
            "number": 1,
            "title": "Test Bug",
            "body": "Bug description",
            "labels": [{"name": "bug"}],
            "assignees": [],
            "comments": 0,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
            "url": "https://github.com/owner/repo/issues/1",
        }

        work_item = self.watcher._create_work_item_from_issue_data(issue)

        assert work_item["type"] == "bug_fix"
        assert work_item["priority"] == 4

    def test_enhancement_label_creates_feature_work_type(self):
        """Enhancement labels should create feature work type"""
        issue = {
            "number": 2,
            "title": "Test Feature",
            "body": "Feature description",
            "labels": [{"name": "enhancement"}],
            "assignees": [],
            "comments": 0,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
            "url": "https://github.com/owner/repo/issues/2",
        }

        work_item = self.watcher._create_work_item_from_issue_data(issue)

        assert work_item["type"] == "feature"
        assert work_item["priority"] == 3

    def test_documentation_label_creates_documentation_work_type(self):
        """Documentation labels should create documentation work type"""
        issue = {
            "number": 3,
            "title": "Update docs",
            "body": "Doc description",
            "labels": [{"name": "documentation"}],
            "assignees": [],
            "comments": 0,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
            "url": "https://github.com/owner/repo/issues/3",
        }

        work_item = self.watcher._create_work_item_from_issue_data(issue)

        assert work_item["type"] == "documentation"
        assert work_item["priority"] == 2

    def test_test_label_creates_test_work_type(self):
        """Test labels should create test work type"""
        issue = {
            "number": 4,
            "title": "Add tests",
            "body": "Test description",
            "labels": [{"name": "test"}],
            "assignees": [],
            "comments": 0,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
            "url": "https://github.com/owner/repo/issues/4",
        }

        work_item = self.watcher._create_work_item_from_issue_data(issue)

        assert work_item["type"] == "test"
        assert work_item["priority"] == 3

    def test_urgent_label_increases_priority(self):
        """Urgent/critical labels should increase priority"""
        issue = {
            "number": 5,
            "title": "Critical Bug",
            "body": "Critical bug description",
            "labels": [{"name": "bug"}, {"name": "critical"}],
            "assignees": [],
            "comments": 0,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
            "url": "https://github.com/owner/repo/issues/5",
        }

        work_item = self.watcher._create_work_item_from_issue_data(issue)

        # Bug priority is 4, critical adds 1, so should be 5
        assert work_item["priority"] == 5

    def test_priority_capped_at_5(self):
        """Priority should not exceed 5"""
        issue = {
            "number": 6,
            "title": "Super Critical Bug",
            "body": "Very critical bug",
            "labels": [{"name": "bug"}, {"name": "critical"}, {"name": "urgent"}],
            "assignees": [],
            "comments": 0,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
            "url": "https://github.com/owner/repo/issues/6",
        }

        work_item = self.watcher._create_work_item_from_issue_data(issue)

        assert work_item["priority"] == 5

    def test_only_unassigned_filter(self):
        """Should skip assigned issues when only_unassigned is True"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            watcher = GitHubWatcher(
                {
                    "enabled": True,
                    "repo": "owner/repo",
                    "auth_method": "gh_cli",
                    "only_unassigned": True,
                }
            )

        issue = {
            "number": 7,
            "title": "Assigned Issue",
            "body": "Issue description",
            "labels": [{"name": "bug"}],
            "assignees": [{"login": "someuser"}],
            "comments": 0,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
            "url": "https://github.com/owner/repo/issues/7",
        }

        work_item = watcher._create_work_item_from_issue_data(issue)

        assert work_item is None

    def test_work_item_structure(self):
        """Work item should have correct structure"""
        issue = {
            "number": 8,
            "title": "Test Issue",
            "body": "Issue body",
            "labels": [{"name": "bug"}],
            "assignees": [{"login": "testuser"}],
            "comments": 5,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
            "url": "https://github.com/owner/repo/issues/8",
        }

        work_item = self.watcher._create_work_item_from_issue_data(issue)

        assert "type" in work_item
        assert "title" in work_item
        assert "description" in work_item
        assert "priority" in work_item
        assert "source" in work_item
        assert work_item["source"] == "github_watcher"
        assert "source_file" in work_item
        assert "context" in work_item
        assert "github_issue" in work_item["context"]
        assert work_item["context"]["github_issue"]["number"] == 8


class TestDescriptionFormatting:
    """Test issue description formatting"""

    def setup_method(self):
        """Create a watcher instance for testing"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            self.watcher = GitHubWatcher(
                {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}
            )

    def test_format_issue_description_includes_all_parts(self):
        """Description should include issue number, URL, dates, labels, assignees"""
        issue = {
            "number": 1,
            "title": "Test Issue",
            "body": "This is the issue body",
            "labels": [{"name": "bug"}, {"name": "urgent"}],
            "assignees": [{"login": "user1"}, {"login": "user2"}],
            "comments": 3,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
            "url": "https://github.com/owner/repo/issues/1",
        }

        description = self.watcher._format_issue_description(issue)

        assert "**GitHub Issue #1**" in description
        assert "https://github.com/owner/repo/issues/1" in description
        assert "2024-01-01T00:00:00Z" in description
        assert "Comments: 3" in description
        assert "bug" in description
        assert "urgent" in description
        assert "user1" in description
        assert "user2" in description
        assert "This is the issue body" in description

    def test_format_issue_description_handles_missing_body(self):
        """Should handle issues without a body"""
        issue = {
            "number": 2,
            "title": "No Body Issue",
            "body": None,
            "labels": [],
            "assignees": [],
            "comments": 0,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
            "url": "https://github.com/owner/repo/issues/2",
        }

        description = self.watcher._format_issue_description(issue)

        assert "No description provided." in description


class TestDiscovery:
    """Test issue discovery functionality"""

    @pytest.mark.asyncio
    async def test_discover_returns_empty_when_disabled(self):
        """Discover should return empty list when watcher is disabled"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": False}
        watcher = GitHubWatcher(config)

        result = await watcher.discover()

        assert result == []

    @pytest.mark.asyncio
    async def test_discover_uses_gh_cli_when_available(self):
        """Should use GH CLI discovery when available"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            watcher = GitHubWatcher(
                {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}
            )

        mock_work_items = [{"type": "bug_fix", "title": "Test"}]

        with patch.object(
            watcher, "_discover_issues_gh_cli", return_value=mock_work_items
        ) as mock_discover:
            result = await watcher.discover()

            mock_discover.assert_called_once()
            assert result == mock_work_items

    @pytest.mark.asyncio
    async def test_discover_handles_exceptions_gracefully(self):
        """Should handle exceptions and return empty list"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            watcher = GitHubWatcher(
                {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}
            )

        with patch.object(
            watcher, "_discover_issues_gh_cli", side_effect=Exception("Test error")
        ):
            result = await watcher.discover()

            assert result == []


class TestGitHubCLIDiscovery:
    """Test GitHub CLI-based issue discovery"""

    @pytest.mark.asyncio
    async def test_discover_issues_gh_cli_parses_response(self):
        """Should parse GH CLI response and create work items"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            watcher = GitHubWatcher(
                {
                    "enabled": True,
                    "repo": "owner/repo",
                    "auth_method": "gh_cli",
                    "issue_labels": ["bug"],
                }
            )

        mock_issues = [
            {
                "number": 1,
                "title": "Bug Issue",
                "body": "Bug description",
                "labels": [{"name": "bug"}],
                "assignees": [],
                "comments": 0,
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-01T00:00:00Z",
                "url": "https://github.com/owner/repo/issues/1",
            }
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=json.dumps(mock_issues), stderr=""
            )

            result = await watcher._discover_issues_gh_cli()

            assert len(result) == 1
            assert result[0]["type"] == "bug_fix"

    @pytest.mark.asyncio
    async def test_discover_issues_gh_cli_handles_command_failure(self):
        """Should handle GH CLI command failure"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            watcher = GitHubWatcher(
                {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}
            )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error")

            result = await watcher._discover_issues_gh_cli()

            assert result == []

    @pytest.mark.asyncio
    async def test_discover_issues_gh_cli_limits_results(self):
        """Should limit results to 10 issues after filtering"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            watcher = GitHubWatcher(
                {
                    "enabled": True,
                    "repo": "owner/repo",
                    "auth_method": "gh_cli",
                    "issue_labels": [],  # Include all
                }
            )

        # Create 15 mock issues
        mock_issues = [
            {
                "number": i,
                "title": f"Issue {i}",
                "body": f"Description {i}",
                "labels": [],
                "assignees": [],
                "comments": 0,
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-01T00:00:00Z",
                "url": f"https://github.com/owner/repo/issues/{i}",
            }
            for i in range(1, 16)
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=json.dumps(mock_issues), stderr=""
            )

            result = await watcher._discover_issues_gh_cli()

            assert len(result) == 10


class TestHealthCheck:
    """Test health check functionality"""

    @pytest.mark.asyncio
    async def test_health_check_returns_disabled_status(self):
        """Should return disabled status when watcher is disabled"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": False}
        watcher = GitHubWatcher(config)

        result = await watcher.health_check()

        assert result["enabled"] is False
        assert "reason" in result

    @pytest.mark.asyncio
    async def test_health_check_gh_cli_returns_auth_status(self):
        """Should return authentication status for GH CLI"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            watcher = GitHubWatcher(
                {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}
            )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = await watcher.health_check()

            assert result["enabled"] is True
            assert result["method"] == "GitHub CLI"
            assert result["authenticated"] is True
            assert result["repository"] == "owner/repo"

    @pytest.mark.asyncio
    async def test_health_check_handles_errors(self):
        """Should handle errors gracefully"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            watcher = GitHubWatcher(
                {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}
            )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Test error")

            result = await watcher.health_check()

            assert result["enabled"] is True
            assert "error" in result


class TestGitHubInteractions:
    """Test GitHub interaction methods (comment, assign, close, PR)"""

    @pytest.mark.asyncio
    async def test_comment_on_issue_returns_false_when_disabled(self):
        """Should return False when watcher is disabled"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": False}
        watcher = GitHubWatcher(config)

        result = await watcher.comment_on_issue(1, "Test comment")

        assert result is False

    @pytest.mark.asyncio
    async def test_comment_via_gh_cli_success(self):
        """Should successfully comment using GH CLI"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            watcher = GitHubWatcher(
                {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}
            )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = await watcher._comment_via_gh_cli(1, "Test comment")

            assert result is True
            # Verify correct command was called
            call_args = mock_run.call_args[0][0]
            assert "issue" in call_args
            assert "comment" in call_args

    @pytest.mark.asyncio
    async def test_assign_issue_returns_false_when_disabled(self):
        """Should return False when watcher is disabled"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": False}
        watcher = GitHubWatcher(config)

        result = await watcher.assign_issue(1)

        assert result is False

    @pytest.mark.asyncio
    async def test_assign_via_gh_cli_success(self):
        """Should successfully assign issue using GH CLI"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            watcher = GitHubWatcher(
                {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}
            )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = await watcher._assign_via_gh_cli(1)

            assert result is True
            call_args = mock_run.call_args[0][0]
            assert "--add-assignee" in call_args
            assert "@me" in call_args

    @pytest.mark.asyncio
    async def test_close_issue_returns_false_when_disabled(self):
        """Should return False when watcher is disabled"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": False}
        watcher = GitHubWatcher(config)

        result = await watcher.close_issue(1)

        assert result is False

    @pytest.mark.asyncio
    async def test_close_issue_via_gh_cli_with_comment(self):
        """Should close issue with optional completion comment"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            watcher = GitHubWatcher(
                {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}
            )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = await watcher._close_issue_via_gh_cli(1, "Completed!")

            assert result is True
            # Should have called subprocess twice (comment + close)
            assert mock_run.call_count == 2

    @pytest.mark.asyncio
    async def test_create_pull_request_returns_none_when_disabled(self):
        """Should return None when watcher is disabled"""
        from sugar.discovery.github_watcher import GitHubWatcher

        config = {"enabled": False}
        watcher = GitHubWatcher(config)

        result = await watcher.create_pull_request("branch", "title", "body")

        assert result is None

    @pytest.mark.asyncio
    async def test_create_pr_via_gh_cli_success(self):
        """Should successfully create PR using GH CLI"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            watcher = GitHubWatcher(
                {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}
            )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="https://github.com/owner/repo/pull/1"
            )

            result = await watcher._create_pr_via_gh_cli(
                "feature-branch", "PR Title", "PR Body", "main"
            )

            assert result == "https://github.com/owner/repo/pull/1"
            call_args = mock_run.call_args[0][0]
            assert "pr" in call_args
            assert "create" in call_args

    @pytest.mark.asyncio
    async def test_create_pr_via_gh_cli_failure(self):
        """Should return None on PR creation failure"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            watcher = GitHubWatcher(
                {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}
            )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="PR creation failed")

            result = await watcher._create_pr_via_gh_cli(
                "feature-branch", "PR Title", "PR Body", "main"
            )

            assert result is None


class TestPyGithubDiscovery:
    """Test PyGithub-based issue discovery"""

    @pytest.mark.asyncio
    async def test_discover_uses_pygithub_when_gh_cli_unavailable(self):
        """Should use PyGithub discovery when GH CLI is not available"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=False):
            with patch.object(GitHubWatcher, "_init_pygithub", return_value=True):
                watcher = GitHubWatcher(
                    {"enabled": True, "repo": "owner/repo", "auth_method": "auto"}
                )
                watcher.pygithub_available = True

        mock_work_items = [{"type": "bug_fix", "title": "Test"}]

        with patch.object(
            watcher, "_discover_issues_pygithub", return_value=mock_work_items
        ) as mock_discover:
            result = await watcher.discover()

            mock_discover.assert_called_once()
            assert result == mock_work_items

    @pytest.mark.asyncio
    async def test_discover_issues_pygithub_filters_pull_requests(self):
        """Should skip pull requests in issue list"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                            "issue_labels": ["bug"],
                        }
                    )
                    watcher.pygithub_available = True

            # Mock repo and issues
            mock_issue = MagicMock()
            mock_issue.pull_request = True  # This is a PR
            mock_issue.number = 1

            mock_repo = MagicMock()
            mock_repo.get_issues.return_value = [mock_issue]

            mock_github = MagicMock()
            mock_github.get_repo.return_value = mock_repo

            watcher.github = mock_github

            result = await watcher._discover_issues_pygithub()

            # Should return empty - the only "issue" was actually a PR
            assert result == []

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_discover_issues_pygithub_processes_real_issues(self):
        """Should process real issues and create work items"""
        from sugar.discovery import github_watcher
        from datetime import datetime

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                            "issue_labels": ["bug"],
                        }
                    )
                    watcher.pygithub_available = True

            # Mock label
            mock_label = MagicMock()
            mock_label.name = "bug"

            # Mock issue (not a PR)
            mock_issue = MagicMock()
            mock_issue.pull_request = None  # Not a PR
            mock_issue.number = 1
            mock_issue.title = "Test Bug"
            mock_issue.body = "Bug description"
            mock_issue.labels = [mock_label]
            mock_issue.assignee = None
            mock_issue.comments = 0
            mock_issue.created_at = datetime(2024, 1, 1)
            mock_issue.updated_at = datetime(2024, 1, 2)
            mock_issue.html_url = "https://github.com/owner/repo/issues/1"

            mock_repo = MagicMock()
            mock_repo.get_issues.return_value = [mock_issue]

            mock_github = MagicMock()
            mock_github.get_repo.return_value = mock_repo

            watcher.github = mock_github

            result = await watcher._discover_issues_pygithub()

            assert len(result) == 1
            assert result[0]["type"] == "bug_fix"

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_discover_issues_pygithub_limits_to_10_results(self):
        """Should limit results to 10 issues"""
        from sugar.discovery import github_watcher
        from datetime import datetime

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                            "issue_labels": [],  # Include all
                        }
                    )
                    watcher.pygithub_available = True

            # Create 15 mock issues
            mock_issues = []
            for i in range(15):
                mock_issue = MagicMock()
                mock_issue.pull_request = None
                mock_issue.number = i
                mock_issue.title = f"Issue {i}"
                mock_issue.body = f"Description {i}"
                mock_issue.labels = []
                mock_issue.assignee = None
                mock_issue.comments = 0
                mock_issue.created_at = datetime(2024, 1, 1)
                mock_issue.updated_at = datetime(2024, 1, 2)
                mock_issue.html_url = f"https://github.com/owner/repo/issues/{i}"
                mock_issues.append(mock_issue)

            mock_repo = MagicMock()
            mock_repo.get_issues.return_value = mock_issues

            mock_github = MagicMock()
            mock_github.get_repo.return_value = mock_repo

            watcher.github = mock_github

            result = await watcher._discover_issues_pygithub()

            assert len(result) == 10

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_discover_issues_pygithub_handles_api_error(self):
        """Should handle PyGithub API errors gracefully"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True

            mock_github = MagicMock()
            mock_github.get_repo.side_effect = Exception("API error")

            watcher.github = mock_github

            result = await watcher._discover_issues_pygithub()

            assert result == []

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value


class TestPyGithubHealthCheck:
    """Test PyGithub health check functionality"""

    @pytest.mark.asyncio
    async def test_health_check_pygithub_returns_rate_limit_info(self):
        """Should return rate limit info for PyGithub"""
        from sugar.discovery import github_watcher
        from datetime import datetime

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True
                    watcher.gh_cli_available = False

            # Mock rate limit response
            mock_rate_limit = MagicMock()
            mock_rate_limit.core.remaining = 4500
            mock_rate_limit.core.limit = 5000
            mock_rate_limit.core.reset = datetime(2024, 1, 1, 12, 0, 0)

            mock_github = MagicMock()
            mock_github.get_rate_limit.return_value = mock_rate_limit

            watcher.github = mock_github

            result = await watcher.health_check()

            assert result["enabled"] is True
            assert result["method"] == "PyGithub"
            assert "api_rate_limit" in result
            assert result["api_rate_limit"]["remaining"] == 4500
            assert result["api_rate_limit"]["limit"] == 5000

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value


class TestPyGithubInteractions:
    """Test PyGithub-based interaction methods"""

    @pytest.mark.asyncio
    async def test_comment_via_pygithub_success(self):
        """Should successfully comment using PyGithub"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True

            mock_issue = MagicMock()
            mock_repo = MagicMock()
            mock_repo.get_issue.return_value = mock_issue

            mock_github = MagicMock()
            mock_github.get_repo.return_value = mock_repo

            watcher.github = mock_github

            result = await watcher._comment_via_pygithub(1, "Test comment")

            assert result is True
            mock_issue.create_comment.assert_called_once_with("Test comment")

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_comment_via_pygithub_failure(self):
        """Should return False on PyGithub comment failure"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True

            mock_github = MagicMock()
            mock_github.get_repo.side_effect = Exception("API error")

            watcher.github = mock_github

            result = await watcher._comment_via_pygithub(1, "Test comment")

            assert result is False

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_assign_via_pygithub_success_adds_new_assignee(self):
        """Should add current user to assignees"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True

            mock_user = MagicMock()
            mock_user.login = "testuser"

            mock_issue = MagicMock()
            mock_issue.assignees = []  # No current assignees

            mock_repo = MagicMock()
            mock_repo.get_issue.return_value = mock_issue

            mock_github = MagicMock()
            mock_github.get_repo.return_value = mock_repo
            mock_github.get_user.return_value = mock_user

            watcher.github = mock_github

            result = await watcher._assign_via_pygithub(1)

            assert result is True
            mock_issue.edit.assert_called_once_with(assignees=["testuser"])

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_assign_via_pygithub_skips_already_assigned(self):
        """Should not re-add user if already assigned"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True

            mock_user = MagicMock()
            mock_user.login = "testuser"

            mock_existing_assignee = MagicMock()
            mock_existing_assignee.login = "testuser"

            mock_issue = MagicMock()
            mock_issue.assignees = [mock_existing_assignee]  # Already assigned

            mock_repo = MagicMock()
            mock_repo.get_issue.return_value = mock_issue

            mock_github = MagicMock()
            mock_github.get_repo.return_value = mock_repo
            mock_github.get_user.return_value = mock_user

            watcher.github = mock_github

            result = await watcher._assign_via_pygithub(1)

            assert result is True
            mock_issue.edit.assert_not_called()  # Should not update

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_assign_via_pygithub_failure(self):
        """Should return False on PyGithub assignment failure"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True

            mock_github = MagicMock()
            mock_github.get_repo.side_effect = Exception("API error")

            watcher.github = mock_github

            result = await watcher._assign_via_pygithub(1)

            assert result is False

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_close_issue_via_pygithub_success(self):
        """Should successfully close issue using PyGithub"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True

            mock_issue = MagicMock()
            mock_repo = MagicMock()
            mock_repo.get_issue.return_value = mock_issue

            mock_github = MagicMock()
            mock_github.get_repo.return_value = mock_repo

            watcher.github = mock_github

            result = await watcher._close_issue_via_pygithub(1)

            assert result is True
            mock_issue.edit.assert_called_once_with(state="closed")

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_close_issue_via_pygithub_with_comment(self):
        """Should add completion comment before closing"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True

            mock_issue = MagicMock()
            mock_repo = MagicMock()
            mock_repo.get_issue.return_value = mock_issue

            mock_github = MagicMock()
            mock_github.get_repo.return_value = mock_repo

            watcher.github = mock_github

            result = await watcher._close_issue_via_pygithub(1, "Completed!")

            assert result is True
            mock_issue.create_comment.assert_called_once_with("Completed!")
            mock_issue.edit.assert_called_once_with(state="closed")

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_close_issue_via_pygithub_continues_on_comment_failure(self):
        """Should continue to close even if comment fails"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True

            mock_issue = MagicMock()
            mock_issue.create_comment.side_effect = Exception("Comment failed")

            mock_repo = MagicMock()
            mock_repo.get_issue.return_value = mock_issue

            mock_github = MagicMock()
            mock_github.get_repo.return_value = mock_repo

            watcher.github = mock_github

            result = await watcher._close_issue_via_pygithub(1, "Completed!")

            assert result is True
            mock_issue.edit.assert_called_once_with(state="closed")

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_close_issue_via_pygithub_failure(self):
        """Should return False on PyGithub close failure"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True

            mock_github = MagicMock()
            mock_github.get_repo.side_effect = Exception("API error")

            watcher.github = mock_github

            result = await watcher._close_issue_via_pygithub(1)

            assert result is False

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_create_pr_via_pygithub_success(self):
        """Should successfully create PR using PyGithub"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True

            mock_pr = MagicMock()
            mock_pr.number = 42
            mock_pr.html_url = "https://github.com/owner/repo/pull/42"

            mock_repo = MagicMock()
            mock_repo.create_pull.return_value = mock_pr

            mock_github = MagicMock()
            mock_github.get_repo.return_value = mock_repo

            watcher.github = mock_github

            result = await watcher._create_pr_via_pygithub(
                "feature-branch", "PR Title", "PR Body", "main"
            )

            assert result == "https://github.com/owner/repo/pull/42"
            mock_repo.create_pull.assert_called_once_with(
                title="PR Title", body="PR Body", head="feature-branch", base="main"
            )

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_create_pr_via_pygithub_failure(self):
        """Should return None on PyGithub PR creation failure"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True

            mock_github = MagicMock()
            mock_github.get_repo.side_effect = Exception("API error")

            watcher.github = mock_github

            result = await watcher._create_pr_via_pygithub(
                "feature-branch", "PR Title", "PR Body", "main"
            )

            assert result is None

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value


class TestInteractionMethodRouting:
    """Test that interaction methods route correctly to GH CLI or PyGithub"""

    @pytest.mark.asyncio
    async def test_comment_routes_to_pygithub_when_cli_unavailable(self):
        """Should route to PyGithub when GH CLI is unavailable"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True
                    watcher.gh_cli_available = False

            with patch.object(
                watcher, "_comment_via_pygithub", return_value=True
            ) as mock_pygithub:
                result = await watcher.comment_on_issue(1, "Test")

                mock_pygithub.assert_called_once()
                assert result is True

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_assign_routes_to_pygithub_when_cli_unavailable(self):
        """Should route to PyGithub when GH CLI is unavailable"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True
                    watcher.gh_cli_available = False

            with patch.object(
                watcher, "_assign_via_pygithub", return_value=True
            ) as mock_pygithub:
                result = await watcher.assign_issue(1)

                mock_pygithub.assert_called_once()
                assert result is True

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_close_routes_to_pygithub_when_cli_unavailable(self):
        """Should route to PyGithub when GH CLI is unavailable"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True
                    watcher.gh_cli_available = False

            with patch.object(
                watcher, "_close_issue_via_pygithub", return_value=True
            ) as mock_pygithub:
                result = await watcher.close_issue(1)

                mock_pygithub.assert_called_once()
                assert result is True

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_create_pr_routes_to_pygithub_when_cli_unavailable(self):
        """Should route to PyGithub when GH CLI is unavailable"""
        from sugar.discovery import github_watcher

        original_value = github_watcher.PYGITHUB_AVAILABLE
        github_watcher.PYGITHUB_AVAILABLE = True

        try:
            with patch.object(
                github_watcher.GitHubWatcher, "_check_gh_cli", return_value=False
            ):
                with patch.object(
                    github_watcher.GitHubWatcher, "_init_pygithub", return_value=True
                ):
                    watcher = github_watcher.GitHubWatcher(
                        {
                            "enabled": True,
                            "repo": "owner/repo",
                            "auth_method": "token",
                            "token": "test_token",
                        }
                    )
                    watcher.pygithub_available = True
                    watcher.gh_cli_available = False

            with patch.object(
                watcher, "_create_pr_via_pygithub", return_value="https://url"
            ) as mock_pygithub:
                result = await watcher.create_pull_request("branch", "title", "body")

                mock_pygithub.assert_called_once()
                assert result == "https://url"

        finally:
            github_watcher.PYGITHUB_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_methods_return_failure_when_no_auth_available(self):
        """Should return failure when neither auth method is available"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=False):
            with patch.object(GitHubWatcher, "_init_pygithub", return_value=False):
                watcher = GitHubWatcher(
                    {"enabled": True, "repo": "owner/repo", "auth_method": "auto"}
                )
                # Force enable to test the methods
                watcher.enabled = True
                watcher.gh_cli_available = False
                watcher.pygithub_available = False

        assert await watcher.comment_on_issue(1, "Test") is False
        assert await watcher.assign_issue(1) is False
        assert await watcher.close_issue(1) is False
        assert await watcher.create_pull_request("branch", "title", "body") is None


class TestLogLabelFilteringMode:
    """Test label filtering mode logging"""

    def setup_method(self):
        """Create a watcher instance for testing"""
        from sugar.discovery.github_watcher import GitHubWatcher

        with patch.object(GitHubWatcher, "_check_gh_cli", return_value=True):
            self.watcher = GitHubWatcher(
                {"enabled": True, "repo": "owner/repo", "auth_method": "gh_cli"}
            )

    def test_log_label_filtering_mode_empty_list(self):
        """Should log 'ALL open issues' for empty config"""
        import logging

        with patch.object(
            logging.getLogger("sugar.discovery.github_watcher"), "debug"
        ) as mock_debug:
            self.watcher._log_label_filtering_mode([])
            # Method should execute without error
            # (debug logging may not be captured depending on log level)

    def test_log_label_filtering_mode_wildcard(self):
        """Should log 'Issues with ANY labels' for wildcard"""
        self.watcher._log_label_filtering_mode(["*"])
        # Method should execute without error

    def test_log_label_filtering_mode_unlabeled(self):
        """Should log 'Only UNLABELED issues' for unlabeled config"""
        self.watcher._log_label_filtering_mode(["unlabeled"])
        # Method should execute without error

    def test_log_label_filtering_mode_specific_labels(self):
        """Should log specific labels"""
        self.watcher._log_label_filtering_mode(["bug", "enhancement"])
        # Method should execute without error
