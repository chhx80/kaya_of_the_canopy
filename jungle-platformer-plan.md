# Jungle Platformer — Mobile Build Plan

A design + architecture plan for an original 2D platformer in the spirit of early-90s DOS action games (tile-based levels, screen-flip scrolling, an overworld hub, animal transformations, a thrown boomerang-style weapon). Written to be handed to Claude Code (Opus) and executed phase by phase.

**Note on IP:** the plan targets the *feel* of that era. All characters, names, sprites, music, and level layouts must be original. Don't reuse the original game's assets, character name, or level data.

---

## 1. What we're building (design pillars)

| Pillar | Definition |
|---|---|
| **Tile-based world** | 16×16 tiles, 20×15 tile screens (320×240 logical). Solid, one-way, ladder, water, hazard, and trigger tiles. |
| **Screen-flip scrolling** | Camera snaps one screen at a time when the player crosses an edge (configurable: smooth-scroll mode as an option). |
| **Overworld hub** | A top-down map with level doors. Completing a level returns you to the hub and opens the next door. |
| **Transformations** | Certain levels turn the player into a frog (high jump, no weapon), fish (swim, water levels), or bird (flight, limited). Each form is its own controller. |
| **Throw-and-return weapon** | Primary attack is a thrown blade that flies out and boomerangs back; pickups swap it for other projectiles. |
| **Keys, switches, gems** | Keys open matching doors; switches toggle tile groups; gems are score. |
| **Enemies with simple state machines** | Walkers, jumpers, shooters, swimmers, a boss per world. |
| **Retro presentation** | 16-color-style palette, chunky pixel art, PC-speaker/AdLib-inspired chiptune, integer-scaled pixel-perfect rendering. |

**Target platforms:** iOS + Android (phone and tablet), landscape only. Secondary: web build for playtesting.

**Input:** virtual d-pad + 2 buttons (jump, attack), plus MFi/Bluetooth gamepad support. Optional swipe-to-throw.

---

## 2. Architecture options

Four viable stacks. Scored 1–5 on what matters for *this* project with *Claude Code* as the primary developer.

| Criterion | A. Phaser 3 + Capacitor | B. Godot 4 | C. Unity 2D | D. Flutter Flame |
|---|---|---|---|---|
| Claude Code friendliness (text-based files, headless tests, fast iteration) | 5 | 4 | 2 | 4 |
| 2D platformer tooling (tilemaps, sprites, cameras) | 4 | 5 | 5 | 3 |
| Mobile perf for a 320×240 pixel game | 4 | 5 | 5 | 4 |
| Store deployment friction | 3 | 4 | 4 | 4 |
| Runs in browser for instant playtests | 5 | 4 | 2 | 4 |
| Licensing / cost | 5 (MIT) | 5 (MIT) | 3 | 5 |
| Ecosystem for level editors (Tiled/LDtk) | 5 | 5 | 4 | 3 |
| **Total** | **31** | **32** | **25** | **27** |

### Option A — Phaser 3 + TypeScript + Capacitor
- **Stack:** Phaser 3 (Arcade physics *disabled*; custom AABB), TypeScript, Vite, Capacitor for iOS/Android shells, Tiled for levels.
- **Pros:** Everything is plain text. Claude Code can write, refactor, and unit-test the whole game with Vitest in seconds. Web build doubles as dev preview. Huge platformer example base.
- **Cons:** WebView on low-end Android can hit frame pacing issues (mitigated by low logical resolution and no DOM). Audio latency in WebView is noticeably worse than native — a real concern for a jump-feel game. Store review sometimes flags WebView apps.
- **Best if:** you want the fastest possible build loop and a web demo for free.

