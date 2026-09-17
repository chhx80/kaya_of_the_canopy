# wave1/enemies — three new enemy types (M2–M5)

Branch `wave1/enemies`. Purely additive: **no tracked file was modified**, only
new files added. `git status --porcelain | grep -v '^??'` is empty.

---

## 1. What I built

Three enemies, each a subclass of `Enemy` (`src/enemies/enemy_base.gd`), each
driven entirely from `data/enemies/<id>.json`. There is no numeric literal in
any of the three scripts that is not a fallback for a key the JSON provides.

### CHARGER — `charger` / "THORN BOAR"
`src/enemies/charger.gd`, `data/enemies/charger.json`

`PATROL → WINDUP → CHARGE → RECOVER`.

* Patrols at **26 px/s** (Kaya runs at 108, so you can walk away from it).
* Spots you only when you are **in front of it**, within `sight_range` 140 px,
  within `sight_band` 20 px vertically, **and** down a line with no solid tile
  in it. `line_is_clear()` samples the eye line every `sight_step` 6 px.
* Stops **dead** and raises its crest for `wind_up` **0.55 s**. The wind-up is
  unconditional — it is not cancelled by the player leaving, because a
  telegraph you can cancel is not a promise.
* Charges at **165 px/s** for `charge_time` 0.85 s. That is faster than Kaya can
  run, which is exactly why the tell has to be honest.
* Cannot stop: `RECOVER` bleeds the speed off at `skid_decel` 240 px/s², so it
  always slides past where you were standing, and stays dazed for `recover`
  1.1 s (`wall_recover` 1.3 s if it ran into a wall). That is the counter-attack
  window, and it is measured in the tests, not asserted in prose.
* 3 HP, so three blade throws.

### DROPPER — `dropper` / "HOLLOW TICK"
`src/enemies/dropper.gd`, `data/enemies/dropper.json`

`CLING → TELL → FALL → WALK`.

* Hangs at its spawn point with gravity off. It does **not** require a solid
  tile above it — the author places it and it hangs there. `_ready()` lifts it
  from the bottom of its authored tile to the top, because `level.gd` sits
  every enemy on its tile and a ceiling-clinger belongs against the one above.
* Lets go when the player is **below** it, inside `trigger_width` 14 px either
  side and within `trigger_depth` 112 px.
* Shivers in place for `wind_up` **0.45 s** first. Also unconditional.
* On landing, `land_action` decides: `"walk"` (shipped default — it crawls off
  like a beetle, turning at walls and ledges) or `"die"` (it bursts; a one-shot
  trap you can bait). **Both paths are covered by tests.**
* 1 HP — one blade throw kills it, on the ceiling or on the ground.

### FLYER — `flyer` / "CANOPY WASP"
`src/enemies/flyer.gd`, `data/enemies/flyer.json`

* `gravity: 0.0` and `drop_through = true`, permanently. The second one is the
  point: a flyer that lands on the first wooden walkway it crosses is a walker
  with wings.
* Patrols a fixed leg (`patrol_range` 64 px) with a sine bob (`bob_amplitude`
  6 px, `bob_period` 1.7 s) held by proportional steering, so altitude is
  authored rather than emergent. Turns at the end of the leg **or** at a solid
  wall, re-anchoring so the next leg is full length instead of grinding along
  the wall.
* Does **not** chase. The path is the threat.
* Per-instance shape comes off the level entity, so one data file covers a
  horizontal sentry and a vertical shaft patrol:
  `{"type": "enemy_flyer", "x": 12, "y": 5, "axis": "y", "range": 48, "bob": 0}`
* 2 HP.

### Art — `tools/art/sprites_enemies_v2.py` (new; nothing existing touched)
Original 16×16 ASCII grids, re-lit through `palette.auto_shade()` from the
shared upper-left light, in the same character vocabulary as
`tools/art/sprites.py`. Frame layout is the contract with the JSON:

| sheet | frames |
|---|---|
| `enemy_charger` | 0–1 patrol · 2–3 wind-up (escalating, `"loop": false`) · 4–5 charge · 6 dazed |
| `enemy_dropper` | 0 cling · 1–2 shiver · 3 falling · 4–5 crawl |
| `enemy_flyer` | 0–3 wing beat |

Silhouettes are deliberately unlike the four that exist: a wide low boar with a
bristle crest (dirt + ember + metal tusks), a hanging teardrop with legs on top
(stone + gold), and the only winged enemy in the game (gold + metal). Brown,
stone grey and gold were the three palettes not already claimed by the beetle
(purple), hopper (ember), bloom (purple-on-green) and piranha (cyan).

**Verified 0 off-ramp colours** in all three sheets.

---

## 2. Exact commands to verify

