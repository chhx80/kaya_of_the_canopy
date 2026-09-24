extends TestCase
## Proof that every gateway on staging/hub_v2.json can actually be reached.
##
## The overworld is top-down with no gravity, so none of the platformer
## reachability rules apply — but "the door is on the map" is exactly the kind
## of statement that shipped six unfinishable levels. The mechanism is not the
## outcome. So this file does two independent things, in the order of least to
## most evidence:
##
##   1. A flood fill over the space of *player positions* — not tiles. A
##      position is a place the real 10x10 HubPlayer box can be without
##      overlapping a tile TileWorld.is_solid() calls solid. Steps are one
##      pixel along one axis, which is less than the 1.23 px a frame of walking
##      covers, so nothing here is a step the character could not take.
##
##   2. An actual walk. For every gateway, a simulated HubPlayer — real box,
##      real SPEED/ACCEL/FRICTION out of src/hub/hub_player.gd, real
##      TileCollision.move_x/move_y — is driven from the spawn along the route
##      the flood fill found, one 60 Hz frame at a time, and has to arrive.
##      This is what covers the gap the flood fill leaves: the character
##      accelerates and slides, and a path through free space is not the same
##      claim as a character that gets there.
##
## Plus a negative control: seal a gateway in and confirm the flood fill
## reports it. A prover that cannot fail proves nothing.

const TS := TileData4.TILE_SIZE

## Copied from the shipping hub. test_the_numbers_this_file_trusts_are_still_
## the_ones_the_game_uses pins each of them to its source line.
const BOX := Vector2(10, 10)             ## HubPlayer._ready()
const SPAWN_OFFSET := Vector2(3, 5)      ## overworld.gd, _load()
const RETURN_OFFSET := Vector2(3, 20)    ## overworld.gd, _move_player_to_door()
const DOOR_GROW := 6.0                   ## overworld.gd, _physics_process()

const FRAME := 1.0 / 60.0
## A walk that has not arrived in this many frames has not arrived. The longest
## real route is about 2,000 px, or 1,600 frames at the walk speed.
const WALK_FRAME_BUDGET := 6000
const ARRIVE := 2.0                      ## px; a waypoint is "reached" inside this
## How far a waypoint may be nudged to sit in the middle of its corridor
## instead of scraping the wall the flood fill happened to hug. A player walks
## down the middle of a path; the flood fill does not care where it walks.
const SLIDE := 12

var def: LevelLoader.LevelDef = null
var doors: Array = []

# --- the flood, computed once for the file
var _free: PackedByteArray = PackedByteArray()
var _seen: PackedByteArray = PackedByteArray()
var _from: PackedInt32Array = PackedInt32Array()
var _stride := 0
var _pw := 0
var _ph := 0
var _flooded := false

## tools/build_hub.py writes staging/hub_v2.json; the merge that adopts it
## renames that to levels/hub.json. Follow the file, so this proof does not
## quietly stop running on the day it becomes the real overworld.
func _hub_id() -> String:
	return "hub_v2" if FileAccess.file_exists("res://staging/hub_v2.json") else "hub"


func _load_hub() -> LevelLoader.LevelDef:
	if FileAccess.file_exists("res://staging/hub_v2.json"):
		return LevelLoader.load_path("res://staging/hub_v2.json", "hub_v2")
	return LevelLoader.load_level("hub")

func before_each() -> void:
	if def == null:
		def = _load_hub()
		if def.ok():
			doors = def.entities_of("hub_door")
	if not _flooded and def.ok():
		_flooded = true
		_free = _free_mask(def.world)
		_flood(def.spawn + SPAWN_OFFSET)

