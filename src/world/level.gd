extends Node2D
## A playing level: tile layers, parallax, entities, camera and HUD.

signal level_ready()

## Three planes, three speeds. The gaps between them are what the eye reads as
## distance; the art in each plane is painted to a contrast budget that matches
## its speed (tools/art/backdrops.py). Vertical parallax is deliberately zero on
## all three — see ParallaxBg.
const PARALLAX_SKY := 0.10
const PARALLAX_FAR := 0.28
const PARALLAX_NEAR := 0.58

var def: LevelLoader.LevelDef = null
var world: TileWorld = null
var player: Player = null

@onready var bg_far: ParallaxBg = $BgFar
@onready var bg_near: ParallaxBg = $BgNear
## Built in code rather than in level.tscn: the scene predates phase 3 and the
## three ambience layers have to be inserted at exact depths between nodes that
## are already there.
var bg_sky: ParallaxBg = null
var air: AmbienceLayer = null
var shade: AmbienceLayer = null
var lights: AmbienceLayer = null
var amb: Ambience = null
@onready var tiles_bg: TileRenderer = $TilesBg
@onready var tiles_fg: TileRenderer = $TilesFg
@onready var entities: Node2D = $Entities
@onready var particles: ParticleField = $Particles
@onready var cam: CameraController = $Camera

var hud: Node = null
var boss: Enemy = null
var _restarting := false

func _ready() -> void:
	bg_sky = ParallaxBg.new()
	bg_sky.name = "BgSky"
	add_child(bg_sky)
	move_child(bg_sky, 0)
	air = _make_layer("Air", AmbienceLayer.Role.AIR, bg_near.get_index() + 1)
	shade = _make_layer("Shade", AmbienceLayer.Role.SHADE, tiles_fg.get_index() + 1)
	lights = _make_layer("Lights", AmbienceLayer.Role.LIGHT, shade.get_index() + 1)

func _make_layer(n: String, role: AmbienceLayer.Role, at: int) -> AmbienceLayer:
	var l := AmbienceLayer.new()
	l.name = n
	l.role = role
	add_child(l)
	move_child(l, at)
	return l

## Backdrop planes and tile tints, from data/ambience.json. Missing art leaves
## the plane empty rather than erroring: a level still plays with no backdrop.
func _apply_ambience() -> void:
	amb = Ambience.for_level(def.id)
	var planes := {
		bg_sky: ["sky", PARALLAX_SKY], bg_far: ["far", PARALLAX_FAR],
		bg_near: ["near", PARALLAX_NEAR],
	}
	for node: ParallaxBg in planes.keys():
		var spec: Array = planes[node]
		var path := "res://assets/sprites/bg_%s_%s.png" % [amb.world, String(spec[0])]
		if ResourceLoader.exists(path):
			node.setup(path, float(spec[1]), 0.0)
		else:
			push_warning("Level: no backdrop plane at '%s'" % path)
	tiles_bg.modulate_color = amb.bg_tint
	tiles_fg.modulate_color = amb.fg_tint
	for l: AmbienceLayer in [air, shade, lights]:
		l.setup(l.role, amb, world)

func load_level(id: String) -> void:
	def = LevelLoader.load_level(id)
	if not def.ok():
		for e in def.errors:
			push_error("Level: %s" % e)
		return
	world = def.world
	tiles_bg.setup(world, "bg")
	tiles_fg.setup(world, "fg")
	_apply_ambience()

	_spawn_entities()
	if player == null:
		push_error("Level: no player spawned")
		return

	cam.setup(world, player)
	# Juice is wired up once the camera and the particle layer both exist. If
	# either half of it fails to load the level plays on without it.
	Fx.attach(particles, cam)
	cam.screen_changed.connect(_on_screen_changed)
	_on_screen_changed(cam.screen)

	hud = load("res://src/ui/hud.tscn").instantiate()
	Game.main.ui.add_child(hud)
	if hud.has_method("set_level_name"):
		hud.set_level_name(def.display_name)

	if def.music != "":
		AudioManager.music(def.music)
	Game.sim_paused = false
	level_ready.emit()