### Option B — Godot 4 (GDScript, or C# where perf matters) ★ Recommended
- **Stack:** Godot 4.3+, GDScript, `TileMapLayer`, `CharacterBody2D` with custom move logic (not `move_and_slide` alone), LDtk or Godot's native tile editor, GUT for unit tests, export templates for iOS/Android.
- **Pros:** Scenes (`.tscn`) and scripts (`.gd`) are text and diff cleanly, so Claude Code can author them directly. Native rendering, real audio latency, pixel-perfect viewport scaling built in (`canvas_items` stretch + integer scale). Headless mode (`godot --headless -s`) runs tests in CI. Free, no royalties.
- **Cons:** Claude Code can't *see* the editor, so scene tree mistakes surface at runtime — mitigate with a `validate_scenes.gd` script run headless. iOS export needs a Mac with Xcode.
- **Best if:** you want a shippable native game and are okay opening the editor occasionally to verify.

### Option C — Unity 2D (C#)
- **Pros:** Best-in-class 2D tooling, asset store, proven mobile pipeline.
- **Cons:** Binary/YAML scenes and prefabs are painful for an AI to edit reliably; Unity Editor is required constantly; per-install/seat licensing changes; heavier binaries and slower iteration. Overkill for a 320×240 game.
- **Best if:** you already know Unity well and will do most editor work yourself.

### Option D — Flutter Flame
- **Pros:** Single Dart codebase, hot reload, decent component system, native performance.
- **Cons:** Smaller platformer ecosystem; tilemap tooling is thinner; fewer references for Claude to lean on.
- **Best if:** you're already a Flutter shop.

### Recommendation
**Primary: Godot 4 (Option B).** It gives native feel and audio, text-based project files, and a headless test path — the combination that lets Claude Code do most of the work while producing something that belongs on a phone.

**Alternative: Phaser + Capacitor (Option A)** if you'd rather prototype entirely in a browser first and accept WebView trade-offs. Section 4 is written for Godot; an appendix maps it to Phaser.

---

## 3. Core technical decisions (engine-independent)

1. **Fixed timestep simulation** at 60 Hz, render interpolation off (pixel game, integer positions). All physics in tile-units/sec, integers or fixed-point for determinism.
2. **Custom AABB tile collision**, not a general physics engine. Sub-step per axis: move X, resolve, move Y, resolve. Supports one-way platforms, ladders, slopes are *not* required (period-accurate).
3. **Data-driven everything:** levels, enemies, tiles, weapons, and transforms are JSON/resource files. Code reads data; Claude Code can add an enemy by adding a file.
4. **Level format:** LDtk (preferred — clean JSON, entity layers, enums) or Tiled. Import script converts to engine-native at build time.
5. **Entity/component-lite:** every actor is a scene/prefab with `Health`, `Hitbox`, `Hurtbox`, `Mover`, and an `AIState` script. No full ECS — keep it readable.
6. **Screen-flip camera** as a `CameraController` that owns a `current_screen: Vector2i` and tweens on edge crossing (~120 ms) while the sim pauses.
7. **Input abstraction:** `InputState { left, right, up, down, jump, attack }` filled by either touch overlay or gamepad; game code never reads raw input.
8. **Save system:** single JSON save with hub progress, unlocked doors, high scores, settings. Versioned with a migration function.
9. **Pixel-perfect rendering:** logical 320×240 (or 400×240 for widescreen phones — decide in Phase 1), integer-scaled, letterboxed, nearest-neighbour.

---

## 4. Project layout (Godot)