```bash
cd <this worktree>

# ---- the three project gates. All three exit 0.
tools/test.sh        # 129 tests, 8566 assertions, 0 failed
tools/validate.sh    # validate: OK
tools/itest.sh       # integration: 273 checks, ALL PASSED

# ---- my own integration suite: 97 checks.
# tests/integration/enemies_v2_tests.gd carries its own harness. It is NOT
# wired into tools/itest.sh, because that loads exactly one file and
# tests/integration/integration_tests.gd is not mine to edit (see §4).
# This runs it against the real game, headless, and cleans up after itself:
source tools/env.sh
cat > _enemies_v2_runner.tscn <<'TSCN'
[gd_scene load_steps=3 format=3]

[ext_resource type="PackedScene" path="res://src/core/main.tscn" id="1_main"]
[ext_resource type="Script" path="res://tests/integration/enemies_v2_tests.gd" id="2_run"]

[node name="Root" type="Node"]

[node name="Main" parent="." instance=ExtResource("1_main")]

[node name="EnemiesV2Tests" type="Node" parent="."]
script = ExtResource("2_run")
TSCN
"$GODOT" --headless --path . res://_enemies_v2_runner.tscn; echo "RC=$?"
rm -f _enemies_v2_runner.tscn
# => enemies_v2: 97 checks, ALL PASSED   RC=0

# ---- regenerate the art (deterministic; re-running produces identical PNGs)
source tools/env.sh && "$PYVENV" tools/art/sprites_enemies_v2.py && tools/import.sh

# ---- regenerate the screenshot (needs a display)
source tools/env.sh
cat > _enemies_v2_shot.tscn <<'TSCN'
[gd_scene load_steps=3 format=3]

[ext_resource type="PackedScene" path="res://src/core/main.tscn" id="1_main"]
[ext_resource type="Script" path="res://tests/integration/enemies_v2_shot.gd" id="2_shot"]

[node name="Root" type="Node"]

[node name="Main" parent="." instance=ExtResource("1_main")]

[node name="EnemiesV2Shot" type="Node" parent="."]
script = ExtResource("2_shot")
TSCN
"$GODOT" --path . --rendering-driver opengl3 --resolution 1200x720 res://_enemies_v2_shot.tscn
rm -f _enemies_v2_shot.tscn
# => shots/enemies_v2.png — all three drawn in the real game next to Kaya
```

### The two required claims, and where they are proved

Both are proved **in the integration tier, by doing it**, not by reading code:

| claim | test |
|---|---|
| charger killable by the blade | `t_the_blade_kills_a_charger_and_scores_it` — three real throws, asserts it dies and that `Game.score` rose by exactly `score_value` |
| dropper killable by the blade | `t_the_blade_kills_a_dropper_on_its_ceiling` — one throw, killed while still clinging |
| flyer killable by the blade | `t_the_blade_kills_a_flyer_and_scores_it` — two throws, asserts score |
| charger damages on contact | `t_a_charger_damages_the_player_on_contact` — `Game.health` drops |
| dropper damages on contact | `t_a_falling_dropper_damages_the_player_on_contact` — it falls onto Kaya and `Game.health` drops |
| flyer damages on contact | `t_a_flyer_damages_the_player_on_contact` — `Game.health` drops |

### The tests are outcome-shaped, and I proved they bite

Per the brief's warning about checking the mechanism instead of the outcome:
the wind-up test never reads the state enum. It records `(x, vel.x, sprite
region)` every frame, finds the frame the charge starts, walks backwards
through every frame the boar was stationary, and asserts (a) the stationary run
is at least `wind_up × 0.9`, (b) x moved less than 1 px across it, (c) the
sprite cells drawn during it are **disjoint from the set drawn while
patrolling** — a pose change, not just a pause. The one-way test finds the exact
frame the flyer's box crossed row 8's top edge and asserts that
`TileCollision.is_on_floor(world, probe, false)` was true there — i.e. an actor
that respects one-ways *would* have been stopped — and that the flyer was not.

I then broke the implementation five ways and confirmed each is caught:

| mutation | result |
|---|---|
| charger skips `WINDUP` entirely | `FAIL … the wind-up holds it still for the advertised time (got 0.016667, want >= 0.495000)` |
| `wind_up` shortened in data to 0.05 s | `FAIL … so the tell has to be long enough to read (got 0.050000, want >= 0.300000)` |
| flyer `drop_through = false` | 5 FAILs in the one-way test, incl. `it gets well below the platform (got 127.4, want >= 136.0)` |
| dropper drops with no shiver | `FAIL … only after shivering in place for the advertised tell (got 0.033333, want >= 0.405000)` |
| all three `contact_damage: 0` | 3 FAILs, one per contact test |

The behaviour tests assert against the value in the JSON, so on their own they
could be satisfied by a wind-up of zero. `t_the_new_enemies_are_tuned_against_
kaya_not_against_nothing` pins the data with absolute floors
(`wind_up >= 0.3`, `recover >= 0.5`, patrol speed `<` Kaya's `max_run` `<`
charge speed) — mutation 2 above is the proof that pairing works.

