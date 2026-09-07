class_name InputState
extends RefCounted
## One frame of intent. Actors read this, never `Input` directly, so touch
## controls, gamepads and the dev capture harness are interchangeable.

var left := false
var right := false
var up := false
var down := false
var jump := false           ## held
var jump_pressed := false   ## rising edge this tick
var jump_released := false
var attack := false
var attack_pressed := false

var _prev_jump := false
var _prev_attack := false

func poll() -> void:
	_prev_jump = jump
	_prev_attack = attack
	left = Input.is_action_pressed(&"move_left")
	right = Input.is_action_pressed(&"move_right")
	up = Input.is_action_pressed(&"move_up")
	down = Input.is_action_pressed(&"move_down")
	jump = Input.is_action_pressed(&"jump")
	attack = Input.is_action_pressed(&"attack")
	jump_pressed = jump and not _prev_jump
	jump_released = _prev_jump and not jump
	attack_pressed = attack and not _prev_attack

func clear() -> void:
	_prev_jump = jump
	_prev_attack = attack
	left = false; right = false; up = false; down = false
	jump = false; attack = false
	jump_pressed = false; jump_released = false; attack_pressed = false

func axis_x() -> float:
	return (1.0 if right else 0.0) - (1.0 if left else 0.0)

func axis_y() -> float:
	return (1.0 if down else 0.0) - (1.0 if up else 0.0)