```
jungle/
├── CLAUDE.md                  # conventions, commands, how to test (see §7)
├── project.godot
├── addons/gut/                # unit test framework
├── src/
│   ├── core/
│   │   ├── game.gd            # state machine: Boot → Title → Hub → Level → Pause → GameOver
│   │   ├── input_state.gd
│   │   ├── save_manager.gd
│   │   └── audio_manager.gd
│   ├── world/
│   │   ├── level.gd           # loads LDtk level, spawns entities
│   │   ├── tile_collision.gd  # AABB vs tilemap, one-way, ladders, water
│   │   ├── camera_controller.gd
│   │   └── triggers/          # switches, doors, exits, transform pads
│   ├── player/
│   │   ├── player.gd          # owns current Form
│   │   ├── forms/
│   │   │   ├── form_base.gd
│   │   │   ├── form_human.gd
│   │   │   ├── form_frog.gd
│   │   │   ├── form_fish.gd
│   │   │   └── form_bird.gd
│   │   └── weapons/
│   │       ├── weapon_base.gd
│   │       ├── boomerang_blade.gd
│   │       └── projectile.gd
│   ├── enemies/
│   │   ├── enemy_base.gd      # Health, Hurtbox, AIState hooks
│   │   ├── walker.gd
│   │   ├── jumper.gd
│   │   ├── shooter.gd
│   │   ├── swimmer.gd
│   │   └── boss_*.gd
│   ├── hub/
│   │   ├── overworld.gd
│   │   └── door.gd
│   └── ui/
│       ├── touch_controls.gd
│       ├── hud.gd
│       └── menus/
├── data/
│   ├── tiles.json             # tile id → {solid, oneway, ladder, water, hazard}
│   ├── enemies/*.json
│   ├── weapons/*.json
│   └── forms/*.json           # per-form movement tuning
├── levels/
│   ├── world.ldtk
│   └── import_ldtk.gd
├── assets/
│   ├── sprites/  (Aseprite sources + exported sheets)
│   ├── tiles/
│   ├── audio/
│   └── fonts/
├── tests/
│   ├── test_tile_collision.gd
│   ├── test_player_forms.gd
│   ├── test_boomerang.gd
│   ├── test_save_migration.gd
│   └── test_level_validity.gd # every level has an exit, no unreachable keys, etc.
└── tools/
    ├── validate_scenes.gd     # headless scene-tree checks
    ├── export_android.sh
    └── export_ios.sh
```

---

## 5. Systems spec

### 5.1 Tile collision
- Tile flags from `data/tiles.json`: `solid`, `oneway`, `ladder`, `water`, `hazard`, `breakable`, `switch_group:N`.
- `Mover.move(delta_px)` → per-axis sweep against tiles overlapped by the AABB. One-way: only collide when moving down and feet were above tile top last frame.
- Ladders: while overlapping and pressing up/down, gravity off, vertical speed = climb speed.
- Water: gravity ×0.3, max fall speed reduced; fish form has full 8-way movement.
- Tests: table-driven cases for each flag type and corner cases (landing exactly on a tile seam, jumping into a one-way from below).

### 5.2 Player forms
Each form defines: `gravity`, `max_run`, `accel`, `jump_vel`, `can_attack`, `can_climb`, `move_mode ∈ {ground, swim, fly}`, sprite sheet, and hurtbox size.

| Form | Movement | Attack | Special |
|---|---|---|---|
| Human | Run/jump/climb | Boomerang blade | Default |
| Frog | Very high jump, slow run | None | Sticks to walls briefly |
| Fish | 8-way swim, dies out of water | Bite (short-range) | Water levels only |
| Bird | Flight with stamina bar | None | Stamina refills on perch |

Transform pads swap the form mid-level; the level's exit reverts to human.

### 5.3 Boomerang blade
- Launch at fixed speed in facing direction; after `max_range` px or hitting a solid, reverse and home toward the player. Caught on overlap → ready again. Only one in flight. Damages enemies both ways.
- Weapon pickups (e.g., "spinner", "fire") replace it with straight projectiles with ammo counts.

### 5.4 Enemies
`enemy_base` handles health, damage flash, death animation, drop table. AI is a small state machine per type:
- **Walker:** patrol, turn at walls/ledges, optional chase when player within N tiles.
- **Jumper:** idle → wind-up → jump toward player → land → cooldown.
- **Shooter:** stationary, fires on a timer when player is in line.
- **Swimmer:** sine-wave path, only in water.
- **Boss:** scripted phases, screen-locked.

All tuning in `data/enemies/*.json` so balancing needs no code edits.

### 5.5 Hub / progression
- `world.ldtk` has a `Hub` level with `Door` entities: `{level_id, requires_flag}`.
- Completing a level sets `flags[level_id] = true`. Doors check flags to unlock. Final door requires all.
- Hub is screen-flip like levels but with top-down movement (no gravity).

### 5.6 Camera
- `screen_size = 320×240` (or 400×240). Player crossing a screen edge triggers a 120 ms slide; sim freezes during slide. Enemies off-screen are frozen; entering a screen resets its enemies (period-accurate and cheap).

