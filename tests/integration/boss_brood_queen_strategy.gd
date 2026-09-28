extends Node
## Records the strategy tape ADR 005's checks 1 and 2 replay against THE BROOD
## QUEEN.
##
## The tape is the proof; this is only the pen. A scripted controller fights the
## real boss while every button it presses is written down, and the gate then
## replays those frames *blind* — no policy, no live reads — so what is checked
## is a fixed sequence of presses against the real fight, exactly as a human's
## run would be.
##
##   $GODOT --headless --fixed-fps 60 --path . \
##       res://tests/integration/boss_brood_queen_runner.tscn   (KAYA_QUEEN_MODE=record)
##
## WHY THIS EXISTS AND NOT tests/integration/boss_gate_strategy.gd
## ---------------------------------------------------------------
## That file is the Grove Warden's pen, and `tools/bossgate/bossgate_runner.gd`
## preloads exactly one — so every boss after the first has added a runner of its
## own, and this is the fourth. Only *recording* is boss-specific, because only
## the policy is; `tools/bossgate.sh --level=deeps_5 --boss=brood_queen` still
## runs the whole gate.
##
## What this policy has to do that the other three do not:
##
##   * **Walk to the fight.** The gate stages Kaya on the leftmost tile of the
##     lowest standable row, which in the royal cell is (26,27) — eight tiles west
##     of the span the Queen is clamped inside. So the first thing the tape does
##     is close.
##   * **Answer two attacks with two different answers.** The floor wave is
##     dodged by leaving the ground and HOLDING the jump; the spore fall is
##     dodged by standing under a comb. Jumping into a spore fall is worse than
##     standing still, and running out from under a comb while one is in the air
##     is how you eat six of them.
##   * **Find the comb rather than be told where it is.** The shelter columns are
##     read off the live `TileWorld` — the floor tiles that have solid earth in
##     the row the spore fall is thrown from — so this pen does not carry a copy
##     of deeps_5's geometry that could drift out of step with it.
##
## It does not need to wait for a window: unlike the Stormcrest, the Queen can be
## hurt on any frame, and unlike the Maw she never leaves the floor. The darkness
## is not modelled at all, and that is deliberate — a pen that reads `boss.pos`
## is reading something a player in a dark room cannot. What that leaves
## unanswered is the whole subject of
## tests/integration/boss_brood_queen_tests.gd's last three cases.

const Tape := preload("res://tests/integration/boss_gate_tape.gd")

## src/enemies/brood_queen.gd's `St`, which is the other three bosses'. Read
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
## Frames of held movement toward her before the attack press.
## `Player._physics_process` polls input, then steps the form (which is where
## `facing` is written), then calls `try_attack` — so one frame of aim is read a
## tick late and two is the first that is certainly enough.
var aim_frames := 3
## The human form cuts a jump the moment the button lifts, so a dodge has to be
## HELD. 18 frames is the full 46 px, which clears a wave running 4 px off the
## floor with 39 px to spare.
var jump_hold := 18
## How far ahead of a wave's arrival to leave the ground, in seconds.
var dodge_lead := 0.34
var dodge_late := 0.06
## After a hit, disengage rather than stand in whatever just landed on her.
var panic_hold := 24
## Inside this her body is the danger and distance is the only answer.
var flee_gap := 46.0
## How much room to open up once the rumble line says a charge is coming, in
## pixels. This is the single number that decides whether the tape wins, and the
## arithmetic behind it is the fight: the windup is 0.62 s, in which Kaya runs
## 108 px/s = 67 px; the longest charge is 164 px/s for 0.85 s = 139 px, during
## which she opens another 92. So a charge read at the rumble line and answered by
## running LOSES 48 px of the standoff and no hearts, and a charge read at the
## moment she surfaces costs one. Her body is 46 px tall and Kaya's jump is 46 px,
## so there is no jumping over this and no shelf high enough to be over it: the
## telegraph is the whole defence, which is exactly what the rumble line is for.
var charge_room := 156.0
## How long to sit under a comb once a spore fall is in the air, in frames.
var comb_hold := 46
## Give up on reaching a comb further away than this, in pixels: running for a
## shelter you cannot make is worse than taking the fall where you stand.
var comb_max := 132.0

var gate: Node = null
var max_frames := 5400            ## 90 s, ADR 005's defeat bound
var trace := false

var _aim := 0
var _jump_latch := 0
var _panic := 0
var _comb := 0
var _last_health := 5
var _shelters: Array = []         ## floor-column x centres that a comb roofs

func configure(d: Dictionary) -> void:
	for k: String in d.keys():
		if k in self:
			set(k, d[k])

