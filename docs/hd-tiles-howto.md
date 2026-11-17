# How to redraw a world's tiles at 2x

docs/plan-hd.md, phase H1. The jungle and the shared tiles (ids 0-27, the verbs
200-215) are native, and the ruins (220-231) have a first native pass in
`hd_tiles_ruins.py` that its agent takes over; heights, deeps and nest still
ship their 1x cells nearest-upscaled. This is how to switch one of those worlds
over, with the jungle as the worked example (`tools/art/hd_tiles_jungle.py`) and
the ruins as a second, shorter one.

## The shape of it

| file | what | who edits it |
|---|---|---|
| `tools/art/hd_tilekit.py` | the 2x machinery: primitives, edge bands, corners, the refit rim, ink, contact shadows, and the registries | nobody, in H1 (report what you need) |
| `tools/art/hd_tiles_<world>.py` | that world's 2x painters, dressers, accents, decorations | **only that world's agent** |
| `tools/art/tiles.py` | the 1x tileset, the variant specs, the atlas assembly | nobody (the 1x painters are read-only reference) |
| `tools/art/hd_native/hdtiles.txt` | `tileset`, `contact_shadow`, `tile_anim` are already native | nobody |

So four worlds can be redrawn in parallel without touching the same file. You do
**not** add anything to `hd_native/`: the atlas is already native as a whole,
and a cell is drawn at 2x the moment its id is registered.

The atlas layout, every tile id, `assets/tiles/variants.json` and
`data/level_legend.json` do not change. `tools/hd_tiles_check.py` proves it.

## What "native" means, mechanically

`tiles.py` asks `hd_tilekit.is_native(tid)` for every gameplay id:

* **not native** -- the gameplay cell, its variants, its 47 blob cases and its
  decorations are painted at 1x exactly as before and upscaled. Byte-identical
  to what H0 shipped.
* **native** -- the gameplay cell is your painter at 32x32. Its variant
  interiors are your painter with each seed of its `V(...)` spec. Every blob
  case is that interior run through `hd_tilekit.paint_edges()` -- the same steps
  as 1x (side bands, convex corners, corner pockets, the material's dresser, the
  phase C course, the refit rim), written in texels -- and then its 2x dresser.
  Accent paintings use your 2x accents, decorations your 2x decorations. If
  any of those twins is missing, `tools/gen_art.py` stops with a message naming
  it. Nothing silently falls back to an upscale.

## Step by step (ruins as the example)

1. **Read the 1x painters** in `tiles.py` (`t_ruin_*`, `dress_ruin*`,
   `d_kelp_hang`) and the world's rules in the comment above them (the luma
   bands "a world must not swallow the player" -- they still hold at 2x).

2. **Write a painter per tile** in `hd_tiles_ruins.py`, taking the same seed:

   ```python
   from .hd_tilekit import N, blob, fill, new, put, tile, wave   # etc.

   def t_ruin_stone_hd(seed, algae=False):
       rnd = random.Random(seed)
       img = new(255)
       ...                     # 32x32, whole ramp steps, wrapped structures
       return img

   tile(220, 2201)(t_ruin_stone_hd)
   tile(221, 2211)(lambda s: t_ruin_stone_hd(s, algae=True))
   ```

   The seed is the one on the tile's `T_AT(...)` line, which is also seeds[0] of
   its `V(...)` spec; `tiles.py` asserts they match. See-through voids (224, 244,
   264, 284) stay `tile(0)`-empty: register nothing for them.

3. **Write the 2x twin of every dresser your rims name**, keyed by the 1x
   function's name:

   ```python
   @dresser("dress_ruin")
   def dress_ruin_hd(img, mask, rnd): ...
   ```

   `mask` is the canonical blob mask (`BIT_N` etc. set = that neighbour is the
   same material). Use `side_xy(side, k, i)` to address "k texels into the tile
   from `side`, at i along it", and `clear()` / `put_c()` for anything that
   must not wrap.

4. **Accents** for your groups, cycled like `tiles_p3.ACCENTS`:
   `ACCENTS["ruin"] = [...]`, `CAP_ACCENTS[221] = [...]` (painters `(img, rnd)`).
   The jungle's `pebble`, `chip` and `crack_down` in hd_tiles_jungle.py are
   generic and importable.

