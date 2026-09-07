extends Node2D
## A playing level: tile layers, parallax, entities, camera and HUD.

signal level_ready()

const PARALLAX_FAR := 0.25
const PARALLAX_NEAR := 0.55

var def: LevelLoader.LevelDef = null
var world: TileWorld = null
var player: Player = null

@onready var bg_far: ParallaxBg = $BgFar
@onready var bg_near: ParallaxBg = $BgNear
@onready var tiles_bg: TileRenderer = $TilesBg
@onready var tiles_fg: TileRenderer = $TilesFg
@onready var entities: Node2D = $Entities
@onready var cam: CameraController = $Camera

var hud: Node = null
var boss: Enemy = null
var _restarting := false

func _ready() -> void:
	bg_far.setup("res://assets/sprites/bg_far.png", PARALLAX_FAR, 0.0)
	bg_near.setup("res://assets/sprites/bg_near.png", PARALLAX_NEAR, 0.0)
	bg_near.tint = Color(1, 1, 1, 0.9)

func load_level(id: String) -> void:
	def = LevelLoader.load_level(id)
	if not def.ok():
		for e in def.errors:
			push_error("Level: %s" % e)
		return
	world = def.world
	tiles_bg.setup(world, "bg")
	tiles_fg.setup(world, "fg")
	tiles_bg.modulate_color = Color(0.62, 0.66, 0.72)

	_spawn_entities()
	if player == null:
		push_error("Level: no player spawned")
		return

	cam.setup(world, player)
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
	bg_far.set_view(r)
	bg_near.set_view(r)

func _process(_delta: float) -> void:
	if cam == null or world == null:
		return
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

func complete() -> void:
	if _restarting:
		return
	_restarting = true
	AudioManager.play("level_clear")
	Game.complete_level(def.id)
