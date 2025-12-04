"""
Tests for ToolOrchestrator initialization.

Tests the initialization and configuration of the ToolOrchestrator class.
"""

from pathlib import Path

import pytest

from sugar.discovery.external_tool_config import ExternalToolConfig
from sugar.discovery.orchestrator import (
    DEFAULT_TIMEOUT_SECONDS,
    ToolOrchestrator,
)


class TestToolOrchestratorInit:
    """Tests for ToolOrchestrator initialization"""

    def test_init_with_tools(self, temp_dir):
        """Test orchestrator initialization with tools"""
        tools = [
            ExternalToolConfig(name="eslint", command="npx eslint ."),
            ExternalToolConfig(name="ruff", command="ruff check ."),
        ]
        orchestrator = ToolOrchestrator(tools, working_dir=temp_dir)
        assert len(orchestrator.external_tools) == 2
        assert orchestrator.working_dir == temp_dir
        assert orchestrator.default_timeout == DEFAULT_TIMEOUT_SECONDS

    def test_init_without_tools(self, temp_dir):
        """Test orchestrator initialization without tools"""
        orchestrator = ToolOrchestrator([], working_dir=temp_dir)
        assert len(orchestrator.external_tools) == 0

    def test_init_with_custom_timeout(self, temp_dir):
        """Test orchestrator with custom timeout"""
        orchestrator = ToolOrchestrator([], working_dir=temp_dir, default_timeout=60)
        assert orchestrator.default_timeout == 60

    def test_init_uses_cwd_when_no_working_dir(self):
        """Test orchestrator uses cwd when working_dir not specified"""
        orchestrator = ToolOrchestrator([])
        assert orchestrator.working_dir == Path.cwd()

    def test_get_tool_names(self, temp_dir):
        """Test get_tool_names method"""
        tools = [
            ExternalToolConfig(name="eslint", command="npx eslint ."),
            ExternalToolConfig(name="ruff", command="ruff check ."),
        ]
        orchestrator = ToolOrchestrator(tools, working_dir=temp_dir)
        names = orchestrator.get_tool_names()
        assert names == ["eslint", "ruff"]

    def test_get_tool_count(self, temp_dir):
        """Test get_tool_count method"""
        tools = [
            ExternalToolConfig(name="eslint", command="npx eslint ."),
            ExternalToolConfig(name="ruff", command="ruff check ."),
        ]
        orchestrator = ToolOrchestrator(tools, working_dir=temp_dir)
        assert orchestrator.get_tool_count() == 2
