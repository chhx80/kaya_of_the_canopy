class_name Enemy
extends Actor
## Shared enemy behaviour: config loading, health, damage flash, death, drops,
## contact damage and off-screen freezing. Subclasses implement `think()` only.

signal killed(enemy: Enemy)

const FLASH_TIME := 0.12
const DEATH_TIME := 0.35

var cfg: Dictionary = {}
var enemy_id := ""
var health := 1
var max_health := 1
var contact_damage := 1
var score_value := 100
var gravity := 720.0
var speed := 0.0

var sprite: Sprite2D = null
var _frame_size := Vector2i(16, 16)
var _anim := "move"
var _anim_t := 0.0
var _anim_i := 0
var _flash := 0.0
var _dying := 0.0

var home_screen := Vector2i.ZERO
var spawn_pos := Vector2.ZERO
var active := true
var props: Dictionary = {}

static func load_config(id: String) -> Dictionary:
	var path := "res://data/enemies/%s.json" % id
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("Enemy: missing %s" % path)
		return {}
	var d: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	return d if typeof(d) == TYPE_DICTIONARY else {}

func configure(id: String, e: Dictionary = {}) -> void:
	enemy_id = id
	cfg = load_config(id)
	props = e
	max_health = int(cfg.get("health", 1))
	health = max_health
	contact_damage = int(cfg.get("contact_damage", 1))
	score_value = int(cfg.get("score", 100))
	gravity = float(cfg.get("gravity", 720.0))
	speed = float(cfg.get("speed", 0.0))
	var hb: Dictionary = cfg.get("hitbox", {"w": 14, "h": 12, "ox": 1, "oy": 2})
	box = Vector2(float(hb.get("w", 14)), float(hb.get("h", 12)))
	_frame_size = Vector2i(int(cfg.get("frame_w", 16)), int(cfg.get("frame_h", 16)))
	if String(e.get("facing", "")) == "left":
		facing = -1
	on_configured()

func on_configured() -> void:
	pass

func _ready() -> void:
	add_to_group(&"enemies")
	sprite = Sprite2D.new()
	sprite.centered = false
	sprite.region_enabled = true
	sprite.texture = load(String(cfg.get("sprite", "res://assets/sprites/enemy_walker.png")))
	sprite.region_rect = Rect2(0, 0, _frame_size.x, _frame_size.y)
	add_child(sprite)
	spawn_pos = pos
	home_screen = Screen.index_of(center(), Vector2i(999, 999))
	_update_anim(0.0)
	_sync_render_position()

## Called by the level when the camera lands on a screen. Enemies on the screen
## you just entered are reset to their spawn state — cheap, and period-accurate.
func set_active_screen(s: Vector2i) -> void:
	var was := active
	active = s == home_screen
	if active and not was:
		respawn()

func respawn() -> void:
	pos = spawn_pos
	vel = Vector2.ZERO
	health = max_health
	_dying = 0.0
	_flash = 0.0
	visible = true
	on_respawn()

func on_respawn() -> void:
	pass

func _physics_process(delta: float) -> void:
	if _dying > 0.0:
		_dying -= delta
		position.y -= 40.0 * delta
		modulate.a = clampf(_dying / DEATH_TIME, 0.0, 1.0)
		if _dying <= 0.0:
			queue_free()
		return
	if Game.sim_paused or not active:
		return
	_flash = maxf(0.0, _flash - delta)
	think(delta)
	step_motion(delta)
	if fell_out_of_world():
		queue_free()
		return
	_touch_player()
	_update_anim(delta)
	_sync_render_position()

## Subclass hook: set `vel` for this tick.
func think(_delta: float) -> void:
	pass

func apply_gravity(delta: float) -> void:
	vel.y = minf(vel.y + gravity * delta, 340.0)

func player() -> Player:
	if level != null and level.get("player") != null:
		return level.player
	return null

func _touch_player() -> void:
	var p := player()
	if p == null or p.dead or contact_damage <= 0:
		return
	if aabb().intersects(p.aabb()):
		p.take_damage(contact_damage, center() - p.center())

# ---------------------------------------------------------------- damage
func hurt(amount: int, from: Vector2 = Vector2.ZERO) -> void:
	if _dying > 0.0:
		return
	health -= amount
	_flash = FLASH_TIME
	if health <= 0:
		die(from)
	else:
		AudioManager.play("enemy_hit")
		vel.x += signf(center().x - from.x) * 40.0

func die(_from: Vector2 = Vector2.ZERO) -> void:
	if _dying > 0.0:
		return
	_dying = DEATH_TIME
	AudioManager.play("enemy_die")
	Game.add_score(score_value)
	remove_from_group(&"enemies")
	_drop_loot()
	killed.emit(self)

func _drop_loot() -> void:
	var drops: Dictionary = cfg.get("drops", {})
	if drops.is_empty() or level == null:
		return
	var rng := RandomNumberGenerator.new()
	rng.randomize()
	for kind: String in drops.keys():
		if rng.randf() < float(drops[kind]):
			level.spawn_entity({
				"type": kind,
				"px": pos.x + box.x * 0.5 - 8.0,
				"py": pos.y + box.y - 16.0,
				"from_drop": true,
			})
			return   # at most one drop per enemy

# ---------------------------------------------------------------- animation
func set_anim(name: String) -> void:
	if _anim != name:
		_anim = name
		_anim_t = 0.0
		_anim_i = 0

func _update_anim(delta: float) -> void:
	var anims: Dictionary = cfg.get("anim", {})
	var a: Dictionary = anims.get(_anim, {"frames": [0], "fps": 1})
	var frames: Array = a.get("frames", [0])
	var fps := float(a.get("fps", 1))
	if fps > 0.0 and frames.size() > 1:
		_anim_t += delta
		while _anim_t >= 1.0 / fps:
			_anim_t -= 1.0 / fps
			_anim_i = (_anim_i + 1) % frames.size()
	var frame := int(frames[_anim_i % frames.size()])
	sprite.region_rect = Rect2(frame * _frame_size.x, 0, _frame_size.x, _frame_size.y)
	sprite.flip_h = facing < 0
	var hb: Dictionary = cfg.get("hitbox", {})
	var ox := -float(hb.get("ox", 1))
	var oy := -float(hb.get("oy", 2))
	sprite.offset = Vector2(ox, oy)
	if sprite.flip_h:
		sprite.offset.x = -(float(_frame_size.x) + ox - box.x)
	sprite.modulate = Color(2.4, 2.0, 2.0) if _flash > 0.0 else Color.WHITE
