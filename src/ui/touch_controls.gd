extends Control
## Floating virtual d-pad and two action buttons.
##
## It feeds the ordinary input actions with Input.action_press/release, so the
## rest of the game never learns that touch exists — `InputState` is the only
## thing anything reads.
##
## Left half: the stick appears wherever your thumb lands and follows it.
## Right half: Jump (lower-right) and Attack (above it), sized for a thumb.

const DEAD_ZONE := 9.0
const STICK_RADIUS := 26.0
const BTN_R := 21.0
const DIR_ACTIONS := [&"move_right", &"move_down", &"move_left", &"move_up"]

var enabled := true
var opacity := 0.5
var ui_scale := 1.0

var _stick_touch := -1
var _stick_origin := Vector2.ZERO
var _stick_pos := Vector2.ZERO
var _btn_touch := {}                 ## touch index -> action
var _held: Dictionary = {}           ## action -> true

@onready var _jump_centre := Vector2(Screen.W - 44, Screen.H - 40)
@onready var _attack_centre := Vector2(Screen.W - 88, Screen.H - 62)

func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	process_mode = Node.PROCESS_MODE_ALWAYS
	refresh_settings()
	Input.joy_connection_changed.connect(_on_joy_changed)
	_update_visibility()

func refresh_settings() -> void:
	opacity = float(SaveManager.setting("touch_opacity", 0.5))
	ui_scale = float(SaveManager.setting("touch_scale", 1.0))
	_jump_centre = Vector2(Screen.W - 44 * ui_scale, Screen.H - 40 * ui_scale)
	_attack_centre = Vector2(Screen.W - 88 * ui_scale, Screen.H - 62 * ui_scale)
	queue_redraw()

func _on_joy_changed(_device: int, _connected: bool) -> void:
	_update_visibility()

## A connected gamepad is always the better control scheme, so the overlay steps
## aside as soon as one appears.
func _update_visibility() -> void:
	var has_pad := not Input.get_connected_joypads().is_empty()
	var touch := DisplayServer.is_touchscreen_available()
	enabled = touch and not has_pad
	if not enabled:
		_release_all()
	visible = enabled
	queue_redraw()

func force_enable(on: bool) -> void:
	## Used by the dev capture harness to photograph the overlay on desktop.
	enabled = on
	visible = on
	queue_redraw()

# ---------------------------------------------------------------- input
func _input(event: InputEvent) -> void:
	if not enabled:
		return
	if event is InputEventScreenTouch:
		var t := event as InputEventScreenTouch
		if t.pressed:
			_begin(t.index, t.position)
		else:
			_end(t.index)
		get_viewport().set_input_as_handled()
	elif event is InputEventScreenDrag:
		var d := event as InputEventScreenDrag
		if d.index == _stick_touch:
			_stick_pos = d.position
			_apply_stick()
			queue_redraw()

func _begin(index: int, p: Vector2) -> void:
	var hit := _button_at(p)
	if hit != &"":
		_btn_touch[index] = hit
		_press(hit)
		_haptic()
		queue_redraw()
		return
	if p.x < Screen.W * 0.5 and _stick_touch == -1:
		_stick_touch = index
		_stick_origin = p
		_stick_pos = p
		queue_redraw()

func _end(index: int) -> void:
	if _btn_touch.has(index):
		_release(_btn_touch[index])
		_btn_touch.erase(index)
	if index == _stick_touch:
		_stick_touch = -1
		for a in DIR_ACTIONS:
			_release(a)
	queue_redraw()

func _button_at(p: Vector2) -> StringName:
	var r := BTN_R * ui_scale
	if p.distance_to(_jump_centre) <= r + 6.0:
		return &"jump"
	if p.distance_to(_attack_centre) <= r + 6.0:
		return &"attack"
	return &""

func _apply_stick() -> void:
	var v := _stick_pos - _stick_origin
	if v.length() < DEAD_ZONE:
		for a in DIR_ACTIONS:
			_release(a)
		return
	# Snap to eight directions so ladders and diagonals feel deliberate.
	var oct := int(round(v.angle() / (PI / 4.0))) & 7
	var octants: Dictionary = {
		0: [&"move_right"], 1: [&"move_right", &"move_down"], 2: [&"move_down"],
		3: [&"move_left", &"move_down"], 4: [&"move_left"],
		5: [&"move_left", &"move_up"], 6: [&"move_up"], 7: [&"move_right", &"move_up"],
	}
	var want: Array = octants[oct]
	for a in DIR_ACTIONS:
		if a in want:
			_press(a)
		else:
			_release(a)

func _press(action: StringName) -> void:
	if not _held.has(action):
		_held[action] = true
		Input.action_press(action)

func _release(action: StringName) -> void:
	if _held.has(action):
		_held.erase(action)
		Input.action_release(action)

func _release_all() -> void:
	for a: StringName in _held.keys().duplicate():
		_release(a)
	_stick_touch = -1
	_btn_touch.clear()

func _haptic() -> void:
	Input.vibrate_handheld(14)

# ---------------------------------------------------------------- drawing
func _draw() -> void:
	if not enabled:
		return
	var a := opacity
	var r := STICK_RADIUS * ui_scale
	var origin := _stick_origin if _stick_touch != -1 else Vector2(62 * ui_scale, Screen.H - 54 * ui_scale)
	var knob := _stick_pos if _stick_touch != -1 else origin
	var live := 1.0 if _stick_touch != -1 else 0.55
	_ring(origin, r, Color(1, 1, 1, a * 0.55 * live))
	var d := (knob - origin).limit_length(r)
	_disc(origin + d, 8.0 * ui_scale, Color(1, 1, 1, a * 0.8 * live))
	_button(_jump_centre, "A", &"jump", a)
	_button(_attack_centre, "B", &"attack", a)

func _button(c: Vector2, label: String, action: StringName, a: float) -> void:
	var pressed := _held.has(action)
	var r := BTN_R * ui_scale
	_disc(c, r, Color(1, 1, 1, a * (0.42 if pressed else 0.2)))
	_ring(c, r, Color(1, 1, 1, a * 0.7))
	PixelFont.draw_centered(self, c.x, c.y - 4.0, label, Color(1, 1, 1, a + 0.25), 1, 0, false)

func _disc(c: Vector2, r: float, col: Color) -> void:
	draw_circle(c, r, col)

func _ring(c: Vector2, r: float, col: Color) -> void:
	draw_arc(c, r, 0.0, TAU, 28, col, 1.0)
