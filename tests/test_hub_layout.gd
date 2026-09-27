extends TestCase
## Structure of the overworld maps: the shipped `levels/hub.json` AND the staged
## 25-door `staging/hub_v2.json` (built by tools/build_hub.py).
##
## The walkability proof lives next door in tests/test_hub_walkable.gd. This
## file only checks the things a reader of the JSON could check: the shape, the
## gateway list, and the requires chain that decides what is open when.
##
## BOTH maps, and that is the point. These two files used to test whichever hub
## was "current" -- hub_v2 while staging/ existed, levels/hub.json otherwise --
## so for a whole milestone the map the game actually loads had no structural
## coverage at all. What slipped through: M2 shipped five SUNKEN RUINS levels
## and never added their gateways to levels/hub.json, and M1's HEART OF THE
## GROVE door kept a `requires_all` that counted those unreachable levels, so
## the shipped overworld had a dead World 2 and an unopenable World 1 boss. A
## suite that only reads the staging file cannot see either.
##
## staging/hub_v2.json still carries gateways for the twenty levels of worlds 4
## and 5, which do not exist yet — so "the target file is on disk" is asserted
## for the shipped hub only.

const TS := TileData4.TILE_SIZE

## id -> where it lives. A hub that is not on disk is skipped, not failed:
## hub_v2 disappears the day it is promoted over levels/hub.json.
const HUB_PATHS := {
	"hub": "res://levels/hub.json",
	"hub_v2": "res://staging/hub_v2.json",
}
## The map the running game loads. Rules that are about shipping, not about
## being a hub, apply to this one.
const SHIPPED := "hub"

var _defs := {}          ## id -> LevelLoader.LevelDef
var _doors := {}         ## id -> Array of door dictionaries

func before_each() -> void:
	if not _defs.is_empty():
		return
	for id: String in HUB_PATHS:
		var path := String(HUB_PATHS[id])
		if not FileAccess.file_exists(path):
			continue
		var def := LevelLoader.load_path(path, id)
		_defs[id] = def
		_doors[id] = def.entities_of("hub_door") if def.ok() else []

func _ids() -> Array:
	var out: Array = _defs.keys()
	out.sort()
	return out

func _def(id: String) -> LevelLoader.LevelDef:
	return _defs[id] as LevelLoader.LevelDef

func _gateways(id: String) -> Array:
	return _doors[id] as Array

func _levels_of(id: String) -> Array:
	var out: Array = []
	for d: Dictionary in _gateways(id):
		out.append(String(d.get("level", "")))
	return out

func _door(id: String, level_id: String) -> Dictionary:
	for d: Dictionary in _gateways(id):
		if String(d.get("level", "")) == level_id:
			return d
	return {}

const WORLDS := {
	"jungle": ["jungle_1", "jungle_2", "jungle_3", "jungle_4", "jungle_5"],
	"ruins": ["ruins_1", "ruins_2", "ruins_3", "ruins_4", "ruins_5"],
	"heights": ["heights_1", "heights_2", "heights_3", "heights_4", "heights_5"],
	"deeps": ["deeps_1", "deeps_2", "deeps_3", "deeps_4", "deeps_5"],
	"nest": ["nest_1", "nest_2", "nest_3", "nest_4", "nest_5"],
}
## The order the player meets the worlds. World N+1 opens on World N's last level.
const WORLD_ORDER := ["jungle", "ruins", "heights", "deeps", "nest"]

# ------------------------------------------------------------- both hubs load
func test_both_hubs_are_on_disk() -> void:
	ok(FileAccess.file_exists(String(HUB_PATHS[SHIPPED])),
		"levels/hub.json is the map the game loads; it has to exist")
	gt(float(_defs.size()), 0.0, "no hub JSON was found at all")

func test_every_hub_loads() -> void:
	for id: String in _ids():
		ok(_def(id).ok(), "%s: %s" % [id, ", ".join(_def(id).errors)])

func test_every_hub_is_a_whole_number_of_screens() -> void:
	for id: String in _ids():
		var w := _def(id).world.width
		var h := _def(id).world.height
		gt(float(w), 0.0, "%s has width" % id)
		gt(float(h), 0.0, "%s has height" % id)
		eq(w % 25, 0, "%s is %d tiles wide, which is not whole screens" % [id, w])
		eq(h % 15, 0, "%s is %d tiles tall, which is not whole screens" % [id, h])

func test_the_staged_hub_is_two_by_two_screens_of_fifty_by_thirty() -> void:
	if not _defs.has("hub_v2"):
		return
	eq(_def("hub_v2").world.width, 50, "hub_v2 width")
	eq(_def("hub_v2").world.height, 30, "hub_v2 height")

