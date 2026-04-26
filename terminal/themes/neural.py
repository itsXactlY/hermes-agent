"""
Neural Bioluminescent Theme — Hermes Terminal.

Palette: deep ocean black + electric cyan synapses + violet axon pulses.
Inspired by bioluminescent deep-sea neural firing and signal propagation.
"""
from __future__ import annotations
from rich import box as _box


class _NeuralPalette:
    # ── Backgrounds ──────────────────────────────────────────────────────────
    BG         = "#020810"   # deep abyss — near-absolute black with blue tint
    PANEL_BG   = "#060f1e"   # deep navy panel surfaces
    MATRIX_BG  = "#010508"   # void black for matrix overlay

    # ── Primary ──────────────────────────────────────────────────────────────
    PRIMARY    = "#00d4ff"   # electric cyan — synapse fire, main borders & text
    BRIGHT     = "#80eeff"   # ice-blue — active/selected/highlight
    DIM        = "#0a1e30"   # deep shadow — inactive separators

    # ── Semantic text ────────────────────────────────────────────────────────
    SECONDARY  = "#1a5070"   # muted steel-blue — labels, metadata, timestamps
    ACCENT     = "#9d4dff"   # electric violet — axon pulse, warnings
    CRITICAL   = "#ff2060"   # hot overload — magenta-red
    SUCCESS    = "#00ff94"   # bioluminescent green-cyan — healthy

    # ── Gradient stops (cyan → violet → hot-pink) ────────────────────────────
    GRADIENT_START = "#00d4ff"
    GRADIENT_MID   = "#9d4dff"
    GRADIENT_END   = "#ff2060"

    # ── Matrix rain ──────────────────────────────────────────────────────────
    MATRIX_BRIGHT = "#c0f4ff"   # ice-blue leading edge
    MATRIX_TRAIL  = "#00d4ff"   # cyan trail body
    MATRIX_DIM    = "#003d55"   # deep teal fade

    # Neural matrix chars: Greek alphabet + mathematical operators + digits
    MATRIX_CHARS = (
        "αβγδεζηθικλμνξπρστυφχψω"   # lowercase Greek
        "ΑΒΓΔΕΖΗΘΛΜΝΞΠΡΣΦΧΨΩ"       # uppercase Greek (selective)
        "∑∏∫∂∇∞≈≠≤≥±×÷"             # math
        "0123456789"                  # digits
        "⊕⊗⊙⊛⋆◈◇▸"                  # circuit / symbolic
    )

    # ── Status colors ────────────────────────────────────────────────────────
    STATUS_ACTIVE    = "#00ff94"
    STATUS_THINKING  = "#9d4dff"
    STATUS_INDEXING  = "#00d4ff"
    STATUS_IDLE      = "#1a5070"
    STATUS_OBSERVING = "#ff60c8"
    STATUS_ERROR     = "#ff2060"

    # ── Rich box style (rounded corners ╭╮╰╯) ────────────────────────────────
    BOX = _box.ROUNDED

    # ── Box drawing ──────────────────────────────────────────────────────────
    H = "─"; V = "│"; TL = "╭"; TR = "╮"; BL = "╰"; BR = "╯"
    LT = "├"; RT = "┤"; UT = "┬"; DT = "┴"; CROSS = "┼"
    H2 = "═"; V2 = "║"; TL2 = "╔"; TR2 = "╗"; BL2 = "╚"; BR2 = "╝"
    LT2 = "╠"; RT2 = "╣"; UT2 = "╦"; DT2 = "╩"; CROSS2 = "╬"

    # ── Block / braille characters ────────────────────────────────────────────
    D1 = "░"; D2 = "▒"; D3 = "█"; UPPER = "▀"; LOWER = "▄"
    SPARKLINE = " ▁▂▃▄▅▆▇█"

    BRAILLE_OFFSET = 0x2800
    BRAILLE_DOTS = (
        "⠀","⠁","⠂","⠃","⠄","⠅","⠆","⠇","⠈","⠉","⠊","⠋","⠌","⠍","⠎","⠏",
        "⠐","⠑","⠒","⠓","⠔","⠕","⠖","⠗","⠘","⠙","⠚","⠛","⠜","⠝","⠞","⠟",
        "⠠","⠡","⠢","⠣","⠤","⠥","⠦","⠧","⠨","⠩","⠪","⠫","⠬","⠭","⠮","⠯",
        "⠰","⠱","⠲","⠳","⠴","⠵","⠶","⠷","⠸","⠹","⠺","⠻","⠼","⠽","⠾","⠿",
        "⡀","⡁","⡂","⡃","⡄","⡅","⡆","⡇","⡈","⡉","⡊","⡋","⡌","⡍","⡎","⡏",
        "⡐","⡑","⡒","⡓","⡔","⡕","⡖","⡗","⡘","⡙","⡚","⡛","⡜","⡝","⡞","⡟",
        "⡠","⡡","⡢","⡣","⡤","⡥","⡦","⡧","⡨","⡩","⡪","⡫","⡬","⡭","⡮","⡯",
        "⡰","⡱","⡲","⡳","⡴","⡵","⡶","⡷","⡸","⡹","⡺","⡻","⡼","⡽","⡾","⡿",
        "⢀","⢁","⢂","⢃","⢄","⢅","⢆","⢇","⢈","⢉","⢊","⢋","⢌","⢍","⢎","⢏",
        "⢐","⢑","⢒","⢓","⢔","⢕","⢖","⢗","⢘","⢙","⢚","⢛","⢜","⢝","⢞","⢟",
        "⢠","⢡","⢢","⢣","⢤","⢥","⢦","⢧","⢨","⢩","⢪","⢫","⢬","⢭","⢮","⢯",
        "⢰","⢱","⢲","⢳","⢴","⢵","⢶","⢷","⢸","⢹","⢺","⢻","⢼","⢽","⢾","⢿",
        "⣀","⣁","⣂","⣃","⣄","⣅","⣆","⣇","⣈","⣉","⣊","⣋","⣌","⣍","⣎","⣏",
        "⣐","⣑","⣒","⣓","⣔","⣕","⣖","⣗","⣘","⣙","⣚","⣛","⣜","⣝","⣞","⣟",
        "⣠","⣡","⣢","⣣","⣤","⣥","⣦","⣧","⣨","⣩","⣪","⣫","⣬","⣭","⣮","⣯",
        "⣰","⣱","⣲","⣳","⣴","⣵","⣶","⣷","⣸","⣹","⣺","⣻","⣼","⣽","⣾","⣿",
    )

    @staticmethod
    def rgb(r: int, g: int, b: int) -> str:
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def gradient_color(position: float) -> str:
        """cyan (#00d4ff) → violet (#9d4dff) → hot-pink (#ff2060)"""
        if position < 0.5:
            t = position * 2
            r = int(0x00 + (0x9d - 0x00) * t)
            g = int(0xd4 + (0x4d - 0xd4) * t)
            b = int(0xff + (0xff - 0xff) * t)
        else:
            t = (position - 0.5) * 2
            r = int(0x9d + (0xff - 0x9d) * t)
            g = int(0x4d + (0x20 - 0x4d) * t)
            b = int(0xff + (0x60 - 0xff) * t)
        return f"#{r:02x}{g:02x}{b:02x}"


