extends Node2D
## Title screen. Drawn entirely in code so there is no scene tree to get wrong.
##
## A 400 x 240 picture in world units (Main shows a camera-less scene whole).
## Kaya stands on the left, framed by the low sun; the logo, the menu and the
## small print share the right-hand column, so nothing is drawn over her face
## and nothing is drawn over the menu.

const ITEMS_NEW := ["START GAME", "OPTIONS", "QUIT"]
const ITEMS_CONTINUE := ["CONTINUE", "NEW GAME", "OPTIONS", "QUIT"]

## Kaya: tools/art/hd_title_kaya.py, frames of KAYA_SIZE world units, drawn
## with the cell's top-left at KAYA_POS (her soles land just above the bottom
## edge). KAYA_FACE is her face inside the cell, the one thing nothing else
## may be drawn over.
const KAYA_SHEET := "res://assets/sprites/title_kaya.png"
const KAYA_SIZE := Vector2(84, 176)
const KAYA_POS := Vector2(40, 62)
const KAYA_FACE := Rect2(28, 20, 28, 30)
## The idle cycle: rest, breathe in, rest with the hair and ribbon drifting,
## breathe in again. Every second cycle she blinks at the end of a rest.
const IDLE_ORDER := [0, 1, 2, 1]
const IDLE_STEP := 0.7
const BLINK_FRAME := 3
const BLINK_TIME := 0.14

## The right-hand column: everything but Kaya is centred on COL_X.
const COL_X := 258.0
const LOGO_Y := 18.0
const SUBTITLE_Y := 70.0
## Menu rows: the first row's tap band top and the pitch between rows. Shared
## by the drawing and by the tap test, so a tap always lands on what is drawn.
const ROW0_Y := 106.0
const ROW_H := 15.0
const ROW_HALF_W := 70.0
const TEXT_IN_ROW := 4.0
const BEST_Y := 176.0
const HINT_Y := 208.0
const VERSION_Y := 220.0

var _logo: Texture2D = null
var _bg: Texture2D = null
var _kaya: Texture2D = null
var _items: Array[String] = []
var _sel := 0
var _t := 0.0
var _fireflies: Array = []
var _input := InputState.new()
var _busy := false
var _tap: Control = null

## Main's world is a SubViewport drawn as a texture, so nothing inside it ever
## sees an InputEvent. This sits in Main's UI layer instead and hands the title
## each tap or click in world units. It is added after the touch overlay, so it
## sees a touch first, and it only claims touches that land on a menu row.
class TapCatcher extends Control:
	## Takes a root-viewport point; true if it was a menu row.
	var on_tap: Callable

	func _input(event: InputEvent) -> void:
		var p := Vector2.INF
		if event is InputEventScreenTouch and (event as InputEventScreenTouch).pressed:
			p = (event as InputEventScreenTouch).position
		elif event is InputEventMouseButton:
			var mb := event as InputEventMouseButton
			if mb.pressed and mb.button_index == MOUSE_BUTTON_LEFT:
				p = mb.position
		if p == Vector2.INF or not on_tap.is_valid():
			return
		var hit: bool = on_tap.call(p)
		if hit:
			get_viewport().set_input_as_handled()

func _ready() -> void:
	_bg = Display.texture("res://assets/sprites/title_bg.png")
	_logo = Display.texture("res://assets/sprites/logo.png")
	if ResourceLoader.exists(KAYA_SHEET):
		_kaya = Display.texture(KAYA_SHEET)
	var has_save: bool = SaveManager.completed_count() > 0
	_items.assign(ITEMS_CONTINUE if has_save else ITEMS_NEW)
	var rng := RandomNumberGenerator.new()
	rng.seed = 4242
	for i in 22:
		_fireflies.append({
			"x": rng.randf_range(0, Game.SCREEN_W),
			"y": rng.randf_range(120, Game.SCREEN_H),
			"phase": rng.randf_range(0, TAU),
			"speed": rng.randf_range(4.0, 12.0),
			"bob": rng.randf_range(3.0, 9.0),
		})
	if Game.main != null:
		_tap = TapCatcher.new()
		_tap.name = "TitleTap"
		_tap.on_tap = func(p: Vector2) -> bool: return tap(world_point(p))
		_tap.mouse_filter = Control.MOUSE_FILTER_IGNORE
		Game.main.ui.add_child(_tap)
	AudioManager.music("title")

