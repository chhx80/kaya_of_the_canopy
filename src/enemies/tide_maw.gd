extends Enemy
## THE TIDE MAW — World 2's boss. Three scripted phases driven entirely by
## data/enemies/tide_maw.json, the same data-driven machine as
## src/enemies/boss_grove.gd and deliberately not a second one:
##
##   EBB       the arena is drained. It lurches along the bed and CRASHES, and
##             the crash throws a bore — a wave running the floor both ways.
##   FLOOD     the arena floods. Same crash, plus a spray of spines, and the
##             water it brought in carries a current.
##   UNDERTOW  the tide goes out again, fastest and angriest.
##
## Two things here are not in boss_grove.gd.
##
## **The tide is a real tile change.** `_apply_tide()` writes water, a surface
## row and two lanes of current into the arena's tile grid and takes them out
## again, so being flooded is a fact about the world and not a tint: the fish
## can swim in it, the human wades in it, `FormBase.current_at()` pushes both,
## and `TileCollision` answers the same questions it always did. It is bounded
## by three rules, because a boss that edits the level is a boss that can break
## it:
##
##   1. it only ever writes into the rectangle `tide.x/y/w/h` names;
##   2. inside that rectangle it only touches tiles the LEVEL AUTHORED EMPTY —
##      the flanking shelves stay shelves, the floor stays floor;
##   3. draining restores the captured ids, so drained is bit-identical to the
##      level as shipped. levels/ruins_5.json is authored drained and phase 1
##      is drained, which is what lets tools/prove.sh and the tape replay see
##      exactly the geometry in the file.
##
## Water is not solid and does not change what `TileCollision.is_on_floor()`
## answers, so the set of standable tiles is the same in both tide states. That
## is what makes the Boss Gate's fairness sweep — which finds the standable
## tiles once and then sweeps every phase — mean what it says here.
##
## **The arena is narrower than the screen.** `arena_inset` clamps the Maw to a
## pit inside its own screen (cols 31–43 of ruins_5) rather than to the screen,
## because the fall into the arena has to land somewhere the level's tape can be
## checked against and because the fight reads better anchored. The refuge slabs
## sit INSIDE that span, not outside it, and the 46 px hitbox is the number that
## makes them work: from a slab the blade reaches the Maw (a refuge you cannot
## shoot back from is a stalemate — the note tools/bossgate.sh prints about the
## Grove Warden) and the Maw reaches you (a refuge it can never stand under is a
## corner to camp in). Nothing in this arena is safe from everything; every
## attack has somewhere that is safe from it, which is what check 3 asks.

## Same six states, in the same order, as boss_grove.gd. Not a coincidence and
## not free to change: tests/integration/boss_gate_checks.gd names an attack by
## the state transition it fired on and reads those names out of a fixed list,
## and boss_gate_strategy.gd watches for WINDUP -> AIR to time its pass.
enum St { IDLE, WALK, WINDUP, AIR, LAND, SPRAY }

var st: St = St.IDLE
var t := 0.0
var phase := 0
var phase_cfg: Dictionary = {}
var spray_t := 0.0
var arena_min := 0.0
var arena_max := 0.0
var defeated := false

## The tide, and the arena exactly as the level authored it.
var flooded := false
var _tide: Dictionary = {}
var _authored: PackedInt32Array = PackedInt32Array()

func on_configured() -> void:
	_tide = cfg.get("tide", {})
	_capture_arena()
	_set_phase(0)

func _ready() -> void:
	super._ready()
	add_to_group(&"bosses")
	# Lock the Maw to the pit, not to the screen. boss_grove.gd insets by 8 px;
	# this one insets by whatever data/enemies/tide_maw.json says, which is how
	# the flanking shelves become somewhere it cannot reach.
	var origin := Screen.origin(home_screen)
	var inset := float(cfg.get("arena_inset", 8.0))
	arena_min = origin.x + inset
	arena_max = origin.x + Screen.W - inset - box.x
	t = 0.9

func on_respawn() -> void:
	st = St.IDLE
	t = 0.9
	_set_phase(0)

func _set_phase(i: int) -> void:
	var phases: Array = cfg.get("phases", [])
	if phases.is_empty():
		return
	phase = clampi(i, 0, phases.size() - 1)
	phase_cfg = phases[phase]
	spray_t = float(phase_cfg.get("spray_interval", 2.0))
	_apply_tide(String(phase_cfg.get("tide", "drain")) == "flood")

