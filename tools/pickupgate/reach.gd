class_name PickupReach
extends RefCounted
## Can the real body TOUCH a rectangle, starting from a given state?
##
## The Route Prover's search (ProverSearch) with the two differences a pickup
## needs, and nothing else changed. The physics is ProverSim's -- the shipping
## `form.update()` + `actor.step_motion()` at 60 Hz -- so a REACHED verdict is a
## replayable tape, not an opinion.
##
##   * THE GOAL IS TOUCH, NOT STAND.  `Pickup._physics_process` collects on any
##     overlap of its 12x12 box with the player's, mid-jump included, and a pad
##     fires on its box grown by 3 px. So the goal is overlap on any frame, which
##     is what the trigger itself checks. `stand` asks the prover's question
##     instead (on the floor, climbing, swimming or the bird), for "can she get
##     THERE and stay" -- the question a "stuck" report asks.
##   * ATTACK IS PRESSED, AND A BROKEN TILE IS PART OF THE STATE.  The prover
##     cannot break a wall (ProverSearch.action_set() has no ATTACK, and its
##     snapshot leaves TileWorld._broken out); a player can, and World 4 hides
##     its hearts behind walls on purpose. Here a state carries the broken set,
##     the shoulder's `break_progress` and the blade's reload, so a wall broken
##     on one branch is not broken on another, and holding attack against a wall
##     is not deduplicated into standing still.
##   * THE BLADE IS THROWN.  It is a Node the prover never builds, and some
##     walls (deep_glowwall 270, jungle crates) declare no break_hold, so only
##     the blade opens them. A press of attack by a form that carries the
##     boomerang blade flies Blade's OUT leg -- its own numbers, a real Actor,
##     the real TileCollision -- and breaks what it strikes, as
##     Blade._hit_tiles() does. Two liberties, both small, both in the generous
##     direction and both said here: the tiles break on the frame of the press
##     rather than when the blade arrives (at most ~0.6 s early), and the next
##     throw is allowed once the out leg has had time to fly there and back,
##     rather than when the blade is caught.
##
## Not modelled, as in the prover: enemies, and hazards are pruned unless
## `sim.allow_hazard` is set.

const MACRO := 4
const DT := 1.0 / 60.0
const ATTACK := ProverSearch.ATTACK

var sim: ProverSim = null
## Frames until the modelled blade can be thrown again. Part of the state.
var blade_cd := 0
var _blade_cfg: Dictionary = {}
var _blade: Actor = null


func _init(s: ProverSim) -> void:
	sim = s
	var f := FileAccess.open("res://data/weapons/boomerang_blade.json", FileAccess.READ)
	if f != null:
		var parsed: Variant = JSON.parse_string(f.get_as_text())
		f.close()
		if typeof(parsed) == TYPE_DICTIONARY:
			_blade_cfg = parsed
	_blade = Actor.new()


## The blade's body is an Actor, which is a Node: free it when done.
func dispose() -> void:
	if _blade != null:
		_blade.free()
		_blade = null


static func has_breakables(s: ProverSim) -> bool:
	for y in s.world.height:
		for x in s.world.width:
			if s.world.flags_at(x, y) & TileData4.Flag.BREAKABLE:
				return true
	return false


## The trigger box an entity fires on, exactly as its script sizes it:
## level.gd places a pickup at p + (2, 2) with Pickup.SIZE, and a pad at
## p + (0, 8) with TransformPad.SIZE, which fires on that box grown by 3.
static func target_rect(e: Dictionary) -> Rect2:
	var p := Vector2(float(e.get("x", 0)) * 16.0, float(e.get("y", 0)) * 16.0)
	if String(e.get("type", "")).begins_with("pad_"):
		return Rect2(p + Vector2(0, 8), TransformPad.SIZE).grow(3.0)
	return Rect2(p + Vector2(2, 2), Pickup.SIZE)


static func tile_rect(t: Vector2i) -> Rect2:
	return Rect2(Vector2(t) * 16.0, Vector2(16, 16))


## Put the body on a tile as `form`, feet on the floor of row `t.y`, centred in
## the column, and give it the prover's four settle frames. The world is left as
## it is -- including any tile a previous search broke.
func seed_at(t: Vector2i, form: String) -> Array:
	sim.set_form(form)
	sim.actor.pos = Vector2(t.x * 16.0 + 8.0 - sim.actor.box.x * 0.5,
		(t.y + 1) * 16.0 - sim.actor.box.y)
	sim.actor.vel = Vector2.ZERO
	var neutral := InputState.new()
	for _i in 4:
		sim.step(neutral)
	return snap()


