# M6 — the 25-door hub

Branch `wave1/hub`. Files added, and nothing else touched:

| File | What it is |
|---|---|
| `tools/build_hub.py` | standalone generator for the new overworld; refuses to write a map it cannot prove |
| `levels/hub_v2.json` | the generated map, 50×30, 25 gateways, five clusters |
| `tests/test_hub_layout.gd` | shape, gateway list, and the `requires` chain |
| `tests/test_hub_walkable.gd` | the walkability proof, and a negative control for it |
| `shots/m6_hub_*.png` | screenshots (see *Evidence*) |

`tools/build_levels.py`, `levels/hub.json` and `src/**` are untouched — `git
status` shows them clean and `git diff` is empty for all three. `build_hub.py`
imports nothing from `build_levels.py`, so the two can be merged in any order.

## The map

```
 rows  0..1    border
 rows  2..7    WORLD 5  The Obsidian Nest   x  2..47   dark rock, metal walkways, lava veins
 row   8       ridge, crossings at x 6..7 and x 42..43
 rows  9..14   WORLD 4  Termite Deeps       x  2..23   black ground, brown tunnels, dirt mounds
               WORLD 3  Thermal Heights     x 26..47   brown ash, rock trails, stone crags, vents
 row  15       ridge, crossings at x 6..7 and x 42..43
 rows 16..27   WORLD 1  Canopy Trail        x  2..23   grass, brown trails, trees      <- spawn (3,26)
               WORLD 2  Sunken Ruins        x 26..47   mossy flagstones, blue water
 rows 28..29   border
 cols 24..25   the wall between the left and right clusters, crossings at y 12..13 and y 22..23
```

Region edges sit on the screen seams (x=25, y=15) wherever they can, so no
cluster is split across a screen flip. Only the Nest band spans both screen
columns, the same way the shipped five-door hub spanned both of its screens.

Each region has its own ground tile, its own trail tile and its own obstacle
tile — five different grounds (`g` grass, `S` mossy brick, `d` ash, `X` dark,
`r` rock) and five different obstacles (`@` tree, `W` water, `s` stone, `d`
dirt, `M` metal), so no two clusters read alike.

**The five jungle gateways keep their shipped level ids and labels** —
`jungle_1` CANOPY TRAIL, `jungle_2` ROOT HOLLOW, `jungle_3` THE WATERWAY,
`jungle_4` SKY BRANCH, `jungle_5` HEART OF THE GROVE — asserted by
`test_the_five_jungle_gateways_keep_their_shipped_ids_and_labels`. Their tile
positions moved, because the map they lived on is now a quarter of the map.

### Gating

One `requires` chain per world, and each world's first gateway requires the
previous world's fifth:

```
jungle_1 (open)  -> jungle_2 -> jungle_3 -> jungle_4 -> jungle_5
jungle_5 -> ruins_1   -> ruins_2   -> ruins_3   -> ruins_4   -> ruins_5
ruins_5  -> heights_1 -> heights_2 -> heights_3 -> heights_4 -> heights_5
heights_5 -> deeps_1  -> deeps_2   -> deeps_3   -> deeps_4   -> deeps_5
deeps_5  -> nest_1    -> nest_2    -> nest_3    -> nest_4    -> nest_5
```

No new mechanism: this is the existing `hub_door` `requires` field and
`HubDoor.unlocked()`, unchanged.

**`requires_all` is deliberately not used, including on `jungle_5`, which
shipped with it.** `HubDoor.unlocked()` implements `requires_all` as *every
file in `levels/` except `hub` and `test_arena` has its flag set*. That counts
files, not worlds, so it has two problems here:

1. While `levels/hub_v2.json` sits next to `levels/hub.json`, `hub_v2` is
   itself counted as an unfinished level, and any `requires_all` gateway is
   locked forever.
2. With 25 levels it means "clear all 24 others", which is a game-wide gate,
   not a world gate.

Under a strict chain the two are equivalent for the final door anyway — you
cannot reach `nest_5` without having cleared all 24 — so the chain loses
nothing. `test_no_gateway_uses_the_requires_all_shortcut` pins this.
If you want `jungle_5` to keep `requires_all` at merge, it will behave
correctly only *after* the file is renamed to `levels/hub.json`.

