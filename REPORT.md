# wave2/registry — the three finished enemies can be placed in a level

Branch `wave2/registry`, from `wave1/integration`.

`src/world/level.gd:141` matched exactly four entity types, so `charger`,
`dropper` and `flyer` — finished, tuned, art-complete and covered by 97 of
their own integration checks — could not appear in a level file. This branch
registers them, and rebuilds their suite so that it would have caught the
omission instead of passing around it.

---

## 1. What I built

### 1.1 `src/world/level.gd` — the registry

The literal

```gdscript
		"enemy_walker", "enemy_jumper", "enemy_shooter", "enemy_swimmer":
			return _spawn_enemy(type.substr(6), p, e)
```

is gone. In its place, ahead of the `match`:

```gdscript
const ENEMY_PREFIX := "enemy_"
const ENEMY_IDS: Array[String] = [
	"walker", "jumper", "shooter", "swimmer", "charger", "dropper", "flyer",
]
...
	if type.begins_with(ENEMY_PREFIX):
		return _spawn_named_enemy(type.substr(ENEMY_PREFIX.length()), p, e)
```

and

```gdscript
func _spawn_named_enemy(id: String, p: Vector2, e: Dictionary) -> Enemy:
	if not ENEMY_IDS.has(id):
		push_warning("Level: '%s%s' is not a registered enemy; known ids are %s"
			% [ENEMY_PREFIX, id, ", ".join(PackedStringArray(ENEMY_IDS))])
		return null
	return _spawn_enemy(id, p, e)
```

`_spawn_enemy()` already resolved `res://src/enemies/<id>.gd` dynamically and
is unchanged, so the file names already matched: `charger.gd`, `dropper.gd`,
`flyer.gd`. Registering an enemy is now **one id in one list**.

Why a list and not "whatever `.gd` is in `src/enemies/`": `enemy_base.gd` and
`projectile.gd` live in that directory and neither is placeable. A glob would
happily instantiate `Enemy` itself — a node with an empty `think()` that never
moves and never dies — which is exactly the kind of silent half-success this
project has been bitten by. `t_an_enemy_the_registry_does_not_know_spawns_nothing`
asserts `enemy_enemy_base` and `enemy_projectile` are refused.

**Requirement 4, the unknown type.** Two warnings fire, both naming the level's
own word:

```
WARNING: Level: 'enemy_ghost' is not a registered enemy; known ids are walker, jumper, shooter, swimmer, charger, dropper, flyer
WARNING: Level: unknown entity type 'enemy_ghost'
```

The second is the pre-existing one in `spawn_entity()` and is left in place —
it is still true, and it is what a level author greps for. Nothing is spawned,
nothing half-exists (asserted), and the level keeps playing (asserted).

`data/enemies/charger.json`, `dropper.json` and `flyer.json` are mine and
**needed no change**. Every key the three scripts read is already present and
already loads; the registry was the whole defect.

### 1.2 `tests/integration/enemies_v2_tests.gd` — made to bite

The old suite spawned every enemy with `level()._spawn_enemy(id, ...)`, which
reaches *past* the `enemy_*` dispatch. That is why 97 green checks coexisted
with three unplaceable enemies. Changed:

* **`spawn()` now goes through the front door** — it builds an entity
  dictionary in the exact shape `LevelLoader.from_dict()` emits (`type`, `x`,
  `y`, `px`, `py`, plus the authored props) and hands it to
  `Level.spawn_entity()`, the same call `Level._spawn_entities()` makes for
  every line of a level file. Every one of the 21 existing behaviour tests now
  depends on the registry.
* **`spawn()` asserts the spawn.** Several tests did `if c == null: return`,
  which turned a missing registration into a *shorter green run*. A null enemy
  is now a named failure at the point of spawning.
