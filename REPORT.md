# wave1/verbs — M2-M4 engine verbs

Branch `wave1/verbs`. Four verbs: currents, updrafts, darkness, breakable walls.

---

## 1. Gate status — read this first

| Gate | Result |
|------|--------|
| `tools/test.sh` | **1 assertion group fails**, and it is not mine to fix — see §2. 170 tests, 8,910 assertions, everything else green. Baseline before my work: 129 tests / 8,489 assertions / 0 failed. |
| `tools/validate.sh` | **passes**, exit 0. All six levels still reachable, all four form envelopes unchanged. |
| `tools/itest.sh` | **passes**, exit 0, 273 checks. Identical to the baseline I measured with `git stash` (same count, same pre-existing stderr noise from `integration_tests.gd:182` and `boomerang_blade.gd:8`). |

I am not claiming a green suite. One check is red and §2 says exactly why and
who owns the fix.

**Also: `tools/env.sh` in this worktree was wrong when I started.** Its
`PROJECT_ROOT` pointed at `/Users/christianheuer/git/jungle-project` — the main
checkout — so every `tools/*.sh` invocation ran against *main*, not this
worktree. My first three "baseline" runs were measuring the wrong tree. It is
gitignored so the fix is local-only, but **every other agent in this wave is
very likely running their gates against main too**, and would not notice: the
suite passes there. Check line 4 of your `tools/env.sh` before you trust a
green run.

## 2. The one red check, and the handoff it belongs to

```
FAIL test_tile_variants.gd :: test_variant_cells_never_collide_with_a_gameplay_id
     expected 200.000000 < 32.000000 — gameplay id 200 sits below the variants
     ... (one per id, 200 through 215)
```

`assets/tiles/variants.json` declares `variant_base: 32`, and its autotile
variants currently occupy atlas cells 1 through 1485 — **including every cell
from 200 to 219 and 220 to 399**. The shared-file protocol reserves 200-219 for
me and 220-399 for the art agent, so *both* our ranges are inside the variant
allocation. The test asserts every gameplay id sits below `variant_base`, so it
fails the moment either of us appends an id.

