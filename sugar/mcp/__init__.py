"""
Sugar MCP Server

Model Context Protocol server for Sugar, enabling integration with:
- GitHub Copilot Custom Agents
- Other MCP-compatible clients
"""

from .server import SugarMCPServer, create_server

__all__ = ["SugarMCPServer", "create_server"]
