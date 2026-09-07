extends Node2D
## Title screen. Drawn entirely in code so there is no scene tree to get wrong.

const ITEMS_NEW := ["START GAME", "OPTIONS", "QUIT"]
const ITEMS_CONTINUE := ["CONTINUE", "NEW GAME", "OPTIONS", "QUIT"]

var _logo: Texture2D = null
var _bg: Texture2D = null
var _items: Array[String] = []
var _sel := 0
var _t := 0.0
var _fireflies: Array = []
var _input := InputState.new()
var _busy := false

func _ready() -> void:
	_bg = load("res://assets/sprites/title_bg.png")
	_logo = load("res://assets/sprites/logo.png")
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
	AudioManager.music("title")

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

func _draw() -> void:
	var W := float(Game.SCREEN_W)
	if _bg:
		draw_texture(_bg, Vector2.ZERO)
	# fireflies drift over the canopy
	for f: Dictionary in _fireflies:
		var y: float = f["y"] + sin(_t * 1.7 + f["phase"]) * f["bob"]
		var a: float = 0.45 + 0.55 * (0.5 + 0.5 * sin(_t * 3.1 + f["phase"]))
		draw_rect(Rect2(Vector2(round(f["x"]), round(y)), Vector2.ONE),
			Color(1.0, 0.9, 0.45, a))
	# logo, bobbing gently
	if _logo:
		var lx: float = round((W - _logo.get_width()) * 0.5)
		var ly: float = round(26.0 + sin(_t * 1.2) * 2.0)
		draw_texture(_logo, Vector2(lx, ly))
	PixelFont.draw_centered(self, W * 0.5, 78.0, "OF THE CANOPY",
		Color(0.35, 0.76, 0.35), 2, 1)
	# menu
	var y := 132.0
	for i in _items.size():
		var selected := i == _sel
		var col: Color = Color(1, 0.86, 0.33) if selected else Color(0.85, 0.88, 0.82)
		PixelFont.draw_centered(self, W * 0.5, y, _items[i], col, 1, 1)
		if selected and fmod(_t, 0.6) < 0.42:
			var half: float = PixelFont.width(_items[i], 1, 1) * 0.5
			PixelFont.draw(self, Vector2(round(W * 0.5 - half - 14), y), ">",
				Color(1, 0.86, 0.33), 1, 0)
		y += 14.0
	PixelFont.draw_centered(self, W * 0.5, 206.0,
		"BEST %06d" % int(SaveManager.data.get("best_score", 0)),
		Color(0.65, 0.72, 0.62), 1, 0)
	PixelFont.draw(self, Vector2(4, Game.SCREEN_H - 10), "V0.1.0",
		Color(0.5, 0.55, 0.5), 1, 0)
	var hint := "SPACE-SELECT   ARROWS-MOVE"
	PixelFont.draw(self, Vector2(W - 4 - PixelFont.width(hint, 1, 0),
		Game.SCREEN_H - 10), hint, Color(0.5, 0.55, 0.5), 1, 0)