func record(checks: Node) -> Dictionary:
	gate = checks
	trace = OS.get_environment("KAYA_QUEEN_TRACE") != ""
	await gate.stage_fight()

	var pl: Player = gate.pl
	var boss: Enemy = gate.boss
	_aim = 0
	_jump_latch = 0
	_panic = 0
	_comb = 0
	_last_health = Game.health
	_find_shelters(boss)

	var per_frame: Array = []
	var f := 0
	var low := Game.health
	var throws := 0
	var walls := 0
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
		walls = int(boss.call("walls_broken"))
		var ph := int(boss.get("phase"))
		if ph > 0 and ph < phase_at.size() and phase_at[ph] < 0:
			phase_at[ph] = f
		if trace and f % 60 == 0:
			print("    t=%5.1f  kaya x=%6.1f floor=%s hp=%d | queen x=%6.1f st=%d ph=%d hp=%2d a=%.2f | throws %d walls %d"
				% [float(f) / 60.0, pl.center().x, str(pl.on_floor), Game.health,
					boss.center().x, int(boss.get("st")), ph, boss.health,
					float(boss.get("alpha")), throws, walls])
		if boss.defeated or pl.dead or Game.health <= 0:
			break
	Tape.release_all()
	print("    %d frames (%.1f s), %d throws, %d luminous wall(s) spent, queen %d hp, kaya %d hearts (low %d)%s"
		% [f, float(f) / 60.0, throws, walls, boss.health, Game.health, low,
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
			"walls_broken": walls,
		},
	}

func _secs(frame: int) -> String:
	return "-" if frame < 0 else "%.1f" % (float(frame) / 60.0)

## Where the combs are, read off the live world rather than copied out of
## tools/worlds/deeps_5.py: a floor column with solid earth in the row the spore
## fall is thrown from is a column the fall cannot reach.
func _find_shelters(boss: Enemy) -> void:
	_shelters = []
	var lvl: Node = gate.lvl
	if lvl == null:
		return
	var world: TileWorld = lvl.world
	var s: Dictionary = boss.cfg.get("spore", {})
	var row := int(s.get("row", 16))
	for tile: Vector2i in gate.standable_tiles():
		if world.is_solid(tile.x, row):
			_shelters.append(float(tile.x) * TS + TS * 0.5)
	if trace:
		print("    shelters under a comb: %d column(s)" % _shelters.size())

# ---------------------------------------------------------------- the policy
## In priority order:
##   1. just took a hit — get away from it
##   2. a wave is running the floor at her — jump, and HOLD the jump
##   3. spores are in the air — get under a comb and stay there
##   4. her body is on top of Kaya — run
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
	elif pl.on_floor and _incoming_wave(pl):
		_jump_latch = jump_hold
		held.append("jump")

	# The rumble line. `brood_queen.gd` spends 0.62 s marching dust out along the
	# floor in the direction she is about to burrow, and this is the policy that
	# reads it — which matters more than it looks, because it is the one piece of
	# this fight that a player in a dark chamber MUST be able to see. The pen
	# reads `st` and `facing` rather than the particles, so the suite asserts
	# separately that the particles are there; what this line proves is that the
	# information is sufficient.
	var bst := int(boss.get("st"))
	if bst == ST_WINDUP or bst == ST_AIR:
		var coming: bool = (dx > 0.0 and boss.facing < 0) or (dx < 0.0 and boss.facing > 0)
		if coming and gap < charge_room:
			_aim = 0
			held.append(away)
			return held

	# The spore fall. A comb is a roof, and a roof works every time; being merely
	# somewhere else works only until the fan is wide enough, which it is by
	# HATCH. So this runs for the shelter and then STAYS, which is why it is a
	# latch and not a per-frame test — the shots take about a second to fall and
	# stepping back out at the wrong moment is the same as never having moved.
	if _falling_spores():
		_comb = comb_hold
	if _comb > 0:
		_comb -= 1
		var shelter := _nearest_shelter(pl)
		if shelter > -9000.0:
			var d := shelter - pl.center().x
			if absf(d) > 4.0:
				held.append("right" if d > 0.0 else "left")
			return held
		_comb = 0

	if gap < flee_gap:
		held.append(away)
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

func _nearest_shelter(pl: Player) -> float:
	var best := -9999.0
	var best_d := comb_max
	for x: float in _shelters:
		var d := absf(x - pl.center().x)
		if d < best_d:
			best_d = d
			best = x
	return best

func _blade_is_home() -> bool:
	for n: Node in gate.entity_children():
		if n is Blade and is_instance_valid(n):
			return false
	return true

## True while anything is falling out of the roof. The spore fall is the only
## thing in this fight that travels downward, so the test is its direction.
func _falling_spores() -> bool:
	for n in get_tree().get_nodes_in_group(&"hostile_shots"):
		var s := n as Projectile
		if s == null or not is_instance_valid(s):
			continue
		if s.vel.y > 40.0 and absf(s.vel.x) < 8.0:
			return true
	return false

## True when a floor wave is running at Kaya and this is the frame to leave the
## ground. Only shots at body height count: a spore falling out of the roof is
## dodged by not being under it, and jumping into one is worse than standing
## still.
func _incoming_wave(pl: Player) -> bool:
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