NEURAL = _NeuralPalette()

# Module-level aliases (mirrors amber.py structure)
BG             = NEURAL.BG
PANEL_BG       = NEURAL.PANEL_BG
MATRIX_BG      = NEURAL.MATRIX_BG
PRIMARY        = NEURAL.PRIMARY
BRIGHT         = NEURAL.BRIGHT
DIM            = NEURAL.DIM
SECONDARY      = NEURAL.SECONDARY
ACCENT         = NEURAL.ACCENT
CRITICAL       = NEURAL.CRITICAL
SUCCESS        = NEURAL.SUCCESS
GRADIENT_START = NEURAL.GRADIENT_START
GRADIENT_MID   = NEURAL.GRADIENT_MID
GRADIENT_END   = NEURAL.GRADIENT_END
MATRIX_BRIGHT  = NEURAL.MATRIX_BRIGHT
MATRIX_TRAIL   = NEURAL.MATRIX_TRAIL
MATRIX_DIM     = NEURAL.MATRIX_DIM
MATRIX_CHARS   = NEURAL.MATRIX_CHARS
STATUS_ACTIVE    = NEURAL.STATUS_ACTIVE
STATUS_THINKING  = NEURAL.STATUS_THINKING
STATUS_INDEXING  = NEURAL.STATUS_INDEXING
STATUS_IDLE      = NEURAL.STATUS_IDLE
STATUS_OBSERVING = NEURAL.STATUS_OBSERVING
STATUS_ERROR     = NEURAL.STATUS_ERROR
BOX            = NEURAL.BOX
SPARKLINE      = NEURAL.SPARKLINE
rgb            = NEURAL.rgb
gradient_color = NEURAL.gradient_color