func test_every_hub_is_top_down() -> void:
	for id: String in _ids():
		ok(_def(id).topdown, "%s: an overworld has no gravity and must say so" % id)

func test_every_hub_has_exactly_one_spawn() -> void:
	for id: String in _ids():
		eq(_def(id).entities_of("player_spawn").size(), 1, "%s: one spawn" % id)

# --------------------------------------------------------------- the gateways
func test_the_staged_hub_holds_twenty_five_gateways() -> void:
	if not _defs.has("hub_v2"):
		return
	eq(_gateways("hub_v2").size(), 25, "hub_v2 must hold 25 gateways")

## The regression guard the suite was missing. Every level on disk that is not
## the overworld itself and not the integration fixture is a level the player is
## meant to be able to start, and the only way to start one is a gateway. M2
## shipped five levels with no way in; this is the assertion that says so.
func test_the_shipped_hub_has_a_gateway_for_every_level_on_disk() -> void:
	if not _defs.has(SHIPPED):
		return
	var ids := _levels_of(SHIPPED)
	for level_id in LevelLoader.list_levels():
		if level_id == "hub" or level_id == "test_arena":
			continue
		has(ids, level_id,
			"levels/%s.json ships with no gateway on the overworld — nothing in " % level_id
			+ "the running game can reach it")

func test_every_gateway_belongs_to_a_known_world_and_no_world_is_half_present() -> void:
	for id: String in _ids():
		var ids := _levels_of(id)
		var known: Array = []
		for world: String in WORLDS:
			var want: Array = WORLDS[world]
			var present := 0
			for level_id: String in want:
				if ids.has(level_id):
					present += 1
			if present > 0:
				eq(present, want.size(),
					"%s: world '%s' has %d of its %d gateways — a world arrives whole"
						% [id, world, present, want.size()])
			for level_id: String in want:
				known.append(level_id)
		for level_id: String in ids:
			has(known, level_id, "%s: gateway '%s' is in no known world" % [id, level_id])

func test_every_gateway_is_unique() -> void:
	for id: String in _ids():
		var seen := {}
		for level_id: String in _levels_of(id):
			not_ok(seen.has(level_id), "%s: two gateways both point at '%s'" % [id, level_id])
			seen[level_id] = true

func test_the_five_jungle_gateways_keep_their_shipped_ids_and_labels() -> void:
	# levels/hub.json as shipped. Changing any of these breaks a save file.
	var shipped := {
		"jungle_1": "CANOPY TRAIL",
		"jungle_2": "ROOT HOLLOW",
		"jungle_3": "THE WATERWAY",
		"jungle_4": "SKY BRANCH",
		"jungle_5": "HEART OF THE GROVE",
	}
	for id: String in _ids():
		for level_id: String in shipped:
			var d := _door(id, level_id)
			not_ok(d.is_empty(), "%s lost its '%s' gateway" % [id, level_id])
			if d.is_empty():
				continue
			eq(String(d.get("label", "")), String(shipped[level_id]),
				"%s: '%s' must keep its shipped label" % [id, level_id])

func test_every_gateway_carries_a_label() -> void:
	for id: String in _ids():
		for d: Dictionary in _gateways(id):
			gt(float(String(d.get("label", "")).length()), 0.0,
				"%s: gateway '%s' has no label to show" % [id, String(d.get("level", ""))])

func test_every_gateway_on_the_shipped_hub_points_at_a_level_that_exists() -> void:
	# hub_v2 is exempt: it stages gateways for worlds 4 and 5, whose levels are
	# not written yet. The map the game loads gets no such licence.
	if not _defs.has(SHIPPED):
		return
	for d: Dictionary in _gateways(SHIPPED):
		var target := String(d.get("level", ""))
		ok(FileAccess.file_exists(LevelLoader.level_path(target)),
			"the overworld offers '%s', which is not a file" % target)

# ------------------------------------------------------------------ the chain
func test_exactly_one_gateway_is_open_from_a_fresh_save() -> void:
	for id: String in _ids():
		var open: Array = []
		for d: Dictionary in _gateways(id):
			if String(d.get("requires", "")) == "":
				open.append(String(d.get("level", "")))
		eq(open, ["jungle_1"], "%s: a fresh save must offer exactly one way in" % id)

func test_every_prerequisite_is_itself_a_gateway_on_the_same_map() -> void:
	for id: String in _ids():
		var ids := _levels_of(id)
		for d: Dictionary in _gateways(id):
			var req := String(d.get("requires", ""))
			if req == "":
				continue
			has(ids, req, "%s: gateway '%s' requires '%s', which is not on this map — it "
				% [id, String(d.get("level", "")), req]
				+ "could never unlock")

