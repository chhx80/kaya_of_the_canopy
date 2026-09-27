extends Enemy
## THE STORMCREST — World 3's boss. Three scripted phases driven entirely by
## data/enemies/stormcrest.json, the same data-driven machine as
## src/enemies/boss_grove.gd and src/enemies/tide_maw.gd and deliberately not a
## third one:
##
##   EYRIE     it circles the eyrie, stoops at a roost pad, and the crash throws
##             a bore along the floor both ways.
##   SQUALL    faster, and it feathers the floor from the air between stoops. The
##             gale rises: both wind-shelters are blown out.
##   TEMPEST   fastest, and the gale covers the whole floor, pushing inward.
##
## Two things here are not in boss_grove.gd.
##
## **It is only vulnerable while roosting.** `hurt()` refuses damage on any frame
## the Stormcrest is not on the ground with its wings folded, and rings the blade
## off instead. That is docs/plan-20-levels.md's sentence for this fight — "it is
## only vulnerable while roosting, so the fight is stamina against its roost
## cycle" — and it is the whole shape of the fight: the roost window is short, it
## is the only window, and a window missed is another lap of its attacks.
##
## It matters that this is honest about WHO fights it. The plan says "fought as
## the bird", and data/forms/bird.json is `can_attack: false` — a bird fight is a
## fight in which Kaya cannot deal one point of damage. So the roost comes down to
## the blade instead: the three roost pads are on the arena floor, where a 46 px
## body is the one thing in the arena the blade can reach. The bird is the level's
## verb in the approach; the reasoning is written out in tools/worlds/heights_5.py
## and it is the same call ruins_5 made about the fish's 10 px bite.
##
## **The gale is a real tile change.** `_apply_gale()` writes gust tiles into the
## arena's two lowest rows and takes them out again, so the wind is a fact about
## the world and not a tint: `FormBase.current_at()` pushes Kaya, the prover would
## see the same push, and `TileCollision` answers the questions it always did. It
## is bounded by the three rules src/enemies/tide_maw.gd established, because a
## boss that edits the level is a boss that can break it:
##
##   1. it only ever writes into the rectangle `gale.x/y/w/h` names;
##   2. inside that rectangle it only touches tiles the LEVEL AUTHORED EMPTY — so
##      no amount of wind can eat the floor, a refuge slab or a buttress;
##   3. phase 1 is calm and clearing restores the captured ids, so calm is
##      bit-identical to the level as shipped. levels/heights_5.json is authored
##      calm, which is what lets tools/prove.sh and the traversal tape see exactly
##      the geometry in the file.
##
## A gust is horizontal and 80 px/s against a human's 108, so it never becomes a
## wall and — the reason it is a gust and not a draft — it does not touch the
## height of a jump. `do_jump()` adds `current.y` to the jump velocity, so a
## downdraft anywhere a body jumps from would quietly make the refuge slabs
## unreachable in one phase, and the gate's refuge check only ever looks at phase
## 1. That is the class of bug ADR 005 exists to stop, so this boss does not own a
## vertical draft at all.
##
## The states, and the fact that they are the same six in the same order as the
## other two bosses: tests/integration/boss_gate_checks.gd names an attack by the
## state transition it fired on and reads those names out of a fixed list, so the
## bore is "AIR>LAND" and the volley is "SPRAY>WALK" here exactly as the Warden's
## slam and spray are. IDLE and LAND are the grounded, vulnerable poses; WALK is
## the circle; WINDUP is the stoop telegraph; AIR is the stoop.
enum St { IDLE, WALK, WINDUP, AIR, LAND, SPRAY }

var st: St = St.IDLE
var t := 0.0
var phase := 0
var phase_cfg: Dictionary = {}
var volley_t := 0.0
## What was left of the stoop timer when a volley interrupted it.
var _dive_left := 0.0
var arena_min := 0.0
var arena_max := 0.0
var arena_top := 0.0
var defeated := false

