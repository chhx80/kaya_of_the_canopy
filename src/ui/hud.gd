extends Control
## In-level HUD: hearts, score, gems, keys and a level-name banner on entry.

const HEART_FULL := Rect2(16, 0, 16, 16)      ## frame 1 of pickups.png
const GEM := Rect2(0, 0, 16, 16)              ## frame 0
const KEY_FRAMES := {"yellow": 2, "red": 3, "cyan": 4}

var _pickups: Texture2D = null
var _banner := ""
var _banner_t := 0.0
var _msg := ""
var _msg_t := 0.0

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)
	_pickups = load("res://assets/sprites/pickups.png")
	Game.stats_changed.connect(queue_redraw)

func set_level_name(n: String) -> void:
	_banner = n
	_banner_t = 2.2
	queue_redraw()

func flash_message(m: String, seconds: float = 1.4) -> void:
	_msg = m
	_msg_t = seconds
	queue_redraw()

func _process(delta: float) -> void:
	_banner_t = maxf(0.0, _banner_t - delta)
	_msg_t = maxf(0.0, _msg_t - delta)
	# The boss bar and the form meter track live values, so the HUD redraws
	# every frame. At 400x240 that is a handful of quads.
	queue_redraw()

func _draw() -> void:
	var W := float(Game.SCREEN_W)
	# hearts
	for i in Game.max_health:
		var p := Vector2(4 + i * 11, 4)
		var col := Color(1, 1, 1, 1) if i < Game.health else Color(0.12, 0.12, 0.16, 0.85)
		draw_texture_rect_region(_pickups, Rect2(p, Vector2(16, 16)), HEART_FULL, col)
	# gems
	draw_texture_rect_region(_pickups, Rect2(Vector2(W - 104, 3), Vector2(16, 16)), GEM)
	PixelFont.draw_shadowed(self, Vector2(W - 88, 8), "%03d" % Game.gems,
		Color(0.62, 0.86, 0.9))
	# score
	PixelFont.draw_shadowed(self, Vector2(W - 54, 8), "%06d" % Game.score,
		Color(0.96, 0.86, 0.4))
	# keys
	var kx := 4.0
	for color: String in ["yellow", "red", "cyan"]:
		var n := int(Game.keys.get(color, 0))
		if n <= 0:
			continue
		var frame := int(KEY_FRAMES[color])
		draw_texture_rect_region(_pickups, Rect2(Vector2(kx, 18), Vector2(16, 16)),
			Rect2(frame * 16, 0, 16, 16))
		if n > 1:
			PixelFont.draw_shadowed(self, Vector2(kx + 13, 26), "%d" % n)
		kx += 15.0
	# lives
	PixelFont.draw_shadowed(self, Vector2(4, Game.SCREEN_H - 12),
		"LIVES %d" % Game.lives, Color(0.8, 0.84, 0.78))
	# form meter: bird stamina or fish air
	var lvl: Node = Game.current_level
	var pl: Player = lvl.player if lvl != null and lvl.get("player") != null else null
	if pl != null and pl.form != null:
		var frac := -1.0
		var col := Color(0.35, 0.8, 1.0)
		var label := ""
		if pl.form.max_stamina > 0.0 and pl.form.has_method("stamina_fraction"):
			frac = pl.form.stamina_fraction()
			col = Color(0.95, 0.92, 0.85)
			label = "FLY"
		elif pl.form.has_method("air_fraction"):
			frac = pl.form.air_fraction()
			col = Color(0.35, 0.8, 1.0)
			label = "AIR"
		if frac >= 0.0:
			var bx := 4.0
			var by := 34.0
			PixelFont.draw_shadowed(self, Vector2(bx, by), label, Color(0.8, 0.85, 0.8))
			draw_rect(Rect2(Vector2(bx + 28, by), Vector2(52, 7)), Color(0.05, 0.06, 0.09, 0.8))
			draw_rect(Rect2(Vector2(bx + 29, by + 1), Vector2(50.0 * frac, 5)), col)
	# boss bar
	var bosses := get_tree().get_nodes_in_group(&"bosses")
	for n in bosses:
		var b := n as Enemy
		if b == null or not b.active or b.health <= 0:
			continue
		var frac := clampf(float(b.health) / float(b.max_health), 0.0, 1.0)
		var name: String = b.cfg.get("display_name", "BOSS")
		var phase: String = b.phase_name() if b.has_method("phase_name") else ""
		PixelFont.draw_centered(self, W * 0.5, Game.SCREEN_H - 48.0,
			name if phase == "" else "%s - %s" % [name, phase], Color(1, 0.75, 0.6), 1, 0)
		draw_rect(Rect2(Vector2(W * 0.5 - 82, Game.SCREEN_H - 38), Vector2(164, 9)),
			Color(0.05, 0.06, 0.09, 0.85))
		draw_rect(Rect2(Vector2(W * 0.5 - 81, Game.SCREEN_H - 37), Vector2(162.0 * frac, 7)),
			Color(0.78, 0.28, 0.24))
		break
	# transient message
	if _msg_t > 0.0 and _msg != "":
		var ma: float = clampf(_msg_t / 0.4, 0.0, 1.0)
		PixelFont.draw_centered(self, W * 0.5, 52.0, _msg, Color(1, 0.6, 0.45, ma), 1, 1)
	# entry banner
	if _banner_t > 0.0 and _banner != "":
		var a: float = clampf(_banner_t / 0.5, 0.0, 1.0)
		var y := 100.0
		var w := PixelFont.width(_banner, 2, 1)
		draw_rect(Rect2(Vector2((W - w) * 0.5 - 8, y - 6), Vector2(w + 16, 28)),
			Color(0.05, 0.06, 0.09, 0.72 * a))
		PixelFont.draw_centered(self, W * 0.5, y, _banner, Color(1, 0.9, 0.45, a), 2, 1)
