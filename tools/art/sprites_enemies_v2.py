#!/usr/bin/env python3
"""The three enemies added for the twenty-level plan — original art, 16x16.

Same rules as `tools/art/sprites.py`: ASCII grids in the shared character
vocabulary, re-lit through `palette.auto_shade()` from the upper left, and no
colour that is not a step on a material ramp.

Each sheet is one row of 16x16 cells, and the frame indices below are the
contract with `data/enemies/<id>.json` — `tests/test_art_palette.gd` asserts
every frame an animation names exists in the sheet, so the two cannot drift.

    enemy_charger  0-1 patrol, 2-3 the wind-up, 4-5 the charge, 6 dazed
    enemy_dropper  0 cling, 1-2 the shiver, 3 falling, 4-5 crawl
    enemy_flyer    0-3 the wing beat

The three silhouettes are deliberately unlike the four that already exist: the
boar is wide and low with a bristle crest, the tick is a hanging teardrop with
legs on top, and the wasp is the only enemy in the game with wings.

Run standalone:  tools/env.sh's $PYVENV tools/art/sprites_enemies_v2.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from art import palette                                     # noqa: E402
from art.palette import auto_shade, sheet                   # noqa: E402
from art.sprites import cell                                # noqa: E402

# ---------------------------------------------------------------- materials
# Character -> (ramp, base level); auto_shade() does the rest. Every one of
# these is a ramp reference, so nothing here can invent a colour.
#
# The palettes are chosen to keep the seven enemies apart at a glance: the
# beetle is purple, the hopper ember, the bloom purple-on-green, the piranha
# cyan. That leaves brown, stone grey and gold unclaimed.
CHARGER = {
    'm': ("dirt", 2.0),       # hide
    'M': ("dirt", 4.0),       # lit hide, snout and shoulder
    'r': ("ember", 3.2),      # bristle crest — the "this one hurts" colour
    'y': ("gold", 4.8),       # eye
    'w': ("metal", 6.0),      # tusks
}
DROPPER = {
    'a': ("stone", 2.0),      # carapace
    'A': ("stone", 4.2),      # lit rim
    'y': ("gold", 4.8),       # eyes
    'w': ("metal", 6.0),      # claws and mandibles
}
FLYER = {
    'o': ("gold", 2.4),       # dark band
    'y': ("gold", 4.8),       # lit band
    'r': ("ember", 3.4),      # eye
    'A': ("metal", 4.0),      # wing
    'w': ("metal", 6.0),      # wing leading edge
}

# ---------------------------------------------------------------- charger
# THE THORN BOAR. Seven beats that all stand on row 15, so the charge never
# looks like it left the floor:
#
#   patrol   0-1  head level, crest flat, legs alternating
#   wind-up  2-3  the crest lifts and the head drops — two escalating frames,
#                 and data/enemies/charger.json holds the second for the rest
#                 of the telegraph ("loop": false)
#   charge   4-5  head down, crest swept back, legs blurred into a stride
#   dazed    6    head up, crest flat, feet splayed — the punish window
#
# The tusks ('w', the brightest step on the metal ramp) stick out past the
# snout in every frame: at 16x16 the silhouette is all a player reads, and the
# tusk is the only part of the boar that says which end hurts.
C_PATROL_A = cell([
    "",
    "",
    "",
    ".....r..r.r.....",
    "...krkrkrkrk....",
    "..kmmmmmmmmmkk..",
    ".kmmmmmmmmmmmMk.",
    ".kmmmmmmmmmMMMMk",
    ".kmmmmmmmmmMyMMk",
    ".kmmmmmmmmmMMMMk",
    ".kmmmmmmmmmmMMkk",
    "..kmmmmmmmmmkkww",
    "..kkmmmmmmmkkkwk",
    "..kk.kkk.kk.kk..",
    "..kM.MkM.Mk.k...",
    "..kk.kkk.kk.k...",
])
C_PATROL_B = cell([
    "",
    "",
    "",
    ".....r.r..r.....",
    "...krkrkrkrk....",
    "..kmmmmmmmmmkk..",
    ".kmmmmmmmmmmmMk.",
    ".kmmmmmmmmmMMMMk",
    ".kmmmmmmmmmMyMMk",
    ".kmmmmmmmmmMMMMk",
    ".kmmmmmmmmmmMMkk",
    "..kmmmmmmmmmkkww",
    "..kkmmmmmmmkkkwk",
    "...kk.kk.kkk.k..",
    "...kM.Mk.MkM.k..",
    "...kk.kk.kkk.k..",
])
C_WIND_A = cell([
    "",
    "",
    "....r..r..r.....",
    "....r.rr.rr.....",
    "...krkrkrkrk....",
    "..kmmmmmmmmmkk..",
    "..kmmmmmmmmmmMk.",
    "..kmmmmmmmmMMMMk",
    "..kmmmmmmmmMyMMk",
    "..kmmmmmmmmMMMMk",
    "..kmmmmmmmmmMMkk",
    "...kmmmmmmmmkkww",
    "...kkmmmmmmkkkwk",
    "...kk.kkk.kk.k..",
    "...kM.MkM.Mk.k..",
    "...kk.kkk.kk.k..",
])
C_WIND_B = cell([
    "..r..r...r..r...",
    "..r..r...r..r...",
    "..r..r..rr..r...",
    "..rr.rr.rr.rr...",
    "..krkrkrkrkrk...",
    "..kmmmmmmmmmkk..",
    "..kmmmmmmmmmmMk.",
    "..kmmmmmmmmMMMMk",
    "..kmmmmmmmmMyMMk",
    "..kmmmmmmmmMMMMk",
    "..kmmmmmmmmmMMkk",
    "...kmmmmmmmmkkww",
    "...kkmmmmmmkkkwk",
    "...kkk.kkk.k.k..",
    "...kMk.kMk.k.k..",
    "...kkk.kkk.k.k..",
])
C_CHARGE_A = cell([
    "",
    "",
    "",
    "",
    "..rrrrrr........",
    "..krkrkrkrkk....",
    "..kmmmmmmmmmkk..",
    ".kmmmmmmmmmmmMk.",
    ".kmmmmmmmmmMMMMk",
    ".kmmmmmmmmmMyMMk",
    ".kmmmmmmmmmMMMkk",
    ".kmmmmmmmmmmkkww",
    "..kkmmmmmmmkkkwk",
    ".kk.kkk..kkk.k..",
    ".kM.MkM..MkM.k..",
    ".kk.kkk..kkk.k..",
])
C_CHARGE_B = cell([
    "",
    "",
    "",
    "",
    "..rrrrrr........",
    "..krkrkrkrkk....",
    "..kmmmmmmmmmkk..",
    ".kmmmmmmmmmmmMk.",
    ".kmmmmmmmmmMMMMk",
    ".kmmmmmmmmmMyMMk",
    ".kmmmmmmmmmMMMkk",
    ".kmmmmmmmmmmkkww",
    "..kkmmmmmmmkkkwk",
    "..kkkk..kkkk....",
    ".kMMMMk.kMMk....",
    ".kkkkkk.kkkk....",
])
C_DAZED = cell([
    "",
    "",
    "",
    "",
    "......r..r......",
    "....krkkrkk.....",
    "...kmmmmmmmkk...",
    "..kmmmmmmmmmmMk.",
    "..kmmmmmmmmMMMMk",
    "..kmmmmmmmmMyMMk",
    "..kmmmmmmmmMMMkk",
    "..kmmmmmmmmmkkww",
    "...kkmmmmmmkkkwk",
    ".kkk.kkk.kkk.k..",
    "kMMk.kMk.kMMk...",
    "kkkk.kkk.kkkk...",
])

# ---------------------------------------------------------------- dropper
# THE HOLLOW TICK. Authored hanging: four legs hook *upward* out of the
# shoulders into the ceiling and the body is a teardrop that swells downward,
# so the silhouette reads upside-down even standing still. The shiver shunts
# the whole body a pixel left and right without moving the grip — it is the
# only frame pair in the game that animates by translation, because a tick
# about to let go should look like it is losing its hold.
_D_BODY = [
    "...kkaaaaaakk...",
    "..kaaaaaaaaaak..",
    ".kaaaaaaaaaaaak.",
    ".kaayaaaaaayaak.",
    ".kaaaaAAAAaaaak.",
    ".kaaaaAAAAaaaak.",
    ".kaaaaaaaaaaaak.",
    "..kaaaaaaaaaak..",
    "..kaaaaaaaaak...",
    "...kaaaaaaak....",
    "....kaaaaak.....",
    ".....kwwwk......",
    "......kwk.......",
]
_D_GRIP = [
    "..w..w....w..w..",
    "..kw.kw..kw.kw..",
    "...kwwkkkkwwk...",
]


def _tick(shift):
    """The hanging body, offset `shift` pixels, under a fixed ceiling grip."""
    rows = list(_D_GRIP)
    for r in _D_BODY:
        if shift < 0:
            rows.append(r[-shift:] + "." * -shift)
        elif shift > 0:
            rows.append("." * shift + r[:-shift])
        else:
            rows.append(r)
    return cell(rows)


D_CLING = _tick(0)
D_SHIVER_A = _tick(-1)
D_SHIVER_B = _tick(1)
D_FALL = cell([
    "",
    "....w......w....",
    "...kwk....kwk...",
    "...kkaaaaaakk...",
    "..kaaaaaaaaaak..",
    ".kaaaaaaaaaaaak.",
    ".kaayaaaaaayaak.",
    ".kaaaaAAAAaaaak.",
    ".kaaaaAAAAaaaak.",
    ".kaaaaaaaaaaaak.",
    ".kaaaaaaaaaaaak.",
    "..kaaaaaaaaaak..",
    "..kwaaaaaaaawk..",
    ".kwwkkwwwwkkwwk.",
    ".kwk..kwwk..kwk.",
    "......kkkk......",
])
_D_STANDING = [
    "...kkaaaaaakk...",
    "..kaaaaaaaaaak..",
    ".kaaaaaaaaaaaak.",
    ".kaayaaaaaayaak.",
    ".kaaaaAAAAaaaak.",
    ".kaaaaAAAAaaaak.",
    ".kaaaaaaaaaaaak.",
    "..kaaaaaaaaaak..",
    "..kkaaaaaaaakk..",
]
D_CRAWL_A = cell(["", "", ""] + _D_STANDING + [
    ".kw.kw....wk.wk.",
    ".kw..kw..wk..wk.",
    ".kk..kk..kk..kk.",
])
D_CRAWL_B = cell(["", "", ""] + _D_STANDING + [
    "kw..kw....wk..wk",
    "kw...kw..wk...wk",
    "kk...kk..kk...kk",
])

# ---------------------------------------------------------------- flyer
# THE CANOPY WASP. Authored facing right, four beats of wing. The banded body
# never moves between frames — only the wings do — so a patrolling wasp reads
# as a steady line of flight rather than a bob, which is what
# src/enemies/flyer.gd needs it to be: the path is the threat, not a lunge.
# Abdomen, then an ink waist, then a head with one ember eye. The ink columns
# inside the abdomen are the bands: at 16x16 a stripe has to be a hole in the
# silhouette to read as a stripe at all.
_F_BODY = [
    ".kkkkkkkkkkkkkk.",
    ".koyykyykyokkork",
    "koyyykyykyyokrrk",
    ".koyykyykyokkork",
    ".kkkkkkkkkkkkkk.",
]


def _wasp(upper, lower):
    """Wings above (rows 1-5) and below (rows 11-15) a fixed body."""
    rows = ["." * 16] * 16
    for i, r in enumerate(upper):
        rows[6 - len(upper) + i] = r
    for i, r in enumerate(_F_BODY):
        rows[6 + i] = r
    for i, r in enumerate(lower):
        rows[11 + i] = r
    return cell(rows)


F_UP = _wasp([
    "..kwwk..........",
    ".kwAAwk.........",
    ".kwAAAwk........",
    "..kwAAAwk.......",
    "...kwAAwk.......",
], [
    "....kwAwk.......",
    ".....kwwk.......",
])
F_MID_A = _wasp([
    "..kwwwwk........",
    "..kwAAAAwk......",
    "...kwAAAwkk.....",
], [
    "...kwAAAwk......",
    "....kwAAwk......",
    ".....kwwk.......",
])
F_DOWN = _wasp([
    "..kwwwwwwk......",
    "...kwAAAwk......",
], [
    "..kwAAAAwk......",
    ".kwAAAAwk.......",
    ".kwAAAwk........",
    "..kwwwk.........",
])
F_MID_B = _wasp([
    "..kwwwwk........",
    "..kwAAAAwk......",
    "...kwAAAwkk.....",
], [
    "...kwAAAwk......",
    "....kwAAwk......",
    ".....kwwk.......",
])


def lit(cells, mapping, **kw):
    return [auto_shade(c, mapping, **kw) for c in cells]


def build():
    # depth=3 everywhere: all three are organic shapes that should read as
    # round, the same call the beetle and the hopper make.
    sheet("enemy_charger",
          lit([C_PATROL_A, C_PATROL_B, C_WIND_A, C_WIND_B,
               C_CHARGE_A, C_CHARGE_B, C_DAZED], CHARGER), 16, 16)
    sheet("enemy_dropper",
          lit([D_CLING, D_SHIVER_A, D_SHIVER_B, D_FALL,
               D_CRAWL_A, D_CRAWL_B], DROPPER), 16, 16)
    sheet("enemy_flyer",
          lit([F_UP, F_MID_A, F_DOWN, F_MID_B], FLYER), 16, 16)
    print("enemies v2 written to %s" % palette.SPRITES)


if __name__ == "__main__":
    build()
