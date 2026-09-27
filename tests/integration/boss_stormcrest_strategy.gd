extends Node
## Records the strategy tape ADR 005's checks 1 and 2 replay against THE
## STORMCREST.
##
## The tape is the proof; this is only the pen. A scripted controller fights the
## real boss while every button it presses is written down, and the gate then
## replays those frames *blind* — no policy, no live reads — so what is checked
## is a fixed sequence of presses against the real fight, exactly as a human's
## run would be.
##
##   $GODOT --headless --fixed-fps 60 --path . \
##       res://tests/integration/boss_stormcrest_runner.tscn   (KAYA_CREST_MODE=record)
##
## WHY THIS EXISTS AND NOT tests/integration/boss_gate_strategy.gd
## ---------------------------------------------------------------
## That file is the Grove Warden's pen, and the Warden is a boss you can hit at
## any moment: its policy throws the blade whenever the blade is home and the
## range is right. Against the Stormcrest that policy spends most of the fight
## ringing the blade off an invulnerable bird — `stormcrest.gd.hurt()` refuses
## damage on every frame it is not roosting — and every one of those throws is a
## second of cooldown bought for nothing, during which it is stooping at her.
##
## So the one thing this policy does that that one does not is **wait for the
## window**. It throws only while the Stormcrest is on the ground with its wings
## folded, and it spends the rest of the cycle doing the two things that keep her
## alive: holding a blade-range standoff from the pad it is about to land on, and
## leaving the ground when the bore comes off that landing. Everything else here
## is smaller than its equivalent in the Warden's pen, not cleverer — including
## the aim, which is that file's own fix (`FormBase.run_axis()` writes `facing`
## from the movement axis, so a throw has to be preceded by a step toward the
## target or the blade flies backwards).

const Tape := preload("res://tests/integration/boss_gate_tape.gd")

## src/enemies/stormcrest.gd's `St`, which is boss_grove.gd's and tide_maw.gd's.
## Read rather than imported, because the gate's own attack tags depend on these
## six being these six.
const ST_IDLE := 0
const ST_WALK := 1
const ST_WINDUP := 2
const ST_AIR := 3
const ST_LAND := 4
const ST_SPRAY := 5

## The standoff, held against wherever the Stormcrest is about to roost. The
## blade's `max_range` is 118 px and it leaves Kaya's chest 8 px out, so this band
## sits inside the damage window with room for the gale to push her about.
var near := 62.0
var far := 96.0
## Never press attack outside this: a blade that turns back before it arrives is
## a second of cooldown bought for nothing.
var throw_min := 30.0
var throw_max := 112.0
## Frames of held movement toward the bird before the attack press. Three,
## because `Player._physics_process` polls input, then steps the form (which is
## where `facing` is written), then calls `try_attack` — so one frame of aim is
## read a tick late and two is the first that is certainly enough.
var aim_frames := 3
## The human form cuts a jump the moment the button lifts, so a dodge has to be
## HELD. 18 frames is the full 46 px, which clears a bore running 4 px off the
## floor with 39 px to spare.
var jump_hold := 18
## How far ahead of a bore's arrival to leave the ground, in seconds.
var dodge_lead := 0.34
var dodge_late := 0.06
## After a hit, disengage rather than stand in whatever just landed on her.
var panic_hold := 24
## Inside this its body is the danger and distance is the only answer.
var flee_gap := 44.0
## While it is in the air, being under it is what the feather volley punishes.
var under_gap := 46.0

var gate: Node = null
var max_frames := 5400            ## 90 s, ADR 005's defeat bound
var trace := false

var _aim := 0
var _jump_latch := 0
var _panic := 0
var _last_health := 5

func configure(d: Dictionary) -> void:
	for k: String in d.keys():
		if k in self:
			set(k, d[k])