## The pad it is stooping at, and the floor its own spawn defines.
var roost_x := 0.0
var floor_y := 0.0
var _bob := 0.0

## The gale, and the arena exactly as the level authored it.
var _gale: Dictionary = {}
var _authored: PackedInt32Array = PackedInt32Array()
var _lanes_applied := "-"

func on_configured() -> void:
	_gale = cfg.get("gale", {})
	_capture_arena()
	_set_phase(0)

func _ready() -> void:
	super._ready()
	add_to_group(&"bosses")
	# Clamped to a span inside the screen it spawned on, not to the screen:
	# `arena_inset` is tide_maw.gd's mechanism and this is the same use of it. The
	# ends of the arena floor — the four tiles under each buttress — become rock
	# it never roosts on, which is what makes them somewhere to stand.
	var origin := Screen.origin(home_screen)
	var inset := float(cfg.get("arena_inset", 8.0))
	arena_min = origin.x + inset
	arena_max = origin.x + Screen.W - inset - box.x
	arena_top = origin.y + float(cfg.get("ceiling_inset", 20.0))
	# The floor is wherever the level stood it, not a row written twice. An arena
	# and a boss that disagree about where the floor is have no chance at all.
	floor_y = spawn_pos.y + box.y
	roost_x = pos.x
	# One-way slabs are not floors to a bird: without this the stoop lands ON a
	# refuge, which is both absurd and the end of the dodge window that slab
	# exists to be. Same line, same reason, as the other two bosses.
	drop_through = true
	t = 0.9

func on_respawn() -> void:
	st = St.IDLE
	t = 0.9
	_bob = 0.0
	roost_x = spawn_pos.x
	drop_through = true
	_set_phase(0)

func _set_phase(i: int) -> void:
	var phases: Array = cfg.get("phases", [])
	if phases.is_empty():
		return
	phase = clampi(i, 0, phases.size() - 1)
	phase_cfg = phases[phase]
	volley_t = float(phase_cfg.get("volley_interval", 2.4))
	_apply_gale(phase_cfg.get("lanes", []) as Array)

## EYRIE, SQUALL and TEMPEST are three birds, not three tints, so each pose
## exists once per phase in data/enemies/stormcrest.json as `<pose>_p1/_p2/_p3`.
## Anything without a per-phase variant falls back to the plain name, so the
## state machine below never has to know about this.
func set_anim(pose: String) -> void:
	var key := "%s_p%d" % [pose, phase + 1]
	var anims: Dictionary = cfg.get("anim", {})
	super.set_anim(key if anims.has(key) else pose)

## On the ground with its wings folded: the only state in which it can be hurt.
func roosting() -> bool:
	return st == St.IDLE or st == St.LAND

func hurt(amount: int, from: Vector2 = Vector2.ZERO) -> void:
	if not roosting():
		# The blade rings off it. "locked" is the cue this game already uses for
		# "not like that", which is exactly what this is; inventing a new one is
		# the audio pipeline's job and not this branch's.
		AudioManager.play("locked")
		Fx.burst("spark", center(), center() - from)
		return
	super.hurt(amount, from)
	# The killing blow is not a phase change, and on a boss that writes to the
	# level that distinction is not cosmetic. `Enemy.hurt()` calls `die()` inside
	# the line above, `die()` drops the gale — and then this loop used to run
	# anyway, find health at 0, and escalate a corpse all the way to TEMPEST,
	# whose lanes were written into an arena nothing would ever clear again.
	# Measured from a screenshot: `tools/shot.sh` killed it in phase 1 and logged
	# Kaya walking west at a steady 80 px/s across the empty arena afterwards.
	# The suite missed it because it killed the boss from phase 3, where the
	# escalation below is a no-op; it kills from phase 1 now.
	if defeated or health <= 0:
		return
	# Phase boundaries are health thresholds, so a burst of damage can skip one.
	var phases: Array = cfg.get("phases", [])
	for i in phases.size():
		if health <= int((phases[i] as Dictionary).get("until_health", 0)) and i + 1 < phases.size():
			if phase < i + 1:
				_set_phase(i + 1)
				AudioManager.play("boss_phase")

