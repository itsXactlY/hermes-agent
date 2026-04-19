"""Neural Memory tools for semantic memory storage and retrieval.

Registers four tools for the neural memory system:

  neural_remember  — Store a memory (with conflict detection)
  neural_recall    — Search memories by semantic similarity  
  neural_think     — Spreading activation from a memory
  neural_graph     — View knowledge graph statistics

The neural memory provider is loaded via the plugin system and
accessed through the MemoryManager.
"""

import json
import logging
from typing import Dict, Any

from tools.registry import registry, tool_error

logger = logging.getLogger(__name__)

# ── Module-level state ──

_neural_provider = None  # NeuralMemoryProvider instance


def set_neural_provider(provider) -> None:
    """Set the neural memory provider instance.
    
    Called by the MemoryManager when neural provider is loaded.
    """
    global _neural_provider
    _neural_provider = provider


def clear_neural_provider() -> None:
    """Clear the neural provider reference."""
    global _neural_provider
    _neural_provider = None


def _check_neural_available() -> bool:
    """Check if neural memory is available."""
    if _neural_provider is not None:
        return _neural_provider.is_available()
    
    # Try to load it
    try:
        from plugins.memory import load_memory_provider
        provider = load_memory_provider("neural")
        if provider and provider.is_available():
            set_neural_provider(provider)
            return True
    except Exception:
        pass
    return False


# ── Tool schemas ──

_NEURAL_REMEMBER_SCHEMA = {
    "name": "neural_remember",
    "description": (
        "Store a memory in the neural memory system. "
        "Memories are embedded and auto-connected to similar memories. "
        "Use this for facts, user preferences, decisions, and important context. "
        "Automatically detects and updates conflicting memories."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The memory content to store.",
            },
            "label": {
                "type": "string",
                "description": "Short label for the memory (optional, auto-generated from content if omitted).",
            },
        },
        "required": ["content"],
    },
}

_NEURAL_RECALL_SCHEMA = {
    "name": "neural_recall",
    "description": (
        "Search neural memory using semantic similarity. "
        "Returns memories ranked by relevance with connection info. "
        "Use this to recall past conversations, facts, or user preferences."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to search for.",
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (default: 5).",
            },
        },
        "required": ["query"],
    },
}

_NEURAL_THINK_SCHEMA = {
    "name": "neural_think",
    "description": (
        "Spreading activation from a memory — explore connected ideas. "
        "Returns memories activated by traversing the knowledge graph from a starting point. "
        "Use to find related context that isn't directly similar."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "memory_id": {
                "type": "integer",
                "description": "Starting memory ID.",
            },
            "depth": {
                "type": "integer",
                "description": "Activation depth (default: 3).",
            },
        },
        "required": ["memory_id"],
    },
}

_NEURAL_GRAPH_SCHEMA = {
    "name": "neural_graph",
    "description": (
        "Get knowledge graph statistics and top connections. "
        "Use to understand the structure of stored memories."
    ),
    "parameters": {"type": "object", "properties": {}, "required": []},
}


# ── Tool handlers ──

def _handle_neural_remember(args: Dict[str, Any], **kwargs) -> str:
    """Handle neural_remember tool call."""
    if not _neural_provider:
        return tool_error("Neural memory provider not available")
    
    try:
        return _neural_provider.handle_tool_call("neural_remember", args)
    except Exception as e:
        return tool_error(f"neural_remember failed: {e}")


def _handle_neural_recall(args: Dict[str, Any], **kwargs) -> str:
    """Handle neural_recall tool call."""
    if not _neural_provider:
        return tool_error("Neural memory provider not available")
    
    try:
        return _neural_provider.handle_tool_call("neural_recall", args)
    except Exception as e:
        return tool_error(f"neural_recall failed: {e}")


def _handle_neural_think(args: Dict[str, Any], **kwargs) -> str:
    """Handle neural_think tool call."""
    if not _neural_provider:
        return tool_error("Neural memory provider not available")
    
    try:
        return _neural_provider.handle_tool_call("neural_think", args)
    except Exception as e:
        return tool_error(f"neural_think failed: {e}")


def _handle_neural_graph(args: Dict[str, Any], **kwargs) -> str:
    """Handle neural_graph tool call."""
    if not _neural_provider:
        return tool_error("Neural memory provider not available")
    
    try:
        return _neural_provider.handle_tool_call("neural_graph", args)
    except Exception as e:
        return tool_error(f"neural_graph failed: {e}")


# ── Register tools ──

registry.register(
    name="neural_remember",
    toolset="memory",
    schema=_NEURAL_REMEMBER_SCHEMA,
    handler=_handle_neural_remember,
    check_fn=_check_neural_available,
    description="Store a memory in neural memory system with conflict detection",
    emoji="🧠",
)

registry.register(
    name="neural_recall",
    toolset="memory",
    schema=_NEURAL_RECALL_SCHEMA,
    handler=_handle_neural_recall,
    check_fn=_check_neural_available,
    description="Search memories by semantic similarity",
    emoji="🔍",
)

registry.register(
    name="neural_think",
    toolset="memory",
    schema=_NEURAL_THINK_SCHEMA,
    handler=_handle_neural_think,
    check_fn=_check_neural_available,
    description="Explore connected ideas via spreading activation",
    emoji="💡",
)

registry.register(
    name="neural_graph",
    toolset="memory",
    schema=_NEURAL_GRAPH_SCHEMA,
    handler=_handle_neural_graph,
    check_fn=_check_neural_available,
    description="View knowledge graph statistics",
    emoji="📊",
)