## STOMP/LEAP/FURY are three animals in the Warden's sheet and EBB/FLOOD/
## UNDERTOW are three here, so each pose exists once per phase as
## `<pose>_p1/_p2/_p3`. Anything without a per-phase variant falls back to the
## plain name, so the state machine never has to know about this.
func set_anim(pose: String) -> void:
	var key := "%s_p%d" % [pose, phase + 1]
	var anims: Dictionary = cfg.get("anim", {})
	super.set_anim(key if anims.has(key) else pose)

func hurt(amount: int, from: Vector2 = Vector2.ZERO) -> void:
	super.hurt(amount, from)
	# Phase boundaries are health thresholds, so a burst of damage can skip one.
	var phases: Array = cfg.get("phases", [])
	for i in phases.size():
		if health <= int((phases[i] as Dictionary).get("until_health", 0)) and i + 1 < phases.size():
			if phase < i + 1:
				_set_phase(i + 1)
				AudioManager.play("boss_phase")

# ---------------------------------------------------------------- the tide
## Remember the arena exactly as the level drew it, once, before anything has
## been written. Draining restores these ids, so a drained arena is the level
## file and not an approximation of it.
func _capture_arena() -> void:
	_authored = PackedInt32Array()
	if world == null or _tide.is_empty():
		return
	var x0 := int(_tide.get("x", 0))
	var y0 := int(_tide.get("y", 0))
	var w := int(_tide.get("w", 0))
	var h := int(_tide.get("h", 0))
	_authored.resize(w * h)
	for j in h:
		for i in w:
			_authored[j * w + i] = world.get_fg(x0 + i, y0 + j)

## Flood or drain. Only ever writes inside the tide rect, and inside it only
## over tiles the level authored empty — so no amount of tide can eat a shelf,
## a floor or a wall.
func _apply_tide(want_flood: bool) -> void:
	flooded = want_flood
	if world == null or _tide.is_empty() or _authored.is_empty():
		return
	var x0 := int(_tide.get("x", 0))
	var y0 := int(_tide.get("y", 0))
	var w := int(_tide.get("w", 0))
	var h := int(_tide.get("h", 0))
	for j in h:
		for i in w:
			var authored := _authored[j * w + i]
			if authored != 0:
				continue                      # shelf, floor, wall: never ours
			world.set_fg(x0 + i, y0 + j, _flood_tile(x0 + i, y0 + j) if want_flood else 0)
	_repaint()
	# "switch" is the sound of a mechanism changing state, which is what this
	# is; there is no splash in assets/audio/sfx and inventing one is the art
	# pipeline's job, not this branch's.
	AudioManager.play("switch")

## Making the tide VISIBLE, which is a separate problem from making it real.
##
## `TileRenderer` resolves each tile's atlas cell once, at setup, from its
## neighbours (`TileVariants.for_world`), and `_draw()` prefers that resolved
## cell over the tile's own id. So a tile whose id changes underneath it keeps
## drawing the cell it was authored with: measured, the arena flooded, the
## collision changed, the human waded and the fish could have swum — and the
## screenshot showed dry stone. That is this project's own failure mode in one
## frame, the mechanism working and the outcome invisible, so it is worth the
## comment.
##
## Re-resolving is the whole fix. It costs one neighbour sweep of the level per
## tide change, which is twice a fight.
func _repaint() -> void:
	if level == null:
		return
	var fg: Node = level.get("tiles_fg")
	if fg == null or not fg.has_method("setup"):
		return
	TileVariants.release()
	fg.call("setup", world, "fg")

## Which water goes in this cell: the surface row, one of the current lanes, or
## plain water. A lane flowing "in" points at `pivot` — that is the Maw's pull,
## and it lies along the bed where a body has to stand. The lane flowing "out"
## is the counter-current, one tile under the surface, and it is the way out of
## the pull: you ride it, you do not outrun it. A human wades at 108 x 0.62 =
## 67 px/s and the pull is 68.
func _flood_tile(x: int, y: int) -> int:
	if y == int(_tide.get("y", 0)):
		return int(_tide.get("surface", 7))
	var pivot := int(_tide.get("pivot", 0))
	for raw: Variant in (_tide.get("lanes", []) as Array):
		var lane: Dictionary = raw
		if int(lane.get("row", -1)) != y:
			continue
		var outward := String(lane.get("flow", "in")) == "out"
		var west: bool = x < pivot
		# west + outward -> left; west + inward -> right; and mirrored east.
		var left := west == outward
		return int(_tide.get("cur_left" if left else "cur_right", 8))
	return int(_tide.get("water", 8))