# ---------------------------------------------------------------- the gale
## Remember the arena exactly as the level drew it, once, before anything has
## been written. Clearing the gale restores these ids, so a calm arena is the
## level file and not an approximation of it.
func _capture_arena() -> void:
	_authored = PackedInt32Array()
	if world == null or _gale.is_empty():
		return
	var x0 := int(_gale.get("x", 0))
	var y0 := int(_gale.get("y", 0))
	var w := int(_gale.get("w", 0))
	var h := int(_gale.get("h", 0))
	_authored.resize(w * h)
	for j in h:
		for i in w:
			_authored[j * w + i] = world.get_fg(x0 + i, y0 + j)

## Write this phase's lanes. Only ever inside the gale rect, and inside it only
## over tiles the level authored empty.
func _apply_gale(lanes: Array) -> void:
	if world == null or _gale.is_empty() or _authored.is_empty():
		return
	var sig := _lane_signature(lanes)
	if sig == _lanes_applied:
		return                                  # nothing to write, nothing to repaint
	_lanes_applied = sig
	var x0 := int(_gale.get("x", 0))
	var y0 := int(_gale.get("y", 0))
	var w := int(_gale.get("w", 0))
	var h := int(_gale.get("h", 0))
	for j in h:
		for i in w:
			if _authored[j * w + i] != 0:
				continue                        # floor, slab, buttress: never ours
			world.set_fg(x0 + i, y0 + j, _lane_tile(x0 + i, lanes))
	_repaint()
	AudioManager.play("switch")

func _lane_signature(lanes: Array) -> String:
	var parts: PackedStringArray = PackedStringArray()
	for raw: Variant in lanes:
		var l: Dictionary = raw
		parts.append("%d-%d:%s" % [int(l.get("x0", 0)), int(l.get("x1", 0)),
			String(l.get("flow", "east"))])
	return "|".join(parts) if not parts.is_empty() else "-"

## Which tile this column carries: a gust, or nothing at all.
func _lane_tile(x: int, lanes: Array) -> int:
	for raw: Variant in lanes:
		var lane: Dictionary = raw
		if x < int(lane.get("x0", 0)) or x > int(lane.get("x1", 0)):
			continue
		var east := String(lane.get("flow", "east")) == "east"
		return int(_gale.get("gust_east" if east else "gust_west", 0))
	return 0

## Making the gale VISIBLE, which is a separate problem from making it real.
##
## `TileRenderer` resolves each tile's atlas cell once, at setup, from its
## neighbours (`TileVariants.for_world`), and `_draw()` prefers that resolved cell
## over the tile's own id — so a tile whose id changes underneath it keeps drawing
## the cell it was authored with. tide_maw.gd found this the hard way: the arena
## flooded, the collision changed, and the screenshot showed dry stone. One
## neighbour sweep of the level per phase change is the whole fix.
func _repaint() -> void:
	if level == null:
		return
	var fg: Node = level.get("tiles_fg")
	if fg == null or not fg.has_method("setup"):
		return
	TileVariants.release()
	fg.call("setup", world, "fg")

