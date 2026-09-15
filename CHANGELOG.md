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

## Art phase 1 — palette and shading engine

The first phase of `docs/art-direction.md`. A pure repaint: tile ids, the level
legend, collision and every level file are untouched.

**`tools/gen_art.py` split into a package.** The 1624-line generator is now
`tools/art/{palette,tiles,sprites,backdrops}.py`, with `gen_art.py` left as the
running order so `tools/genart.sh` is unchanged. The split was landed first and
verified byte-identical against the old output before any repainting started, so
the two changes can be read apart.

**The ramps.** `tools/art/palette.py` replaces the 18 flat colours with 12
material ramps of 7 steps each — dirt, stone, wood, grass, foliage, cloth, skin,
water, metal, gold, ember, purple — plus one ink for outlines. Nothing in
`tools/art/` picks a colour any more: it picks a ramp and a level, and `dither()`
resolves fractional levels with a 4×4 Bayer matrix. The legacy `PAL` character
map is now *derived* from the ramps, so even art that was not relit shares the
vocabulary. The whole set is written to `assets/palette.json`.

**The engine.** `dither()`, `blob()`, `crack()`, `speckle()`, `bayer_on()` and
`auto_shade()`, all lit from a single direction (upper left) that every tile,
sprite and prop now agrees on.

**Tiles authored, then shaded.** Structure first — pebbles and clods in dirt,
mortar courses in stone, planks and nails in the crate and the platform, ribs in
bark, crust plates in lava, rivets in the metal plate. Fill tiles that tile in a
mass carry no per-tile bevel, because one would band them into bricks.

**Sprites relit.** Every ASCII grid goes through `auto_shade()`, which measures
distance to the silhouette edge for volume and the light direction for facing.
Silhouettes and frame counts are unchanged.

**Measured result:** tileset 18 → 67 colours, Kaya 9 → 26, and every pixel of
every sheet is a step on a ramp.

**New tests** (`tests/test_art_palette.gd`): the palette is 12×7, every ramp
climbs in luminance, no sheet contains an off-ramp colour, the tileset and Kaya
carry the shade depth the overhaul was for, each solid terrain tile is more than
a flat fill, and every id declared in `data/tiles.json` is painted (with tile 0
still fully transparent).

Before/after: `shots/art_phase1_before_after.png`.
## Art phase 5 — motion and juice

`docs/art-direction.md` phase 5: cheap effects, layered on top of the existing
art rather than replacing any of it. Nothing here is load-bearing — every effect
checks that it is available and otherwise does nothing, so a missing atlas or a
deleted `data/fx.json` costs a warning and leaves the game fully playable.

**Animated tiles.** `data/tile_anim.json` maps a tile id to how it moves:
`frames` (cycled out of a small fx atlas), `sway` (a whole-pixel draw offset,
phase-shifted per tile row so foliage ripples instead of sliding as a sheet) and
`tint` (a brightness cycle — a light source that breathes). Water surface, water
body, lava, vines and canopy leaves are animated; levels needed no changes,
because `TileRenderer` resolves all of it at draw time and the tile *id* — and
therefore collision — is untouched. `TileAnim` is pure data and pure maths, so
the whole table is exercised headlessly. The renderer repaints only when
something on the current screen has actually changed, and a screen with no
animated tiles costs nothing per frame.

**Particles.** `ParticleField`: one fixed pool, one texture, one draw pass, no
allocation after setup. Landing dust, blade impact sparks, a twinkle off
pickups, and a scatter when an enemy dies. Emitters are described entirely by
`data/fx.json`. Bursts outside the visible screen are dropped, and a burst that
would overrun the pool is quietly smaller rather than a frame-rate cliff.

**Screen shake.** Added to `CameraController` as a render offset only:
`base_pos` is the camera the screen-flip logic reasons about, `position` is
`base_pos + shake_offset`. The slide tween now drives `base_pos`, so the flip
and the shake cannot fight over one property, and the screen index is still
derived from the player and never from the camera. Capped at 8 px in code —
inside the tile cull's one-tile margin — as well as by `data/fx.json`. Fires on
the boss slam and on taking damage.

**Hitstop.** A few frames of freeze on a kill, reusing the `Game.sim_paused`
flag the camera already freezes the simulation with. It refuses to stack: if
something else owns the freeze the request is dropped, and if a screen flip
starts mid-freeze the slide keeps ownership. It is released on every state
change and whenever a level goes away.

