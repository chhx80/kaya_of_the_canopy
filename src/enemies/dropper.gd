extends Enemy
## THE HOLLOW TICK — clings to a ceiling, drops on whatever walks under it.
##
## A falling enemy is the cheapest unavoidable hit in a platformer, so this one
## shivers for `wind_up` seconds before it lets go. Walking speed being what it
## is, that is the difference between "you were warned" and "you were standing
## in the wrong tile".
##
## What it does on impact is data, not code: `land_action` is `"walk"` (it
## crawls off like a beetle and stays a threat) or `"die"` (it bursts, and is
## purely a trap). Both are used — the first fills a corridor, the second is a
## one-shot ambush you can bait.
##
## It does not need a solid tile above it. The level places it and it hangs
## there; `_ready()` only lifts it from the *bottom* of its authored tile to
## the *top*, because src/world/level.gd sits every enemy on its tile and a
## ceiling-clinger belongs against the one above.

enum St { CLING, TELL, FALL, WALK }

var st: St = St.CLING
var t := 0.0
var _turn_cooldown := 0.0

func _ready() -> void:
	super._ready()
	pos.y -= float(TileData4.TILE_SIZE) - box.y
	spawn_pos = pos
	_sync_render_position()

func on_respawn() -> void:
	st = St.CLING
	t = 0.0
	_turn_cooldown = 0.0
	set_anim("cling")

func think(delta: float) -> void:
	t = maxf(0.0, t - delta)
	_turn_cooldown = maxf(0.0, _turn_cooldown - delta)
	match st:
		St.CLING:
			_cling()
		St.TELL:
			_tell()
		St.FALL:
			_fall(delta)
		St.WALK:
			_walk(delta)

# ---------------------------------------------------------------- states
## No gravity while it holds on. A blade hit knocks `vel.x` sideways in
## Enemy.hurt(); zeroing here is what keeps a wounded tick on its ceiling.
func _cling() -> void:
	vel = Vector2.ZERO
	set_anim("cling")
	if player_underneath():
		st = St.TELL
		t = float(cfg.get("wind_up", 0.45))
		set_anim("tell")
		AudioManager.play(String(cfg.get("sfx_tell", "blip")))

## Unconditional, like the boar's: stepping back out from under it does not
## put the tick back to sleep, so the tell always means the same thing.
func _tell() -> void:
	vel = Vector2.ZERO
	set_anim("tell")
	if t <= 0.0:
		st = St.FALL
		set_anim("fall")

func _fall(delta: float) -> void:
	apply_gravity(delta)
	vel.x = 0.0
	set_anim("fall")
	if on_floor:
		_land()

func _land() -> void:
	AudioManager.play(String(cfg.get("sfx_land", "land")))
	Fx.burst(String(cfg.get("land_fx", "dust")), feet(), Vector2.UP)
	if String(cfg.get("land_action", "walk")) == "die":
		die(center())
		return
	st = St.WALK
	set_anim("walk")

func _walk(delta: float) -> void:
	apply_gravity(delta)
	set_anim("walk")
	if on_floor and _turn_cooldown <= 0.0:
		var blocked := against_wall == facing
		var ledge := bool(cfg.get("turn_at_ledge", true)) \
			and not ground_ahead(facing, float(cfg.get("ledge_lookahead", 2.0)))
		if blocked or ledge:
			facing = -facing
			_turn_cooldown = float(cfg.get("turn_cooldown", 0.15))
	vel.x = speed * facing

# ---------------------------------------------------------------- trigger
## Below, and inside a column `trigger_width` pixels either side of the tick.
## `trigger_depth` stops one on the roof of a tall shaft reacting to a player
## four screens down that it could never reach.
func player_underneath() -> bool:
	var p := player()
	if p == null or p.dead:
		return false
	var d := p.center() - center()
	if absf(d.x) > float(cfg.get("trigger_width", 14.0)):
		return false
	return d.y > 0.0 and d.y <= float(cfg.get("trigger_depth", 112.0))
