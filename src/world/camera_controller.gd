class_name CameraController
extends Camera2D
## The game's camera: centred on Kaya and smoothed, with a look-ahead in the
## way she faces and a vertical anchor on the floor she last stood on, so a jump
## does not bounce the world, plus a vertical look-ahead that leads her down a
## long fall or up a sustained climb (never on an ordinary jump, never inside a
## boss arena). Clamped to the level, and locked inside a boss
## arena while the boss lives. Tunables in data/camera.json.
##
## It never freezes the simulation. The screen flip it replaced held the whole
## game still for 120 ms on every screen edge; nothing here touches
## `Game.sim_paused`, which now belongs to hitstop alone.
##
## Three positions, and only one of them is ever rounded:
## * `base_pos` — the smoothed camera, a float. All the follow maths is here.
## * `view_rect()` — the whole-pixel, *unshaken* view: what the tile cull, the
##   parallax and enemy wake-up reason about. A shake must never make the
##   renderer re-cull, or the tile layers would flicker.
## * `position` — what the player sees: the view plus the shake and dip offsets.
##
## The HD pass (docs/plan-hd.md): the view is Display.view_size() world units
## (308 x 184), not a screen. `zoom` is art_scale, always, so one world unit is
## that many texels in the world's render target; the view's *size* is what a
## boss arena changes. While locked, the view eases out until the whole arena
## is in it, and back in when the lock lets go, centred on itself both ways so
## the pull-back reads as the camera stepping back rather than sliding.

const CAMERA_JSON := "res://data/camera.json"
## Hard ceiling on the shake offset. The tile cull carries one tile (16px) of
## margin, so an offset inside this can never expose an unpainted edge. This is
## a structural bound, not a tunable — amplitudes live in data/fx.json.
const MAX_SHAKE_PX := 8.0

## The whole-pixel view moved. Emitted at most once per physics tick, and only
## when it actually changed, so a still camera costs the layers nothing.
signal view_changed(view: Rect2)

var world: TileWorld = null
var target: Node2D = null
## The overworld: no floor to anchor to and nowhere to look ahead to.
var topdown := false
## Set while a boss arena holds the camera. Level decides when; see lock_to().
var locked := false
var arena := Rect2()
var base_pos := Vector2.ZERO
var shake_offset := Vector2.ZERO
## Phase D, docs/plan-art-motion.md: the 2px landing dip. A second render
## offset, independent of `shake_offset`, so the shake-decay guarantees
## (tests/integration/integration_tests.gd's
## t_shake_moves_the_camera_and_puts_it_back_exactly) stay exactly as they
## were — nothing about this field changes what a shake does.
var dip_offset := Vector2.ZERO

var _cfg: Dictionary = {}
var _lead := 0.0
var _floor_y := 0.0
var _view := Vector2.ZERO
## Arena entry: 0 -> 1 over `arena_ease_s`, from where the camera was.
var _blend := 1.0
var _blend_from := Vector2.ZERO
## Arena pull-back: 0 = the explore view, 1 = the arena, eased in between.
## `_zoom_to` is the arena size it is easing toward, kept after unlock so the
## ease back in starts from the arena it left.
var _zoom := 0.0
var _zoom_to := Vector2.ZERO
var _size := Vector2.ZERO
## The vertical look-ahead: `_look` is the signed weight (-1 up .. +1 down)
## CameraMath.blend_look() takes, `_vy` her smoothed vertical speed, `_climb_t`
## CameraMath.climb_time()'s clock.
var _look := 0.0
var _vy := 0.0
var _climb_t := 0.0

func setup(w: TileWorld, t: Node2D, is_topdown: bool = false) -> void:
	world = w
	target = t
	topdown = is_topdown
	anchor_mode = Camera2D.ANCHOR_MODE_FIXED_TOP_LEFT
	ignore_rotation = true
	var k := float(Display.art_scale())
	zoom = Vector2(k, k)
	_cfg = _load_cfg()
	locked = false
	_zoom = 0.0
	_size = Display.view_size()
	snap_to_target()

## The cull rect: the whole-pixel view with no shake in it. Its size is the
## view's, which is the explore view except while a boss arena pulls it back.
func view_rect() -> Rect2:
	return Rect2(_view, _size)