### 5.7 Touch controls
- Left third of screen: floating d-pad (appears where thumb lands). Right third: Jump and Attack buttons. Opacity/size in settings.
- Gamepad connected → hide overlay. Haptic tick on jump/attack (light).
- Dead-zone and 8-way snapping so ladders and diagonals feel intentional.

### 5.8 Audio
- Chiptune loops per world + hub; SFX via a small pool. `AudioManager` exposes `play(sfx_id)`, `music(track_id, fade)`. All original compositions (e.g., made in Furnace or Bosca Ceoil).

### 5.9 Save / settings
- `user://save.json` with `version`, `flags`, `high_scores`, `settings {music, sfx, controls}`. `migrate(old) → new` chain. Autosave on level exit.

---

## 6. Phased build plan

Each phase ends in a runnable build. Phases map to Claude Code sessions.

| Phase | Deliverable | Exit criteria |
|---|---|---|
| **0. Bootstrap** | Repo, Godot project, GUT installed, CLAUDE.md, CI running headless tests, pixel-perfect viewport, placeholder art | `godot --headless -s addons/gut/gut_cmdln.gd` passes; app runs on a phone via Android export |
| **1. Movement & collision** | Tile collision, human form, screen-flip camera, one test level | Feels good on device; all collision tests pass |
| **2. Combat** | Boomerang blade, walker + jumper enemies, health/HUD, death/respawn | Can clear a level with enemies |
| **3. Level content pipeline** | LDtk import, tile flags, keys/doors/switches, exit, level validator test | Designer can build a level in LDtk and it loads |
| **4. Hub & progression** | Overworld, doors, flags, save/load | Complete 3 levels in sequence, quit, resume |
| **5. Transformations** | Frog, fish, bird forms + transform pads + water tiles | One level per form playable |
| **6. Enemy roster & boss** | Shooter, swimmer, world-1 boss | Boss fight is completable |
| **7. Touch & gamepad polish** | Floating d-pad, buttons, haptics, controller support, settings | Playtesters on iOS/Android don't complain about controls |
| **8. Presentation** | Final art, chiptune, title/pause/game-over screens, transitions | Looks and sounds like a finished game |
| **9. Ship** | Store assets, privacy manifest, iOS/Android exports, TestFlight/Internal test | Builds accepted by both stores |

Rough sizing: phases 0–4 are the engine core (~60% of code). Content (levels/art/music) is the long tail after that.

---

## 7. Working with Claude Code

### CLAUDE.md (put this at repo root)
```markdown
# Jungle Platformer

## Stack
Godot 4.3, GDScript. Tests via GUT. Levels in LDtk (levels/world.ldtk).

## Commands
- Run tests: `godot --headless -s addons/gut/gut_cmdln.gd -gdir=res://tests -gexit`
- Validate scenes: `godot --headless -s tools/validate_scenes.gd`
- Export Android debug: `tools/export_android.sh`

## Conventions
- Fixed 60 Hz sim in `_physics_process`; all speeds in px/s; positions rounded to int before render.
- No engine physics bodies for gameplay collision — use `src/world/tile_collision.gd`.
- All tunables live in `data/`, never as magic numbers in scripts.
- Every new system gets a test in `tests/` before it's considered done.
- Scenes are text `.tscn`; keep node names PascalCase, scripts snake_case.
- Never modify `assets/` sources without asking; exported sheets are fine.