# ---------------------------------------------------------------- free space
## One byte per top-left position the box could take. The tile span is worked
## out the way TileCollision.tile_range() works it out, so a box whose edge
## lands exactly on a tile boundary is judged here exactly as the game judges
## it: `(p + size - EPS) / TS`, which for whole pixels is `(p + size - 1) / TS`.
func _free_mask(world: TileWorld) -> PackedByteArray:
	_pw = world.width * TS - int(BOX.x)
	_ph = world.height * TS - int(BOX.y)
	_stride = _pw + 1
	var solid := PackedByteArray()
	solid.resize(world.width * world.height)
	for y in world.height:
		for x in world.width:
			solid[y * world.width + x] = 1 if world.is_solid(x, y) else 0
	var bw := int(BOX.x)
	var bh := int(BOX.y)
	var out := PackedByteArray()
	out.resize(_stride * (_ph + 1))
	for py in _ph + 1:
		var ty0 := py / TS
		var ty1 := (py + bh - 1) / TS
		var row := py * _stride
		for px in _pw + 1:
			var tx0 := px / TS
			var tx1 := (px + bw - 1) / TS
			var blocked := false
			for ty in range(ty0, ty1 + 1):
				for tx in range(tx0, tx1 + 1):
					if solid[ty * world.width + tx] == 1:
						blocked = true
						break
				if blocked:
					break
			out[row + px] = 0 if blocked else 1
	return out

func _index(p: Vector2) -> int:
	var x := int(p.x)
	var y := int(p.y)
	if x < 0 or y < 0 or x > _pw or y > _ph:
		return -1
	return y * _stride + x

func _is_free(p: Vector2) -> bool:
	var i := _index(p)
	return i >= 0 and _free[i] == 1

func _reached(p: Vector2) -> bool:
	var i := _index(p)
	return i >= 0 and _seen[i] == 1

## Breadth-first over free positions, one pixel at a time, four ways. Records
## where each position was entered from so a route can be read back out.
func _flood(start: Vector2) -> void:
	_seen = PackedByteArray()
	_seen.resize(_free.size())
	_from = PackedInt32Array()
	_from.resize(_free.size())
	var s := _index(start)
	if s < 0 or _free[s] == 0:
		return
	_from[s] = -1
	_seen[s] = 1
	var queue := PackedInt32Array()
	queue.resize(_free.size())
	queue[0] = s
	var head := 0
	var tail := 1
	while head < tail:
		var i := queue[head]
		head += 1
		var x := i % _stride
		var y := i / _stride
		if x > 0 and _seen[i - 1] == 0 and _free[i - 1] == 1:
			_seen[i - 1] = 1
			_from[i - 1] = i
			queue[tail] = i - 1
			tail += 1
		if x < _pw and _seen[i + 1] == 0 and _free[i + 1] == 1:
			_seen[i + 1] = 1
			_from[i + 1] = i
			queue[tail] = i + 1
			tail += 1
		if y > 0 and _seen[i - _stride] == 0 and _free[i - _stride] == 1:
			_seen[i - _stride] = 1
			_from[i - _stride] = i
			queue[tail] = i - _stride
			tail += 1
		if y < _ph and _seen[i + _stride] == 0 and _free[i + _stride] == 1:
			_seen[i + _stride] = 1
			_from[i + _stride] = i
			queue[tail] = i + _stride
			tail += 1

# --------------------------------------------------------------- the targets
func _stand_on(d: Dictionary) -> Vector2:
	return Vector2(float(d["px"]), float(d["py"])) + SPAWN_OFFSET

func _return_to(d: Dictionary) -> Vector2:
	return Vector2(float(d["px"]), float(d["py"])) + RETURN_OFFSET

## The rect overworld.gd tests the player against to offer "PRESS JUMP".
func _prompt_rect(d: Dictionary) -> Rect2:
	return Rect2(Vector2(float(d["px"]), float(d["py"])), HubDoor.SIZE).grow(DOOR_GROW)

func _label(d: Dictionary) -> String:
	return String(d.get("level", "?"))