func _exit_tree() -> void:
	if _tap != null and is_instance_valid(_tap):
		_tap.queue_free()
	_tap = null

func _physics_process(delta: float) -> void:
	_t += delta
	_input.poll()
	if not _busy:
		if _input.up and not _held_up:
			_move_sel(-1)
		if _input.down and not _held_down:
			_move_sel(1)
		if _input.jump_pressed or _input.attack_pressed:
			_activate()
	_held_up = _input.up
	_held_down = _input.down
	for f: Dictionary in _fireflies:
		f["x"] = fposmod(f["x"] + f["speed"] * delta, Game.SCREEN_W)
	queue_redraw()

var _held_up := false
var _held_down := false

func _move_sel(d: int) -> void:
	_sel = wrapi(_sel + d, 0, _items.size())
	AudioManager.play("blip")

## A root-viewport point (a touch, a click) in this picture's world units.
func world_point(screen: Vector2) -> Vector2:
	var r: Rect2 = Game.main.world_display_rect()
	var v: Vector2 = Game.main.shown_view_size()
	if r.size.x <= 0.0 or r.size.y <= 0.0:
		return Vector2.INF
	return (screen - r.position) / r.size * v

## The menu row under a world point, or -1.
func row_at(p: Vector2) -> int:
	if absf(p.x - COL_X) > ROW_HALF_W:
		return -1
	var i := int(floor((p.y - ROW0_Y) / ROW_H))
	return i if i >= 0 and i < _items.size() else -1

## Picks and activates the row under a world point. True if there was one.
func tap(p: Vector2) -> bool:
	if _busy:
		return false
	var i := row_at(p)
	if i < 0:
		return false
	_sel = i
	_activate()
	return true

func _activate() -> void:
	var item: String = _items[_sel]
	AudioManager.play("select")
	match item:
		"START GAME", "NEW GAME":
			if item == "NEW GAME":
				SaveManager.wipe()
			_busy = true
			Game.reset_run()
			Game.goto_hub()
		"CONTINUE":
			_busy = true
			Game.reset_run()
			Game.goto_hub()
		"OPTIONS":
			_busy = true
			Game.main.swap_world("res://src/ui/menus/options_screen.tscn")
		"QUIT":
			get_tree().quit()

## The idle frame at time `t`.
func kaya_frame(t: float) -> int:
	var step := int(floor(t / IDLE_STEP))
	var f: int = IDLE_ORDER[step % IDLE_ORDER.size()]
	if f == 0 and (step / IDLE_ORDER.size()) % 2 == 1 \
			and fmod(t, IDLE_STEP) > IDLE_STEP - BLINK_TIME:
		f = BLINK_FRAME
	return f

# ------------------------------------------------------------ layout, in world units
## Where each piece is drawn, so the layout can be checked (tests/integration)
## and the drawing below can never disagree with it.
func kaya_rect() -> Rect2:
	return Rect2(KAYA_POS, KAYA_SIZE)

func kaya_face_rect() -> Rect2:
	return Rect2(KAYA_POS + KAYA_FACE.position, KAYA_FACE.size)

func logo_rect() -> Rect2:
	var s := _logo.get_size() if _logo != null else Vector2.ZERO
	return Rect2(Vector2(roundf(COL_X - s.x * 0.5), LOGO_Y - 2.0), s + Vector2(0, 4))

func subtitle_rect() -> Rect2:
	return _text_rect("OF THE CANOPY", COL_X, SUBTITLE_Y, 2, 1)

func row_rect(i: int) -> Rect2:
	return Rect2(COL_X - ROW_HALF_W, ROW0_Y + ROW_H * float(i), ROW_HALF_W * 2.0, ROW_H)