This is a coordination prerequisite, not a defect in my work, and it cannot be
fixed from my files (`tools/art/**` is the art agent's). The fix is:

1. `tools/art/tiles.py:677` — `VARIANT_BASE = 32` becomes `400` or higher, so
   the whole 0-399 gameplay range sits below the variants.
2. `tools/genart.sh` regenerates the atlas and `assets/tiles/variants.json`.
   The atlas has to grow: 1,458 variant cells starting at 400 need ~117 rows of
   16, against the 93 rows it has now.
3. **Cells 200-215 then need painting.** They pass
   `test_every_declared_tile_id_is_painted` today only by accident — those
   cells currently hold somebody else's variant art. Once `VARIANT_BASE` moves,
   they go blank unless the art agent paints them. The names to paint are in
   `data/tiles.json`; §6 lists them.

Nothing else in my work depends on the art. The verbs are flags and numbers;
they behave correctly against whatever pixels end up in those cells.

## 3. What was built

### Currents and updrafts — one feature, two data configurations

A tile declares `"current": [vx, vy]` in px/s — the velocity of the medium
inside it. That is the whole of it; an updraft is `[0, -400]` and a river is
`[68, 0]`, out of the same field, through the same code.

- `src/world/tile_data.gd` — `Flag.CURRENT`, `current_x`/`current_y` per id,
  `current_of(id)`, and a `has_currents` bit so a level with none pays nothing.
- `FormBase.current_at(world, rect)` — **static and pure**. Area-weighted mean
  of the current vectors of the tiles the hitbox overlaps. Weighted rather than
  all-or-nothing deliberately: a step function on a tile edge makes the push
  depend on which side of one pixel the hitbox is, and six pixels is what cost
  this project a level (defect 6 in `docs/plan-20-levels.md`).
- `FormBase.update()` samples it into `FormBase.current` and then **offsets
  every target the form steers towards**: the run target, terminal velocity,
  the swim vector, jumps, flaps, wall-kicks, climbing. A form therefore always
  moves relative to the water rather than relative to the world.

That last choice is the design decision worth arguing with. The alternatives I
rejected:

- *Clamping velocity to the current* — a 68 px/s river would pin a 92 px/s fish
  and make upstream impossible at any strength. Wrong for World 2.
- *Accelerating velocity towards the current* — swimming downstream would come
  out **slower** than swimming in still water (the form's `move_toward` to 92
  fights the current's `move_toward` to 68 and settles at 82). Obviously wrong.
- *Adding the current to velocity each tick and subtracting last tick's* —
  correct, but needs per-tick state that collisions invalidate, and it snaps
  your velocity on entry and yanks it back on exit.

Offsetting the *target* is stateless, has no entry or exit snap, compounds with
nothing, and is exactly reversible on paper, which is what makes it provable.

`apply_gravity()` changed from `min(v + g·dt, cap)` to `move_toward(v, cap,
g·dt)`. An updraft puts the cap below your current speed, and walking into one
at full fall speed has to decelerate at gravity, not teleport. Below the cap
the two are identical — the frog's apex is still **5.3385 tiles**, the number
ADR 005 was written around, and `test_verbs_currents.gd` now pins it to ±0.002
tiles rather than trusting that nothing moved.

**A measured behaviour level authors must know about.** Because the push is
area-weighted, you do not shoot out of the top of a draught. The lift tapers as
your hitbox leaves the column and you settle *hovering*, head clear of the lip,
feet still inside it. For Kaya in tile 206 that is 178.15 px against a lip at
160 px — 3.85 px of her head above it, stable indefinitely. You leave by
steering sideways, or as the bird by flapping. **You cannot jump out**: you are
airborne the whole time, so there is no coyote time. A landing at the top of a
draught has to be reachable from the hover, not from an imagined launch. Three
tests assert exactly this so nobody has to rediscover it in a level.

### Breakable walls

The blade already shattered any `BREAKABLE` tile, so the generalisation is not
"more tiles" — it is **a break that does not need a weapon and does not need a
Node**. Two reasons:

1. The frog has `can_attack: false` and is half of World 4. A wall only the
   blade could open would be a wall the frog could not pass.
2. The blade is a Node. It does not exist under `tools/test.sh` and it does not
   exist inside the prover. A route through a blade-only wall could never be
   proved.

So: a breakable tile may declare `"break_hold"`, the seconds of shouldering it
takes. Hold attack, press into it; up and down beat facing, so a frog can dig a
ceiling or a floor out of a shaft. It is `FormBase.tick_break()` — form state
against a `TileWorld`, calling the `TileWorld.break_tile()` that already
existed. When there is a `Level`, it forwards `on_tile_broken` for the debris
and the noise; when there is not, the wall still opens.

**Crates are untouched.** Id 10 declares no `break_hold`, so shouldering does
nothing to it and the blade remains the only way in — exactly as for the last
five levels. Asserted, not assumed.

### Darkness

`"darkness": 0.86` on a level's `data/ambience.json` entry (or an object
overriding any default) draws a palette-ramp shade over the whole screen plus
one additive pool that follows Kaya. Defaults live in `data/fx.json`. Drawn
over the tiles and under the entities, so a dark level *raises* the contrast
between her and the ground — the readability rule that was already structural
in `AmbienceLayer`.

The lantern is drawn outside `_visible`, deliberately: `MAX_POOLS` caps
emissive tiles at 16, and a room with enough glowing tiles to push the player's
own light out of the budget would leave her blind in a room she cannot see.
That is a softlock made of pixels, and no test could tell it from the level
being hard.

**Visual only, and held to it by test rather than by intention.**
`test_movement_is_identical_in_the_dark` runs the same 240-tick input script
for human, frog and bird, once lit and once at `darkness = 1.0`, and requires
the two position traces to agree to the last float (max drift asserted at
exactly 0.0). `test_darkness_never_becomes_a_tile_flag` walks every declared
tile and asserts no flag outside the nine collision understands. If someone
later tries to make darkness matter to movement, both go red.

## 4. How to verify it

```bash
# check this first — see §1
grep PROJECT_ROOT tools/env.sh

tools/test.sh        # 170 tests; expect exactly the §2 failure and nothing else
tools/validate.sh    # exit 0
tools/itest.sh       # exit 0, 273 checks

# just the new suites
tools/test.sh 2>&1 | grep verbs_

# darkness, rendered (regenerates shots/m4_darkness.png's inputs)
tools/shot.sh --scenario=level:jungle_1 --frames=60 --out=shots/m4_dark_off.png
tools/shot.sh --scenario=level:jungle_1 --frames=60 --darkness=0.88 --out=shots/m4_dark_on.png
tools/shot.sh --scenario=level:jungle_2 --frames=60 --darkness=0.9  --out=shots/m4_dark_cave.png
tools/grid.sh shots/m4_darkness.png 3 2 shots/m4_dark_off.png shots/m4_dark_on.png shots/m4_dark_cave.png
```

The architectural constraint, stated as three tests you can point at:

- `test_verbs_currents.gd :: test_currents_need_no_scene_tree_no_level_and_no_player`
  builds a `TileWorld` with a current tile, an `Actor` with `level = null` that
  asserts `not is_inside_tree()` and `get_parent() == null`, calls
  `form.update()` + `actor.step_motion()` once, and asserts `vel.x` changed and
  changed in the direction the tile declares.
- `test_verbs_breakables.gd :: test_breaking_needs_no_scene_tree_no_level_and_no_weapon`
  does the same for a wall: no tree, no level, no weapon, wall opens.
- `test_verbs_currents.gd :: test_the_current_is_visible_on_the_form_the_prover_holds`
  reads `form.current` back off the form, which is what a prover scoring a
  search node has to be able to do.

Every other behavioural test in both files runs the same two calls the prover
runs. There is no third code path.

## 5. What I could NOT verify

- **No in-game screenshot of currents, updrafts or breakable walls.** I own no
  level file (`levels/*.json` and `tools/build_levels.py` are explicitly not
  mine), so there is nowhere to place tile 200 or 211 and photograph it. These
  three are verified only headlessly — which for movement is the stronger
  evidence, but it is not a picture, and this project's history says pictures
  catch things. **The first World 2/3/4 level to use these tiles is where they
  get seen for the first time.** Screenshot it early.
- **No integration-tier coverage.** `tools/itest.sh` plays in
  `levels/test_arena.json`, which I may not edit, so I added no in-game checks —
  only the guarantee that the existing 273 still pass unchanged. A current tile
  in the arena would be a cheap and worthwhile addition for whoever owns it.
- **The lantern's on-screen position is verified by eye, not by assertion.**
  `AmbienceLayer` is a Node and cannot run under `tools/test.sh`.
  `shots/m4_darkness.png` is the evidence. The test I *do* have for it
  (`test_the_lantern_is_drawn_outside_the_pool_budget`) inspects the source
  text, which is a mechanism check and weaker than I would like.
- **None of the tile numbers are playtested.** 68 px/s, 120 px/s, -400, 0.35 s
  are reasoned from the form tunables (fish swims 92, human falls 330) and the
  arithmetic is asserted, but nobody has played them. Expect to retune. They
  are all in `data/tiles.json` and changing them changes nothing else.
- **Darkness is not measured on a device.** It adds one full-screen `draw_rect`
  and one `draw_texture_rect` per frame, plus a redraw whenever Kaya moves a
  whole pixel. I did not run `tools/seq/perf.json`. The `lighting: false`
  switch does strip darkness too, so the A/B is still an A/B (asserted).

## 6. Files I touched, and the ones I should not have

**Mine, as briefed:**

- `src/world/tile_data.gd` — `Flag.CURRENT`, current vectors, `break_hold`,
  `has_currents`, `current_of()`, `break_hold_of()`.
- `data/tiles.json` — **ids 200-215 only, appended**. Nothing renumbered,
  nothing removed, 216-219 left free. Names, for the art agent:
  `water_current_{right,left,up,down}` (200-203),
  `water_current_{right,left}_fast` (204-205), `updraft` (206),
  `updraft_strong` (207), `downdraft` (208), `gust_{right,left}` (209-210),
  `cracked_stone` (211), `cracked_dirt` (212), `termite_wall` (213),
  `luminous_wall` (214), `rubble` (215).
- `src/player/forms/form_base.gd`, `form_human.gd`, `form_fish.gd`,
  `form_frog.gd`, `form_bird.gd`.
- `data/fx.json` — a `darkness` block of defaults.
- `tests/test_verbs_currents.gd`, `tests/test_verbs_breakables.gd`,
  `tests/test_verbs_darkness.gd` (all new).
- `CHANGELOG.md`, `REPORT.md`.

**Outside my list — flag these at merge:**

- `src/world/ambience.gd` and `src/world/ambience_layer.gd`. My brief says I own
  `src/fx/ambience*.gd`. **No such files exist** — `Ambience` and
  `AmbienceLayer` are in `src/world/`. I read that as the directory being wrong
  in the brief rather than the feature being unowned, and edited them, because
  darkness cannot be built anywhere else. If a merge discards them, darkness
  disappears cleanly and nothing else breaks: no other file references any of
  the new fields except `data/fx.json`, which is inert on its own.
- `tools/env.sh` — one line, gitignored, never committed. See §1.

**Deliberately not touched**, though I wanted to:

- `data/forms/*.json`. Not on my list, so no form declares a break strength or a
  current resistance. Everything reads from the tile instead, which turned out
  to be the better design anyway.
- `data/ambience.json`. No level is dark in this branch. `Ambience` reads the
  `"darkness"` key and has defaults for everything else, so turning World 4 on
  is one key per level. That is why `--darkness=` exists — I needed a way to
  photograph the feature without editing a file I do not own.
- `src/world/tile_collision.gd`, `src/world/tile_world.gd`, `src/world/actor.gd`,
  `src/player/player.gd`, `src/player/weapons/*`. Not mine. Everything is built
  on their existing surface: `TileCollision.tiles_with_flag`,
  `TileCollision.tile_range`, `TileWorld.break_tile`, `Actor.aabb`.

## 7. Assumptions about other agents' work

1. **The art agent moves `VARIANT_BASE` above 400 and paints cells 200-215.**
   The hard one. Until then `tools/test.sh` is red for anyone who appends a
   gameplay id, mine or theirs. §2 has the steps.
2. **The prover drives `form.update()` + `actor.step_motion()`, as ADR 005
   says**, and does not reach past `update()` into a per-form method. I renamed
   the per-form override from `update()` to `step()` and made `FormBase.update()`
   a wrapper that samples the current, calls `step()`, then ticks the break
   verb. `Player` still calls `form.update()` and needed no change. **If the
   prover calls `form.step()` directly it will silently see a world with no
   currents and no breakable walls, and will prove routes that do not exist.**
   This is the single most dangerous assumption in this branch.
3. **The prover's action set includes `attack` held across a macro**, or a wall
   that needs 0.18-0.45 s of shouldering (11 to 27 frames, so three to seven
   4-frame macros) can never be opened by it. ADR 005 says "plus attack when the
   form can" — the frog's `can_attack` is `false` and it is exactly the form
   that needs this. **The prover must offer attack to every form, not only to
   armed ones.**
4. **The prover applies `TileWorld.break_tile()` results across hops**, as it
   already does for `switch_a/b` tile solidity. A wall broken in hop 2 must
   still be open in hop 3.
5. **`--script` headless has autoloads after all.** ADR 005 states it does not,
   and that the form scripts' `AudioManager` references make `--script` mode
   unusable. Measured in 4.7.2: the autoload *object* exists and resolves, but
   `_ready()` never ran, so `AudioManager._pool` is empty and every cue threw a
   backtrace into the test log. I routed all four forms' cues through
   `FormBase.sfx()`, which checks `is_node_ready()` first. Forms can now be
   driven headlessly *including jumps*, which is what makes
   `tests/test_verbs_currents.gd` possible. **The prover gets this for free and
   may not need the one-node-scene workaround ADR 005 describes.** Worth
   remeasuring before building around the old assumption.
6. **The level agents place these tiles from the DSL.** I added no DSL legend
   entries — `tools/build_levels.py` and `data/level_legend.json` are not mine.
   Ids 200-215 need legend characters before a level can use them.
7. **Nobody else edits `src/world/ambience*.gd`.** If the art agent owns
   lighting, we will conflict there; see §6.
