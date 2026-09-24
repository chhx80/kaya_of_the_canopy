class_name ProverSim
extends RefCounted
## The prover's simulation: the *real* Actor, the *real* FormBase subclass and
## the *real* TileCollision, stepped one 60 Hz tick at a time.
##
## Nothing in here models movement. Every pixel comes from `form.update()` and
## `actor.step_motion()`, which is the whole point of ADR 005 — six shipped
## defects came from a hand-written envelope being more generous than the game.
##
## What this file *does* own is the part of the level that lives in nodes rather
## than in the movement code: transform pads, keys, doors and switches. Those are
## re-implemented here against the same AABBs and the same rules the trigger
## scripts use, because the trigger scripts are `Node2D`s driven by
## `_physics_process` and the search needs to step time by hand. Every constant
## below is read back from the trigger script that owns it, so the two cannot
## drift apart silently.

const DT := 1.0 / 60.0

## Entity kinds the prover understands. Anything else is scenery to it.
enum Kind { PAD, KEY, DOOR, SWITCH, EXIT, MARKER, SPAWN }

var world: TileWorld = null
var actor: Actor = null
var form: FormBase = null
var form_id := ""
var spawn_pos := Vector2.ZERO

## Parsed entity records — see `_record()`.
var ents: Array = []
## Indices into `ents`, grouped so the per-frame contact pass does not rescan.
var pads: PackedInt32Array = PackedInt32Array()
var keys: PackedInt32Array = PackedInt32Array()
var doors: PackedInt32Array = PackedInt32Array()
var switches: PackedInt32Array = PackedInt32Array()

## Mutable run state.
## Keys are *counts* in Game, not flags — a level may hand out two yellows.
var key_counts := 0        ## three 8-bit counts, one per KEY_COLORS entry
var taken := 0              ## bitmask over `keys` (which pickups are gone)
var opened := 0             ## bitmask over `doors`
var switch_bits := 0        ## bit 0 = group 1, bit 1 = group 2
var cooldowns: PackedFloat32Array = PackedFloat32Array()
## ents index -> slot in `cooldowns`; only pads and switches have one.
var _cool_slot: Dictionary = {}

# Flattened trigger geometry — see _flatten_triggers(). Four floats per rect.
var _trigger_count := 0
var _pad_box: PackedFloat32Array = PackedFloat32Array()
var _pad_form: PackedStringArray = PackedStringArray()
var _pad_slot: PackedInt32Array = PackedInt32Array()
var _key_box: PackedFloat32Array = PackedFloat32Array()
var _key_color: PackedInt32Array = PackedInt32Array()
var _door_box: PackedFloat32Array = PackedFloat32Array()
var _door_color: PackedInt32Array = PackedInt32Array()
var _switch_box: PackedFloat32Array = PackedFloat32Array()
var _switch_group: PackedInt32Array = PackedInt32Array()
var _switch_slot: PackedInt32Array = PackedInt32Array()

## Prover policy, not game rules — see prove.gd for why each exists.
var allow_hazard := false
var drown_fish := true

const KEY_COLORS := ["yellow", "red", "cyan"]

## Key counts live in one int, eight bits each — snapshots are taken eighteen
## times per expansion and an allocation there is not free.
static func _key_count(packed: int, ci: int) -> int:
	return (packed >> (ci * 8)) & 255

static func _add_key(packed: int, ci: int) -> int:
	return packed + (1 << (ci * 8))

static func _use_key(packed: int, ci: int) -> int:
	return packed - (1 << (ci * 8))

const FORM_IDS := ["human", "frog", "bird", "fish"]

# Form instances are recycled rather than reallocated: a hop search restores
# thousands of states a second and `FormBase.load_form()` touches the disk.
var _form_pool: Dictionary = {}       ## form_id -> FormBase
var _form_props: Dictionary = {}      ## form_id -> Array[StringName]
var _form_baseline: Dictionary = {}   ## form_id -> Array (values straight after configure)
var _form_dirty: Dictionary = {}      ## form_id -> Array of prop indices currently off-baseline


# ---------------------------------------------------------------- construction

func setup(def: LevelLoader.LevelDef) -> void:
	world = def.world
	spawn_pos = def.spawn
	_build_entities(def)
	actor = Actor.new()
	actor.world = world
	_prime_forms()
	reset()


