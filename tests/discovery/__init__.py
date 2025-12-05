"""Tests for the sugar.discovery module - Work Discovery Sources.

This package contains tests for Sugar's discovery layer, which identifies potential
work items from various sources for autonomous processing.

Test Modules
------------
test_github_watcher.py
    Comprehensive tests for GitHub issue and PR discovery, including:

    - **Initialization**: Configuration validation, authentication method selection
      (GH CLI vs PyGithub), and auto-detection of available auth methods

    - **Issue Discovery**: Both GH CLI and PyGithub backends, label filtering
      (wildcard, specific labels, unlabeled), result limiting, and error handling

    - **Work Item Creation**: Type mapping (bug→bug_fix, enhancement→feature, etc.),
      priority calculation based on labels (critical, urgent), and filtering
      options (only_unassigned)

    - **GitHub Interactions**: Comment creation, issue assignment, issue closing
      with completion comments, and pull request creation

    - **Health Checks**: Authentication status, API rate limits (PyGithub),
      and graceful error handling

Related Modules
---------------
- ``sugar.discovery.github_watcher``: The GitHubWatcher component being tested
- ``sugar.discovery.error_monitor``: Error log monitoring (tests pending)
- ``sugar.discovery.code_quality``: Code quality scanning (tests pending)
- ``sugar.discovery.test_coverage``: Test coverage analysis (tests pending)

See Also
--------
- ``sugar.discovery``: Main discovery module documentation
- ``tests/``: Main test suite documentation
"""
