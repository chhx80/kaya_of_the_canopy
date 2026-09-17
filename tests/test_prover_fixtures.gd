extends TestCase
## The gate's own gate.
##
## Six defects shipped levels that could not be finished, and every one was
## found by a human on a phone rather than by the suite. `tests/fixtures/`
## reproduces all six as tiny levels, and this file asserts the Route Prover
## **fails** every one of them.
##
## If the prover ever passes a fixture, the gate is worthless and twenty levels
## ship broken. These are the assertions to fix first if they ever go red.
##
## Each fixture is paired with a `_fixed` twin that differs by the smallest
## repair that makes the level finishable, and the prover must PASS the twin.
## That pairing is the point. A fixture that fails on its own proves nothing —
## a typo in its route, a misplaced entity or a broken command line would fail
## it just as convincingly. A fixture that fails while a one-tile-different twin
## passes can only be failing for the reason it was built to fail for.
##
## The prover needs autoloads and this tier has none (ADR 003), so each case
## runs `tools/solver/prove.tscn` as a child process and reads its exit code —
## the same code `tools/prove.sh` returns. What is asserted is the outcome of
## the real tool, not a re-implementation of it.

## The hardest twin proves in 84 expansions; the budget is two orders of
## magnitude above that. A broken fixture failing here is never a budget that
## was too mean — measured costs are in REPORT.md.
const BUDGET := 8000

## Fixtures run as child processes, so they run concurrently. Capped rather than
## unbounded: this suite shares a machine.
const LANES := 4

const EXIT_OK := 0
const EXIT_HOP_FAILED := 1
const EXIT_NO_ROUTE := 2

const FIXTURES := [
	"a_vine_no_exit",
	"b_oneway_headroom",
	"c_short_door",
	"d_fish_bank",
	"e_sealed_spawn",
	"f_capped_shaft",
]

## Filled once by `_results()` and reused: twelve prover runs is the expensive
## part of this file, and every test below wants the same twelve.
static var _cache: Dictionary = {}


func _args(fixture: String, extra: PackedStringArray) -> PackedStringArray:
	var args := PackedStringArray([
		"--headless",
		"--path", ProjectSettings.globalize_path("res://"),
		"res://tools/solver/prove.tscn",
		"--",
		"--no-tape",
		"--budget", str(BUDGET),
		"--level-file", "res://tests/fixtures/%s.json" % fixture,
	])
	args.append_array(extra)
	return args


## Run one fixture and wait. Used where the *output* matters, not just the code.
func _prove(fixture: String, extra: PackedStringArray = PackedStringArray()) -> Dictionary:
	var out: Array = []
	var code := OS.execute(OS.get_executable_path(), _args(fixture, extra), out, true)
	return {"code": code, "text": "\n".join(PackedStringArray(out))}


## Run every fixture and twin, `LANES` at a time, and return {name: exit code}.
func _results() -> Dictionary:
	if not _cache.is_empty():
		return _cache
	var queue: Array[String] = []
	for name: String in FIXTURES:
		queue.append(name)
		queue.append(name + "_fixed")
	var running: Array = []        ## [{name, pid}]
	while not queue.is_empty() or not running.is_empty():
		while running.size() < LANES and not queue.is_empty():
			var name: String = queue.pop_front()
			var pid := OS.create_process(OS.get_executable_path(),
				_args(name, PackedStringArray()), false)
			if pid <= 0:
				_cache[name] = -1
				continue
			running.append({"name": name, "pid": pid})
		var still: Array = []
		for r: Dictionary in running:
			if OS.is_process_running(int(r["pid"])):
				still.append(r)
			else:
				_cache[String(r["name"])] = OS.get_process_exit_code(int(r["pid"]))
		running = still
		if not running.is_empty():
			OS.delay_msec(50)
	return _cache


# ------------------------------------------------------------------ the six

func test_the_prover_fails_every_historical_defect() -> void:
	var got := _results()
	for name: String in FIXTURES:
		eq(int(got.get(name, -1)), EXIT_HOP_FAILED,
			"%s reproduces a defect that shipped an unfinishable level. The prover has to fail it; it returned %s. Run: tools/prove.sh --level-file=res://tests/fixtures/%s.json"
				% [name, str(got.get(name, "nothing")), name])


func test_the_repaired_twin_of_every_defect_passes() -> void:
	# The control. Without this, a fixture could be failing for any reason at
	# all and the assertion above would still look green.
	var got := _results()
	for name: String in FIXTURES:
		var twin := name + "_fixed"
		eq(int(got.get(twin, -1)), EXIT_OK,
			"%s is the same level with the defect repaired. If the prover cannot finish it, the failure of %s is not evidence of anything. Run: tools/prove.sh --level-file=res://tests/fixtures/%s.json"
				% [twin, name, twin])


func test_each_failure_names_the_hop_and_how_close_it_got() -> void:
	# A gate that only says "no" costs an afternoon of bisecting. Every failure
	# has to name the hop, the closest approach in pixels and what it spent.
	var r := _prove("c_short_door")
	var text := String(r["text"])
	ok("hop 2/3" in text, "the report should name which hop failed:\n%s" % text)
	ok("key_yellow > door_yellow" in text, "...and its two waypoints:\n%s" % text)
	ok("closest approach" in text, "...and how close it got, in pixels:\n%s" % text)
	ok("expansions" in text, "...and the expansions it spent:\n%s" % text)


# ------------------------------------------------------ silence is not a pass

func test_a_level_that_declares_no_route_fails_the_gate() -> void:
	# ADR 005: "A level with no route fails the gate. Silence is not a pass."
	# g_no_route is a flat, walkable corridor, and it still fails.
	var r := _prove("g_no_route")
	eq(int(r["code"]), EXIT_NO_ROUTE,
		"a level with no declared route must fail with exit 2. Prover said:\n%s" % r["text"])


func test_the_same_level_passes_once_it_declares_its_route() -> void:
	var r := _prove("g_no_route", PackedStringArray(["--route", "spawn>exit:human"]))
	eq(int(r["code"]), EXIT_OK,
		"g_no_route is walkable, so only the missing route should have failed it. Prover said:\n%s"
			% r["text"])


func test_a_route_that_is_not_a_chain_is_rejected() -> void:
	# Hops carry position and velocity across the join, so a route with a gap in
	# it would silently teleport Kaya and the tape would not replay.
	var r := _prove("g_no_route",
		PackedStringArray(["--route", "spawn>exit:human,gem>exit:human"]))
	eq(int(r["code"]), EXIT_NO_ROUTE,
		"a route whose hops do not join up must be rejected. Prover said:\n%s" % r["text"])


func test_a_route_that_does_not_start_at_spawn_is_rejected() -> void:
	var r := _prove("g_no_route", PackedStringArray(["--route", "exit>exit:human"]))
	eq(int(r["code"]), EXIT_NO_ROUTE,
		"a route has to start where Kaya does. Prover said:\n%s" % r["text"])
