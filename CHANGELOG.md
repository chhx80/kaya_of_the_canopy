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

## Fix — vines you could climb but not get off

Reported from play, a second time: the platform in ROOT HOLLOW's upper screen
was still not reachable after the previous fix.

The vine reached the upper screen, but **column 21 was empty at every row** —
the nearest ledge sat one column away. Stepping off dropped you into the gap, so
the only way across was a blind mid-air jump from a ladder. The reachability
check passed it because it allows jumps of up to three tiles; reachable on paper
is not the same as playable.

Fixed by extending the ledge and the platform to sit flush against the vine, so
you simply walk off. Verified with no jump pressed: the player leaves the vine
and lands on the ledge, `on_floor=true`.

Added a design rule to `tools/reachability.py`: **every climbable column must
have somewhere to step off within three tiles of its top.** It immediately found
the same defect in two more levels:

- SKY BRANCH — the vine ended inside the ledge above it, so the climb finished
  in solid rock.
- HEART OF THE GROVE — the vine stopped in mid-air below the upper ledge, and
  was drawn before it, so it had no exit at all.

Both now run through to a standing surface.

## Fix — the frog was sealed in a box

Reported from play: in SKY BRANCH, transforming into a frog leaves you unable to
jump anywhere, walls on both sides.

Exactly right. The shaft's left wall ran from row 8 all the way to the floor —
20 tiles — and both the spawn and the frog pad sat on its left. Becoming a frog
put you in a sealed box. Everything past it, including the bird pad, the human
pad and the exit, was unreachable.

The reachability check passed it because **its jumps went through walls**. It
only verified that the destination was standable, so a two-tile hop from column
10 to column 12 ignored the 20-tile wall at column 11. `path_clear()` now
requires every column a move crosses to have a two-tile gap somewhere in the
band the arc covers. With that in place the check reports all three unreachable
entities, and the wall now stops two tiles above the floor so you walk into the
shaft.

## Fix — the frog shaft was a chimney with a lid

Reported from play: past the wall on the right, and the top, were both
unreachable in SKY BRANCH.

The shaft was capped at row 7 across its **full width**. You climbed the whole
thing and hit a lid, with the bird pad, the human pad and the exit all on the
far side of it. Cols 12-14 are now open sky, the climb ends underneath them,
and you come out on the roof beside the bird pad.

The climb was also re-spaced from 4-tile steps to 3. The frog's apex is 5.16
tiles, but that is a jump held to full height; release early and `jump_cut`
halves what is left, which tops out near 4.37 tiles. A 4-tile step therefore
had about six pixels of margin, and measurement in the running game showed
identical-looking rungs landing or dropping you to the bottom of the shaft
depending on rounding. All seven rungs now catch with a deliberately cut jump.

`path_clear()` missed the lid because it returned True for any move in a single
column — it never checked what was between you and where you landed, so it
happily jumped through the very slab it was landing on. It now models a move
the way it is played: rise in the start column to a travel row, cross at that
row, drop into the destination column. A self-test pins both this and the
earlier jump-through-walls case, and fails if either is reintroduced.

## M2-M4 — the engine verbs the later worlds are built on

Four new verbs for worlds 2, 3 and 4. Three of them change where the player
ends up, so all three live in the *tile flags* and are applied inside
`FormBase.update()` — never in a Node. The Route Prover (ADR 005) drives
`form.update()` + `actor.step_motion()` and nothing else, so anything it cannot
see is something it would prove a level without. Every case below is exercised
headlessly against a real `TileWorld`, with no scene tree, no `Level` and no
`Player` in the loop.

**Currents and updrafts — one feature, two data configurations.** A tile may
declare `"current": [vx, vy]` in px/s: the velocity of the medium standing in
it. `FormBase.current_at()` samples the tiles the hitbox overlaps, weighted by
how much of the hitbox is in each, and `FormBase.current` then offsets every
target the form steers towards — the run target, terminal velocity, the swim
vector, a jump, a flap, a climb. So a form always moves *relative to the water*:
the fish's own 92 px/s against a 68 px/s push is 24 px/s of headway, and the
120 px/s push is a one-way gate. Ids 200-205 are water pushes for the Sunken
Ruins, 206-210 air for Thermal Heights. Weighted rather than all-or-nothing
because a step function on a tile edge makes the answer depend on which side of
a single pixel you are, and six pixels is what cost this project a level.

