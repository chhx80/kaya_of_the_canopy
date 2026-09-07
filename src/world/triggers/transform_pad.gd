class_name TransformPad
extends Node2D
## Steps Kaya into (or out of) an animal form. Pads are one-way by design: the
## level decides where each form starts and ends, so a form can never be carried
## somewhere it would break the puzzle.

const SIZE := Vector2(16, 8)
const FRAMES := {"frog": 5, "fish": 6, "bird": 7}

var pos := Vector2.ZERO
var form_id := "frog"
var level: Node = null
var _cooldown := 0.0
var _t := 0.0
var sprite: Sprite2D = null

func setup(p: Vector2, id: String) -> void:
	pos = p
	form_id = id

func _ready() -> void:
	add_to_group(&"pads")
	sprite = Sprite2D.new()
	sprite.centered = false
	sprite.region_enabled = true
	sprite.texture = load("res://assets/sprites/props.png")
	sprite.region_rect = Rect2(int(FRAMES.get(form_id, 5)) * 16, 0, 16, 16)
	sprite.offset = Vector2(0, -8)
	add_child(sprite)
	position = pos.round()

func aabb() -> Rect2:
	return Rect2(pos, SIZE)

func _physics_process(delta: float) -> void:
	if Game.sim_paused:
		return
	_t += delta
	_cooldown = maxf(0.0, _cooldown - delta)
	sprite.modulate = Color(1, 1, 1).lerp(Color(1.5, 1.4, 1.0), 0.5 + 0.5 * sin(_t * 4.0))
	if _cooldown > 0.0:
		return
	var p: Player = level.player if level != null and level.get("player") != null else null
	if p == null or p.dead or p.form_id == form_id:
		return
	if aabb().grow(3.0).intersects(p.aabb()):
		_cooldown = 0.8
		AudioManager.play("transform")
		p.set_form(form_id)
		if level.hud != null and level.hud.has_method("flash_message"):
			var label: String = p.form.cfg.get("display_name", form_id.to_upper())
			level.hud.flash_message(label)