# -------------------------------------------------------------------- checks
func test_the_map_and_the_spawn_load() -> void:
	ok(def.ok(), "%s: %s" % [_hub_id(), ", ".join(def.errors)])
	gt(float(doors.size()), 0.0, "the hub needs gateways")
	ok(_is_free(def.spawn + SPAWN_OFFSET), "the spawn is inside a wall")

func test_the_flood_actually_covers_ground() -> void:
	var n := 0
	for b in _seen:
		n += b
	gt(float(n), 10000.0, "the flood reached %d positions — it did not run" % n)

func test_every_gateway_can_be_walked_to_from_the_spawn() -> void:
	for d: Dictionary in doors:
		ok(_reached(_stand_on(d)),
			"'%s' at tile (%d,%d): nothing you can walk to from the spawn puts "
			% [_label(d), int(d["x"]), int(d["y"])]
			+ "the player on the gateway")

func test_every_gateway_returns_you_somewhere_you_can_stand() -> void:
	# overworld.gd drops you one tile below the gateway when you come back out
	# of a level. If that tile is solid you return inside a wall.
	for d: Dictionary in doors:
		ok(_reached(_return_to(d)),
			"'%s': the tile the game returns you to, (%d,%d), is not walkable"
			% [_label(d), int(d["x"]), int(d["y"]) + 1])

func test_every_gateway_can_be_stood_close_enough_to_open() -> void:
	# Reaching the tile is the mechanism. Lighting the prompt is the outcome.
	for d: Dictionary in doors:
		var r := _prompt_rect(d)
		var opens := false
		var y := maxi(0, int(r.position.y - BOX.y))
		while y <= int(r.end.y) and not opens:
			var x := maxi(0, int(r.position.x - BOX.x))
			while x <= int(r.end.x):
				var p := Vector2(x, y)
				if _reached(p) and r.intersects(Rect2(p, BOX)):
					opens = true
					break
				x += 1
			y += 1
		ok(opens, "'%s': no position you can walk to lights its prompt" % _label(d))

## Negative control. Wall the gateway in and the flood has to notice — if this
## passes while the checks above also pass, they are checking something real.
func test_a_walled_in_gateway_is_reported() -> void:
	var d: Dictionary = doors[0]
	var tx := int(d["x"])
	var ty := int(d["y"])
	var world := def.world
	var was: Array[int] = []
	var ring: Array[Vector2i] = []
	for dy in range(-1, 3):
		for dx in range(-1, 2):
			if dx == 0 and (dy == 0 or dy == 1):
				continue     # leave the gateway tile and its return tile open
			ring.append(Vector2i(tx + dx, ty + dy))
	for t in ring:
		was.append(world.get_fg(t.x, t.y))
		world.set_fg(t.x, t.y, 3)        # stone: solid in every switch state
	_free = _free_mask(world)
	_flood(def.spawn + SPAWN_OFFSET)
	var still := _reached(_stand_on(d))
	for i in ring.size():
		world.set_fg(ring[i].x, ring[i].y, was[i])
	_free = _free_mask(world)
	_flood(def.spawn + SPAWN_OFFSET)
	not_ok(still, "sealing '%s' in did not make the flood fill fail — the "
		% _label(d) + "walkability check is not checking anything")
	ok(_reached(_stand_on(d)), "unsealing did not restore the route")

# ------------------------------------------------------------------ the walk
## Read the route back out of the flood, as a list of positions where the
## direction changes.
func _route_to(target: Vector2) -> Array[Vector2]:
	var out: Array[Vector2] = []
	var i := _index(target)
	if i < 0 or _seen[i] == 0:
		return out
	var raw := PackedInt32Array()
	while i != -1:
		raw.append(i)
		i = _from[i]
	raw.reverse()
	# The start belongs in the list: every leg the walk takes has to be one the
	# flood says is clear, including the first one.
	out.append(Vector2(raw[0] % _stride, raw[0] / _stride))
	var last_dir := Vector2i.ZERO
	for n in range(1, raw.size()):
		var a := Vector2i(raw[n - 1] % _stride, raw[n - 1] / _stride)
		var b := Vector2i(raw[n] % _stride, raw[n] / _stride)
		var dir := b - a
		if dir != last_dir and n > 1:
			out.append(Vector2(a))
		last_dir = dir
	out.append(target)
	return out

