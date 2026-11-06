class_name Player
extends Actor
## Kaya. Owns the current form (which does the moving), the sprite, the weapon
## and the damage/invulnerability state.

signal died()
signal form_changed(form_id: String)

const HURT_TIME := 0.35
const INVULN_TIME := 1.1
const KNOCKBACK := Vector2(110.0, -150.0)

## ---- Phase A render-only juice (docs/plan-art-motion.md). None of this ever
## writes to `facing`, `vel`, `pos` or any other physics state — it only reads
## them, the way _update_anim already did. See _update_anim()/_update_overlays().
const THROW_TIME := 0.17        ## 2 throw frames held on the air
const CATCH_TIME := 0.12        ## 1 catch frame held on the catch
## Phase F, docs/plan-art-motion.md: the idle dance. `_idle_t` is the one
## clock both beats share — dance is the FIRST beat at 5s, fidget the SECOND
## at 12s, so they never collide: landing the dance beat always resets the
## clock, so the fidget threshold is only ever reached on an idle stretch
## that did NOT just dance (its cooldown was still running). See
## _update_overlays().
const DANCE_IDLE_TIME := 5.0    ## seconds of true stillness before a dance
const DANCE_COOLDOWN := 15.0    ## seconds after a dance before another can start
const FIDGET_IDLE_TIME := 12.0  ## seconds of true stillness before a fidget
const FIDGET_PLAY_TIME := 0.5   ## 3 fidget frames at 6 fps, played once
const SQUASH_EASE_TIME := 0.12
const SQUASH_MAX := Vector2(1.15, 0.85)
const STRETCH_TIME := 0.10
const STRETCH_MAX := Vector2(0.85, 1.15)

var form: FormBase = null
var form_id := "human"
var input := InputState.new()
var control_enabled := true

var sprite: Sprite2D = null
var _frame_size := Vector2i(32, 40)
var _anim := "idle"
var _anim_t := 0.0
var _anim_i := 0

var invuln := 0.0
var hurt_t := 0.0
var dead := false
var weapon: WeaponBase = null

var _render_fsm := RenderFacingFSM.new()
var _prev_blade_state: int = WeaponBase.FlightState.NONE
var _throw_t := 0.0
var _catch_t := 0.0
var _idle_t := 0.0             ## Phase F: shared clock for the dance and fidget beats
var _fidget_play_t := 0.0
var _dance_play_t := 0.0
var _dance_cooldown_t := 0.0
var _squash_t := 0.0
var _squash_scale := Vector2.ONE
var _stretch_t := 0.0

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
	sprite.scale = Vector2.ONE
	sprite.position = Vector2.ZERO
	_set_anim("idle")
	# A transformation is a hard cut, not a turn: render_facing must not carry
	# a mid-turn lag or a squash/stretch in flight across the shape change.
	_render_fsm.reset(facing)
	_throw_t = 0.0
	_catch_t = 0.0
	_idle_t = 0.0
	_fidget_play_t = 0.0
	_dance_play_t = 0.0
	_dance_cooldown_t = 0.0
	_squash_t = 0.0
	_stretch_t = 0.0
	_prev_blade_state = WeaponBase.FlightState.NONE
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

	var fall_speed := vel.y
	step_motion(delta)
	_note_motion_events(fall_speed)

	if touching_hazard():
		take_damage(1, Vector2(-facing, 0))
	if fell_out_of_world():
		kill()

	_update_anim(delta)
	_sync_render_position()

