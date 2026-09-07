class_name Pickup
extends Node2D
## Gems, hearts and keys. Bobs in place, collected on overlap with the player.
## Drops from enemies get a short toss so they read as loot rather than scenery.

const FRAMES := {"gem": 0, "heart": 1, "key_yellow": 2, "key_red": 3, "key_cyan": 4}
const SIZE := Vector2(12, 12)

var kind := "gem"
var pos := Vector2.ZERO
var vel := Vector2.ZERO
var world: TileWorld = null
var level: Node = null
var tossed := false
var _t := 0.0
var _taken := false
var sprite: Sprite2D = null

func setup(k: String, p: Vector2, from_drop: bool = false) -> void:
	kind = k
	pos = p
	tossed = from_drop
	if from_drop:
		vel = Vector2(randf_range(-30.0, 30.0), -130.0)

func _ready() -> void:
	add_to_group(&"pickups")
	sprite = Sprite2D.new()
	sprite.centered = false
	sprite.region_enabled = true
	sprite.texture = load("res://assets/sprites/pickups.png")
	sprite.region_rect = Rect2(int(FRAMES.get(kind, 0)) * 16, 0, 16, 16)
	sprite.offset = Vector2(-2, -2)
	add_child(sprite)
	position = pos.round()

func aabb() -> Rect2:
	return Rect2(pos, SIZE)

func _physics_process(delta: float) -> void:
	if Game.sim_paused or _taken:
		return
	_t += delta
	if tossed and world != null:
		vel.y = minf(vel.y + 700.0 * delta, 300.0)
		var r := TileCollision.move_x(world, aabb(), vel.x * delta)
		var r2 := TileCollision.move_y(world, r.rect, vel.y * delta)
		pos = r2.rect.position
		if r2.on_floor:
			vel = Vector2.ZERO
			tossed = false
	var bob := 0.0 if tossed else sin(_t * 3.4) * 1.5
	position = (pos + Vector2(0, bob)).round()

	var p: Player = level.player if level != null and level.get("player") != null else null
	if p != null and not p.dead and aabb().intersects(p.aabb()):
		_collect(p)

func _collect(p: Player) -> void:
	_taken = true
	match kind:
		"gem":
			Game.add_gem(1)
			AudioManager.play("gem")
		"heart":
			p.heal(1)
			AudioManager.play("heal")
		"key_yellow": Game.add_key("yellow"); AudioManager.play("key")
		"key_red": Game.add_key("red"); AudioManager.play("key")
		"key_cyan": Game.add_key("cyan"); AudioManager.play("key")
	queue_free()
