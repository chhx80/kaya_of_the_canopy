extends Node2D
## Standalone options screen reached from the title menu. Wraps the shared
## panel so the title can swap to it like any other world scene.

var _bg: Texture2D = null

func _ready() -> void:
	_bg = load("res://assets/sprites/title_bg.png")
	var panel: Control = (load("res://src/ui/menus/options_panel.gd") as GDScript).new()
	panel.on_closed = func() -> void:
		Game.goto_title()
	Game.main.ui.add_child(panel)
	tree_exiting.connect(func() -> void:
		if is_instance_valid(panel):
			panel.queue_free())

func _draw() -> void:
	if _bg:
		draw_texture(_bg, Vector2.ZERO, Color(0.6, 0.65, 0.7))
