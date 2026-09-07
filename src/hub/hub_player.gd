class_name HubPlayer
extends Actor
## Kaya on the overworld: top-down, eight directions, no gravity.

const SPEED := 74.0
const ACCEL := 900.0
const FRICTION := 1200.0

var input := InputState.new()
var control_enabled := true
var sprite: Sprite2D = null
var _anim_t := 0.0
var _anim_i := 0
var _frame := Vector2i(16, 24)

func _ready() -> void:
	box = Vector2(10, 10)          ## feet-only box, so you can walk "behind" trees
	sprite = Sprite2D.new()
	sprite.centered = false
	sprite.region_enabled = true
	sprite.texture = load("res://assets/sprites/kaya_human.png")
	sprite.offset = Vector2(-3, -14)
	add_child(sprite)
	_sync_render_position()

func _physics_process(delta: float) -> void:
	if Game.sim_paused or not control_enabled:
		input.clear()
		_sync_render_position()
		return
	input.poll()
	var want := Vector2(input.axis_x(), input.axis_y())
	if want.length() > 1.0:
		want = want.normalized()
	if want.length() > 0.01:
		vel = vel.move_toward(want * SPEED, ACCEL * delta)
		if absf(want.x) > 0.01:
			facing = 1 if want.x > 0.0 else -1
	else:
		vel = vel.move_toward(Vector2.ZERO, FRICTION * delta)

	# Top-down: resolve both axes as walls, no gravity and no one-ways.
	var r := aabb()
	r = TileCollision.move_x(world, r, vel.x * delta).rect
	r = TileCollision.move_y(world, r, vel.y * delta).rect
	pos = r.position

	_animate(delta)
	_sync_render_position()

func _animate(delta: float) -> void:
	var moving := vel.length() > 8.0
	var frames := [1, 2, 3, 2] if moving else [0]
	if moving:
		_anim_t += delta
		while _anim_t >= 1.0 / 10.0:
			_anim_t -= 1.0 / 10.0
			_anim_i += 1
	else:
		_anim_i = 0
	var f := int(frames[_anim_i % frames.size()])
	sprite.region_rect = Rect2(f * _frame.x, 0, _frame.x, _frame.y)
	sprite.flip_h = facing < 0
	sprite.offset.x = -3.0 if facing > 0 else -(float(_frame.x) - 3.0 - box.x)
