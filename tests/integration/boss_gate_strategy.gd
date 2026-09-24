extends Node
## Records the strategy tape that ADR 005's checks 1 and 2 replay.
##
## The tape is the proof; this is only the pen. A scripted controller fights the
## real boss while every button it presses is written down, and the result is
## frozen into tools/bossgate/tapes/<boss>.json as a flat list of frames. The
## gate then replays those frames *blind* — no policy, no live reads — so what
## is checked afterwards is a fixed sequence of presses against the real fight,
## exactly as a human's run would be.
##
## Re-record with:  tools/bossgate.sh --record
## Trace what the policy is doing with:  KAYA_BOSSGATE_TRACE=1

const Tape := preload("res://tests/integration/boss_gate_tape.gd")

## The blade's own numbers, read from the weapon so the policy cannot drift away
## from the weapon it is throwing.
var reach := 118.0
## Kaya is airborne for about 0.68 s, and clears the shockwave for roughly the
## middle half a second of that. Leaving the ground this far ahead of a shot
## puts her over it rather than into it.
## boss_grove.gd's St enum. Read, never written.
const ST_WINDUP := 2
const ST_AIR := 3

## Everything the policy can be told to do differently. These are knobs on the
## *pen*, not on the gate: whichever setting first produces a winning tape is
## the one that gets written down, and from then on only the tape matters.
var dodge_lead := 0.30       ## leave the ground this long before a shot arrives
var dodge_late := 0.11
var near := 64.0             ## closer than this and she backs off
var far := 92.0              ## further than this and she closes in
var throw_max := 104.0       ## the blade turns back at max_range; do not waste throws
var jump_hold := 20          ## the human form cuts a jump the moment the button lifts
var under_trigger := 84.0    ## start the under-pass from inside this gap
var under_min := 30.0        ## and not from closer than this: it is already on her
var under_hold := 44         ## frames committed to the pass once started
var add_jump_gap := 30.0     ## how close a beetle gets before she hops it
var panic_hold := 34         ## frames spent disengaging after a hit
var throw_min := 26.0        ## too close and the blade is past it before it arms
var use_under := true        ## attempt the under-pass at all
## 0: fight whatever is nearest.  1: keep the blade on the Warden and vault the
## beetles. LEAP ends at 6 damage, so ending it quickly is itself a defence —
## the arena gains two more beetles every slam and never loses one.
var add_mode := 0
## Keep hopping rather than standing. The shockwave runs 6 px tall along the
## floor and a beetle is 11 px tall; Kaya's jump is 46 px and lasts 0.68 s, so
## a continuous hop is above both of them for most of every cycle. The blade
## leaves from her chest, so throwing while airborne aims it *higher* into the
## Warden's body, not over it.
var hop_mode := false
var hop_period := 44         ## frames per hop: held for all but the last four
var throw_airborne := false  ## let her throw while off the ground

func configure(d: Dictionary) -> void:
	for k: String in d.keys():
		if k in self:
			set(k, d[k])

var gate: Node = null
var max_frames := 5400           ## 90 s, the defeat bound
var trace := false

## Frames of jump still to hold, and frames of "keep going, you are under it".
var _jump_latch := 0
var _under := 0
var _under_dir := 0
var _under_from := 0
var _prev_st := 0
var _panic := 0
var _last_health := 5
var _vault := 0
var _vault_dir := 0
var _frame := 0

var _amin := 0.0
var _amax := 0.0
var _floor_y := 0.0

