extends TestCase
## PickupReach, the search behind tools/pickupgate.sh.
##
## REACHED has to be a real way in, so every positive below is replayed. The
## negatives are BOUNDED, not exhaustive: exhausting even a 5x2 room costs this
## search 8,000-14,000 expansions and 75-170 s (measured: the shoulder wall as
## the human 7,945 exp, as the frog 13,772; the crate as the frog 13,772 -- all
## exhausted, none found), which no unit suite can pay on every run. So a
## negative here is "not within NEG_BUDGET", paired with the same room's
## positive, which is what makes the difference the verb's and not the budget's.

const NEG_BUDGET := 300

const HEART_RECT_OFFSET := Vector2(2, 2)


## `rows` drawn in the jungle legend: s stone, k cracked_stone (a shoulder wall,
## break_hold 0.35), c crate (no break_hold: the blade only).
func _room(rows: Array, ents: Array) -> ProverSim:
	var bg: Array = []
	for r: String in rows:
		bg.append(".".repeat(r.length()))
	var all: Array = [{"type": "player_spawn", "x": 1, "y": rows.size() - 2}]
	all.append_array(ents)
	var def := LevelLoader.from_dict({"id": "pickupgate_room", "name": "ROOM",
		"topdown": false, "fg": rows, "bg": bg, "entities": all})
	var sim := ProverSim.new()
	sim.setup(def)
	return sim


func _heart(x: int, y: int) -> Rect2:
	return PickupReach.target_rect({"type": "heart", "x": x, "y": y})


func _corridor(plug: String) -> ProverSim:
	# Two rows of air and no more: with a third, the 11 px frog hops the plug.
	return _room([
		"ssssssssss",
		"ssssssssss",
		"s....%s...s" % plug,
		"s....%s...s" % plug,
		"ssssssssss",
	], [])


# ------------------------------------------------------------------ the goal

## A heart hung in the air is collected by a jump through it -- Pickup collects on
## overlap -- so touch finds it, and "stand on it" must not.
func test_touch_counts_in_mid_air() -> void:
	var sim := _room([
		"ssssssssss",
		"s........s",
		"s........s",
		"s........s",
		"s........s",
		"ssssssssss",
	], [])
	var reach := PickupReach.new(sim)
	var start := reach.seed_at(Vector2i(2, 4), "human")
	var goal := _heart(5, 2)
	var r := reach.search(start, 0, goal, false, false, 3000)
	ok(bool(r["found"]), "a jump through the heart collects it")
	ok(reach.replays(start, 0, r["actions"], goal, false), "and the tape does it again")
	var s := reach.search(start, 0, goal, true, false, NEG_BUDGET)
	not_ok(bool(s["found"]), "nothing to stand on up there")
	reach.dispose()


## 48 px over the floor is the deeps_2 shelf's rise. The human's apex is 44.5 px.
func test_a_three_tile_ledge_is_out_of_the_humans_reach() -> void:
	var sim := _room([
		"ssssssssss",
		"s........s",
		"s........s",
		"s.....ssss",
		"s........s",
		"s........s",
		"ssssssssss",
	], [])
	var reach := PickupReach.new(sim)
	var start := reach.seed_at(Vector2i(2, 5), "human")
	var r := reach.search(start, 0, PickupReach.tile_rect(Vector2i(7, 2)), true, false, NEG_BUDGET)
	not_ok(bool(r["found"]), "no standing on a ledge three tiles up")
	var two := reach.search(start, 0, PickupReach.tile_rect(Vector2i(5, 2)), false, false, 3000)
	ok(bool(two["found"]), "though her jump does carry her up beside it")
	reach.dispose()


# ------------------------------------------------------------------ breaking

## A shoulder wall: closed without attack, open with it, to every form.
func test_a_shoulder_wall_opens_only_to_attack() -> void:
	for form: String in ["human", "frog"]:
		var sim := _corridor("k")
		var reach := PickupReach.new(sim)
		var start := reach.seed_at(Vector2i(2, 3), form)
		var goal := _heart(7, 3)
		var shut := reach.search(start, 0, goal, false, false, NEG_BUDGET)
		not_ok(bool(shut["found"]), "%s: the wall is a wall without attack" % form)
		var open := reach.search(start, 0, goal, false, true, 3000)
		ok(bool(open["found"]), "%s: holding attack into it opens it" % form)
		gt(float(open["broke"]), 0.0, "%s: by breaking it" % form)
		ok(reach.replays(start, 0, open["actions"], goal, false),
			"%s: and the replay breaks it too" % form)
		reach.dispose()


## A crate declares no break_hold: the shoulder cannot open it, the blade can,
## and the frog carries no blade.
func test_a_blade_only_wall_opens_to_the_human_and_not_the_frog() -> void:
	var goal := _heart(7, 3)
	# One room each: a search leaves the world as its last state had it, and
	# seed_at() starts from that world -- the crate the human broke stays broken.
	var reach := PickupReach.new(_corridor("c"))
	var human := reach.search(reach.seed_at(Vector2i(2, 3), "human"), 0, goal, false, true, 3000)
	ok(bool(human["found"]), "the thrown blade shatters the crate")
	gt(float(human["broke"]), 0.0, "by breaking it")
	reach.dispose()
	reach = PickupReach.new(_corridor("c"))
	var frog := reach.search(reach.seed_at(Vector2i(2, 3), "frog"), 0, goal, false, true, NEG_BUDGET)
	not_ok(bool(frog["found"]), "the frog has no blade")
	reach.dispose()


## A broken tile is state. Restoring a snapshot taken before the break must put
## the wall back, or one branch's break would open the wall for every branch.
func test_restore_puts_a_broken_wall_back() -> void:
	var sim := _corridor("k")
	var reach := PickupReach.new(sim)
	var before := reach.snap()
	ok(sim.world.is_solid(5, 3), "the plug starts solid")
	sim.world.break_tile(5, 3)
	not_ok(sim.world.is_solid(5, 3), "broken")
	var after := reach.snap()
	reach.restore(before)
	ok(sim.world.is_solid(5, 3), "restore() put it back")
	reach.restore(after)
	not_ok(sim.world.is_solid(5, 3), "and restore() of the later state breaks it again")
	reach.dispose()