func _exit_tree() -> void:
	Fx.detach(particles)
	if hud != null and is_instance_valid(hud):
		hud.queue_free()

func _spawn_entities() -> void:
	for e: Dictionary in def.entities:
		spawn_entity(e)

## Central factory. New entity types are registered here and nowhere else.
func spawn_entity(e: Dictionary) -> Node:
	var type := String(e.get("type", ""))
	var p := Vector2(float(e.get("px", 0.0)), float(e.get("py", 0.0)))
	match type:
		"player_spawn":
			player = (load("res://src/player/player.tscn") as PackedScene).instantiate()
			player.world = world
			player.level = self
			entities.add_child(player)
			player.pos = Vector2(p.x + 3.0, p.y + 16.0 - player.box.y)
			player.died.connect(_on_player_died)
			return player
		"boss_exit":
			# Placed only once the boss dies — see on_boss_defeated().
			return null
		_:
			var node := _spawn_gameplay_entity(type, p, e)
			if node == null:
				push_warning("Level: unknown entity type '%s'" % type)
			return node

func _spawn_gameplay_entity(type: String, p: Vector2, e: Dictionary) -> Node:
	match type:
		"enemy_walker", "enemy_jumper", "enemy_shooter", "enemy_swimmer":
			return _spawn_enemy(type.substr(6), p, e)
		"boss_grove":
			boss = _spawn_enemy(type, p, e)
			return boss
		"gem", "heart", "key_yellow", "key_red", "key_cyan":
			var pu := Pickup.new()
			pu.setup(type, p + Vector2(2, 2), bool(e.get("from_drop", false)))
			pu.world = world
			pu.level = self
			entities.add_child(pu)
			return pu
		"door_yellow", "door_red", "door_cyan":
			var dr := Door.new()
			dr.world = world
			dr.level = self
			dr.setup(p, type.substr(5))
			entities.add_child(dr)
			tiles_fg.queue_redraw()
			return dr
		"switch_a", "switch_b":
			var sw := SwitchTrigger.new()
			sw.world = world
			sw.level = self
			sw.setup(p + Vector2(1, 6), 1 if type.ends_with("a") else 2,
				bool(e.get("on", type.ends_with("a"))))
			entities.add_child(sw)
			tiles_fg.queue_redraw()
			return sw
		"pad_frog", "pad_fish", "pad_bird", "pad_human":
			var pad := TransformPad.new()
			pad.level = self
			pad.setup(p + Vector2(0, 8), type.substr(4))
			entities.add_child(pad)
			return pad
		"exit":
			var ex := LevelExit.new()
			ex.setup(p)
			ex.level = self
			entities.add_child(ex)
			return ex
	return null

func _spawn_enemy(id: String, p: Vector2, e: Dictionary) -> Enemy:
	var script_path := "res://src/enemies/%s.gd" % id
	if not ResourceLoader.exists(script_path):
		push_warning("Level: no script for enemy '%s'" % id)
		return null
	var en: Enemy = (load(script_path) as GDScript).new()
	en.world = world
	en.level = self
	en.configure(id, e)
	# Entities are placed by their top-left tile; sit the enemy on that tile.
	en.pos = Vector2(p.x + (16.0 - en.box.x) * 0.5, p.y + 16.0 - en.box.y)
	entities.add_child(en)
	return en

## Called by the blade when a crate shatters, so the tile layer redraws.
func on_tile_broken(_t: Vector2i) -> void:
	tiles_fg.queue_redraw()

## Switch blocks change solidity, so the layer has to be repainted.
func on_switch_toggled(_group: int) -> void:
	tiles_fg.queue_redraw()