func record(checks: Node) -> Dictionary:
	gate = checks
	trace = OS.get_environment("KAYA_BOSSGATE_TRACE") != ""
	var w := WeaponBase.load_weapon("boomerang_blade")
	if w != null:
		reach = float(w.cfg.get("max_range", 118.0))
	await gate.stage_fight()

	var pl: Player = gate.pl
	var boss: Enemy = gate.boss
	_amin = float(boss.get("arena_min"))
	_amax = float(boss.get("arena_max"))
	_floor_y = pl.pos.y

	_jump_latch = 0
	_under = 0
	_under_dir = 0
	_under_from = 0
	_prev_st = 0
	_panic = 0
	_vault = 0
	_vault_dir = 0
	_frame = 0
	_last_health = Game.health

	var per_frame: Array = []
	var f := 0
	var low := Game.health
	var throws := 0
	var seen_blades: Dictionary = {}
	var blade_frames := 0
	var overlap_frames := 0
	while f < max_frames:
		var held := _decide(pl, boss)
		Tape.apply(held)
		per_frame.append(held)
		await get_tree().physics_frame
		f += 1
		if Game.health < low and trace:
			var near_shot := 999.0
			for n in get_tree().get_nodes_in_group(&"hostile_shots"):
				var sp := n as Projectile
				if sp != null and is_instance_valid(sp):
					near_shot = minf(near_shot, sp.aabb().get_center().distance_to(pl.center()))
			var nadds := 0
			for na in get_tree().get_nodes_in_group(&"enemies"):
				if is_instance_valid(na) and na != boss:
					nadds += 1
			print("    HIT at t=%5.2f  hp->%d | kaya x=%6.1f dx=%+6.1f y=%6.1f floor=%s beetles=%d"
				% [float(f) / 60.0, Game.health, pl.center().x,
					boss.center().x - pl.center().x, pl.pos.y, str(pl.on_floor), nadds]
				+ "  warden st=%d feet=%6.1f | nearest shot %.0f px"
				% [int(boss.get("st")), boss.pos.y + boss.box.y, near_shot])
		low = mini(low, Game.health)
		for n: Node in gate.entity_children():
			if n is Blade:
				blade_frames += 1
				if not seen_blades.has(n.get_instance_id()):
					seen_blades[n.get_instance_id()] = true
					throws += 1
				if (n as Blade).aabb().intersects(boss.aabb()):
					overlap_frames += 1
		if trace and f % 30 == 0:
			print("    t=%5.2f  kaya x=%6.1f y=%6.1f hp=%d | warden x=%6.1f st=%d ph=%d hp=%2d"
				% [float(f) / 60.0, pl.center().x, pl.center().y, Game.health,
					boss.center().x, int(boss.get("st")), int(boss.get("phase")), boss.health])
		if boss.defeated or pl.dead or Game.health <= 0:
			break
	Tape.release_all()
	if trace:
		print("    throws=%d  blade-in-air frames=%d  blade-on-warden frames=%d  damage dealt=%d"
			% [throws, blade_frames, overlap_frames, boss.max_health - boss.health])
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

# ---------------------------------------------------------------- the policy
## The Warden walks at 46-78 px/s and Kaya runs at 108, so she can hold any
## standoff she likes — until the arena wall arrives. The fight is therefore
## about one thing: getting back past it. It leaps once per slam cycle, and at
## the top of that leap its feet clear her head; that is the only moment the
## arena lets her change sides, so the policy takes it every time.
##
## In priority order:
##   1. the Warden is overhead — run under it and come out behind
##   2. a shockwave is running along the floor — jump it, and *hold* the jump
##   3. otherwise hold the blade's standoff and keep throwing
func _decide(pl: Player, boss: Enemy) -> Array:
	var held: Array = []
	var pc := pl.center()
	# She fights whatever is closest. LEAP and FURY call in beetles, and
	# treating them as scenery is what ended every run of the earlier policy:
	# she kept her standoff from the Warden and walked backwards into a beetle.
	# A beetle has two health and the blade hits everything it passes through,
	# so clearing one costs two throws she was going to make anyway.
	_frame += 1
	var target: Enemy = boss if add_mode == 1 else _nearest_enemy(pl)
	if target == null:
		target = boss
	var on_boss: bool = target == boss
	var bc := target.center()
	var dx := bc.x - pc.x
	var away := -1 if dx > 0.0 else 1
	var toward := -away
	var st := int(boss.get("st"))
	var took_off: bool = st == ST_AIR and _prev_st == ST_WINDUP
	_prev_st = st

	# Taking a hit used to start a loop: knocked into the Warden, no input for
	# the 0.35 s of hurt, and hit again the instant the i-frames ran out —
	# three hearts in three seconds without her ever getting a say. After any
	# hit she now disengages from whatever is nearest before doing anything
	# else.
	if Game.health < _last_health:
		_panic = panic_hold
		_under = 0
	_last_health = Game.health
	if _panic > 0:
		_panic -= 1
		var nearest := _nearest_body(pl)
		if nearest != 0:
			held.append("right" if nearest < 0 else "left")
		return held

	# The pass is triggered on the Warden's *takeoff*, not on where its feet
	# happen to be. Measured: it is airborne for 0.62 s and closes at ~182 px/s
	# relative, so from inside 84 px Kaya is through and out the far side with
	# the arc still above her. Reading "is it overhead right now" instead put
	# her under it as it came down, and that was every hit she took.
	if use_under and on_boss and took_off and pl.on_floor \
			and absf(dx) < under_trigger and absf(dx) > under_min:
		_under = under_hold
		_under_dir = toward
		_under_from = signi(dx)

	var step := 0
	if absf(dx) < near:
		step = away
	elif absf(dx) > far:
		step = toward

	if _under > 0:
		_under -= 1
		step = _under_dir
		# Out the other side with room behind her: the pass is done.
		if signi(dx) != _under_from and absf(dx) > 30.0:
			_under = 0
	else:
		# The human form cuts a jump the moment the button comes up, so the
		# dodge has to be *held*, not tapped. Releasing it at the top of the
		# arc turned a 46 px jump into an 18 px one and walked her into the
		# shockwave she was trying to clear.
		if hop_mode and _jump_latch <= 0 and _vault <= 0:
			# A rising edge every hop_period frames; the form buffers the press
			# for 0.12 s, so she leaves the ground the moment she touches it.
			if _frame % hop_period < hop_period - 4:
				held.append("jump")
		if _jump_latch > 0:
			_jump_latch -= 1
		elif _incoming_shot(pl):
			_jump_latch = jump_hold
		elif _add_underfoot(pl):
			_jump_latch = jump_hold
			# Vault it rather than backing off: backing off in this arena just
			# means meeting the next one.
			_vault = jump_hold
			_vault_dir = _add_side(pl)
		if _jump_latch > 0:
			held.append("jump")
		if _vault > 0:
			_vault -= 1
			step = _vault_dir
		elif (not on_boss or st != ST_AIR) and absf(dx) < 30.0 and pl.on_floor:
			# It is on the floor and on top of her, and the pass is not on.
			# Over it is all that is left.
			held.append("jump")
			step = toward

	if step > 0:
		held.append("right")
	elif step < 0:
		held.append("left")

	# try_attack is cooldown- and in-flight-gated, so holding attack simply
	# throws as often as the blade allows. Measured (KAYA_BOSSGATE_MODE=probe):
	# from the floor, at any gap from 40 to 104 px, this lands about one hit a
	# second — 18 health in twenty-odd seconds, well inside the time bound.
	if (pl.on_floor or throw_airborne) and absf(dx) > throw_min \
			and absf(dx) <= throw_max:
		held.append("attack")
	return held

