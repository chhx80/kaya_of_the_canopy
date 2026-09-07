@tool
class_name PixelLabel
extends Control
## Control wrapper around PixelFont so labels can be placed in .tscn files.

enum Align { LEFT, CENTER, RIGHT }

@export var text := "":
	set(v): text = v; queue_redraw(); _fit()
@export var text_color := Color(0.957, 0.941, 0.902):
	set(v): text_color = v; queue_redraw()
@export var shadow_color := Color(0, 0, 0, 0.75):
	set(v): shadow_color = v; queue_redraw()
@export var shadowed := true:
	set(v): shadowed = v; queue_redraw()
@export_range(1, 8) var text_scale := 1:
	set(v): text_scale = v; queue_redraw(); _fit()
@export_range(-4, 8) var tracking := 0:
	set(v): tracking = v; queue_redraw(); _fit()
@export var align: Align = Align.LEFT:
	set(v): align = v; queue_redraw()

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fit()

func _fit() -> void:
	custom_minimum_size = Vector2(
		PixelFont.width(text, text_scale, tracking), PixelFont.height(text_scale))

func _draw() -> void:
	var w := PixelFont.width(text, text_scale, tracking)
	var x := 0.0
	match align:
		Align.CENTER: x = round((size.x - w) * 0.5)
		Align.RIGHT: x = size.x - w
	if shadowed:
		PixelFont.draw_shadowed(self, Vector2(x, 0), text, text_color, shadow_color,
			text_scale, tracking)
	else:
		PixelFont.draw(self, Vector2(x, 0), text, text_color, text_scale, tracking)