# ---------------------------------------------------------------- state

## ProverSim's snapshot, plus what it leaves out: the broken tiles and the blade.
func snap() -> Array:
	var b := PackedInt32Array()
	for k: Variant in sim.world._broken.keys():
		b.append(int(k))
	b.sort()
	return [sim.snapshot(), b, blade_cd]


func restore(s: Array) -> void:
	sim.restore(s[0])
	sim.world._broken.clear()
	for k: int in (s[1] as PackedInt32Array):
		sim.world._broken[k] = true
	blade_cd = int(s[2])


## ProverSearch._key's buckets, plus the state that makes breaking possible at
## all: the shoulder's progress (or a body pressed still against a wall would be
## the same state every macro and the hold could never finish), the blade's
## reload, and the broken set (or two branches would share a wall).
func _key() -> int:
	var a := sim.actor
	var f := sim.form
	return hash([int(floor(a.pos.x)), int(floor(a.pos.y)),
		int(round(a.vel.x / 8.0)), int(round(a.vel.y / 8.0)), sim.form_id,
		a.on_floor, f.climbing, f.coyote > 0.0, f.buffer > 0.0,
		sim.switch_bits, sim.opened, sim.taken,
		int(f.break_progress * 60.0), blade_cd > 0,
		sim.world._broken.size(), hash(sim.world._broken.keys())])


# ---------------------------------------------------------------- one frame

## The prover's tick, then the blade, in the order Player runs them
## (form.update, then try_attack). The sim has already moved the body when the
## blade leaves, which puts the throw one frame later than the game would.
func tick(input: InputState) -> void:
	sim.step(input)
	if blade_cd > 0:
		blade_cd -= 1
	elif input.attack_pressed and sim.form.can_attack \
			and sim.form.weapon_id() == "boomerang_blade":
		blade_cd = _throw()


## Blade.setup() and the OUT half of Blade._physics_process(), on a real Actor.
## Returns the frames before another throw is allowed.
func _throw() -> int:
	var b := _blade
	var hb: Dictionary = _blade_cfg.get("hitbox", {})
	b.world = sim.world
	b.box = Vector2(float(hb.get("w", 12)), float(hb.get("h", 12)))
	b.facing = sim.actor.facing
	b.on_floor = false
	b.set_center(sim.actor.center() + Vector2(b.facing * 8.0, 0.0))
	var origin := b.center()
	b.vel = Vector2(float(_blade_cfg.get("speed", 205.0)) * b.facing,
		float(_blade_cfg.get("rise", -18.0)))
	var reach := float(_blade_cfg.get("max_range", 118.0))
	var frames := 0
	while frames < 120:
		frames += 1
		if origin.distance_to(b.center()) >= reach:
			break
		b.step_motion(DT)
		if b.against_wall != 0 or b.on_ceiling or b.on_floor:
			for t in TileCollision.tiles_with_flag(sim.world, b.aabb().grow(2.0),
					TileData4.Flag.BREAKABLE):
				sim.world.break_tile(t.x, t.y)
			break
	var cooldown := int(ceil(float(_blade_cfg.get("cooldown", 0.26)) * 60.0))
	return maxi(cooldown, frames * 2)


static func actions(attack: bool) -> PackedInt32Array:
	var out := ProverSearch.action_set()
	if attack:
		# Shouldering is a hold in a direction, and a throw is a press facing
		# one; jumping while doing either buys nothing a separate jump does not.
		for h: int in [0, ProverSearch.LEFT, ProverSearch.RIGHT]:
			for v: int in [0, ProverSearch.UP, ProverSearch.DOWN]:
				out.append(h | v | ATTACK)
	return out


func touching(goal: Rect2, stand: bool) -> bool:
	if not goal.intersects(sim.actor.aabb()):
		return false
	if not stand:
		return true
	return sim.actor.on_floor or sim.form.climbing or sim.actor.submerged() \
		or sim.form_id == "bird"


static func gap(box: Rect2, g: Rect2) -> float:
	var dx: float = maxf(0.0, maxf(g.position.x - box.end.x, box.position.x - g.end.x))
	var dy: float = maxf(0.0, maxf(g.position.y - box.end.y, box.position.y - g.end.y))
	return dx + dy


# ---------------------------------------------------------------- the search

