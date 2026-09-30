extends Node
## Records the strategy tape ADR 005's checks 1 and 2 replay against THE
## OBSIDIAN HEART.
##
## The tape is the proof; this is only the pen. A scripted controller fights the
## real boss while every button it presses is written down, and the gate then
## replays those frames *blind* — no policy, no live reads — so what is checked
## is a fixed sequence of presses against the real fight, exactly as a human's
## run would be.
##
##   $GODOT --headless --fixed-fps 60 --path . \
##       res://tests/integration/boss_obsidian_heart_runner.tscn   (KAYA_HEART_MODE=record)
##
## WHY THIS EXISTS AND NOT tests/integration/boss_gate_strategy.gd
## ---------------------------------------------------------------
## That file is the Grove Warden's pen, and `tools/bossgate/bossgate_runner.gd`
## preloads exactly one — so every boss after the first has added a runner of its
## own, and this is the fifth. Only *recording* is boss-specific, because only
## the policy is; `tools/bossgate.sh --level=nest_5 --boss=obsidian_heart` still
## runs the whole gate.
##
## WHAT THIS POLICY HAS TO DO THAT THE OTHER FOUR DO NOT
## -----------------------------------------------------
## The hearthold has three heights and the Heart has one attack for each of
## them, so where to stand is not one answer, it is three — and two of the three
## are *stay on the floor*:
##
##   * **The bore** runs the floor. The answer is to leave it: hold the jump.
##     Not tap it — the human form cuts a jump the moment the button lifts, and
##     18 held frames is the full 46 px against a wave running 4 px up.
##   * **The glass** is swept along the STEP band, which is 32 px up. A body on
##     the floor is *under* it, so the answer is to stay down — and the one thing
##     this pen must never do is jump into it. So the jump is conditional on a
##     bore specifically, read off the shot's own velocity, and never on "a shot
##     exists".
##   * **The shed** falls down nine named columns. The pen does not read
##     `shed.cols` out of the config — a pen that carries a copy of the level's
##     numbers drifts out of step with the level — it reads the live falling
##     shots and steps out from under them, which is the same information a
##     player has.
##
## The Heart cannot be hurt any less at any moment — there is no roost window and
## no invulnerable phase — so the rest of this is boss_gate_strategy.gd's
## standoff, with one addition: `_close` walks her east at the start, because the
## gate stages Kaya on the leftmost tile of the lowest standable row, which in
## the hearthold is (26,27), and the Heart's left edge never passes x 512.
##
## THE RECONFIGURATION IS NOT MODELLED AT ALL, and that is deliberate. The pen
## fights on the arena floor, and the floor is the one part of this arena that no
## configuration touches (every switch tile in the level is at rows 21-22 and a
## body on the floor occupies rows 25-26). So the tape it writes is a tape that
## never needed to know — which is the honest demonstration that the fight is
## winnable without the bays, and leaves the bays as what they are: an offer.
## What the reconfiguration does to a player who DOES take the offer is
## tests/integration/boss_obsidian_heart_tests.gd's subject.

const Tape := preload("res://tests/integration/boss_gate_tape.gd")

## src/enemies/obsidian_heart.gd's `St`, which is the other four bosses'. Read
## rather than imported, because the gate's own attack tags depend on these six
## being these six.
const ST_IDLE := 0
const ST_WALK := 1
const ST_WINDUP := 2
const ST_AIR := 3
const ST_LAND := 4
const ST_SPRAY := 5

const TS := 16.0

## The standoff. The blade's `max_range` is 118 px and it leaves Kaya's chest
## 8 px out, so this band sits inside the damage window and outside a 40 px body.
var near := 58.0
var far := 96.0
## Never press attack outside this: a blade that turns back before it arrives is
## a second of cooldown bought for nothing.
var throw_min := 30.0
var throw_max := 112.0
## Frames of held movement toward it before the attack press.
## `Player._physics_process` polls input, then steps the form (which is where
## `facing` is written), then calls `try_attack` — so one frame of aim is read a
## tick late and two is the first that is certainly enough.
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
var flee_gap := 46.0
## How far to slide sideways to get out from under a falling shard, in pixels,
## and how long to keep sliding once one is in the air.
var shard_room := 13.0
var shard_hold := 22
## The reforge. While `reforging` is true the Heart is stock still and harmless,
## and everything already in the air is still coming — so the pen spends the beat
## closing rather than throwing, which is also what a player would do.
var reforge_close := true

