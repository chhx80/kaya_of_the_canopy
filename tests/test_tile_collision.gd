extends TestCase
## Table-driven collision cases. Grid legend used below:
##   0 empty  1 dirt(solid)  5 wood(one-way)  6 vine(ladder)  8 water  9 spikes
##  10 crate(breakable)  11 switch A on-solid  26 switch A off-solid

const TS := 16

var world: TileWorld

func before_each() -> void:
	# 8x6 room: solid floor along the bottom, solid walls on both sides.
	var rows: Array = []
	for y in 6:
		var r: Array = []
		for x in 8:
			var v := 0
			if y == 5 or x == 0 or x == 7:
				v = 1
			r.append(v)
		rows.append(r)
	world = TileWorld.from_rows(rows)

func _actor(px: float, py: float, w: float = 12.0, h: float = 20.0) -> Rect2:
	return Rect2(Vector2(px, py), Vector2(w, h))

# ---------------------------------------------------------------- solids
func test_falls_and_lands_exactly_on_floor_top() -> void:
	var r := _actor(32, 20)
	var res := TileCollision.move_y(world, r, 200.0)
	ok(res.on_floor, "should land")
	near(res.rect.position.y + res.rect.size.y, 5 * TS, 0.001, "feet flush with floor top")

func test_landing_on_seam_does_not_sink() -> void:
	# Start already flush with the floor; a tiny downward nudge must not move us.
	var r := _actor(32, 5 * TS - 20)
	var res := TileCollision.move_y(world, r, 0.4)
	ok(res.on_floor, "still grounded")
	near(res.rect.position.y, 5 * TS - 20, 0.001, "no sinking through the seam")

func test_walks_into_right_wall_and_stops() -> void:
	var r := _actor(32, 5 * TS - 20)
	var res := TileCollision.move_x(world, r, 200.0)
	ok(res.hit_right, "hit the right wall")
	near(res.rect.position.x + res.rect.size.x, 7 * TS, 0.001, "flush against wall")

func test_walks_into_left_wall_and_stops() -> void:
	var r := _actor(32, 5 * TS - 20)
	var res := TileCollision.move_x(world, r, -200.0)
	ok(res.hit_left, "hit the left wall")
	near(res.rect.position.x, 1 * TS, 0.001, "flush against wall")

func test_jump_into_ceiling_stops_at_tile_bottom() -> void:
	world.set_fg(2, 1, 1)
	world.set_fg(3, 1, 1)
	var r := _actor(2 * TS + 2, 3 * TS)
	var res := TileCollision.move_y(world, r, -100.0)
	ok(res.hit_ceiling, "bonked")
	near(res.rect.position.y, 2 * TS, 0.001, "flush under ceiling tile")

func test_fast_move_does_not_tunnel_through_thin_wall() -> void:
	world.set_fg(4, 4, 1)
	var r := _actor(1 * TS + 2, 4 * TS - 4, 12, 20)
	var res := TileCollision.move_x(world, r, 400.0)
	ok(res.hit_right, "must be stopped by the single-tile pillar")
	lt(res.rect.position.x + res.rect.size.x, 4 * TS + 0.5, "did not pass through")

# ---------------------------------------------------------------- one-way
func test_oneway_catches_you_when_falling_from_above() -> void:
	world.set_fg(3, 3, 5)
	var r := _actor(3 * TS, 3 * TS - 24)   # feet at 3*TS-4, above the platform top
	var res := TileCollision.move_y(world, r, 12.0)
	ok(res.on_floor, "landed on the one-way")
	near(res.rect.position.y + res.rect.size.y, 3 * TS, 0.001, "stands on its top edge")

func test_oneway_is_passable_from_below() -> void:
	world.set_fg(3, 3, 5)
	var r := _actor(3 * TS, 3 * TS + 4)    # feet already below the platform top
	var res := TileCollision.move_y(world, r, -20.0)
	not_ok(res.hit_ceiling, "must pass straight through going up")
	near(res.rect.position.y, 3 * TS - 16.0, 0.001, "moved the full distance")

func test_oneway_is_passable_when_dropping_through() -> void:
	world.set_fg(3, 3, 5)
	var r := _actor(3 * TS, 3 * TS - 20)
	var res := TileCollision.move_y(world, r, 8.0, true)
	not_ok(res.on_floor, "drop-through ignores the platform")