## The render beats a tick of motion sets off: landing dust and squash, takeoff
## kick and stretch. Split out of _physics_process so tools/clipgate.sh can drive
## the exact render path the game runs, against the prover's simulation, without
## also running the damage and death rules.
func _note_motion_events(fall_speed: float) -> void:
	if on_floor and not was_on_floor:
		var land_min := Fx.timing("land_dust_min_fall", 170.0)
		if fall_speed >= land_min:
			Fx.burst("dust", feet())
			Fx.landing_dip()
			# Proportional: a kerb-height landing barely squashes, a fall from
			# terminal velocity hits the cap. Render-only — the hitbox (`box`)
			# never moves, only `sprite.scale` in _update_anim().
			var span := maxf(1.0, (form.max_fall if form != null else 330.0) - land_min)
			var intensity := clampf((fall_speed - land_min) / span, 0.0, 1.0)
			_squash_t = SQUASH_EASE_TIME
			_squash_scale = Vector2.ONE.lerp(SQUASH_MAX, intensity)
	elif not on_floor and was_on_floor and vel.y < 0.0:
		# Left the ground going UP: a jump, not a walk off a ledge (which
		# leaves vel.y at gravity's small positive nudge, not jump_vel).
		Fx.burst("takeoff_kick", feet())
		_stretch_t = STRETCH_TIME

# ---------------------------------------------------------------- damage
func take_damage(amount: int, from_dir: Vector2 = Vector2.ZERO) -> void:
	if invuln > 0.0 or dead:
		return
	Game.damage(amount)
	AudioManager.play("hurt")
	Fx.shake("hurt")
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
	# `render_facing` lags `facing` through a turn/skid before the sprite's
	# flip catches up — see RenderFacingFSM. It only ever reads `facing`/`vel`
	# /`on_floor`/the input axis and writes its own fields, never physics.
	var prev_render_state: int = _render_fsm.state
	# Phase B: the bird (move_mode "fly") always resolves a reversal as the
	# 2-frame banking pair — see RenderFacingFSM's `flying` parameter. Every
	# other form passes the default false and is bit-identical to Phase A.
	_render_fsm.update(delta, facing, vel.x, on_floor, input.axis_x(),
		form.move_mode == "fly")
	if on_floor and _render_fsm.state == RenderFacingFSM.State.TURN \
			and prev_render_state != RenderFacingFSM.State.TURN:
		Fx.burst("turn_scuff", feet(), Vector2(-float(facing), 0.0))
	elif _render_fsm.state == RenderFacingFSM.State.SKID \
			and prev_render_state != RenderFacingFSM.State.SKID:
		Fx.burst("dust", feet())   # the lean-back's heel puff — the existing emitter
	_update_overlays(delta)

	var wanted := _resolve_anim_state()
	_set_anim(_pose_anim(wanted))
	var a: Dictionary = form.anim(_anim)
	var frames: Array = a.get("frames", [0])
	var fps := float(a.get("fps", 1))
	if _anim == "turn":
		# The turn strip is paced by the FSM's own clock, not by fps/looping —
		# that clock is what the coyote-time guard test measures.
		_anim_i = clampi(_render_fsm.turn_frame_index(), 0, frames.size() - 1)
	elif fps > 0.0 and frames.size() > 1:
		_anim_t += delta
		while _anim_t >= 1.0 / fps:
			_anim_t -= 1.0 / fps
			_anim_i += 1
		# "loop": false plays the list once and holds the last frame. That is
		# what makes a jump read as anticipate -> launch -> rise -> hold, rather
		# than cycling back through the crouch in mid-air.
		if bool(a.get("loop", true)):
			_anim_i %= frames.size()
		else:
			_anim_i = mini(_anim_i, frames.size() - 1)
	else:
		_anim_i = 0
	var frame := int(frames[_anim_i % frames.size()])
	_show_frame(frame)
	# Flash while invulnerable.
	sprite.visible = not (invuln > 0.0 and fmod(invuln, 0.16) < 0.08)
	_apply_squash_stretch(delta, KayaPose.allows_scale(wanted, _anim))
	_place_against_walls(frame)

