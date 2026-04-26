// matrix-rain.glsl
// Matrix-style falling code effect for Ghostty
// Semi-transparent overlay — terminal text stays readable.
// Copy to ~/.config/ghostty/shaders/ and set custom-shader in ghostty config.

#i channel0 "texture"  // Terminal texture (required)

float hash(float n) {
    return fract(sin(n) * 43758.5453);
}

float charHash(vec2 p, float time) {
    return hash(floor(p.x) * 12.34 + floor(p.y + time * 2.0) * 56.78);
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    // Sample base terminal texture
    vec4 col = texture(iChannel0, fragCoord / iResolution.xy);

    // Matrix rain coordinates
    vec2 uv = fragCoord / iResolution.xy;
    uv.y = 1.0 - uv.y;  // Flip Y (rain falls down)

    // Column position + falling speed variation
    float colX = uv.x * 80.0;
    float colTime = colX * 0.1 + iTime * 0.8;

    // Random brightness per column (some columns dimmer than others)
    float colBrightness = hash(floor(colX) * 0.137) * 0.6 + 0.4;

    // Trail length (brightness decay from head)
    float trailPos = fract(uv.y + colTime);
    float trail = smoothstep(0.0, 0.15, trailPos) * smoothstep(1.0, 0.3, trailPos);

    // Head bright flash
    float head = smoothstep(0.98, 1.0, trailPos) * 0.8;

    // Character randomization
    float charVal = charHash(vec2(colX, uv.y), iTime);
    float matrixIntensity = (head + trail * 0.5) * colBrightness;

    // Green/amber matrix color
    vec3 matrixCol = mix(
        vec3(0.1, 0.5, 0.05),   // Dark green trail
        vec3(0.7, 1.0, 0.3),   // Bright green head
        head
    );

    // Amber variation for Hermes theme
    matrixCol = mix(
        vec3(0.4, 0.3, 0.0),   // Dim amber trail
        vec3(1.0, 0.85, 0.3),  // Bright amber head
        head
    );

    // Blend matrix over terminal (10-35% opacity)
    float alpha = matrixIntensity * 0.25;
    col.rgb = mix(col.rgb, matrixCol, alpha);

    fragColor = col;
}
