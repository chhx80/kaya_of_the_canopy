class_name TestCase
extends RefCounted
## Minimal assertion base. Every `test_*` method on a subclass is run by
## tests/run_tests.gd. We roll our own instead of pulling in GUT so the suite
## has zero third-party surface and runs in a plain headless Godot.

var failures: Array[String] = []
var checks := 0

func before_each() -> void:
	pass

func after_each() -> void:
	pass

func _fail(msg: String) -> void:
	failures.append(msg)

func ok(cond: bool, msg: String = "") -> void:
	checks += 1
	if not cond:
		_fail("expected true — %s" % msg)

func not_ok(cond: bool, msg: String = "") -> void:
	checks += 1
	if cond:
		_fail("expected false — %s" % msg)

func eq(a: Variant, b: Variant, msg: String = "") -> void:
	checks += 1
	if a != b:
		_fail("expected %s == %s — %s" % [str(a), str(b), msg])

func ne(a: Variant, b: Variant, msg: String = "") -> void:
	checks += 1
	if a == b:
		_fail("expected %s != %s — %s" % [str(a), str(b), msg])

func near(a: float, b: float, tol: float = 0.001, msg: String = "") -> void:
	checks += 1
	if absf(a - b) > tol:
		_fail("expected %f ~= %f (tol %f) — %s" % [a, b, tol, msg])

func gt(a: float, b: float, msg: String = "") -> void:
	checks += 1
	if not (a > b):
		_fail("expected %f > %f — %s" % [a, b, msg])

func lt(a: float, b: float, msg: String = "") -> void:
	checks += 1
	if not (a < b):
		_fail("expected %f < %f — %s" % [a, b, msg])

func has(container: Variant, item: Variant, msg: String = "") -> void:
	checks += 1
	if not (item in container):
		_fail("expected %s to contain %s — %s" % [str(container), str(item), msg])