## Definition of done for a task
1. Tests pass headless. 2. `validate_scenes.gd` passes. 3. Change is described in CHANGELOG.md.
```

### Session prompts (one per phase, in order)
Give each to Claude Code as a fresh task. Include "read the plan in `docs/plan.md` and CLAUDE.md first."

1. *"Bootstrap the Godot 4 project per Phase 0. Set up GUT, a headless test script, a 320×240 pixel-perfect viewport with integer scaling, a placeholder tileset, and a GitHub Actions workflow that runs tests. Commit."*
2. *"Implement Phase 1: `tile_collision.gd` with solid/oneway/ladder flags, `form_human.gd`, and `camera_controller.gd` with screen-flip. Write table-driven tests for collision edge cases. Build one test level in LDtk and load it."*
3. *"Phase 2: boomerang blade with return-and-catch, hitbox/hurtbox system, walker and jumper enemies driven by `data/enemies/*.json`, HUD with health and score, death and respawn at level start."*
4. *"Phase 3: full LDtk importer covering tile flags, entities (keys, doors, switches, exit, spawn). Add `test_level_validity.gd` that fails if any level lacks a spawn or exit or has a door without a reachable key."*
5. *"Phase 4: overworld hub with doors gated by flags, `save_manager.gd` with versioned JSON and a migration test."*
6. *"Phase 5: frog, fish, bird forms from `data/forms/*.json`, transform pads, water tiles. One test level per form."*
7. *"Phase 6: shooter and swimmer enemies, and a world-1 boss with three phases."*
8. *"Phase 7: floating touch d-pad and buttons, gamepad auto-detect, haptics, controls settings screen."*
9. *"Phase 8: title, pause, game-over screens; music/SFX manager; level transitions."*
10. *"Phase 9: Android and iOS export presets, store icons/splash, privacy manifest, release build scripts."*

### Tips for the Claude Code loop
- Ask it to run the tests and scene validator after every change — it can't see the editor, so these are its eyes.
- For anything "feel"-related (jump arc, throw speed), have it expose sliders in `data/forms/human.json` and iterate on device yourself; then tell it the numbers you liked.
- Keep sessions scoped to one phase. Start each with "read CLAUDE.md and docs/plan.md."
- Have it write a short `docs/adr/NNN-*.md` for each non-obvious decision (e.g., why screen-flip freezes the sim).

---

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Controls feel bad on touch | Phase 7 is dedicated; test floating d-pad early (Phase 1 stub). Prioritize gamepad support as the "premium" path. |
| Claude Code breaks scenes it can't see | `validate_scenes.gd` + tests in CI; keep scenes small and mostly built from code. |
| iOS export requires a Mac | Budget for a Mac mini or a cloud Mac (e.g., MacStadium) by Phase 9. |
| Widescreen phones vs 4:3 logical res | Decide in Phase 1: 400×240 (16:9-ish, more horizontal view) vs 320×240 letterboxed. Recommend 400×240. |
| Content bottleneck (art/music) | Placeholders through Phase 7; commission or make art in parallel. Aseprite + Furnace tracker. |
| IP similarity | Original name, character, art, music, and level layouts. "Inspired by" is fine; copies are not. |

---

## Appendix A — Mapping to Phaser 3 + Capacitor

| Godot concept | Phaser equivalent |
|---|---|
| `TileMapLayer` + custom collision | `Tilemaps.TilemapLayer` for render; custom AABB against `layer.getTileAtWorldXY` |
| `CharacterBody2D` | Plain `Phaser.GameObjects.Sprite` with your own `Mover` |
| `.tscn` scenes | TypeScript classes extending `Phaser.Scene` / `Container` |
| GUT tests | Vitest on pure-TS sim modules (keep sim separate from Phaser objects so it's testable) |
| Integer scaling | `Scale.FIT` + `zoom` + `pixelArt: true`, `roundPixels: true` |
| Export templates | `npx cap add ios/android`, `npx cap sync`, build in Xcode/Android Studio |
| Audio | Use Web Audio via Phaser's `WebAudioSoundManager`; preload and unlock on first touch |

Key structural rule for Phaser: put *all* game logic in `src/sim/` (no Phaser imports) and have `src/scenes/` only render and forward input. That makes the sim fully unit-testable and lets Claude Code work without a browser.

## Appendix B — Asset checklist (all original)
- Player: 4 forms × (idle, run/swim/fly, jump, climb, hurt, death) at 16×24 or 24×24.
- Tiles: 3 worlds × ~64 tiles + hub tileset.
- Enemies: 5 types + 1 boss, 3–6 frames each.
- Weapons/pickups: blade, 2 alt weapons, key ×3 colours, gem, heart, transform pads.
- UI: 8×8 bitmap font, HUD icons, touch d-pad/buttons.
- Audio: title, hub, 3 world loops, boss loop; ~20 SFX.