**New tools.** `tools/gen_fx.py` / `tools/genfx.sh` generate the two fx atlases.
The animated tile frames are *derived from `assets/tiles/tileset.png`* rather
than drawn from scratch, so a repaint of the tileset carries into the animation
on the next `tools/genfx.sh`. `tools/dev_capture.gd` now prints the physics
frame with each capture — a capture is not free, and sequences that have to land
on a specific moment are timed off those numbers.

**Tests.** `tests/test_fx_data.gd` (18 tests) covers the data: every emitter
frame lands inside its atlas, every animated id exists in `data/tiles.json`,
sway is whole-pixel and clamped, a malformed entry is dropped rather than
half-applied, a missing table leaves every tile still, and — the two that matter
— no shake preset can out-reach the camera's cap and no hitstop preset can
out-last its ceiling. 83 tests / 940 assertions.

Nine integration tests cover the parts made of nodes, including the two
soft-lock guards the effects could plausibly introduce: hitstop always releases
`sim_paused` (including across a level change, and when nothing is attached),
and a shake always decays to exactly zero with the camera back on its exact
screen origin and its screen index never touched. 252 checks.

Captures: `tools/seq/m9_juice.json` and `tools/seq/m9_shake.json` →
`shots/39_landing_dust.png` … `shots/45_shake_boss_slam.png`, contact sheet in
`shots/46_phase5_contact_sheet.png`.

## Art phase 2 — tile variety and autotiling

Phase 1 repainted every tile with authored structure and left a corollary it
could not act on: a fill tile has exactly one variant, so structure strong
enough to *read* is strong enough to *tile visibly*. The hub grass was the
proof — a meadow of identical 16×16 squares reading as a lattice. This phase is
what finishes phase 1's fills, not a polish layer on top of them.

**Random variants.** Four interchangeable paintings of every fill — dirt, grass
top, stone, mossy stone, bark, the authored grass edges, water, hub grass, hub
path, hub water, plank platform, metal plate — and six or eight of the ones a
level lays down in the hundreds with nothing to break them up: background
leaves, background rock, background dark, the hub tree canopy. The one drawn is picked by a
hash of the tile's position, so it is stable across frames, reloads and screen
flips, and a wall never repeats visibly.

**Autotiling.** The 47-case blob set for the seven materials that form masses
(dirt, grass top, stone, mossy stone, background rock, hub grass, hub path),
resolved at load from the eight neighbours. Every case carries the full set of
paintings, not just the interior one — the top of a ledge is a single blob case
and the commonest tile on a platform screen, so one painting of it grids just as
badly as an undifferentiated fill did. Terrain grows a sunlit crest, an
occluded underside, lit and shadowed cheeks, ambient occlusion in inside
corners, and per-material edge dressing: pebbles and crumbling soil on earth,
sod wrapping over an exposed shoulder, chipped faces on cut stone, blades
leaning out over the end of the meadow, a gravel kerb along the path.

**Decorative overlays** on the background layer only: roots, hanging vines,
cracks, moss and splintered bone, at 12-17% of background cells. Each one is
gated on the foreground around the cell, so a vine hangs from a ledge and a
root sits on something.

**Nothing gameplay-facing moved.** `levels/*.json`, `tools/build_levels.py`,
`data/tiles.json` and `data/level_legend.json` are byte-identical. Variants are
*derived*, never authored: `TileWorld` still stores the id the level wrote and
collision still reads that array. Variant art lives in the atlas above the 28
gameplay ids, and `src/world/tile_variants.gd` maps (id, neighbours, position)
to an atlas cell — the same trick phase 5 used for animated tiles, applied to
the still art.

**New files.** `assets/tiles/variants.json` (generated beside the atlas by
`tools/art/tiles.py`), `src/world/tile_variants.gd`. The atlas grew from 28 to
1482 cells — 256x1488, about 1.5 MB of VRAM against 32 KB before. Nothing on
the desktop notices; it is the number phase 6's on-device pass is for.

**Tests.** `tests/test_tile_variants.gd` (16 tests) is the one the plan asked
for: every autotiled material has all 47 blob cases, every case offers at least
one variant, every variant cell is inside the sheet and has paint on it, no
variant is allocated on top of a gameplay id, a mass of dirt really does draw
from several cells, two independent resolutions agree, a neighbour going away
changes the tile drawn, and — the hard constraint — resolving leaves the id
grid and every solidity answer untouched. Every real level is resolved through
it as well. 106 tests / 8154 assertions.

