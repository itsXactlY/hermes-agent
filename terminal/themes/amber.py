"""Amber-on-Dark theme constants for Hermes Terminal."""

# Backward-compatibility class wrapper
class _AmberPalette:
    """Namespace for all amber theme constants. Allows: from amber import AMBER; AMBER.PRIMARY"""
    BG = "#1a1a24"
    PANEL_BG = "#2a2a34"
    MATRIX_BG = "#0a0a14"
    PRIMARY = "#f5b731"
    BRIGHT = "#ffcc00"
    DIM = "#333344"
    SECONDARY = "#666677"
    ACCENT = "#ff8800"
    CRITICAL = "#ff3333"
    SUCCESS = "#33cc33"
    GRADIENT_START = "#f5b731"
    GRADIENT_MID = "#ff8800"
    GRADIENT_END = "#ff3333"
    MATRIX_BRIGHT = "#ffffff"
    MATRIX_TRAIL = "#f5b731"
    MATRIX_DIM = "#665500"
    STATUS_ACTIVE = "#33cc33"
    STATUS_THINKING = "#ff8800"
    STATUS_INDEXING = "#33ccff"
    STATUS_IDLE = "#666677"
    STATUS_OBSERVING = "#ff33ff"
    STATUS_ERROR = "#ff3333"
    # Box drawing (single-line)
    H = "─"; V = "│"; TL = "┌"; TR = "┐"; BL = "└"; BR = "┘"
    LT = "├"; RT = "┤"; UT = "┬"; DT = "┴"; CROSS = "┼"
    # Box drawing (double-line)
    H2 = "═"; V2 = "║"; TL2 = "╔"; TR2 = "╗"; BL2 = "╚"; BR2 = "╝"
    LT2 = "╠"; RT2 = "╣"; UT2 = "╦"; DT2 = "╩"; CROSS2 = "╬"
    # Block characters
    D1 = "░"; D2 = "▒"; D3 = "█"; UPPER = "▀"; LOWER = "▄"
    # Braille
    BRAILLE_OFFSET = 0x2800
    BRAILLE_DOTS = (
        "⠀", "⠁", "⠂", "⠃", "⠄", "⠅", "⠆", "⠇", "⠈", "⠉", "⠊", "⠋", "⠌", "⠍", "⠎", "⠏",
        "⠐", "⠑", "⠒", "⠓", "⠔", "⠕", "⠖", "⠗", "⠘", "⠙", "⠚", "⠛", "⠜", "⠝", "⠞", "⠟",
        "⠠", "⠡", "⠢", "⠣", "⠤", "⠥", "⠦", "⠧", "⠨", "⠩", "⠪", "⠫", "⠬", "⠭", "⠮", "⠯",
        "⠰", "⠱", "⠲", "⠳", "⠴", "⠵", "⠶", "⠷", "⠸", "⠹", "⠺", "⠻", "⠼", "⠽", "⠾", "⠿",
        "⡀", "⡁", "⡂", "⡃", "⡄", "⡅", "⡆", "⡇", "⡈", "⡉", "⡊", "⡋", "⡌", "⡍", "⡎", "⡏",
        "⡐", "⡑", "⡒", "⡓", "⡔", "⡕", "⡖", "⡗", "⡘", "⡙", "⡚", "⡛", "⡜", "⡝", "⡞", "⡟",
        "⡠", "⡡", "⡢", "⡣", "⡤", "⡥", "⡦", "⡧", "⡨", "⡩", "⡪", "⡫", "⡬", "⡭", "⡮", "⡯",
        "⡰", "⡱", "⡲", "⡳", "⡴", "⡵", "⡶", "⡷", "⡸", "⡹", "⡺", "⡻", "⡼", "⡽", "⡾", "⡿",
        "⢀", "⢁", "⢂", "⢃", "⢄", "⢅", "⢆", "⢇", "⢈", "⢉", "⢊", "⢋", "⢌", "⢍", "⢎", "⢏",
        "⢐", "⢑", "⢒", "⢓", "⢔", "⢕", "⢖", "⢗", "⢘", "⢙", "⢚", "⢛", "⢜", "⢝", "⢞", "⢟",
        "⢠", "⢡", "⢢", "⢣", "⢤", "⢥", "⢦", "⢧", "⢨", "⢩", "⢪", "⢫", "⢬", "⢭", "⢮", "⢯",
        "⢰", "⢱", "⢲", "⢳", "⢴", "⢵", "⢶", "⢷", "⢸", "⢹", "⢺", "⢻", "⢼", "⢽", "⢾", "⢿",
        "⣀", "⣁", "⣂", "⣃", "⣄", "⣅", "⣆", "⣇", "⣈", "⣉", "⣊", "⣋", "⣌", "⣍", "⣎", "⣏",
        "⣐", "⣑", "⣒", "⣓", "⣔", "⣕", "⣖", "⣗", "⣘", "⣙", "⣚", "⣛", "⣜", "⣝", "⣞", "⣟",
        "⣠", "⣡", "⣢", "⣣", "⣤", "⣥", "⣦", "⣧", "⣨", "⣩", "⣪", "⣫", "⣬", "⣭", "⣮", "⣯",
        "⣰", "⣱", "⣲", "⣳", "⣴", "⣵", "⣶", "⣷", "⣸", "⣹", "⣺", "⣻", "⣼", "⣽", "⣾", "⣿",
    )
    SPARKLINE = " ▁▂▃▄▅▆▇█"

    @staticmethod
    def rgb(r: int, g: int, b: int) -> str:
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def gradient_color(position: float) -> str:
        if position < 0.5:
            t = position * 2
            r = int(0xf5 + (0xff - 0xf5) * t)
            g = int(0xb7 + (0x88 - 0xb7) * t)
            b = int(0x31 + (0x00 - 0x31) * t)
        else:
            t = (position - 0.5) * 2
            r = 0xff
            g = int(0x88 + (0x33 - 0x88) * t)
            b = int(0x00 + (0x33 - 0x00) * t)
        return _AmberPalette.rgb(r, g, b)


