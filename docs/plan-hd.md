# Plan: 30% larger, double-resolution art ("HD pass")

Decided with the owner, 2026-11-14:

1. The camera shows 30% less world, so everything is 30% larger on screen.
2. All art is regenerated at **double pixel density**, so the extra size carries
   real new detail rather than bigger pixels.
3. In a boss fight the camera **pulls back** to show the whole arena.
4. The picture is scaled to fill the device height **exactly** (not whole-number
   steps), through a filter that keeps pixel edges sharp.

## The contract every workstream builds against

**World units do not change.** A tile is 16 units. Hitboxes, speeds, level
files, proof tapes, boss gates: untouched, and they must all still pass.

**`ART_SCALE = 2` texels per world unit.** One number, in `data/display.json`,
read by the engine and by `tools/art`. A tile's atlas cell is 32x32 texels, Kaya's
cell 64x80, and so on. Gameplay-facing data (`data/forms/*.json`,
`data/enemies/*.json`: frame sizes, hitbox offsets, render offsets) **stays in
world units**; renderers multiply by `ART_SCALE` to find texture regions and draw
at `1 / ART_SCALE`. Frame indices and sheet names do not change.

**The view is 308 x 184 world units** (19.25 x 11.5 tiles; was 400 x 240), i.e.
616 x 368 texels. `Screen.W/H` (400 x 240) stay what they are today: the size of
a boss-arena cell and the grid levels were authored on. The view gets its own
constants.

**Boss arenas:** while the camera is locked to an arena it eases its zoom out
until the whole 400 x 240 arena is visible, and back in when the lock releases.

**Presentation:** the world is scaled to the device with a sharp-bilinear
filter so 30% is exact on every device and pixel edges stay crisp. HUD, menus
and touch controls keep the apparent size and positions they have today.

**Art comes in two steps, so the engine never waits for the artists:**
- Step 1: `tools/art` emits every sheet at 2x by nearest-neighbour upscaling
  what it draws today. Bigger pixels, no new detail, but the whole game runs on
  the new pipeline and every gate can be run.
- Step 2: sheets are redrawn natively at 2x, one area at a time. A sheet is
  switched from "upscaled" to "native" by adding its name to one set in
  `tools/art/palette.py` (`HD_NATIVE`); nothing else changes hands.

## Phases

- **H0** Engine pipeline on upscaled art (one agent) + a look sample: Kaya and a
  slice of jungle tiles drawn natively at 2x, in the new framing (one agent).
  Checkpoint: the owner approves the look.
- **H1** Native 2x art, in parallel: Kaya; frog/fish/bird; enemies and bosses;
  five tilesets; backdrops, pickups, props, effects, HUD portrait.
- **H2** Integration, every gate by exit code, store screenshots recaptured,
  TestFlight build, owner plays on device (frame rate: 4x the texels).

## Known consequences

- The player sees 19 tiles ahead instead of 25. Levels were proved for
  traversal, not for visibility; the camera's look-ahead may need tuning and a
  few drops may need a hint. Measured during H0 by replaying all 27 tapes.
- Texture memory and fill rate rise about 4x. Only a device can judge it.
