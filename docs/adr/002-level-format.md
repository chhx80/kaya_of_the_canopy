# ADR 002 — Levels are JSON char-grids, not LDtk

**Status:** accepted

## Context
The plan proposed LDtk (or Tiled) with a build-time importer. Both are GUI
editors. The developer on this project is an agent that cannot open a GUI, so an
LDtk pipeline would mean either hand-editing LDtk's own JSON — which is verbose,
uid-heavy and hostile to diffs — or blocking on a human for every level tweak.

## Decision
`levels/<id>.json` holds two layers as arrays of equal-length strings, one
character per tile, plus a flat entity list in tile coordinates:

```json
{ "id": "jungle_1", "name": "CANOPY TRAIL",
  "fg": ["....|....", "#########"],
  "bg": ["LLLLLLLLL", "........."],
  "entities": [{"type": "player_spawn", "x": 2, "y": 25}] }
```

The character→tile-id map is shared across every level in
`data/level_legend.json`. `tools/build_levels.py` is an *authoring aid* that
emits these files from a small Python DSL (`g.ground()`, `g.vine()`, …); the
committed JSON is the source of truth the game loads.

## Consequences
- A level diff is readable: you can see the shape of the change in the patch.
- `tests/test_level_validity.gd` loads every level through `LevelLoader` and
  fails on ragged rows, unknown characters, a missing spawn or a spawn hanging
  over a bottomless drop.
- No import step and no third-party format version to track.
- We give up LDtk's visual editing. If a human designer joins, writing an
  LDtk→this-format converter is a contained job, because the runtime only ever
  sees `LevelLoader.LevelDef`.

---

## Amendment, 2026-09-24 — the legend is per-world, not global

**Status:** accepted. Amends the Decision above; the grid format itself is
unchanged.

### Context

`docs/plan-20-levels.md` adds four worlds — Sunken Ruins, Thermal Heights,
Termite Deeps, The Obsidian Nest. `data/tiles.json` grew to match: ids 200–215
for the movement verbs (currents, updrafts, cracked and luminous walls) and
220–291 for the four worlds' tilesets. All of it is painted in
`assets/tiles/tileset.png` and covered by tests.

None of it could appear in a level. A level is a character grid, and
`data/level_legend.json` mapped 28 characters to ids 0–27. Sixty painted,
tested tiles were unreachable, because nothing could name them.

One global legend does not scale to that. Five worlds is roughly seventy-five
gameplay ids competing for printable ASCII, and long before that runs out the
grid stops being readable — which was the whole argument for a character grid
over LDtk. A legend where `Ω` is the ruins' stone and `∂` is the nest's ledge
is an LDtk uid table with extra steps.

### Decision

**A character means whatever the level's world says it means.**

`data/level_legend.json` holds:

- `shared` — characters that mean the same tile in every world: water, the
  movement verbs, the switch blocks, the hub tiles. A tileset may not redefine
  one.
- `tilesets` — one character map per world (`jungle`, `ruins`, `heights`,
  `deeps`, `nest`). Each binds the same twelve **role characters** to its own
  art:

  | | role | | role |
  |---|---|---|---|
  | `#` | the world's ground cap | `L` | background wall |
  | `S` | the solid it autotiles against | `T` | background column |
  | `d` | the fill under the cap | `r` | background accent |
  | `s` | a second, harder solid | `X` | background deep / void |
  | `=` | one-way platform | `^` | hazard |
  | `\|` | ladder / climbable | `c` | breakable block |

  So `#` is grass in the jungle, `ruin_stone` in the ruins, `obsidian` in the
  nest, and `g.ground()` builds all three. The jungle adds `[`, `]` and `-` for
  tiles no other world has.
- `default_tileset` — `jungle`.
- `legend` — a *derived* copy of `shared` + `tilesets.jungle`, kept only
  because `tools/reachability.py` and `tools/build_hub.py` read that key
  straight out of the JSON and both only ever look at jungle levels and the
  hub. `tests/test_level_format.gd` fails if it drifts, so it is a view and not
  a second source of truth.

A level names its world with a top-level key:

```json
{ "id": "ruins_1", "name": "THE DROWNED GATE", "tileset": "ruins",
  "fg": ["....|....", "#########"], ... }
```

**The key is optional and absent means `jungle`.** That is deliberate: writing
`"tileset": "jungle"` into the six existing levels would change their bytes,
change their `source_sha`, and stale every proof tape in `proofs/` (ADR 005)
to say something the absence of the key already says. Verified: `tools/genlevels.sh`
regenerates all seven committed level files byte-identically.

In the DSL the world belongs to the grid, because it is what the grid's
characters mean: `Grid(50, 30, tileset="ruins")`. `write()` reads it from the
grid, so `tools/build_levels.py` needs no signature change.

### Failing loudly

A character the level's own world does not define is an **error**, not empty
space. `LevelLoader.from_dict()` names every offending character *and the
tileset it was checked against*, and then returns a `LevelDef` with **no
world at all** (`def.world == null`).

The null is the point. The unmapped character used to fall through
`legend.get(ch, 0)` to tile 0, so the grid came back looking like a level with
some air in it, and only `errors` — which a caller can forget to check — said
otherwise. A mis-declared world would have produced a level of almost entirely
empty space, loading, rendering and unplayable. That is the exact shape of the
six defects this project has already shipped: the mechanism reported a
problem, the outcome looked fine. Now there is nothing to misuse.

The same mistake also fails one step earlier, at authoring time:
`Grid.to_dict()` refuses to serialise a grid containing a character its
tileset does not define, and names the layer and coordinates of the first one.

A level naming a tileset that does not exist fails the same way, and the error
lists the ones that do.

### Consequences

- The four new worlds' tiles are placeable. `tests/test_level_format.gd`
  asserts the outcome directly: **every id declared in `data/tiles.json` is
  named by some character in some tileset.** A world whose art lands without a
  legend entry fails that test, rather than being discovered by an author who
  cannot place it.
- A level file stays as readable in the ruins as in the jungle, and a level
  reads the same in every world — which also means a screen can be ported
  between worlds by changing one key.
- The cost: a character grid is no longer self-describing. You cannot read
  `levels/nest_3.json` without looking at its `tileset` key first. The loader,
  the DSL and the validity tier all check it, so the failure mode is loud, but
  a human skimming a diff has one more thing to hold.
- `tools/reachability.py` and `tools/build_hub.py` still read the flat
  `legend` key and therefore still resolve every character against the jungle.
  Today that gives them the right *answer* on a non-jungle level anyway, for a
  reason worth naming: the role mapping preserves gameplay flags across
  worlds — `#` is solid in all five, `^` is a hazard in all five, `=` is
  one-way in all five — and those two tools read nothing but flags. That is a
  property of the table as it stands, not a guarantee of the design, so
  `tests/test_level_format.gd` pins it: bind `r` to something solid in one
  world and the test fails rather than the prover quietly modelling a wall as
  air. Both tools should still learn `legend_for(tileset)` before a world
  binds a role differently; neither is touched here, and this is the hand-off.
