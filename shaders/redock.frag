#version 450

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform Glass {
    mat4 qt_Matrix;
    float qt_Opacity;
    float widthPx;
    float heightPx;
    float cornerRadius;
    float flareWidth;
    float flareHeight;
    vec3 glassTopRgb;
    vec3 glassBottomRgb;
    vec3 glassRimRgb;
    float topOpacity;
    float bottomOpacity;
} glass;

void main() {
    vec2 p = qt_TexCoord0 * vec2(glass.widthPx, glass.heightPx);
    float edgeX = min(p.x, glass.widthPx - p.x);
    float r = glass.cornerRadius;
    float flareTop = glass.heightPx - glass.flareHeight;

    // The top shoulders are convex. At the screen edge, the same silhouette
    // opens outward along two concave quarter ellipses.
    vec2 shoulder = vec2(glass.flareWidth + r - edgeX, r - p.y);
    float distance = length(max(shoulder, 0.0)) + min(max(shoulder.x, shoulder.y), 0.0) - r;
    if (p.y >= flareTop) {
        vec2 arc = vec2(edgeX / glass.flareWidth, (p.y - flareTop) / glass.flareHeight);
        distance = (1.0 - length(arc)) * glass.flareHeight;
    }
    float coverage = 1.0 - smoothstep(-0.6, 0.6, distance);
    float heightFraction = qt_TexCoord0.y;

    vec3 tint = mix(glass.glassTopRgb, glass.glassBottomRgb, smoothstep(0.0, 1.0, heightFraction));
    float bodyAlpha = mix(glass.topOpacity, glass.bottomOpacity, smoothstep(0.38, 1.0, heightFraction));
    vec4 body = vec4(tint * bodyAlpha, bodyAlpha);

    // A narrow edge reflection and a softer light falloff across the top.
    float reflection = exp(-p.y / 7.0) * 0.16;
    float rim = (1.0 - smoothstep(0.0, 1.55, abs(distance))) * mix(0.54, 0.12, heightFraction);
    float lightAlpha = min(1.0, reflection + rim);
    vec4 light = vec4(glass.glassRimRgb * lightAlpha, lightAlpha);
    fragColor = (light + body * (1.0 - lightAlpha)) * coverage * glass.qt_Opacity;
}
