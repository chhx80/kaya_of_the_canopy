extends Node
## Root of the running game. Holds the world slot, the UI layer and the fader.

@onready var world: Node2D = $World
@onready var ui: CanvasLayer = $UI
@onready var touch_layer: CanvasLayer = $TouchLayer
@onready var fade: ColorRect = $Fade/Rect

var _current: Node = null
var touch: Control = null

func _ready() -> void:
	# Deliberately NOT PROCESS_MODE_ALWAYS: Main is the parent of the world, so
	# forcing it to always process would make `get_tree().paused` a no-op for
	# every actor underneath it. The pause overlay and the touch layer opt in
	# individually instead.
	Game.main = self
	fade.color = Color(0, 0, 0, 0)
	touch = (load("res://src/ui/touch_controls.gd") as GDScript).new()
	touch.name = "TouchControls"
	touch_layer.add_child(touch)
	_maybe_start_dev_harness()
	Game.goto_title()

## The screenshot/integration harness lives in tools/, which release exports
## strip. It used to be an autoload, which meant a shipped build died at startup
## on a missing script — so it is now loaded on demand and only when asked for.
func _maybe_start_dev_harness() -> void:
	if OS.get_cmdline_user_args().is_empty():
		return
	const PATH := "res://tools/dev_capture.gd"
	if not ResourceLoader.exists(PATH):
		return
	var script: GDScript = load(PATH)
	if script == null or not script.can_instantiate():
		return
	var harness: Node = script.new()
	harness.name = "DevCapture"
	add_child(harness)

## Polled rather than handled as an event: synthetic input (touch overlay, the
## capture harness, on-screen pause button) sets the action state directly and
## never produces an InputEvent.
func _process(_delta: float) -> void:
	if not Input.is_action_just_pressed(&"pause"):
		return
	# Pause only exists inside a level or on the hub.
	if Game.state != Game.State.LEVEL and Game.state != Game.State.HUB:
		return
	if ui.has_node("PauseScreen"):
		return
	var pause: Control = (load("res://src/ui/menus/pause_screen.gd") as GDScript).new()
	pause.name = "PauseScreen"
	ui.add_child(pause)
	AudioManager.play("select")

## Replaces whatever is in the world slot. Returns the new instance.
func swap_world(scene_path: String) -> Node:
	if _current != null and is_instance_valid(_current):
		_current.queue_free()
		world.remove_child(_current)
		_current = null
	if not ResourceLoader.exists(scene_path):
		push_error("Main: missing scene %s" % scene_path)
		return null
	var packed: PackedScene = load(scene_path)
	var inst := packed.instantiate()
	world.add_child(inst)
	_current = inst
	_transition_in()
	return inst

## Every scene arrives out of black. Cheap, and it hides the one-frame pop while
## a level builds its tile layers.
func _transition_in(duration: float = 0.22) -> void:
	fade.color = Color(0, 0, 0, 1)
	var t := create_tween()
	t.set_pause_mode(Tween.TWEEN_PAUSE_PROCESS)
	t.tween_property(fade, "color", Color(0, 0, 0, 0), duration)

## Static caches (the bitmap font texture, the tile flag table) are not owned by
## the tree, so they have to be dropped explicitly or the engine reports them as
## leaked at exit.
func _exit_tree() -> void:
	PixelFont.release()
	TileData4.release()

func current_scene() -> Node:
	return _current

## Short fade used between screens. Awaited by callers that care.
func flash_fade(duration: float = 0.25) -> void:
	var t := create_tween()
	fade.color = Color(0, 0, 0, 1)
	t.tween_property(fade, "color", Color(0, 0, 0, 0), duration)
	await t.finished
