// terminal-glow.glsl
// Subtle bloom/glow effect for Ghostty
// Makes amber text feel luminous with minimal performance impact.
// Copy to ~/.config/ghostty/shaders/ and set custom-shader in ghostty config.

#i channel0 "texture"  // Terminal texture (required)

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    vec4 col = texture(iChannel0, uv);

    // Sample neighboring pixels for bloom
    vec2 texel = 1.0 / iResolution.xy;
    vec4 bloom = vec4(0.0);
    float bloomRadius = 2.0;

    for (float x = -bloomRadius; x <= bloomRadius; x += 1.0) {
        for (float y = -bloomRadius; y <= bloomRadius; y += 1.0) {
            vec2 offset = vec2(x, y) * texel;
            vec4 sample = texture(iChannel0, uv + offset);
            float weight = 1.0 / (1.0 + dot(vec2(x, y), vec2(x, y)));
            bloom += sample * weight;
        }
    }

    // Only bloom bright (non-background) pixels
    float brightness = dot(col.rgb, vec3(0.299, 0.587, 0.114));
    float bloomMask = smoothstep(0.1, 0.4, brightness);

    // Amber-tinted bloom for Hermes theme
    vec3 amberBloom = vec3(0.96, 0.72, 0.19) * 0.15;
    bloom.rgb = mix(bloom.rgb, bloom.rgb * amberBloom * 2.0, 0.5);

    // Blend original + bloom
    col.rgb += bloom.rgb * bloomMask * 0.15;

    // Very subtle vignette
    vec2 vig = uv * (1.0 - uv);
    float vignette = pow(vig.x * vig.y * 15.0, 0.3);
    col.rgb *= 0.95 + 0.05 * vignette;

    fragColor = col;
}
