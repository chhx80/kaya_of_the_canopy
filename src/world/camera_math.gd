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

## The vertical look-ahead (HD pass, docs/plan-hd.md). Which way the view
## should lead her right now: +1 down, -1 up, 0 not at all.
##
## Down: she is falling (`vy` past `fall_speed`) and already `fall_drop` below
## the floor she last stood on. Measured from that floor, not from the apex, so
## a jump that lands where it took off, or on a ledge a few tiles down, never
## gets there: ordinary platforming does not bob the view.
##
## Up: she has been rising for `climb_secs` (see climb_time()). A jump rises
## for a fraction of a second; a flight, a wall climb, a vine or a thermal
## keeps on rising.
##
## Never while she stands, swims or holds a ladder going down: those re-anchor
## the view to her already.
static func look_mode(standing: bool, swimming: bool, below_floor: float, vy: float,
		climb_t: float, fall_drop: float, fall_speed: float, climb_secs: float) -> int:
	if standing or swimming:
		return 0
	if vy > fall_speed and below_floor > fall_drop:
		return 1
	if climb_t >= climb_secs:
		return -1
	return 0

## How long she has been climbing, as a leaky clock: it runs while she rises
## faster than `speed`, drains `decay` times as fast while she does not, and
## empties the moment she stands. Leaky rather than reset, because a frog
## climbing a wall rises in hops with a cling between them and a bird rises in
## flaps; reset on standing, because a staircase of jumps is not a climb.
static func climb_time(t: float, vy: float, standing: bool, speed: float, decay: float,
		delta: float) -> float:
	if standing:
		return 0.0
	if vy < -speed:
		return t + delta
	return maxf(0.0, t - delta * decay)

## The vertical the view centres on while it leads her: `ahead` past her centre
## in the direction `dir`, plus the follow lag at her (smoothed) speed `vy`.
## The follow is exponential at `follow_rate`, so at a steady speed it trails
## by exactly vy / follow_rate; leading the goal by that much puts her where
## `ahead` says rather than wherever the lag leaves her. The lead is capped at
## `max_lag` so a glitch in her speed cannot fling the view.
static func look_y(c_y: float, vy: float, dir: int, ahead: float, follow_rate: float,
		max_lag: float) -> float:
	var lag := clampf(vy / maxf(0.001, follow_rate), -max_lag, max_lag)
	return c_y + float(dir) * ahead + lag

## The vertical follow rate for a look-ahead weight `s`: the ordinary rate
## with no look, the quicker `fast` one with all of it, in proportion between.
## The goal and the follow lag it cancels (look_y()) must use the same number.
static func follow_rate(base: float, fast: float, s: float) -> float:
	return lerpf(base, fast, absf(s))

## Move `from` toward `to` but never by more than `max_step`. The smoothing's
## speed cap: an exponential follow moves fastest when it is furthest behind,
## which is exactly when a look-ahead switching on (or a thermal) has just
## moved the goal a long way. keep_in() runs after this and still holds her,
## so the cap can slow the view but never lose her.
static func limit_step(from: float, to: float, max_step: float) -> float:
	return from + clampf(to - from, -max_step, max_step)

## Blend the floor anchor into the look-ahead by a signed weight `s` in
## [-1, 1]: its sign is the direction, its size how far in. Passing through 0
## when the direction changes keeps the goal continuous.
static func blend_look(anchored: float, c_y: float, vy: float, s: float, ahead: float,
		follow_rate: float, max_lag: float) -> float:
	if s == 0.0:
		return anchored
	var dir := 1 if s > 0.0 else -1
	return lerpf(anchored, look_y(c_y, vy, dir, ahead, follow_rate, max_lag), absf(s))

## The approach to a boss arena (HD pass): the band `margin` deep above
## `arena`, as wide as it. Every arena is entered by a drop from above, and
## the lock only engages as her centre crosses the arena's top, mid-fall, so
## the pull-back that brings the arena floor into view arrived after she
## landed. A fall through this band starts the arena framing early. Only above:
## walking in from the side already has the floor in view.
static func approach_zone(arena: Rect2, margin: float) -> Rect2:
	return Rect2(arena.position.x, arena.position.y - margin, arena.size.x, arena.size.y + margin)

## Whether the camera frames the arena ahead of the lock this tick. It starts
## on a real fall (look_mode()'s test: `falling`) inside the band while armed,
## holds while she stays airborne and `near` it (the band grown by the release
## margin, so its rim does not thrash), and ends the moment she stands on
## something outside the arena or drifts off. Armed means she has been clear of
## the band since the camera last let go of the arena, so the release after a
## fight is exactly what it was. The lock itself takes over from here and is
## Level's to decide; this never starts or stops the fight.
static func approach_on(was_on: bool, armed: bool, in_zone: bool, near: bool, standing: bool,
		falling: bool) -> bool:
	if standing or not near:
		return false
	if was_on:
		return true
	return armed and in_zone and falling

## Re-arm the approach once she is clear of its band; disarm it while she is
## in it and the arena has just let her go.
static func approach_armed(armed: bool, near: bool) -> bool:
	return armed or not near