func _prime_forms() -> void:
	for id: String in FORM_IDS:
		var f := FormBase.load_form(id)
		if f == null:
			push_error("prover: cannot load form '%s'" % id)
			continue
		var names: Array[StringName] = []
		for p: Dictionary in f.get_property_list():
			if int(p.get("usage", 0)) & PROPERTY_USAGE_SCRIPT_VARIABLE:
				names.append(StringName(p["name"]))
		var base: Array = []
		for n: StringName in names:
			base.append(f.get(n))
		_form_pool[id] = f
		_form_props[id] = names
		_form_baseline[id] = base
		_form_dirty[id] = []


## Entity records carry the *game's* AABB for each trigger, not a tile guess.
## `level.gd` places them and the trigger scripts size them; both are mirrored
## here, offsets included, so a waypoint is "reached" under exactly the
## predicate that fires it in play.
func _build_entities(def: LevelLoader.LevelDef) -> void:
	for e: Dictionary in def.entities:
		var type := String(e.get("type", ""))
		var p := Vector2(float(e.get("px", 0.0)), float(e.get("py", 0.0)))
		if type.begins_with("pad_"):
			# level.gd: pad.setup(p + Vector2(0, 8), ...); TransformPad.SIZE = (16, 8)
			pads.append(ents.size())
			ents.append(_record(type, Kind.PAD, Rect2(p + Vector2(0, 8), TransformPad.SIZE), 3.0,
				{"form": type.substr(4)}))
		elif type.begins_with("key_"):
			# level.gd: pu.setup(type, p + Vector2(2, 2)); Pickup.SIZE = (12, 12)
			keys.append(ents.size())
			ents.append(_record(type, Kind.KEY, Rect2(p + Vector2(2, 2), Pickup.SIZE), 0.0,
				{"color": type.substr(4)}))
		elif type.begins_with("door_"):
			# Door.aabb() anchors on the *bottom* tile and extends upward.
			var dr := Rect2(p - Vector2(0, 16.0 * (Door.HEIGHT_TILES - 1)), Door.SIZE)
			var tiles: Array = []
			var bx := int(p.x / TileData4.TILE_SIZE)
			var by := int(p.y / TileData4.TILE_SIZE)
			for i in Door.HEIGHT_TILES:
				tiles.append(Vector2i(bx, by - i))
			doors.append(ents.size())
			ents.append(_record(type, Kind.DOOR, dr, 2.0,
				{"color": type.substr(5), "tiles": tiles}))
		elif type == "switch_a" or type == "switch_b":
			# level.gd: sw.setup(p + Vector2(1, 6), ...); SwitchTrigger.SIZE = (14, 10)
			switches.append(ents.size())
			ents.append(_record(type, Kind.SWITCH, Rect2(p + Vector2(1, 6), SwitchTrigger.SIZE), 0.0,
				{"group": 1 if type.ends_with("a") else 2,
				 "starts_on": bool(e.get("on", type.ends_with("a")))}))
		elif type == "gem" or type == "heart":
			# Not a route effect — collecting one changes nothing you can walk
			# on — but they are real, placed, named points, which makes them
			# free anchors for splitting a hop that is too coarse.
			ents.append(_record(type, Kind.MARKER, Rect2(p + Vector2(2, 2), Pickup.SIZE), 0.0, {}))
		elif type == "exit" or type == "boss_exit":
			ents.append(_record(type, Kind.EXIT, Rect2(p, LevelExit.SIZE), 0.0, {}))
		elif type == "marker":
			ents.append(_record(String(e.get("name", "marker")), Kind.MARKER,
				Rect2(p, Vector2(TileData4.TILE_SIZE, TileData4.TILE_SIZE)), 0.0, {}))
	# Only pads and switches have a cooldown, and a snapshot duplicates this
	# array eighteen times per expansion — so it is sized by those, not by the
	# whole entity list.
	for i: int in pads:
		_cool_slot[i] = _cool_slot.size()
	for i: int in switches:
		_cool_slot[i] = _cool_slot.size()
	cooldowns.resize(_cool_slot.size())
	_flatten_triggers()


