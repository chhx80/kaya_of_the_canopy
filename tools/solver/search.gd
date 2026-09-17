class_name ProverSearch
extends RefCounted
## One hop of the route: best-first search over the real movement code.
##
## ADR 005 fixes the shape of this deliberately. A blind whole-level search is
## not tractable — greedy best-first solved jungle_2 in 8,461 expansions but gave
## up on jungle_1 and jungle_4 at 400,000, stalling in local minima and never
## finding the transform pads. Decomposing into short hops is not an optimisation,
## it is the reason the prover terminates at all. If a hop needs more than the
## default budget, the hop is too coarse; raising the budget is the wrong fix.

## Four frames per macro, as ADR 005 specifies.
const MACRO := 4

## Action bits. The tape spells these out as `+`-joined names.
const LEFT := 1
const RIGHT := 2
const UP := 4
const DOWN := 8
const JUMP := 16
const ATTACK := 32

const NAMES := {LEFT: "left", RIGHT: "right", UP: "up", DOWN: "down",
	JUMP: "jump", ATTACK: "attack"}


class Result extends RefCounted:
	var found := false
	var actions: PackedInt32Array = PackedInt32Array()   ## one entry per frame
	var expansions := 0
	var closest := 1.0e9
	var closest_at := Vector2.ZERO
	var reason := ""        ## why it stopped, when it did not find anything
	var end_state: Array = []


## {left, none, right} x {jump, no jump} x {none, up, down} = 18.
static func action_set() -> PackedInt32Array:
	var out := PackedInt32Array()
	for h: int in [0, LEFT, RIGHT]:
		for j: int in [0, JUMP]:
			for v: int in [0, UP, DOWN]:
				out.append(h | j | v)
	return out


static func action_name(a: int) -> String:
	var parts: Array[String] = []
	for bit: int in [LEFT, RIGHT, UP, DOWN, JUMP, ATTACK]:
		if a & bit:
			parts.append(String(NAMES[bit]))
	return "+".join(parts) if not parts.is_empty() else "none"


# ---------------------------------------------------------------- the search

## `goals` are entity indices; reaching any of them ends the hop.
## Returns a Result whose `actions` is a per-frame action list from `start`.
func run(sim: ProverSim, start: Array, goals: PackedInt32Array, budget: int) -> Result:
	var res := Result.new()
	var goal_rects: Array[Rect2] = []
	for g: int in goals:
		goal_rects.append(sim.waypoint_rect(g))
	if goal_rects.is_empty():
		res.reason = "the waypoint names nothing in this level"
		return res

	var actions := action_set()
	var input := InputState.new()

	# Parallel node arrays. Packed where the type allows it; a hop can hold
	# several hundred thousand of these and an Array of Dictionaries does not.
	var n_parent := PackedInt32Array([-1])
	var n_action := PackedInt32Array([0])
	var n_frames := PackedInt32Array([0])
	var n_state: Array = [start]

	var seen := {}
	sim.restore(start)
	seen[_key(sim)] = true

	# Binary heap of (priority, node). Pure greedy on manhattan distance, with
	# insertion order breaking ties so a run is reproducible.
	var h_pri := PackedFloat32Array()
	var h_seq := PackedInt32Array()
	var h_node := PackedInt32Array()
	var seq := 0
	_push(h_pri, h_seq, h_node, _dist(sim.actor.aabb(), goal_rects), seq, 0)
	seq += 1

	res.closest = _dist(sim.actor.aabb(), goal_rects)
	res.closest_at = sim.actor.pos

	while h_node.size() > 0:
		if res.expansions >= budget:
			res.reason = "budget of %d expansions spent" % budget
			return res
		var node := _pop(h_pri, h_seq, h_node)
		res.expansions += 1
		var parent_state: Array = n_state[node]

		for a: int in actions:
			sim.restore(parent_state)
			_set_input(input, a, n_action[node])
			var used := 0
			var hit := false
			var bad := ""
			for f in MACRO:
				sim.step(input)
				# Only the first frame of a macro is a fresh press; the rest are
				# a held button, which is what a human's thumb actually does and
				# what the tape has to reproduce.
				input.jump_pressed = false
				input.attack_pressed = false
				input.jump_released = false
				used += 1
				bad = sim.rejection()
				if bad != "":
					break
				if _reached(sim.actor.aabb(), goal_rects):
					hit = true
					break
			if bad != "":
				continue

			var box := sim.actor.aabb()
			var d := _dist(box, goal_rects)
			if d < res.closest:
				res.closest = d
				res.closest_at = sim.actor.pos

			if hit:
				res.found = true
				res.end_state = sim.snapshot()
				res.actions = _unwind(n_parent, n_action, n_frames, node)
				for _i in used:
					res.actions.append(a)
				return res

			var k := _key(sim)
			if seen.has(k):
				continue
			seen[k] = true
			n_parent.append(node)
			n_action.append(a)
			n_frames.append(used)
			n_state.append(sim.snapshot())
			_push(h_pri, h_seq, h_node, d, seq, n_state.size() - 1)
			seq += 1

	res.reason = "frontier exhausted after %d expansions — no route exists for this action set" \
		% res.expansions
	return res


