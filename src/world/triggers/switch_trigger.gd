class_name SwitchTrigger
extends Node2D
## A lever that flips a switch group, swapping which half of the paired blocks
## is solid. Hit it by walking into it or by catching it with the blade.

const SIZE := Vector2(14, 10)
const OFF_FRAME := 3
const ON_FRAME := 4

var pos := Vector2.ZERO
var group := 1
var level: Node = null
var world: TileWorld = null
var on := false
var _cooldown := 0.0
var sprite: Sprite2D = null

func setup(p: Vector2, grp: int, starts_on: bool = false) -> void:
	pos = p
	group = grp
	on = starts_on

func _ready() -> void:
	add_to_group(&"switches")
	sprite = Sprite2D.new()
	sprite.centered = false
	sprite.region_enabled = true
	sprite.texture = load("res://assets/sprites/props.png")
	sprite.offset = Vector2(-1, -5)
	sprite.modulate = Color(1.2, 1.1, 0.6) if group == 1 else Color(0.9, 0.75, 1.2)
	add_child(sprite)
	position = pos.round()
	if world != null:
		world.set_switch(group, on)
	_refresh()

func aabb() -> Rect2:
	return Rect2(pos, SIZE)

func _refresh() -> void:
	sprite.region_rect = Rect2((ON_FRAME if on else OFF_FRAME) * 16, 0, 16, 16)

func toggle() -> void:
	if _cooldown > 0.0:
		return
	_cooldown = 0.45
	on = not on
	if world != null:
		world.set_switch(group, on)
	_refresh()
	AudioManager.play("switch")
	if level != null:
		level.on_switch_toggled(group)

func _physics_process(delta: float) -> void:
	if Game.sim_paused:
		return
	_cooldown = maxf(0.0, _cooldown - delta)
	var p: Player = level.player if level != null and level.get("player") != null else null
	if p != null and not p.dead and aabb().intersects(p.aabb()):
		toggle()