Captures: `shots/phase2/gridding_before_after.png` (hub and CANOPY TRAIL,
before left, after right) and `shots/phase2/levels_after.png`;
`tools/seq/m4_hub.json` re-run into `shots/13*_hub*.png`.
## Art phase 3 — depth and light

Three parallax planes instead of two flat strips, a per-level ambience file, and
lighting. Nothing in `levels/*.json` changed: every level is the same geometry,
re-lit. Full write-up, including the measurements the lighting decision was made
on, in `docs/art-direction.md` ("Phase 3 as built").

**Atmospheric perspective, structurally.** `tools/art/backdrops.py` gained a
`Plane`: a depth plane owns a slice of one ramp (its *window*) and every brush
paints in material value, 0 for a thing's shadowed side and 1 for its lit side.
The window's width is the plane's whole contrast budget, so a far plane cannot
out-contrast a near one however it is drawn. The old strips had this backwards —
all three painted at the dark end of `foliage`, which made the furthest thing on
screen the highest-contrast thing on screen.

**Real layered backdrops.** Two worlds, three planes each (`bg_<world>_sky`,
`_far`, `_near`), all still generated: a jungle of receding trees under pale
blue air, and a high sky of cloud banks over a hazed canopy with a branch across
the top. Only two worlds, because ROOT HOLLOW and THE WATERWAY wall every screen
with `bg_rock` and show 0% of the parallax — those two are lit instead.

**Ambience.** `data/ambience.json` keys off the level id: backdrop world, a haze
quad over the parallax, a tint per tile layer, vignette strength, light pools and
emissive tile ids. Every colour in it is a ramp step out of `assets/palette.json`,
never an RGB literal. ROOT HOLLOW is a cold cave picked out by warm flickering
pools; SKY BRANCH is pale and airy; HEART OF THE GROVE is CANOPY TRAIL pushed
violet.

**Lighting is additive pools, not `Light2D`.** Measured in one process with a
new `{"perf": …}` step in `tools/dev_capture.gd`: the whole phase costs
+0.05–0.19 ms a frame and three draw calls, where `Light2D` + `CanvasModulate`
cost 55% more frame time on the same scene *and* dimmed Kaya along with the room.
The pools are drawn behind the entities, so a dark level now has more contrast
between the player and the floor, not less.

**`ParallaxBg` draws the copies it needs.** It used to add a spare row and column
every frame; with three planes that was a third of the backdrop's draw calls
spent off-screen. The vertical screen-lock is unchanged and now documented — it
only works because a plane is exactly one screen tall.

**Tests.** `tests/test_art_depth.gd` (9 tests) closes the backdrop exemption
phase 1 left in the palette check: every plane and both lighting textures are
pure ramp output, every plane is exactly 400x240 (the seam contract), the sky
plane has no holes, no plane out-contrasts the tileset, and no level's ambience
may dim the solid layer below two thirds or below its own background layer —
the readability rule, which was the one thing here a data file could break
silently. 99 tests / 1311 assertions. Two integration tests cover the part made
of nodes: the three ambience layers sit at the right depths with the right roles,
and light pools are found per screen and stay capped. 268 checks.

Captures: `tools/seq/art_phase3.json` → `shots/47_phase3_canopy_trail.png` …
`shots/51_phase3_heart_of_the_grove.png`, contact sheet in
`shots/52_phase3_contact_sheet.png`, the four-screen seam proof in
`shots/53_phase3_screen_lock.png`, before/after in
`shots/54_phase3_before_after.png`, the planes themselves in
`shots/55_phase3_planes.png`, and the rejected `Light2D` build beside the
shipped one in `shots/56_phase3_light2d_rejected.png`.
## Art phase 4 — Sprites and animation
See `docs/art-direction.md`. Detail and motion on top of phase 1's relighting;
every sheet is still generated by `tools/art/sprites.py`.

**Kaya: 8 frames → 20.** A real eight-frame run cycle (contact, absorb, pass,
push-off, twice) with the body sinking up to two pixels under its own weight and
the arms swinging against the legs; a four-pose jump arc that opens on a crouch
of anticipation and holds at the apex; a landing squash; a three-frame vine
climb; a breathing idle; and a hurt pose that is thrown back off its feet rather
than recoloured. The frames are composed from a head, five torsos and twelve leg
blocks rather than drawn one at a time, and the far limb now has its own two
steps of the ramp — without that separation eight frames read as one leg
flickering.

