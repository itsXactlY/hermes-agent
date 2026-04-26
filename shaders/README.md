# Ghostty Shaders for Hermes Terminal

> GPU-accelerated terminal visual effects via Ghostty's native GLSL support.
> These shaders require [Ghostty](https://github.com/ghostty-org/ghostty) terminal emulator.

## Setup

```bash
# Create shaders directory
mkdir -p ~/.config/ghostty/shaders

# Copy desired shader
cp crt-amber.glsl ~/.config/ghostty/shaders/

# Edit ~/.config/ghostty/config and add:
custom-shader = ~/.config/ghostty/shaders/crt-amber.glsl
```

## Available Shaders

### crt-amber.glsl
Amber CRT phosphor simulation with scanlines, subtle screen curvature, and vignette.
Warm glow — matches the Hermes amber-on-dark palette perfectly.

### matrix-rain.glsl
Matrix-style falling code effect. Semi-transparent overlay — text remains readable.
Uses Shadertoy-compatible uniforms (iTime, iResolution, iMouse).

### terminal-glow.glsl
Subtle bloom/glow effect on all text. Makes amber characters feel luminous.
Low-performance impact, high aesthetic return.

## Shader Uniforms

Ghostty provides these Shadertoy-compatible uniforms:

| Uniform | Type | Description |
|---------|------|-------------|
| `iTime` | float | Seconds since start |
| `iResolution` | vec3 | (width, height, 1.0) |
| `iMouse` | vec4 | (x, y, click_x, click_y) |
| `iFrame` | int | Frame counter |
| `iTimeDelta` | float | Seconds since last frame |
| `iFrameRate` | float | Approximate FPS |
| `iSampleRate` | float | Audio sample rate (44100.0) |
| `iDate` | vec4 | (year, month, day, seconds) |

## Shader Development

The entry point for all shaders is:

```glsl
void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    // ... your effect here
}
```