## Best-first on manhattan gap -- ProverSearch's frontier, with touch as the goal.
## Returns {found, actions, expansions, closest, closest_at, broke, exhausted}.
func search(start: Array, held: int, goal: Rect2, stand: bool, attack: bool,
		budget: int) -> Dictionary:
	var res := {"found": false, "actions": PackedInt32Array(), "expansions": 0,
		"closest": 1.0e9, "closest_at": Vector2.ZERO, "broke": 0, "exhausted": false}
	var acts := actions(attack)
	var input := InputState.new()
	var n_parent := PackedInt32Array([-1])
	var n_action := PackedInt32Array([held])
	var n_frames := PackedInt32Array([0])
	var n_state: Array = [start]
	var seen := {}
	restore(start)
	if touching(goal, stand):
		res["found"] = true
		return res
	seen[_key()] = true
	var heap := _Heap.new()
	heap.push(gap(sim.actor.aabb(), goal), 0)
	res["closest"] = gap(sim.actor.aabb(), goal)
	res["closest_at"] = sim.actor.pos
	var expansions := 0
	while heap.size() > 0:
		if expansions >= budget:
			res["expansions"] = expansions
			return res
		var node := heap.pop()
		expansions += 1
		for a: int in acts:
			restore(n_state[node])
			ProverTape.apply(input, a, n_action[node])
			var used := 0
			var hit := false
			var bad := ""
			for _f in MACRO:
				tick(input)
				# Only a macro's first frame is a press; the rest are a held
				# button, which is what the tape has to reproduce.
				input.jump_pressed = false
				input.attack_pressed = false
				input.jump_released = false
				input._prev_jump = input.jump
				input._prev_attack = input.attack
				used += 1
				bad = sim.rejection()
				if bad != "":
					break
				if touching(goal, stand):
					hit = true
					break
			if bad != "":
				continue
			var d := gap(sim.actor.aabb(), goal)
			if d < float(res["closest"]):
				res["closest"] = d
				res["closest_at"] = sim.actor.pos
			if hit:
				res["found"] = true
				res["actions"] = _unwind(n_parent, n_action, n_frames, node, a, used)
				res["expansions"] = expansions
				res["broke"] = sim.world._broken.size() - (start[1] as PackedInt32Array).size()
				return res
			var k := _key()
			if seen.has(k):
				continue
			seen[k] = true
			n_parent.append(node)
			n_action.append(a)
			n_frames.append(used)
			n_state.append(snap())
			heap.push(d, n_state.size() - 1)
	res["expansions"] = expansions
	res["exhausted"] = true
	return res


func _unwind(parent: PackedInt32Array, action: PackedInt32Array, frames: PackedInt32Array,
		node: int, last: int, used: int) -> PackedInt32Array:
	var chain: Array[int] = []
	var n := node
	while n > 0:
		chain.append(n)
		n = parent[n]
	chain.reverse()
	var out := PackedInt32Array()
	for i: int in chain:
		for _k in frames[i]:
			out.append(action[i])
	for _k in used:
		out.append(last)
	return out


## Replay a found tape from its start in a fresh restore and require it to touch
## the goal again. A search that explores by snapshot and restore can believe
## things its buttons do not reproduce; the prover learned that three times.
func replays(start: Array, held: int, acts: PackedInt32Array, goal: Rect2,
		stand: bool) -> bool:
	restore(start)
	if touching(goal, stand):
		return true
	var input := InputState.new()
	var prev := held
	for a: int in acts:
		ProverTape.apply(input, a, prev)
		tick(input)
		prev = a
		if touching(goal, stand):
			return true
	return false


class _Heap extends RefCounted:
	var pri := PackedFloat32Array()
	var seq := PackedInt32Array()
	var node := PackedInt32Array()
	var _n := 0

	func size() -> int:
		return node.size()

	func push(p: float, n: int) -> void:
		pri.append(p)
		seq.append(_n)
		node.append(n)
		_n += 1
		var i := node.size() - 1
		while i > 0:
			var up := (i - 1) >> 1
			if _less(up, i):
				break
			_swap(i, up)
			i = up

	func pop() -> int:
		var top := node[0]
		var last := node.size() - 1
		_swap(0, last)
		pri.resize(last)
		seq.resize(last)
		node.resize(last)
		var i := 0
		while true:
			var l := 2 * i + 1
			var r := l + 1
			var s := i
			if l < last and _less(l, s):
				s = l
			if r < last and _less(r, s):
				s = r
			if s == i:
				break
			_swap(i, s)
			i = s
		return top

	func _less(a: int, b: int) -> bool:
		return pri[a] < pri[b] or (pri[a] == pri[b] and seq[a] < seq[b])

	func _swap(a: int, b: int) -> void:
		var fp := pri[a]; pri[a] = pri[b]; pri[b] = fp
		var s := seq[a]; seq[a] = seq[b]; seq[b] = s
		var n := node[a]; node[a] = node[b]; node[b] = n