## Copy every trigger AABB into flat float arrays. `_touch_triggers()` runs a
## few million times per level; a Dictionary lookup per entity per frame is the
## difference between a prover you run and one you avoid running.
func _flatten_triggers() -> void:
	_trigger_count = pads.size() + keys.size() + doors.size() + switches.size()
	_pad_box.resize(pads.size() * 4)
	_pad_form.resize(pads.size())
	_pad_slot.resize(pads.size())
	for n in pads.size():
		var e: Dictionary = ents[pads[n]]
		_store_box(_pad_box, n * 4, (e["rect"] as Rect2).grow(float(e["grow"])))
		_pad_form[n] = String(e["form"])
		_pad_slot[n] = _cool_slot[pads[n]]
	_key_box.resize(keys.size() * 4)
	_key_color.resize(keys.size())
	for n in keys.size():
		var e: Dictionary = ents[keys[n]]
		_store_box(_key_box, n * 4, e["rect"] as Rect2)
		_key_color[n] = KEY_COLORS.find(String(e["color"]))
	_door_box.resize(doors.size() * 4)
	_door_color.resize(doors.size())
	for n in doors.size():
		var e: Dictionary = ents[doors[n]]
		_store_box(_door_box, n * 4, (e["rect"] as Rect2).grow(float(e["grow"])))
		_door_color[n] = KEY_COLORS.find(String(e["color"]))
	_switch_box.resize(switches.size() * 4)
	_switch_group.resize(switches.size())
	_switch_slot.resize(switches.size())
	for n in switches.size():
		var e: Dictionary = ents[switches[n]]
		_store_box(_switch_box, n * 4, e["rect"] as Rect2)
		_switch_group[n] = int(e["group"])
		_switch_slot[n] = _cool_slot[switches[n]]


static func _store_box(a: PackedFloat32Array, o: int, r: Rect2) -> void:
	a[o] = r.position.x
	a[o + 1] = r.position.y
	a[o + 2] = r.size.x
	a[o + 3] = r.size.y


func _record(type: String, kind: Kind, rect: Rect2, grow: float, extra: Dictionary) -> Dictionary:
	var d := {"type": type, "kind": kind, "rect": rect, "grow": grow}
	d.merge(extra)
	return d


## Markers declared outside the entity list (the DSL's `g.mark`).
func add_marker(name: String, tx: int, ty: int) -> void:
	ents.append(_record(name, Kind.MARKER,
		Rect2(Vector2(tx * TileData4.TILE_SIZE, ty * TileData4.TILE_SIZE),
			Vector2(TileData4.TILE_SIZE, TileData4.TILE_SIZE)), 0.0, {}))


# ---------------------------------------------------------------- run state

## Back to the state the level is in the instant it finishes loading.
func reset() -> void:
	key_counts = 0
	taken = 0
	opened = 0
	world.reset_broken()
	# TileWorld's own defaults, then whatever each switch declares — the same
	# order SwitchTrigger._ready() applies them in.
	world.set_switch(1, true)
	world.set_switch(2, false)
	switch_bits = 1
	for i: int in switches:
		var e: Dictionary = ents[i]
		_set_switch(int(e["group"]), bool(e["starts_on"]))
	# Door._ready() makes a closed door solid across its whole height.
	for i: int in doors:
		for t: Vector2i in (ents[i]["tiles"] as Array):
			world.set_fg(t.x, t.y, _DOOR_TILE)
	cooldowns.fill(0.0)
	set_form("human")
	seed_at_spawn()

## Door._door_tile_id(): metal, solid, never used for scenery.
const _DOOR_TILE := 25


func seed_at_spawn() -> void:
	# level.gd: player.pos = Vector2(p.x + 3.0, p.y + 16.0 - player.box.y)
	actor.pos = Vector2(spawn_pos.x + 3.0, spawn_pos.y + 16.0 - actor.box.y)
	actor.vel = Vector2.ZERO
	actor.on_floor = false
	actor.was_on_floor = false
	actor.on_ceiling = false
	actor.against_wall = 0
	actor.facing = 1
	actor.drop_through = false


