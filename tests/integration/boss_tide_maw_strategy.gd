extends Node
## Records the strategy tape ADR 005's checks 1 and 2 replay against THE TIDE MAW.
##
## The tape is the proof; this is only the pen. A scripted controller fights the
## real boss while every button it presses is written down, and the gate then
## replays those frames *blind* — no policy, no live reads — so what is checked
## is a fixed sequence of presses against the real fight, exactly as a human's
## run would be.
##
##   $GODOT --headless --fixed-fps 60 --path . \
##       res://tests/integration/boss_tide_maw_runner.tscn   (with KAYA_TIDE_MODE=record)
##
## WHY THIS EXISTS AND NOT tests/integration/boss_gate_strategy.gd
## ---------------------------------------------------------------
## That file is the Grove Warden's pen and it cannot hold this one, for a reason
## worth writing down because it is a real defect in a shipped policy and not a
## difference of taste:
##
##   **it throws the blade backwards.** `FormBase.run_axis()` sets `p.facing`
##   from the movement axis and `Blade.setup()` reads `p.facing`, so the
##   direction Kaya last *walked* is the direction the blade flies. That policy
##   holds a standoff by stepping AWAY when the boss is inside `near` and
##   holding nothing in the band — so on a slow boss it spends most of the fight
##   facing away from the thing it is aiming at. Measured against the Maw:
##   a hundred and more attempts across two runs of `--record`, best result six
##   damage of eighteen in the full ninety seconds, while the blade probe
##   (`KAYA_BOSSGATE_MODE=probe`) shows nine damage in TEN seconds from a
##   standing throw at any gap from 40 to 104 px. The weapon was never the
##   problem.
##
## So the one thing this policy does that that one does not is **aim**: a throw
## is preceded by AIM_FRAMES of held movement toward the Maw, and the attack
## button is only pressed on a frame where Kaya is already facing it. Everything
## else here is smaller than its equivalent there, not cleverer.

const Tape := preload("res://tests/integration/boss_gate_tape.gd")

## The standoff. The blade probe puts the damage window at 40-104 px of centre
## separation; this sits inside it with room to drift. Wider than it needs to be
## on purpose: the Maw walks at 44-74 px/s and Kaya runs at 108, so holding a
## band costs nothing, and a band that needs constant correction is a band that
## spends the fight walking rather than throwing.
var near := 62.0
var far := 96.0
## Never press attack outside this, because a blade that turns back before it
## arrives is a second of cooldown bought for nothing.
var throw_min := 34.0
var throw_max := 112.0
## Frames of held movement toward the Maw before the attack press. Three,
## because `Player._physics_process` polls input, then steps the form (which is
## where `facing` is written), then calls `try_attack` — so a single frame of
## aim is read one tick late, and two is the first that is certainly enough.
var aim_frames := 3
## The human form cuts a jump the moment the button lifts, so a dodge has to be
## HELD. 18 frames is the full 46 px.
var jump_hold := 18
## How far ahead of a bore's arrival to leave the ground, in seconds.
var dodge_lead := 0.34
var dodge_late := 0.06
## After a hit, disengage rather than stand in whatever just landed on her.
var panic_hold := 26
## Inside this the Maw's body is the danger and distance is the only answer.
var flee_gap := 46.0

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
	trace = OS.get_environment("KAYA_TIDE_TRACE") != ""
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
		var ph := int(boss.get("phase"))
		if ph > 0 and ph < phase_at.size() and phase_at[ph] < 0:
			phase_at[ph] = f
		if trace and f % 60 == 0:
			print("    t=%5.1f  kaya x=%6.1f y=%6.1f %s wet=%s floor=%s hp=%d | maw x=%6.1f st=%d ph=%d hp=%2d | throws %d blade_home=%s aim=%d"
				% [float(f) / 60.0, pl.center().x, pl.center().y, pl.form_id,
					str(pl.submerged()), str(pl.on_floor), Game.health,
					boss.center().x, int(boss.get("st")), ph, boss.health, throws,
					str(_blade_is_home()), _aim])
		if boss.defeated or pl.dead or Game.health <= 0:
			break
	Tape.release_all()
	print("    %d frames (%.1f s), %d throws, maw %d hp, kaya %d hearts (low %d)%s"
		% [f, float(f) / 60.0, throws, boss.health, Game.health, low,
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
##   3. the Maw's body is on top of her — run
##   4. the blade is back — turn and throw
##   5. otherwise hold the standoff
func _decide(pl: Player, boss: Enemy) -> Array:
	var held: Array = []
	var dx := boss.center().x - pl.center().x
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

	# Aim, then throw. The aim is the whole point: `facing` comes from the
	# movement axis, so the blade only goes where she last walked.
	if _aim <= 0 and _blade_is_home() and gap >= throw_min and gap <= throw_max:
		_aim = aim_frames
	if _aim > 0:
		_aim -= 1
		held.append(toward)
		if _aim == 0:
			held.append("attack")
		return held

	if gap < near:
		held.append(away)
	elif gap > far:
		held.append(toward)
	return held

func _blade_is_home() -> bool:
	for n: Node in gate.entity_children():
		if n is Blade and is_instance_valid(n):
			return false
	return true

## True when a hostile shot is running the floor at Kaya and this is the frame
## to leave the ground. Only shots at body height count: the spray arcs over
## her, and jumping into it is worse than standing still.
func _incoming_bore(pl: Player) -> bool:
	var pr := pl.aabb()
	for n in get_tree().get_nodes_in_group(&"hostile_shots"):
		var s := n as Projectile
		if s == null or not is_instance_valid(s):
			continue
		if absf(s.vel.x) < 1.0:
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