---

## 3. What I could NOT verify — plainly

1. **None of the three has been spawned from an authored level.** `level.gd`
   has no entity type for them (§4.1) and I am not allowed to edit it, so every
   test calls `level._spawn_enemy(...)` directly — the same function the entity
   factory calls, but bypassing the `match` that names it. **Nothing I ran
   proves a `{"type": "enemy_charger"}` entity in a level JSON works.** It
   cannot, until the registry entry lands.
2. **No level-design verification at all.** I never placed one in a real level
   and never played past one. I do not know whether a charger in a corridor is
   fun, whether the 0.55 s tell is enough on a phone, or whether a dropper over
   a pit is a cheap death. The tests prove the tell *exists and lasts as long
   as the data says*; they do not prove it is long enough for a human. That is
   a playtest, and it has not happened.
3. **No ADR 005 prover/tape coverage.** `tools/prove.sh` and `tools/solver/`
   do not exist in this worktree — M1 is another agent's. So I have not shown
   these enemies survive a tape replay, and I have not shown a charger cannot
   knock a replaying tape off course. A tape recorded on a level containing a
   charger is likely to be **fragile**, because the charge is player-position
   dependent; flag that when M1 and this branch meet.
4. **`tools/genart.sh` does not build these sheets** (§4.2). They are committed
   and correct, but a full art regen will not refresh them until `gen_art.py`
   calls my builder. It will not delete them either.
5. **`tests/test_art_palette.gd`'s `SHEETS` list does not include them** (§4.3).
   I verified ramp purity myself (0 off-ramp colours) and added
   `t_the_new_sheets_stay_on_the_material_ramps` to my own suite as a stopgap,
   but that suite is not in `tools/itest.sh` yet, so right now nothing in the
   standing gates guards it.
6. **No performance measurement.** Not on a phone, not anywhere. Three more
   enemy types on screen at once is untested for frame cost.
7. **No audio verification beyond "the id exists."** The three scripts play
   `blip`, `hop` and `land`, which are real files in `assets/audio/sfx/`. I did
   not listen to them; a charge telegraphed with `blip` may well sound wrong.
8. **Multi-screen behaviour is covered only synthetically.** I call
   `set_active_screen()` by hand in
   `t_a_screen_flip_freezes_them_and_puts_them_back_as_they_started` (frozen →
   does not move → wakes at spawn, full health, clinging again). I never walked
   a camera across a real screen boundary with one of these on the far side,
   because the arena is one screen and I cannot author a two-screen level.

---

## 4. What a merge step must do (files I do not own)

### 4.1 `src/world/level.gd` — REQUIRED, nothing works without it
In `_spawn_gameplay_entity()`, the existing line

```gdscript
		"enemy_walker", "enemy_jumper", "enemy_shooter", "enemy_swimmer":
			return _spawn_enemy(type.substr(6), p, e)
```

becomes

```gdscript
		"enemy_walker", "enemy_jumper", "enemy_shooter", "enemy_swimmer", \
		"enemy_charger", "enemy_dropper", "enemy_flyer":
			return _spawn_enemy(type.substr(6), p, e)
```

`_spawn_enemy()` itself resolves `res://src/enemies/<id>.gd` dynamically and
needs no change; the file names already match (`charger.gd`, `dropper.gd`,
`flyer.gd`). The level-authoring DSL will also need `enemy_charger` /
`enemy_dropper` / `enemy_flyer` in `data/level_legend.json` or wherever the
level agent maps characters to entities — that is theirs, not mine.

### 4.2 `tools/gen_art.py` — so a full art regen keeps them
```python
from art import backdrops, palette, sprites, sprites_enemies_v2, tiles
...
def main():
    ...
    sprites.build_boss()
    sprites_enemies_v2.build()      # <-- add
```

### 4.3 `tests/test_art_palette.gd` — bring them under the ramp-purity gate
Add to `SHEETS`:
```gdscript
	"res://assets/sprites/enemy_charger.png",
	"res://assets/sprites/enemy_dropper.png",
	"res://assets/sprites/enemy_flyer.png",
```
(`test_every_animation_frame_is_inside_its_sheet` already globs
`res://data/enemies`, so frame-index coverage is live now and passing.)

### 4.4 `tests/integration/integration_tests.gd` — run my 97 checks in CI
Cheapest merge: keep `enemies_v2_tests.gd` as-is and have `run_all()` in
`integration_tests.gd` finish with

```gdscript
	var v2: Node = (load("res://tests/integration/enemies_v2_tests.gd") as GDScript).new()
	get_tree().root.add_child(v2)
```

