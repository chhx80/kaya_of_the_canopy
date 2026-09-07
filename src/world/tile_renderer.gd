class_name TileRenderer
extends Node2D
## Draws one tile layer straight from the atlas, culled to the visible screen.
## A TileMapLayer would need a TileSet resource authored in the editor; this is
## ~40 lines, fully deterministic, and lets the camera drive the cull.

const TS := TileData4.TILE_SIZE

var world: TileWorld = null
var layer := "fg"                       ## "fg" or "bg"
var atlas: Texture2D = null
var modulate_color := Color.WHITE
var view := Rect2(0, 0, 400, 240)

func setup(w: TileWorld, which: String) -> void:
	world = w
	layer = which
	atlas = load("res://assets/tiles/tileset.png")
	queue_redraw()

func set_view(r: Rect2) -> void:
	if r != view:
		view = r
		queue_redraw()

func _draw() -> void:
	if world == null or atlas == null:
		return
	var x0 := maxi(0, int(floor(view.position.x / TS)) - 1)
	var y0 := maxi(0, int(floor(view.position.y / TS)) - 1)
	var x1 := mini(world.width - 1, int(ceil((view.position.x + view.size.x) / TS)) + 1)
	var y1 := mini(world.height - 1, int(ceil((view.position.y + view.size.y) / TS)) + 1)
	var cols := world.data.atlas_columns
	for ty in range(y0, y1 + 1):
		for tx in range(x0, x1 + 1):
			var id := world.get_bg(tx, ty) if layer == "bg" else world.get_fg(tx, ty)
			if id <= 0:
				continue
			if layer == "fg" and world.flags_at(tx, ty) & TileData4.Flag.SWITCHED:
				# Ghost the inactive half of a switch pair instead of hiding it.
				if not world.is_solid(tx, ty):
					id = _ghost_of(id)
			var src := Rect2(float((id % cols) * TS), float((id / cols) * TS), TS, TS)
			draw_texture_rect_region(atlas,
				Rect2(Vector2(tx * TS, ty * TS), Vector2(TS, TS)), src, modulate_color)

func _ghost_of(id: int) -> int:
	match id:
		11: return 26
		26: return 11
		12: return 27
		27: return 12
	return id
