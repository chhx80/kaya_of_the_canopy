class_name HubDoor
extends Node2D
## A gateway on the overworld. Locked until its prerequisite level is done;
## shows a tick once its own level is cleared. Step onto it and press Up.

const SIZE := Vector2(16, 16)

var pos := Vector2.ZERO
var level_id := ""
var display_name := ""
var requires := ""
var requires_all := false
var hub: Node = null
var sprite: Sprite2D = null
var _t := 0.0

func setup(p: Vector2, e: Dictionary) -> void:
	pos = p
	level_id = String(e.get("level", ""))
	display_name = String(e.get("label", level_id.to_upper()))
	requires = String(e.get("requires", ""))
	requires_all = bool(e.get("requires_all", false))

func unlocked() -> bool:
	if requires_all:
		for id in LevelLoader.list_levels():
			if id == "hub" or id == "test_arena" or id == level_id:
				continue
			if not SaveManager.get_flag(id):
				return false
		return true
	return requires == "" or SaveManager.get_flag(requires)

func completed() -> bool:
	return SaveManager.get_flag(level_id)

func _ready() -> void:
	add_to_group(&"hub_doors")
	sprite = Sprite2D.new()
	sprite.centered = false
	sprite.region_enabled = true
	sprite.texture = load("res://assets/sprites/props.png")
	add_child(sprite)
	position = pos.round()
	_refresh()

const FRAME_LOCKED := 8
const FRAME_OPEN := 9
const FRAME_CLEARED := 10

func _refresh() -> void:
	var frame := FRAME_CLEARED if completed() else (FRAME_OPEN if unlocked() else FRAME_LOCKED)
	sprite.region_rect = Rect2(frame * 16, 0, 16, 16)
	sprite.modulate = Color(1, 1, 1) if unlocked() else Color(0.52, 0.5, 0.6)

func aabb() -> Rect2:
	return Rect2(pos, SIZE)

func _process(delta: float) -> void:
	_t += delta
	if unlocked() and not completed():
		sprite.modulate = Color(1, 1, 1).lerp(Color(1.4, 1.3, 0.8), 0.5 + 0.5 * sin(_t * 3.0))
