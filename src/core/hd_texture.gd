class_name HdTexture
extends Texture2D
## A world-space sheet at `art_scale` texels per world unit, presented to the
## game in world units (docs/plan-hd.md).
##
## Its size is the sheet's size divided by the scale, and every source rect it
## is asked to draw is multiplied by it on the way to the RenderingServer. So a
## Sprite2D's `region_rect` and `offset`, a `draw_texture_rect_region()` source
## rect, a tile atlas cell, a parallax strip's width — all of it stays exactly
## what it was in the 1x game, and the one multiplication lives here.
##
## The drawn quad is in world units too, which in the world viewport (camera
## zoom = art_scale) lands one texel per screen texel. Nothing else in the
## engine needs to know.

var base: Texture2D = null
var k := 2.0

static func wrap(tex: Texture2D, scale: int) -> HdTexture:
	var t := HdTexture.new()
	t.base = tex
	t.k = float(scale)
	return t

func _get_width() -> int:
	return int(base.get_width() / k)

func _get_height() -> int:
	return int(base.get_height() / k)

func _has_alpha() -> bool:
	return base.has_alpha()

func _is_pixel_opaque(x: int, y: int) -> bool:
	var img := base.get_image()
	if img == null:
		return true
	return img.get_pixel(int(float(x) * k), int(float(y) * k)).a > 0.0

func _get_rid() -> RID:
	return base.get_rid()

func _draw(ci: RID, pos: Vector2, modulate: Color, transpose: bool) -> void:
	RenderingServer.canvas_item_add_texture_rect(ci, Rect2(pos, get_size()),
		base.get_rid(), false, modulate, transpose)

func _draw_rect(ci: RID, rect: Rect2, tile: bool, modulate: Color, transpose: bool) -> void:
	if tile:
		# A tiled fill repeats per *texel* in the server; ask for the source
		# in texels instead so it repeats per world unit of the sheet.
		RenderingServer.canvas_item_add_texture_rect_region(ci, rect, base.get_rid(),
			Rect2(Vector2.ZERO, rect.size * k), modulate, transpose, false)
		return
	RenderingServer.canvas_item_add_texture_rect(ci, rect, base.get_rid(), false,
		modulate, transpose)

func _draw_rect_region(ci: RID, rect: Rect2, src: Rect2, modulate: Color,
		transpose: bool, clip_uv: bool) -> void:
	RenderingServer.canvas_item_add_texture_rect_region(ci, rect, base.get_rid(),
		Rect2(src.position * k, src.size * k), modulate, transpose, clip_uv)