func row_count() -> int:
	return _items.size()

func best_rect() -> Rect2:
	return _text_rect(_best_text(), COL_X, BEST_Y, 1, 0)

func hint_rect() -> Rect2:
	return _text_rect(_hint(), COL_X, HINT_Y, 1, 0)

func version_rect() -> Rect2:
	return _text_rect(_version_text(), COL_X, VERSION_Y, 1, 0)

func _text_rect(text: String, cx: float, y: float, scale: int, tracking: int) -> Rect2:
	var w := float(PixelFont.width(text, scale, tracking))
	# +scale: draw_centered's drop shadow
	return Rect2(Vector2(roundf(cx - w * 0.5), y),
		Vector2(w + scale, float(PixelFont.height(scale) + scale)))

func _best_text() -> String:
	return "BEST %06d" % int(SaveManager.data.get("best_score", 0))

func _version_text() -> String:
	return "V0.1.0  %s" % Game.build_label()

## The hint has to match whatever the player is actually holding — a keyboard
## hint on a phone is just noise. Ask the touch overlay whether it is live
## rather than the display server, so the two can never disagree.
func _hint() -> String:
	var touch_active: bool = Game.main != null and Game.main.touch != null \
		and Game.main.touch.enabled
	if not Input.get_connected_joypads().is_empty():
		return "A-SELECT   DPAD-MOVE"
	if touch_active:
		return "TAP TO SELECT"
	return "SPACE-SELECT   ARROWS-MOVE"

func _draw() -> void:
	if _bg:
		draw_texture(_bg, Vector2.ZERO)
	if _kaya:
		var src := Rect2(Vector2(KAYA_SIZE.x * float(kaya_frame(_t)), 0.0), KAYA_SIZE)
		draw_texture_rect_region(_kaya, Rect2(KAYA_POS, KAYA_SIZE), src)
	# fireflies drift over the canopy, and past her
	for f: Dictionary in _fireflies:
		var y: float = f["y"] + sin(_t * 1.7 + f["phase"]) * f["bob"]
		var a: float = 0.45 + 0.55 * (0.5 + 0.5 * sin(_t * 3.1 + f["phase"]))
		draw_rect(Rect2(Vector2(round(f["x"]), round(y)), Vector2.ONE),
			Color(1.0, 0.9, 0.45, a))
	# logo, bobbing gently
	if _logo:
		var lx: float = round(COL_X - _logo.get_width() * 0.5)
		var ly: float = round(LOGO_Y + sin(_t * 1.2) * 2.0)
		draw_texture(_logo, Vector2(lx, ly))
	PixelFont.draw_centered(self, COL_X, SUBTITLE_Y, "OF THE CANOPY",
		Color(0.35, 0.76, 0.35), 2, 1)
	# menu
	for i in _items.size():
		var y := ROW0_Y + ROW_H * float(i) + TEXT_IN_ROW
		var selected := i == _sel
		var col: Color = Color(1, 0.86, 0.33) if selected else Color(0.85, 0.88, 0.82)
		PixelFont.draw_centered(self, COL_X, y, _items[i], col, 1, 1)
		if selected and fmod(_t, 0.6) < 0.42:
			var half: float = PixelFont.width(_items[i], 1, 1) * 0.5
			PixelFont.draw(self, Vector2(round(COL_X - half - 14), y), ">",
				Color(1, 0.86, 0.33), 1, 0)
	PixelFont.draw_centered(self, COL_X, BEST_Y, _best_text(),
		Color(0.65, 0.72, 0.62), 1, 0)
	# the small print: the control hint over the build line, one per row, so
	# neither can run into the other however long the build label gets
	PixelFont.draw_centered(self, COL_X, HINT_Y, _hint(), Color(0.62, 0.68, 0.6), 1, 0)
	PixelFont.draw_centered(self, COL_X, VERSION_Y, _version_text(),
		Color(0.5, 0.55, 0.5), 1, 0)
