extends Node
## Proof-of-render for the three new enemies, because "the tests pass" and
## "it draws" are different claims and only one of them is checkable by eye.
##
## `tools/shot.sh` drives the real game against a level on disk, and no level
## in `levels/` places these three yet. So this boots the arena and authors one
## of each into it — through `Level.spawn_entity()`, the same entity dictionary
## a level file would carry — then poses them: the boar mid-charge, the tick
## hanging, the wasp in flight. What it captures is therefore the registry
## working, not three nodes assembled beside it.
##
## Needs a window: the frames it captures do not exist under --headless.
##
##   KAYA_V2_MODE=shot $GODOT --path . --rendering-driver opengl3 \
##       --resolution 1200x720 res://tests/integration/enemies_v2_runner.tscn
##
## Writes shots/enemies_v2.png.

const ARENA := "test_arena"
const TS := 16.0
const OUT := "shots/enemies_v2.png"

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	call_deferred("run")

func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame

## One authored entity, in the shape LevelLoader.from_dict() emits, through the
## level's own factory.
func author(level: Node, type: String, tx: int, ty: int) -> Enemy:
	var n: Node = level.spawn_entity({
		"type": type, "x": tx, "y": ty,
		"px": float(tx) * TS, "py": float(ty) * TS,
	})
	if n is Enemy:
		(n as Enemy).contact_damage = 0
	return n as Enemy

func run() -> void:
	Game.reset_run()
	Game.goto_level(ARENA)
	await frames(6)
	var level: Node = Game.current_level
	for n in get_tree().get_nodes_in_group(&"enemies"):
		var old := n as Enemy
		old.remove_from_group(&"enemies")
		old.queue_free()
	await frames(2)

	# Kaya on the left, out of everyone's trigger, so the poses stay put. No
	# invulnerability: src/player/player.gd blinks the sprite while `invuln`
	# is set, and half the frames of a blink are an empty screenshot.
	var p: Player = level.player
	p.pos = Vector2(4.0 * TS, 10.0 * TS)
	p.vel = Vector2.ZERO
	level.cam.snap_to_target()

	# The boar: far enough away that it patrols rather than charging, then
	# forced into its charge pose for the capture.
	var boar: Enemy = author(level, "enemy_charger", 8, 11)
	# The tick: hanging, which is the pose that has to read as upside-down.
	var tick: Enemy = author(level, "enemy_dropper", 13, 3)
	# The wasp: mid-patrol over the one-way platform it ignores.
	var wasp: Enemy = author(level, "enemy_flyer", 17, 6)
	if boar == null or tick == null or wasp == null:
		print("[capture] the level refused an enemy; nothing to shoot")
		get_tree().quit(1)
		return

	await frames(30)
	boar.set_anim("charge")
	await frames(4)

	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var dir := OUT.get_base_dir()
	if dir != "" and not DirAccess.dir_exists_absolute(dir):
		DirAccess.make_dir_recursive_absolute(dir)
	var err := img.save_png(OUT)
	print("[capture] %s (%dx%d) err=%d" % [OUT, img.get_width(), img.get_height(), err])
	get_tree().quit(0 if err == OK else 1)
