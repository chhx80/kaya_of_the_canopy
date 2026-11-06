extends Control
## In-level HUD: Kaya's portrait, hearts, score, gems, keys and a level-name
## banner on entry.

const HEART_FULL := Rect2(16, 0, 16, 16)      ## frame 1 of pickups.png
const GEM := Rect2(0, 0, 16, 16)              ## frame 0
const KEY_FRAMES := {"yellow": 2, "red": 3, "cyan": 4}
## Kaya Refit phase 3: her portrait, cut from the 40 px puppet by
## tools/art/hud_portrait.py. Frame 0 smiling, frame 1 eyes shut. Top-left of
## the world rect, which no touch layout ever draws on: on a phone the controls
## sit in the side margins, on a tablet in the bottom margin, and with no
## margin at all they fall back to the bottom corners (src/ui/touch_controls.gd).
const PORTRAIT_PATH := "res://assets/sprites/hud_portrait.png"
const PORTRAIT_SIZE := 24
const PORTRAIT_AT := Vector2(3, 3)
## How long the eyes-shut frame holds after a hit.
const PORTRAIT_WINCE_S := 0.6
## The hearts and keys start right of the portrait.
const ROW_X := 30.0

var _pickups: Texture2D = null
var _portrait: Texture2D = null
var _wince_t := 0.0
var _last_health := -1
var _banner := ""
var _banner_t := 0.0
var _msg := ""
var _msg_t := 0.0

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)
	_pickups = load("res://assets/sprites/pickups.png")
	_portrait = load(PORTRAIT_PATH)
	_last_health = Game.health
	Game.stats_changed.connect(_on_stats_changed)

func _on_stats_changed() -> void:
	if Game.health < _last_health:
		_wince_t = PORTRAIT_WINCE_S
	_last_health = Game.health
	queue_redraw()

## The portrait's rect in the world rect, for the touch-layout tests.
static func portrait_rect() -> Rect2:
	return Rect2(PORTRAIT_AT, Vector2(PORTRAIT_SIZE, PORTRAIT_SIZE))

## Which portrait frame is showing: 1 (eyes shut) while wincing or down.
func portrait_frame() -> int:
	return 1 if _wince_t > 0.0 or Game.health <= 0 else 0

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
	_wince_t = maxf(0.0, _wince_t - delta)
	# The boss bar and the form meter track live values, so the HUD redraws
	# every frame. At 400x240 that is a handful of quads.
	queue_redraw()

func _draw() -> void:
	# The HUD belongs to the game image, not the device: draw it in the world
	# rect so it looks the same on every aspect ratio. Only the touch controls
	# move out into the margins.
	var origin := Screen.world_rect_in_ui(get_viewport()).position
	draw_set_transform(origin, 0.0, Vector2.ONE)
	var W := float(Game.SCREEN_W)
	# portrait
	if _portrait != null:
		var sz := float(PORTRAIT_SIZE)
		draw_texture_rect_region(_portrait, portrait_rect(),
			Rect2(float(portrait_frame()) * sz, 0.0, sz, sz))
	# hearts
	for i in Game.max_health:
		var p := Vector2(ROW_X + i * 11, 4)
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
	var kx := ROW_X
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