## Which way the nearest beetle lies: vault that way.
func _add_side(pl: Player) -> int:
	var best := 1e9
	var side := 0
	for n in get_tree().get_nodes_in_group(&"enemies"):
		var e := n as Enemy
		if e == null or not is_instance_valid(e) or e == gate.boss or not e.active:
			continue
		var d := e.center().x - pl.center().x
		if absf(d) < best:
			best = absf(d)
			side = -1 if d < 0.0 else 1
	return side

## The closest thing that can hurt her by touching her.
func _nearest_enemy(pl: Player) -> Enemy:
	var best := 1e9
	var out: Enemy = null
	for n in get_tree().get_nodes_in_group(&"enemies"):
		var e := n as Enemy
		if e == null or not is_instance_valid(e) or not e.active:
			continue
		var d := absf(e.center().x - pl.center().x)
		if d < best:
			best = d
			out = e
	return out

## Which side the closest hostile body is on: -1 left of her, +1 right, 0 none.
func _nearest_body(pl: Player) -> int:
	var best := 999.0
	var side := 0
	for n in get_tree().get_nodes_in_group(&"enemies"):
		var e := n as Enemy
		if e == null or not is_instance_valid(e) or not e.active:
			continue
		var d := e.center().x - pl.center().x
		if absf(d) < best:
			best = absf(d)
			side = -1 if d < 0.0 else 1
	return side

## LEAP and FURY call in beetles, and they were what actually killed every run
## of this policy once phase 2 opened: four of five hits came from a walker
## while Kaya was busy reading the Warden. They are 11 px tall and she clears
## 46, so the answer is simply to jump them.
func _add_underfoot(pl: Player) -> bool:
	if not pl.on_floor:
		return false
	var pr := pl.aabb()
	for n in get_tree().get_nodes_in_group(&"enemies"):
		var e := n as Enemy
		if e == null or not is_instance_valid(e) or e == gate.boss or not e.active:
			continue
		var er := e.aabb()
		if absf(er.get_center().x - pr.get_center().x) > add_jump_gap:
			continue
		if er.end.y < pr.position.y or er.position.y > pr.end.y:
			continue
		return true
	return false