## Mirrors Player.set_form(): the feet stay planted when the hitbox height changes.
func set_form(new_id: String) -> void:
	var f: FormBase = _form_pool.get(new_id)
	if f == null:
		push_error("prover: unknown form '%s'" % new_id)
		return
	_reset_form(new_id)
	var old_bottom := actor.pos.y + actor.box.y
	var old_cx := actor.pos.x + actor.box.x * 0.5
	form = f
	form_id = new_id
	var hb: Dictionary = f.hitbox()
	actor.box = Vector2(float(hb.get("w", 10)), float(hb.get("h", 22)))
	actor.pos = Vector2(old_cx - actor.box.x * 0.5, old_bottom - actor.box.y)


func _set_switch(group: int, on: bool) -> void:
	world.set_switch(group, on)
	var bit := 1 << (group - 1)
	switch_bits = (switch_bits | bit) if on else (switch_bits & ~bit)


# ---------------------------------------------------------------- the tick

## One physics tick, exactly as Player._physics_process orders it: the form
## moves the actor, then the triggers it is now touching fire.
func step(input: InputState) -> void:
	form.update(actor, input, DT)
	actor.step_motion(DT)
	_touch_triggers()


## Runs once per simulated frame — several million times per level — so the
## hot path reads flat float arrays built in `_flatten_triggers()` rather than
## indexing a Dictionary per entity per frame. The AABBs are still the ones the
## trigger scripts use; only the storage changed.
func _touch_triggers() -> void:
	if _trigger_count == 0:
		return
	var bx := actor.pos.x
	var by := actor.pos.y
	var bw := actor.box.x
	var bh := actor.box.y
	for n in pads.size():
		var slot: int = _pad_slot[n]
		var cd: float = cooldowns[slot] - DT
		cooldowns[slot] = cd if cd > 0.0 else 0.0
		if cd > 0.0 or _pad_form[n] == form_id:
			continue
		var o := n * 4
		if _overlap(_pad_box, o, bx, by, bw, bh):
			cooldowns[slot] = 0.8       # TransformPad._physics_process
			set_form(_pad_form[n])
			bx = actor.pos.x
			by = actor.pos.y
			bw = actor.box.x
			bh = actor.box.y
	for n in keys.size():
		if taken & (1 << n):
			continue
		if _overlap(_key_box, n * 4, bx, by, bw, bh):
			taken |= 1 << n
			key_counts = _add_key(key_counts, _key_color[n])   # Game.add_key()
	for n in doors.size():
		if opened & (1 << n):
			continue
		if not _overlap(_door_box, n * 4, bx, by, bw, bh):
			continue
		var ci := _door_color[n]
		if _key_count(key_counts, ci) <= 0:
			continue                      # Game.use_key() would refuse
		key_counts = _use_key(key_counts, ci)
		opened |= 1 << n
		for t: Vector2i in (ents[doors[n]]["tiles"] as Array):
			world.set_fg(t.x, t.y, 0)     # Door._open()
	for n in switches.size():
		var slot: int = _switch_slot[n]
		var cd: float = cooldowns[slot] - DT
		cooldowns[slot] = cd if cd > 0.0 else 0.0
		if cd > 0.0:
			continue
		if _overlap(_switch_box, n * 4, bx, by, bw, bh):
			cooldowns[slot] = 0.45        # SwitchTrigger.toggle()
			var g := _switch_group[n]
			_set_switch(g, not bool(world.switch_states.get(g, false)))


## Rect2.intersects() on a rect stored as four consecutive floats.
static func _overlap(r: PackedFloat32Array, o: int, bx: float, by: float,
		bw: float, bh: float) -> bool:
	return r[o] < bx + bw and r[o] + r[o + 2] > bx \
		and r[o + 1] < by + bh and r[o + 1] + r[o + 3] > by


## Why a state is not worth searching from. Empty string means it is fine.
##
## Every rule here *removes* states, so the prover can only ever under-report
## what is reachable. That direction is deliberate: a gate that fails loudly on
## a route a human could scrape through costs an afternoon, and a gate that
## passes a level nobody can finish costs a shipped defect.
func rejection() -> String:
	if actor.fell_out_of_world():
		return "fell out of the world"
	if not allow_hazard and actor.touching_hazard():
		return "touching a hazard"
	if drown_fish and form_id == "fish" and float(form.get("air_left")) <= 0.0:
		# form_fish.gd reverts a beached fish to human, but only for a Player.
		# The prover refuses the state instead of silently continuing as a form
		# the route did not declare.
		return "fish out of air"
	return ""


# ---------------------------------------------------------------- snapshots

