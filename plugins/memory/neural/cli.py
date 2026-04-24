"""CLI commands for Neural Memory provider.

Handles: hermes neural status | remember | recall | think | graph
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from plugins.memory import load_memory_provider
from hermes_constants import get_hermes_home


def _load_provider():
    """Load and return the neural memory provider, or None."""
    try:
        from hermes_cli.config import load_config
        cfg = load_config()
        mem_cfg = cfg.get("memory", {})
        if mem_cfg.get("provider") != "neural":
            return None
        return load_memory_provider("neural")
    except Exception:
        return None


def _ensure_provider():
    """Load provider, exit with error if not available."""
    prov = _load_provider()
    if prov is None:
        print("Neural memory provider is not active.")
        print("  Set memory.provider=neural in ~/.hermes/config.yaml to enable.")
        print("  Or: hermes config set memory.provider neural")
        sys.exit(1)
    return prov


# ────────────────────────────────────────────────────────────────────────────
# Commands
# ────────────────────────────────────────────────────────────────────────────

def cmd_status(args) -> None:
    """Show neural memory status."""
    prov = _load_provider()

    if prov is None:
        print("Neural memory provider is not active (memory.provider != 'neural')")
        print("\nTo enable:")
        print("  hermes config set memory.provider neural")
        return

    prov.initialize(session_id="neural-cli-status", platform="cli",
                     hermes_home=str(Path("~/.hermes").expanduser()),
                     agent_context="cli")

    db_path = "?"
    size_mb = "?"
    try:
        db_path = Path(prov._config.get("db_path", "~/.neural_memory/memory.db"))
        db_path = db_path.expanduser()
        exists = db_path.exists()
        size = db_path.stat().st_size if exists else 0
        size_mb = f"{size / (1024 * 1024):.2f}"
    except Exception:
        pass

    mem_count = "?"
    conn_count = "?"
    try:
        stats = prov._memory.stats() if hasattr(prov._memory, 'stats') else {}
        mem_count = stats.get('memories', stats.get('memory_count', '?'))
        conn_count = stats.get('connections', stats.get('connection_count', '?'))
    except Exception:
        pass

    print(f"  DB path:    {db_path}")
    print(f"  DB size:    {size_mb} MB")
    print(f"  Memories:   {mem_count}")
    print(f"  Connections:{conn_count}")
    print()

    # Embedding backend
    try:
        backend = prov._config.get("embedding_backend", "auto")
        print(f"  Embedding:  {backend}")
    except Exception:
        pass

    # Dream engine status
    try:
        if prov._dream and prov._dream.is_running():
            print(f"  Dream:      running (pid={prov._dream._pid})")
        else:
            print(f"  Dream:      stopped")
    except Exception:
        pass

    print()


def _cli_init(prov):
    """Initialize a provider for CLI use."""
    prov.initialize(
        session_id="neural-cli",
        platform="cli",
        hermes_home=str(Path("~/.hermes").expanduser()),
        agent_context="cli",
    )


def cmd_remember(args) -> None:
    """Store a memory directly from CLI."""
    prov = _ensure_provider()
    _cli_init(prov)

    content = " ".join(args.content) if isinstance(args.content, list) else args.content
    if not content:
        print("Usage: hermes neural remember <content>")
        print("  Stores a memory in the neural memory system.")
        print()
        print("Examples:")
        print("  hermes neural remember User prefers dark mode")
        print("  hermes neural remember --label=user_prefs 'Dark mode preferred'")
        sys.exit(1)

    try:
        label = args.label if hasattr(args, "label") and args.label else None
        result = prov._handle_remember({"content": content, "label": label})
        parsed = json.loads(result)
        if "error" in parsed:
            print(f"Error: {parsed['error']}")
            sys.exit(1)
        else:
            memory_id = parsed.get("id", "?")
            print(f"Stored (id={memory_id})")
    except Exception as e:
        print(f"Failed: {e}")
        sys.exit(1)


def cmd_recall(args) -> None:
    """Search memories from CLI."""
    prov = _ensure_provider()
    _cli_init(prov)

    query = " ".join(args.query) if isinstance(args.query, list) else args.query
    if not query:
        print("Usage: hermes neural recall <query>")
        print("  Search neural memory semantically.")
        print()
        print("Examples:")
        print("  hermes neural recall python environment")
        print("  hermes neural recall --limit=10 'hermes setup'")
        sys.exit(1)

    try:
        limit = args.limit if hasattr(args, "limit") and args.limit else 5
        result = prov._handle_recall({"query": query, "limit": limit})
        parsed = json.loads(result)
        if "error" in parsed:
            print(f"Error: {parsed['error']}")
            sys.exit(1)

        memories = parsed.get("results", [])
        if not memories:
            print("No results found.")
        else:
            for i, mem in enumerate(memories, 1):
                label = mem.get("label", "")
                content = mem.get("content", "")[:200]
                mem_id = mem.get("id", "")
                score = mem.get("similarity", 0)
                conns_count = len(mem.get("connections", [])) if isinstance(mem.get("connections"), list) else mem.get("connections", 0)
                print(f"\n{i}. [{label}] (id={mem_id}, score={score:.2f}, {conns_count} connections)")
                print(f"   {content}")
        print()
    except Exception as e:
        print(f"Failed: {e}")
        sys.exit(1)


def cmd_think(args) -> None:
    """Spreading activation from CLI."""
    prov = _ensure_provider()
    _cli_init(prov)

    # Resolve memory_id (positional only now)
    memory_id = args.memory_id

    if memory_id is None and not args.query:
        print("Usage: hermes neural think <memory_id|query>")
        print("  Explore connected memories via spreading activation.")
        print()
        print("Examples:")
        print("  hermes neural think 1234")
        print("  hermes neural think --query='hermes setup'")
        print("  hermes neural think --memory-id=5678 --depth=3")
        sys.exit(1)

    try:
        depth = args.depth if hasattr(args, "depth") and args.depth else 3
        if memory_id:
            result = prov._handle_think({
                "memory_id": int(memory_id),
                "depth": depth,
            })
        else:
            query = " ".join(args.query) if isinstance(args.query, list) else args.query
            # First recall to get memory_id, then think
            recall_result = prov._handle_recall({"query": query, "limit": 1})
            recall_parsed = json.loads(recall_result)
            memories = recall_parsed.get("results", [])
            if not memories:
                print("No memory found for query.")
                sys.exit(1)
            mem_id = memories[0].get("id")
            if not mem_id:
                print("No memory_id in result.")
                sys.exit(1)
            result = prov._handle_think({"memory_id": int(mem_id), "depth": depth})

        parsed = json.loads(result)
        if "error" in parsed:
            print(f"Error: {parsed['error']}")
            sys.exit(1)

        activated = parsed.get("results", [])
        print(f"Activated {len(activated)} memories:")
        for mem in activated:
            mem_id = mem.get("id", "?")
            label = mem.get("label", "")
            content = mem.get("content", "")[:150]
            depth_val = mem.get("depth", 0)
            print(f"  [{mem.get('activation', 0):.3f}] ({mem_id}) {label}: {content}...")
        print()
    except Exception as e:
        print(f"Failed: {e}")
        sys.exit(1)


def cmd_graph(args) -> None:
    """Show knowledge graph stats."""
    prov = _load_provider()

    if prov is None:
        print("Neural memory provider is not active.")
        sys.exit(1)

    prov = _load_provider()
    _cli_init(prov)

    try:
        result = prov._handle_graph({})
        parsed = json.loads(result)
        if "error" in parsed:
            print(f"Error: {parsed['error']}")
            sys.exit(1)

        graph = parsed.get("graph", {})
        stats = parsed.get("stats", {})

        # Main stats (stats dict has: memories, connections, embedding_dim, etc.)
        total_mem = stats.get("memories", stats.get("total_memories", "?"))
        total_conn = stats.get("connections", stats.get("total_connections", "?"))
        embed_dim = stats.get("embedding_dim", "?")
        backend = stats.get("embedding_backend", "?")
        mssql = stats.get("mssql_mirror", False)

        # DB size from graph nodes count (approximate)
        try:
            nodes = graph.get("nodes", [])
            db_size = f"{len(nodes) * 0.001:.1f}"
        except Exception:
            db_size = "?"

        print(f"  Memories:     {total_mem}")
        print(f"  Connections:  {total_conn}")
        print(f"  Embedding:    {embed_dim}d ({backend})")
        print(f"  MSSQL mirror: {mssql}")
        print()

        # Top connections (edges: {from, to, weight})
        try:
            graph = parsed.get("graph", {})
            stats = parsed.get("stats", {})

            # Top edges (connections between memories)
            top_edges = graph.get("top_edges", [])
            if top_edges:
                print("  Top edges:")
                for item in top_edges[:10]:
                    if isinstance(item, dict):
                        frm = item.get("from", "?")
                        to = item.get("to", "?")
                        weight = item.get("weight", 0)
                        print(f"    {frm} → {to} (weight={weight:.2f})")
                    else:
                        print(f"    {item}")
                print()
        except Exception:
            pass

    except Exception as e:
        print(f"Failed: {e}")
        sys.exit(1)


# ────────────────────────────────────────────────────────────────────────────
# CLI registration
# ────────────────────────────────────────────────────────────────────────────

def register_cli(subparser) -> None:
    """Register neural memory CLI commands (hermes neural ...).

    subparser is ALREADY the 'neural' ArgumentParser created by main.py.
    Do NOT call subparser.add_parser("neural", ...). Just add sub-subcommands.
    """
    neural_sub = subparser.add_subparsers(dest="neural_cmd", metavar="CMD")

    # hermes neural status
    status_parser = neural_sub.add_parser(
        "status", help="Show neural memory status and stats."
    )
    status_parser.set_defaults(func=cmd_status)

    # hermes neural remember
    remember_parser = neural_sub.add_parser(
        "remember", help="Store a memory in neural memory."
    )
    remember_parser.add_argument("content", nargs="+", help="Memory content")
    remember_parser.add_argument("--label", "-l", dest="label",
                                 help="Optional label for this memory")
    remember_parser.set_defaults(func=cmd_remember)

    # hermes neural recall
    recall_parser = neural_sub.add_parser(
        "recall", help="Search memories semantically."
    )
    recall_parser.add_argument("query", nargs="+", help="Search query")
    recall_parser.add_argument("--limit", type=int, default=5,
                               help="Max results (default: 5)")
    recall_parser.set_defaults(func=cmd_recall)

    # hermes neural think
    think_parser = neural_sub.add_parser(
        "think", help="Explore connected memories via spreading activation."
    )
    think_parser.add_argument("memory_id", nargs="?", type=int, default=None,
                             help="Starting memory ID")
    think_parser.add_argument("--query", "-q", dest="query",
                             help="Query to find starting memory (searches first)")
    think_parser.add_argument("--depth", "-d", type=int, default=3,
                             help="Activation depth (default: 3)")
    think_parser.set_defaults(func=cmd_think)

    # hermes neural graph
    graph_parser = neural_sub.add_parser(
        "graph", help="Show knowledge graph statistics."
    )
    graph_parser.set_defaults(func=cmd_graph)
