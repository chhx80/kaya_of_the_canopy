extends Node
## Root of the running game. Holds the world slot, the UI layer and the fader.

## Phase D, docs/plan-art-motion.md: the scene fade's pixel-dissolve mask. See
## src/core/fade_dissolve.gdshader for the shader itself; FADE_STEPS is what
## turns its continuous `progress` uniform into a 4-frame effect — the same
## vocabulary as a particle one-shot's 4 frames, not 4 physics ticks.
const FADE_SHADER := preload("res://src/core/fade_dissolve.gdshader")
const FADE_STEPS := 4
## The HD pass (docs/plan-hd.md): the sharp-bilinear blit of the world.
const WORLD_SHADER := preload("res://src/core/world_view.gdshader")

@onready var world: Node2D = $WorldFrame/WorldView/WorldViewport/World
@onready var world_view: TextureRect = $WorldFrame/WorldView
@onready var world_viewport: SubViewport = $WorldFrame/WorldView/WorldViewport
@onready var ui: CanvasLayer = $UI
@onready var touch_layer: CanvasLayer = $TouchLayer
@onready var fade: ColorRect = $Fade/Rect

var _current: Node = null
var touch: Control = null
## The part of the world's render target being shown, and the world units it
## covers: the explore view, an arena, or somewhere in the ease between them.
var _world_region: AtlasTexture = null
var _world_mat: ShaderMaterial = null
var _view_size := Vector2.ZERO

func _ready() -> void:
	# Deliberately NOT PROCESS_MODE_ALWAYS: Main is the parent of the world, so
	# forcing it to always process would make `get_tree().paused` a no-op for
	# every actor underneath it. The pause overlay and the touch layer opt in
	# individually instead.
	Game.main = self
	var fade_mat := ShaderMaterial.new()
	fade_mat.shader = FADE_SHADER
	fade.material = fade_mat
	fade.color = Color(0, 0, 0, 0)
	_set_fade_progress(1.0)   # idle: fully revealed, nothing hidden
	_setup_world_view()
	get_viewport().size_changed.connect(_layout_world_view)
	touch = (load("res://src/ui/touch_controls.gd") as GDScript).new()
	touch.name = "TouchControls"
	touch_layer.add_child(touch)
	_maybe_start_dev_harness()
	Game.goto_title()

## The world renders into a SubViewport at art_scale texels per world unit,
## sized once for the largest view the camera ever asks for (a whole boss
## arena), so pulling back never reallocates it. The camera's zoom is
## art_scale, always; what changes is how much of the target is shown. That
## region is drawn as large as the device allows, centred, through the
## sharp-bilinear filter — no whole-number stepping (Display.world_display_for).
##
## The HUD and the touch controls are not in here. They are in the root, in a
## Screen.W x Screen.H frame at a whole stretch factor, exactly as before, so
## their size and positions are what they always were.
func _setup_world_view() -> void:
	world_viewport.size = Display.render_texels()
	_world_region = AtlasTexture.new()
	_world_region.atlas = world_viewport.get_texture()
	world_view.texture = _world_region
	world_view.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	_world_mat = ShaderMaterial.new()
	_world_mat.shader = WORLD_SHADER
	world_view.material = _world_mat
	_show_view(Display.view_size())

## World units the display is showing right now: the camera's, while there is
## one (its view eases out to a boss arena and back), else the explore view.
func shown_view_size() -> Vector2:
	return _view_size

func _show_view(v: Vector2) -> void:
	_view_size = v
	var t := v * float(Display.art_scale())
	_world_region.region = Rect2(Vector2.ZERO, t)
	_world_mat.set_shader_parameter("region", Vector4(0.0, 0.0, t.x, t.y))
	_layout_world_view()

func _layout_world_view() -> void:
	var r := Display.world_display_for(Screen.ui_size(get_viewport()), _view_size)
	world_view.position = r.position
	world_view.size = r.size

## Where the world is drawn in the root viewport, in logical pixels.
func world_display_rect() -> Rect2:
	return Rect2(world_view.position, world_view.size)

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
	var cam := world_viewport.get_camera_2d() as CameraController
	var v := cam.view_size() if cam != null and cam.world != null else Display.view_size()
	if cam == null:
		# A scene with no camera (the title, the victory screen) is a whole
		# Screen.W x Screen.H picture laid out in world units: show all of it,
		# at the art's density, as a camera's zoom would.
		v = Display.max_view_size()
		var k := float(Display.art_scale())
		world_viewport.canvas_transform = Transform2D(0.0, Vector2(k, k), 0.0, Vector2.ZERO)
	if v != _view_size:
		_show_view(v)
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

## Quantised to FADE_STEPS discrete bands rather than a smooth ramp — a
## dither-threshold dissolve read as 4 frames, the same vocabulary as any
## other "4-frame" one-shot in the game (see fade_dissolve.gdshader).
func _set_fade_progress(p: float) -> void:
	var mat := fade.material as ShaderMaterial
	if mat != null:
		mat.set_shader_parameter("progress",
			floor(clampf(p, 0.0, 1.0) * float(FADE_STEPS)) / float(FADE_STEPS))

## Every scene arrives out of black. Cheap, and it hides the one-frame pop while
## a level builds its tile layers. `fade.color` stays flat opaque black for the
## whole transition now — the shader owns the reveal, dissolving it in rather
## than blending it out.
func _transition_in(duration: float = 0.22) -> void:
	fade.color = Color(0, 0, 0, 1)
	_set_fade_progress(0.0)
	var t := create_tween()
	t.set_pause_mode(Tween.TWEEN_PAUSE_PROCESS)
	t.tween_method(_set_fade_progress, 0.0, 1.0, duration)

## Static caches (the bitmap font texture, the tile flag table) are not owned by
## the tree, so they have to be dropped explicitly or the engine reports them as
## leaked at exit.
func _exit_tree() -> void:
	PixelFont.release()
	Display.release()
	TileData4.release()
	TileAnim.release()

func current_scene() -> Node:
	return _current

## Short fade used between screens. Awaited by callers that care.
func flash_fade(duration: float = 0.25) -> void:
	fade.color = Color(0, 0, 0, 1)
	_set_fade_progress(0.0)
	var t := create_tween()
	t.tween_method(_set_fade_progress, 0.0, 1.0, duration)
	await t.finished
