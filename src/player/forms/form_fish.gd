extends FormBase
## Fish: free eight-way movement in water, helpless out of it. The air timer is
## the whole tension of a water level — you always know how far the next pool is.

var air_left := 0.0
## Phase B, docs/plan-art-motion.md: read-only cosmetic timers, never fed back
## into vel/pos/facing. `_burst_t` holds the burst-stroke frame for a beat
## after a swim stroke starts from near-standstill; `_prev_speed` is what
## detects that transition.
var _burst_t := 0.0
var _prev_speed := 0.0

func configure(d: Dictionary) -> void:
	super.configure(d)
	air_left = float(cfg.get("air_seconds", 2.6))

func step(p: Actor, input: InputState, delta: float) -> void:
	_burst_t = maxf(0.0, _burst_t - delta)
	var wet := p.in_water()
	if wet:
		air_left = float(cfg.get("air_seconds", 2.6))
		_swim(p, input, delta)
	else:
		air_left -= delta
		_prev_speed = 0.0
		_flop(p, input, delta)
		if air_left <= 0.0 and p is Player:
			# Running out of air turns Kaya back rather than killing her. Dying
			# to a mechanic you have not been taught reads as a bug, and it made
			# a beached fish a dead end. The air meter still creates the
			# pressure; a transform pad is just the faster way back.
			if String(cfg.get("out_of_water", "revert")) == "die":
				(p as Player).kill()
			else:
				sfx("transform")
				(p as Player).set_form("human")

func _swim(p: Actor, input: InputState, delta: float) -> void:
	var was_still := _prev_speed < 8.0
	var want := Vector2(input.axis_x(), input.axis_y())
	if want.length() > 1.0:
		want = want.normalized()
	var top := float(cfg.get("swim_speed", 92.0))
	# Every target is expressed in the water's frame: `current` is the water, and
	# the fish swims relative to it. Swimming into a 68 px/s push at 92 px/s of
	# its own makes 24 px/s of headway, which is the whole of World 2's tension.
	if want.length() > 0.01:
		p.vel = p.vel.move_toward(want * top + current,
			float(cfg.get("swim_accel", 620.0)) * delta)
		if absf(want.x) > 0.01:
			p.facing = 1 if want.x > 0.0 else -1
		# A burst flash for the first stroke out of a standstill — cosmetic
		# only, held by anim_for() below via _burst_t.
		if was_still and p.vel.length() >= 8.0 and has_anim("burst"):
			_burst_t = 0.14
	else:
		p.vel = p.vel.move_toward(current, float(cfg.get("swim_drag", 420.0)) * delta)
	# Break the surface with a hop so you can cross a lip of land.
	if input.jump_pressed and not p.submerged():
		p.vel.y = float(cfg.get("surface_hop", -150.0)) + current.y
		# A splash at the break — purely cosmetic, and safe to call from any
		# context FormBase runs in (the real game, tools/test.sh under ADR 003,
		# the Route Prover): Fx.burst() is a no-op wherever it has no live
		# ParticleField, and never feeds anything back into `p`.
		Fx.burst("splash", p.center())
	_prev_speed = p.vel.length()

func _flop(p: Actor, input: InputState, delta: float) -> void:
	tick_timers(p, input, delta)
	run_axis(p, input.axis_x(), delta)
	apply_gravity(p, delta, false)
	if can_jump_now(p):
		do_jump(p)

func anim_for(p: Actor) -> String:
	if p.in_water():
		if _burst_t > 0.0 and has_anim("burst"):
			return "burst"
		return "swim" if p.vel.length() > 10.0 else "idle"
	return "flop"

## 0..1 — drawn as an air meter by the HUD.
func air_fraction() -> float:
	var total := float(cfg.get("air_seconds", 2.6))
	return clampf(air_left / total, 0.0, 1.0) if total > 0.0 else 1.0
