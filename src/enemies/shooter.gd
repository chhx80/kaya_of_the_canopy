extends Enemy
## Rooted bloom. Waits until the player is roughly level with it and within
## range, telegraphs, then spits.

enum St { IDLE, WINDUP }

var st: St = St.IDLE
var t := 0.0
var _aim := Vector2.RIGHT

func on_configured() -> void:
	gravity = 0.0

func on_respawn() -> void:
	st = St.IDLE
	t = float(cfg.get("fire_interval", 1.7))
	set_anim("idle")

func _ready() -> void:
	super._ready()
	t = float(cfg.get("fire_interval", 1.7))

func think(delta: float) -> void:
	vel = Vector2.ZERO
	t = maxf(0.0, t - delta)
	var p := player()
	match st:
		St.IDLE:
			set_anim("idle")
			if p == null or p.dead:
				return
			var d := p.center() - center()
			if absf(d.x) > float(cfg.get("sight_range", 168.0)):
				return
			if absf(d.y) > float(cfg.get("sight_band", 26.0)):
				return
			facing = 1 if d.x > 0.0 else -1
			if t <= 0.0:
				st = St.WINDUP
				t = float(cfg.get("wind_up", 0.45))
				_aim = d.normalized()
		St.WINDUP:
			set_anim("windup")
			if t <= 0.0:
				_shoot()
				st = St.IDLE
				t = float(cfg.get("fire_interval", 1.7))

func _shoot() -> void:
	if level == null:
		return
	var shot := Projectile.new()
	shot.setup(cfg.get("projectile", {}), center() + _aim * 9.0, _aim, world, level)
	level.entities.add_child(shot)
	AudioManager.play("spit")
