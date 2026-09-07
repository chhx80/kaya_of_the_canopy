class_name WeaponBase
extends RefCounted
## A weapon owns its cooldown and decides what a press of Attack spawns.
## Config comes from data/weapons/<id>.json.

var cfg: Dictionary = {}
var id := ""
var cooldown := 0.25
var _cd := 0.0
var ammo := -1            ## -1 = unlimited

static func load_weapon(weapon_id: String) -> WeaponBase:
	var path := "res://data/weapons/%s.json" % weapon_id
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("Weapon: missing %s" % path)
		return null
	var d: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(d) != TYPE_DICTIONARY:
		return null
	var script_path := "res://src/player/weapons/%s.gd" % weapon_id
	var w: WeaponBase = (load(script_path) as GDScript).new() if ResourceLoader.exists(script_path) \
		else WeaponBase.new()
	w.configure(d)
	return w

func configure(d: Dictionary) -> void:
	cfg = d
	id = String(d.get("id", ""))
	cooldown = float(d.get("cooldown", 0.25))
	ammo = int(d.get("ammo", -1))

func tick(delta: float) -> void:
	_cd = maxf(0.0, _cd - delta)

func ready_to_fire(_p: Player) -> bool:
	return _cd <= 0.0 and (ammo != 0)

func try_attack(p: Player) -> bool:
	if not ready_to_fire(p):
		return false
	if not fire(p):
		return false
	_cd = cooldown
	if ammo > 0:
		ammo -= 1
	return true

## Returns true if something was actually spawned.
func fire(_p: Player) -> bool:
	return false

func display_name() -> String:
	return String(cfg.get("display_name", id.to_upper()))
