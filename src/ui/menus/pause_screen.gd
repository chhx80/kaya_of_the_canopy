extends Control
## Pause overlay. Lives on Main's UI layer above the HUD and stops the tree.

const ITEMS := ["RESUME", "RESTART LEVEL", "OPTIONS", "QUIT TO TITLE"]

var _sel := 0
var _t := 0.0
var _input := InputState.new()
var _held_up := false
var _held_down := false
var _busy := false

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	get_tree().paused = true

func _exit_tree() -> void:
	get_tree().paused = false

func _process(delta: float) -> void:
	_t += delta
	_input.poll()
	if _busy:
		return
	if _input.up and not _held_up:
		_sel = wrapi(_sel - 1, 0, ITEMS.size())
		AudioManager.play("blip")
	if _input.down and not _held_down:
		_sel = wrapi(_sel + 1, 0, ITEMS.size())
		AudioManager.play("blip")
	_held_up = _input.up
	_held_down = _input.down
	if Input.is_action_just_pressed(&"pause"):
		_close()
	elif _input.jump_pressed or _input.attack_pressed:
		_activate()
	queue_redraw()

func _close() -> void:
	_busy = true
	get_tree().paused = false
	queue_free()

func _activate() -> void:
	AudioManager.play("select")
	match ITEMS[_sel]:
		"RESUME":
			_close()
		"RESTART LEVEL":
			_busy = true
			get_tree().paused = false
			var id: String = Game.current_level_id
			queue_free()
			if id != "":
				Game.goto_level(id)
		"OPTIONS":
			_busy = true
			visible = false          # otherwise the pause text bleeds through
			var opts: Control = (load("res://src/ui/menus/options_panel.gd") as GDScript).new()
			opts.on_closed = func() -> void:
				_busy = false
				visible = true
			get_parent().add_child(opts)
		"QUIT TO TITLE":
			_busy = true
			get_tree().paused = false
			queue_free()
			Game.goto_title()

func _draw() -> void:
	var W := float(Screen.W)
	draw_rect(Rect2(Vector2.ZERO, Vector2(Screen.W, Screen.H)), Color(0.03, 0.05, 0.06, 0.78))
	PixelFont.draw_centered(self, W * 0.5, 52.0, "PAUSED", Color(1, 0.86, 0.33), 2, 2)
	var y := 100.0
	for i in ITEMS.size():
		var selected := i == _sel
		var col := Color(1, 0.86, 0.33) if selected else Color(0.82, 0.86, 0.8)
		PixelFont.draw_centered(self, W * 0.5, y, ITEMS[i], col, 1, 1)
		if selected and fmod(_t, 0.6) < 0.42:
			var half: float = PixelFont.width(ITEMS[i], 1, 1) * 0.5
			PixelFont.draw(self, Vector2(round(W * 0.5 - half - 14), y), ">", col, 1, 0)
		y += 16.0
	PixelFont.draw_centered(self, W * 0.5, 200.0, "SCORE %06d   GEMS %03d" % [Game.score, Game.gems],
		Color(0.62, 0.7, 0.62), 1, 0)