# ---------------------------------------------------------------- the fight
func think(delta: float) -> void:
	drop_through = true
	t = maxf(0.0, t - delta)
	_bob += delta
	var p := player()

	match st:
		St.IDLE:
			# Roosted on the pad the level stood it on: the fight opens with a
			# window, which is how a player learns what the window is.
			vel.x = move_toward(vel.x, 0.0, 400.0 * delta)
			vel.y = 0.0
			set_anim("idle")
			if t <= 0.0:
				_take_off()
		St.WALK:
			set_anim("walk")
			if pos.x <= arena_min:
				facing = 1
			elif pos.x >= arena_max:
				facing = -1
			vel.x = float(phase_cfg.get("cruise_speed", 58.0)) * facing
			_hold_altitude(delta, true)
			_maybe_volley(delta)
			if t <= 0.0:
				# Pick the pad nearest the player and hang over it. The choice is
				# a pad and not her exact x because a pad is a place the player
				# can read off the floor a second before the stoop starts, and
				# because it keeps every roost inside blade reach of every tile
				# she can stand on.
				roost_x = _nearest_pad(p)
				st = St.WINDUP
				t = float(cfg.get("windup_time", 0.55))
		St.WINDUP:
			set_anim("windup")
			facing = 1 if roost_x > pos.x else -1
			vel.x = clampf((roost_x - pos.x) * 6.0, -220.0, 220.0)
			_hold_altitude(delta, false)
			if t <= 0.0:
				st = St.AIR
				vel.y = float(phase_cfg.get("dive_speed", 300.0))
				AudioManager.play("boss_jump")
		St.AIR:
			set_anim("air")
			vel.y = float(phase_cfg.get("dive_speed", 300.0))
			vel.x = clampf((roost_x - pos.x) * 4.0, -140.0, 140.0)
			if on_floor:
				_crash()
				st = St.LAND
				t = float(phase_cfg.get("roost_time", 2.2))
		St.LAND:
			# ROOSTED. The window.
			vel.x = move_toward(vel.x, 0.0, 700.0 * delta)
			vel.y = 0.0
			set_anim("land")
			if t <= 0.0:
				_take_off()
		St.SPRAY:
			set_anim("windup")
			vel.x = move_toward(vel.x, 0.0, 500.0 * delta)
			_hold_altitude(delta, false)
			if t <= 0.0:
				_volley()
				st = St.WALK
				# Back onto the lap timer it left, NOT onto a fresh one. The
				# first cut restarted the dive timer here, and since
				# `volley_interval` is shorter than `dive_interval` the volley
				# re-armed the stoop forever: measured, the Stormcrest stooped
				# twice in the opening ten seconds and then circled for the rest
				# of the ninety, which is a boss with no vulnerable window at
				# all. The roost cycle is this fight; nothing may reset it but
				# the roost.
				t = maxf(0.05, _dive_left)
	_hold_the_arena(delta)

## Steer to the cruise line rather than fall to it: this animal has no gravity
## (data/enemies/stormcrest.json, `gravity: 0.0`) and its altitude is authored,
## which is the flyer.gd lesson — an emergent altitude is one the level author
## cannot place an attack under.
func _hold_altitude(delta: float, bob: bool) -> void:
	var want := floor_y - float(phase_cfg.get("cruise_y", 108.0)) - box.y
	if bob:
		want += sin(_bob * 1.7) * float(phase_cfg.get("bob", 8.0))
	var gain := float(cfg.get("steer_gain", 4.0))
	var rate := float(cfg.get("climb_rate", 150.0))
	vel.y = clampf((want - pos.y) * gain, -rate, rate)
	if delta <= 0.0:
		vel.y = 0.0

func _take_off() -> void:
	st = St.WALK
	t = float(phase_cfg.get("dive_interval", 2.2))
	var p := player()
	if p != null and not p.dead:
		facing = 1 if p.center().x > center().x else -1
	AudioManager.play("flap")

## The nearest roost pad, in world pixels, as a body position. The pads are
## authored as absolute tile columns (data/enemies/stormcrest.json, `roost_pads`)
## so the arena's bleached rock and the fight name the same three places, and they
## are clamped to the arena span, so a pad written outside it cannot walk the boss
## out of its own arena. With no pads at all it stoops straight at her.
func _nearest_pad(p: Player) -> float:
	var pads: Array = cfg.get("roost_pads", [])
	var target := center().x if p == null or p.dead else p.center().x
	if pads.is_empty():
		return clampf(target - box.x * 0.5, arena_min, arena_max)
	var best := clampf(pos.x, arena_min, arena_max)
	var best_d := 1.0e9
	for raw: Variant in pads:
		var x := clampf(float(int(raw)) * 16.0 + 8.0 - box.x * 0.5, arena_min, arena_max)
		var d := absf(x + box.x * 0.5 - target)
		if d < best_d:
			best_d = d
			best = x
	return best

