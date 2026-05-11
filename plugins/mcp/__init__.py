"""Generic MCP (Model Context Protocol) client utilities for Hermes.

This package contains transport-level helpers — it does NOT itself register
a memory provider.  See ``plugins.memory.mcp`` for the memory provider that
wraps :class:`MCPClient` and routes the four ``neural_*`` tools through it.
"""

from .client import MCPClient

__all__ = ["MCPClient"]
