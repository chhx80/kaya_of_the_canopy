class_name ParallaxBg
extends Node2D
## Tiling parallax layer. A plain Sprite2D only covers one screen, so this draws
## the strip enough times to cover the camera wherever the screen flip lands.
##
## Two properties of this are load-bearing and neither is obvious:
##
## * **The strip is exactly one screen (400x240).** Horizontally that is what
##   makes the wrap invisible — the art is generated to tile at 400 — and
##   vertically it is what keeps a tall level seam-free. With `vertical_factor`
##   at 0 the offset is always 0, so `start.y` lands on a multiple of 240, which
##   is exactly where a screen boundary is: every screen row of a level draws the
##   same backdrop from its own top edge. Give a layer a vertical factor and the
##   wrap point drifts off the screen grid, and the join becomes a visible seam
##   sliding down the level. Phase 3 keeps all three planes at 0.
## * **`view` is the camera's *unshaken* rect** (CameraController.view_rect), so
##   a screen shake cannot make the backdrop re-tile under itself.

var texture: Texture2D = null
var factor := 0.25          ## 0 = glued to the camera, 1 = glued to the world
var tint := Color.WHITE
var view := Rect2(0, 0, 400, 240)
var vertical_factor := 0.0  ## usually flatter than horizontal, or 0 for locked

func setup(tex_path: String, f: float, vf: float = -1.0) -> void:
	texture = load(tex_path)
	factor = f
	vertical_factor = f * 0.5 if vf < 0.0 else vf
	queue_redraw()

func set_view(r: Rect2) -> void:
	view = r
	queue_redraw()

func _draw() -> void:
	if texture == null:
		return
	var ts := texture.get_size()
	var off := Vector2(view.position.x * factor, view.position.y * vertical_factor)
	var start := Vector2(
		view.position.x - fposmod(view.position.x - off.x, ts.x),
		view.position.y - fposmod(view.position.y - off.y, ts.y))
	# Exactly the copies the view touches. The old `+ 1` always drew a spare row
	# and column; with three planes instead of two that was a third of the
	# backdrop's draw calls spent entirely off-screen, and on the common case —
	# a screen-aligned view and a screen-sized strip — the honest count is one.
	var cols := int(ceil((view.size.x + view.position.x - start.x) / ts.x))
	var rows := int(ceil((view.size.y + view.position.y - start.y) / ts.y))
	for ry in rows:
		for rx in cols:
			draw_texture(texture, (start + Vector2(rx * ts.x, ry * ts.y)).round(), tint)