var gate: Node = null
var max_frames := 5400            ## 90 s, ADR 005's defeat bound
var trace := false

var _aim := 0
var _jump_latch := 0
var _panic := 0
var _shard := 0
var _last_health := 5

func configure(d: Dictionary) -> void:
	for k: String in d.keys():
		if k in self:
			set(k, d[k])

func record(checks: Node) -> Dictionary:
	gate = checks
	trace = OS.get_environment("KAYA_HEART_TRACE") != ""
	await gate.stage_fight()

	var pl: Player = gate.pl
	var boss: Enemy = gate.boss
	_aim = 0
	_jump_latch = 0
	_panic = 0
	_shard = 0
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
			print("    t=%5.1f  kaya x=%6.1f floor=%s hp=%d | heart x=%6.1f st=%d ph=%d hp=%2d flips=%d | throws %d"
				% [float(f) / 60.0, pl.center().x, str(pl.on_floor), Game.health,
					boss.center().x, int(boss.get("st")), ph, boss.health,
					int(boss.call("flips")), throws])
		if boss.defeated or pl.dead or Game.health <= 0:
			break
	Tape.release_all()
	print("    %d frames (%.1f s), %d throws, %d reconfiguration(s), heart %d hp, kaya %d hearts (low %d)%s"
		% [f, float(f) / 60.0, throws, int(boss.call("flips")), boss.health,
			Game.health, low, "  DEFEATED" if boss.defeated else ""])
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
			"flips": int(boss.call("flips")),
		},
	}

func _secs(frame: int) -> String:
	return "-" if frame < 0 else "%.1f" % (float(frame) / 60.0)

# ---------------------------------------------------------------- the policy
## In priority order:
##   1. just took a hit — get away from it
##   2. a bore is running the floor at her — jump, and HOLD the jump
##   3. a shard is falling on her — slide out from under it, and keep sliding
##   4. its body is on top of Kaya — run
##   5. otherwise — hold the standoff and throw
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

	# The shed. Falling shots are dodged sideways and never upward — jumping into
	# one is the single worst thing this pen could do, which is why the jump
	# above tests for a BORE by its velocity rather than for "a shot".
	var slide := _shard_side(pl)
	if slide != 0:
		_shard = shard_hold
	if _shard > 0:
		_shard -= 1
		if slide != 0:
			held.append("right" if slide > 0 else "left")
			return held

	if gap < flee_gap:
		held.append(away)
		return held

	# The reforge beat: it cannot be hurt any less, but it also cannot hurt her,
	# so this is free distance. Spend it closing to the standoff.
	if reforge_close and bool(boss.get("reforging")):
		if gap > near:
			held.append(toward)
		return held

	# Aim, then throw: `facing` comes from the movement axis, so the blade only
	# goes where she last walked. That is boss_gate_strategy.gd's own fix and it
	# is the difference between a fight and a blade thrown backwards for 90 s.
	if _aim <= 0 and _blade_is_home() and gap >= throw_min and gap <= throw_max:
		_aim = aim_frames
	if _aim > 0:
		_aim -= 1
		held.append(toward)
		if _aim == 0:
			held.append("attack")
		return held
	if gap > far:
		held.append(toward)
	elif gap < near:
		held.append(away)
	return held

func _blade_is_home() -> bool:
	for n: Node in gate.entity_children():
		if n is Blade and is_instance_valid(n):
			return false
	return true

## Which way to step to get out from under a falling shard, or 0 for "nothing is
## coming down on her". Read off the live shots rather than off the boss's
## `shed.cols`, because a pen that carries a copy of the level's numbers is a pen
## that stops being about the level.
func _shard_side(pl: Player) -> int:
	var best := 0
	var best_d := shard_room
	var pr := pl.aabb()
	for n in get_tree().get_nodes_in_group(&"hostile_shots"):
		var s := n as Projectile
		if s == null or not is_instance_valid(s):
			continue
		if s.vel.y < 40.0 or absf(s.vel.x) > 8.0:
			continue                          ## not falling
		if s.pos.y > pr.position.y + pr.size.y:
			continue                          ## already past her
		var d := s.aabb().get_center().x - pr.get_center().x
		if absf(d) < best_d:
			best_d = absf(d)
			best = -1 if d > 0.0 else 1
	return best

## True when a floor wave is running at Kaya and this is the frame to leave the
## ground. Only shots at body height and travelling sideways count: a shard
## falling out of the vault is dodged by not being under it, and the glass is
## swept 32 px up where a body on the floor already is not.
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