# ---------------------------------------------------------------- the fight
func think(delta: float) -> void:
	# The refuge slabs are one-way platforms inside the Maw's own span, and its
	# slam clears 56 px against their 32 — so without this it would land ON a
	# refuge, which is both absurd and the end of the dodge window that slab
	# exists to be. `drop_through` is Actor's own switch for "one-ways are not
	# floors this tick"; the Maw is never anything but on the bed.
	drop_through = true
	apply_gravity(delta)
	t = maxf(0.0, t - delta)
	var p := player()
	var walk: float = float(phase_cfg.get("walk_speed", 46.0))

	match st:
		St.IDLE:
			vel.x = move_toward(vel.x, 0.0, 400.0 * delta)
			set_anim("idle")
			if t <= 0.0:
				st = St.WALK
				t = float(phase_cfg.get("slam_interval", 2.4))
		St.WALK:
			set_anim("walk")
			if p != null and not p.dead:
				facing = 1 if p.center().x > center().x else -1
			vel.x = walk * facing
			if pos.x <= arena_min and facing < 0:
				facing = 1
			elif pos.x >= arena_max and facing > 0:
				facing = -1
			if t <= 0.0 and on_floor:
				st = St.WINDUP
				t = 0.45
			_maybe_spray(delta)
		St.WINDUP:
			vel.x = move_toward(vel.x, 0.0, 900.0 * delta)
			set_anim("windup")
			if t <= 0.0:
				vel.y = float(phase_cfg.get("slam_jump", -250.0))
				vel.x = walk * 1.6 * facing
				st = St.AIR
				AudioManager.play("boss_jump")
		St.AIR:
			set_anim("air")
			if pos.x <= arena_min or pos.x >= arena_max:
				vel.x = -vel.x
				facing = -facing
			if on_floor and vel.y >= 0.0:
				_crash()
				st = St.LAND
				t = 0.5
		St.LAND:
			vel.x = move_toward(vel.x, 0.0, 700.0 * delta)
			set_anim("land")
			if t <= 0.0:
				st = St.WALK
				t = float(phase_cfg.get("slam_interval", 2.4))
		St.SPRAY:
			vel.x = 0.0
			set_anim("windup")
			if t <= 0.0:
				_spray()
				st = St.WALK
				t = float(phase_cfg.get("slam_interval", 2.4))
	_hold_the_arena(delta)

## Check 4 of the boss gate is "the boss stays inside arena_min/arena_max", and
## it is measured at the END of the physics frame — after `step_motion()`, which
## runs after `think()`. boss_grove.gd clamps `pos.x` here and gets away with it
## because its arena is the whole screen and the screen has walls; this arena is
## a pit inside the screen, and while the Maw is airborne it is above the shelves
## that would otherwise stop it. Clamping the position and then moving left the
## Maw about two pixels outside its own arena on two frames, and two frames is a
## failure. So the clamp bites on the VELOCITY, before the move that would use
## it, and the position clamp stays as the backstop.
func _hold_the_arena(delta: float) -> void:
	pos.x = clampf(pos.x, arena_min, arena_max)
	if delta <= 0.0:
		return
	var next_x := pos.x + vel.x * delta
	if next_x < arena_min:
		vel.x = (arena_min - pos.x) / delta
	elif next_x > arena_max:
		vel.x = (arena_max - pos.x) / delta

func _maybe_spray(delta: float) -> void:
	if int(phase_cfg.get("spray", 0)) <= 0:
		return
	spray_t = maxf(0.0, spray_t - delta)
	if spray_t <= 0.0:
		spray_t = float(phase_cfg.get("spray_interval", 2.0))
		st = St.SPRAY
		t = 0.4

## The spines. An upward fan, so it is short-ranged by construction and the way
## to dodge it is distance, not height — the opposite of the bore, which is why
## the two attacks are worth having together.
func _spray() -> void:
	var n := int(phase_cfg.get("spray", 5))
	var pj: Dictionary = cfg.get("projectile", {})
	for i in n:
		var a := lerpf(-0.9, 0.9, float(i) / maxf(1.0, float(n - 1)))
		var dir := Vector2(sin(a) * float(facing), -cos(a) * 0.6 - 0.35)
		var shot := Projectile.new()
		shot.setup(pj, center() + Vector2(0, -6), dir, world, level)
		level.entities.add_child(shot)
	AudioManager.play("spit")

## The bore: the crash throws a wave along the bed in both directions, four
## pixels off the floor. It is the fight's main attack and it is dodged by
## being on a shelf — 32 px up, and behind the shelf's own solid face, which is
## what stops the wave rather than a rule saying it stops.
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
	# The tide goes out with it. Check 5 of the boss gate walks Kaya from the
	# arena floor to the gate, and it should be walking out of a drained ruin
	# and not swimming out of a flooded one.
	_apply_tide(false)
	super.die(from)
	if level != null and level.has_method("on_boss_defeated"):
		level.on_boss_defeated(self)
