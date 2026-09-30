extends TestCase
## Structure of THE CANOPY, `levels/hub.json` — the game's one and only
## overworld, built by tools/build_hub.py.
##
## The walkability proof lives next door in tests/test_hub_walkable.gd. This
## file only checks the things a reader of the JSON could check: the shape, the
## gateway list, the labels, and the requires chain that decides what is open
## when.
##
## ONE map, and that is the point. For three milestones there were two: the
## shipped 20-door `levels/hub.json` and the staged 25-door
## `staging/hub_v2.json`, and this file tested both because before that it
## tested whichever was "current" -- and so for a whole milestone the map the
## game actually loads had no structural coverage at all. What slipped through:
## M2 shipped five SUNKEN RUINS levels and never added their gateways to
## levels/hub.json, and M1's HEART OF THE GROVE door kept a `requires_all` that
## counted those unreachable levels, so the shipped overworld had a dead World 2
## and an unopenable World 1 boss.
##
## M5 promoted the staged map over the shipped one and deleted the staging copy,
## which is what closes that hole for good: there is no longer a second map for
## a gateway to be authored into. Every rule below now applies to the map the
## running game loads, with no exemptions -- including
## `test_the_hub_has_a_gateway_for_every_level_on_disk`, which was an expected
## failure from the day World 2 shipped until the day of the promotion.

const TS := TileData4.TILE_SIZE

## The overworld, and there is exactly one —
## test_there_is_exactly_one_overworld_map is what keeps that true.
const HUB := "res://levels/hub.json"
const HUB_ID := "hub"

var _def: LevelLoader.LevelDef = null
var _doors: Array = []

func before_each() -> void:
	if _def != null:
		return
	_def = LevelLoader.load_path(HUB, HUB_ID)
	_doors = _def.entities_of("hub_door") if _def.ok() else []

func _levels() -> Array:
	var out: Array = []
	for d: Dictionary in _doors:
		out.append(String(d.get("level", "")))
	return out

func _door(level_id: String) -> Dictionary:
	for d: Dictionary in _doors:
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

# --------------------------------------------------------------- the hub loads
func test_the_overworld_is_on_disk() -> void:
	ok(FileAccess.file_exists(HUB),
		"levels/hub.json is the map the game loads; it has to exist")

func test_the_overworld_loads() -> void:
	ok(_def.ok(), "hub: %s" % ", ".join(_def.errors))

## The promotion's own invariant. Two overworld maps is the arrangement that let
## five levels ship with no way in: the gateways went into the staged map and the
## shipped one was never touched. staging/ is gone and must stay gone, and
## levels/ must hold exactly one top-down map.
func test_there_is_exactly_one_overworld_map() -> void:
	not_ok(DirAccess.dir_exists_absolute("res://staging"),
		"staging/ is back. It held a second overworld for three milestones and "
		+ "that is how M2's five gateways went missing from the shipped map")
	var topdown: Array = []
	for level_id in LevelLoader.list_levels():
		if LevelLoader.load_level(level_id).topdown:
			topdown.append(level_id)
	eq(topdown, [HUB_ID],
		"levels/ must hold exactly one top-down map and it must be the hub, got %s"
			% str(topdown))

func test_the_overworld_is_a_whole_number_of_screens() -> void:
	var w := _def.world.width
	var h := _def.world.height
	gt(float(w), 0.0, "the hub has width")
	gt(float(h), 0.0, "the hub has height")
	eq(w % 25, 0, "the hub is %d tiles wide, which is not whole screens" % w)
	eq(h % 15, 0, "the hub is %d tiles tall, which is not whole screens" % h)

func test_the_overworld_is_two_by_two_screens_of_fifty_by_thirty() -> void:
	eq(_def.world.width, 50, "hub width")
	eq(_def.world.height, 30, "hub height")

func test_the_overworld_is_top_down() -> void:
	ok(_def.topdown, "an overworld has no gravity and must say so")

func test_the_overworld_has_exactly_one_spawn() -> void:
	eq(_def.entities_of("player_spawn").size(), 1, "one spawn")

# --------------------------------------------------------------- the gateways
func test_the_overworld_holds_twenty_five_gateways() -> void:
	eq(_doors.size(), 25, "the hub must hold 25 gateways, one per level")

## The regression guard the suite was missing. Every level on disk that is not
## the overworld itself and not the integration fixture is a level the player is
## meant to be able to start, and the only way to start one is a gateway. M2
## shipped five levels with no way in; this is the assertion that says so, and
## from M2 until the promotion it was the suite's one expected failure.
func test_the_hub_has_a_gateway_for_every_level_on_disk() -> void:
	var ids := _levels()
	for level_id in LevelLoader.list_levels():
		if level_id == HUB_ID or level_id == "test_arena":
			continue
		has(ids, level_id,
			"levels/%s.json ships with no gateway on the overworld — nothing in " % level_id
			+ "the running game can reach it")

