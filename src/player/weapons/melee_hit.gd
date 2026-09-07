class_name MeleeHit
extends Node2D
## A short-lived damage box parented to the world but following the attacker.
## Used by the fish's bite; any future melee weapon can reuse it.

var cfg: Dictionary = {}
var attacker: Player = null
var life := 0.14
var damage := 1
var reach := 10.0
var box := Vector2(14, 12)
var _hit: Array[int] = []
var sprite: Sprite2D = null

func setup(config: Dictionary, p: Player) -> void:
	cfg = config
	attacker = p
	life = float(cfg.get("life", 0.14))
	damage = int(cfg.get("damage", 1))
	reach = float(cfg.get("reach", 10.0))
	var hb: Dictionary = cfg.get("hitbox", {})
	box = Vector2(float(hb.get("w", 14)), float(hb.get("h", 12)))

func _ready() -> void:
	sprite = Sprite2D.new()
	sprite.centered = true
	sprite.region_enabled = true
	sprite.texture = load(String(cfg.get("sprite", "res://assets/sprites/projectiles.png")))
	var frames: Array = cfg.get("frames", [1])
	var fw := int(cfg.get("frame_w", 8))
	sprite.region_rect = Rect2(int(frames[0]) * fw, 0, fw, int(cfg.get("frame_h", 8)))
	add_child(sprite)

func aabb() -> Rect2:
	if attacker == null or not is_instance_valid(attacker):
		return Rect2()
	var c := attacker.center() + Vector2(attacker.facing * reach, 0.0)
	return Rect2(c - box * 0.5, box)

func _physics_process(delta: float) -> void:
	if Game.sim_paused:
		return
	if attacker == null or not is_instance_valid(attacker):
		queue_free()
		return
	life -= delta
	var r := aabb()
	position = r.get_center().round()
	sprite.modulate.a = clampf(life / maxf(0.01, float(cfg.get("life", 0.14))), 0.0, 1.0)
	for n in get_tree().get_nodes_in_group(&"enemies"):
		var e := n as Enemy
		if e == null or not e.active:
			continue
		var eid := e.get_instance_id()
		if _hit.has(eid):
			continue
		if r.intersects(e.aabb()):
			_hit.append(eid)
			e.hurt(damage, r.get_center())
	if life <= 0.0:
		queue_free()
