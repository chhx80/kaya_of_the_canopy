extends WeaponBase
## The signature weapon: one blade in flight at a time, and you only get it back
## by catching it. Missing the catch is the cost of a bad throw.

var _in_flight: Array = []

func ready_to_fire(_p: Player) -> bool:
	_in_flight = _in_flight.filter(func(n: Node) -> bool: return is_instance_valid(n))
	return _cd <= 0.0 and _in_flight.size() < int(cfg.get("max_in_flight", 1))

func fire(p: Player) -> bool:
	if p.level == null:
		return false
	var blade: Blade = (load("res://src/player/weapons/blade.gd") as GDScript).new()
	blade.setup(cfg, p)
	p.level.entities.add_child(blade)
	_in_flight.append(blade)
	AudioManager.play("throw")
	return true