`apply_gravity()` now falls with `move_toward` instead of `min(v + g·dt, cap)`,
because an updraft puts the cap *below* your current speed and walking into one
at full fall speed has to decelerate at gravity rather than snap. The two are
identical below the cap, so every measured arc is unchanged — the frog's real
apex is still 5.34 tiles, pinned by a test.

Measured, and it is a fact level authors need: because the push is weighted, a
rider does not shoot out of the top of a draught. The lift tapers as the hitbox
leaves it and you settle hovering with your head clear of the lip. You leave by
steering sideways, or — as the bird — by flapping. You cannot jump out; you were
never on the ground.

**Breakable walls.** Crate-breaking generalised: any `breakable` tile may
declare `"break_hold"`, the seconds of shouldering it takes to open without a
weapon. Hold attack and press into it; up and down beat facing, so a frog can
dig a ceiling or a floor. Ids 211-215. The frog carries no weapon and is half of
the Termite Deeps, and the blade is a Node the prover cannot see, so the verb
lives on the form instead. Crates declare no `break_hold` and so behave exactly
as they have for five levels: blade only.

**Darkness.** `"darkness": 0.86` on a level's `data/ambience.json` entry draws a
palette-ramp shade over the whole screen and one additive pool that follows
Kaya, with the defaults in `data/fx.json`. Drawn over the tiles and under the
entities, so a dark level *raises* the contrast between her and the ground.

It is visual only, and that is a constraint rather than an omission: the prover
cannot see, so a level whose solvability turned on what was lit could never be
proved. `tests/test_verbs_darkness.gd` holds it to that by running 240 ticks of
the same inputs lit and dark for three forms and requiring the traces to agree
to the last float. `tools/shot.sh --darkness=0.9` forces any level dark for
tuning and capture; `shots/m4_darkness.png` is the before and after.
## M2-M5 art — four world tilesets and four parallax backdrops

Tilesets for SUNKEN RUINS, THERMAL HEIGHTS, TERMITE DEEPS and THE OBSIDIAN
NEST, twelve gameplay tiles each, and a three-plane parallax backdrop for each
world. All of it is script-generated from the same ramps, dithering and
auto-shading as the jungle set — `tools/genart.sh`.

- `data/tiles.json` gains ids **220-231** (ruins), **240-251** (heights),
  **260-271** (deeps) and **280-291** (nest). Nothing already declared moved.
  Each block is a solid mass, its capped form, a background wall, a secondary
  solid, two more background fills, a background column, a one-way, a hazard, a
  climbable and a breakable.
- Three materials per world autotile across the 47-case blob set and pick from
  three paintings per case; background fills get six. `VARIANT_BASE` moves from
  32 to 400 so gameplay ids and variants stop sharing the front of the atlas.
  The sheet grows from 256x1488 to **256x3680** — 3.8 MB as RGBA, inside the
  4096 px every target guarantees, with 416 px of headroom left.
- `tools/gen_art.py --readability` is new, and is the reason the worlds look
  the way they do. It composites the real layers, stands each of the four forms
  in the scene at seven positions, and measures how much of each silhouette the
  world swallows — against a threshold derived from the palette's own finest
  step rather than picked. It is calibrated on the defect the brief names: the
  green frog on the green jungle parallax scores worst in the table, losing
  15.2% of its outline with a 10.4% connected hole. Every new world beats it;
  the worst new combination is the fish in TERMITE DEEPS at 10.4% / 5.0%.
  `--preview` writes the panels the per-world contact sheets are built from.
- Findings that came out of that loop and changed the art: THERMAL HEIGHTS read
  as planking until its strata were broken up and half its surface turned grey;
  TERMITE DEEPS had no separation at all between the mass and the wall behind
  it; the heights mountains were eating a tenth of the fish's outline in one
  run and were hazed two ramp steps paler to stop it.
- Screenshots: `shots/world_{ruins,heights,deeps,obsidian}_sheet.png`, each
  four panels — the world drawn by the running game, the same world with all
  four forms standing in it, the parallax alone, and the twelve tiles.

## Wave 1 integration — the proofs and the game disagree

All eight parallel branches are merged. The headline is not the merge, it is
what the merge revealed: **the prover's tapes do not reproduce in the real
game.** Five of six levels fail to replay.

