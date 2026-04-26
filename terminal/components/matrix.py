"""
Matrix Rain Effect for Hermes Terminal.

Falling character columns with brightness-decay trails.
Supports configurable colors and character sets for theme integration.
"""
import random
import string
from typing import Iterator, Optional, Tuple

from rich.console import RenderableType
from rich.text import Text
from textual.widget import Widget

from terminal.themes.amber import AMBER

_DEFAULT_CHARS = string.ascii_letters + string.digits + "!@#$%^&*()<>{}[]|;:."


class MatrixColumn:
    """Single column of falling characters."""

    def __init__(self, x: int, height: int, chars: str = _DEFAULT_CHARS):
        self.x = x
        self.height = height
        self.y = random.randint(-30, 0)
        self.trail = random.randint(8, 20)
        self.speed = random.uniform(0.2, 0.8)
        self.chars = chars

    def advance(self) -> Iterator[Tuple[int, str, float]]:
        """Yield (y, char, brightness) tuples for each trail segment."""
        for i in range(self.trail):
            y = self.y - i
            if 0 <= y < self.height:
                yield (y, random.choice(self.chars), 1.0 - (i / self.trail))
        self.y += 1
        if self.y - self.trail > self.height:
            self.y = random.randint(-30, 0)
            self.trail = random.randint(8, 20)


class MatrixRain:
    """
    Matrix rain effect rendered as a 2D character grid.

    Each falling column has a bright leading head and fading trail.
    Brightness controls rendering color: bright → trail → dim.
    """

    def __init__(self, width: int = 80, height: int = 24, chars: Optional[str] = None):
        self.width = width
        self.height = height
        self._chars = chars or _DEFAULT_CHARS
        self.columns: list[MatrixColumn] = []
        self.frame: int = 0

    def resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.columns = [MatrixColumn(x, height, chars=self._chars) for x in range(width)]

    def tick(self) -> None:
        self.frame += 1

    def render(
        self,
        bright_color: str = "#ffffff",
        trail_color: str = AMBER.PRIMARY,
        dim_color: str = AMBER.MATRIX_DIM,
    ) -> Text:
        """Render the current frame as a Rich Text object."""
        grid = [[" " for _ in range(self.width)] for _ in range(self.height)]
        bright = [[0.0 for _ in range(self.width)] for _ in range(self.height)]

        for col in self.columns:
            for y, ch, b in col.advance():
                if 0 <= y < self.height and 0 <= col.x < self.width:
                    grid[y][col.x] = ch
                    bright[y][col.x] = max(bright[y][col.x], b)

        lines = []
        for y in range(self.height):
            line = Text()
            for x in range(self.width):
                ch = grid[y][x]
                b = bright[y][x]
                if ch == " ":
                    line.append(" ")
                elif b > 0.7:
                    line.append(ch, style=f"bold {bright_color}")
                elif b > 0.4:
                    line.append(ch, style=trail_color)
                else:
                    line.append(ch, style=dim_color)
            lines.append(line)

        return Text("\n").join(lines)


class MatrixBackground(Widget):
    """Full-screen Matrix rain overlay — toggle visibility to show/hide."""

    DEFAULT_CSS = """
    MatrixBackground {
        layer: overlay;
        width: 100%;
        height: 100%;
        background: #0a0a14;
        display: none;
    }
    """

    def __init__(
        self,
        bright_color: str = "#ffffff",
        trail_color: str = AMBER.PRIMARY,
        dim_color: str = AMBER.MATRIX_DIM,
        chars: Optional[str] = None,
        bg_color: str = AMBER.MATRIX_BG,
    ) -> None:
        super().__init__()
        self._bright = bright_color
        self._trail = trail_color
        self._dim = dim_color
        self._bg = bg_color
        self._rain = MatrixRain(chars=chars)
        self._ready = False

    def on_mount(self) -> None:
        w, h = self.size.width or 80, self.size.height or 24
        self._rain.resize(w, h)
        self._ready = True
        self.set_interval(0.065, self._tick)  # ~15 fps

    def on_resize(self, event) -> None:
        self._rain.resize(event.size.width, event.size.height)
        self._ready = True
        # Push bg color into CSS dynamically
        self.styles.background = self._bg

    def _tick(self) -> None:
        if not self._ready:
            w, h = self.size.width or 80, self.size.height or 24
            self._rain.resize(w, h)
            self._ready = True
        self._rain.tick()
        if self.display:
            self.refresh()

    def render(self) -> RenderableType:
        return self._rain.render(
            bright_color=self._bright,
            trail_color=self._trail,
            dim_color=self._dim,
        )