func test_every_gateway_belongs_to_a_known_world_and_no_world_is_half_present() -> void:
	var ids := _levels()
	var known: Array = []
	for world: String in WORLDS:
		var want: Array = WORLDS[world]
		var present := 0
		for level_id: String in want:
			if ids.has(level_id):
				present += 1
		if present > 0:
			eq(present, want.size(),
				"world '%s' has %d of its %d gateways — a world arrives whole"
					% [world, present, want.size()])
		for level_id: String in want:
			known.append(level_id)
	for level_id: String in ids:
		has(known, level_id, "gateway '%s' is in no known world" % level_id)

func test_every_gateway_is_unique() -> void:
	var seen := {}
	for level_id: String in _levels():
		not_ok(seen.has(level_id), "two gateways both point at '%s'" % level_id)
		seen[level_id] = true

func test_the_five_jungle_gateways_keep_their_shipped_ids_and_labels() -> void:
	# levels/hub.json as originally shipped. Changing any of these breaks a save
	# file, so the promotion had to carry them across unchanged.
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
	for d: Dictionary in _doors:
		gt(float(String(d.get("label", "")).length()), 0.0,
			"gateway '%s' has no label to show" % String(d.get("level", "")))

## The door-label defect class, made an assertion. A gateway's label is the only
## name the player ever sees for a level, and it is authored in a completely
## different file from the level's own `name` field — tools/build_hub.py's
## table versus tools/build_levels.py's registration — so the two can drift
## silently and the overworld ends up offering a door that says one thing and
## opens on a level titled another. Checked for all 25, both directions.
func test_every_gateway_label_is_the_levels_own_name() -> void:
	for d: Dictionary in _doors:
		var level_id := String(d.get("level", ""))
		var target := LevelLoader.load_level(level_id)
		if not target.ok():
			continue          # covered by the gateway-points-at-a-file test
		eq(String(d.get("label", "")), target.display_name,
			"the gateway for '%s' is labelled '%s' but the level calls itself '%s'"
				% [level_id, String(d.get("label", "")), target.display_name])

func test_every_gateway_points_at_a_level_that_exists() -> void:
	# No exemption any more. While the staged map existed it was allowed to hold
	# gateways for levels nobody had written; the map the game loads never was,
	# and now it is the only map there is.
	for d: Dictionary in _doors:
		var target := String(d.get("level", ""))
		ok(FileAccess.file_exists(LevelLoader.level_path(target)),
			"the overworld offers '%s', which is not a file" % target)

# ------------------------------------------------------------------ the chain
func test_exactly_one_gateway_is_open_from_a_fresh_save() -> void:
	var open: Array = []
	for d: Dictionary in _doors:
		if String(d.get("requires", "")) == "":
			open.append(String(d.get("level", "")))
	eq(open, ["jungle_1"], "a fresh save must offer exactly one way in")

func test_every_prerequisite_is_itself_a_gateway_on_the_same_map() -> void:
	var ids := _levels()
	for d: Dictionary in _doors:
		var req := String(d.get("requires", ""))
		if req == "":
			continue
		has(ids, req, "gateway '%s' requires '%s', which is not on this map — it "
			% [String(d.get("level", "")), req] + "could never unlock")

func test_the_requires_chain_never_loops() -> void:
	var req := {}
	for d: Dictionary in _doors:
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
## which counts FILES, not worlds. levels/hub.json shipped a requires_all on
## HEART OF THE GROVE, so the day World 2's five levels landed on disk the World
## 1 boss became unopenable: the door asked for flags no gateway could set. The
## explicit chain gives the same gate without that.
func test_no_gateway_uses_the_requires_all_shortcut() -> void:
	for d: Dictionary in _doors:
		not_ok(bool(d.get("requires_all", false)),
			"gateway '%s' uses requires_all" % String(d.get("level", "")))

## The outcome behind the rule above: with the whole chain walked, every gateway
## must actually come open. Replays the save the player would build, one level
## at a time, and insists nothing is left grey at the end.
func test_walking_the_whole_chain_opens_every_gateway() -> void:
	var req := {}
	for d: Dictionary in _doors:
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
		"%d of %d gateways can be opened by playing; the rest are walled off"
			% [opened.size(), req.size()])

# ------------------------------------------------------------------ placement
func test_no_two_gateways_share_a_tile() -> void:
	var seen := {}
	for d: Dictionary in _doors:
		var t := Vector2i(int(d["x"]), int(d["y"]))
		not_ok(seen.has(t), "two gateways sit on tile %s" % str(t))
		seen[t] = true

func test_no_gateway_sits_on_the_spawn() -> void:
	var s := Vector2i(int(_def.spawn.x / TS), int(_def.spawn.y / TS))
	for d: Dictionary in _doors:
		ne(Vector2i(int(d["x"]), int(d["y"])), s, "a gateway is on top of the spawn")

func test_every_gateway_sits_inside_the_map_with_room_below_it() -> void:
	# The game returns you one tile *below* the gateway you came from
	# (overworld.gd), so the bottom row can never hold one.
	var world := _def.world
	for d: Dictionary in _doors:
		var x := int(d["x"])
		var y := int(d["y"])
		ok(x >= 0 and x < world.width,
			"gateway '%s' is off the map" % String(d["level"]))
		ok(y >= 0 and y + 1 < world.height,
			"gateway '%s' has no tile below it to come back to" % String(d["level"]))