## Collapse the corners into as few legs as possible: straight runs through
## open ground become one waypoint instead of a hundred. The start stays at the
## head of the list, so every consecutive pair is one axis-aligned leg.
func _simplify(points: Array[Vector2]) -> Array[Vector2]:
	var out: Array[Vector2] = []
	if points.is_empty():
		return out
	out.append(points[0])
	var i := 0
	while i < points.size() - 1:
		var j := points.size() - 1
		var corner := Vector2.ZERO
		while j > i:
			var c := _clear_corner(points[i], points[j])
			if c.x > -0.5:
				corner = c
				break
			j -= 1
		if j <= i:
			out.append(points[i + 1])
			i += 1
			continue
		if corner != points[i] and corner != points[j]:
			out.append(corner)
		out.append(points[j])
		i = j
	return out

## Is there an L-shaped run of free positions from a to b? Returns the corner,
## or (-1,-1) if neither leg order is clear.
func _clear_corner(a: Vector2, b: Vector2) -> Vector2:
	for c in [Vector2(b.x, a.y), Vector2(a.x, b.y)]:
		if _leg_free(a, c) and _leg_free(c, b):
			return c
	return Vector2(-1, -1)

func _leg_free(a: Vector2, b: Vector2) -> bool:
	if a.x != b.x and a.y != b.y:
		return false
	var steps := int(maxf(absf(b.x - a.x), absf(b.y - a.y)))
	var step := Vector2(signf(b.x - a.x), signf(b.y - a.y))
	var p := a
	for _n in steps:
		p += step
		if not _is_free(p):
			return false
	return true

## Slide each leg sideways to the middle of the free space it runs through.
##
## The flood fill hugs whichever wall its neighbour order happened to reach
## first, and a route along the very last free pixel is one the real character
## cannot hold: it accelerates, and it coasts a couple of pixels past where it
## meant to stop. A player walks down the middle of a path. Bounded by SLIDE,
## and every shift is thrown away unless the whole route is still clear — so
## this can make the walk easier but can never invent a way through.
func _relax(route: Array[Vector2]) -> Array[Vector2]:
	var out: Array[Vector2] = route.duplicate()
	# The first waypoint is the spawn and the last is the gateway. Neither moves.
	for n in range(1, out.size() - 2):
		var a: Vector2 = out[n]
		var b: Vector2 = out[n + 1]
		var vertical := is_equal_approx(a.x, b.x)
		if not vertical and not is_equal_approx(a.y, b.y):
			continue
		var perp := Vector2(1, 0) if vertical else Vector2(0, 1)
		var lo := 0
		while lo < SLIDE and _leg_clear(a - perp * float(lo + 1), b - perp * float(lo + 1)):
			lo += 1
		var hi := 0
		while hi < SLIDE and _leg_clear(a + perp * float(hi + 1), b + perp * float(hi + 1)):
			hi += 1
		var shift: float = floor(float(hi - lo) * 0.5)
		if is_zero_approx(shift):
			continue
		out[n] = a + perp * shift
		out[n + 1] = b + perp * shift
		if not _route_clear(out):
			out[n] = a
			out[n + 1] = b
	return out

func _leg_clear(a: Vector2, b: Vector2) -> bool:
	return _is_free(a) and _leg_free(a, b)

func _route_clear(route: Array[Vector2]) -> bool:
	for n in range(1, route.size()):
		if _clear_corner(route[n - 1], route[n]).x < -0.5:
			return false
	return true

