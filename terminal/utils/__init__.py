"""Real data utilities for the Hermes terminal dashboard."""
from __future__ import annotations

import json
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import psutil

_HERMES_DIR = Path.home() / ".hermes"
_GATEWAY_STATE = _HERMES_DIR / "gateway_state.json"
_LOG_PATH = _HERMES_DIR / "logs" / "agent.log"
_NEURAL_DB = Path.home() / ".neural_memory" / "memory.db"

_LOG_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+)\s+"
    r"(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s+"
    r"(?:\[([^\]]+)\]\s+)?"
    r"([^:]+):\s*(.*)"
)


def get_hermes_state() -> dict:
    """Read gateway_state.json; return {} on error."""
    try:
        return json.loads(_GATEWAY_STATE.read_text())
    except Exception:
        return {}


def get_system_metrics(prev: dict | None = None) -> tuple[dict[str, float], dict]:
    """
    Return (metrics_dict, new_prev) where values are 0-100 percentages.
    prev holds previous IO counters for delta-rate computation.
    """
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()

    disk_read_pct = 0.0
    disk_write_pct = 0.0
    net_tx_pct = 0.0

    now = time.monotonic()
    try:
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()
    except Exception:
        disk_io = net_io = None

    if prev and disk_io and net_io:
        dt = now - prev.get("time", now)
        if dt > 0:
            dr = (disk_io.read_bytes - prev.get("dr", disk_io.read_bytes)) / dt
            dw = (disk_io.write_bytes - prev.get("dw", disk_io.write_bytes)) / dt
            ns = (net_io.bytes_sent - prev.get("ns", net_io.bytes_sent)) / dt
            # Scale: 100 MB/s → 100%
            disk_read_pct = min(dr / 1_000_000, 99.0)
            disk_write_pct = min(dw / 1_000_000, 99.0)
            net_tx_pct = min(ns / 1_000_000, 99.0)

    new_prev: dict = {"time": now}
    if disk_io:
        new_prev["dr"] = disk_io.read_bytes
        new_prev["dw"] = disk_io.write_bytes
    if net_io:
        new_prev["ns"] = net_io.bytes_sent
        new_prev["nr"] = net_io.bytes_recv

    return {
        "CPU": cpu,
        "RAM": mem.percent,
        "Disk R": disk_read_pct,
        "Disk W": disk_write_pct,
        "Net TX": net_tx_pct,
    }, new_prev


def get_hermes_processes() -> list[dict]:
    """Return hermes/python processes sorted by CPU descending (max 8)."""
    procs: list[dict] = []
    gateway_pid = get_hermes_state().get("pid")

    for p in psutil.process_iter(["pid", "name", "cmdline", "cpu_percent", "memory_info"]):
        try:
            info = p.info
            cmdline = " ".join(info.get("cmdline") or [])
            name = info.get("name") or ""
            is_hermes = (
                "hermes" in cmdline.lower()
                or "mcp_local" in cmdline
                or "neural_memory" in cmdline
                or "neural-memory" in cmdline
                or info["pid"] == gateway_pid
            )
            if not is_hermes:
                continue
            label = name[:14]
            if "python" in name.lower():
                parts = (info.get("cmdline") or [])[1:]
                if parts:
                    label = Path(parts[0]).name[:14]
            procs.append({
                "pid": info["pid"],
                "name": label,
                "cpu": info["cpu_percent"] or 0.0,
                "mem": (info["memory_info"].rss >> 20) if info["memory_info"] else 0,
                "gateway": info["pid"] == gateway_pid,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return sorted(procs, key=lambda p: p["cpu"], reverse=True)[:8]


def get_neural_stats() -> dict:
    """Query neural memory DB for counts, recent memories, and last dream session."""
    try:
        con = sqlite3.connect(str(_NEURAL_DB), timeout=2.0)
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM memories")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM connections")
        connections = cur.fetchone()[0]
        cur.execute(
            "SELECT content, created_at FROM memories ORDER BY created_at DESC LIMIT 4"
        )
        recent_rows = cur.fetchall()
        cur.execute(
            "SELECT started_at, memories_processed, connections_strengthened "
            "FROM dream_sessions ORDER BY started_at DESC LIMIT 1"
        )
        dream = cur.fetchone()
        con.close()

        recent = []
        for content, ts in recent_rows:
            try:
                dt = datetime.fromtimestamp(float(ts)).strftime("%H:%M")
            except Exception:
                dt = "??:??"
            recent.append({"content": content[:55], "ts": dt})

        last_dream: dict = {}
        if dream:
            try:
                last_dream = {
                    "started": datetime.fromtimestamp(float(dream[0])).strftime("%H:%M"),
                    "processed": dream[1],
                    "strengthened": dream[2],
                }
            except Exception:
                pass

        return {
            "total": total,
            "connections": connections,
            "recent": recent,
            "last_dream": last_dream,
        }
    except Exception as e:
        return {"total": 0, "connections": 0, "recent": [], "last_dream": {}, "error": str(e)}


def tail_log(n: int = 18) -> list[str]:
    """Return last n lines from agent.log as Rich markup strings."""
    level_colors = {
        "DEBUG": "#666677",
        "INFO": "#f5b731",
        "WARNING": "#ff9900",
        "ERROR": "#ff4444",
        "CRITICAL": "bold #ff0000",
    }
    try:
        text = _LOG_PATH.read_text(errors="replace")
        lines = [l for l in text.splitlines() if l.strip()][-n:]
    except Exception:
        return ["[#666677]no log data[/]"]

    result = []
    for line in lines:
        m = _LOG_RE.match(line)
        if m:
            ts, level, session, module, msg = m.groups()
            ts_short = ts[11:19]
            lc = level_colors.get(level, "#ffffff")
            mod = (module or "").split(".")[-1][:16]
            session_part = f"[{session[:12]}] " if session else ""
            result.append(
                f"[#555566]{ts_short}[/] [{lc}]{level[:4]}[/] "
                f"[#557799]{session_part}[/][#99aacc]{mod}[/] {msg[:65]}"
            )
        else:
            result.append(f"[#555566]{line[:85]}[/]")
    return result