func test_oneway_does_not_block_horizontal_movement() -> void:
	world.set_fg(3, 2, 5)
	var r := _actor(2 * TS, 2 * TS)
	var res := TileCollision.move_x(world, r, 20.0)
	not_ok(res.hit_wall(), "one-way tiles are never walls")

# ---------------------------------------------------------------- flags
func test_ladder_flag_is_detected_by_overlap() -> void:
	world.set_fg(3, 3, 6)
	var on := _actor(3 * TS + 2, 3 * TS + 2)
	ok(TileCollision.has_flag(world, on, TileData4.Flag.LADDER), "overlapping the vine")
	var off := _actor(5 * TS, 3 * TS)
	not_ok(TileCollision.has_flag(world, off, TileData4.Flag.LADDER), "away from the vine")

func test_ladder_is_not_solid() -> void:
	world.set_fg(3, 4, 6)
	var r := _actor(3 * TS, 3 * TS)
	var res := TileCollision.move_y(world, r, 10.0)
	not_ok(res.on_floor, "vines never stop a fall")

func test_water_and_hazard_flags() -> void:
	world.set_fg(2, 4, 8)
	world.set_fg(4, 4, 9)
	ok(TileCollision.has_flag(world, _actor(2 * TS + 1, 4 * TS + 1, 8, 8), TileData4.Flag.WATER))
	ok(TileCollision.has_flag(world, _actor(4 * TS + 1, 4 * TS + 1, 8, 8), TileData4.Flag.HAZARD))
	not_ok(TileCollision.has_flag(world, _actor(2 * TS + 1, 4 * TS + 1, 8, 8), TileData4.Flag.HAZARD))

func test_tiles_with_flag_lists_every_overlapped_cell() -> void:
	world.set_fg(2, 3, 9)
	world.set_fg(3, 3, 9)
	var found := TileCollision.tiles_with_flag(world, _actor(2 * TS + 8, 3 * TS + 4, 16, 8),
		TileData4.Flag.HAZARD)
	eq(found.size(), 2, "spans two spike tiles")
	has(found, Vector2i(2, 3))
	has(found, Vector2i(3, 3))

# ---------------------------------------------------------------- switches
func test_switch_blocks_swap_solidity_with_the_group() -> void:
	world.set_fg(3, 4, 11)   # group 1, solid while group 1 is ON
	world.set_fg(4, 4, 26)   # group 1, solid while group 1 is OFF
	world.set_switch(1, true)
	ok(world.is_solid(3, 4), "A-on is solid when the group is on")
	not_ok(world.is_solid(4, 4), "A-off is passable when the group is on")
	world.toggle_switch(1)
	not_ok(world.is_solid(3, 4), "…and they swap")
	ok(world.is_solid(4, 4))

func test_switch_block_stops_a_fall_only_while_solid() -> void:
	world.set_fg(3, 3, 11)
	world.set_switch(1, true)
	var r := _actor(3 * TS, 3 * TS - 24)
	ok(TileCollision.move_y(world, r, 20.0).on_floor, "solid: lands")
	world.set_switch(1, false)
	not_ok(TileCollision.move_y(world, r, 20.0).on_floor, "off: falls through")

# ---------------------------------------------------------------- breakables
func test_breaking_a_crate_removes_its_collision() -> void:
	world.set_fg(3, 3, 10)
	ok(world.is_solid(3, 3), "crate starts solid")
	ok(world.break_tile(3, 3), "crate is breakable")
	not_ok(world.is_solid(3, 3), "gone after breaking")
	world.reset_broken()
	ok(world.is_solid(3, 3), "restored on level reset")

func test_non_breakable_tiles_refuse_to_break() -> void:
	not_ok(world.break_tile(1, 5), "dirt is not breakable")
	ok(world.is_solid(1, 5))

# ---------------------------------------------------------------- bounds
func test_out_of_bounds_sides_are_walls_but_the_floor_is_open() -> void:
	ok(world.is_solid(-1, 2), "left of the map is a wall")
	ok(world.is_solid(99, 2), "right of the map is a wall")
	ok(world.is_solid(3, -1), "above the map is a wall")
	not_ok(world.is_solid(3, 99), "below the map is open so you can fall out")

func test_tile_range_covers_exact_spans() -> void:
	eq(TileCollision.tile_range(0.0, 16.0), Vector2i(0, 0), "a rect flush in one tile")
	eq(TileCollision.tile_range(0.0, 17.0), Vector2i(0, 1), "spilling into the next")
	eq(TileCollision.tile_range(15.9, 32.0), Vector2i(0, 1))
