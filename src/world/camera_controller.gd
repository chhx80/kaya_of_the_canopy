class_name CameraController
extends Camera2D
## Screen-flip camera. The level is a grid of 400x240 screens; crossing an edge
## slides the view one whole screen while the simulation is frozen — the way
## early DOS platformers scrolled. Smooth follow is available as a setting.
##
## Screen shake (Phase 5) is layered on as a *render offset only*: `base_pos` is
## the camera the flip logic reasons about, `position` is what the player sees.
## Nothing in here lets a shake change `screen`, because the screen index is
## derived from the player, never from where the camera happens to be.

const SLIDE_TIME := 0.12
## Hard ceiling on the shake offset. The tile cull carries one tile (16px) of
## margin, so an offset inside this can never expose an unpainted edge. This is
## a structural bound, not a tunable — amplitudes live in data/fx.json.
const MAX_SHAKE_PX := 8.0

signal screen_changed(screen: Vector2i)

var world: TileWorld = null
var target: Node2D = null
var screen := Vector2i.ZERO
var screens := Vector2i(1, 1)
var flip_mode := true
## Set while a screen-locked encounter (a boss) is running.
var locked := false
## Where the camera would sit with no shake. The slide tweens this, never
## `position`, so the two cannot fight over the same property.
var base_pos := Vector2.ZERO
var shake_offset := Vector2.ZERO
## Phase D, docs/plan-art-motion.md: the 2px landing dip. A second render
## offset, independent of `shake_offset`, so the existing shake-decay
## guarantees (tests/integration/integration_tests.gd's
## t_shake_moves_the_camera_and_puts_it_back_exactly) stay exactly as they
## were — nothing about this field changes what a shake does.
var dip_offset := Vector2.ZERO
var _sliding := false

# ---- follow mode (refit): centred with a look-ahead, vertically anchored to
# the floor she last stood on so a jump does not bounce the world.
const CAMERA_JSON := "res://data/camera.json"
var _cfg: Dictionary = {}
var _lead := 0.0
var _floor_y := 0.0

func setup(w: TileWorld, t: Node2D) -> void:
	world = w
	target = t
	anchor_mode = Camera2D.ANCHOR_MODE_FIXED_TOP_LEFT
	ignore_rotation = true
	screens = Screen.count_for(w.pixel_width(), w.pixel_height())
	flip_mode = bool(SaveManager.setting("screen_flip", true))
	_cfg = _load_cfg()
	_lead = 0.0
	_floor_y = _target_point().y
	snap_to_target()

func screen_of(p: Vector2) -> Vector2i:
	return Screen.index_of(p, screens)

func screen_origin(s: Vector2i) -> Vector2:
	return Screen.origin(s)

## The cull rect, which is deliberately the *unshaken* view: shaking must not
## make the renderer re-cull, or a shake would flicker the tile layers.
func view_rect() -> Rect2:
	if flip_mode:
		return Screen.rect(screen)
	return Rect2(base_pos, Vector2(Screen.W, Screen.H))

func is_sliding() -> bool:
	return _sliding

func snap_to_target() -> void:
	if target == null:
		return
	if flip_mode:
		screen = screen_of(_target_point())
		base_pos = screen_origin(screen)
	else:
		base_pos = _clamped_follow()
	_apply_position()
	screen_changed.emit(screen)

## The only way anything outside this script moves the camera off its screen.
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

func _apply_position() -> void:
	position = (base_pos + shake_offset + dip_offset).round()

func _target_point() -> Vector2:
	if target is Actor:
		return (target as Actor).center()
	return target.position

func _load_cfg() -> Dictionary:
	var f := FileAccess.open(CAMERA_JSON, FileAccess.READ)
	if f == null:
		return {}
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	return parsed if typeof(parsed) == TYPE_DICTIONARY else {}

func _num(key: String, fallback: float) -> float:
	return float(_cfg.get(key, fallback))

## Where the view wants to be centred: her centre, pushed ahead in the way she
## faces, and vertically on the floor she last stood on unless she has climbed
## or fallen out of a band around it. Jumping inside the band moves nothing.
func _focus() -> Vector2:
	var c := _target_point()
	var y := _floor_y
	var up := _num("air_band_up_px", 56.0)
	var down := _num("air_band_down_px", 8.0)
	if c.y < y - up:
		y = c.y + up
	elif c.y > y + down:
		y = c.y - down
	return Vector2(c.x + _lead, y)

func _clamped_follow() -> Vector2:
	var c := _focus()
	var p := c - Vector2(Screen.W, Screen.H) * 0.5
	p.x = clampf(p.x, 0.0, maxf(0.0, world.pixel_width() - Screen.W))
	p.y = clampf(p.y, 0.0, maxf(0.0, world.pixel_height() - Screen.H))
	return p.round()

## The slide tween drives `base_pos` on the idle clock, so the visible position
## is re-derived there too — otherwise a slide would only step at 60Hz.
func _process(_delta: float) -> void:
	_apply_position()

func _physics_process(delta: float) -> void:
	if target == null or world == null:
		return
	if not flip_mode:
		_track(delta)
		var goal := _clamped_follow()
		var kx := 1.0 - exp(-_num("follow_x_rate", 10.0) * delta)
		var ky := 1.0 - exp(-_num("follow_y_rate", 6.0) * delta)
		base_pos = Vector2(lerpf(base_pos.x, goal.x, kx), lerpf(base_pos.y, goal.y, ky))
		_apply_position()
		return
	if _sliding or locked:
		return
	var s := screen_of(_target_point())
	if s != screen:
		_slide_to(s)

## Follow-mode bookkeeping: ease the look-ahead toward her facing, and re-anchor
## the vertical to the floor whenever she is standing, climbing or swimming.
func _track(delta: float) -> void:
	if not (target is Actor):
		return
	var a := target as Actor
	var want := _num("lead_px", 24.0) * float(a.facing)
	_lead = lerpf(_lead, want, 1.0 - exp(-_num("lead_rate", 4.0) * delta))
	if a.on_floor or a.submerged() or a.on_ladder():
		_floor_y = a.center().y

func _slide_to(s: Vector2i) -> void:
	_sliding = true
	# Freezing the sim during the slide is what makes it read as a screen flip
	# rather than a fast scroll — enemies and the player hold their pose.
	Game.sim_paused = true
	screen = s
	var t := create_tween()
	t.tween_property(self, "base_pos", screen_origin(s), SLIDE_TIME)\
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	await t.finished
	base_pos = screen_origin(s)
	_apply_position()
	_sliding = false
	Game.sim_paused = false
	screen_changed.emit(s)
