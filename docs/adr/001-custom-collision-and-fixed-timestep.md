# ADR 001 — Custom AABB tile collision, fixed 60 Hz

**Status:** accepted

## Context
The plan calls for period-accurate platforming: tile-locked geometry, one-way
platforms, ladders, no slopes. Godot's `CharacterBody2D.move_and_slide` gives
sliding, floor snapping and sub-pixel drift we would have to fight, and its
behaviour lives in the engine where a unit test cannot reach it.

## Decision
Gameplay collision is `src/world/tile_collision.gd`: static functions that sweep
an AABB against a `TileWorld` grid, one axis at a time (X, resolve, Y, resolve),
sub-stepped to at most 15 px so nothing tunnels. Everything runs in
`_physics_process` at a fixed 60 Hz. No `PhysicsBody2D` is used for gameplay.

## Consequences
- The whole collision model is testable headless — `tests/test_tile_collision.gd`
  covers seams, one-way platforms from four directions, switch blocks and
  breakables without instancing a single node. That is the main reason to do it.
- One-way platforms need the *previous* bottom edge, so movement must be
  resolved per axis rather than as one vector.
- Slopes are not supported. That matches the era and is not a regression.
- Out-of-bounds is asymmetric on purpose: the sides and top are walls, below the
  map is open, so falling off a level kills you instead of trapping you.
