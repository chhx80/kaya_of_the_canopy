class_name LevelExit
extends Node2D
## The totem gateway that ends a level. Reverts Kaya to her human form first,
## so a transformation can never leak into the hub.

const SIZE := Vector2(16, 16)

var pos := Vector2.ZERO
var level: Node = null
var _fired := false
var _t := 0.0
var sprite: Sprite2D = null

func setup(p: Vector2) -> void:
	pos = p

func _ready() -> void:
	add_to_group(&"triggers")
	sprite = Sprite2D.new()
	sprite.centered = false
	sprite.region_enabled = true
	sprite.texture = load("res://assets/sprites/props.png")
	sprite.region_rect = Rect2(2 * 16, 0, 16, 16)   # frame 2 = totem gateway
	add_child(sprite)
	position = pos.round()

func aabb() -> Rect2:
	return Rect2(pos, SIZE)

func _physics_process(delta: float) -> void:
	if _fired or Game.sim_paused:
		return
	_t += delta
	sprite.modulate = Color(1, 1, 1).lerp(Color(1.4, 1.3, 0.7), 0.5 + 0.5 * sin(_t * 3.0))
	var p: Player = level.player if level != null and level.get("player") != null else null
	if p == null or p.dead:
		return
	if aabb().intersects(p.aabb()):
		_fired = true
		if p.form_id != "human":
			p.set_form("human")
		p.control_enabled = false
		level.complete()
