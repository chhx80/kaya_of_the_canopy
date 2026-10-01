shader_type canvas_item;
// Phase D, docs/plan-art-motion.md: the scene fade's pixel-dissolve mask.
//
// Applied to Main's full-window Fade/Rect (src/core/main.gd). The rect's own
// `color` stays flat opaque black for the whole transition; this shader is
// what reveals it, one ordered-dither threshold band at a time, instead of a
// smooth alpha blend. `progress` is quantised into 4 steps by the caller
// (main.gd's _dissolve_progress()), which is what makes this a "4-frame"
// effect rather than a continuous fade — the same vocabulary as the game's
// other one-shots (a particle burst's "4 frames" at some fps).
//
// The matrix is tools/art/palette.py's BAYER, unchanged, so a UI dissolve
// ages exactly like the dithering every piece of art in the game already
// uses — "in keeping with the palette engine's dithering identity."

uniform float progress : hint_range(0.0, 1.0) = 0.0; // 0 = fully hidden, 1 = fully revealed
uniform float cell_px : hint_range(1.0, 8.0) = 1.0;   // dissolve grain, in LOGICAL (400x240) pixels
uniform vec2 logical_size = vec2(400.0, 240.0);

const float BAYER[16] = float[16](
	0.0, 8.0, 2.0, 10.0,
	12.0, 4.0, 14.0, 6.0,
	3.0, 11.0, 1.0, 9.0,
	15.0, 7.0, 13.0, 5.0
);

void fragment() {
	vec2 logical_px = SCREEN_UV * logical_size;
	vec2 cell = floor(logical_px / cell_px);
	int bx = int(mod(cell.x, 4.0));
	int by = int(mod(cell.y, 4.0));
	float threshold = (BAYER[by * 4 + bx] + 0.5) / 16.0;
	float revealed = step(threshold, progress);
	COLOR.a = COLOR.a * (1.0 - revealed);
}