## World units in view right now.
func view_size() -> Vector2:
	return _size

## The view's size for a pull-back of `z` (0..1) toward `arena_size`.
static func size_at(z: float, explore: Vector2, arena_size: Vector2) -> Vector2:
	return explore.lerp(arena_size, CameraMath.ease(z))

## Jump straight to where the camera wants to be: level start, a respawn, a
## teleport. The only discontinuity the camera ever makes.
func snap_to_target() -> void:
	if target == null or world == null:
		return
	_floor_y = _target_point().y
	_lead = _want_lead()
	_look = 0.0
	_vy = 0.0
	_climb_t = 0.0
	_blend = 1.0
	_zoom = 1.0 if locked else 0.0
	_update_size()
	base_pos = _goal()
	_apply_position()

## Hold the view inside `r` until unlock(). The pan into it is eased over
## `arena_ease_s` rather than snapped: walking into a boss arena should read as
## the room closing around you, not as a cut.
func lock_to(r: Rect2) -> void:
	locked = true
	arena = r
	_zoom_to = r.size
	_blend_from = base_pos
	var secs := _num("arena_ease_s", 0.6)
	_blend = 0.0 if secs > 0.0 else 1.0

func unlock() -> void:
	locked = false
	_blend = 1.0

## The bounds the view is heading for: the arena when locked, else the level.
func bounds() -> Rect2:
	if locked:
		return arena
	return level_bounds()

func level_bounds() -> Rect2:
	return Rect2(Vector2.ZERO, Vector2(world.pixel_width(), world.pixel_height()))

## True while the camera is still panning into an arena it has just locked to.
func is_entering_arena() -> bool:
	return locked and _blend < 1.0

## The only way anything outside this script moves the camera off its view.
## Clamped here as well as in Fx so a bad tunable cannot push the view off the
## painted area.
func set_shake(offset: Vector2) -> void:
	shake_offset = offset.limit_length(MAX_SHAKE_PX)
	_apply_position()

## Same bound as set_shake(), for the same reason: a render offset must never
## be able to expose an unpainted edge past the tile cull's margin.
func set_dip(offset: Vector2) -> void:
	dip_offset = offset.limit_length(MAX_SHAKE_PX)
	_apply_position()

func cfg_num(key: String, fallback: float) -> float:
	return _num(key, fallback)

func _physics_process(delta: float) -> void:
	if target == null or world == null or not is_instance_valid(target):
		return
	_track(delta)
	_ease_zoom(delta)
	var goal := _goal()
	if _blend < 1.0:
		_blend = minf(1.0, _blend + delta / maxf(0.001, _num("arena_ease_s", 0.6)))
		base_pos = _blend_from.lerp(goal, CameraMath.ease(_blend))
	else:
		var kx := CameraMath.approach(_num("follow_x_rate", 10.0), delta)
		var ky := CameraMath.approach(_follow_y_rate(), delta)
		base_pos = Vector2(lerpf(base_pos.x, goal.x, kx), CameraMath.limit_step(base_pos.y,
			lerpf(base_pos.y, goal.y, ky), _num("follow_y_max_speed", 480.0) * delta))
		var size := _size
		var m := Vector2(_num("keep_in_x_px", 48.0), _num("keep_in_y_px", 32.0))
		base_pos = CameraMath.clamp_view(
			CameraMath.keep_in(base_pos, size, _target_point(), m), bounds(), size)
	_apply_position()

func _apply_position() -> void:
	if world == null:
		position = (base_pos + shake_offset + dip_offset).round()
		return
	var v := base_pos.round()
	if target != null and is_instance_valid(target):
		v = CameraMath.snap(base_pos, _target_point())
	# Mid-pan into an arena the view is still allowed to stand outside it;
	# clamping to the arena there would be exactly the snap the ease is for.
	var hold := level_bounds() if is_entering_arena() else bounds()
	v = CameraMath.clamp_view(v, hold, _size)
	position = v + (shake_offset + dip_offset).round()
	if v != _view:
		_view = v
		view_changed.emit(view_rect())

func _target_point() -> Vector2:
	if target is Actor:
		return (target as Actor).center()
	return target.position

