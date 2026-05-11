"""MCP-bridged memory provider.

This provider satisfies the same :class:`MemoryProvider` contract as
``plugins.memory.mazemaker`` but routes the four ``mazemaker_*`` tools through
the dual-transport MCP server in ``~/projects/mazemaker-mcp/``
(commit ``245e83f``+, branch ``feat/mcp-dual-listener``).

Why this exists
---------------
The legacy ``mazemaker`` provider loads ``Mazemaker`` directly in-process,
which doubles model load + dream-engine + embed-server connections every
time another agent (IDE plugin, second hermes shell, …) attaches.
Routing through the MCP socket makes a single long-lived ``Mazemaker``
the source of truth and lets every attached agent share it.

Config (in ``~/.hermes/config.yaml``)::

    memory:
      provider: mcp
      mcp:
        socket_path: ~/.mazemaker/mcp.sock     # default
        spawn_fallback: true                       # default
        request_timeout: 30.0                      # seconds

Transport semantics are handled inside :class:`plugins.mcp.MCPClient` —
this module is a thin adapter from the hermes ``MemoryProvider`` ABC to
``client.call_tool``.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.memory_provider import MemoryProvider
from plugins.mcp import MCPClient
from plugins.mcp.client import MCPClientError
from tools.registry import tool_error

logger = logging.getLogger(__name__)


# Public schema names this provider exposes to the model. Mirrors the
# mazemaker-mcp server's own ``tools/list`` (``mazemaker_*``) — the
# legacy in-process plugin used ``mazemaker_*`` names, so callers that
# went through that path continue to work via the alias map below.
MAZEMAKER_REMEMBER_SCHEMA: Dict[str, Any] = {
    "name": "mazemaker_remember",
    "description": (
        "Store a fact in persistent semantic memory (routed via MCP). "
        "Content is embedded and auto-linked to similar memories. Use for "
        "user preferences, decisions, fixes, paths and other durable "
        "context the user expects you to recall later."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "The durable fact to remember."},
            "label":   {"type": "string", "description": "Stable topic slug (e.g. 'pref:shell')."},
        },
        "required": ["content"],
    },
}

MAZEMAKER_RECALL_SCHEMA: Dict[str, Any] = {
    "name": "mazemaker_recall",
    "description": (
        "Search persistent semantic memory by meaning. Returns top-k stored "
        "memories ranked by similarity. Always call before answering when "
        "the user references prior context, files, preferences, or past "
        "decisions."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for."},
            "limit": {"type": "integer", "description": "Max results (default 5)."},
        },
        "required": ["query"],
    },
}

MAZEMAKER_THINK_SCHEMA: Dict[str, Any] = {
    "name": "mazemaker_think",
    "description": (
        "Spreading-activation graph traversal from a memory id. After a "
        "neural_recall hit, call this to surface adjacent memories the "
        "direct query would not have returned."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "memory_id": {"type": "integer", "description": "Starting memory id."},
            "depth":     {"type": "integer", "description": "Traversal depth 1-5 (default 3)."},
        },
        "required": ["memory_id"],
    },
}

MAZEMAKER_GRAPH_SCHEMA: Dict[str, Any] = {
    "name": "mazemaker_graph",
    "description": (
        "Knowledge-graph overview: total memories, connection count and top "
        "weighted edges. Use for meta questions about the memory store."
    ),
    "parameters": {"type": "object", "properties": {}, "required": []},
}

ALL_TOOL_SCHEMAS: List[Dict[str, Any]] = [
    MAZEMAKER_REMEMBER_SCHEMA,
    MAZEMAKER_RECALL_SCHEMA,
    MAZEMAKER_THINK_SCHEMA,
    MAZEMAKER_GRAPH_SCHEMA,
]


# Tool aliases (mazemaker_* -> canonical names)
# Keeps ``tools/mazemaker_tools.py`` (which dispatches under ``mazemaker_*``)
# working without changes elsewhere.
_TOOL_ALIASES: Dict[str, str] = {
    "mazemaker_remember": "mazemaker_remember",
    "mazemaker_recall":   "mazemaker_recall",
    "mazemaker_think":    "mazemaker_think",
    "mazemaker_graph":    "mazemaker_graph",
}

# Tools the MCP server actually accepts. Anything outside this set comes
# back as an MCP error which we surface verbatim to the model.
_VALID_TOOLS = frozenset({s["name"] for s in ALL_TOOL_SCHEMAS})


def _read_yaml_config() -> Dict[str, Any]:
    """Best-effort load of ``~/.hermes/config.yaml`` ``memory.mcp`` section.

    Returns an empty dict if the file or the section is missing — the
    provider falls back to defaults baked into :class:`MCPClient`.
    """
    home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    cfg_path = home / "config.yaml"
    if not cfg_path.exists():
        return {}
    try:
        import yaml  # type: ignore[import]

        with cfg_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception as exc:  # pragma: no cover — config errors fall back to defaults
        logger.debug("MCP provider could not read %s: %s", cfg_path, exc)
        return {}
    mem = data.get("memory") or {}
    return mem.get("mcp") or {}


class MCPMemoryProvider(MemoryProvider):
    """:class:`MemoryProvider` shim that delegates to an :class:`MCPClient`."""

    def __init__(self) -> None:
        self._client: Optional[MCPClient] = None
        self._config: Dict[str, Any] = {}
        self._session_id: str = ""

    @property
    def name(self) -> str:
        return "mcp"

    # -- availability ---------------------------------------------------

    def is_available(self) -> bool:
        """The MCP provider is available whenever either transport CAN work.

        We DON'T open a connection here (this is called during startup
        before user intent is clear and would stall hermes for the cold
        socket path). Instead we check the cheap predicates:

          * Socket file exists, or
          * Fallback command points at a readable mcp_local.py.
        """
        cfg = _read_yaml_config()
        sock = os.path.expanduser(
            cfg.get("socket_path") or str(Path.home() / ".mazemaker" / "mcp.sock")
        )
        if Path(sock).exists():
            return True
        # If spawn_fallback is disabled, only the socket path counts.
        if cfg.get("spawn_fallback") is False:
            return False
        fallback = cfg.get("spawn_fallback_cmd")
        if fallback:
            argv = fallback if isinstance(fallback, list) else [str(fallback)]
            target = os.path.expanduser(str(argv[-1]))
        else:
            target = str(Path.home() / "projects" / "mazemaker-mcp" / "mcp_local.py")
        return Path(target).exists()

    # -- lifecycle ------------------------------------------------------

    def initialize(self, session_id: str, **kwargs: Any) -> None:
        """Open the MCP transport. Idempotent."""
        self._session_id = session_id
        self._config = _read_yaml_config()

        if self._client is not None:
            return

        sock_path = os.path.expanduser(
            self._config.get("socket_path")
            or str(Path.home() / ".mazemaker" / "mcp.sock")
        )
        spawn_fallback = self._config.get("spawn_fallback", True)
        fallback_cmd = self._config.get("spawn_fallback_cmd") if spawn_fallback else None
        request_timeout = float(self._config.get("request_timeout", 30.0))

        try:
            self._client = MCPClient(
                socket_path=sock_path,
                spawn_fallback_cmd=fallback_cmd,
                request_timeout=request_timeout,
            )
            self._client.initialize()
            logger.info(
                "MCP memory provider connected via %s (sock=%s)",
                self._client.transport,
                sock_path,
            )
        except Exception as exc:
            logger.warning("MCP memory provider init failed: %s", exc)
            self._client = None

    def shutdown(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    # -- per-turn absorption -------------------------------------------

    def absorb_message(self, role: str, content: str, **kwargs: Any) -> None:
        """Save every user/assistant message back to mazemaker as a
        durable auto-memory. Fires per turn from MemoryManager.absorb_message.

        Architecture:
          - Symmetric with mazemaker_recall: hermes already RECALLS from
            mazemaker every turn; this closes the loop so it also REMEMBERS
            every turn. No more silent forgetting.
          - Background-dispatched: the MCP remember call is sub-second on
            small DBs but can spike to several seconds on large ones (embed
            + auto-connect). We don't want to block hermes between turns.
            Thread-per-absorb is fine — message volume is low (≤2/turn).
          - Idempotent labels: `auto:hermes:<sid8>:t<N>:<role-initial>`.
            Re-runs against the same session+turn no-op via the engine's
            label-equality dedup. Long messages get sliced into ≤28k-char
            chunks so bge-m3's 8192-token window doesn't silently truncate.
        """
        if self._client is None or not content:
            return
        text = content.strip()
        if len(text) < 30:
            return  # skip noise (single tokens, "ok", etc.)

        # Per-instance turn counter — survives across multiple absorbs in
        # one session, resets when a new session re-initialises this
        # provider. Sufficient for unique labels.
        self._turn_counter = getattr(self, "_turn_counter", 0) + 1
        n = self._turn_counter
        sid = (self._session_id or "unknown")[:18]
        role_initial = (role or "?")[:1]

        # Slice into bge-m3-sized chunks to avoid silent truncation. 28k
        # chars ≈ 8000 tokens; matches the bridge/ingest-everything-gpu.py
        # convention so historical bulk-imports and live absorbs share
        # the same chunking semantic.
        CHUNK = 28_000
        chunks = [text[i:i+CHUNK] for i in range(0, len(text), CHUNK)] or [text]

        # Paragraph-level granular saves: salient facts in a turn (an
        # address, a date, a name) end up averaged into the per-turn
        # embedding and become hard to retrieve later. Splitting on
        # blank lines and saving each paragraph as its OWN memory means
        # each fact gets its own embedding + FTS5 row → recall on
        # "tankstellen Greifswalder Chaussee" surfaces the paragraph
        # that mentions the address, not the whole turn.
        # Heuristic for paragraph-rows: keep paragraphs ≥40 chars (most
        # natural-language sentences are 50-150 chars). Skip per-para
        # rows entirely for one-block turns where the whole-turn row
        # already captures the same content.
        MIN_PARA_CHARS = 40
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= MIN_PARA_CHARS]
        if len(paragraphs) < 2:
            paragraphs = []  # don't duplicate single-block turns

        client = self._client  # capture — survives provider shutdown race
        sid_ref = self._session_id or "unknown"

        def _save_all() -> None:
            # 1) Full turn (rolled-up context — keeps "what was discussed")
            for ci, chunk in enumerate(chunks):
                label = f"auto:hermes:{sid}:t{n}:{role_initial}"
                if len(chunks) > 1:
                    label += f":c{ci}"
                content_with_meta = (
                    f"role: {role}\n"
                    f"session: {sid_ref}\n"
                    f"turn: {n}\n"
                    + (f"chunk: {ci+1}/{len(chunks)}\n" if len(chunks) > 1 else "")
                    + "\n" + chunk
                )
                try:
                    client.call_tool("mazemaker_remember", {
                        "label": label,
                        "content": content_with_meta,
                    })
                except Exception as exc:
                    logger.debug("absorb_message remember(%s) failed: %s", label, exc)
                    return  # backend down — skip rest

            # 2) Per-paragraph rows (granular facts — keeps "where the address is")
            for pi, para in enumerate(paragraphs):
                label = f"auto:hermes:{sid}:t{n}:{role_initial}:p{pi}"
                content_with_meta = (
                    f"role: {role}\n"
                    f"session: {sid_ref}\n"
                    f"turn: {n}\n"
                    f"paragraph: {pi+1}/{len(paragraphs)}\n"
                    "\n" + para
                )
                try:
                    client.call_tool("mazemaker_remember", {
                        "label": label,
                        "content": content_with_meta,
                    })
                except Exception as exc:
                    logger.debug("absorb_message paragraph(%s) failed: %s", label, exc)
                    return

        try:
            threading.Thread(
                target=_save_all,
                daemon=True,
                name=f"mzm-absorb-{role_initial}{n}",
            ).start()
        except Exception as exc:
            logger.debug("absorb_message dispatch failed: %s", exc)

    # -- tool surface ---------------------------------------------------

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return ALL_TOOL_SCHEMAS

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs: Any) -> str:
        """Route a tool call through the MCP server.

        Accepts both the canonical ``mazemaker_*`` names (matching the MCP
        server's ``tools/list`` and ``tools/mazemaker_tools.py``) and the
        legacy ``neural_*`` aliases some callers still use.
        """
        if self._client is None:
            return tool_error("MCP memory provider not initialized")

        canonical = _TOOL_ALIASES.get(tool_name, tool_name)
        if canonical not in _VALID_TOOLS:
            return tool_error(f"Unknown tool: {tool_name}")

        try:
            envelope = self._client.call_tool(canonical, args or {})
        except MCPClientError as exc:
            return tool_error(f"MCP {canonical} failed: {exc}")
        except Exception as exc:  # pragma: no cover — defensive
            return tool_error(f"MCP {canonical} crashed: {exc}")

        return _unwrap_envelope(canonical, envelope)

    # -- system prompt --------------------------------------------------

    def system_prompt_block(self) -> str:
        """Brief notice that recall is wired through the shared MCP daemon."""
        if self._client is None:
            return ""
        transport = self._client.transport or "?"
        return (
            "# Mazemaker (MCP) — persistent semantic memory\n"
            "Four tools — mazemaker_remember / mazemaker_recall / mazemaker_think / "
            "mazemaker_graph — route through the shared mazemaker-mcp "
            f"daemon (transport: {transport}). Use them whenever the user "
            "references prior context or states a durable fact."
        )

    # -- config schema --------------------------------------------------

    def get_config_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "socket_path",
                "description": "Unix domain socket path used by mcp_local.py",
                "required": False,
                "default": str(Path.home() / ".mazemaker" / "mcp.sock"),
            },
            {
                "key": "spawn_fallback",
                "description": "Spawn mcp_local.py over stdio if the socket is unreachable",
                "required": False,
                "default": True,
            },
            {
                "key": "request_timeout",
                "description": "Seconds to wait for a single tool call to return",
                "required": False,
                "default": 30.0,
            },
        ]


def _unwrap_envelope(tool_name: str, envelope: Any) -> str:
    """Convert an MCP ``tools/call`` envelope into a hermes tool-result string.

    The mazemaker-mcp server returns::

        {"content": [{"type": "text", "text": "<json blob>"}], "isError": false}

    Hermes tool handlers contract is "return a JSON string", so we extract
    the inner text.  Errors come back as ``isError: true`` — we surface them
    via ``tool_error`` so the model gets a clean diagnostic.
    """
    if envelope is None:
        return tool_error(f"{tool_name}: empty MCP response")
    if not isinstance(envelope, dict):
        return json.dumps(envelope, ensure_ascii=False)
    if envelope.get("isError"):
        # Pull text out of the content list for the diagnostic.
        text = ""
        for item in envelope.get("content") or []:
            if isinstance(item, dict) and item.get("type") == "text":
                text = str(item.get("text") or "")
                if text:
                    break
        return tool_error(text or f"{tool_name} returned an error envelope")
    content = envelope.get("content") or []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            return str(item.get("text") or "")
    # No text item — return the envelope verbatim so the model can still see it.
    return json.dumps(envelope, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Plugin entry point — invoked by ``plugins.memory.load_memory_provider``.
# ---------------------------------------------------------------------------


def register(ctx: Any) -> None:
    ctx.register_memory_provider(MCPMemoryProvider())
