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
