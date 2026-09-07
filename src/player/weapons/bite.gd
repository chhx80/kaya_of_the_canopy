extends WeaponBase
## The fish's short-range snap. Spawns a hitbox just in front of the mouth for
## a few frames instead of a projectile.

func fire(p: Player) -> bool:
	if p.level == null:
		return false
	var hit: MeleeHit = (load("res://src/player/weapons/melee_hit.gd") as GDScript).new()
	hit.setup(cfg, p)
	p.level.entities.add_child(hit)
	AudioManager.play("bite")
	return true
