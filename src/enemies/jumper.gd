extends Enemy
## idle -> wind-up -> leap toward the player -> land -> cooldown.

enum St { IDLE, WINDUP, AIR, COOLDOWN }

var st: St = St.IDLE
var t := 0.0

func on_respawn() -> void:
	st = St.IDLE
	t = 0.0
	set_anim("idle")

func think(delta: float) -> void:
	apply_gravity(delta)
	t = maxf(0.0, t - delta)
	var p := player()
	match st:
		St.IDLE:
			vel.x = move_toward(vel.x, 0.0, 400.0 * delta)
			set_anim("idle")
			if p != null and not p.dead \
					and center().distance_to(p.center()) < float(cfg.get("trigger_range", 132.0)) \
					and on_floor:
				facing = 1 if p.center().x > center().x else -1
				st = St.WINDUP
				t = float(cfg.get("wind_up", 0.42))
		St.WINDUP:
			vel.x = 0.0
			set_anim("windup")
			if t <= 0.0:
				vel.y = float(cfg.get("jump_vel", -230.0))
				vel.x = float(cfg.get("jump_hspeed", 62.0)) * facing
				st = St.AIR
				AudioManager.play("hop")
		St.AIR:
			set_anim("air")
			if against_wall != 0:
				vel.x = 0.0
			if on_floor and vel.y >= 0.0:
				st = St.COOLDOWN
				t = float(cfg.get("cooldown", 0.85))
		St.COOLDOWN:
			vel.x = move_toward(vel.x, 0.0, 500.0 * delta)
			set_anim("idle")
			if t <= 0.0:
				st = St.IDLE
