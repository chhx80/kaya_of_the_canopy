class_name Projectile
extends Node2D
## An enemy shot. Kept deliberately dumb: travel, hurt the player, die on solid
## geometry or when its life runs out.

const SIZE := Vector2(6, 6)

var cfg: Dictionary = {}
var world: TileWorld = null
var level: Node = null
var pos := Vector2.ZERO
var vel := Vector2.ZERO
var life := 3.0
var damage := 1
var sprite: Sprite2D = null

func setup(config: Dictionary, from: Vector2, direction: Vector2, w: TileWorld, lvl: Node) -> void:
	cfg = config
	world = w
	level = lvl
	pos = from - SIZE * 0.5
	vel = direction.normalized() * float(cfg.get("speed", 96.0))
	life = float(cfg.get("life", 3.0))
	damage = int(cfg.get("damage", 1))

func _ready() -> void:
	add_to_group(&"hostile_shots")
	sprite = Sprite2D.new()
	sprite.centered = true
	sprite.region_enabled = true
	sprite.texture = load("res://assets/sprites/projectiles.png")
	sprite.region_rect = Rect2(int(cfg.get("frame", 0)) * 8, 0, 8, 8)
	add_child(sprite)
	position = (pos + SIZE * 0.5).round()

func aabb() -> Rect2:
	return Rect2(pos, SIZE)

func _physics_process(delta: float) -> void:
	if Game.sim_paused:
		return
	life -= delta
	if life <= 0.0:
		queue_free()
		return
	vel.y += float(cfg.get("gravity", 0.0)) * delta
	pos += vel * delta
	position = (pos + SIZE * 0.5).round()
	sprite.rotation += delta * 9.0

	if world != null and TileCollision.has_flag(world, aabb(), TileData4.Flag.SOLID):
		if world.is_solid(int((pos.x + 3.0) / TileData4.TILE_SIZE),
				int((pos.y + 3.0) / TileData4.TILE_SIZE)):
			queue_free()
			return
	var p: Player = level.player if level != null and level.get("player") != null else null
	if p != null and not p.dead and aabb().intersects(p.aabb()):
		p.take_damage(damage, Vector2(signf(vel.x), 0.0))
		queue_free()