**Enemies: two frames each → four or five.** The bark beetle walks a four-beat
leg cycle with the shell dipping a pixel on alternate beats, and its legs gained
a chitin segment because pure-ink legs vanish against dark terrain. The spine
hopper telegraphs across three escalating frames — settle, crouch, coil with the
eyes lit — then extends in the air and squashes on touchdown. The spitter bloom
peels its petals back, darkens as it draws breath, swells gold, and holds an
open-jawed pose for 200 ms as it spits. The piranha and the fish form swim a
four-beat tail sweep, and both were quietly facing the wrong way — authored
head-left while `flip_h` is keyed off `facing` — so both are now mirrored on
the way out of the generator.

**The Grove Warden: 32×32 × 3 frames → 48×48 × 18.** Six poses per fight phase,
and the three phases are three different animals rather than one tint three
ways. STOMP is squat and heavy on six short legs. LEAP rears up on long coiled
legs with the carapace split open along the thorax to show the flight shell
under it. FURY has lost the carapace entirely: a ridge of spines has erupted
through the plates, ember light shows through the cracks, the jaw hangs open
and the eyes have gone white. Collision is untouched — the box is the same
26×26 it always was — but the render anchor inside the same JSON block had to
follow the frame, `(3, 5)` → `(11, 20)`, or a 48-pixel boss draws down and right
of a 26-pixel hurtbox.

**Animal forms: two frames each → six.** The frog gained a breath, a leap
crouch, a reach on the way down and a flattened wall cling; the fish a four-beat
swim, a bite and a beached flop; the bird a four-beat flap, a spread glide and a
folded perch.

**Code, which the plan said would not be needed.** `"loop": false` on an
animation plays it once and holds the last frame — without it a jump list that
opens on a crouch cycles back through the crouch in mid-air. `form_human.gd`
holds a `land` pose for 110 ms after a touchdown above 130 px/s, sampling the
impact speed on the last airborne tick because `step_motion()` has already
zeroed it by the time the form sees the landing. `boss_grove.gd` resolves
`<pose>_p1/_p2/_p3` before falling back to the plain name, which is what makes
the other twelve boss frames reachable at all. `shooter.gd` gained the `FIRE`
state its `fire` animation had been waiting for since M2. `hub_player.gd` walks
the full eight-frame cycle.

**Tests.** Every frame index named by `data/enemies/*.json` and
`data/forms/*.json` must exist in the sheet, and each sheet's height must match
its declared `frame_h` — an index past the end draws nothing, on one pose, and
ships. Plus an assertion that the Warden's art is anchored on its collision box,
because that failure is silent: it fights correctly, just beside itself.
92 tests / 1264 assertions, 252 integration checks.

Captures: `tools/seq/m10_phase4.json` → `shots/50_kaya_idle.png` …
`shots/70_fish_form.png`, in-game contact sheets in `shots/phase4_kaya.png` and
`shots/phase4_boss.png`, and the sheets themselves frame by frame in
`shots/phase4_kaya_sheet.png`, `shots/phase4_boss_sheet.png` and
`shots/phase4_sheets.png`.

`level.gd` gained `debug_advance_boss_phase()` alongside the existing capture
helpers: the Warden's phases are health thresholds, and a screenshot of all
three otherwise means staging the whole fight from a script.

## Fix — three of five levels were uncompletable

Reported from play: in ROOT HOLLOW you cannot jump from the vine onto the
platform in the upper-left screen.

**Cause.** The vine stopped at row 15, the first row of the *lower* screen, and
the platform above it was at row 12. The human jump apex is 44.5 px — 2.78
tiles — so a 3-tile rise is short by 3.5 px and physically impossible. Screen A
was sealed off entirely.

That was one instance of a pattern. `tools/reachability.py` walks each level
from its spawn using the real jump envelope from `data/forms/*.json`, including
form changes at transform pads, and found **three of five levels uncompletable**:

- ROOT HOLLOW — the key, both switches and the red key unreachable. The left
  route needed a 4-tile climb, and the critical path crossed a switch block that
  starts intangible and is only made solid by a switch on its far side.
- THE WATERWAY — the exit unreachable. The vine was drawn *before* the ledge
  above it, so the ledge overwrote its top two tiles.
- SKY BRANCH — the bird pad unreachable. The frog shaft's first step was 6
  tiles; the frog apex is 5.16.

**Fixed** by re-spacing every climb to at most 2 tiles for the human and 4 for
the frog, drawing the waterway vine after the ledge it passes through, and
giving ROOT HOLLOW's right-hand route a real platform so it no longer depends on
a switch you cannot reach.

`tools/validate.sh` now runs the reachability check, so this cannot recur.
Verified it catches the reported bug by restoring the short vine.
