class_name Player
extends Actor
## Kaya. Owns the current form (which does the moving), the sprite, the weapon
## and the damage/invulnerability state.

signal died()
signal form_changed(form_id: String)

const HURT_TIME := 0.35
const INVULN_TIME := 1.1
const KNOCKBACK := Vector2(110.0, -150.0)

var form: FormBase = null
var form_id := "human"
var input := InputState.new()
var control_enabled := true

var sprite: Sprite2D = null
var _frame_size := Vector2i(16, 24)
var _anim := "idle"
var _anim_t := 0.0
var _anim_i := 0

var invuln := 0.0
var hurt_t := 0.0
var dead := false
var weapon: WeaponBase = null

func _ready() -> void:
	sprite = Sprite2D.new()
	sprite.centered = false
	sprite.region_enabled = true
	add_child(sprite)
	set_form(form_id)


func set_form(new_id: String) -> void:
	var f := FormBase.load_form(new_id)
	if f == null:
		return
	# Keep the feet planted when the hitbox height changes.
	var old_bottom := pos.y + box.y
	var old_cx := pos.x + box.x * 0.5
	form = f
	form_id = new_id
	var hb: Dictionary = form.hitbox()
	box = Vector2(float(hb.get("w", 10)), float(hb.get("h", 22)))
	pos = Vector2(old_cx - box.x * 0.5, old_bottom - box.y)
	_frame_size = form.frame_size()
	var wid := form.weapon_id()
	weapon = WeaponBase.load_weapon(wid) if wid != "" else null
	sprite.texture = load(form.sprite_path())
	sprite.region_rect = Rect2(0, 0, _frame_size.x, _frame_size.y)
	_set_anim("idle")
	form_changed.emit(new_id)

func _physics_process(delta: float) -> void:
	if Game.sim_paused or dead:
		_sync_render_position()
		return
	if control_enabled and hurt_t <= 0.0:
		input.poll()
	else:
		input.clear()

	hurt_t = maxf(0.0, hurt_t - delta)
	invuln = maxf(0.0, invuln - delta)

	if weapon != null:
		weapon.tick(delta)
	if hurt_t <= 0.0 and form != null:
		form.update(self, input, delta)
		if form.can_attack and weapon != null and input.attack_pressed:
			weapon.try_attack(self)
	else:
		vel.y = minf(vel.y + form.gravity * delta, form.max_fall)
		vel.x = move_toward(vel.x, 0.0, 260.0 * delta)

	step_motion(delta)

	if touching_hazard():
		take_damage(1, Vector2(-facing, 0))
	if fell_out_of_world():
		kill()

	_update_anim(delta)
	_sync_render_position()

# ---------------------------------------------------------------- damage
func take_damage(amount: int, from_dir: Vector2 = Vector2.ZERO) -> void:
	if invuln > 0.0 or dead:
		return
	Game.damage(amount)
	AudioManager.play("hurt")
	invuln = INVULN_TIME
	hurt_t = HURT_TIME
	var dir := -1.0 if from_dir.x > 0.0 else 1.0
	if is_zero_approx(from_dir.x):
		dir = -float(facing)
	vel = Vector2(KNOCKBACK.x * dir, KNOCKBACK.y)
	if Game.health <= 0:
		kill()

func kill() -> void:
	if dead:
		return
	dead = true
	AudioManager.play("die")
	died.emit()

func heal(n: int) -> void:
	Game.add_health(n)

func equip(weapon_id: String) -> void:
	var w := WeaponBase.load_weapon(weapon_id)
	if w != null:
		weapon = w

# ---------------------------------------------------------------- animation
func _set_anim(name: String) -> void:
	if _anim == name:
		return
	_anim = name
	_anim_t = 0.0
	_anim_i = 0

func _update_anim(delta: float) -> void:
	if form == null:
		return
	_set_anim("hurt" if hurt_t > 0.0 else form.anim_for(self))
	var a: Dictionary = form.anim(_anim)
	var frames: Array = a.get("frames", [0])
	var fps := float(a.get("fps", 1))
	if fps > 0.0 and frames.size() > 1:
		_anim_t += delta
		while _anim_t >= 1.0 / fps:
			_anim_t -= 1.0 / fps
			_anim_i = (_anim_i + 1) % frames.size()
	else:
		_anim_i = 0
	var frame := int(frames[_anim_i % frames.size()])
	sprite.region_rect = Rect2(frame * _frame_size.x, 0, _frame_size.x, _frame_size.y)
	sprite.flip_h = facing < 0
	# Sprite is wider than the hitbox; centre it and sit it on the feet.
	var hb: Dictionary = form.hitbox()
	var ox := -float(hb.get("ox", 3))
	var oy := -float(hb.get("oy", 2))
	sprite.offset = Vector2(ox, oy)
	if sprite.flip_h:
		sprite.offset.x = -(float(_frame_size.x) + ox - box.x)
	# Flash while invulnerable.
	sprite.visible = not (invuln > 0.0 and fmod(invuln, 0.16) < 0.08)

func _sync_render_position() -> void:
	position = pos.round()
