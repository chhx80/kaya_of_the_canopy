# Changelog

## M0 — Bootstrap
- Godot 4.7 project, 400×240 pixel-perfect viewport with integer scaling.
- Autoloads: `Game` (state machine + run stats), `SaveManager` (versioned JSON),
  `AudioManager` (SFX pool + music), `DevCapture` (screenshot harness).
- Original art pipeline: `tools/gen_art.py` generates the tileset, four player
  forms, five enemies, pickups, props, an 8×8 bitmap font, the logo, the title
  backdrop and the parallax layers.
- `PixelFont` / `PixelLabel` for retro text rendering.
- `TileData4` / `TileWorld` / `TileCollision`: pure, node-free collision core.
- Headless test runner (`tools/test.sh`) + 20 collision tests.
- Title screen with menu, fireflies and best score.

## M1 — Movement, collision and the screen-flip camera
- `Actor`: float AABB stepped through `TileCollision`, with ladder/water/hazard
  probes and a ledge test for AI.
- `FormBase` + `form_human`: run with accel/friction, coyote time, jump buffer,
  variable jump height, vine climbing with column snap, wading, and
  drop-through on one-way platforms. All tuning in `data/forms/human.json`.
- `CameraController`: screen-flip camera that freezes the sim for a 120 ms slide;
  smooth-follow available via the `screen_flip` setting.
- `Screen`: screen-flip geometry, extracted so headless tests can reach it.
- `LevelLoader` + `levels/jungle_1.json` (2×2 screens) and the
  `tools/build_levels.py` authoring DSL.
- `TileRenderer` (camera-culled atlas drawing) and `ParallaxBg` (seamless
  tiling parallax).
- HUD: hearts, gems, score, keys, lives, level-name banner.
- `tools/validate.sh` structural validator; suite now 38 tests.

## M2 — Combat
- `WeaponBase` + `boomerang_blade`: one blade in flight, flies out to
  `max_range` or the first wall, homes back, and must be caught. Damages each
  enemy at most once per throw and shatters crates.
- `Enemy` base: JSON-driven stats, damage flash, death with score and a drop
  table, contact damage, and off-screen freezing with respawn-on-re-entry.
- `walker` (patrol + turn at ledges + optional chase) and `jumper`
  (idle → wind-up → leap → cooldown).
- `Pickup` (gem, heart, three key colours) with a toss arc for enemy drops, and
  `LevelExit` which reverts Kaya to human before completing the level.
- Game over and victory screens.
- New **integration test tier** (`tools/itest.sh`, 29 checks) that drives the
  real running game; plus `levels/test_arena.json`. See ADR 003.
- Unit suite now 48 tests / 202 assertions.

## M3 + M4 — World triggers, the hub, and progression
- `Door`: locked doors are real solid tiles; the matching key is consumed on
  contact and the tile is punched out. Wrong key shows a HUD message.
- `SwitchTrigger`: flips a switch group so the paired blocks swap solidity.
  Tripped by walking into it or by the blade — once per throw, so a boomerang
  pass does not cancel itself.
- `levels/hub.json` + `Overworld` + `HubPlayer` + `HubDoor`: top-down overworld
  that screen-flips, with gateways gated on save flags, a "cleared N/M" readout
  and a per-door label. Entering is a discrete Jump press, not a hold.
- `levels/jungle_2.json` (ROOT HOLLOW): keys, doors, both switch groups,
  breakable crates, spike pits.
- `topdown` level flag so the overworld is exempt from the platformer spawn
  rules.
- Integration suite now 70 checks, including the whole hub → level → exit → hub
  progression loop and a save round-trip.

## M5 — Transformations
- `form_frog`: huge committed jump, slow run, no weapon, and a timed wall cling
  with a kick-off jump. (The cling clamp now runs after gravity — it was
  drifting upward by g·dt every tick.)
- `form_fish`: eight-way swimming, a surface hop, an air timer that kills you
  out of water, and the short-range `bite` weapon (`MeleeHit`).
- `form_bird`: flap on a stamina budget, hold to glide, perch to refill.
- `TransformPad` (frog / fish / bird / human) — swapping forms keeps Kaya's feet
  planted when the hitbox height changes.
- Weapons follow the form: the frog and bird genuinely have none.
- HUD gained a form meter (bird stamina / fish air).
- `levels/jungle_3.json` (THE WATERWAY) and `levels/jungle_4.json` (SKY BRANCH),
  plus two more hub gateways.
- Integration suite now 135 checks.

## M6 — Enemy roster and the boss
- `Projectile`: enemy shots that die on solid tiles and on contact.
- `shooter` (rooted bloom: line-of-sight check, telegraph, spit) and `swimmer`
  (sine cruise in water, lunges at a swimming player, flops when beached).
- `boss_grove` — THE GROVE WARDEN, three data-driven phases (STOMP → LEAP →
  FURY) with leaps, floor shockwaves, reinforcements and a spore spray.
  Thresholds are health-based so burst damage can skip a phase cleanly.
- Boss arenas lock the screen-flip camera; beating the boss unlocks it and
  opens the gate rather than ending the level outright.
