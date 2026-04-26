# Hermes Terminal Themes
from terminal.themes.amber import AMBER
from terminal.themes.neural import NEURAL

THEMES: dict = {
    "amber": AMBER,
    "neural": NEURAL,
}


def get_theme(name: str):
    """Return theme palette by name. Falls back to amber."""
    return THEMES.get(name.lower(), AMBER)
