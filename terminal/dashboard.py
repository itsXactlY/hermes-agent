"""
Hermes Neural Dashboard — Main Application.

Full Textual TUI with real data: psutil metrics, live log tail,
gateway state, neural memory stats, and matrix rain overlay.

Controls:
    q  — Quit
    r  — Force refresh all widgets
    m  — Toggle matrix rain overlay

Theme selection:
    HERMES_THEME=neural python dashboard.py
    python dashboard.py --theme neural
"""
from __future__ import annotations

import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

if __name__ == "__main__":
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

# ── Theme selection (must happen before class bodies evaluate f-strings) ─────
_theme_name = os.environ.get("HERMES_THEME", "amber")
if "--theme" in sys.argv:
    _idx = sys.argv.index("--theme")
    if _idx + 1 < len(sys.argv):
        _theme_name = sys.argv[_idx + 1]

if _theme_name == "neural":
    from terminal.themes.neural import NEURAL as THEME
else:
    from terminal.themes.amber import AMBER as THEME

# ── Remaining imports ─────────────────────────────────────────────────────────
import psutil
from rich import box as _rich_box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, Header, Static

from terminal.components.matrix import MatrixBackground
from terminal.utils import (
    get_hermes_processes,
    get_hermes_state,
    get_neural_stats,
    get_system_metrics,
    tail_log,
)

# ── Panel box style (rounded for neural, square for amber) ────────────────────
_BOX = getattr(THEME, "BOX", _rich_box.SQUARE)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _bar(val: float, width: int = 22) -> Text:
    filled = max(0, min(width, int(val / 100 * width)))
    color = THEME.PRIMARY if val < 50 else THEME.ACCENT if val < 80 else THEME.CRITICAL
    b = Text()
    b.append("█" * filled, style=color)
    b.append("░" * (width - filled), style=THEME.DIM)
    return b