That is the two-tier design working. The prover proves geometry against the
shipping movement code; the replay tier plays the recorded buttons in the real
booted level. They disagree, so one of them is wrong — and until that is
resolved, a `PROVED` verdict is worth less than ADR 005 claims.

Two causes are known. The first is fixed, the second is not:

1. **Damage desynchronises a tape completely.** `player.gd` clears the input for
   the duration of `hurt_t`, so every press after first contact with an enemy
   lands on a different frame than the one it was recorded for. The prover does
   not simulate enemies, so its tapes walk straight into them. All six levels
   failed on this, `test_arena` included — one screen, one walker. The replay
   now runs Kaya unhittable and says so in the code: this tier proves the
   buttons drive the real level through real doors, switches, pads and the
   screen-flip freeze. It does **not** prove survival, and it no longer pretends
   to.

2. **Four of the five remaining failures involve vine columns**, and one of them
   walks off the world entirely. Ladder detection is pure and identical on both
   sides, so the divergence is elsewhere — most likely that the prover applies a
   hop's entity effects at the hop boundary, while the real game applies them on
   the frame Kaya actually overlaps the pad or pickup. Unproven. The diagnostic
   that settles it is a frame-by-frame position comparison between the prover's
   sim and the booted game on one tape.

`jungle_4` replays cleanly, all sixteen hops, which is why this reads as a
specific divergence rather than a broken harness.

## The proofs and the game now agree — mostly, and for a findable reason

The divergence ran down to a single bug, in the one place nobody looks: the
prover's own snapshot/restore.

`_reset_form()` put back only the properties `_apply_form_diff` had touched, on
the theory that nothing else could have changed them. But **the form changes
them**: `form.update()` writes `coyote`, `buffer`, `_drop_timer`, `_land_t` and
`_air_vy` every tick, and nothing marked those dirty. So every `restore()` left
the previous state's timers in place, and the search explored from bodies
carrying **phantom coyote time** — finding jumps that continuous play cannot
make. The proof was real; the tape recording it was not.

It is the quietest possible version of the bug this project keeps meeting. The
mechanism was right — `restore()` was called, every time. The outcome was not —
the state did not actually come back.

Three fixes, each measured:

1. **Restore puts everything back.** jungle_1, jungle_2 and jungle_4 now replay
   in the real game, start to finish.
2. **Arrival at an entity means the entity fired.** Overlapping a door's
   waypoint rect is not opening the door; the rect is the tile grown by two
   pixels, and the door opens only on contact with a key in hand. The prover
   used to finish the job itself with `apply_waypoint_effect()` — opening the
   door *out of band* — so the next hop searched a world its own buttons had
   never produced. Replay the tape and the door is still shut.
3. **The prover replays its own tape before claiming a proof.** A tape that
   does not reproduce the search is not a proof, it is a story about one. This
   is what caught jungle_3, below, and it is now a permanent gate.

`tools/diverge.sh` is the instrument: it steps the prover's simulation and the
real booted game through the same tape and names the first frame where they
part. It found all of the above.

### What is still red, and why

- **jungle_3** — its last hop, a vine climb, still does not reproduce: the tape
  replays to (743,164) where the search left the body at (727,105). The prover
  refuses to emit the tape, which is the gate working.
- **jungle_5** — `boss_exit` does not exist during play. `level.gd` returns
  `null` for it and places it only in `on_boss_defeated()`, so the tape walks to
  the right tile and finds nothing there. The route ends at a waypoint that is
  not in the world until the boss dies, and the prover cannot fight. This is the
  seam ADR 005 already draws: traversal is the prover's, the fight is the boss
  gate's. The route and the replay need to meet at the arena floor.
- **one synthetic fixture** hand-authored before real tapes existed.

## Wave 2 — the prover's two remaining proof-correctness defects

Both were the same shape as everything else this project has had to learn:
verification that checked the mechanism and reported it as the outcome.

**jungle_3's last hop did not reproduce.** The self-check replayed the tape to
(743, 164) where the search had left the body at (727, 105), sixty pixels lower
and a tile to the right. `snapshot()`/`restore()` were not to blame this time —
the join between hops was. A tape is one continuous stream of button presses, so
the first frame of hop N+1 follows the last frame of hop N with no gap for a
thumb to lift in. The search rooted every hop at *no button held*, so its first
macro read a rising edge the replay could never see. jungle_3's hop 7 ends
holding jump and hop 8 starts standing on a transform pad: the search spent that
phantom press on a jump, the replay's jump was already down and did nothing.

