extends SceneTree
## THROWAWAY. Render proof for tests/fixtures/nest_probe.json, and the demo of
## what a switch gate looks like in each of its two configurations. The World 3
## and World 4 twins are tools/_probe_shot_heights.gd and _probe_shot_deeps.gd.
##
## tools/shot.sh can only reach a scenario, and `level:<id>` resolves through
## LevelLoader.load_level() -> res://levels/<id>.json. A probe deliberately does
## not live in levels/, so there is no scenario that can show it.
##
##   $GODOT --path . --rendering-driver opengl3 --resolution 400x240 \
##       --script res://tools/_probe_shot_nest.gd -- --mode=lit
##
## --mode=lit      the probe in its SEED configuration: group 1 on, group 2 off,
##                 so the 'A' gate at column 8 is a wall, the 'a' bypass over the
##                 top is a hole, and the 'b' half of the lid over the pool is
##                 the solid one. This is frame one of any World 5 level.
## --mode=thrown   both levers thrown. Every one of those four facts inverts, and
##                 nothing else in the screen moves.
##
## Everything is reached through load() inside _initialize(): a static reference
## makes Godot compile the whole dependency graph while this file is loading,
## which is before the autoload names exist. Delete after capturing; it is not
## part of the toolchain.

const FIXTURE := "res://tests/fixtures/nest_probe.json"
const TS := 16.0

class Shooter extends Node:
	var out := ""
	func _ready() -> void:
		for _i in 4:
			await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		var err := img.save_png(out)
		print("[capture] %s (%dx%d) err=%d" % [out, img.get_width(), img.get_height(), err])
		get_tree().quit(0 if err == OK else 1)

func _initialize() -> void:
	var mode := "lit"
	var out := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--mode="):
			mode = a.substr(7)
		elif a.begins_with("--out="):
			out = a.substr(6)
	if out == "":
		out = {"lit": "shots/world_nest_probe.png",
			"thrown": "shots/_m5_probe_thrown.png"}.get(mode, "shots/world_nest_probe.png")

	var LL: GDScript = load("res://src/world/level_loader.gd")
	var def: Object = LL.load_path(FIXTURE, "nest_probe")
	if not def.ok():
		printerr("probe failed to load: %s" % ", ".join(def.errors))
		quit(1)
		return
	var world: Object = def.world
	var view := Rect2(0, 0, 400, 240)

	var holder := Node2D.new()
	root.add_child(holder)

	var PB: GDScript = load("res://src/world/parallax_bg.gd")
	for plane: Array in [["sky", 0.10], ["far", 0.28], ["near", 0.58]]:
		var path := "res://assets/sprites/bg_obsidian_%s.png" % String(plane[0])
		if not ResourceLoader.exists(path):
			printerr("no backdrop at %s" % path)
			continue
		var p: Node = PB.new()
		holder.add_child(p)
		p.setup(path, float(plane[1]), 0.0)
		p.set_view(view)

	# The levers first: SwitchTrigger._ready() writes the world's switch state,
	# and the tile renderers below pick their art off world.is_solid(). The real
	# node, at the real offset Level._spawn_entity() uses, so the sprite in the
	# capture is the one the game draws. `thrown` flips the state each lever
	# starts in, which is the same world `toggle()` would leave behind.
	var ST: GDScript = load("res://src/world/triggers/switch_trigger.gd")
	var thrown := mode == "thrown"
	var levers: Array[Node] = []
	for spec: Array in [[Vector2(5, 12), 1, true], [Vector2(21, 12), 2, false]]:
		var sw: Node2D = ST.new()
		sw.world = world
		var starts_on := bool(spec[2]) != thrown
		# setup() before add_child(): _ready() is what writes the world's switch
		# state and builds the sprite, and it must see the real pos and group.
		sw.setup((spec[0] as Vector2) * TS + Vector2(1, 6), int(spec[1]), starts_on)
		# SwitchTrigger._ready() is what normally writes this, but _ready() is
		# DEFERRED for anything added during _initialize() — so the world would
		# still be in its seed state when the lines below print it. Same call,
		# same order, just early; _ready() repeats it harmlessly.
		world.set_switch(int(spec[1]), starts_on)
		holder.add_child(sw)
		sw.set_physics_process(false)          # _physics_process() reads `Game`
		levers.append(sw)
		print("  lever group %d: %s" % [int(spec[1]), "ON" if starts_on else "OFF"])
	print("  (8,12) 'A' gate solid=%s   (10,9) 'a' bypass solid=%s"
		% [world.is_solid(8, 12), world.is_solid(10, 9)])
	print("  (20,10) 'B' solid=%s   (21,10) 'b' solid=%s"
		% [world.is_solid(20, 10), world.is_solid(21, 10)])

	var TR: GDScript = load("res://src/world/tile_renderer.gd")
	for layer: String in ["bg", "fg"]:
		var r: Node = TR.new()
		holder.add_child(r)
		r.setup(world, layer)
		r.set_view(view)
	# The levers are entities and are drawn after the tiles in a real Level.
	for sw: Node in levers:
		holder.move_child(sw, holder.get_child_count() - 1)

	var s := Shooter.new()
	s.out = out
	root.add_child(s)