— but that file quits the tree itself, so the tidier merge is to copy its test
names into `integration_tests.gd`'s `tests` array and its test bodies +
`spawn()`/`park()`/`throw_at()`/`shown_frame()` helpers alongside the existing
ones (`enter_arena`, `place`, `check`, `check_eq` already exist there and are
compatible; `at_least`/`at_most` would need adding, or swapping for `gt_check_f`).
Either way, **do not lose the file** — it is the only coverage these three have.

### 4.5 `CHANGELOG.md` — I did not touch it
`CHANGELOG.md` is the single most merge-conflicting file across eight parallel
branches, and it is not mine, so I left it alone. Entry text:

```markdown
- Three new enemy types: the THORN BOAR (charger — patrols, spots you down a
  clear line, stops dead for a visible 0.55 s wind-up, charges faster than Kaya
  can run, and overshoots into a 1.1 s dazed window), the HOLLOW TICK (dropper —
  clings to a ceiling, shivers for 0.45 s when you pass underneath, then falls
  and either crawls off or bursts, per `land_action` in its data file) and the
  CANOPY WASP (flyer — no gravity, ignores one-way platforms, patrols a fixed
  airborne leg on an axis the level entity chooses). Original art generated by
  `tools/art/sprites_enemies_v2.py`; 97 in-game checks in
  `tests/integration/enemies_v2_tests.gd`.
```

---

## 5. Assumptions I made about other agents' work

1. **`level.gd` keeps resolving enemies by file name** — `_spawn_enemy()` loads
   `res://src/enemies/<id>.gd` and calls `configure(id, e)`. If anyone replaces
   that with an explicit registry, my three file names are the ids.
2. **`enemy_base.gd`'s contract is unchanged**: `think(delta)` sets `vel`, the
   base calls `step_motion`, `_touch_player`, `_update_anim`; `cfg` is a
   per-instance dictionary (my tests mutate it, which is safe only because
   `load_config()` parses fresh JSON per enemy); `respawn()` calls
   `on_respawn()`; `hurt()`/`die()` are the damage path. **Nobody else should be
   editing `enemy_base.gd` either**, but if the wave changes it, the three
   subclasses are the things to re-check.
3. **`Actor.drop_through` still means "ignore one-ways this tick"** in
   `TileCollision.move_y` and `is_on_floor`. The flyer's whole premise is that
   flag. If anyone changes its meaning, `t_flyer_flies_through_a_one_way_
   platform_that_would_catch_anyone_else` will catch it.
4. **`levels/test_arena.json` keeps its shape** — floor row 12, walls at columns
   0 and 24, one-way at row 8 columns 14–16, breakable crate at (18, 11), gem at
   (4, 11), heart at (5, 9). My tests name these as consts, but they are
   *positions*, and if the level agent edits the arena my suite breaks. I chose
   the arena rather than a new level because `levels/*.json` is not mine.
5. **The sfx ids `blip`, `hop` and `land` survive**, and the fx emitter `dust`
   and hitstop preset `kill` survive. All are referenced from data, so an audio
   agent renaming one degrades to silence (`AudioManager.play` no-ops on a
   missing file) rather than crashing.
6. **`data/fx.json`'s `scatter` emitter is still the enemy death burst** — all
   three use `"death_fx": "scatter"`, matching the existing four.
7. **`tools/itest.sh` will move to `--headless`** (it is an M1 task per
   `docs/plan-20-levels.md`). My suite already runs headless; the screenshot
   script does not and says so in its header.
8. **Kaya's `max_run` stays 108 px/s.** The charger's balance is expressed
   relative to it and asserted against it, so a form-tuning agent lowering
   `max_run` below 26 or above 165 will fail
   `t_the_new_enemies_are_tuned_against_kaya_not_against_nothing` rather than
   silently making the boar uncatchable or harmless.

---

## 6. Housekeeping

* **`tools/env.sh` had `PROJECT_ROOT` pointing at the main checkout**
  (`/Users/christianheuer/git/jungle-project`), not this worktree, so every
  `tools/*.sh` would have run against the wrong tree. I repointed it. The file
  is gitignored and machine-local, so this is not in the commit — but **every
  other agent in this wave probably has the same problem.**
  This worktree also had no `.godot/` cache: `tools/test.sh` reported 12 parse
  errors until `tools/import.sh` ran once.
* Files added outside the ownership list, and why:
  * `assets/sprites/enemy_{charger,dropper,flyer}.png` + `.import` — the output
    of `tools/art/sprites_enemies_v2.py`, which I do own. Nothing loads without
    them and the repo commits generated art.
  * `shots/enemies_v2.png` — definition-of-done item 4 ("a screenshot proves the
    feature renders").
  * `tests/integration/enemies_v2_shot.gd` — matches the `enemies_v2_*.gd`
    ownership glob; it generates that screenshot.
  * `src/enemies/*.gd.uid` — Godot writes these next to every script.