## How the walkability is proved

The rule was: prove every gateway is walkable from the spawn, with a flood fill,
as a gating test. It is, twice over, plus a control.

**1. Flood fill over player positions, not tiles.** A tile flood fill is a
model — it would say a 16 px gap is "a walkable tile" without ever asking
whether the player fits. So the flood runs over the space of *positions the
real 10×10 `HubPlayer` box can occupy*, deciding "free" with the game's own
`TileWorld.is_solid()` and the game's own tile-span arithmetic (`(p + size −
EPS) / TS`, the `TileCollision.tile_range()` rule). Steps are one pixel along
one axis; a frame of walking covers 1.23 px at full speed and the character
accelerates from rest, so no step in the flood is a step the character could
not take.

Three things are asserted per gateway, and the third is the one that matters:

- you can walk onto the gateway tile;
- you can walk to **the tile the game returns you to** — `overworld.gd` drops
  you at `door.pos + (3, 20)`, one tile *below* the gateway, when you come back
  out of a level. A solid tile there means you return inside a wall, and
  nothing else in the suite looks at it;
- **some position you can actually reach makes the "PRESS JUMP TO ENTER"
  prompt appear** — the real `door.aabb().grow(6.0).intersects(player.aabb())`
  test from `overworld.gd`. Reaching the tile is the mechanism; lighting the
  prompt is the outcome.

**2. An actual walk.** For each gateway a simulated `HubPlayer` — the real box,
the real `SPEED`/`ACCEL`/`FRICTION` constants read off `HubPlayer`, the real
`TileCollision.move_x`/`move_y` in the real order — is driven from the spawn,
one 60 Hz frame at a time, holding whole d-pad directions along the route the
flood found, and has to arrive. This exists because a path through free space
and a character that gets there are two different claims: the character
accelerates and coasts a couple of pixels past where it meant to stop. The
first version of this test failed on 13 of 25 gateways for exactly that reason
(the flood's route hugged the last free pixel of a two-tile gap), which is why
routes are now relaxed to the middle of their corridor before the walk.

**3. A negative control.** `test_a_walled_in_gateway_is_reported` walls a
gateway in, re-floods, and fails if the flood *still* reaches it. A prover that
cannot fail proves nothing.

**4. A staleness guard.** `test_the_numbers_this_file_trusts_are_still_the_ones_
the_game_uses` reads `src/hub/hub_player.gd` and `src/hub/overworld.gd` and
fails if the box (`Vector2(10, 10)`), the spawn offset (`Vector2(3, 5)`), the
return offset (`Vector2(3, 20)`), the gateway reach (`grow(6.0)`),
`HubDoor.SIZE` or the walk speed change. If someone edits the hub player, this
proof stops quoting a stale result and says so. I confirmed it finds all four
strings today; I did not fire it in the failing direction, because doing so
means editing `src/hub/`, which I do not own.

`tools/build_hub.py` runs the same flood in Python before it writes anything,
so a bad map never reaches `levels/`.

### The gate was fired on purpose

Five defects injected — three through `build_hub.py`, two straight into
`levels/hub_v2.json` — plus the control that lives in the suite:

| Injected | Caught by |
|---|---|
| `jungle_2` moved onto a tree | python: *gateway tile (3,21) cannot be walked to* |
| a solid tile under `jungle_2` | python and GDScript: *the tile the game returns you to, (11,22), is not walkable* |
| both crossings into Thermal Heights bricked up | python: 15 problems across all five `heights_*` gateways |
| ditto, in the JSON | GDScript: all three checks fail for all five, incl. *no position you can walk to lights its prompt* |
| the walled-in gateway control | passes, i.e. sealing a gateway in does break the flood |

Commands to reproduce the injections are in *Verifying it* below.

## Verifying it

```bash
tools/env.sh          # must point PROJECT_ROOT at THIS worktree, see Assumptions
$PYVENV tools/build_hub.py        # regenerates levels/hub_v2.json; prints the proof
tools/test.sh                     # tests/test_hub_layout.gd + tests/test_hub_walkable.gd
tools/validate.sh
tools/itest.sh
```

Results, run on this worktree:

| Gate | As committed (`hub_v2.json` beside `hub.json`) | As merged (`hub_v2.json` → `hub.json`) |
|---|---|---|
| `tools/test.sh` | 155 tests, 8962 assertions, **1 failed** | 155 tests, **1 failed** |
| `tools/validate.sh` | `validate: OK` | `validate: OK` |
| `tools/itest.sh` | `273 checks, ALL PASSED` | `273 checks, ALL PASSED` |

All 26 of my own assertions' test methods pass in both states. The single
failure is in `tests/test_level_validity.gd`, which I do not own — see
*Two things the merge has to fix*.

To re-run the defect injections:

```bash
# python-side gate
$PYVENV - <<'PY'
import importlib.util
spec = importlib.util.spec_from_file_location("bh", "tools/build_hub.py")
bh = importlib.util.module_from_spec(spec); spec.loader.exec_module(bh)
bh.DOORS[1] = ("jungle_2", "ROOT HOLLOW", "jungle_1", (3, 21), "canopy")   # onto a tree
m = bh.build(); seen, stride, _w, _h = bh.prove_walkable(m)
for p in bh.check_doors(m, seen, stride): print("FAIL", p)
PY

