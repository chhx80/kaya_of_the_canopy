# ADR 003 — Two test tiers: headless unit + in-game integration

**Status:** accepted

## Context
`godot --headless --script` replaces the main loop, so **autoloads never run and
there is no scene tree**. That makes it perfect for pure logic (collision, level
parsing, form maths) and useless for anything built out of nodes — the blade,
enemies, pickups, triggers, respawn. Those are exactly the parts most likely to
break, and screenshots can only tell us something *looked* right.

## Decision
Two tiers, both gating:

1. **`tools/test.sh`** — `tests/test_*.gd` run headless against pure classes and
   data files. Fast (~2 s), no rendering, safe in CI.
2. **`tools/itest.sh`** — `tests/integration/integration_tests.gd` boots the real
   game (autoloads, scene tree, physics), drives it frame by frame with `await
   get_tree().physics_frame`, and asserts on real state. It plays in
   `levels/test_arena.json`, a fixed one-screen level that exists only for tests
   so integration coverage never depends on level design.

## Consequences
- The integration tier found four real bugs the first time it ran, including a
  `Array[Node].filter()` type error that silently killed every second blade
  throw and never showed up in a screenshot.
- Tier 2 needs a display, so CI must either use a virtual framebuffer or run
  tier 1 only. Tier 1 alone is still a meaningful gate.
- `test_arena.json` has a documented layout contract: cols 8–13 are a clear
  blade lane with nothing breakable within one throw. Changing it breaks tests
  on purpose.
