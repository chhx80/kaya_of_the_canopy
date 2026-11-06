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
var _frame := Vector2i(24, 28)     ## kaya_hub.png cell, tools/art/kaya40.py HUB_W/H

func _ready() -> void:
	box = Vector2(10, 10)          ## feet-only box, so you can walk "behind" trees
	sprite = Sprite2D.new()
	sprite.centered = false
	sprite.region_enabled = true
	# The new Kaya drawn at the overworld's scale: the platformer's 40 px sprite
	# would stand taller than the huts on a top-down map. tools/art/kaya40.py.
	sprite.texture = load("res://assets/sprites/kaya_hub.png")
	sprite.offset = Vector2(-_side_pad(), -float(_frame.y) + box.y)
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
	# Frames 2-9 of kaya_hub.png are the eight-frame run cycle; 0 is the idle.
	var frames := [2, 3, 4, 5, 6, 7, 8, 9] if moving else [0]
	if moving:
		_anim_t += delta
		while _anim_t >= 1.0 / 12.0:
			_anim_t -= 1.0 / 12.0
			_anim_i += 1
	else:
		_anim_i = 0
	var f := int(frames[_anim_i % frames.size()])
	sprite.region_rect = Rect2(f * _frame.x, 0, _frame.x, _frame.y)
	sprite.flip_h = facing < 0
	sprite.offset.x = -_side_pad() if facing > 0 else -(float(_frame.x) - _side_pad() - box.x)

## Cell columns to the left of the foot box when she faces right. The cell is
## drawn centred on her feet, so this is the same both ways round.
func _side_pad() -> float:
	return (float(_frame.x) - box.x) * 0.5