# gdscript-side gate: brick up both crossings into Thermal Heights, then restore
python3 - <<'PY'
import json
d = json.load(open('levels/hub_v2.json')); fg = [list(r) for r in d['fg']]
for x, y, ch in [(42,8,'s'),(43,8,'s'),(42,15,'W'),(43,15,'W'),
                 (24,12,'d'),(25,12,'d'),(24,13,'d'),(25,13,'d')]:
    fg[y][x] = ch
d['fg'] = [''.join(r) for r in fg]; json.dump(d, open('levels/hub_v2.json','w'), indent=1)
PY
tools/test.sh            # expect test_hub_walkable failures for all five heights_*
$PYVENV tools/build_hub.py   # regenerate the good map
```

## Evidence

Screenshots were taken by temporarily copying `levels/hub_v2.json` over
`levels/hub.json` (the `hub` capture scenario hardcodes `HUB_ID = "hub"`), then
restoring `levels/hub.json` from git. It is byte-identical to `HEAD` now.

- `shots/m6_hub_regions.png` — contact sheet, one screen per region. The HUD
  reads **CLEARED 0/25**, and the gateway prompts show **UPDRAFT / LOCKED**,
  **THE LIGHTLESS / LOCKED**, **BLACK GLASS / LOCKED** — the `requires` chain
  doing its job in the running game, not in a test.
- `shots/m6_hub_region_{canopy,ruins,heights,deeps,nest}.png` — the five
  clusters. These five were captured with the spawn moved into each region (a
  scratch copy of the map, never written to `levels/`) purely to point the
  camera; the geometry is the shipped geometry, and each variant was re-proved
  before capture.
- `shots/m6_hub_walk_{1_spawn,2_seam,3_ruins}.png` — one continuous capture,
  **real input only, no teleports**: from the spawn, right, up, and right
  across the col-24/25 crossing, with the screen flipping into Sunken Ruins.

## What I could NOT verify

- **That the twenty new levels exist.** They do not. Every `ruins_*`,
  `heights_*`, `deeps_*` and `nest_*` gateway points at a file that is not on
  disk. My tests tolerate this deliberately: `test_hub_layout.gd` checks that
  every `requires` names another *gateway on this map*, never that the target
  *file* exists. Nothing here proves those levels load, are finishable, or have
  the ids the level authors will actually use. If a level author picks
  different ids, `DOORS` in `tools/build_hub.py` is the one place to change.
- **That a human enjoys walking it.** The proof says every gateway is
  reachable and that a simulated walk arrives. It says nothing about whether
  the routes are pleasant, whether 25 doors on one map is legible, or whether
  the Nest band spanning two screens is confusing in the hand. That is a
  playtest, and this project's history says the playtest is where the real
  answers come from.
- **On-device cost.** The rest of M6 (difficulty curve, VRAM and frame cost on
  a real iPhone) is not in this branch. The hub is two screens' worth of the
  same tileset the levels use, so I expect nothing new, but I did not measure
  it.
- **The `_relax`/`_walk` route follower is my code, not the game's.** The
  physics inside it (`_step`) is the real constants and the real
  `TileCollision` calls in the real order, but the *controller* that decides
  which direction to hold is mine — a player might hold different directions.
  It proves a route can be walked; it does not prove every route can.
- **Screen-flip behaviour during the walk** is only covered by the one real-
  input capture above; the simulated walk in `test_hub_walkable.gd` has no
  camera and therefore no screen flip, and `overworld.gd` does not freeze the
  sim on a flip the way a level does, so I do not believe there is a gap —
  but I did not prove it.

## Two things the merge has to fix

Both are in `tests/test_level_validity.gd`, which another agent owns. I did not
touch it. Neither is caused by the map being wrong.

1. **`test_every_playable_level_has_a_way_out` fails on `hub_v2`.** It skips
   `id == "hub"` and demands an `exit` or `boss_exit` from everything else. An
   overworld has neither. This is the one failing assertion in the committed
   state. Fix: `if id == "hub" or def.topdown: continue` — or just rename
   `hub_v2.json` to `hub.json`, which is the plan anyway.
2. **`test_every_level_a_hub_gateway_points_at_actually_exists` fails once the
   map becomes `hub.json`** — 20 gateways, 39 assertions, all "points at
   missing level 'ruins_1'" and friends. It will keep failing until the twenty
   levels land. Fix while the worlds are being built: skip a target whose file
   is absent, or keep a list of ids that are allowed to be pending.

I could have made the first one go away by putting a fake `exit` entity in the
overworld. I did not, because a hub with an exit in it is exactly the kind of
data that makes a later test lie.

## Assumptions I made about other agents' work

1. **`levels/hub_v2.json` will be renamed to `levels/hub.json` at merge.**
   Nothing loads `hub_v2`: `Overworld.HUB_ID` is the literal `"hub"` and I did
   not edit `src/`. Until the rename, the new map is data nobody reads.
   My two test files call `_hub_id()`, which returns `"hub_v2"` if that file
   exists and `"hub"` otherwise, so they follow the map through the rename with
   no edit — and if `hub_v2.json` is deleted without the rename they fail
   loudly against the old five-door hub rather than silently passing.
2. **`src/hub/hub_player.gd` and `src/hub/overworld.gd` stay as they are.** The
   proof depends on four literals in them; the staleness guard above fails if
   any of them moves. It is a string match on the source, so a purely cosmetic
   reformat of those lines would also fail it. That is the intended trade.
3. **`data/tiles.json` and `data/level_legend.json` keep their current tile
   ids and characters.** `build_hub.py` reads both and derives solidity from
   them rather than hardcoding it, so a *new* tile is fine; changing which
   character maps to which id is not.
4. **`HubDoor.unlocked()` keeps its current `requires` semantics.** If someone
   changes `requires_all` to mean "the levels this door's world contains", the
   chain still works — it just becomes one of two valid ways to express it.
5. **The world order is jungle → ruins → heights → deeps → nest**, taken from
   `docs/plan-20-levels.md` (World 2 Sunken Ruins, 3 Thermal Heights, 4 Termite
   Deeps, 5 The Obsidian Nest). The level *labels* I invented for the twenty
   pending gateways (`DROWNED GATE`, `THE CISTERN`, …) are placeholders; the
   boss levels are named after the bosses the plan names (`THE TIDE MAW`, `THE
   STORMCREST`, `THE BROOD QUEEN`, `THE OBSIDIAN HEART`). Whoever builds a
   world should overwrite its labels in `DOORS`.
6. **`CHANGELOG.md` is not mine**, so it does not mention this. It needs a line
   at merge.
7. **`tools/env.sh` is gitignored and was pointing `PROJECT_ROOT` at the main
   checkout**, not this worktree, so every tool script would have run against
   the wrong tree. I repointed it locally. Nothing is committed — but every
   agent in a worktree has this, and a first `tools/import.sh` is also needed
   or the whole suite reports "parse error" on files that are fine.
