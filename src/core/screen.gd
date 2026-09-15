class_name Screen
extends RefCounted
## The logical screen. Kept out of the Game autoload so the screen-flip maths is
## reachable from headless tests (a `--script` run has no autoloads).

const W := 400
const H := 240
const SIZE := Vector2i(W, H)

## How many whole screens a world of `px` pixels covers.
static func count_for(px_w: int, px_h: int) -> Vector2i:
	return Vector2i(maxi(1, ceili(float(px_w) / W)), maxi(1, ceili(float(px_h) / H)))

## Which screen a world point belongs to, clamped to the level.
static func index_of(p: Vector2, screens: Vector2i) -> Vector2i:
	return Vector2i(
		clampi(int(floor(p.x / W)), 0, screens.x - 1),
		clampi(int(floor(p.y / H)), 0, screens.y - 1))

static func origin(s: Vector2i) -> Vector2:
	return Vector2(s.x * W, s.y * H)

static func rect(s: Vector2i) -> Rect2:
	return Rect2(origin(s), Vector2(W, H))

# ---------------------------------------------------------------- device fit
## W x H is the size of one *world* screen and never changes — the screen-flip
## camera is built on it. The root viewport, by contrast, is as wide as the
## device: 400 on a 5:3 display, ~522 on a 19.5:9 phone. The world is drawn into
## a SubViewport of exactly W x H and centred, and the leftover margin is where
## the HUD and touch controls live — off the play area, against the physical
## edge where a thumb actually rests.

## Actual root viewport size in logical pixels.
static func ui_size(vp: Viewport) -> Vector2:
	if vp == null:
		return Vector2(W, H)
	return vp.get_visible_rect().size

## Where the W x H world view sits inside a root viewport of `ui` pixels.
## Pure, so tests/test_screen_flip.gd can check it without a scene tree.
static func world_rect_for(ui: Vector2) -> Rect2:
	return Rect2(((ui - Vector2(W, H)) * 0.5).floor(), Vector2(W, H))

## Where the W x H world view sits inside the root viewport.
static func world_rect_in_ui(vp: Viewport) -> Rect2:
	return world_rect_for(ui_size(vp))

## Width of one side margin. Zero on a display that matches the game's aspect.
static func margin(vp: Viewport) -> float:
	return maxf(0.0, (ui_size(vp).x - W) * 0.5)