AMBER = _AmberPalette()

# =============================================================================
# PRIMARY PALETTE
# =============================================================================

# Backgrounds
BG: str = "#1a1a24"          # Primary dark background (navy-black)
PANEL_BG: str = "#2a2a34"    # Panel/surface background
MATRIX_BG: str = "#0a0a14"   # Matrix rain background (deeper)

# Primary text & borders
PRIMARY: str = "#f5b731"     # Warm amber — main text, borders, highlights
BRIGHT: str = "#ffcc00"      # Bright amber — active/selected elements
DIM: str = "#333344"         # Dim elements — separators, inactive borders

# Semantic text
SECONDARY: str = "#666677"   # Muted labels, metadata, timestamps
ACCENT: str = "#ff8800"      # Orange — warnings, mid-range values
CRITICAL: str = "#ff3333"    # Red — errors, high-load states
SUCCESS: str = "#33cc33"     # Green — healthy/active states

# =============================================================================
# GRADIENT STOPS
# =============================================================================

# Thermal gradient: amber → orange → red (for resource bars)
GRADIENT_START: str = PRIMARY   # #f5b731
GRADIENT_MID: str = ACCENT      # #ff8800
GRADIENT_END: str = CRITICAL    # #ff3333

# =============================================================================
# MATRIX RAIN
# =============================================================================

MATRIX_BRIGHT: str = "#ffffff"   # Leading edge characters
MATRIX_TRAIL: str = PRIMARY      # Mid-trail characters
MATRIX_DIM: str = "#665500"      # Fading trail characters

# =============================================================================
# STATUS COLORS (for agent rows)
# =============================================================================

STATUS_ACTIVE: str = SUCCESS          # Green
STATUS_THINKING: str = ACCENT         # Orange
STATUS_INDEXING: str = "#33ccff"      # Cyan
STATUS_IDLE: str = SECONDARY           # Muted
STATUS_OBSERVING: str = "#ff33ff"     # Magenta
STATUS_ERROR: str = CRITICAL           # Red

# =============================================================================
# BOX DRAWING (Unicode)
# =============================================================================

# Single-line (subtle, modern)
H: str = "─"
V: str = "│"
TL: str = "┌"
TR: str = "┐"
BL: str = "└"
BR: str = "┘"
LT: str = "├"
RT: str = "┤"
UT: str = "┬"
DT: str = "┴"
CROSS: str = "┼"

# Double-line (emphasis)
H2: str = "═"
V2: str = "║"
TL2: str = "╔"
TR2: str = "╗"
BL2: str = "╚"
BR2: str = "╝"
LT2: str = "╠"
RT2: str = "╣"
UT2: str = "╦"
DT2: str = "╩"
CROSS2: str = "╬"

# =============================================================================
# BLOCK CHARACTERS
# =============================================================================

# Density levels (sparse → dense)
D1: str = "░"
D2: str = "▒"
D3: str = "█"

# Vertical resolution doubling
UPPER: str = "▀"   # Upper half-block
LOWER: str = "▄"   # Lower half-block