## One frame of HubPlayer._physics_process, minus the parts that need a scene
## tree: the same acceleration, the same friction, the same axis-separated
## TileCollision sweep in the same order.
func _step(pos: Vector2, vel: Vector2, want: Vector2, world: TileWorld) -> Array:
	if want.length() > 1.0:
		want = want.normalized()
	if want.length() > 0.01:
		vel = vel.move_toward(want * HubPlayer.SPEED, HubPlayer.ACCEL * FRAME)
	else:
		vel = vel.move_toward(Vector2.ZERO, HubPlayer.FRICTION * FRAME)
	var r := Rect2(pos, BOX)
	r = TileCollision.move_x(world, r, vel.x * FRAME).rect
	r = TileCollision.move_y(world, r, vel.y * FRAME).rect
	return [r.position, vel]

## Walk from the spawn to `target` along `route`, holding directions like a
## player would. Reports where it got to, so a failure names the leg it died on.
func _walk(route: Array[Vector2], target: Vector2, world: TileWorld) -> Dictionary:
	var pos: Vector2 = route[0]
	var vel := Vector2.ZERO
	var closest := pos.distance_to(target)
	var n := 1
	var frames := 0
	while n < route.size() and frames < WALK_FRAME_BUDGET:
		var wp: Vector2 = route[n]
		var d := wp - pos
		if absf(d.x) <= ARRIVE and absf(d.y) <= ARRIVE:
			n += 1
			continue
		# What a player holds on the d-pad: whole directions, never a fraction.
		var want := Vector2(
			0.0 if absf(d.x) <= ARRIVE else signf(d.x),
			0.0 if absf(d.y) <= ARRIVE else signf(d.y))
		var out := _step(pos, vel, want, world)
		pos = out[0]
		vel = out[1]
		closest = minf(closest, pos.distance_to(target))
		frames += 1
	return {"closest": closest, "pos": pos, "leg": n, "legs": route.size(), "frames": frames}

func test_a_walk_arrives_at_every_gateway() -> void:
	for d: Dictionary in doors:
		var target := _stand_on(d)
		var route := _relax(_simplify(_route_to(target)))
		gt(float(route.size()), 1.0, "'%s': the flood found no route" % _label(d))
		if route.size() < 2:
			continue
		var w := _walk(route, target, def.world)
		# Arriving means the prompt would light, not landing on a pixel.
		ok(float(w["closest"]) <= DOOR_GROW + BOX.x,
			"'%s': a walk from the spawn stalled on leg %d of %d at %s, %.1f px "
			% [_label(d), int(w["leg"]), int(w["legs"]), str(w["pos"]), float(w["closest"])]
			+ "from the gateway, after %d frames (route %s)" % [int(w["frames"]), str(route)])

## Everything above trusts four numbers that live in src/hub/. If one of them
## moves, this proof is measuring a player who no longer exists — so fail here,
## loudly, rather than keep quoting a stale result.
func test_the_numbers_this_file_trusts_are_still_the_ones_the_game_uses() -> void:
	var hp := FileAccess.get_file_as_string("res://src/hub/hub_player.gd")
	var ow := FileAccess.get_file_as_string("res://src/hub/overworld.gd")
	gt(float(hp.length()), 0.0, "src/hub/hub_player.gd is unreadable")
	gt(float(ow.length()), 0.0, "src/hub/overworld.gd is unreadable")
	ok(hp.contains("box = Vector2(10, 10)"),
		"HubPlayer's box is no longer 10x10 — this file's free space is wrong")
	ok(ow.contains("player.pos = p + Vector2(3, 5)"),
		"the spawn offset moved — this file floods from the wrong place")
	ok(ow.contains("player.pos = d.pos + Vector2(3, 20)"),
		"the return offset moved — the 'you come back inside a wall' check is wrong")
	ok(ow.contains("grow(6.0)"),
		"the gateway's reach changed — the prompt check is wrong")
	eq(HubDoor.SIZE, Vector2(16, 16), "a gateway is no longer one tile")
	near(HubPlayer.SPEED * FRAME, 1.2333, 0.01,
		"walk speed changed; a one-pixel flood step is no longer conservative")