## A complete, restorable state. Compact on purpose: a hop search holds hundreds
## of thousands of these.
func snapshot() -> Array:
	return [
		actor.pos.x, actor.pos.y, actor.vel.x, actor.vel.y,
		_actor_bits(), FORM_IDS.find(form_id), _form_diff(),
		key_counts, taken, opened, switch_bits, cooldowns.duplicate(),
	]


func restore(s: Array) -> void:
	var fid: String = FORM_IDS[int(s[5])]
	if form_id != fid:
		form = _form_pool[fid]
		form_id = fid
		var hb: Dictionary = form.hitbox()
		actor.box = Vector2(float(hb.get("w", 10)), float(hb.get("h", 22)))
	_reset_form(fid)
	_apply_form_diff(fid, s[6])
	actor.pos = Vector2(s[0], s[1])
	actor.vel = Vector2(s[2], s[3])
	_set_actor_bits(int(s[4]))
	key_counts = int(s[7])
	taken = int(s[8])
	var was_opened := opened
	opened = int(s[9])
	cooldowns = (s[11] as PackedFloat32Array).duplicate()
	var bits := int(s[10])
	if bits != switch_bits:
		_set_switch(1, bits & 1 != 0)
		_set_switch(2, bits & 2 != 0)
	switch_bits = bits
	if was_opened != opened:
		for n in doors.size():
			if (was_opened ^ opened) & (1 << n) == 0:
				continue
			var want := opened & (1 << n) != 0
			for t: Vector2i in (ents[doors[n]]["tiles"] as Array):
				world.set_fg(t.x, t.y, 0 if want else _DOOR_TILE)


func _actor_bits() -> int:
	var b := 0
	if actor.on_floor: b |= 1
	if actor.was_on_floor: b |= 2
	if actor.on_ceiling: b |= 4
	if actor.drop_through: b |= 8
	if actor.facing > 0: b |= 16
	b |= (actor.against_wall + 1) << 5
	return b


func _set_actor_bits(b: int) -> void:
	actor.on_floor = b & 1 != 0
	actor.was_on_floor = b & 2 != 0
	actor.on_ceiling = b & 4 != 0
	actor.drop_through = b & 8 != 0
	actor.facing = 1 if b & 16 else -1
	actor.against_wall = ((b >> 5) & 3) - 1


## Only the form variables that have moved off their post-`configure()` value.
## Derived by reflection rather than by listing them, so a form that gains a new
## piece of per-tick state is captured without anyone remembering to come here.
func _form_diff() -> Array:
	var names: Array[StringName] = _form_props[form_id]
	var base: Array = _form_baseline[form_id]
	var out: Array = []
	for i in names.size():
		var v: Variant = form.get(names[i])
		# `is_same` compares values for scalars and *identity* for Dictionaries.
		# `==` would deep-compare `cfg` — every tunable and every animation
		# table — on each of the eighteen successors of every expansion.
		if not is_same(v, base[i]):
			out.append(i)
			out.append(v)
	return out


## Put every form property back to its baseline.
##
## This used to reset only the properties `_apply_form_diff` had touched, on the
## theory that nothing else could have changed them. But the FORM changes them:
## `form.update()` writes `coyote`, `buffer`, `_drop_timer`, `_land_t`, `_air_vy`
## every tick, and nothing marks those dirty. So a restore left the last
## simulated timer values in place, and the search explored from states carrying
## phantom coyote time -- finding jumps that continuous play cannot make.
##
## That is why the emitted tape did not reproduce its own proof. It is the
## quietest possible version of this project's recurring bug: the mechanism
## (restore was called) was right, the outcome (the state actually came back)
## was not.
func _reset_form(fid: String) -> void:
	var f: FormBase = _form_pool[fid]
	var names: Array[StringName] = _form_props[fid]
	var base: Array = _form_baseline[fid]
	for i in names.size():
		f.set(names[i], base[i])
	(_form_dirty[fid] as Array).clear()


func _apply_form_diff(fid: String, diff: Array) -> void:
	var f: FormBase = _form_pool[fid]
	var names: Array[StringName] = _form_props[fid]
	var dirty: Array = _form_dirty[fid]
	var i := 0
	while i < diff.size():
		var idx := int(diff[i])
		f.set(names[idx], diff[i + 1])
		dirty.append(idx)
		i += 2