func _load_cfg() -> Dictionary:
	var f := FileAccess.open(CAMERA_JSON, FileAccess.READ)
	if f == null:
		push_warning("CameraController: no %s; using built-in fallbacks" % CAMERA_JSON)
		return {}
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	return parsed if typeof(parsed) == TYPE_DICTIONARY else {}

func _num(key: String, fallback: float) -> float:
	return float(_cfg.get(key, fallback))

func _want_lead() -> float:
	if topdown or not (target is Actor):
		return 0.0
	return _num("lead_px", 32.0) * float((target as Actor).facing)

## Where the view wants to be: centred on her focus, clamped to the bounds.
func _goal() -> Vector2:
	var c := _target_point()
	var focus := c
	if not topdown:
		var y := CameraMath.anchored_y(c.y, _floor_y,
			_num("air_band_up_px", 56.0), _num("air_band_down_px", 8.0))
		if not locked:
			y = CameraMath.blend_look(y, c.y, _vy, _look, _num("look_y_ahead_px", 30.0),
				_follow_y_rate(), _num("look_y_max_lag_px", 60.0))
		focus = Vector2(c.x + _lead, y)
	return CameraMath.clamp_view(focus - _size * 0.5, bounds(), _size)

## Step the pull-back toward the arena while locked and back out of it after,
## at the same pace as the pan into the arena. The view grows and shrinks
## about its centre: `base_pos` moves by half of each change.
func _ease_zoom(delta: float) -> void:
	var want := 1.0 if locked else 0.0
	if _zoom == want:
		return
	var secs := _num("arena_ease_s", 0.6)
	var step := 1.0 if secs <= 0.0 else delta / secs
	_zoom = move_toward(_zoom, want, step)
	var before := _size
	_update_size()
	base_pos += (before - _size) * 0.5
	if _blend < 1.0:
		_blend_from += (before - _size) * 0.5

func _update_size() -> void:
	var explore := Display.view_size()
	if _zoom_to == Vector2.ZERO:
		_zoom_to = explore
	_size = size_at(_zoom, explore, _zoom_to)

## Ease the look-ahead toward her facing, and re-anchor the vertical to the
## floor whenever she is standing, climbing or swimming.
func _track(delta: float) -> void:
	if topdown or not (target is Actor):
		_floor_y = _target_point().y
		return
	var a := target as Actor
	_lead = lerpf(_lead, _want_lead(), CameraMath.approach(_num("lead_rate", 4.0), delta))
	if a.on_floor or a.submerged() or a.on_ladder():
		_floor_y = a.center().y
	_track_look(a, delta)

## The vertical follow rate: quicker while the look-ahead leads, so the view
## can get ahead of a fall that only lasts a second (CameraMath.follow_rate()).
func _follow_y_rate() -> float:
	return CameraMath.follow_rate(_num("follow_y_rate", 6.0), _num("look_follow_y_rate", 12.0),
		_look)

## The vertical look-ahead's state: her smoothed speed, the climb clock, and
## the weight eased toward what CameraMath.look_mode() asks for, in at one
## rate and back out (on landing, or turning round) at another. Held at 0
## inside a boss arena, where the view is the arena.
func _track_look(a: Actor, delta: float) -> void:
	_vy = lerpf(_vy, a.vel.y, CameraMath.approach(_num("look_y_vel_rate", 8.0), delta))
	var swimming := a.submerged()
	_climb_t = CameraMath.climb_time(_climb_t, a.vel.y, a.on_floor or swimming,
		_num("look_climb_speed", 40.0), _num("look_climb_decay", 1.0), delta)
	var want := 0
	if not locked:
		want = CameraMath.look_mode(a.on_floor, swimming, a.center().y - _floor_y, a.vel.y,
			_climb_t, _num("look_fall_drop_px", 52.0), _num("look_fall_speed", 120.0),
			_num("look_climb_s", 0.6))
	var rate := _num("look_y_in_rate", 8.0)
	if want == 0 or (_look != 0.0 and signf(_look) != float(want)):
		rate = _num("look_y_out_rate", 2.0)
	_look = lerpf(_look, float(want), CameraMath.approach(rate, delta))
	if want == 0 and absf(_look) < 0.001:
		_look = 0.0