- HUD boss bar with the phase name; the HUD now redraws every frame so live
  values (boss health, stamina, air) are never stale.
- `levels/jungle_5.json` (HEART OF THE GROVE) and the final hub gateway, which
  requires every other level to be cleared.
- Integration suite now 158 checks.

## M7 — Controls and menus
- `TouchControls`: floating stick (appears under your thumb, 8-way snapped with
  a dead zone) plus A/Jump and B/Attack buttons, drawn at the game's own
  resolution and feeding the ordinary input actions — nothing downstream knows
  touch exists. Haptic tick on button press.
- Gamepad auto-detect: connecting a pad hides the overlay and releases anything
  it was holding.
- Pause overlay (resume / restart / options / quit) and a shared options panel
  reachable from both the title and the pause menu; every row writes through to
  `SaveManager`, including the screen-flip-vs-smooth-scroll camera mode.
- Two tooling fixes this milestone surfaced:
  - `tools/validate.sh` was reporting OK on scripts with parse errors — a
    GDScript with a parse error still loads as an object, so it now checks
    `can_instantiate()`. It also covers `tests/` now.
  - `tools/itest.sh` is hard-bounded, so a hang fails instead of hanging.
- And one real bug: `Main` had been marked `PROCESS_MODE_ALWAYS`, which made
  `get_tree().paused` a no-op for the entire world beneath it.
- Integration suite now 172 checks.

## M8 — Audio and presentation
- `tools/gen_audio.py`: an original PSG-style synth (square / triangle / LFSR
  noise + ADSR) rendered to 16-bit WAVs. 29 SFX and 6 music tracks — title,
  hub, two world themes, boss and victory — all composed here, no samples.
- Music loops seamlessly: the WAV importer defaults to one-shot, so the loop is
  set on the stream itself instead of restarting on `finished`.
- `tests/test_audio_assets.gd` greps `src/` for every `AudioManager.play/music`
  call and fails if the WAV is missing — a silent sound raises no error at
  runtime, so nothing else would catch it.
- Scenes now fade in from black on every swap.
- Art: the bird form is a bright macaw instead of a pale grey blob (it was
  invisible against the canopy), and hub gateways are stone arches with three
  clearly different states (locked / open-and-glowing / cleared).

## M9 — Ship
- `export_presets.cfg` for Web, macOS, Android, iOS, plus a **macOS Playtest**
  preset that keeps the capture harness so a *packaged* build can be driven.
- Build scripts per target; the Android and iOS scripts fail with an
  explanation rather than a Godot stack trace when their prerequisites are
  missing.
- Store icons at 20 sizes and a boot splash, all generated from the same source
  roundel; `export/PrivacyInfo.xcprivacy`.
- Enabled ETC2/ASTC VRAM compression (required for arm64/universal exports).
- **`tools/smoke_build.sh`** — boots the exported binary headless and fails on
  startup errors. It immediately caught a release-only bug: `DevCapture` was an
  autoload living in `tools/`, which the export filter strips, so the shipped
  build died before the first frame. The harness is now instantiated on demand
  by `Main` and only when the CLI actually asks for it.
- Static caches (`PixelFont._tex`, `TileData4._shared`) and the audio players
  are released on exit.
- `docs/shipping.md` documents every target's prerequisites and status.

## Post-M9 — completability checks
- `tests/test_level_validity.gd` now also asserts that every playable level has
  an exit, that each locked door has at least one key of its colour in the same
  level, that a boss level pairs its boss with a `boss_exit`, that every
  transform pad names a form that exists, and that every hub gateway points at a
  level that exists (including its prerequisite). 57 tests / 529 assertions.

## Fix — ROOT HOLLOW was unfinishable

Reported from play: the yellow door opened and the character still could not
get through.

**Cause.** A door occupied one tile. One tile is 16 px; the human hitbox is
22 px. The doorway looked open on the grid and was a solid wall in play. The red
door had it too, so the level was unfinishable past the first door.

**Fix.** `Door` now spans `HEIGHT_TILES = 2` — it makes every tile it covers
solid while locked and clears all of them when unlocked, and draws its sprite
stacked. Both doorways in ROOT HOLLOW are carved two tiles tall so the level
states its intent rather than relying on the door to punch through rock.

**Guarded by three new tests**, each verified to fail on the original code:
- `test_a_door_is_at_least_as_tall_as_the_player` — compares `Door.HEIGHT_TILES`
  against the human hitbox, so this cannot be reintroduced by tuning either one.
- `test_everything_the_player_must_reach_has_headroom` — every key, door, exit,
  pad and switch in every level needs the player's height of clearance.
- `test_no_standable_pockets_are_too_short_to_stand_in` — sweeps all geometry for
  standable tiles with too little headroom that you could walk up to.

The sweep found one more: the boss arena's left wall stopped a tile short of the
floor, leaving a nook nobody could enter. Sealed.

The integration suite now asserts the player **walks through** the opened door
and lands on the far side, rather than just asserting the door reports itself
open — which is what let this ship.
