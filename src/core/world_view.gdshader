shader_type canvas_item;
// The HD pass (docs/plan-hd.md): the world's render target, shown at whatever
// size fits the device exactly, with pixel edges kept crisp.
//
// Sharp bilinear. Plain nearest at a fractional scale (6.4 device pixels per
// world unit on a phone) makes some texels a pixel wider than their
// neighbours, which reads as wobble when the view scrolls; plain bilinear
// blurs. This samples each texel's interior as flat colour and blends only in
// the one-pixel seam between two texels, so every texel is the same width and
// its edge is at most one pixel soft. The texture must be sampled LINEAR
// (main.gd sets the filter on the node).
//
// `region` is the part of the render target the camera is showing, in texels:
// the target is sized for a whole boss arena and the exploring view uses less
// of it. Sampling is clamped inside it so the seam blend never reaches the
// unpainted texels beyond its edge.

uniform vec4 region = vec4(0.0, 0.0, 616.0, 368.0); // x, y, w, h in texels

void fragment() {
	vec2 tex_size = 1.0 / TEXTURE_PIXEL_SIZE;
	vec2 texel = UV * tex_size;
	// Device pixels per texel along each axis, measured rather than passed in,
	// so it is right mid-zoom and on every device without a uniform to keep
	// in step.
	vec2 scale = max(vec2(1.0), 1.0 / max(fwidth(texel), vec2(1e-5)));
	vec2 base = floor(texel);
	vec2 off = fract(texel) - 0.5;
	vec2 inner = 0.5 - 0.5 / scale;
	vec2 f = (off - clamp(off, -inner, inner)) * scale + 0.5;
	vec2 t = base + f;
	t = clamp(t, region.xy + 0.5, region.xy + region.zw - 0.5);
	COLOR = texture(TEXTURE, t * TEXTURE_PIXEL_SIZE);
}