## The render-only nudges that keep the drawn frame out of the rock: down under a
## ceiling while airborne, sideways off a wall. A squash is 15% wider than the
## frame; where that much more cannot be shifted clear, the squash is dropped
## for the tick rather than drawn into the wall. See KayaPose.
func _place_against_walls(frame: int) -> void:
	var pose: Dictionary = form.cfg.get("pose", {})
	var dy := KayaPose.nudge_y(_anim, form, world, pos, box, on_floor)
	sprite.position.y += dy
	var rows := KayaPose.bounds(String(pose.get("bounds", "")))
	if frame >= rows.size() or world == null:
		return
	var cap := float(pose.get("max_nudge_x", 0.0))
	var hb := Rect2(pos.round(), box)
	var org := pos.round() + sprite.position + sprite.offset * sprite.scale
	var dx := KayaPose.nudge_x(rows[frame], sprite.flip_h, _frame_size.x, org, sprite.scale,
		world, hb, cap)
	if dx == 0.0 and sprite.scale != Vector2.ONE and KayaPose.wall_overlap(rows[frame],
			sprite.flip_h, _frame_size.x, org, sprite.scale, world, hb) != Vector2.ZERO:
		sprite.scale = Vector2.ONE
		sprite.position = Vector2(0.0, dy)
		org = pos.round() + sprite.position + sprite.offset
		dx = KayaPose.nudge_x(rows[frame], sprite.flip_h, _frame_size.x, org, Vector2.ONE,
			world, hb, cap)
	sprite.position.x += dx

## Point the sprite at sheet cell `frame`, facing the way render_facing says,
## with the cell placed so the hitbox sits at its feet. tools/clipgate.sh's sweep
## calls this directly to draw frames no proof tape reaches.
func _show_frame(frame: int) -> void:
	sprite.region_rect = Rect2(frame * _frame_size.x, 0, _frame_size.x, _frame_size.y)
	sprite.flip_h = _render_fsm.render_facing < 0
	# Sprite is wider than the hitbox; centre it and sit it on the feet.
	var hb: Dictionary = form.hitbox()
	var ox := -float(hb.get("ox", 3))
	var oy := -float(hb.get("oy", 2))
	sprite.offset = Vector2(ox, oy)
	if sprite.flip_h:
		sprite.offset.x = -(float(_frame_size.x) + ox - box.x)

## The animation actually drawn: `wanted` unless the space she is in says
## otherwise. Render-only; see KayaPose.
func _pose_anim(wanted: String) -> String:
	return KayaPose.choose(wanted, form, world, pos, box, on_floor,
		world != null and submerged(), _render_fsm.render_facing < 0)

## Which animation state to show this tick, highest priority first. Hurt and
## the weapon-driven throw/catch beats pre-empt everything; shouldering and
## skid/turn pre-empt the base locomotion states `form.anim_for()` returns.
## Every overlay is gated on `form.has_anim()` so a form that has not drawn
## the frames for it (every animal form, still Phase B) falls straight
## through to its own base animation instead of showing frame 0 of nothing.
func _resolve_anim_state() -> String:
	if hurt_t > 0.0:
		return "hurt"
	if _catch_t > 0.0 and form.has_anim("catch"):
		return "catch"
	if _throw_t > 0.0 and form.has_anim("throw"):
		return "throw"
	if form.break_progress > 0.0 and form.has_anim("push"):
		return "push"
	if _render_fsm.state == RenderFacingFSM.State.SKID and form.has_anim("skid"):
		return "skid"
	if _render_fsm.state == RenderFacingFSM.State.TURN and form.has_anim("turn"):
		return "turn"
	# Phase F: the dance and the fidget are mutually exclusive by construction
	# (see _update_overlays()) — at most one of their play timers is ever
	# positive at once — but dance is checked first since it is the primary
	# idle beat and the fidget is the fallback.
	if _dance_play_t > 0.0 and form.has_anim("dance"):
		return "dance"
	if _fidget_play_t > 0.0 and form.has_anim("fidget"):
		return "fidget"
	return form.anim_for(self)

