extends TestCase
## Regressions for the three TestFlight reports against World 4 (fb_01..03).
## Each was a heart, or the way on, in plain view and out of reach -- which the
## Route Prover cannot see, because it proves the EXIT and nothing else. These
## run the real movement code (PickupReach over ProverSim) from where the owner
## was standing.


func _reach(level_id: String, broken: Array[Vector2i] = []) -> PickupReach:
	var def := LevelLoader.load_level(level_id)
	var sim := ProverSim.new()
	sim.setup(def)
	for t: Vector2i in broken:
		sim.world.break_tile(t.x, t.y)
	return PickupReach.new(sim)


func _heart_at(level_id: String, x: int, y: int) -> Rect2:
	var def := LevelLoader.load_level(level_id)
	for e: Dictionary in def.entities:
		if String(e.get("type", "")) == "heart" and int(e.get("x", -1)) == x \
				and int(e.get("y", -1)) == y:
			return PickupReach.target_rect(e)
	_fail("%s has no heart at (%d,%d)" % [level_id, x, y])
	return Rect2()


## fb_03, "the heart is not reachable": Kaya on deeps_2's low line under the
## reward shelf. The shelf is 48 px over that floor and her apex 44.5, so she
## needs the ladder in the pit to get back onto the high line -- and the heart
## is still behind the cracked_dirt wall, so it still costs the verb.
func test_fb03_the_low_line_climbs_back_to_the_shelf_heart() -> void:
	var reach := _reach("deeps_2")
	var start := reach.seed_at(Vector2i(13, 20), "human")
	var up := reach.search(start, 0, PickupReach.tile_rect(Vector2i(14, 17)), true, false, 3000)
	ok(bool(up["found"]), "from the low line she stands on the high line again")
	var high := reach.seed_at(Vector2i(14, 17), "human")
	var heart := _heart_at("deeps_2", 7, 17)
	var walk := reach.search(high, 0, heart, false, false, 300)
	not_ok(bool(walk["found"]), "the wall still stands between the high line and the heart (not within 300)")
	var brk := reach.search(high, 0, heart, false, true, 3000)
	ok(bool(brk["found"]), "and breaking it gets the heart")
	reach.dispose()


## fb_02, "stuck": the frog on deeps_2's stair. The way on used to be two blind
## jumps up a one-tile shaft beside a ladder the frog cannot climb. Now the top
## tread turns her back into Kaya, who can.
func test_fb02_the_stair_top_gives_back_the_human() -> void:
	var def := LevelLoader.load_level("deeps_2")
	var pads: Array[Vector2i] = []
	for e: Dictionary in def.entities:
		if String(e.get("type", "")) == "pad_human":
			pads.append(Vector2i(int(e["x"]), int(e["y"])))
	eq(pads, [Vector2i(41, 18)] as Array[Vector2i], "one human pad, on the stair's top tread")
	var reach := _reach("deeps_2")
	var pad := PickupReach.target_rect({"type": "pad_human", "x": 41, "y": 18})
	var r := reach.search(reach.seed_at(Vector2i(36, 21), "frog"), 0, pad, false, false, 3000)
	ok(bool(r["found"]), "the frog on tread 2 reaches the human pad")
	# And back: from the stair top she can drop to the cellar, where the frog pad is.
	var down := reach.search(reach.seed_at(Vector2i(41, 18), "human"), 0,
		PickupReach.tile_rect(Vector2i(41, 27)), true, false, 3000)
	ok(bool(down["found"]), "and the woman can get back down to the cellar")
	reach.dispose()


## fb_01, "out of reach": deeps_4 with the lantern block broken -- one blade
## throw does it. The vault ledge is 64 px over the gallery floor against a
## 44.5 px apex; the one-way shelf at (17,7) is what makes it two 32 px steps.
func test_fb01_the_vault_survives_a_broken_lantern_block() -> void:
	var block: Array[Vector2i] = [Vector2i(15, 7), Vector2i(16, 7), Vector2i(15, 8), Vector2i(16, 8)]
	var reach := _reach("deeps_4", block)
	not_ok(reach.sim.world.is_solid(15, 8), "the block is broken")
	var ledge := reach.search(reach.seed_at(Vector2i(17, 8), "human"), 0,
		PickupReach.tile_rect(Vector2i(18, 4)), true, false, 3000)
	ok(bool(ledge["found"]), "she still gets onto the vault ledge")
	var heart := _heart_at("deeps_4", 23, 4)
	var r := reach.search(reach.seed_at(Vector2i(19, 4), "human"), 0, heart, false, true, 3000)
	ok(bool(r["found"]), "and the blade opens the vault to the heart")
	reach.dispose()
