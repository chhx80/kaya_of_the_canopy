class_name CameraMath
extends RefCounted
## The follow camera's geometry, kept out of CameraController so the headless
## `--script` tier (no autoloads, no scene tree) can test it — the same reason
## Screen exists. Everything here is pure and works in world pixels.

## Where a view of `size` may sit inside `bounds` (the level, or a boss arena).
## A bounds narrower than the view pins the view to its left/top edge, which is
## what the level clamp always did for a level smaller than a screen.
static func clamp_view(p: Vector2, bounds: Rect2, size: Vector2) -> Vector2:
	return Vector2(
		clampf(p.x, bounds.position.x, maxf(bounds.position.x, bounds.end.x - size.x)),
		clampf(p.y, bounds.position.y, maxf(bounds.position.y, bounds.end.y - size.y)))

## The vertical the view centres on. `floor_y` is where she last stood; inside a
## band around it nothing moves, so a jump does not bounce the world. Climb above
## the band (a tall vine, a bird's flight) or fall below it and the view follows
## from the band's edge, without a jump.
static func anchored_y(c_y: float, floor_y: float, band_up: float, band_down: float) -> float:
	if c_y < floor_y - band_up:
		return c_y + band_up
	if c_y > floor_y + band_down:
		return c_y - band_down
	return floor_y

## The whole-pixel view for a smoothed camera at `base` following `target`.
##
## Rounding the camera and the target independently makes the player shimmer by
## a pixel against the screen whenever the follow lag has a fractional part —
## the camera's rounding and hers flip on different frames. Rounding the
## *distance between them* instead keeps her on the same screen pixel while the
## camera tracks her, and costs nothing when the camera is still: for a whole-
## pixel `base` this returns `base` exactly.
##
## Rounds half *up* rather than with `round()`, which rounds half away from
## zero: with that, a gap of -109.5 and a target at 10.5 round in opposite
## directions and a still camera gets nudged a pixel. floor(x + 0.5) makes the
## whole-pixel case exact for every sign. (Actors draw at `pos.round()`, which
## agrees with this everywhere a body can be: positive coordinates.)
static func snap(base: Vector2, target: Vector2) -> Vector2:
	return _half_up(target) - _half_up(target - base)

static func _half_up(v: Vector2) -> Vector2:
	return (v + Vector2(0.5, 0.5)).floor()

## The hard zone. Smoothing lags by speed / rate, and something fast enough (a
## thermal, a long fall) outruns any rate gentle enough to look calm — the tape
## audit measured Kaya leaving the view on four levels. So after smoothing, the
## view is pushed just far enough that `target` sits at least `margin` inside
## each edge. Below that speed this never acts; above it the view moves exactly
## as fast as she does, which is the least it can do and still keep her.
static func keep_in(view_pos: Vector2, size: Vector2, target: Vector2, margin: Vector2) -> Vector2:
	var p := view_pos
	p.x = clampf(p.x, target.x - size.x + margin.x, target.x - margin.x)
	p.y = clampf(p.y, target.y - size.y + margin.y, target.y - margin.y)
	return p

## The arena entry ease: sine in-out, so the pan into a boss arena starts and
## lands softly instead of snapping or lurching.
static func ease(t: float) -> float:
	var k := clampf(t, 0.0, 1.0)
	return 0.5 - 0.5 * cos(k * PI)

## Exponential approach factor for a per-second rate, frame-rate independent.
static func approach(rate: float, delta: float) -> float:
	return 1.0 - exp(-rate * delta)