## True when a hostile shot is running along the floor at Kaya and this frame is
## the moment to leave the ground.
func _incoming_shot(pl: Player) -> bool:
	var pr := pl.aabb()
	if not pl.on_floor:
		return false
	for n in get_tree().get_nodes_in_group(&"hostile_shots"):
		var s := n as Projectile
		if s == null or not is_instance_valid(s):
			continue
		if absf(s.vel.x) < 1.0:
			continue
		var gap := s.aabb().get_center().x - pr.get_center().x
		if signf(s.vel.x) * signf(gap) >= 0.0:
			continue                       ## travelling away from her
		# Only shots at body height matter; the spray arcs over her head.
		if s.pos.y + 6.0 < pr.position.y or s.pos.y > pr.position.y + pr.size.y:
			continue
		var eta := (absf(gap) - pr.size.x * 0.5) / absf(s.vel.x)
		if eta > dodge_late and eta < dodge_lead:
			return true
	return false

# ---------------------------------------------------------------- diagnostics
## Measures what the blade actually does to the Warden, rather than assuming.
## The Warden is held still at its spawn so the only variable is where Kaya
## stands; she holds attack for ten seconds at each distance.
func probe_blade(checks: Node) -> void:
	gate = checks
	var pl: Player = gate.pl
	var boss: Enemy = gate.boss
	print("  blade probe: Kaya standing, Warden held still at x=%.0f" % boss.center().x)
	for gap in [-120, -104, -88, -72, -56, -40, 40, 56, 72, 88, 104, 120]:
		gate.reset_arena(0)
		boss.active = true
		var tile := Vector2i(int((boss.center().x + float(gap)) / 16.0), 27)
		pl.control_enabled = true
		pl.dead = false
		pl.pos = gate.stand_pos(tile)
		pl.vel = Vector2.ZERO
		pl.invuln = 999.0
		gate.lvl.cam.snap_to_target()
		Tape.release_all()
		await gate.frames(2)
		var blade_lo := 9999.0
		var blade_hi := -9999.0
		var overlaps := 0
		var throws: Dictionary = {}
		for f in 600:
			# Freeze the Warden: this probe is about the weapon, not the walk.
			boss.set("st", 0)
			boss.set("t", 9.0)
			boss.pos = boss.spawn_pos
			boss.vel = Vector2.ZERO
			pl.invuln = 999.0
			pl.hurt_t = 0.0
			pl.pos = gate.stand_pos(tile)
			pl.vel = Vector2.ZERO
			pl.facing = 1 if gap < 0 else -1
			Game.health = Game.max_health
			Tape.apply(["attack"] if (f / 3) % 2 == 0 else [])
			await get_tree().physics_frame
			for n: Node in gate.entity_children():
				if n is Blade:
					var b := n as Blade
					throws[b.get_instance_id()] = true
					blade_lo = minf(blade_lo, b.aabb().position.y)
					blade_hi = maxf(blade_hi, b.aabb().end.y)
					if b.aabb().intersects(boss.aabb()):
						overlaps += 1
		Tape.release_all()
		var br := boss.aabb()
		print("    gap %+4d px | throws %2d | blade y %.0f..%.0f vs Warden y %.0f..%.0f | overlap frames %3d | damage %d"
			% [gap, throws.size(), blade_lo, blade_hi, br.position.y, br.end.y,
				overlaps, boss.max_health - boss.health])

## Counts what the arena is holding over time, per phase. Nothing in the five
## checks asks this; it was written because every losing run died in a crowd.
func probe_adds(checks: Node) -> void:
	gate = checks
	var pl: Player = gate.pl
	var boss: Enemy = gate.boss
	var phases: Array = boss.cfg.get("phases", [])
	print("  add probe: Kaya parked out of reach, Warden left to fight the air")
	for phase in phases.size():
		var pcfg: Dictionary = phases[phase]
		gate.reset_arena(phase)
		# Park her on a ledge the Warden cannot reach, so the only thing
		# driving the count is the boss's own slam cycle.
		pl.control_enabled = false
		pl.dead = false
		pl.invuln = 999.0
		gate.lvl.cam.snap_to_target()
		var counts: PackedStringArray = PackedStringArray()
		for f in 1800:
			pl.invuln = 999.0
			pl.hurt_t = 0.0
			pl.vel = Vector2.ZERO
			pl.pos = gate.stand_pos(Vector2i(30, 21))
			Game.health = Game.max_health
			await get_tree().physics_frame
			if (f + 1) % 300 == 0:
				var n := 0
				for e in get_tree().get_nodes_in_group(&"enemies"):
					if is_instance_valid(e) and e != boss:
						n += 1
				counts.append("%ds:%d" % [(f + 1) / 60, n])
		print("    phase %d %-6s slam every %.1fs, %d add(s) per slam | live beetles %s"
			% [phase, String(pcfg.get("name", "")), float(pcfg.get("slam_interval", 0.0)),
				int(pcfg.get("spawn_adds", 0)), ", ".join(counts)])