## Beating the boss opens the way out rather than ending the level outright, so
## the player still gets to walk through the gate.
func on_boss_defeated(fallen: Enemy) -> void:
	cam.locked = false
	AudioManager.play("boss_die")
	if hud != null and hud.has_method("flash_message"):
		hud.flash_message("THE WARDEN FALLS", 2.4)
	for e: Dictionary in def.entities:
		if String(e.get("type", "")) == "boss_exit":
			var open_at := e.duplicate()
			open_at["type"] = "exit"
			spawn_entity(open_at)
			return
	# No dedicated gate authored: drop one where the boss stood.
	spawn_entity({"type": "exit", "px": fallen.pos.x, "py": fallen.pos.y})

func _on_screen_changed(s: Vector2i) -> void:
	# A live boss locks the camera to its arena.
	cam.locked = boss != null and is_instance_valid(boss) and not boss.defeated \
		and s == boss.home_screen
	for n in get_tree().get_nodes_in_group(&"enemies"):
		var e := n as Enemy
		if e != null and e.level == self:
			e.set_active_screen(s)
	var r := cam.view_rect()
	tiles_bg.set_view(r)
	tiles_fg.set_view(r)
	bg_sky.set_view(r)
	bg_far.set_view(r)
	bg_near.set_view(r)
	air.set_view(r)
	shade.set_view(r)
	lights.set_view(r)

func _process(delta: float) -> void:
	if cam == null or world == null:
		return
	# One clock for both tile layers, so the two never drift out of phase. It
	# stops with the simulation, which is what makes hitstop freeze the water
	# as well as the fight.
	if not Game.sim_paused:
		TileAnim.shared().advance(delta)
	# In smooth-scroll mode the view changes every frame; in flip mode the
	# screen_changed signal already covers it.
	if not cam.flip_mode:
		_on_screen_changed(cam.screen)

func _on_player_died() -> void:
	if _restarting:
		return
	_restarting = true
	await get_tree().create_timer(0.9).timeout
	Game.lose_life()

## Used only by tools/seq capture scripts, so a screenshot can show the state
## after a key is collected without simulating the whole route to it.
func debug_make_fish() -> void:
	if player != null:
		player.set_form("fish")

func debug_give_yellow_key() -> void:
	Game.add_key("yellow")

## Likewise: puts the nearest enemy down on the spot, so a capture can show the
## death scatter and the hitstop without first staging a two-throw fight.
func debug_kill_nearest_enemy() -> void:
	if player == null:
		return
	var nearest: Enemy = null
	var best := INF
	for n in get_tree().get_nodes_in_group(&"enemies"):
		var e := n as Enemy
		if e == null or e.level != self:
			continue
		var d := e.center().distance_to(player.center())
		if d < best:
			best = d
			nearest = e
	if nearest != null:
		nearest.hurt(nearest.health, nearest.center())

## And again. Phase 4 of the art overhaul gave the Warden three distinct bodies
## rather than three tints, and a screenshot has to be able to show all three.
## Its phases are health thresholds, so this drops it onto the next one instead
## of asking the capture harness to stage six minutes of fight.
func debug_advance_boss_phase() -> void:
	for n in get_tree().get_nodes_in_group(&"bosses"):
		var b := n as Enemy
		if b == null or b.level != self:
			continue
		var phases: Array = b.cfg.get("phases", [])
		var cur := int(b.get("phase"))
		if cur + 1 >= phases.size():
			continue
		var target := int((phases[cur] as Dictionary).get("until_health", 0))
		b.hurt(maxi(1, b.health - target), b.center() + Vector2(48.0, 0.0))

## And again: fires the slam shake on demand. The Warden's own slam is on a
## timer the capture harness cannot see, and one frame either side of it the
## offset rounds to nothing — so a screenshot of the shake asks for it directly.
## This is the same call the boss makes in boss_grove.gd.
func debug_shake_boss_slam() -> void:
	Fx.shake("boss_slam")

func complete() -> void:
	if _restarting:
		return
	_restarting = true
	AudioManager.play("level_clear")
	Game.complete_level(def.id)
