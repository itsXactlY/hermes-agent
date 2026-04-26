# Cutting-Edge Terminal Visual Capabilities Research (2025-2026)

## Research Date: April 2026
## Status: ACTIVE — Technology rapidly evolving

---

## 1. GHOSTTY — GPU SHADERS IN TERMINAL

**Ghostty** (50,929 stars) is the reference implementation for shader-accelerated terminal rendering. It natively supports custom GLSL fragment shaders via a simple config directive.

### Configuration
```bash
# In ~/.config/ghostty/config
custom-shader = ~/.config/ghostty/shaders/my-effect.glsl
```

### Shader Entry Point
```glsl
void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    // Shadertoy-compatible uniforms available:
    // iTime, iResolution, iMouse, iFrame, iTimeDelta, iFrameRate, iDate
}
```

### Shader Ecosystem (github.com/hackr-sh/ghostty-shaders — 1,259 stars)
35+ effects ready to use:

| Category | Effects |
|----------|---------|
| CRT/Retro | crt.glsl, bettercrt.glsl, in-game-crt.glsl, retro-terminal.glsl |
| Matrix | inside-the-matrix.glsl, matrix-hallway.glsl |
| Galaxy/Space | galaxy.glsl, starfield.glsl, starfield-colors.glsl |
| Fire/Smoke | sparks-from-fire.glsl, smoke-and-ghost.glsl, fireworks.glsl |
| Water | underwater.glsl, water.glsl |
| Glitch | glitchy.glsl, glow-rgbsplit-twitchy.glsl |
| Other | bloom.glsl, dither.glsl, spotlight.glsl, gradient-background.glsl |

---

## 2. TERMGL — SHADERTOY IN YOUR TERMINAL

**termgl** (github.com/Cubified/termgl) renders any Shadertoy-compatible fragment shader in a terminal.

### How It Works
- Creates an invisible GLFW/OpenGL context
- Renders any Shadertoy shader (copy-paste the GLSL)
- Converts pixel data to ANSI escape sequences
- Multi-threaded: render thread + input thread separately

### Building
```bash
git clone https://github.com/Cubified/termgl.git
cd termgl
./configure --with-pthreads && make
./termgl demos/1-basic.frag
```

### Compatibility
Works in any terminal — best results in GPU-accelerated terminals (Kitty, Alacritty, Ghostty).

---

## 3. TERMINAL GRAPHICS LIBRARIES

### Chafa (4,599 stars) — Terminal Graphics for the 21st Century
**Repo:** github.com/hpjansson/chafa
- Converts images/video to terminal output
- Supports: symbols, half-blocks, braille, sixel, Kitty protocol, iTerm2 protocol
- Best-in-class Unicode/braille rendering
- Usage: `chafa image.png` or `chafa video.mp4`

### Notcurses (4,466 stars) — Blingful Character Graphics
**Repo:** github.com/dankamongmen/notcurses
- C library for TUI with pixel-level control
- Supports: sixel, Kitty, iTerm2 image protocols
- Real-time video playback in terminal

### timg (2,600 stars) — Terminal Image & Video Viewer
**Repo:** github.com/hzeller/timg
- Renders images, videos, PDFs, SVGs in terminal
- Braille/quadrant character rendering fallback

### viu (3,155 stars) — Terminal Image Viewer
**Repo:** github.com/atanunq/viu
- Native Kitty and iTerm2 graphics protocol
- Animated GIF support (Rust-based, fast)

### lsix (4,156 stars) — Like `ls` but for Images
**Repo:** github.com/hackerb9/lsix
- Shows image thumbnails using sixel protocol

---

## 4. UNICODE/BRAILLE ART TECHNIQUES

### Character Density Levels
```
Blocks:    ░▒▓█
Braille:   ⠀⠁⠃⠇⠏⠟⠿⡿⣿
Quadrants: ▘▖▗▝▞▟▌▐█
Lines:     ─│┌┐└┘├┤┬┴┼
Shades:    ░▒▓ (25% 50% 75%)
```

