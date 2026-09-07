class_name Door
extends Node2D
## A locked door inside a level. Consumes one matching key on contact and then
## stays open for the rest of the visit.

const SIZE := Vector2(16, 16)
const CLOSED_FRAME := 0
const OPEN_FRAME := 1

var pos := Vector2.ZERO
var key_color := "yellow"
var level: Node = null
var world: TileWorld = null
var open := false
var _tile := Vector2i.ZERO
var _nudge := 0.0
var sprite: Sprite2D = null

func setup(p: Vector2, color: String) -> void:
	pos = p
	key_color = color
	_tile = Vector2i(int(p.x / TileData4.TILE_SIZE), int(p.y / TileData4.TILE_SIZE))

func _ready() -> void:
	add_to_group(&"doors")
	sprite = Sprite2D.new()
	sprite.centered = false
	sprite.region_enabled = true
	sprite.texture = load("res://assets/sprites/props.png")
	sprite.region_rect = Rect2(CLOSED_FRAME * 16, 0, 16, 16)
	sprite.modulate = _key_tint()
	add_child(sprite)
	position = pos.round()
	# A closed door is a solid tile; opening it punches a hole in the grid.
	if world != null:
		world.set_fg(_tile.x, _tile.y, _door_tile_id())

func _key_tint() -> Color:
	match key_color:
		"red": return Color(1.25, 0.72, 0.62)
		"cyan": return Color(0.7, 1.15, 1.25)
	return Color(1.2, 1.1, 0.6)

func _door_tile_id() -> int:
	return 25   # metal: solid, and never used for scenery

func aabb() -> Rect2:
	return Rect2(pos, SIZE)

func _physics_process(delta: float) -> void:
	if Game.sim_paused:
		return
	_nudge = maxf(0.0, _nudge - delta)
	if open:
		return
	var p: Player = level.player if level != null and level.get("player") != null else null
	if p == null or p.dead:
		return
	if not aabb().grow(2.0).intersects(p.aabb()):
		return
	if Game.use_key(key_color):
		_open()
	elif _nudge <= 0.0:
		_nudge = 0.6
		AudioManager.play("locked")
		if level.hud != null and level.hud.has_method("flash_message"):
			level.hud.flash_message("NEED THE %s KEY" % key_color.to_upper())

func _open() -> void:
	open = true
	AudioManager.play("door")
	sprite.region_rect = Rect2(OPEN_FRAME * 16, 0, 16, 16)
	if world != null:
		world.set_fg(_tile.x, _tile.y, 0)
	if level != null:
		level.on_tile_broken(_tile)
	Game.add_score(50)
