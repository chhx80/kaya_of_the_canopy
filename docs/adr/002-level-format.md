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
