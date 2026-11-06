extends Control
## Pause overlay. Lives on Main's UI layer above the HUD and stops the tree.

## In a level you can leave it for the world map, standing at its door. On the
## map itself there is no level to restart or leave, so those rows are absent
## rather than present and doing nothing (RESTART LEVEL used to be offered on
## the map and silently did nothing there).
const ITEMS_LEVEL := ["RESUME", "RESTART LEVEL", "LEAVE LEVEL", "OPTIONS", "QUIT TO TITLE"]
const ITEMS_HUB := ["RESUME", "OPTIONS", "QUIT TO TITLE"]
## Menu rows: the first row's text top and the pitch between rows. Shared by
## the drawing and by the tap test, so a tap always lands on what is drawn.
const ROW0_Y := 96.0
const ROW_H := 16.0
const ROW_HALF_W := 96.0

var ITEMS: Array = ITEMS_LEVEL

var _sel := 0
var _t := 0.0
var _in := InputState.new()
var _held_up := false
var _held_down := false
var _busy := false

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	ITEMS = ITEMS_LEVEL if Game.state == Game.State.LEVEL else ITEMS_HUB
	get_tree().paused = true

func _exit_tree() -> void:
	get_tree().paused = false

func _process(delta: float) -> void:
	_t += delta
	_in.poll()
	if _busy:
		return
	if _in.up and not _held_up:
		_sel = wrapi(_sel - 1, 0, ITEMS.size())
		AudioManager.play("blip")
	if _in.down and not _held_down:
		_sel = wrapi(_sel + 1, 0, ITEMS.size())
		AudioManager.play("blip")
	_held_up = _in.up
	_held_down = _in.down
	if Input.is_action_just_pressed(&"pause"):
		_close()
	elif _in.jump_pressed or _in.attack_pressed:
		_activate()
	queue_redraw()

## A tap (or a click) on a row picks and activates it. The touch overlay keeps
## working while paused, so the stick and A also drive the menu, but on a phone
## tapping the line you want is what a player tries first. This node is added
## after the overlay, so it sees a touch before the overlay does, and it only
## claims touches that land on a row.
func _input(event: InputEvent) -> void:
	if _busy or not visible:
		return
	var p := Vector2.INF
	if event is InputEventScreenTouch and (event as InputEventScreenTouch).pressed:
		p = (event as InputEventScreenTouch).position
	elif event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.pressed and mb.button_index == MOUSE_BUTTON_LEFT:
			p = mb.position
	if p == Vector2.INF:
		return
	var i := row_at(get_global_transform_with_canvas().affine_inverse() * p)
	if i < 0:
		return
	_sel = i
	get_viewport().set_input_as_handled()
	_activate()

## The row under a point in this control's coordinates, or -1.
func row_at(local: Vector2) -> int:
	var W := Screen.ui_size(get_viewport()).x
	if absf(local.x - W * 0.5) > ROW_HALF_W:
		return -1
	var i := int(floor((local.y - ROW0_Y) / ROW_H))
	return i if i >= 0 and i < ITEMS.size() else -1

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
		"LEAVE LEVEL":
			# Back to the world map, standing at the door of the level just
			# left. Progress inside the level is not kept, exactly as on death.
			_busy = true
			get_tree().paused = false
			var from: String = Game.current_level_id
			queue_free()
			Game.goto_hub(from)
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
	var ui := Screen.ui_size(get_viewport())
	var W := ui.x
	draw_rect(Rect2(Vector2.ZERO, ui), Color(0.03, 0.05, 0.06, 0.78))
	PixelFont.draw_centered(self, W * 0.5, 52.0, "PAUSED", Color(1, 0.86, 0.33), 2, 2)
	var y := ROW0_Y + 4.0
	for i in ITEMS.size():
		var selected := i == _sel
		var col := Color(1, 0.86, 0.33) if selected else Color(0.82, 0.86, 0.8)
		PixelFont.draw_centered(self, W * 0.5, y, ITEMS[i], col, 1, 1)
		if selected and fmod(_t, 0.6) < 0.42:
			var half: float = PixelFont.width(ITEMS[i], 1, 1) * 0.5
			PixelFont.draw(self, Vector2(round(W * 0.5 - half - 14), y), ">", col, 1, 0)
		y += ROW_H
	PixelFont.draw_centered(self, W * 0.5, 200.0, "SCORE %06d   GEMS %03d" % [Game.score, Game.gems],
		Color(0.62, 0.7, 0.62), 1, 0)
	PixelFont.draw_centered(self, W * 0.5, 214.0, Game.build_label(),
		Color(0.45, 0.5, 0.45), 1, 0)
