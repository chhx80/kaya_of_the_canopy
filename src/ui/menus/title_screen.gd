extends Node2D
## Title screen. Drawn entirely in code so there is no scene tree to get wrong.
##
## A 400 x 240 picture in world units (Main shows a camera-less scene whole).
## Kaya stands on the left, framed by the low sun; the logo, the menu and the
## small print share the right-hand column, so nothing is drawn over her face
## and nothing is drawn over the menu.

const ITEMS_NEW := ["START GAME", "OPTIONS", "QUIT"]
const ITEMS_CONTINUE := ["CONTINUE", "NEW GAME", "OPTIONS", "QUIT"]

## Kaya is the owner's own picture of her (docs/reference/kaya_title_original.jpg,
## cut from its white page by tools/cut_title_kaya.py and otherwise untouched):
## the one piece of art in the game that no script draws. KAYA_SIZE is her
## picture in world units, at its own aspect; KAYA_POS its top-left (her soles
## land just above the bottom edge). KAYA_FACE is her face inside it, the one
## thing nothing else may be drawn over.
##
## She is not drawn into the world's render target, which would shrink her to
## its texel grid: she is a TextureRect in the root viewport, placed over the
## world's display rect, so the device shows the picture at its own resolution.
const KAYA_IMAGE := "res://assets/title/kaya.png"
const KAYA_SIZE := Vector2(66, 208)
const KAYA_POS := Vector2(49, 26)
const KAYA_FACE := Rect2(20, 12, 28, 28)
## Above the world (layer 0), below the menus, touch overlay and fade.
const KAYA_LAYER := 1
## The tester's switch: this many taps on her, each within SECRET_GAP seconds
## of the last, turns god mode (Game.god_mode) on or off.
const SECRET_TAPS := 7
const SECRET_GAP := 1.2
const SECRET_NOTE_TIME := 2.0

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
var _kaya_layer: CanvasLayer = null
var _kaya_view: TextureRect = null
var _secret_n := 0
var _secret_t := -100.0
var _note_t := -100.0
var _items: Array[String] = []
var _sel := 0
var _t := 0.0
var _fireflies: Array = []
var _input := InputState.new()
var _busy := false
var _tap: Control = null

## Main's world is a SubViewport drawn as a texture, so nothing inside it ever
## sees an InputEvent. This sits in Main's UI layer instead and hands the title
## each tap or click in world units. The touch overlay sees a touch BEFORE this
## node does (Godot calls `_input` on the last node in the tree first), so it
## asks claims_tap() and lets a touch on a row or on Kaya through.
class TapCatcher extends Control:
	## Takes a root-viewport point; true if it was a menu row.
	var on_tap: Callable
	## Takes a root-viewport point; true if a tap there would do something.
	var wants: Callable

	func _ready() -> void:
		add_to_group(&"tap_menus")

	## For the touch overlay (TouchControls.TAP_MENUS).
	func claims_tap(p: Vector2) -> bool:
		return wants.is_valid() and bool(wants.call(p))

	func _input(event: InputEvent) -> void:
		var p := Vector2.INF
		if event is InputEventScreenTouch and (event as InputEventScreenTouch).pressed:
			p = (event as InputEventScreenTouch).position
		elif event is InputEventMouseButton:
			var mb := event as InputEventMouseButton
			# Not the click Godot makes up from a touch: the touch itself
			# arrives here too, and seven taps on Kaya must count as seven.
			if mb.pressed and mb.button_index == MOUSE_BUTTON_LEFT \
					and mb.device != InputEvent.DEVICE_ID_EMULATION:
				p = mb.position
		if p == Vector2.INF or not on_tap.is_valid():
			return
		var hit: bool = on_tap.call(p)
		if hit:
			get_viewport().set_input_as_handled()

func _ready() -> void:
	_bg = Display.texture("res://assets/sprites/title_bg.png")
	_logo = Display.texture("res://assets/sprites/logo.png")
	_setup_kaya()
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
		_tap.wants = func(p: Vector2) -> bool: return wants_tap(world_point(p))
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
	_place_kaya()
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

## Would a tap at a world point do anything? Asked before the tap is taken.
func wants_tap(p: Vector2) -> bool:
	return not _busy and (kaya_rect().has_point(p) or row_at(p) >= 0)

## Picks and activates the row under a world point. True if there was one.
func tap(p: Vector2) -> bool:
	if _busy:
		return false
	if kaya_rect().has_point(p):
		_secret_tap()
		return true
	var i := row_at(p)
	if i < 0:
		return false
	_sel = i
	_activate()
	return true

func _secret_tap() -> void:
	_secret_n = _secret_n + 1 if _t - _secret_t <= SECRET_GAP else 1
	_secret_t = _t
	if _secret_n < SECRET_TAPS:
		return
	_secret_n = 0
	Game.set_god_mode(not Game.god_mode())
	_note_t = _t
	AudioManager.play("select" if Game.god_mode() else "locked")

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

func _setup_kaya() -> void:
	if not ResourceLoader.exists(KAYA_IMAGE):
		return
	var src: Texture2D = load(KAYA_IMAGE)
	var img := src.get_image() if src != null else null
	if img == null:
		return
	# Mipmaps, so a small desktop window shrinks her cleanly.
	img = img.duplicate()
	if img.is_compressed():
		img.decompress()
	img.generate_mipmaps()
	_kaya = ImageTexture.create_from_image(img)
	_kaya_view = TextureRect.new()
	_kaya_view.name = "Kaya"
	_kaya_view.texture = _kaya
	_kaya_view.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_kaya_view.stretch_mode = TextureRect.STRETCH_SCALE
	_kaya_view.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	_kaya_view.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_kaya_layer = CanvasLayer.new()
	_kaya_layer.name = "KayaLayer"
	_kaya_layer.layer = KAYA_LAYER
	_kaya_layer.custom_viewport = get_tree().root
	_kaya_layer.add_child(_kaya_view)
	add_child(_kaya_layer)
	_place_kaya()

## Her world-unit rect, mapped to where Main shows the world in the root.
func _place_kaya() -> void:
	if _kaya_view == null or Game.main == null:
		return
	var r: Rect2 = Game.main.world_display_rect()
	var v: Vector2 = Game.main.shown_view_size()
	if v.x <= 0.0 or v.y <= 0.0:
		return
	var k := r.size / v
	_kaya_view.position = r.position + KAYA_POS * k
	_kaya_view.size = KAYA_SIZE * k

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
	# the tester's switch: a note when it changes, a marker while it is on
	var cx := KAYA_POS.x + KAYA_SIZE.x * 0.5
	if _t - _note_t < SECRET_NOTE_TIME:
		PixelFont.draw_centered(self, cx, 12.0,
			"GOD MODE %s" % ("ON" if Game.god_mode() else "OFF"), Color(1.0, 0.82, 0.3))
	elif Game.god_mode():
		PixelFont.draw_centered(self, cx, 12.0, "GOD", Color(1.0, 0.82, 0.3, 0.7))
