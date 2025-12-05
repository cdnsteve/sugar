"""Configuration templates and examples for Sugar.

This module contains template configuration files and examples that users can
reference when setting up their Sugar autonomous development environment.

Template Files:
    sugar.yaml: The primary configuration template demonstrating all available
        settings for Sugar, including:
        - Core loop settings (interval, concurrency, dry-run mode)
        - Claude Code CLI integration (command path, timeout, agents)
        - Work discovery modules (error logs, GitHub, code quality, test coverage)
        - Storage configuration (database path, backup interval)
        - Safety settings (retry limits, excluded paths)
        - Logging configuration (level, output file)

Usage:
    Users should copy the template files to their project's `.sugar/` directory
    and customize them for their specific needs:

    .. code-block:: bash

        # Create the .sugar directory
        mkdir -p .sugar

        # Copy and customize the configuration
        cp path/to/sugar/config/sugar.yaml .sugar/config.yaml

        # Edit to match your environment
        # - Set the Claude CLI path
        # - Configure discovery modules
        # - Adjust timing and concurrency settings

Configuration Sections:
    The sugar.yaml template is organized into the following sections:

    **sugar.loop_interval**: Time in seconds between discovery cycles (default: 300)

    **sugar.claude**: Claude Code CLI integration settings
        - command: Path to the Claude CLI executable
        - timeout: Maximum execution time per task
        - use_structured_requests: Enable JSON-based communication
        - agent_selection: Map work types to specific Claude agents

    **sugar.discovery**: Work discovery module configuration
        - error_logs: Monitor log directories for errors
        - github: GitHub issue integration (requires setup)
        - code_quality: Static code analysis settings
        - test_coverage: Test coverage gap detection

    **sugar.storage**: Database and persistence settings
        - database: Path to the SQLite database file
        - backup_interval: Automatic backup frequency

    **sugar.safety**: Safety constraints for autonomous operation
        - max_retries: Retry limit before marking work as failed
        - excluded_paths: System paths to never modify

    **sugar.logging**: Logging configuration
        - level: Log verbosity (DEBUG, INFO, WARNING, ERROR)
        - file: Log output file path

See Also:
    - AGENTS.md: Instructions for AI agents working with Sugar
    - docs/configuration.md: Detailed configuration documentation
    - sugar/main.py: Main entry point that loads configuration

Note:
    This is a template directory. The actual runtime configuration is loaded
    from the `.sugar/config.yaml` file in your project root, not from this
    location directly.
"""