## Check 4 of the boss gate is "the boss stays inside arena_min/arena_max", and it
## is measured at the END of the physics frame — after `step_motion()`, which runs
## after `think()`. Clamping the position here and then moving is the bug the
## Grove Warden shipped: it reported 4,502 frames outside its own arena. So the
## clamp bites on the VELOCITY, before the move that would use it, and the
## position clamp stays as the backstop. It holds the ceiling as well as the ends,
## because this is the first boss that can fly out of the top of its screen.
func _hold_the_arena(delta: float) -> void:
	pos.x = clampf(pos.x, arena_min, arena_max)
	pos.y = maxf(pos.y, arena_top)
	if delta <= 0.0:
		return
	var next_x := pos.x + vel.x * delta
	if next_x < arena_min:
		vel.x = (arena_min - pos.x) / delta
	elif next_x > arena_max:
		vel.x = (arena_max - pos.x) / delta
	var next_y := pos.y + vel.y * delta
	if next_y < arena_top:
		vel.y = (arena_top - pos.y) / delta

func _maybe_volley(delta: float) -> void:
	if int(phase_cfg.get("volley", 0)) <= 0:
		return
	volley_t = maxf(0.0, volley_t - delta)
	if volley_t <= 0.0:
		volley_t = float(phase_cfg.get("volley_interval", 2.2))
		_dive_left = t
		st = St.SPRAY
		t = 0.4

## The feather volley: a fan thrown DOWN out of the sky, which is why the two
## buttresses are what dodges it — eight floor tiles with 32 px of clearance and
## nine rows of solid rock over them. The fan is narrow enough that being away
## from under it works too; the difference is that a roof works every time.
func _volley() -> void:
	var n := int(phase_cfg.get("volley", 4))
	var pj: Dictionary = cfg.get("projectile", {})
	var spread := float(cfg.get("volley_spread", 1.0))
	for i in n:
		var a := lerpf(-spread, spread, float(i) / maxf(1.0, float(n - 1)))
		var dir := Vector2(sin(a), cos(a))
		var shot := Projectile.new()
		shot.setup(pj, center() + Vector2(0, 6), dir, world, level)
		level.entities.add_child(shot)
	AudioManager.play("spit")

## The bore: the stoop ends on the rock and throws a pressure wave along the floor
## in both directions, four pixels up. It is the fight's main attack and it is
## dodged by being on a refuge slab — 32 px over it — which is the shape ruins_5
## proved and jungle_5 was reworked into.
func _crash() -> void:
	AudioManager.play("boss_land")
	Fx.shake("boss_slam")
	Fx.burst("dust", Vector2(center().x, pos.y + box.y))
	var pj: Dictionary = (cfg.get("projectile", {}) as Dictionary).duplicate()
	pj["speed"] = float(phase_cfg.get("bore_speed", 132.0))
	pj["gravity"] = 0.0
	pj["life"] = float(phase_cfg.get("bore_life", 1.6))
	pj["frame"] = 1
	for dir in [Vector2.LEFT, Vector2.RIGHT]:
		var shot := Projectile.new()
		shot.setup(pj, Vector2(center().x, pos.y + box.y - 4.0), dir, world, level)
		level.entities.add_child(shot)

func die(from: Vector2 = Vector2.ZERO) -> void:
	if defeated:
		return
	defeated = true
	# The wind drops with it. Check 5 of the boss gate walks Kaya from the arena
	# floor to the gate, and she should be walking out of a calm eyrie.
	_apply_gale([])
	super.die(from)
	if level != null and level.has_method("on_boss_defeated"):
		level.on_boss_defeated(self)
