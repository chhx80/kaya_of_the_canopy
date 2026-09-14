#!/usr/bin/env python3
"""Generates all original pixel art for Kaya of the Canopy.

Everything here is authored from scratch (ASCII grids + deterministic
procedural texture, lit through the ramps in `tools/art/palette.py`).
Re-run with:  tools/genart.sh
Output goes to assets/tiles/, assets/sprites/ and assets/fonts/.

This file is only the running order. The generators themselves live in
`tools/art/`:

    art.palette    ramps, dither(), blob(), crack(), auto_shade()
    art.tiles      the tileset
    art.sprites    player forms, enemies, boss, pickups, props, projectiles
    art.backdrops  title bg, parallax planes, lighting art, logo, font, icons
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from art import backdrops, palette, sprites, tiles     # noqa: E402

# Re-exported so `from gen_art import ...` keeps working for the small scripts
# that reach into the art (tools/proto_shade.py, tools/gen_store_shots.py).
PAL = palette.PAL
grid = palette.grid
blit = palette.blit
sheet = palette.sheet
K_IDLE = sprites.K_IDLE
# The beetle's frames are composed now, so there is no single grid to re-export
# — tools/proto_shade.py wants frame 0.
E_WALKER1 = sprites.walker(0)


def main():
    palette.write_manifest()
    tiles.build_tileset()
    sprites.build_sprites()
    sprites.build_boss()
    backdrops.build_font()
    backdrops.build_logo()
    backdrops.build_title_bg()
    backdrops.build_backdrops()
    backdrops.build_light_art()
    backdrops.build_icon()
    backdrops.build_store_icons()
    print("done")


if __name__ == "__main__":
    main()
