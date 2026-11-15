"""5. THE OBSIDIAN NEST (ids 280-291), drawn natively at 2x.

Not redrawn yet: every tile of this world still ships as its 1x painting
through palette.upscale(). To redraw it, follow docs/hd-tiles-howto.md, with
hd_tiles_jungle.py as the worked example. In short, in THIS file only:

  * one painter per tile, registered with `tile(tid, seed)` (the seed its
    T_AT line in tiles.py uses, which is also its V spec's seeds[0]);
  * the 2x twin of each edge dresser this world's rims name, registered with
    `dresser("<1x name>\")`: dress_nest, dress_nest_hot, dress_nest_bg;
  * accents for its groups (nest, nest_bg) in `ACCENTS` / `CAP_ACCENTS`;
  * the 2x twin of each world-only decoration with `decoration("<1x name>")`:
    d_ember_seam, d_chain_hang. (d_crack, d_moss, d_roots, d_bones and d_vines are already done,
    in hd_tiles_jungle.py.)

A tile becomes native the moment it is registered; tiles.py refuses to build
a native material whose dresser, accents or decorations have no 2x twin.
"""
from .hd_tilekit import tile  # noqa: F401
