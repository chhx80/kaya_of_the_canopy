extends TestCase
## Structure of the 25-door overworld, staging/hub_v2.json (built by
## tools/build_hub.py).
##
## The walkability proof lives next door in tests/test_hub_walkable.gd. This
## file only checks the things a reader of the JSON could check: the shape, the
## gateway list, and the requires chain that decides what is open when.
##
## The twenty new levels do not exist yet, so nothing here asserts that a
## gateway's target file is on disk — see REPORT.md.

const TS := TileData4.TILE_SIZE

var def: LevelLoader.LevelDef = null
var doors: Array = []

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

const WORLDS := {
	"jungle": ["jungle_1", "jungle_2", "jungle_3", "jungle_4", "jungle_5"],
	"ruins": ["ruins_1", "ruins_2", "ruins_3", "ruins_4", "ruins_5"],
	"heights": ["heights_1", "heights_2", "heights_3", "heights_4", "heights_5"],
	"deeps": ["deeps_1", "deeps_2", "deeps_3", "deeps_4", "deeps_5"],
	"nest": ["nest_1", "nest_2", "nest_3", "nest_4", "nest_5"],
}
## The order the player meets the worlds. World N+1 opens on World N's last level.
const WORLD_ORDER := ["jungle", "ruins", "heights", "deeps", "nest"]

func _ids() -> Array:
	var out: Array = []
	for d: Dictionary in doors:
		out.append(String(d.get("level", "")))
	return out

func _door(level_id: String) -> Dictionary:
	for d: Dictionary in doors:
		if String(d.get("level", "")) == level_id:
			return d
	return {}

func test_the_hub_loads() -> void:
	ok(def.ok(), "%s: %s" % [_hub_id(), ", ".join(def.errors)])

func test_it_is_two_by_two_screens_of_fifty_by_thirty() -> void:
	eq(def.world.width, 50, "hub width")
	eq(def.world.height, 30, "hub height")
	eq(def.world.width / 25, 2, "two screens across")
	eq(def.world.height / 15, 2, "two screens down")

func test_it_is_top_down() -> void:
	ok(def.topdown, "the overworld has no gravity and must say so")

func test_it_has_exactly_one_spawn() -> void:
	eq(def.entities_of("player_spawn").size(), 1, "one spawn")

func test_it_holds_twenty_five_gateways() -> void:
	eq(doors.size(), 25, "the hub must hold 25 gateways")

func test_the_gateways_are_five_worlds_of_five() -> void:
	var ids := _ids()
	for world: String in WORLDS:
		var want: Array = WORLDS[world]
		for level_id: String in want:
			has(ids, level_id, "world '%s' is missing a gateway for %s" % [world, level_id])
	eq(ids.size(), 25, "no gateways beyond the five worlds")

func test_every_gateway_is_unique() -> void:
	var seen := {}
	for level_id: String in _ids():
		not_ok(seen.has(level_id), "two gateways both point at '%s'" % level_id)
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
	for level_id: String in shipped:
		var d := _door(level_id)
		not_ok(d.is_empty(), "the hub lost its '%s' gateway" % level_id)
		if d.is_empty():
			continue
		eq(String(d.get("label", "")), String(shipped[level_id]),
			"'%s' must keep its shipped label" % level_id)

func test_every_gateway_carries_a_label() -> void:
	for d: Dictionary in doors:
		gt(float(String(d.get("label", "")).length()), 0.0,
			"gateway '%s' has no label to show" % String(d.get("level", "")))

func test_exactly_one_gateway_is_open_from_a_fresh_save() -> void:
	var open: Array = []
	for d: Dictionary in doors:
		if String(d.get("requires", "")) == "":
			open.append(String(d.get("level", "")))
	eq(open, ["jungle_1"], "a fresh save must offer exactly one way in")

func test_every_prerequisite_is_itself_a_gateway_on_this_map() -> void:
	var ids := _ids()
	for d: Dictionary in doors:
		var req := String(d.get("requires", ""))
		if req == "":
			continue
		has(ids, req, "gateway '%s' requires '%s', which is not on the hub — it "
			% [String(d.get("level", "")), req]
			+ "could never unlock")

func test_the_requires_chain_never_loops() -> void:
	var req := {}
	for d: Dictionary in doors:
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
		not_ok(looped, "the requires chain from '%s' loops" % level_id)

func test_each_world_unlocks_one_level_at_a_time() -> void:
	for world: String in WORLDS:
		var chain: Array = WORLDS[world]
		for i in range(1, chain.size()):
			var d := _door(String(chain[i]))
			if d.is_empty():
				continue
			eq(String(d.get("requires", "")), String(chain[i - 1]),
				"'%s' must open on '%s'" % [chain[i], chain[i - 1]])

func test_each_world_is_gated_on_the_previous_world_being_finished() -> void:
	for i in range(1, WORLD_ORDER.size()):
		var world: String = WORLD_ORDER[i]
		var previous: String = WORLD_ORDER[i - 1]
		var first: String = WORLDS[world][0]
		var last_of_previous: String = WORLDS[previous][4]
		var d := _door(first)
		if d.is_empty():
			continue
		eq(String(d.get("requires", "")), last_of_previous,
			"world '%s' must stay shut until '%s' is cleared" % [world, last_of_previous])

## HubDoor.unlocked() treats requires_all as "every level in levels/ is done",
## which counts files, not worlds — while hub_v2.json sits next to hub.json it
## counts the hub itself. The chain above gives the same gate without that.
func test_no_gateway_uses_the_requires_all_shortcut() -> void:
	for d: Dictionary in doors:
		not_ok(bool(d.get("requires_all", false)),
			"gateway '%s' uses requires_all" % String(d.get("level", "")))

func test_no_two_gateways_share_a_tile() -> void:
	var seen := {}
	for d: Dictionary in doors:
		var t := Vector2i(int(d["x"]), int(d["y"]))
		not_ok(seen.has(t), "two gateways sit on tile %s" % str(t))
		seen[t] = true

func test_no_gateway_sits_on_the_spawn() -> void:
	var s := Vector2i(int(def.spawn.x / TS), int(def.spawn.y / TS))
	for d: Dictionary in doors:
		ne(Vector2i(int(d["x"]), int(d["y"])), s, "a gateway is on top of the spawn")

func test_every_gateway_sits_inside_the_map_with_room_below_it() -> void:
	# The game returns you one tile *below* the gateway you came from
	# (overworld.gd), so the bottom row can never hold one.
	for d: Dictionary in doors:
		var x := int(d["x"])
		var y := int(d["y"])
		ok(x >= 0 and x < def.world.width, "gateway '%s' is off the map" % String(d["level"]))
		ok(y >= 0 and y + 1 < def.world.height,
			"gateway '%s' has no tile below it to come back to" % String(d["level"]))