### Braille Rendering (2x4 pixel grid per character)
Each braille character = 2-wide × 4-tall = **8 pixels** per character cell.
This gives **4x the resolution** of basic block characters.
Used by chafa, notcurses, and terminal image viewers.

### Half-Block Technique
Uses `▄` `▀` `█` characters to achieve **2x vertical resolution** within one character row.

### Quarter-Block Technique
Uses `▘▖▗▝` characters for **2x2 sub-character resolution**.

---

## 5. TERMINAL ANIMATION & EFFECTS

### Textual Framework — Full TUI with Animation
- `widget.animate(attribute, value, duration=, speed=)` — programmatic easing
- `reactive` variables auto-update UI when changed
- `set_interval()` or `set_timer()` for frame-based updates
- `auto_refresh = 1/30` for 30fps rendering
- Custom `RenderableType` classes using Rich under the hood

### Rich Live — Real-Time Updating Panels
```python
from rich.live import Live
with Live(get_renderable, refresh_per_second=4) as live:
    while True:
        time.sleep(0.25)  # Update data, Live re-renders automatically
```

### Key Libraries
| Library | Stars | Purpose |
|---------|-------|---------|
| cli-spinners | 2,842 | 60+ spinner animations |
| ora | 9,665 | Elegant terminal spinners |
| slides | 11,445 | Terminal presentations |
| vhs | 19,388 | Terminal video recorder |
| FTXUI | 9,954 | C++ TUI with canvas + animation |

### TermCaster — Terminal Raycaster
**Repo:** github.com/tmpstpdwn/TermCaster
- Wolfenstein-style raycaster rendered to terminal
- Pure terminal implementation

---

## 6. MODERN TERMINAL EMULATORS

| Terminal | GPU | Shaders | Image Protocol | Notes |
|----------|-----|---------|----------------|-------|
| **Ghostty** | Native | GLSL native | Kitty/iTerm2 | macOS + Linux, fastest |
| **Kitty** | OpenGL | Custom | Highest fidelity | Very active development |
| **WezTerm** | WebGPU/OpenGL | Lua-configurable | Yes | Lua scripting |
| **Alacritty** | OpenGL | No | No (by design) | Fastest raw text |
| **Foot** | GPU | Via widgets | Sixel/Kitty | Wayland-native |

---

## 7. QUICK-START COMMANDS

```bash
# Install chafa
sudo pacman -S chafa        # Arch
sudo apt install chafa       # Debian/Ubuntu

# Install termgl
git clone https://github.com/Cubified/termgl.git
cd termgl && ./configure --with-pthreads && make
./termgl demos/1-basic.frag

# Install viu
cargo install viu

# Install slides
go install github.com/maaslalani/slides@latest

# Install vhs (terminal recorder)
go install github.com/charmbracelet/vhs@latest

# Get Ghostty shaders
git clone --depth 1 https://github.com/hackr-sh/ghostty-shaders

# Python deps for dashboard
pip install textual rich psutil
```

---

## 8. RECOMMENDED STACK FOR HERMES

### NOW (Alacritty + i3)
- `chafa` for image/video viewing
- `viu` for image protocol display
- `notcurses` demos for rich TUI
- `btop` with custom hermes-amber theme
- tmux status bar with amber theme
- Custom Python dashboard via Textual + Rich

### FUTURE (Ghostty)
- Native GLSL shaders for CRT/matrix effects
- GPU-accelerated rendering
- Custom font rendering with ligatures
- Full Shadertoy shader compatibility

### Migration Path
1. Install ghostty alongside Alacritty
2. Copy shaders from hackr-sh/ghostty-shaders
3. Configure: `custom-shader = ~/.config/ghostty/shaders/crt-amber.glsl`
4. Amber-on-dark scheme works natively