## Timers for the overlays above. Everything here is read-only against the
## systems it watches: the blade's own flight state (WeaponBase.flight_state,
## never written to from here) and the input bits already gathered this tick.
func _update_overlays(delta: float) -> void:
	var blade_state: int = weapon.flight_state() if weapon != null else WeaponBase.FlightState.NONE
	if blade_state != WeaponBase.FlightState.NONE and _prev_blade_state == WeaponBase.FlightState.NONE:
		_throw_t = THROW_TIME       # just fired
	elif blade_state == WeaponBase.FlightState.NONE and _prev_blade_state != WeaponBase.FlightState.NONE:
		_catch_t = CATCH_TIME       # the only way a live blade disappears mid-level
	_prev_blade_state = blade_state
	_throw_t = maxf(0.0, _throw_t - delta)
	_catch_t = maxf(0.0, _catch_t - delta)

	# The cooldown ticks down in real time, idle or not — a player who dances,
	# then immediately moves off and comes back, should not get a second dance
	# for free. It never gates the fidget, which has no cooldown of its own.
	_dance_cooldown_t = maxf(0.0, _dance_cooldown_t - delta)

	if not _is_truly_idle():
		# Any input, damage or ground loss cancels whichever beat is playing
		# on the very next frame — the dance must never cost a frame of
		# responsiveness, the same rule the turn lives under (Phase A).
		_idle_t = 0.0
		_fidget_play_t = 0.0
		_dance_play_t = 0.0
		return
	if _dance_play_t > 0.0:
		_dance_play_t = maxf(0.0, _dance_play_t - delta)
		return
	if _fidget_play_t > 0.0:
		_fidget_play_t = maxf(0.0, _fidget_play_t - delta)
		return
	_idle_t += delta
	if _idle_t >= DANCE_IDLE_TIME and _dance_cooldown_t <= 0.0 and form.has_anim("dance"):
		_idle_t = 0.0
		var da: Dictionary = form.anim("dance")
		var dframes: Array = da.get("frames", [0])
		var dfps: float = maxf(1.0, float(da.get("fps", 8.0)))
		_dance_play_t = float(dframes.size()) / dfps
		_dance_cooldown_t = DANCE_COOLDOWN
	elif _idle_t >= FIDGET_IDLE_TIME:
		_idle_t = 0.0
		_fidget_play_t = FIDGET_PLAY_TIME

## True only with no input bit held, feet on the ground, no knockback, not
## mid-shoulder and not mid-turn — the same "never costs a frame of
## responsiveness" rule Phase F's dance is built on, applied here first.
func _is_truly_idle() -> bool:
	return form != null and on_floor and hurt_t <= 0.0 and form.break_progress <= 0.0 \
		and absf(vel.x) < 1.0 and absf(vel.y) < 1.0 \
		and not (input.left or input.right or input.up or input.down \
			or input.jump or input.attack) \
		and _render_fsm.state == RenderFacingFSM.State.NORMAL

## Landing squash / launch stretch: a render-space scale on `sprite` only,
## eased back to 1.0. The hitbox (`box`) is never touched — see step_motion()
## in actor.gd, which this never calls into.
func _apply_squash_stretch(delta: float, allowed: bool = true) -> void:
	var scale := Vector2.ONE
	if not allowed:
		_squash_t = maxf(0.0, _squash_t - delta)
		_stretch_t = maxf(0.0, _stretch_t - delta)
	elif _squash_t > 0.0:
		var t := _squash_t / SQUASH_EASE_TIME
		scale = Vector2.ONE.lerp(_squash_scale, t)
		_squash_t = maxf(0.0, _squash_t - delta)
	elif _stretch_t > 0.0:
		var t := _stretch_t / STRETCH_TIME
		var want := Vector2.ONE.lerp(STRETCH_MAX, t)
		# Under a ceiling the stretch would draw into the rock; drop it for the
		# tick and let it decay, as a blocked squash does.
		if KayaPose.allows_stretch(form, _anim, world, pos, box, want.y):
			scale = want
		_stretch_t = maxf(0.0, _stretch_t - delta)
	sprite.scale = scale
	# Keep the feet and the horizontal centre pinned to the hitbox (`box`) as
	# the sprite scales, so a squash reads as weight into the ground rather
	# than the whole sprite sinking or drifting sideways.
	sprite.position = Vector2(box.x * 0.5 * (1.0 - scale.x), box.y * (1.0 - scale.y))

func _sync_render_position() -> void:
	position = pos.round()