The fix carries the last frame's action across the join (`ProverSearch.run(...,
held)`), and `tools/diverge.sh` now reports that the prover's simulation and the
real booted game **agree for every frame of all five tapes** — 750, 783, 689,
1040 and 823 frames. `t_replay_jungle_3` passes in the real game.

Three things were tightened at the same time, because the bug got through a gate
that was watching:

- **`restore()` really does restore.** `last_floor_tile` and `last_wall_tile`
  were never snapshotted. Nothing in the movement path reads them, which is
  exactly the argument that was wrong the last two times; they are packed into
  the snapshot now.
- **The self-check compares the whole outcome, not the position.** Landing on
  the right pixel with the wrong velocity is somewhere else a frame later, and
  landing there without having taken the key walks the next hop through a door
  the search found open. Velocity, form, grounded/climbing state, keys, doors and
  switches are all compared now.
- **A self-check that does not finish is not a self-check that passed.** A type
  error inside its loop aborted it halfway and the level still printed PROVED,
  because "no error string" was read as "checked". It now reports how many hops
  it got through, and the prover requires that to be all of them.

**jungle_5's route ended at a waypoint that does not exist during play.**
`Level.spawn_entity()` returns null for `boss_exit`; `on_boss_defeated()` places
it. The prover treated it as ordinary scenery, walked to the tile, and claimed a
level it had not finished.

ADR 005 already draws the seam — section 2 gives the prover traversal, section 4
gives the boss gate the fight and its check 5, "boss_exit is reachable from the
arena floor after defeat" — so the prover now stops at the arena and says so:

```
PARTIAL jungle_5 — 6 hops, 823 frames (13.7s of play), 8925 expansions
       NOT a full proof: traversal is proved to 'arena_floor'; 1 hop(s) to
       'boss_exit' are the boss gate's (ADR 005 section 4).
```

The tape carries `"partial": true`, `"ends_at"` and an `"unproved"` list naming
the hops and their owner, the run ends with a summary of every partial level, and
`--verify-tapes` reports a partial tape as `partial`, never as `ok`.
`--require-full` turns a partial into a failure for anyone who wants that.
The prover deliberately does **not** search its own simulation for the last hop:
the gate exists there and not in the game, and proving a level the player never
sees is the modelling mistake ADR 005 exists to stop.

New: `tests/test_prover_snapshot.gd` (9 cases) asserts restore-fidelity as an
outcome — save, disturb, restore, and require the same frames — plus the hop
join, and a classification test that fails when `Actor` gains a variable nobody
has decided about. `tools/prove.sh --diff-hops` names the state that differs on
either side of a hop boundary; it is what found this one.

## Wave 2 — the gates are green and the four new worlds are reachable

All four gates pass. Three of them for the first time together.

```
tools/test.sh      260 tests, 37,897 assertions, 0 failed
tools/validate.sh  OK
tools/itest.sh     304 checks, ALL PASSED
tools/prove.sh     5 PROVED, 1 PARTIAL (jungle_5, honestly)
```

### The three proof defects are closed

**jungle_3's last hop reproduces.** It was the same class as the previous one —
state that snapshot/restore did not round-trip — and the prover's own self-check
caught it rather than a human playing the level.

**jungle_5 no longer claims what it cannot prove.** `boss_exit` does not exist
during play: `level.gd` returns `null` for it and places it only in
`on_boss_defeated()`. The prover cannot fight a boss, so it now reports

```
PARTIAL jungle_5 — 6 hops, 823 frames
        NOT a full proof: traversal is proved to 'arena_floor'; 1 hop(s) to
        'boss_exit' are the boss gate's (ADR 005 section 4).
```

and stamps the tape partial. The replay tier asserts arrival at the arena floor
instead of a level completion a traversal tape can never reach. That is the seam
ADR 005 drew; both sides now sit on it honestly.

**The stale synthetic fixture is gone**, deleted rather than repaired, because
six real tapes cover the same ground and a test kept alive by being mended is
worse than no test.

### The four new worlds can now be built

**Per-world legends.** A level declares a `tileset` and the same twelve role
characters bind to that world's art — `#` is always this world's ground, `|`
always its ladder. Verbs (currents, updrafts, cracked and luminous walls) are
shared across all five. Before this, `data/level_legend.json` mapped 28
characters to ids 0-27 and every one of the 64 new world tiles was unreachable:
painted, tested, and impossible to place.

