extends Node2D
## The overworld hub: a top-down map of gateways into the levels.
## Screen-flips like a level, but nothing here can hurt you.

const HUB_ID := "hub"

var def: LevelLoader.LevelDef = null
var world: TileWorld = null
var player: HubPlayer = null
var doors: Array[HubDoor] = []
var _near: HubDoor = null
var _entering := false
var _spawn_door := ""

@onready var tiles_bg: TileRenderer = $TilesBg
@onready var tiles_fg: TileRenderer = $TilesFg
@onready var entities: Node2D = $Entities
@onready var cam: CameraController = $Camera
@onready var overlay: Control = $Ui/Overlay

func _ready() -> void:
	overlay.draw.connect(_draw_overlay)
	_load()
	AudioManager.music("hub")

func place_at_door(level_id: String) -> void:
	_spawn_door = level_id
	if player != null:
		_move_player_to_door(level_id)

func _load() -> void:
	def = LevelLoader.load_level(HUB_ID)
	if not def.ok():
		for e in def.errors:
			push_error("Hub: %s" % e)
		return
	world = def.world
	tiles_bg.setup(world, "bg")
	tiles_fg.setup(world, "fg")
	tiles_bg.modulate_color = Color(0.9, 0.94, 0.9)

	for e: Dictionary in def.entities:
		var p := Vector2(float(e["px"]), float(e["py"]))
		match String(e["type"]):
			"player_spawn":
				player = HubPlayer.new()
				player.world = world
				player.level = self
				entities.add_child(player)
				player.pos = p + Vector2(3, 5)
			"hub_door":
				var d := HubDoor.new()
				d.hub = self
				d.setup(p, e)
				entities.add_child(d)
				doors.append(d)
	if player == null:
		push_error("Hub: levels/hub.json has no player_spawn")
		return
	if _spawn_door != "":
		_move_player_to_door(_spawn_door)
	cam.setup(world, player)
	cam.screen_changed.connect(_on_screen_changed)
	_on_screen_changed(cam.screen)

func _move_player_to_door(level_id: String) -> void:
	for d in doors:
		if d.level_id == level_id:
			player.pos = d.pos + Vector2(3, 20)
			if cam != null:
				cam.snap_to_target()
			return

func _on_screen_changed(_s: Vector2i) -> void:
	var r := cam.view_rect()
	tiles_bg.set_view(r)
	tiles_fg.set_view(r)

func _physics_process(_delta: float) -> void:
	if player == null or _entering:
		return
	_near = null
	for d in doors:
		if d.aabb().grow(6.0).intersects(player.aabb()):
			_near = d
			break
	overlay.queue_redraw()
	# Deliberately a discrete press, not a hold: walking onto a gateway should
	# show you where it goes, not yank you into it.
	if _near != null and player.input.jump_pressed and not _entering:
		_try_enter(_near)

func _try_enter(d: HubDoor) -> void:
	if not d.unlocked():
		AudioManager.play("locked")
		return
	_entering = true
	player.control_enabled = false
	AudioManager.play("enter")
	Game.goto_level(d.level_id)

func _draw_overlay() -> void:
	var W := float(Screen.W)
	PixelFont.draw_shadowed(overlay, Vector2(4, 4), "THE CANOPY", Color(0.85, 0.95, 0.8))
	PixelFont.draw(overlay, Vector2(4, Screen.H - 12),
		"CLEARED %d/%d" % [_cleared(), doors.size()], Color(0.7, 0.78, 0.68))
	PixelFont.draw(overlay, Vector2(W - 4 - PixelFont.width("SCORE %06d" % Game.score, 1, 0), 4),
		"SCORE %06d" % Game.score, Color(0.96, 0.86, 0.4))
	if _near == null:
		return
	var label := _near.display_name
	var sub := "PRESS JUMP TO ENTER"
	if _near.completed():
		sub = "CLEARED - PRESS JUMP TO REPLAY"
	elif not _near.unlocked():
		sub = "LOCKED"
	var w: float = maxf(PixelFont.width(label, 1, 1), PixelFont.width(sub, 1, 0)) + 16.0
	overlay.draw_rect(Rect2(Vector2((W - w) * 0.5, 186), Vector2(w, 30)),
		Color(0.05, 0.06, 0.09, 0.8))
	PixelFont.draw_centered(overlay, W * 0.5, 191.0, label, Color(1, 0.9, 0.45), 1, 1)
	PixelFont.draw_centered(overlay, W * 0.5, 203.0, sub,
		Color(0.85, 0.88, 0.82) if _near.unlocked() else Color(0.75, 0.4, 0.35), 1, 0)

func _cleared() -> int:
	var n := 0
	for d in doors:
		if d.completed():
			n += 1
	return n
