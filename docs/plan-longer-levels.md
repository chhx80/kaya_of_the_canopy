# Plan: levels five times as long, bosses a player can beat

Status: pilot in progress, 2026-11-19. Owner's verdict from TestFlight: "The
levels are way too easy and the bosses too hard."

## Measured, before

- All 25 levels are 50×30 tiles (2×2 screens of 25×15).
- Proof-tape route per level: 6–34 s. The whole game is 6.8 minutes of perfect
  play. jungle_1: 12 s.
- 2–8 enemies per level. No checkpoints: a death restarts the level.
- Boss levels: a 6–13 s walk, then 12–24 boss health against 5 hearts.

## Target

- **5× the route, not 5× empty space.** A level's proof tape runs 75–120 s
  (about 4–6 minutes on a first play), on roughly 16–20 screens, shaped to the
  world.
- A level is five or six **sections**, each about one of today's levels, each
  with its own idea, joined so that the route runs through all of them.
- **Difficulty rises inside a level and across a world**, and is measured:
  enemies per route-minute, timed hazards, hops that need a second form.
- **Checkpoints** between sections. A death returns to the last one touched.
- **Bosses:** a checkpoint at the arena door, a heart in the arena, longer
  telegraphs, less health. The boss gate's winning tape must keep a stated
  margin of hearts.

## Phases

1. **Pilot** (this document's scope): checkpoints + level metrics; jungle_1 at
   full length; the Grove Warden retuned. To TestFlight; the owner judges
   length and difficulty on the phone.
2. Fan-out by world, four levels each, to the pilot's template.
3. The other four bosses.
4. Whole-game pass: curve, device performance, store screenshots.

## Pilot contract (so three branches can be built in parallel)

- A checkpoint is a level entity `{"type": "checkpoint", "x": <tile>, "y": <tile>}`
  whose tile is the cell Kaya stands in (her feet on the tile below). `long/engine`
  implements it; `long/jungle1` and `long/warden` only place it.
- Levels stay `levels/*.json` (ADR 002) and stay proved (ADR 005). A larger
  level is more screens of the same 25×15, not a new format.
- Nothing ships without: test, validate, itest, prove, clipgate --all-forms,
  the boss gates, pickupgate leads settled, sync_ios last then test.
