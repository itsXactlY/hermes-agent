// crt-amber.glsl
// Amber CRT phosphor simulation for Ghostty
// Renders warm amber (#f5b731) on dark with scanlines, curvature, and glow.
// Copy to ~/.config/ghostty/shaders/ and set custom-shader in ghostty config.

#i channel0 "texture"  // Terminal texture (required)

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    // Normalized coordinates
    vec2 uv = fragCoord / iResolution.xy;

    // CRT curvature (barrel distortion)
    vec2 centered = uv * 2.0 - 1.0;
    float dist = dot(centered, centered);
    centered *= 1.0 + dist * 0.05;
    vec2 curved = (centered + 1.0) / 2.0;

    // Sample terminal texture with curvature offset
    vec4 col = texture(iChannel0, curved);

    // Amber phosphor color shift
    // Original text is white/gray — tint to amber
    float gray = dot(col.rgb, vec3(0.299, 0.587, 0.114));
    vec3 amber = vec3(0.96, 0.72, 0.19);  // #f5b731
    col.rgb = mix(col.rgb, gray * amber, 0.85);

    // Scanlines
    float scanline = sin(fragCoord.y * 1.5) * 0.08;
    col.rgb -= scanline;

    // Horizontal line glow (phosphor persistence simulation)
    float glow = sin(fragCoord.y * 0.5 + iTime * 2.0) * 0.02;
    col.rgb += vec3(glow * 0.15, glow * 0.1, 0.0);

    // Vignette (subtle darkening at edges)
    vec2 vig = uv * (1.0 - uv);
    float vignette = vig.x * vig.y * 15.0;
    vignette = pow(vignette, 0.25);
    col.rgb *= vignette;

    // Subtle flicker
    float flicker = 1.0 + 0.01 * sin(iTime * 60.0);
    col.rgb *= flicker;

    fragColor = col;
}
