class_name Actor
extends Node2D
## Anything that moves against the tile grid: the player, enemies, projectiles.
## Owns a float AABB and steps it through TileCollision. Rendering rounds to
## whole pixels; the simulation never does.

signal landed()
signal hit_wall()

var world: TileWorld = null
var level: Node = null

var pos := Vector2.ZERO          ## top-left of the AABB, world pixels
var vel := Vector2.ZERO          ## px/s
var box := Vector2(12, 20)       ## AABB size

var on_floor := false
var was_on_floor := false
var on_ceiling := false
var against_wall := 0            ## -1 left, +1 right, 0 none
var facing := 1                  ## -1 or +1
var drop_through := false        ## ignore one-ways this tick

var last_floor_tile := Vector2i(-1, -1)
var last_wall_tile := Vector2i(-1, -1)

func aabb() -> Rect2:
	return Rect2(pos, box)

func set_center(c: Vector2) -> void:
	pos = c - box * 0.5

func center() -> Vector2:
	return pos + box * 0.5

func feet() -> Vector2:
	return Vector2(pos.x + box.x * 0.5, pos.y + box.y)

## Integrate one tick. Returns true if anything was hit.
func step_motion(delta: float) -> void:
	was_on_floor = on_floor
	against_wall = 0
	on_ceiling = false
	var r := aabb()

	var rx := TileCollision.move_x(world, r, vel.x * delta)
	r = rx.rect
	if rx.hit_left:
		against_wall = -1
	elif rx.hit_right:
		against_wall = 1
	if rx.hit_wall():
		last_wall_tile = rx.wall_tile
		vel.x = 0.0
		hit_wall.emit()

	var ry := TileCollision.move_y(world, r, vel.y * delta, drop_through)
	r = ry.rect
	on_floor = ry.on_floor
	on_ceiling = ry.hit_ceiling
	if ry.on_floor:
		last_floor_tile = ry.floor_tile
		if vel.y > 0.0:
			vel.y = 0.0
		if not was_on_floor:
			landed.emit()
	elif ry.hit_ceiling:
		last_floor_tile = Vector2i(-1, -1)
		if vel.y < 0.0:
			vel.y = 0.0

	pos = r.position
	if not on_floor:
		# Grounded state must survive standing still on a one-way platform.
		on_floor = TileCollision.is_on_floor(world, aabb(), drop_through)

func overlaps_flag(flag: int) -> bool:
	return TileCollision.has_flag(world, aabb(), flag)

## Sampled at the actor's upper body, so wading is not the same as swimming.
func submerged() -> bool:
	var probe := Rect2(pos + Vector2(1, 1), Vector2(box.x - 2, box.y * 0.5))
	return TileCollision.has_flag(world, probe, TileData4.Flag.WATER)

func in_water() -> bool:
	return overlaps_flag(TileData4.Flag.WATER)

func on_ladder() -> bool:
	return overlaps_flag(TileData4.Flag.LADDER)

func touching_hazard() -> bool:
	var probe := Rect2(pos + Vector2(2, 2), box - Vector2(4, 4))
	return TileCollision.has_flag(world, probe, TileData4.Flag.HAZARD)

## True when solid ground continues ahead — used by walkers to turn at ledges.
func ground_ahead(dir: int, lookahead: float = 8.0) -> bool:
	var x := pos.x + (box.x + lookahead if dir > 0 else -lookahead)
	return TileCollision.solid_at_pixel(world, x, pos.y + box.y + 2.0)

func fell_out_of_world() -> bool:
	return world != null and pos.y > float(world.pixel_height()) + 32.0

func _sync_render_position() -> void:
	position = pos.round()