Proved end to end rather than assumed: `tests/fixtures/ruins_probe.json`
declares `"tileset": "ruins"`, is built from Sunken Ruins tiles, and
`tools/prove.sh` plays it — three hops, 226 frames. It is the only thing that
demonstrates a non-jungle world is playable, so it stays.

**The three new enemies can be placed.** `charger`, `dropper` and `flyer` were
finished, tunable and tested, and no level could contain one because
`level.gd` dispatched four hard-coded ids.

**`tools/world_kit.py`** — 37 helpers for flooded chambers, colonnades, current
channels, updraft shafts, tunnels and switch lattices, each checking its own
geometry against the measured jump envelope rather than the modelled one.

## M2 — World 2, Sunken Ruins

### ruins_3 — TIDE GALLERY

The level where air is the resource, and the one that had to read
`src/player/forms/form_fish.gd` before it drew a tile. The code does the
opposite of what "a submerged gallery" suggests: `air_left` is *refilled* every
tick the fish is wet and drained every tick it is not. For a fish, water is
breath. Nothing is ever charged for the length of a swim — only for the length
of a dry crossing.

So the hall is flooded and broken into four pools by courses of masonry standing
exactly one tile proud of the waterline, and the fish crosses one by breaking the
surface and flopping over the top at 40 px/s. `surface_hop` -210 against gravity
900 is 24.5 px, so a course can be one tile and never two, which is what
`world_kit.bank()` has refused since defect 4. Three dry crossings, at two, three
and four tiles, and `ProverSim.rejection()` enforces every one: a crossing a tile
too long fails the gate rather than the player.

**The budget is measured, not chosen.** Detouring the fish along the eastern
terrace with `--mark`: four, six and eight tiles of flop all prove; ten fails at
*closest approach 18.8 px, frontier exhausted after 1,292 expansions* — the
meter ended it, not the geometry and not the budget. The portage asks for four,
about half the ceiling, on `tools/world_kit.py`'s own argument about the frog's
4-tile step: the prover finds the one input that works, so a crossing it clears
with a handful of frames to spare is provable and unplayable.

**Currents make the distance between pools asymmetric.** `>` pushes 68 against
the fish's 92 — 160 px/s downstream, 24 upstream — and a human's 108 ×
`water_move_scale` 0.62 = 66.96 px/s cannot beat it at all, so every lane has
still water beside it to swim home through and the level has no softlock. `}`
pushes 120, which the fish cannot out-swim, so the covered aqueduct at the fork
is a valve rather than a shortcut. The colonnade under it is current-free,
two-way, 3.6 s slower, and holds the heart — the aqueduct buys time and costs
you the room. Both halves are proved, forwards and back.

`tools/prove.sh ruins_3`: **PROVED**, 12 hops, 742 frames, 248 expansions against
a budget of 50,000. The tape replays in the booted game — `ruins_3 COMPLETE in
742 sim frames`, full health at the totem.

Two things the gate could not see, both found by looking at the game:

- **A route that runs along a screen seam passes every check and plays badly.**
  The first layout put the waterline at row 12 and every swim waypoint at row 14,
  a pixel-wobble from the horizontal seam at y=240. `CameraController` picks the
  screen from the player's *centre* and freezes the sim for each flip, so the
  swim thrashed the camera. The prover has no camera and the replay correctly
  skips paused ticks, so both reported success; a contact sheet of the four
  screens is what caught it. All water now sits below the seam, as `jungle_3`'s
  does, and the surface hop's apex clears it by eighteen pixels.
- **A transform pad fires the instant the body overlaps it**, so a fish flopping
  east along the terrace turns human at `pad_human` whether the route said so or
  not. That is the design here — the hop's success condition is *reach the pad
  before the meter empties* — but it means the terrace beyond the pad is not part
  of the air budget, and moving the pad moves the pinch.

The level's module is `tools/worlds/ruins_3.py`; it runs standalone and writes
`levels/ruins_3.json`. It carries a small `RuinsLegend(Palette)` subclass because
`world_kit.py`'s tile lookup still resolves role characters through the flat
jungle legend — the hand-off ADR 002's amendment already names. With it the
ruins palette substitutes nothing.
