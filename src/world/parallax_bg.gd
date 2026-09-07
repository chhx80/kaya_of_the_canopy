class_name ParallaxBg
extends Node2D
## Tiling parallax layer. A plain Sprite2D only covers one screen, so this draws
## the strip enough times to cover the camera wherever the screen flip lands.

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
	var cols := int(ceil(view.size.x / ts.x)) + 1
	var rows := int(ceil(view.size.y / ts.y)) + 1
	for ry in rows:
		for rx in cols:
			draw_texture(texture, (start + Vector2(rx * ts.x, ry * ts.y)).round(), tint)
