class_name Checkpoint
extends Node2D
## A post Kaya lights by touching it. The active one is where a death (with
## lives left) brings her back, instead of the level's spawn; see
## Level.on_checkpoint_touched() for what is remembered and Game.restart_level()
## for when it is used. Tunables in data/checkpoint.json.
##
## The entity's tile is the cell Kaya stands in, exactly like player_spawn: her
## feet on the tile below. The post is two tiles tall and stands on that floor.

const CONFIG_PATH := "res://data/checkpoint.json"
const SHEET := "res://assets/sprites/checkpoint.png"
const POOL_TEX := "res://assets/sprites/light_pool.png"
const TS := TileData4.TILE_SIZE

static var _cfg: Dictionary = {}

var pos := Vector2.ZERO          ## top-left of the entity's tile, world px
var index := -1                  ## which entity in LevelDef.entities this is
var level: Node = null
var lit := false
var sprite: Sprite2D = null
var _glow: Sprite2D = null
var _t := 0.0
## Was Kaya on the post last tick. A respawn seats her on it, so the level sets
## this on the post it restores to: coming back is not a fresh touch.
var _inside := false

func mark_occupied() -> void:
	_inside = true

static func cfg() -> Dictionary:
	if _cfg.is_empty():
		var f := FileAccess.open(CONFIG_PATH, FileAccess.READ)
		if f != null:
			var d: Variant = JSON.parse_string(f.get_as_text())
			f.close()
			if typeof(d) == TYPE_DICTIONARY:
				_cfg = d as Dictionary
	return _cfg

static func num(key: String, fallback: float) -> float:
	return float(cfg().get(key, fallback))

## The box that lights a post: the stood-in cell and the one above it, grown by
## touch_grow_px. Static and pure, because the prover and tools/levelstats ask
## "does the route pass this checkpoint" under exactly the rule play uses.
static func trigger_rect(tile_px: Vector2) -> Rect2:
	return Rect2(tile_px - Vector2(0, TS), Vector2(TS, TS * 2)).grow(num("touch_grow_px", 1.0))

## Where Kaya is put back, given her hitbox: the spawn rule (Level.spawn_entity's
## player_spawn), so a checkpoint and a spawn on the same tile seat her alike.
static func seat(tile_px: Vector2, box: Vector2) -> Vector2:
	return Vector2(tile_px.x + 3.0, tile_px.y + float(TS) - box.y)

func setup(p: Vector2, entity_index: int) -> void:
	pos = p
	index = entity_index

func _ready() -> void:
	add_to_group(&"checkpoints")
	var c := cfg()
	_glow = Sprite2D.new()
	_glow.texture = Display.texture(POOL_TEX)
	var m := CanvasItemMaterial.new()
	m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_glow.material = m
	add_child(_glow)
	sprite = Sprite2D.new()
	sprite.centered = false
	sprite.region_enabled = true
	sprite.texture = Display.texture(SHEET)
	add_child(sprite)
	# The post's foot is the bottom of the stood-in cell.
	var fh := float(c.get("frame_h", 32))
	sprite.position = Vector2(0.0, float(TS) - fh)
	position = pos.round()
	_refresh()

func aabb() -> Rect2:
	return trigger_rect(pos)

## The brazier, in world px: where the flame burns and the burst comes from.
func brazier() -> Vector2:
	return pos + Vector2(TS * 0.5, float(TS) - num("glow_lift_px", 24.0))

func set_lit(on: bool) -> void:
	lit = on
	_refresh()

func _frame() -> int:
	var c := cfg()
	if not lit:
		return int(c.get("unlit_frame", 0))
	var frames: Array = c.get("lit_frames", [1])
	if frames.is_empty():
		return int(c.get("unlit_frame", 0))
	var i := int(_t * num("flame_fps", 8.0)) % frames.size()
	return int(frames[i])

func _refresh() -> void:
	if sprite == null:
		return
	var fw := num("frame_w", 16.0)
	var fh := num("frame_h", 32.0)
	sprite.region_rect = Rect2(float(_frame()) * fw, 0.0, fw, fh)
	var col: Array = cfg().get("glow_colour", [1.0, 0.72, 0.36, 0.55])
	var c := Color(float(col[0]), float(col[1]), float(col[2]), float(col[3]))
	var pulse := num("glow_pulse", 0.18)
	c.a *= 1.0 - pulse * (0.5 + 0.5 * sin(_t * TAU * num("glow_pulse_hz", 1.3)))
	if not lit:
		c.a *= num("unlit_glow_alpha", 0.22)
	_glow.modulate = c
	var r := num("glow_radius_px", 40.0)
	var ts := _glow.texture.get_size() if _glow.texture != null else Vector2.ONE
	_glow.scale = Vector2(r * 2.0 / maxf(1.0, ts.x), r * 2.0 / maxf(1.0, ts.y))
	_glow.position = brazier() - pos.round()

func _physics_process(delta: float) -> void:
	if Game.sim_paused:
		return
	_t += delta
	_refresh()
	var p: Player = level.player if level != null and level.get("player") != null else null
	var inside := p != null and not p.dead and aabb().intersects(p.aabb())
	# Edge-triggered: the level remembers the world as it is the moment she
	# steps onto the post, and again each time she comes back to it — never on
	# every frame she stands there.
	if inside and not _inside and level.has_method("on_checkpoint_touched"):
		level.on_checkpoint_touched(self)
	_inside = inside
