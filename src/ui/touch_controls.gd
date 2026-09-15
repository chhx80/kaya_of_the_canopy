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

## Placement is computed from whatever margin the device leaves around the
## world view. On a 19.5:9 phone that is ~61 px each side; on a 4:3 iPad it is
## ~30 px top and bottom. Buttons go in the margin so they never sit on top of
## the play area, and they hug the physical screen edge where a thumb rests.
var _jump_centre := Vector2(Screen.W - 44, Screen.H - 40)
var _attack_centre := Vector2(Screen.W - 88, Screen.H - 62)
var _stick_home := Vector2(62, Screen.H - 54)
var _in_margin := false

func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	process_mode = Node.PROCESS_MODE_ALWAYS
	refresh_settings()
	get_viewport().size_changed.connect(func() -> void:
		_layout()
		queue_redraw())
	Input.joy_connection_changed.connect(_on_joy_changed)
	_update_visibility()

func refresh_settings() -> void:
	opacity = float(SaveManager.setting("touch_opacity", 0.5))
	ui_scale = float(SaveManager.setting("touch_scale", 1.0))
	_layout()
	queue_redraw()

func _layout() -> void:
	var vp := get_viewport()
	var ui := Screen.ui_size(vp)
	var world := Screen.world_rect_in_ui(vp)
	var side := world.position.x                      # left/right margin width
	var vert := world.position.y                      # top/bottom margin height
	var r := BTN_R * ui_scale
	if side >= r * 2.0 + 2.0:
		# Widescreen: stack the buttons in the right margin, stick in the left.
		_in_margin = true
		var cx := ui.x - side * 0.5
		_jump_centre = Vector2(cx, ui.y * 0.5 + r + 4.0)
		_attack_centre = Vector2(cx, ui.y * 0.5 - r - 4.0)
		_stick_home = Vector2(side * 0.5, ui.y * 0.5)
	elif vert >= r + 2.0:
		# Tall-ish display (iPad): use the bottom margin.
		_in_margin = true
		var cy := ui.y - vert * 0.5
		_jump_centre = Vector2(ui.x - r - 6.0, cy)
		_attack_centre = Vector2(ui.x - r * 3.0 - 12.0, cy)
		_stick_home = Vector2(r + 6.0, cy)
	else:
		# No margin to use — fall back to overlaying the play area.
		_in_margin = false
		_jump_centre = Vector2(ui.x - 44.0 * ui_scale, ui.y - 40.0 * ui_scale)
		_attack_centre = Vector2(ui.x - 88.0 * ui_scale, ui.y - 62.0 * ui_scale)
		_stick_home = Vector2(62.0 * ui_scale, ui.y - 54.0 * ui_scale)

## True when the buttons sit outside the play area.
func buttons_clear_of_play_area() -> bool:
	return _in_margin

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
	if p.x < Screen.ui_size(get_viewport()).x * 0.5 and _stick_touch == -1:
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
	var origin := _stick_origin if _stick_touch != -1 else _stick_home
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