# ---------------------------------------------------------------- waypoints

## Resolve a route waypoint id to the entity indices it may mean.
## `spawn` is the literal start; `type#n` picks one of several of a type.
func waypoint_indices(id: String) -> PackedInt32Array:
	var out := PackedInt32Array()
	if id == "spawn":
		return out
	var want := id
	var pick := -1
	if "#" in id:
		var parts := id.split("#")
		want = parts[0]
		pick = int(parts[1])
	var seen := 0
	for i in ents.size():
		if String(ents[i]["type"]) != want:
			continue
		if pick < 0 or seen == pick:
			out.append(i)
		seen += 1
	return out


## The rectangle a waypoint is "reached" by touching, already grown by whatever
## slack the real trigger allows.
func waypoint_rect(i: int) -> Rect2:
	var e: Dictionary = ents[i]
	return (e["rect"] as Rect2).grow(float(e["grow"]))


func spawn_rect() -> Rect2:
	# The AABB the player occupies on frame zero, in human form.
	var hb: Dictionary = (_form_pool["human"] as FormBase).hitbox()
	var box := Vector2(float(hb.get("w", 10)), float(hb.get("h", 22)))
	return Rect2(Vector2(spawn_pos.x + 3.0, spawn_pos.y + 16.0 - box.y), box)


## The effect standing on a waypoint has, applied between hops exactly as the
## trigger would apply it in play. Returns "" or the reason it could not.
## Has this waypoint actually been USED, by the simulation itself?
##
## Overlapping a door's waypoint rect is not opening the door. The rect is the
## entity's tile grown by two pixels; the door opens in _touch_triggers() only
## when the body overlaps the door's own box with a key in hand. A hop that
## ended on the rect without firing the trigger used to be finished off by
## apply_waypoint_effect(), which opened the door OUT OF BAND -- so the next hop
## searched a world with an open doorway that its own buttons had never opened.
## Replay the tape and the door is still shut. Measured on jungle_2: the tape
## ended hop 2 four pixels short of the door and hop 3 twenty-five pixels short
## of the vine, and Kaya walked off the bottom of the world.
##
## So arrival at an entity means the entity fired. That is the outcome, not the
## mechanism, and it is the same lesson this project keeps relearning.
func waypoint_satisfied(i: int) -> bool:
	var e: Dictionary = ents[i]
	match int(e["kind"]):
		Kind.PAD:
			return form_id == String(e["form"])
		Kind.KEY:
			var kn := keys.find(i)
			return kn >= 0 and (taken & (1 << kn)) != 0
		Kind.DOOR:
			var dn := doors.find(i)
			return dn >= 0 and (opened & (1 << dn)) != 0
	return false


## True when this waypoint is one the simulation has to fire, rather than one
## the body merely has to stand on.
func waypoint_is_triggered(i: int) -> bool:
	match int((ents[i])["kind"]):
		Kind.PAD, Kind.KEY, Kind.DOOR:
			return true
	return false


func apply_waypoint_effect(i: int) -> String:
	var e: Dictionary = ents[i]
	match int(e["kind"]):
		Kind.PAD:
			if form_id != String(e["form"]):
				cooldowns[_cool_slot[i]] = 0.8
				set_form(String(e["form"]))
		Kind.KEY:
			var kn := keys.find(i)
			if kn >= 0 and taken & (1 << kn) == 0:
				taken |= 1 << kn
				key_counts = _add_key(key_counts, KEY_COLORS.find(String(e["color"])))
		Kind.DOOR:
			var dn := doors.find(i)
			if dn < 0:
				return "door is not in the level"
			if opened & (1 << dn) != 0:
				return ""
			var ci := KEY_COLORS.find(String(e["color"]))
			if _key_count(key_counts, ci) <= 0:
				return "no %s key in hand" % String(e["color"])
			key_counts = _use_key(key_counts, ci)
			opened |= 1 << dn
			for t: Vector2i in (e["tiles"] as Array):
				world.set_fg(t.x, t.y, 0)
		Kind.SWITCH:
			var g := int(e["group"])
			cooldowns[_cool_slot[i]] = 0.45
			_set_switch(g, not bool(world.switch_states.get(g, false)))
	return ""
