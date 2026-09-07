class_name Door
extends Node2D
## A locked door inside a level. Consumes one matching key on contact and then
## stays open for the rest of the visit.

## A door has to be as tall as the thing walking through it. One tile is 16 px
## and the human hitbox is 22 px, so a one-tile doorway is a wall with a gap you
## can see through and never enter.
const HEIGHT_TILES := 2
const SIZE := Vector2(16, 16 * HEIGHT_TILES)
const CLOSED_FRAME := 0
const OPEN_FRAME := 1

var pos := Vector2.ZERO
var key_color := "yellow"
var level: Node = null
var world: TileWorld = null
var open := false
var _tile := Vector2i.ZERO      ## the bottom tile; the door extends upward
var _nudge := 0.0
var _sprites: Array[Sprite2D] = []

func setup(p: Vector2, color: String) -> void:
	pos = p
	key_color = color
	_tile = Vector2i(int(p.x / TileData4.TILE_SIZE), int(p.y / TileData4.TILE_SIZE))

## Every tile the door occupies, bottom first.
func tiles() -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	for i in HEIGHT_TILES:
		out.append(Vector2i(_tile.x, _tile.y - i))
	return out

func _ready() -> void:
	add_to_group(&"doors")
	var tex: Texture2D = load("res://assets/sprites/props.png")
	for i in HEIGHT_TILES:
		var s := Sprite2D.new()
		s.centered = false
		s.region_enabled = true
		s.texture = tex
		s.region_rect = Rect2(CLOSED_FRAME * 16, 0, 16, 16)
		s.modulate = _key_tint()
		s.position = Vector2(0, -16 * i)
		add_child(s)
		_sprites.append(s)
	position = pos.round()
	# A closed door is solid across its whole height; opening it punches the
	# full-height hole back out of the grid.
	if world != null:
		for t in tiles():
			world.set_fg(t.x, t.y, _door_tile_id())

func _key_tint() -> Color:
	match key_color:
		"red": return Color(1.25, 0.72, 0.62)
		"cyan": return Color(0.7, 1.15, 1.25)
	return Color(1.2, 1.1, 0.6)

func _door_tile_id() -> int:
	return 25   # metal: solid, and never used for scenery

func aabb() -> Rect2:
	return Rect2(pos - Vector2(0, 16 * (HEIGHT_TILES - 1)), SIZE)

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
	for s in _sprites:
		s.region_rect = Rect2(OPEN_FRAME * 16, 0, 16, 16)
	if world != null:
		for t in tiles():
			world.set_fg(t.x, t.y, 0)
	if level != null:
		level.on_tile_broken(_tile)
	Game.add_score(50)