5. **World-only decorations** (`d_kelp_hang` etc.) with
   `@decoration("d_kelp_hang")`. `d_crack`, `d_moss`, `d_roots`, `d_bones` and
   `d_vines` are already done (hd_tiles_jungle.py) and apply to your walls too.

6. **Optional rim tuning.** The side bands come from the 1x `RIM_*` dict
   (`top=[...]` deltas are resampled to texels by `_profile()`), applied as a
   relative shift so your painter's detail survives near an edge. Override per
   group with `hd_tilekit.RIM_HD["ruin"] = {"top_hd": [...], "ragged": ...}` --
   from your own module.

7. **Regenerate and check**:

   ```
   tools/genart.sh && tools/genfx.sh          # genfx re-times water/lava from the atlas
   git show <base>:assets/tiles/tileset.png > /tmp/old.png
   $PYVENV tools/hd_tiles_check.py /tmp/old.png          # exit 0: no lazy doubles,
                                                          # no other world touched
   $PYVENV tools/hd_tiles_sheet.py ruins                 # shots/hd1_tiles_ruins_*.png
   ```

   `hd_tiles_sheet.py` prints, per native id, how much of the cell differs from
   the doubled 1x cell, and for each fill its **wrap** ratio (the step across a
   painting's own wrap line over the step across a world-unit line inside it:
   about 1 is seamless) and **bias** (a lit or dark frame round the cell). Its
   `_fields.png` shows every autotiled material as a terrain field of real blob
   cases beside the 1x one -- look at it at 100%, then in game:
   `tools/shot.sh --res=2556x1179 --seq=tools/seq/hd_worlds.json`.

## Rules the helpers encode (do not fight them)

* **Whole ramp steps, no Bayer.** `put()` rounds. A fractional level at 2x is a
  checkerboard over four times the texels.
* **Grain in 2x2 cells** (`fill(..., cell=2)`); per-texel grain reads as static.
* **Wrap fills, clip objects.** `put`/`blob(wrap=True)` wrap; `put_c`,
  `blob(wrap=False)` clip. A fill must tile with itself and its own variants.
* **Edges are relative.** `shift()` moves a texel along whatever ramp it is on.
  Overdrawing a flat band (as 1x did) erases the detail 2x exists to show.
* **Line weight.** Inked tiles (ladders, one-ways, hazards: `tiles_p3.INKED`)
  are lifted a step and outlined by `hd_tilekit.ink_interactive()`: one texel,
  plus a second on the shadow side, like the 2x Kaya. Don't ink them yourself.
* **Light from the upper left**, a world unit is `WU` (2) texels, a tile `N`
  (32). Distances you take from a 1x painter are world units: multiply.
* **Gameplay must read at a glance**: solid vs background (backgrounds stay at
  the dark, low-contrast end), one-way and ladder and hazard inked, water
  continuous, breakables carrying a visible crack, voids empty.

## The jungle, as the worked example

`hd_tiles_jungle.py`, in order:

1. the eleven approved look-sample painters (grass top, dirt, stone, platform,
   vine, water x2, spikes, crate, bg leaves, trunk), unchanged in design except
   water's seed handling (see its docstring);
2. the rest of the jungle: mossy stone (`_moss_cap`), bg rock, bg dark, the two
   authored grass edges (`_sod_over_shoulder`, shared with the sod dresser), the
   rope bridge;
3. the overworld (hub grass, path, water, tree), top-down lit;
4. the shared tiles: lava (a periodic plate/seam pattern), tread plate, switch
   blocks on and off;
5. dressers `dress_earth/sod/stone/bg_rock/hub_grass/hub_path`;
6. accents (`pebble`, `chip`, `crack_down`, `flower`);
7. the five shared decorations;
8. the registrations, one `tile(id, seed)` line per id, in id order.

`hd_tiles_verbs.py` is a second, smaller example: tiles built on another
module's painters (currents on `t_water_hd`, cracked walls on stone/dirt).