def _fmt_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _panel(content, title: str = "", subtitle: str = "") -> Panel:
    return Panel(
        content,
        title=title,
        subtitle=subtitle,
        box=_BOX,
        border_style=THEME.PRIMARY,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Widgets
# ─────────────────────────────────────────────────────────────────────────────

class NeuralWaveform(Static):
    """Animated waveform — live neural memory count in subtitle."""

    def on_mount(self) -> None:
        self._t0 = time.time()
        self._total = 0
        self._connections = 0
        self.auto_refresh = 0.1
        self.set_interval(30.0, self._refresh_stats)
        self._refresh_stats()

    def _refresh_stats(self) -> None:
        s = get_neural_stats()
        self._total = s.get("total", 0)
        self._connections = s.get("connections", 0)

    def render(self) -> Panel:
        t = time.time() - self._t0
        bars = THEME.SPARKLINE
        n = 96
        line = Text()
        for i in range(n):
            p = t * 1.8 + i * 0.13
            v = 0.5 + 0.32 * math.sin(p) + 0.12 * math.sin(p * 2.7) + 0.07 * math.sin(t * 7.3 + i * 0.37)
            v = max(0.0, min(0.999, v))
            line.append(bars[int(v * (len(bars) - 1))], style=THEME.PRIMARY)
        return _panel(
            line,
            title=f"[bold {THEME.PRIMARY}]⟨ Neural Activity ⟩[/]",
            subtitle=f"[{THEME.DIM}]{_fmt_num(self._total)} mem · {_fmt_num(self._connections)} edges[/]",
        )


class GatewayStatus(Static):
    """Live gateway state from gateway_state.json."""

    def on_mount(self) -> None:
        self._state: dict = {}
        self._update()
        self.set_interval(5.0, self._update)

    def _update(self) -> None:
        self._state = get_hermes_state()
        self.refresh()

    def render(self) -> Panel:
        s = self._state
        gw = s.get("gateway_state", "offline")
        gw_color = THEME.SUCCESS if gw == "running" else THEME.CRITICAL
        active = s.get("active_agents", 0)

        body = Text()
        body.append("Gateway   ", style=THEME.SECONDARY)
        body.append(f"{gw.upper()}\n", style=f"bold {gw_color}")
        for name, info in s.get("platforms", {}).items():
            st = info.get("state", "?")
            sc = THEME.SUCCESS if st == "connected" else THEME.CRITICAL
            body.append(f"{name[:8]:<10}", style=THEME.SECONDARY)
            body.append(f"{st}\n", style=sc)
        body.append("\nAgents    ", style=THEME.SECONDARY)
        body.append(str(active) + "\n", style=THEME.ACCENT if active else THEME.SECONDARY)
        if s.get("pid"):
            body.append(f"PID       {s['pid']}", style=THEME.SECONDARY)

        return _panel(body, title=f"[bold {THEME.PRIMARY}]⟨ Gateway ⟩[/]")


class ClockWidget(Static):
    """HH:MM:SS.mmm precision clock with system uptime."""

    def on_mount(self) -> None:
        self.auto_refresh = 0.1

    def render(self) -> Panel:
        now = datetime.now()
        ts = now.strftime("%H:%M:%S")
        ms = now.strftime("%f")[:3]
        try:
            up_s = int(time.time() - psutil.boot_time())
            h, rem = divmod(up_s, 3600)
            m, _ = divmod(rem, 60)
            uptime = f"up {h}h{m:02d}m"
        except Exception:
            uptime = ""
        date_str = now.strftime("%Y-%m-%d")
        return _panel(
            Text.assemble(
                (f"{ts}.{ms}\n", f"bold {THEME.PRIMARY}"),
                (f"{date_str}\n", THEME.SECONDARY),
                (uptime, THEME.DIM),
            ),
            title=f"[bold {THEME.PRIMARY}]⟨ Clock ⟩[/]",
        )


class AgentPanel(Static):
    """Hermes processes + gateway summary."""

    def on_mount(self) -> None:
        self._procs: list[dict] = []
        psutil.cpu_percent(interval=None)  # seed per-process CPU tracking
        self._update()
        self.set_interval(3.0, self._update)

    def _update(self) -> None:
        self._procs = get_hermes_processes()
        self.refresh()

    def render(self) -> Panel:
        table = Table(show_header=True, box=None, pad_edge=False, expand=True)
        table.add_column("Process", style=f"bold {THEME.PRIMARY}", max_width=14)
        table.add_column("PID", style=THEME.SECONDARY, width=7)
        table.add_column("CPU%", justify="right", width=6)
        table.add_column("MB", justify="right", width=5)

        for p in self._procs:
            cpu = p["cpu"]
            cpu_c = THEME.SUCCESS if cpu < 10 else THEME.ACCENT if cpu < 50 else THEME.CRITICAL
            marker = "●" if p.get("gateway") else "·"
            mc = THEME.SUCCESS if p.get("gateway") else THEME.DIM
            table.add_row(
                f"[{mc}]{marker}[/] {p['name'][:12]}",
                str(p["pid"]),
                f"[{cpu_c}]{cpu:.1f}[/]",
                str(p["mem"]),
            )

        if not self._procs:
            table.add_row(f"[{THEME.SECONDARY}]no hermes procs[/]", "", "", "")

        return _panel(table, title=f"[bold {THEME.PRIMARY}]⟨ Agent Processes ⟩[/]")


class SystemMetrics(Static):
    """Real-time system resource gauges with delta rates for disk/net."""

    def on_mount(self) -> None:
        self._metrics: dict[str, float] = {}
        self._prev: dict = {}
        psutil.cpu_percent(interval=None)
        self._metrics, self._prev = get_system_metrics()
        self.set_interval(2.0, self._update)

    def _update(self) -> None:
        self._metrics, self._prev = get_system_metrics(self._prev)
        self.refresh()

    def render(self) -> Panel:
        table = Table(show_header=False, box=None, pad_edge=False, expand=True)
        table.add_column("Name", style=THEME.PRIMARY, width=7)
        table.add_column("Bar")
        table.add_column("Val", justify="right", width=7)
        for name, val in self._metrics.items():
            table.add_row(name, _bar(val, 18), f"{val:.1f}%")
        return _panel(table, title=f"[bold {THEME.PRIMARY}]⟨ System ⟩[/]")


class NeuralMemoryWidget(Static):
    """Neural memory stats: counts, recent memories, last dream session."""

    def on_mount(self) -> None:
        self._stats: dict = {}
        self._update()
        self.set_interval(20.0, self._update)

    def _update(self) -> None:
        self._stats = get_neural_stats()
        self.refresh()

    def render(self) -> Panel:
        s = self._stats
        body = Text()
        body.append("Memories  ", style=THEME.SECONDARY)
        body.append(f"{_fmt_num(s.get('total', 0))}\n", style=f"bold {THEME.PRIMARY}")
        body.append("Edges     ", style=THEME.SECONDARY)
        body.append(f"{_fmt_num(s.get('connections', 0))}\n", style=THEME.ACCENT)

        ld = s.get("last_dream", {})
        if ld:
            body.append(f"\n● Dream @ {ld.get('started','?')}\n", style=THEME.SUCCESS)
            body.append(
                f"  +{ld.get('processed',0)} proc  +{ld.get('strengthened',0)} links\n",
                style=THEME.SECONDARY,
            )

        for r in s.get("recent", [])[:3]:
            body.append(f"[{r['ts']}] ", style=THEME.SECONDARY)
            body.append(f"{r['content'][:45]}\n", style=f"dim {THEME.PRIMARY}")

        if "error" in s:
            body.append(f"[ERR] {s['error'][:40]}", style=THEME.CRITICAL)

        return _panel(body, title=f"[bold {THEME.PRIMARY}]⟨ Neural Memory ⟩[/]")


class ProcessList(Static):
    """Hermes processes — wider table with status column."""

    def on_mount(self) -> None:
        self._procs: list[dict] = []
        self._update()
        self.set_interval(3.0, self._update)

    def _update(self) -> None:
        self._procs = get_hermes_processes()
        self.refresh()

    def render(self) -> Panel:
        table = Table(show_header=True, box=None, pad_edge=False, expand=True)
        table.add_column("Process", style=f"bold {THEME.PRIMARY}", max_width=18)
        table.add_column("PID", style=THEME.SECONDARY, width=7)
        table.add_column("CPU%", justify="right", width=6)
        table.add_column("MB", justify="right", width=5)
        table.add_column("Role", width=9)

        for p in self._procs:
            cpu = p["cpu"]
            cpu_c = THEME.SUCCESS if cpu < 10 else THEME.ACCENT if cpu < 50 else THEME.CRITICAL
            marker = "●" if p.get("gateway") else "·"
            mc = THEME.SUCCESS if p.get("gateway") else THEME.DIM
            role = "gateway" if p.get("gateway") else "worker"
            table.add_row(
                f"[{mc}]{marker}[/] {p['name'][:16]}",
                str(p["pid"]),
                f"[{cpu_c}]{cpu:.1f}[/]",
                str(p["mem"]),
                f"[{THEME.SECONDARY}]{role}[/]",
            )

        if not self._procs:
            table.add_row(f"[{THEME.SECONDARY}]no hermes processes found[/]", "", "", "", "")

        return _panel(table, title=f"[bold {THEME.PRIMARY}]⟨ Processes ⟩[/]")


class ActivityLog(Static):
    """Live tail of ~/.hermes/logs/agent.log."""

    def on_mount(self) -> None:
        self._lines: list[str] = []
        self._update()
        self.set_interval(3.0, self._update)

    def _update(self) -> None:
        self._lines = tail_log(18)
        self.refresh()

    def render(self) -> Panel:
        body = Text()
        for line in self._lines:
            body.append_text(Text.from_markup(line))
            body.append("\n")
        return _panel(body, title=f"[bold {THEME.PRIMARY}]⟨ Agent Log ⟩[/]")


# ─────────────────────────────────────────────────────────────────────────────
# Application
# ─────────────────────────────────────────────────────────────────────────────

class HermesDashboard(App):
    """Hermes Neural Dashboard — themed, real data, matrix overlay."""

    CSS = f"""
    Screen {{
        layers: base overlay;
        background: {THEME.BG};
        color: {THEME.PRIMARY};
    }}

    MatrixBackground {{
        layer: overlay;
        width: 100%;
        height: 100%;
        background: {THEME.MATRIX_BG};
        display: none;
    }}

    #main-grid {{
        layer: base;
        layout: grid;
        grid-size: 4 4;
        grid-gutter: 0 1;
        grid-rows: 1fr 2fr 2fr 2fr;
        padding: 0 1;
        height: 1fr;
    }}

    #waveform   {{ column-span: 2; }}
    #gateway    {{ column-span: 1; }}
    #clock      {{ column-span: 1; }}

    #agents     {{ column-span: 1; row-span: 2; }}
    #metrics    {{ column-span: 2; }}
    #neural     {{ column-span: 1; row-span: 2; }}

    #processes  {{ column-span: 2; }}

    #log        {{ column-span: 4; }}

    Static {{
        background: {THEME.BG};
    }}

    Header {{
        background: {THEME.BG};
        color: {THEME.PRIMARY};
    }}

    Footer {{
        background: {THEME.BG};
        color: {THEME.SECONDARY};
    }}
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh_all", "Refresh"),
        ("m", "toggle_matrix", "Matrix"),
    ]

    _matrix_on: bool = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Container(id="main-grid"):
            yield NeuralWaveform(id="waveform")
            yield GatewayStatus(id="gateway")
            yield ClockWidget(id="clock")
            yield AgentPanel(id="agents")
            yield SystemMetrics(id="metrics")
            yield NeuralMemoryWidget(id="neural")
            yield ProcessList(id="processes")
            yield ActivityLog(id="log")
        yield MatrixBackground(
            bright_color=THEME.MATRIX_BRIGHT,
            trail_color=THEME.MATRIX_TRAIL,
            dim_color=THEME.MATRIX_DIM,
            chars=getattr(THEME, "MATRIX_CHARS", None),
            bg_color=THEME.MATRIX_BG,
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"HERMES  [{_theme_name.upper()}]"
        self.sub_title = "neural dashboard · q quit · m matrix · r refresh"

    def action_refresh_all(self) -> None:
        for w in self.query(Static):
            w.refresh()

    def action_toggle_matrix(self) -> None:
        matrix = self.query_one(MatrixBackground)
        self._matrix_on = not self._matrix_on
        matrix.display = self._matrix_on
        if self._matrix_on:
            self.notify(
                f"Matrix ON [{_theme_name}] — press M to exit",
                title="⟨ MATRIX ⟩",
                timeout=2,
            )


if __name__ == "__main__":
    HermesDashboard().run()