func record(checks: Node) -> Dictionary:
	gate = checks
	trace = OS.get_environment("KAYA_CREST_TRACE") != ""
	await gate.stage_fight()

	var pl: Player = gate.pl
	var boss: Enemy = gate.boss
	_aim = 0
	_jump_latch = 0
	_panic = 0
	_last_health = Game.health

	var per_frame: Array = []
	var f := 0
	var low := Game.health
	var throws := 0
	var windows := 0
	var was_roosting := true
	var seen: Dictionary = {}
	var phase_at: Array = [0, -1, -1]
	while f < max_frames:
		var held := _decide(pl, boss)
		Tape.apply(held)
		per_frame.append(held)
		await get_tree().physics_frame
		f += 1
		low = mini(low, Game.health)
		for n: Node in gate.entity_children():
			if n is Blade and not seen.has(n.get_instance_id()):
				seen[n.get_instance_id()] = true
				throws += 1
		var roosting := _roosting(boss)
		if roosting and not was_roosting:
			windows += 1
		was_roosting = roosting
		var ph := int(boss.get("phase"))
		if ph > 0 and ph < phase_at.size() and phase_at[ph] < 0:
			phase_at[ph] = f
		if trace and f % 60 == 0:
			print("    t=%5.1f  kaya x=%6.1f floor=%s hp=%d | crest x=%6.1f y=%6.1f st=%d ph=%d hp=%2d | throws %d windows %d"
				% [float(f) / 60.0, pl.center().x, str(pl.on_floor), Game.health,
					boss.center().x, boss.center().y, int(boss.get("st")), ph,
					boss.health, throws, windows])
		if boss.defeated or pl.dead or Game.health <= 0:
			break
	Tape.release_all()
	print("    %d frames (%.1f s), %d throws over %d roost window(s), crest %d hp, kaya %d hearts (low %d)%s"
		% [f, float(f) / 60.0, throws, windows, boss.health, Game.health, low,
			"  DEFEATED" if boss.defeated else ""])
	print("    phase 2 at %s s, phase 3 at %s s"
		% [_secs(phase_at[1]), _secs(phase_at[2])])
	# A few idle frames so the kill sits inside the tape, not on its edge.
	for i in 6:
		per_frame.append([])
	return {
		"boss": gate.boss_id, "level": gate.level_id, "fps": 60,
		"source_sha": Tape.source_sha(gate.level_id, gate.boss_id),
		"recorded_frames": per_frame.size(),
		"frames": Tape.encode(per_frame),
		"outcome": {
			"boss_defeated": boss.defeated, "boss_health": boss.health,
			"hearts_left": Game.health, "lowest_hearts": low, "kaya_dead": pl.dead,
		},
	}

func _secs(frame: int) -> String:
	return "-" if frame < 0 else "%.1f" % (float(frame) / 60.0)

# ---------------------------------------------------------------- the policy
## In priority order:
##   1. just took a hit — get away from it
##   2. a bore is running the floor at her — jump, and HOLD the jump
##   3. its body is on top of her — run
##   4. it is ROOSTING — turn and throw, this is the only window
##   5. it is in the air — hold the standoff from the pad it will land on, and
##      do not stand under it
func _decide(pl: Player, boss: Enemy) -> Array:
	var held: Array = []
	var anchor := _anchor(boss)
	var dx := anchor - pl.center().x
	var toward := "right" if dx > 0.0 else "left"
	var away := "left" if dx > 0.0 else "right"
	var gap := absf(dx)

	if Game.health < _last_health:
		_panic = panic_hold
		_aim = 0
	_last_health = Game.health
	if _panic > 0:
		_panic -= 1
		held.append(away)
		return held

	if _jump_latch > 0:
		_jump_latch -= 1
		held.append("jump")
	elif pl.on_floor and _incoming_bore(pl):
		_jump_latch = jump_hold
		held.append("jump")

	if gap < flee_gap:
		held.append(away)
		return held

	if _roosting(boss):
		# The window. Aim, then throw: `facing` comes from the movement axis, so
		# the blade only goes where she last walked.
		if _aim <= 0 and _blade_is_home() and gap >= throw_min and gap <= throw_max:
			_aim = aim_frames
		if _aim > 0:
			_aim -= 1
			held.append(toward)
			if _aim == 0:
				held.append("attack")
			return held
		if gap > throw_max:
			held.append(toward)
		elif gap < throw_min:
			held.append(away)
		return held

	# Airborne: nothing to hit, so this is all positioning. Standing under it is
	# what the feather volley is for.
	_aim = 0
	if absf(boss.center().x - pl.center().x) < under_gap:
		held.append("left" if boss.center().x > pl.center().x else "right")
		return held
	if gap < near:
		held.append(away)
	elif gap > far:
		held.append(toward)
	return held

## Where the fight is about to be: the pad it has committed to while it stoops,
## and its own body the rest of the time.
func _anchor(boss: Enemy) -> float:
	var st := int(boss.get("st"))
	if st == ST_WINDUP or st == ST_AIR:
		return float(boss.get("roost_x")) + boss.box.x * 0.5
	return boss.center().x

func _roosting(boss: Enemy) -> bool:
	var st := int(boss.get("st"))
	return st == ST_IDLE or st == ST_LAND

func _blade_is_home() -> bool:
	for n: Node in gate.entity_children():
		if n is Blade and is_instance_valid(n):
			return false
	return true

## True when a hostile shot is running the floor at Kaya and this is the frame to
## leave the ground. Only shots at body height count: a feather falling out of the
## sky is dodged by not being under it, and jumping into one is worse than
## standing still.
func _incoming_bore(pl: Player) -> bool:
	var pr := pl.aabb()
	for n in get_tree().get_nodes_in_group(&"hostile_shots"):
		var s := n as Projectile
		if s == null or not is_instance_valid(s):
			continue
		if absf(s.vel.x) < 1.0 or absf(s.vel.y) > 40.0:
			continue
		var d := s.aabb().get_center().x - pr.get_center().x
		if signf(s.vel.x) * signf(d) >= 0.0:
			continue                          ## travelling away from her
		if s.pos.y + 6.0 < pr.position.y or s.pos.y > pr.position.y + pr.size.y:
			continue
		var eta := (absf(d) - pr.size.x * 0.5) / absf(s.vel.x)
		if eta > dodge_late and eta < dodge_lead:
			return true
	return false