func test_the_requires_chain_never_loops() -> void:
	for id: String in _ids():
		var req := {}
		for d: Dictionary in _gateways(id):
			req[String(d.get("level", ""))] = String(d.get("requires", ""))
		for level_id: String in req.keys():
			var seen := {}
			var cur: String = level_id
			var looped := false
			while cur != "":
				if seen.has(cur):
					looped = true
					break
				seen[cur] = true
				cur = String(req.get(cur, ""))
			not_ok(looped, "%s: the requires chain from '%s' loops" % [id, level_id])

func test_each_world_unlocks_one_level_at_a_time() -> void:
	for id: String in _ids():
		for world: String in WORLDS:
			var chain: Array = WORLDS[world]
			for i in range(1, chain.size()):
				var d := _door(id, String(chain[i]))
				if d.is_empty():
					continue
				eq(String(d.get("requires", "")), String(chain[i - 1]),
					"%s: '%s' must open on '%s'" % [id, chain[i], chain[i - 1]])

func test_each_world_is_gated_on_the_previous_world_being_finished() -> void:
	for id: String in _ids():
		for i in range(1, WORLD_ORDER.size()):
			var world: String = WORLD_ORDER[i]
			var previous: String = WORLD_ORDER[i - 1]
			var first: String = WORLDS[world][0]
			var last_of_previous: String = WORLDS[previous][4]
			var d := _door(id, first)
			if d.is_empty():
				continue
			eq(String(d.get("requires", "")), last_of_previous,
				"%s: world '%s' must stay shut until '%s' is cleared"
					% [id, world, last_of_previous])

## HubDoor.unlocked() treats requires_all as "every level in levels/ is done",
## which counts FILES, not worlds. levels/hub.json shipped a requires_all on
## HEART OF THE GROVE, so the day World 2's five levels landed on disk the World
## 1 boss became unopenable: the door asked for flags no gateway could set. The
## explicit chain gives the same gate without that.
func test_no_gateway_uses_the_requires_all_shortcut() -> void:
	for id: String in _ids():
		for d: Dictionary in _gateways(id):
			not_ok(bool(d.get("requires_all", false)),
				"%s: gateway '%s' uses requires_all" % [id, String(d.get("level", ""))])

## The outcome behind the rule above: with the whole chain walked, every gateway
## must actually come open. Replays the save the player would build, one level
## at a time, and insists nothing is left grey at the end.
func test_walking_the_whole_chain_opens_every_gateway() -> void:
	for id: String in _ids():
		var req := {}
		for d: Dictionary in _gateways(id):
			req[String(d.get("level", ""))] = String(d.get("requires", ""))
		var cleared := {}
		var opened: Array = []
		var guard := 0
		while opened.size() < req.size() and guard < 100:
			guard += 1
			var progressed := false
			for level_id: String in req.keys():
				if cleared.has(level_id):
					continue
				var need := String(req[level_id])
				if need == "" or cleared.has(need):
					cleared[level_id] = true
					opened.append(level_id)
					progressed = true
			if not progressed:
				break
		eq(opened.size(), req.size(),
			"%s: %d of %d gateways can be opened by playing; the rest are walled off"
				% [id, opened.size(), req.size()])

# ------------------------------------------------------------------ placement
func test_no_two_gateways_share_a_tile() -> void:
	for id: String in _ids():
		var seen := {}
		for d: Dictionary in _gateways(id):
			var t := Vector2i(int(d["x"]), int(d["y"]))
			not_ok(seen.has(t), "%s: two gateways sit on tile %s" % [id, str(t)])
			seen[t] = true

func test_no_gateway_sits_on_the_spawn() -> void:
	for id: String in _ids():
		var s := Vector2i(int(_def(id).spawn.x / TS), int(_def(id).spawn.y / TS))
		for d: Dictionary in _gateways(id):
			ne(Vector2i(int(d["x"]), int(d["y"])), s,
				"%s: a gateway is on top of the spawn" % id)

func test_every_gateway_sits_inside_the_map_with_room_below_it() -> void:
	# The game returns you one tile *below* the gateway you came from
	# (overworld.gd), so the bottom row can never hold one.
	for id: String in _ids():
		var world := _def(id).world
		for d: Dictionary in _gateways(id):
			var x := int(d["x"])
			var y := int(d["y"])
			ok(x >= 0 and x < world.width,
				"%s: gateway '%s' is off the map" % [id, String(d["level"])])
			ok(y >= 0 and y + 1 < world.height,
				"%s: gateway '%s' has no tile below it to come back to"
					% [id, String(d["level"])])
