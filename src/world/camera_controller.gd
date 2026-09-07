class_name CameraController
extends Camera2D
## Screen-flip camera. The level is a grid of 400x240 screens; crossing an edge
## slides the view one whole screen while the simulation is frozen — the way
## early DOS platformers scrolled. Smooth follow is available as a setting.

const SLIDE_TIME := 0.12

signal screen_changed(screen: Vector2i)

var world: TileWorld = null
var target: Node2D = null
var screen := Vector2i.ZERO
var screens := Vector2i(1, 1)
var flip_mode := true
## Set while a screen-locked encounter (a boss) is running.
var locked := false
var _sliding := false

func setup(w: TileWorld, t: Node2D) -> void:
	world = w
	target = t
	anchor_mode = Camera2D.ANCHOR_MODE_FIXED_TOP_LEFT
	ignore_rotation = true
	screens = Screen.count_for(w.pixel_width(), w.pixel_height())
	flip_mode = bool(SaveManager.setting("screen_flip", true))
	snap_to_target()

func screen_of(p: Vector2) -> Vector2i:
	return Screen.index_of(p, screens)

func screen_origin(s: Vector2i) -> Vector2:
	return Screen.origin(s)

func view_rect() -> Rect2:
	if flip_mode:
		return Screen.rect(screen)
	return Rect2(position, Vector2(Screen.W, Screen.H))

func snap_to_target() -> void:
	if target == null:
		return
	if flip_mode:
		screen = screen_of(_target_point())
		position = screen_origin(screen)
	else:
		position = _clamped_follow()
	screen_changed.emit(screen)

func _target_point() -> Vector2:
	if target is Actor:
		return (target as Actor).center()
	return target.position

func _clamped_follow() -> Vector2:
	var c := _target_point()
	var p := c - Vector2(Screen.W, Screen.H) * 0.5
	p.x = clampf(p.x, 0.0, maxf(0.0, world.pixel_width() - Screen.W))
	p.y = clampf(p.y, 0.0, maxf(0.0, world.pixel_height() - Screen.H))
	return p.round()

func _physics_process(delta: float) -> void:
	if target == null or world == null:
		return
	if not flip_mode:
		position = position.lerp(_clamped_follow(), 1.0 - pow(0.001, delta)).round()
		return
	if _sliding or locked:
		return
	var s := screen_of(_target_point())
	if s != screen:
		_slide_to(s)

func _slide_to(s: Vector2i) -> void:
	_sliding = true
	# Freezing the sim during the slide is what makes it read as a screen flip
	# rather than a fast scroll — enemies and the player hold their pose.
	Game.sim_paused = true
	screen = s
	var t := create_tween()
	t.tween_property(self, "position", screen_origin(s), SLIDE_TIME)\
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	await t.finished
	position = screen_origin(s)
	_sliding = false
	Game.sim_paused = false
	screen_changed.emit(s)
