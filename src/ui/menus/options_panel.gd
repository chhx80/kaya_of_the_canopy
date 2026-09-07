extends Control
## Settings, usable from the title screen and from the pause menu.
## Every row writes straight through to SaveManager.

class Row extends RefCounted:
	var key := ""
	var label := ""
	var kind := "float"          ## "float" | "bool" | "action"
	var step := 0.1
	func _init(k: String, l: String, ki: String = "float", st: float = 0.1) -> void:
		key = k; label = l; kind = ki; step = st

var rows: Array[Row] = []
var _sel := 0
var _t := 0.0
var _input := InputState.new()
var _held := {}
var on_closed: Callable = Callable()

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	rows = [
		Row.new("music", "MUSIC"),
		Row.new("sfx", "SOUND"),
		Row.new("touch_opacity", "TOUCH OPACITY"),
		Row.new("touch_scale", "TOUCH SIZE", "float", 0.1),
		Row.new("screen_flip", "SCREEN FLIP", "bool"),
		Row.new("", "BACK", "action"),
	]

func _process(delta: float) -> void:
	_t += delta
	_input.poll()
	if _edge("up", _input.up):
		_sel = wrapi(_sel - 1, 0, rows.size())
		AudioManager.play("blip")
	if _edge("down", _input.down):
		_sel = wrapi(_sel + 1, 0, rows.size())
		AudioManager.play("blip")
	var r := rows[_sel]
	if r.kind == "float":
		if _edge("left", _input.left):
			_bump(r, -r.step)
		if _edge("right", _input.right):
			_bump(r, r.step)
	elif r.kind == "bool":
		if _edge("left", _input.left) or _edge("right", _input.right) \
				or _input.jump_pressed or _input.attack_pressed:
			SaveManager.set_setting(r.key, not bool(SaveManager.setting(r.key, true)))
			SaveManager.save()
			AudioManager.play("blip")
	if r.kind == "action" and (_input.jump_pressed or _input.attack_pressed):
		_close()
	if Input.is_action_just_pressed(&"pause"):
		_close()
	queue_redraw()

func _edge(name: String, now: bool) -> bool:
	var was := bool(_held.get(name, false))
	_held[name] = now
	return now and not was

func _bump(r: Row, d: float) -> void:
	var v: float = clampf(float(SaveManager.setting(r.key, 0.5)) + d, 0.0, 1.0 if r.key != "touch_scale" else 1.6)
	if r.key == "touch_scale":
		v = clampf(v, 0.6, 1.6)
	SaveManager.set_setting(r.key, v)
	SaveManager.save()
	AudioManager.apply_settings()
	AudioManager.play("blip")
	var tc := get_tree().root.find_child("TouchControls", true, false)
	if tc != null and tc.has_method("refresh_settings"):
		tc.refresh_settings()

func _close() -> void:
	AudioManager.play("select")
	if on_closed.is_valid():
		on_closed.call()
	queue_free()

func _draw() -> void:
	var W := float(Screen.W)
	draw_rect(Rect2(Vector2.ZERO, Vector2(Screen.W, Screen.H)), Color(0.03, 0.05, 0.06, 0.97))
	PixelFont.draw_centered(self, W * 0.5, 30.0, "OPTIONS", Color(1, 0.86, 0.33), 2, 2)
	var y := 76.0
	for i in rows.size():
		var r := rows[i]
		var selected := i == _sel
		var col := Color(1, 0.86, 0.33) if selected else Color(0.82, 0.86, 0.8)
		PixelFont.draw(self, Vector2(70, y), r.label, col, 1, 1)
		if r.kind == "float":
			var v := float(SaveManager.setting(r.key, 0.5))
			var maxv := 1.6 if r.key == "touch_scale" else 1.0
			var frac: float = clampf(v / maxv, 0.0, 1.0)
			draw_rect(Rect2(Vector2(232, y - 1), Vector2(84, 9)), Color(0.08, 0.1, 0.12))
			draw_rect(Rect2(Vector2(233, y), Vector2(82.0 * frac, 7)), col)
		elif r.kind == "bool":
			var on := bool(SaveManager.setting(r.key, true))
			PixelFont.draw(self, Vector2(232, y), "ON" if on else "OFF",
				col if on else Color(0.6, 0.5, 0.5), 1, 1)
		if selected and fmod(_t, 0.6) < 0.42:
			PixelFont.draw(self, Vector2(54, y), ">", col, 1, 0)
		y += 20.0
	PixelFont.draw_centered(self, W * 0.5, 208.0,
		"ARROWS ADJUST     JUMP CONFIRMS", Color(0.55, 0.62, 0.55), 1, 0)