# Braille dot matrix (2-wide × 4-tall = 8 pixels per char)
BRAILLE_OFFSET: int = 0x2800
BRAILLE_DOTS: tuple = (
    "⠀", "⠁", "⠂", "⠃", "⠄", "⠅", "⠆", "⠇", "⠈", "⠉", "⠊", "⠋", "⠌", "⠍", "⠎", "⠏",
    "⠐", "⠑", "⠒", "⠓", "⠔", "⠕", "⠖", "⠗", "⠘", "⠙", "⠚", "⠛", "⠜", "⠝", "⠞", "⠟",
    "⠠", "⠡", "⠢", "⠣", "⠤", "⠥", "⠦", "⠧", "⠨", "⠩", "⠪", "⠫", "⠬", "⠭", "⠮", "⠯",
    "⠰", "⠱", "⠲", "⠳", "⠴", "⠵", "⠶", "⠷", "⠸", "⠹", "⠺", "⠻", "⠼", "⠽", "⠾", "⠿",
    "⡀", "⡁", "⡂", "⡃", "⡄", "⡅", "⡆", "⡇", "⡈", "⡉", "⡊", "⡋", "⡌", "⡍", "⡎", "⡏",
    "⡐", "⡑", "⡒", "⡓", "⡔", "⡕", "⡖", "⡗", "⡘", "⡙", "⡚", "⡛", "⡜", "⡝", "⡞", "⡟",
    "⡠", "⡡", "⡢", "⡣", "⡤", "⡥", "⡦", "⡧", "⡨", "⡩", "⡪", "⡫", "⡬", "⡭", "⡮", "⡯",
    "⡰", "⡱", "⡲", "⡳", "⡴", "⡵", "⡶", "⡷", "⡸", "⡹", "⡺", "⡻", "⡼", "⡽", "⡾", "⡿",
    "⢀", "⢁", "⢂", "⢃", "⢄", "⢅", "⢆", "⢇", "⢈", "⢉", "⢊", "⢋", "⢌", "⢍", "⢎", "⢏",
    "⢐", "⢑", "⢒", "⢓", "⢔", "⢕", "⢖", "⢗", "⢘", "⢙", "⢚", "⢛", "⢜", "⢝", "⢞", "⢟",
    "⢠", "⢡", "⢢", "⢣", "⢤", "⢥", "⢦", "⢧", "⢨", "⢩", "⢪", "⢫", "⢬", "⢭", "⢮", "⢯",
    "⢰", "⢱", "⢲", "⢳", "⢴", "⢵", "⢶", "⢷", "⢸", "⢹", "⢺", "⢻", "⢼", "⢽", "⢾", "⢿",
    "⣀", "⣁", "⣂", "⣃", "⣄", "⣅", "⣆", "⣇", "⣈", "⣉", "⣊", "⣋", "⣌", "⣍", "⣎", "⣏",
    "⣐", "⣑", "⣒", "⣓", "⣔", "⣕", "⣖", "⣗", "⣘", "⣙", "⣚", "⣛", "⣜", "⣝", "⣞", "⣟",
    "⣠", "⣡", "⣢", "⣣", "⣤", "⣥", "⣦", "⣧", "⣨", "⣩", "⣪", "⣫", "⣬", "⣭", "⣮", "⣯",
    "⣰", "⣱", "⣲", "⣳", "⣴", "⣵", "⣶", "⣷", "⣸", "⣹", "⣺", "⣻", "⣼", "⣽", "⣾", "⣿",
    "⣿"
)

# =============================================================================
# SPARKLINE CHARACTERS
# =============================================================================

SPARKLINE: str = " ▁▂▃▄▅▆▇█"  # 8 levels, single line

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def rgb(r: int, g: int, b: int) -> str:
    """Build a truecolor RGB string for Rich markup."""
    return f"#{r:02x}{g:02x}{b:02x}"


def gradient_color(position: float) -> str:
    """
    Return a color along the thermal gradient.

    Args:
        position: Float 0.0 (amber) → 1.0 (red)

    Returns:
        Hex color string
    """
    if position < 0.5:
        # amber → orange
        t = position * 2
        r = int(0xf5 + (0xff - 0xf5) * t)
        g = int(0xb7 + (0x88 - 0xb7) * t)
        b = int(0x31 + (0x00 - 0x31) * t)
    else:
        # orange → red
        t = (position - 0.5) * 2
        r = int(0xff + (0xff - 0xff) * t)
        g = int(0x88 + (0x33 - 0x88) * t)
        b = int(0x00 + (0x33 - 0x00) * t)
    return rgb(r, g, b)
