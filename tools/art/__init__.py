"""Art generators for Kaya of the Canopy.

Split out of the old monolithic ``tools/gen_art.py`` so the phases of the art
overhaul (docs/art-direction.md) can be worked on independently:

    palette    ramps, dithering and the shading primitives everything else uses
    tiles      the 16x16 tileset
    sprites    player forms, enemies, the boss, pickups, props, projectiles
    backdrops  title background, parallax layers, logo, font, icons

``tools/gen_art.py`` remains the entry point and just calls into these.
"""