## Rebuild the per-frame action list from the parent chain.
func _unwind(parent: PackedInt32Array, action: PackedInt32Array,
		frames: PackedInt32Array, node: int) -> PackedInt32Array:
	var chain: Array[int] = []
	var n := node
	while n > 0:
		chain.append(n)
		n = parent[n]
	chain.reverse()
	var out := PackedInt32Array()
	for i: int in chain:
		for _f in frames[i]:
			out.append(action[i])
	return out


func _set_input(input: InputState, a: int, prev: int) -> void:
	input.left = a & LEFT != 0
	input.right = a & RIGHT != 0
	input.up = a & UP != 0
	input.down = a & DOWN != 0
	var was_jump := prev & JUMP != 0
	var was_attack := prev & ATTACK != 0
	input.jump = a & JUMP != 0
	input.attack = a & ATTACK != 0
	# The edges are what coyote/buffer and the wall-kick read, so they have to
	# be derived from the previous macro rather than asserted every frame.
	input.jump_pressed = input.jump and not was_jump
	input.jump_released = was_jump and not input.jump
	input.attack_pressed = input.attack and not was_attack
	input._prev_jump = was_jump
	input._prev_attack = was_attack


static func _reached(box: Rect2, goals: Array[Rect2]) -> bool:
	for g: Rect2 in goals:
		if g.intersects(box):
			return true
	return false


## Manhattan gap between two rectangles — zero once they touch.
static func _dist(box: Rect2, goals: Array[Rect2]) -> float:
	var best := 1.0e9
	for g: Rect2 in goals:
		var dx: float = maxf(0.0, maxf(g.position.x - box.end.x, box.position.x - g.end.x))
		var dy: float = maxf(0.0, maxf(g.position.y - box.end.y, box.position.y - g.end.y))
		best = minf(best, dx + dy)
	return best


## Duplicate-state key. Position is bucketed to the whole pixel and velocity to
## 8 px/s — coarse enough to collapse the frontier, fine enough that a jump
## decided by six pixels is still its own state. Every bucket can only ever
## *remove* a state, so the failure direction stays safe.
func _key(sim: ProverSim) -> int:
	var k := clampi(int(floor(sim.actor.pos.x)) + 128, 0, 2047)
	k = (k << 11) | clampi(int(floor(sim.actor.pos.y)) + 128, 0, 2047)
	k = (k << 8) | clampi(int(round(sim.actor.vel.x / 8.0)) + 128, 0, 255)
	k = (k << 8) | clampi(int(round(sim.actor.vel.y / 8.0)) + 128, 0, 255)
	k = (k << 2) | ProverSim.FORM_IDS.find(sim.form_id)
	k = (k << 1) | (1 if sim.actor.on_floor else 0)
	# Direct member reads: these are FormBase fields, so no reflection needed.
	k = (k << 1) | (1 if sim.form.climbing else 0)
	k = (k << 1) | (1 if sim.form.coyote > 0.0 else 0)
	k = (k << 1) | (1 if sim.form.buffer > 0.0 else 0)
	k = (k << 2) | (sim.switch_bits & 3)
	k = (k << 7) | (sim.opened & 127)
	k = (k << 7) | (sim.taken & 127)
	return k


# ---------------------------------------------------------------- binary heap

func _push(pri: PackedFloat32Array, seqs: PackedInt32Array, node: PackedInt32Array,
		p: float, s: int, n: int) -> void:
	pri.append(p)
	seqs.append(s)
	node.append(n)
	var i := node.size() - 1
	while i > 0:
		var parent := (i - 1) >> 1
		if pri[parent] < pri[i] or (pri[parent] == pri[i] and seqs[parent] <= seqs[i]):
			break
		_swap(pri, seqs, node, i, parent)
		i = parent


func _pop(pri: PackedFloat32Array, seqs: PackedInt32Array, node: PackedInt32Array) -> int:
	var top := node[0]
	var last := node.size() - 1
	_swap(pri, seqs, node, 0, last)
	pri.resize(last)
	seqs.resize(last)
	node.resize(last)
	var i := 0
	while true:
		var l := 2 * i + 1
		var r := l + 1
		var small := i
		if l < last and (pri[l] < pri[small] or (pri[l] == pri[small] and seqs[l] < seqs[small])):
			small = l
		if r < last and (pri[r] < pri[small] or (pri[r] == pri[small] and seqs[r] < seqs[small])):
			small = r
		if small == i:
			break
		_swap(pri, seqs, node, i, small)
		i = small
	return top


func _swap(pri: PackedFloat32Array, seqs: PackedInt32Array, node: PackedInt32Array,
		a: int, b: int) -> void:
	var fp := pri[a]; pri[a] = pri[b]; pri[b] = fp
	var s := seqs[a]; seqs[a] = seqs[b]; seqs[b] = s
	var n := node[a]; node[a] = node[b]; node[b] = n