* **`t_a_level_definition_can_place_all_three`** (new) — reads
  `levels/test_arena.json` off disk, appends the three enemies to its entity
  list, puts the whole file through the real `LevelLoader.from_dict()`, asserts
  the result is a valid level, then hands every parsed entity to the level's
  own factory. Asserts: every `enemy_*` line in the definition produced an
  `Enemy` (the arena's own walker included), each loaded its own data file,
  each is in the `enemies` group and parented to the level, each collides
  against this level's world, each landed in the authored column — the boar on
  the floor of its tile, the tick against the ceiling above its tile — that a
  per-instance prop authored on the entity (`"axis": "y"`) survives the trip,
  and that all three are still alive after 90 frames of real simulation.
* **`t_an_enemy_the_registry_does_not_know_spawns_nothing`** (new) — five bad
  ids (`enemy_`, `enemy_walkr`, `enemy_enemy_base`, `enemy_projectile`,
  `enemy_ghost`), each returning null, no node left behind, no group
  membership, level still playable. Then reads `ENEMY_IDS` back out of
  `src/world/level.gd` with `get_script_constant_map()` — not a copy in the
  test — and asserts every id in it resolves to both a script and a data file,
  and that all seven are still placeable.
* **The suite is now embeddable.** It no longer starts itself from `_ready()`
  and `_report()` no longer calls `get_tree().quit()`. `run_all()` returns
  `0`/`1`, and `standalone = false` silences its own report so a host can add
  `passes`/`failures` to its own. This is the same shape
  `tests/integration/boss_gate_smoke.gd` uses. See §4.

**97 checks → 179 checks, all passing.**

### 1.3 `tests/integration/enemies_v2_runner.gd` + `.tscn` (new)

Headless entry point. The suite needs autoloads and a scene tree, which
`--headless --script` does not have (ADR 003), so this boots
`src/core/main.tscn` as a child — which is what sets `Game.main` — then awaits
`run_all()` and exits on what it returns. Same shape and same reason as
`tools/bossgate/bossgate_runner.gd`. `KAYA_V2_MODE=shot` runs
`enemies_v2_shot.gd` instead (needs a window); the environment rather than a
`--` user arg, because user args are what switch `tools/dev_capture.gd` into
screenshot mode.

Before this, the suite could only be run by hand-writing a scene file into the
worktree and deleting it afterwards, which is what the previous agent's report
instructed. **`enemies_v2_runner.tscn` is outside my declared ownership** (I own
`tests/integration/enemies_v2_*.gd`, and this is a `.tscn`). It is additive and
conflicts with nothing; if the merge drops it, recreate it from §2 or wire the
suite in per §4 — the `.gd` half is mine and stands either way.

### 1.4 `tests/integration/enemies_v2_shot.gd`

Now authors its three enemies through `Level.spawn_entity()` too, so the
screenshot is evidence of the registry working rather than of three nodes
assembled beside it. Re-running it produced a **byte-identical**
`shots/enemies_v2.png` (git reports the file unmodified), which is a small
extra confirmation that the front-door path places them exactly where the
direct call did.

---

## 2. Exact commands to verify

```bash
cd /Users/christianheuer/.herdr/worktrees/jungle-project/wave2-registry

# One-time in a fresh worktree: tools/env.sh must point PROJECT_ROOT here, and
# the import cache has to exist or every unit test reports "parse error".
tools/import.sh

# ---- my suite: 179 checks, exit 0
source tools/env.sh
"$GODOT" --headless --fixed-fps 60 --path . \
    res://tests/integration/enemies_v2_runner.tscn
echo "RC=$?"
# => enemies_v2: 179 checks, ALL PASSED   RC=0

# ---- the unknown-enemy warning (requirement 4), which the harness cannot
#      assert from inside the process — Godot's warning stream is not readable
#      from GDScript. This is the only claim in this branch a machine here does
#      not make for me:
"$GODOT" --headless --fixed-fps 60 --path . \
    res://tests/integration/enemies_v2_runner.tscn 2>&1 \
    | grep "WARNING: Level:" | sort -u
# => 'enemy_' / 'enemy_walkr' / 'enemy_enemy_base' / 'enemy_projectile' /
#    'enemy_ghost' each "is not a registered enemy; known ids are walker,
#    jumper, shooter, swimmer, charger, dropper, flyer", plus the pre-existing
#    "unknown entity type '<the same>'" for each.

# ---- the four project gates (results and the four pre-existing reds below)
tools/test.sh      # 217 tests, 19283 assertions, 0 failed        exit 0
tools/validate.sh  # every level reachable                        exit 0
tools/itest.sh     # 298 passed, 3 FAILED (all three pre-existing) exit 1
tools/prove.sh     # 5 PROVED, jungle_3 FAIL (pre-existing)        exit 1

# ---- the screenshot (needs a display)
source tools/env.sh
KAYA_V2_MODE=shot "$GODOT" --path . --rendering-driver opengl3 \
    --resolution 1200x720 res://tests/integration/enemies_v2_runner.tscn
# => [capture] shots/enemies_v2.png (400x240) err=0
```

### Gate results on this branch

| gate | baseline (before my change) | after |
|---|---|---|
| `tools/test.sh` | 217 tests, 19283 assertions, 0 failed — exit 0 | **217 tests, 19283 assertions, 0 failed — exit 0** (identical) |
| `tools/validate.sh` | OK, exit 0 | **OK, exit 0** (identical) |
| `tools/itest.sh` | 298 passed, **3 FAILED** — exit 1 | **298 passed, 3 FAILED — exit 1** (the same three, same closest-approach numbers) |
| `tools/prove.sh` | `jungle_3` FAILs (measured separately, see below) | **5 levels PROVED, `jungle_3` FAIL — exit 1** |
| `enemies_v2` suite | 97 checks (per the previous agent's report) | 179 checks, ALL PASSED, exit 0 |

`tools/prove.sh` is the one gate I did not have a baseline for at the start, so
I measured one: I reverted `src/world/level.gd` to `HEAD`, ran
`tools/prove.sh jungle_3` on the untouched file, and got the **same failure**:

```
FAIL   jungle_3 — the tape does not reproduce the proof
       hop 8/8  pad_human > exit replayed to (743.000000, 164.000000),
       but the search left it at (727.000000, 105.000000)
```

Then restored my file. So `jungle_3` is pre-existing and is the same defect as
the red `t_replay_jungle_3` in `tools/itest.sh`. It is also structurally
impossible for this branch to have caused it: `tools/solver/` never
instantiates `Level` — it mirrors the geometry in `sim.gd` and only *quotes*
`level.gd` in comments — and `tools/reachability.py` does not mention enemies
at all. The other five levels prove, and every regenerated `levels/*.tape.json`
came back byte-identical (`git status` clean).

So: **three red integration cases and one red prover level, all four of them
red before I started, none of them mine.** Everything else is green.

### I proved the new tests actually bite

Removing `"charger"` from `ENEMY_IDS` — and changing nothing else — turns the
suite red in fourteen places, including every charger behaviour test that
previously would have returned early and stayed green:

```
FAIL t_a_level_definition_can_place_all_three :: the level factory built a 'enemy_charger'
FAIL t_a_level_definition_can_place_all_three :: every enemy the definition authored reached the world (got 3, want 4)
FAIL t_a_level_definition_can_place_all_three :: including all three of the new ones (got 2, want 3)
FAIL t_an_enemy_the_registry_does_not_know_spawns_nothing :: the registry lists every enemy (["walker", "jumper", "shooter", "swimmer", "dropper", "flyer"])
FAIL t_an_enemy_the_registry_does_not_know_spawns_nothing :: 'charger' is still placeable
FAIL t_charger_patrols_and_turns_at_a_wall :: the level places an enemy_charger at tile (2, 11)
... 8 more, one per charger test
enemies_v2: 93 passed, 14 FAILED
```

The registry was restored immediately afterwards; `git diff` on
`src/world/level.gd` shows the seven ids.

### Requirement 3, and where each half is proved

All six run through `Level.spawn_entity()` on an authored entity dictionary:

| claim | test |
|---|---|
| a level definition can place a charger | `t_a_level_definition_can_place_all_three`, plus every `t_charger_*` |
| a level definition can place a dropper | same, plus every `t_dropper_*` |
| a level definition can place a flyer | same, plus every `t_flyer_*` |
| charger damages Kaya on contact | `t_a_charger_damages_the_player_on_contact` — `Game.health` falls |
| dropper damages Kaya on contact | `t_a_falling_dropper_damages_the_player_on_contact` — it drops onto her and `Game.health` falls |
| flyer damages Kaya on contact | `t_a_flyer_damages_the_player_on_contact` — `Game.health` falls |
| charger dies to the blade | `t_the_blade_kills_a_charger_and_scores_it` — three real throws, and `Game.score` rises by exactly `score_value` |
| dropper dies to the blade | `t_the_blade_kills_a_dropper_on_its_ceiling` — one throw, killed while clinging |
| flyer dies to the blade | `t_the_blade_kills_a_flyer_and_scores_it` — two throws, score asserted |

---

## 3. What I could NOT verify — plainly

1. **No level in `levels/` contains one of these three.** `levels/` and
   `tools/build_levels.py` are not mine. `t_a_level_definition_can_place_all_three`
   builds its fixture by reading `levels/test_arena.json`, appending three
   entities in memory and parsing the result with the real `LevelLoader` — so
   the loader, the entity list and the factory are all real, but the file on
   disk is not. **Nothing I ran boots a committed level file containing a
   charger.** The last hop (`Game.goto_level(id)` → `LevelLoader.load_level`)
   is an id-to-path lookup that does not look at entity types, so I believe the
   gap is inert; I did not prove it.
2. **The unknown-enemy warning text is verified by eye, not by assertion.**
   GDScript cannot read Godot's warning stream from inside the process. The
   test asserts everything else about that path (null return, no node, no group
   membership, level survives); the *wording* is checked by the grep in §2,
   which I ran. If someone changes the message, that grep is what breaks, and
   nothing in the gates will.
3. **The suite is still not in `tools/itest.sh`.** It runs only via the runner
   scene in §2. Until §4.1 lands, a CI run of the four gates does not execute a
   single one of these 179 checks. That is the single most important thing left.
4. **No playtest.** I never played a level containing one of these. Whether a
   charger in a corridor is fair, whether 0.55 s of tell reads on a phone,
   whether a dropper over a pit is a cheap death — all unknown, and all the
   kind of thing this project's six shipped defects were.
5. **No prover/tape coverage of a level containing one.** `tools/prove.sh` and
   `tools/reachability.py` ignore `enemy_*` entities entirely (verified by
   grep: neither file mentions enemies), and I ran `tools/prove.sh` — five
   levels prove and every tape came back byte-identical — so placing one
   cannot break an existing proof. But a tape recorded on a level that *does*
   contain a charger
   is likely to be **fragile**, because the charge is driven by the player's
   position and a replay that arrives a frame late meets a different boar.
   Whoever authors the first level with one should expect to re-record.
6. **No performance measurement**, on a phone or anywhere. Three more enemy
   types on one screen is untested for frame cost.
7. **Multi-screen freeze/respawn is still synthetic.** `test_arena` is one
   screen, so `t_a_screen_flip_freezes_them_and_puts_them_back_as_they_started`
   calls `set_active_screen()` by hand. I never walked a real camera across a
   boundary with one of these on the far side.
8. **I did not touch `CHANGELOG.md`.** It is not mine and an edit would be
   discarded at merge; the entry I would have written is in §4.4.

---

## 4. What a merge step must do (files I do not own)

### 4.1 `tests/integration/integration_tests.gd` — REQUIRED for CI coverage

The suite is ready to be folded in; it no longer self-starts and no longer
quits the process. Add to `run_all()`'s list:

```gdscript
		"t_enemies_v2",
```

and the method:

```gdscript
## The three M5 enemies, in their own file because they carry their own arena
## setup. 179 checks — see tests/integration/enemies_v2_tests.gd.
func t_enemies_v2() -> void:
	var s: Node = (load("res://tests/integration/enemies_v2_tests.gd") as GDScript).new()
	s.standalone = false
	add_child(s)
	await s.run_all()
	passes += s.passes
	failures.append_array(s.failures)
	s.queue_free()
```

Two things to know before wiring it:

* `s.standalone = false` is not optional. Left `true`, the sub-suite prints its
  own `enemies_v2: N checks` report line into the middle of the host's run.
  It will no longer kill the process — that was removed — but the report is
  confusing.
* The suite calls `Game.reset_run()` / `Game.goto_level()` in its own
  `enter_arena()` before every case, so it leaves the host in the arena with a
  fresh run. Put `t_enemies_v2` where the host's next case does its own
  `enter_arena()` — which is every case in `run_all()`'s loop — and nothing
  needs to change. It costs roughly 25 s of wall clock on this machine.

### 4.2 `tools/gen_art.py` — still outstanding from wave 1

`tools/art/sprites_enemies_v2.py` exists but `gen_art.py` still imports only
`backdrops, palette, sprites, tiles` and never calls it. A full `tools/genart.sh`
will not refresh the three sheets. It will not delete them either, so this is
not urgent — but it is a trap.

### 4.3 `tests/test_art_palette.gd` — still outstanding from wave 1

`SHEETS` still lists only the four original enemies. The ramp-purity rule for
the three new sheets is enforced only by
`t_the_new_sheets_stay_on_the_material_ramps` inside my suite, which is not in
the gates until §4.1 lands. Adding

```gdscript
	"res://assets/sprites/enemy_charger.png",
	"res://assets/sprites/enemy_dropper.png",
	"res://assets/sprites/enemy_flyer.png",
```

to `SHEETS` makes `tools/test.sh` guard it and my stopgap redundant.

### 4.4 `CHANGELOG.md`

```markdown
- `src/world/level.gd` dispatches every `enemy_<id>` entity type through one
  registry (`ENEMY_IDS`) instead of a literal list of four, so `charger`,
  `dropper` and `flyer` can be placed in a level at last. An unregistered id
  warns with the ids it could have used and spawns nothing.
- `tests/integration/enemies_v2_tests.gd` places its enemies through
  `Level.spawn_entity()` rather than reaching past the factory, so its checks
  now depend on the registration they used to skip; two cases cover the level
  definition and the unknown-id path. 97 → 179 checks.
```

### 4.5 Nothing else needs to change to author one

`tools/build_levels.py`'s `g.ent()` takes a raw type string, and
`data/level_legend.json` maps *tile characters*, not entities — so
`g.ent("enemy_charger", 12, 25)` works today. The flyer's per-instance props
ride along on the entity dictionary and survive `LevelLoader`, which
`t_a_level_definition_can_place_all_three` asserts:

```python
g.ent("enemy_flyer", 12, 5, axis="y", range=48)
```

---

## 5. Assumptions I made about other agents' work

1. **The three enemy scripts and their data are correct as delivered.** I read
   them and changed neither. Their 21 behaviour tests pass through the new
   spawn path unchanged, which is the evidence.
2. **`tools/itest.sh`'s three red cases are not mine.**
   `t_replay_jungle_3`, `t_replay_jungle_5` and
   `t_the_replay_plays_a_tape_split_across_several_hops` were red before I
   touched anything — I ran the baseline first, and they are the same three
   failures with the same closest-approach numbers afterwards.
   `ERROR: Error calling method from 'filter' … Cannot convert argument 1 from
   Object to Object` out of `src/player/weapons/boomerang_blade.gd:8` also
   appears in the baseline log; it is noise from a freed blade in a lambda
   filter, not something this branch introduced, and not my file.
3. **Nobody else is editing `src/world/level.gd`.** If another wave-2 branch
   adds an entity type to `_spawn_gameplay_entity()`, the merge conflicts with
   my diff hunk. Mine deletes one `match` arm and adds a guard above the
   `match`; another agent's new arm should apply cleanly beside it.
4. **`levels/` belongs to the level agent.** I placed nothing on disk and
   assume whoever authors wave-2 levels will use §4.5.
5. **`REPORT.md` at `HEAD~1` was somebody else's.** It held the wave1/hub
   agent's M6 report, and writing mine over it is what the brief asked for. I
   copied it to `REPORT-wave1-hub.md` rather than lose it; it is also still at
   `git show 2d48d72:REPORT.md`. If the integrator drops per-agent reports the
   way `9c61796` did, drop both.
6. **`shots/enemies_v2.png` is already committed** (by wave 1) and my
   regeneration reproduced it byte-for-byte, so this branch adds no image.
