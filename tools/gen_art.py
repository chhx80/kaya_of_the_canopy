#!/usr/bin/env python3
"""Generates all original pixel art for Kaya of the Canopy.

Everything here is authored from scratch (ASCII grids + deterministic
procedural texture). Re-run with:  tools/genart.sh
Output goes to assets/tiles/ and assets/sprites/.
"""
import math, os, random
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TILES = os.path.join(ROOT, "assets", "tiles")
SPRITES = os.path.join(ROOT, "assets", "sprites")
FONTS = os.path.join(ROOT, "assets", "fonts")
for d in (TILES, SPRITES, FONTS):
    os.makedirs(d, exist_ok=True)

# ---------------------------------------------------------------- palette
PAL = {
    '.': (0, 0, 0, 0),
    'k': (0x0d, 0x0b, 0x0f, 255),   # near-black outline
    'd': (0x1a, 0x1c, 0x2c, 255),   # dark blue-grey
    'n': (0x2b, 0x35, 0x56, 255),   # navy
    'b': (0x3b, 0x6e, 0xa5, 255),   # blue
    'c': (0x41, 0xa6, 0xb5, 255),   # cyan
    'g': (0x14, 0x47, 0x2e, 255),   # dark green
    'G': (0x2a, 0x7a, 0x3f, 255),   # green
    'l': (0x58, 0xc1, 0x5a, 255),   # light green
    'y': (0xf2, 0xd5, 0x65, 255),   # yellow
    'o': (0xe0, 0x8c, 0x3a, 255),   # orange
    'r': (0xc0, 0x4a, 0x3a, 255),   # red
    'm': (0x6b, 0x43, 0x26, 255),   # brown
    'M': (0xa0, 0x6a, 0x3c, 255),   # light brown
    'a': (0x6a, 0x6a, 0x72, 255),   # grey
    'A': (0xb8, 0xb0, 0xa8, 255),   # light grey
    'w': (0xf4, 0xf0, 0xe6, 255),   # off-white
    's': (0xe8, 0xb4, 0x8a, 255),   # skin
    'p': (0x7a, 0x4a, 0x8c, 255),   # purple
}

def grid(rows):
    """ASCII rows -> list of (x, y, rgba)."""
    out = []
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            col = PAL[ch]
            if col[3]:
                out.append((x, y, col))
    return out

def blit(img, ox, oy, pixels):
    for x, y, col in pixels:
        img.putpixel((ox + x, oy + y), col)

def sheet(name, cells, cw, ch, cols=None, folder=SPRITES):
    """cells: list of ASCII-row-lists. Packs them left to right."""
    cols = cols or len(cells)
    rows = (len(cells) + cols - 1) // cols
    img = Image.new("RGBA", (cw * cols, ch * rows), (0, 0, 0, 0))
    for i, cell in enumerate(cells):
        blit(img, (i % cols) * cw, (i // cols) * ch, grid(cell))
    img.save(os.path.join(folder, name + ".png"))
    return img

# ---------------------------------------------------------------- tileset
# Procedural texture helpers keep the rock/dirt from looking flat without
# forcing us to hand-place 256 pixels per tile.
def noisy(base, speckles, seed, w=16, h=16):
    rnd = random.Random(seed)
    px = [[base for _ in range(w)] for _ in range(h)]
    for col, count in speckles:
        for _ in range(count):
            px[rnd.randrange(h)][rnd.randrange(w)] = col
    return px

def to_rows(px):
    return ["".join(r) for r in px]

def dirt(seed=1):
    return to_rows(noisy('m', [('k', 14), ('M', 10)], seed))

def stone(seed=2):
    px = noisy('a', [('d', 16), ('A', 10)], seed)
    for x in range(16):
        px[0][x] = 'A'
        px[15][x] = 'd'
    return to_rows(px)

TILE_DEFS = []

def T(rows):
    assert len(rows) == 16 and all(len(r) == 16 for r in rows), len(rows)
    TILE_DEFS.append(rows)

# 0 empty
T(["." * 16] * 16)
# 1 dirt
T(dirt(11))
# 2 grass top
_g = dirt(12)
_g[0] = "llllllllllllllll"
_g[1] = "lGlGGlllGlGGllGl"
_g[2] = "GmGmmGGmGmmGGmGm"
T(_g)
# 3 stone
T(stone(21))
# 4 stone top (mossy)
_s = stone(22)
_s[0] = "gGggGgggGgGggGgg"
_s[1] = "aGaaaagaaaaGaaaa"
T(_s)
# 5 wood one-way platform
T([
    "MMMMMMMMMMMMMMMM",
    "mMMmMMMmMMmMMMmM",
    "mmmmmmmmmmmmmmmm",
    "kkkkkkkkkkkkkkkk",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
])
# 6 vine ladder
T([
    "......GG.G......",
    ".....GllGG......",
    "....GlGG.GG.....",
    "..GGGlG...GGG...",
    "GGGllG.....lGGGG",
    "..GGGG.....GGG..",
    "......GG.GG.....",
    "......GllG......",
    "......GllG......",
    ".....GGllGG.....",
    "..GGGGlGGGGGG...",
    "GGGllG...GlGGGG.",
    "..GGG.....GGG...",
    "......GG.GG.....",
    "......GllG......",
    "......GGGG......",
])
# 7 water surface
T([
    "cccccccccccccccc",
    "wccwwcccccwwcccc",
    "cccccccwwccccccc",
    "bcccccccccccbccc",
    "bbbcbbbbbbbbbbbb",
    "bbbbbbbbbbbbbbbb",
    "bbbbbbbbnbbbbbbb",
    "bbbnbbbbbbbbbbbb",
    "bbbbbbbbbbbbbbbb",
    "bbbbbbbbbbbnbbbb",
    "bbbbbbbbbbbbbbbb",
    "bnbbbbbbbbbbbbbb",
    "bbbbbbbbbbbbbbbb",
    "bbbbbbbbbbbbbnbb",
    "bbbbbbbbbbbbbbbb",
    "bbbbbbbbbbbbbbbb",
])
# 8 water body
T(to_rows(noisy('b', [('n', 12), ('c', 4)], 31)))
# 9 spikes
T([
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    ".A....A....A....",
    ".A....A....A....",
    "AwA..AwA..AwA...",
    "AwA..AwA..AwA...",
    "AwaA.AwaAAAwaA..",
    "AwaA.AwaAAAwaA..",
    "AwaaAAwaaAAwaaA.",
    "AwaaAAwaaAAwaaA.",
    "aaaaaaaaaaaaaaaa",
    "kkkkkkkkkkkkkkkk",
])
# 10 crate (breakable)
T([
    "MMMMMMMMMMMMMMMM",
    "MmmmmmmmmmmmmmmM",
    "MmMMmmmmmmmmMMmM",
    "MmMkMMmmmmMMkMmM",
    "MmmkkMMmmMMkkmmM",
    "MmmmkkMMMMkkmmmM",
    "MmmmmkkMMkkmmmmM",
    "MmmmmmkkkkmmmmmM",
    "MmmmmmkkkkmmmmmM",
    "MmmmmkkMMkkmmmmM",
    "MmmmkkMMMMkkmmmM",
    "MmmkkMMmmMMkkmmM",
    "MmMkMMmmmmMMkMmM",
    "MmMMmmmmmmmmMMmM",
    "MmmmmmmmmmmmmmmM",
    "MMMMMMMMMMMMMMMM",
])
# 11 switch block A (on)
T([
    "yyyyyyyyyyyyyyyy",
    "yoooooooooooooy.",
    "yoyyyyyyyyyyyoy.",
    "yoyooooooooo.oy.",
    "yoyo.......o.oy.",
    "yoyo.yyyyy.o.oy.",
    "yoyo.y...y.o.oy.",
    "yoyo.y...y.o.oy.",
    "yoyo.y...y.o.oy.",
    "yoyo.yyyyy.o.oy.",
    "yoyo.......o.oy.",
    "yoyooooooooo.oy.",
    "yoyyyyyyyyyyyoy.",
    "yooooooooooooooy",
    "yyyyyyyyyyyyyyyy",
    "kkkkkkkkkkkkkkkk",
])
# 12 switch block B (on)
T([
    "pppppppppppppppp",
    "pnnnnnnnnnnnnnp.",
    "pnppppppppppppp.",
    "pnpnnnnnnnnnnpp.",
    "pnpn.......npp..",
    "pnpn.ppppp.npp..",
    "pnpn.p...p.npp..",
    "pnpn.p...p.npp..",
    "pnpn.p...p.npp..",
    "pnpn.ppppp.npp..",
    "pnpn.......npp..",
    "pnpnnnnnnnnnnpp.",
    "pnppppppppppppp.",
    "pnnnnnnnnnnnnnnp",
    "pppppppppppppppp",
    "kkkkkkkkkkkkkkkk",
])
# 13 background leaves
T(to_rows(noisy('g', [('G', 26), ('d', 20)], 41)))
# 14 tree trunk
T([
    "dmMMmdddddmMMmdd",
    "dmMMmdddddmMMmdd",
    "dmMmmdddddmMmmdd",
    "dmMmmddddmmMmmdd",
    "dmMMmdddddmMMmdd",
    "dmMMmmdddmmMMmdd",
    "dmmMmdddddmMmmdd",
    "dmMMmdddddmMMmdd",
    "dmMMmdddddmMMmdd",
    "dmMmmddddmmMmmdd",
    "dmMMmdddddmMMmdd",
    "dmMMmmdddmmMMmdd",
    "dmmMmdddddmMmmdd",
    "dmMMmdddddmMMmdd",
    "dmMMmdddddmMMmdd",
    "dmMmmdddddmMmmdd",
])
# 15 background rock
T(to_rows(noisy('d', [('n', 18), ('k', 14)], 51)))
# 16 grass left edge
_gl = dirt(13)
for y in range(16):
    _gl[y] = "l" + _gl[y][1:]
_gl[0] = "llllllllllllllll"
_gl[1] = "lGGlGlllGlGGllGl"
T(_gl)
# 17 grass right edge
_gr = dirt(14)
for y in range(16):
    _gr[y] = _gr[y][:15] + "l"
_gr[0] = "llllllllllllllll"
_gr[1] = "lGlGGlllGlGGlGGl"
T(_gr)
# 18 dark background fill
T(to_rows(noisy('d', [('k', 10)], 61)))
# 19 rope bridge
T([
    "................",
    "................",
    "mm............mm",
    "MMmm........mmMM",
    "..MMmmmmmmmmMM..",
    "....MMMMMMMM....",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
])
# 20 hub grass (overworld): darker base, tufts and the odd flower
_hg = noisy('g', [('G', 40), ('l', 10)], 71)
for (tx, ty, c) in ((3, 4, 'l'), (4, 4, 'l'), (3, 5, 'G'), (11, 9, 'l'), (12, 9, 'l'),
                    (11, 10, 'G'), (7, 12, 'l'), (8, 12, 'l')):
    _hg[ty][tx] = c
_hg[2][9] = 'y'; _hg[13][4] = 'y'; _hg[6][13] = 'r'
T(to_rows(_hg))
# 21 hub path: packed sand with pebbles
T(to_rows(noisy('M', [('y', 22), ('m', 10), ('A', 4)], 72)))
# 22 hub water
T(to_rows(noisy('b', [('c', 10), ('n', 10)], 73)))
# 23 hub tree canopy
T([
    "....gggggggg....",
    "..ggGGGGGGGGgg..",
    ".gGGllGGllGGGGg.",
    "gGGllGGGGGGllGGg",
    "gGGGGGGllGGGGGGg",
    "gGGllGGGGGGllGGg",
    "gGGGGGGllGGGGGGg",
    ".gGGllGGGGllGGg.",
    "..ggGGGGGGGGgg..",
    "....gggmmggg....",
    "......mMMm......",
    "......mMMm......",
    "......mMMm......",
    ".....gmMMmg.....",
    "....GGmMMmGG....",
    "...GGGmmmmGGG...",
])
# 24 lava / hot rock hazard
T([
    "oooooooooooooooo",
    "yooyoooooyooooyo",
    "orooooorooooooro",
    "rrrorrrrrrrorrrr",
    "rrrrrrrrrrrrrrrr",
    "krrrrrkrrrrrrrrr",
    "rrrrrrrrrrkrrrrr",
    "rrrkrrrrrrrrrrrr",
    "rrrrrrrrrrrrrkrr",
    "rrrrrrkrrrrrrrrr",
    "rrrrrrrrrrrrrrrr",
    "rrkrrrrrrrrrrrrr",
    "rrrrrrrrrkrrrrrr",
    "rrrrrrrrrrrrrrrr",
    "rrrrkrrrrrrrrrrr",
    "rrrrrrrrrrrrrkrr",
])
# 25 metal plate
T([
    "AAAAAAAAAAAAAAAA",
    "AaaaaaaaaaaaaaaA",
    "AaAaaaaaaaaaaAaA",
    "AaaaaaaaaaaaaaaA",
    "AaaaaaaaaaaaaaaA",
    "AaaaaaaaaaaaaaaA",
    "AaAaaaaaaaaaaAaA",
    "AaaaaaaaaaaaaaaA",
    "AaaaaaaaaaaaaaaA",
    "AaAaaaaaaaaaaAaA",
    "AaaaaaaaaaaaaaaA",
    "AaaaaaaaaaaaaaaA",
    "AaaaaaaaaaaaaaaA",
    "AaAaaaaaaaaaaAaA",
    "AaaaaaaaaaaaaaaA",
    "dddddddddddddddd",
])
# 26 switch block A (off / ghost)
T([
    "................",
    ".y.y.y.y.y.y.y..",
    "................",
    "y..............y",
    "................",
    ".y............y.",
    "................",
    "y..............y",
    "................",
    ".y............y.",
    "................",
    "y..............y",
    "................",
    ".y.y.y.y.y.y.y..",
    "................",
    "................",
])
# 27 switch block B (off / ghost)
T([
    "................",
    ".p.p.p.p.p.p.p..",
    "................",
    "p..............p",
    "................",
    ".p............p.",
    "................",
    "p..............p",
    "................",
    ".p............p.",
    "................",
    "p..............p",
    "................",
    ".p.p.p.p.p.p.p..",
    "................",
    "................",
])

def build_tileset():
    cols = 16
    rows = (len(TILE_DEFS) + cols - 1) // cols
    img = Image.new("RGBA", (cols * 16, rows * 16), (0, 0, 0, 0))
    for i, t in enumerate(TILE_DEFS):
        blit(img, (i % cols) * 16, (i // cols) * 16, grid(t))
    img.save(os.path.join(TILES, "tileset.png"))
    print("tileset.png  %d tiles" % len(TILE_DEFS))

# ---------------------------------------------------------------- player
# Kaya: 16 wide x 24 tall. Ponytail, green tunic, satchel.
K_IDLE = [
    "......kkkkk.....",
    ".....kmmmmmk....",
    "....kmMMMMMmk...",
    "....kmMsssMmk...",
    "....kMsssssMk...",
    "....kskwskwsk...",
    "....kssssssskk..",
    ".....kskkkskmk..",
    "....kkksssskkk..",
    "...klGGGGGGGlk..",
    "..klGGlGGGlGGlk.",
    "..klGGGGGGGGGlk.",
    "..kMGGGGGGGGGMk.",
    "...kGGGGGGGGGk..",
    "...kyyyyyyyyyk..",
    "....kGGGGGGGk...",
    "....ksssksssk...",
    "....kssskssssk..",
    "....kssskssssk..",
    "....kssskssssk..",
    "...kmmmkkmmmmk..",
    "..kmMMmkkmMMMmk.",
    "..kmmmmkkmmmmmk.",
    "..kkkkk..kkkkkk.",
]
K_RUN1 = [
    "......kkkkk.....",
    ".....kmmmmmk....",
    "....kmMMMMMmk...",
    "....kmMsssMmk...",
    "....kMsssssMk...",
    "....kskwskwsk...",
    "....kssssssskk..",
    ".....kskkkskmk..",
    "....kkksssskkk..",
    "..sklGGGGGGGlk..",
    ".skklGGlGGGlGGlk",
    ".sk.lGGGGGGGGGlk",
    "....kMGGGGGGGGMk",
    "....kGGGGGGGGGk.",
    "....kyyyyyyyyk..",
    "....kGGGGGGGk...",
    "...kssskssskk...",
    "..kssskkssssk...",
    "..ksskk.kssssk..",
    ".kssk....kssssk.",
    ".kmmk.....kmmmk.",
    "kmMMmk...kmMMMmk",
    "kmmmmk...kmmmmmk",
    ".kkkk.....kkkkk.",
]
K_RUN2 = [
    "......kkkkk.....",
    ".....kmmmmmk....",
    "....kmMMMMMmk...",
    "....kmMsssMmk...",
    "....kMsssssMk...",
    "....kskwskwsk...",
    "....kssssssskk..",
    ".....kskkkskmk..",
    "....kkksssskkk..",
    "...klGGGGGGGlk..",
    "..klGGlGGGlGGlks",
    "..klGGGGGGGGGlks",
    "..kMGGGGGGGGGMk.",
    "...kGGGGGGGGGk..",
    "...kyyyyyyyyyk..",
    "....kGGGGGGGk...",
    "....ksssksssk...",
    "....kssskssssk..",
    "....ksssksssk...",
    "....kssskssk....",
    "...kmmmkkmmk....",
    "..kmMMmkkmMmk...",
    "..kmmmmkkmmmk...",
    "..kkkkk..kkkk...",
]
K_RUN3 = [
    "......kkkkk.....",
    ".....kmmmmmk....",
    "....kmMMMMMmk...",
    "....kmMsssMmk...",
    "....kMsssssMk...",
    "....kskwskwsk...",
    "....kssssssskk..",
    ".....kskkkskmk..",
    "....kkksssskkk..",
    "...klGGGGGGGlk..",
    "..klGGlGGGlGGlk.",
    "..klGGGGGGGGGlk.",
    "..kMGGGGGGGGGMk.",
    "...kGGGGGGGGGk..",
    "...kyyyyyyyyyk..",
    "...kGGGGGGGGGk..",
    "..kssskkksssk...",
    ".kssskk.kssssk..",
    ".ksskk...kssssk.",
    "kssk......kssssk",
    "kmmk.......kmmmk",
    "kmMmk.....kmMMmk",
    "kmmmk.....kmmmmk",
    ".kkk.......kkkk.",
]
K_JUMP = [
    "......kkkkk.....",
    ".....kmmmmmk....",
    "....kmMMMMMmk...",
    "....kmMsssMmk...",
    "....kMsssssMk...",
    "....kskwskwsk...",
    "....kssssssskk..",
    "s....kskkkskmk..",
    "sk..kkksssskkk..",
    "sk.klGGGGGGGlks.",
    ".sklGGlGGGlGGlks",
    "..klGGGGGGGGGlk.",
    "..kMGGGGGGGGGMk.",
    "...kGGGGGGGGGk..",
    "...kyyyyyyyyyk..",
    "...kGGGGGGGGGk..",
    "..kssskkksssk...",
    ".kssskk..kssk...",
    ".kssk.....kssk..",
    "kmmk......kssk..",
    "kmMmk.....kmmk..",
    "kmmmk....kmMMmk.",
    ".kkk.....kmmmmk.",
    "..........kkkkk.",
]
K_CLIMB1 = [
    "......kkkkk.....",
    ".....kmmmmmk....",
    "....kmMMMMMmk...",
    "....kmMsssMmk...",
    "....kMsssssMk...",
    "....kskkskksk...",
    "....kssssssskk..",
    ".....ksssssk.k..",
    "..s.kkksssskkk..",
    "..sklGGGGGGGlk..",
    "..sklGGGGGGGlks.",
    "...klGGGGGGGlks.",
    "...kMGGGGGGGMk..",
    "...kGGGGGGGGGk..",
    "...kyyyyyyyyyk..",
    "....kGGGGGGGk...",
    "....ksssksssk...",
    "....kssskssssk..",
    "....kssskssssk..",
    "....kssskssssk..",
    "....kmmmkkmmmk..",
    "...kmMMmkkmMMmk.",
    "...kmmmmkkmmmmk.",
    "...kkkkk..kkkkk.",
]
K_CLIMB2 = [
    "......kkkkk.....",
    ".....kmmmmmk....",
    "....kmMMMMMmk...",
    "....kmMsssMmk...",
    "....kMsssssMk...",
    "....kskkskksk...",
    "....kssssssskk..",
    ".....ksssssk.k..",
    "...kkksssskkk...",
    "..sklGGGGGGGlks.",
    "..sklGGGGGGGlks.",
    "...klGGGGGGGlk..",
    "...kMGGGGGGGMk..",
    "...kGGGGGGGGGk..",
    "...kyyyyyyyyyk..",
    "....kGGGGGGGk...",
    "....ksssksssk...",
    "....kssskssssk..",
    "...kssskkssssk..",
    "...ksskk.kssk...",
    "...kmmk..kmmk...",
    "..kmMMmk.kmMMmk.",
    "..kmmmmk.kmmmmk.",
    "..kkkkk...kkkkk.",
]
K_HURT = [
    "......kkkkk.....",
    ".....kmmmmmk....",
    "...kkmMMMMMmk...",
    "..kmmMrrrMmk....",
    "..kMrrrrrrMk....",
    "..kwkrrkrrwk....",
    "..krrrrrrrkk....",
    "...krkkkrkmk....",
    "s..kkkrrrrkkk...",
    "sk.klGGGGGGGlk.s",
    ".sklGGlGGGlGGlks",
    "..klGGGGGGGGGlk.",
    "..kMGGGGGGGGGMk.",
    "...kGGGGGGGGGk..",
    "...kyyyyyyyyyk..",
    "...kGGGGGGGGGk..",
    "..ksssk.ksssk...",
    ".ksssk...kssssk.",
    ".kssk.....kssk..",
    "kmmk.......kmmk.",
    "kmMmk.....kmMMk.",
    "kmmmk.....kmmmk.",
    ".kkk.......kkk..",
    "................",
]

# --- frog form (16x16)
F_IDLE = [
    "................",
    "................",
    "...gg......gg...",
    "..gllg....gllg..",
    "..glwlgggglwlg..",
    "..gllllllllllg..",
    "..glllllllllllg.",
    ".gllGllllllGllg.",
    ".gllllllllllllg.",
    ".gllGGllllGGllg.",
    ".gGllllllllllGg.",
    ".gglllllllllggg.",
    "gglgggllllgggglg",
    "glggg.gggg.ggglg",
    "gg.............g",
    "................",
]
F_JUMP = [
    "................",
    "...gg......gg...",
    "..gllg....gllg..",
    "..glwlgggglwlg..",
    "..gllllllllllg..",
    "..glllllllllllg.",
    ".gllGllllllGllg.",
    ".gllllllllllllg.",
    ".gllGGllllGGllg.",
    ".gGllllllllllGg.",
    "gglllllllllllggg",
    "glgg.gllllg.gglg",
    "gg....gggg....gg",
    "................",
    "................",
    "................",
]
# --- fish form (16x16)
FI_1 = [
    "................",
    "................",
    "......oooo......",
    "....ooyyyyoo..o.",
    "..ooyyyyyyyyooo.",
    ".oykyyyyyyyyyooo",
    ".oyyyyyyyyyyyoo.",
    ".oyyoooyyyyyoooo",
    ".ooyyyyyyyyyyooo",
    "..ooyyyyyyyyyoo.",
    "....ooyyyyoo..o.",
    "......oooo......",
    "................",
    "................",
    "................",
    "................",
]
FI_2 = [
    "................",
    "................",
    "......oooo....o.",
    "....ooyyyyoo.oo.",
    "..ooyyyyyyyyooo.",
    ".oykyyyyyyyyyoo.",
    ".oyyyyyyyyyyyooo",
    ".oyyoooyyyyyyoo.",
    ".ooyyyyyyyyyyoo.",
    "..ooyyyyyyyyoo..",
    "....ooyyyyoo.oo.",
    "......oooo....o.",
    "................",
    "................",
    "................",
    "................",
]
# --- bird form (16x16)
B_1 = [
    "................",
    "................",
    "....kk..........",
    "..kkyykk........",
    ".kyyyyyykk......",
    "kyyoooooyykk....",
    ".kkoorrrrrrok...",
    "...kkrrrkwrok...",
    ".....krrrrykk...",
    "......kkrryk....",
    "........kkk.....",
    "........yy......",
    "........kk......",
    "................",
    "................",
    "................",
]
B_2 = [
    "................",
    "................",
    "................",
    "................",
    "........kk......",
    "......kkyyk.....",
    "....kkyyoookk...",
    "..kkyyoorrrrok..",
    "kkyyoorrrkwrok..",
    ".kkoorrrrrykk...",
    "...kkrrrryk.....",
    ".....kkkkk......",
    "........yy......",
    "........kk......",
    "................",
    "................",
]

# ---------------------------------------------------------------- enemies
E_WALKER1 = [   # armoured beetle
    "................",
    "................",
    "...kkkkkkkkkk...",
    "..kpppppppppk...",
    ".kpprpppprppk...",
    ".kppppppppppk...",
    "kprppppppprpppk.",
    "kppppppppppppkk.",
    "kpppkppppkpppk..",
    ".kppppppppppk...",
    "..kkkkkkkkkk....",
    "..k.k.k..k.k.k..",
    ".kk.kk....kk.kk.",
    "................",
    "................",
    "................",
]
E_WALKER2 = [
    "................",
    "................",
    "...kkkkkkkkkk...",
    "..kpppppppppk...",
    ".kpprpppprppk...",
    ".kppppppppppk...",
    "kprppppppprpppk.",
    "kppppppppppppkk.",
    "kpppkppppkpppk..",
    ".kppppppppppk...",
    "..kkkkkkkkkk....",
    ".k.k..k.k..k.k..",
    "kk..kk...kk...kk",
    "................",
    "................",
    "................",
]
E_JUMPER1 = [   # spiny hopper
    "................",
    "................",
    "................",
    "......rr........",
    "...r.rrrr.r.....",
    "...rrrrrrrr.....",
    "..rrryrrryrr....",
    "..rrrrrrrrrr....",
    ".rrrrkkkkrrrr...",
    ".rrrrrrrrrrrr...",
    "..rrrrrrrrrr....",
    "...rrrrrrrr.....",
    "...kk....kk.....",
    "..kkk....kkk....",
    "................",
    "................",
]
E_JUMPER2 = [
    "................",
    "......rr........",
    "...r.rrrr.r.....",
    "...rrrrrrrr.....",
    "..rrryrrryrr....",
    "..rrrrrrrrrr....",
    ".rrrrkkkkrrrr...",
    ".rrrrrrrrrrrr...",
    "..rrrrrrrrrr....",
    "...rrrrrrrr.....",
    "..kk......kk....",
    ".kkk......kkk...",
    "................",
    "................",
    "................",
    "................",
]
E_SHOOTER1 = [  # spitting flower
    "................",
    "....pp..pp......",
    "...pwwppwwp.....",
    "..pwwwwwwwwp....",
    "..pwwyyyywwp....",
    "..pwwykkywwp....",
    "..pwwyyyywwp....",
    "..pwwwwwwwwp....",
    "...pwwppwwp.....",
    "....GpGGpG......",
    "....GGGGGG......",
    "...GlGGGGlG.....",
    "....GGGGGG......",
    "...GGGGGGGG.....",
    "..GGGGGGGGGG....",
    "..gggggggggg....",
]
E_SHOOTER2 = [
    "....pp..pp......",
    "...pwwppwwp.....",
    "..pwwwwwwwwp....",
    "..pwwyyyywwp....",
    "..pwyykkyywp....",
    "..pwwyyyywwp....",
    "..pwwwwwwwwp....",
    "...pwwppwwp.....",
    "....GpGGpG......",
    "....GGGGGG......",
    "...GlGGGGlG.....",
    "....GGGGGG......",
    "...GGGGGGGG.....",
    "..GGGGGGGGGG....",
    "..gggggggggg....",
    "................",
]
E_SWIMMER1 = [  # piranha
    "................",
    "................",
    "...kkk..........",
    "..kcccck....kk..",
    ".kccccccck.kckk.",
    "kcwkcccccckcccck",
    "kckkccccccccccck",
    "kcwwwccccccccck.",
    ".kcccccccccck...",
    "..kcccccccck....",
    "...kkccccck.....",
    ".....kkkkk......",
    "................",
    "................",
    "................",
    "................",
]
E_SWIMMER2 = [
    "................",
    "................",
    "...kkk......kk..",
    "..kcccck...kckk.",
    ".kcccccccckccck.",
    "kcwkccccccccccck",
    "kckkcccccccccck.",
    "kcwwwcccccccck..",
    ".kccccccccccck..",
    "..kccccccccck...",
    "...kkccccckk....",
    ".....kkkkk......",
    "................",
    "................",
    "................",
    "................",
]

# ---------------------------------------------------------------- items
I_BLADE1 = [
    "................",
    "................",
    "................",
    "....AAAAAA......",
    "...AwwwwwwA.....",
    "..AwwAAAAwwA....",
    "..AwAA..AAwA....",
    "..AwA....AwA....",
    "..AwA....AwA....",
    "..AwAA..AAwA....",
    "..AwwAAAAwwA....",
    "...AwwwwwwA.....",
    "....AAAAAA......",
    "................",
    "................",
    "................",
]
I_BLADE2 = [
    "................",
    "................",
    "......AA........",
    "....AAwwAA......",
    "...AwwwwwwA.....",
    "..AwwA..AwwA....",
    ".AwwA....AwwA...",
    ".AwA......AwA...",
    ".AwwA....AwwA...",
    "..AwwA..AwwA....",
    "...AwwwwwwA.....",
    "....AAwwAA......",
    "......AA........",
    "................",
    "................",
    "................",
]
I_GEM = [
    "................",
    "................",
    "................",
    ".....cccc.......",
    "....cwwwcc......",
    "...cwwccwcc.....",
    "..cwccccccbc....",
    "..ccccccccbc....",
    "...bccccccb.....",
    "....bccccb......",
    ".....bccb.......",
    "......bb........",
    "................",
    "................",
    "................",
    "................",
]
I_HEART = [
    "................",
    "................",
    "................",
    "..rrr...rrr.....",
    ".rwwwr.rrrrr....",
    "rwwrrrrrrrrrr...",
    "rwrrrrrrrrrrr...",
    "rrrrrrrrrrrrr...",
    ".rrrrrrrrrrr....",
    "..rrrrrrrrr.....",
    "...rrrrrrr......",
    "....rrrrr.......",
    ".....rrr........",
    "......r.........",
    "................",
    "................",
]
def key(col):
    return [
        "................",
        "................",
        "................",
        "....kkkk........",
        "...k%%%%k.......",
        "..k%%kk%%k......",
        "..k%%kk%%k......",
        "...k%%%%k.......",
        "....k%%k........",
        "....k%%k........",
        "....k%%kkk......",
        "....k%%%%k......",
        "....k%%kkk......",
        "....k%%%k.......",
        "....kkkk........",
        "................",
    ]
def recolor(rows, ch):
    return [r.replace('%', ch) for r in rows]

I_DOOR_CLOSED = [
    "kkkkkkkkkkkkkkkk",
    "kmMMMMMMMMMMMMmk",
    "kMmmmmmmmmmmmmMk",
    "kMmMMMMMMMMMMmMk",
    "kMmMmmmmmmmmMmMk",
    "kMmMmMMMMMMmMmMk",
    "kMmMmMmmmmMmMmMk",
    "kMmMmMmyymMmMmMk",
    "kMmMmMmyymMmMmMk",
    "kMmMmMmmmmMmMmMk",
    "kMmMmMMMMMMmMmMk",
    "kMmMmmmmmmmmMmMk",
    "kMmMMMMMMMMMMmMk",
    "kMmmmmmmmmmmmmMk",
    "kmMMMMMMMMMMMMmk",
    "kkkkkkkkkkkkkkkk",
]
I_DOOR_OPEN = [
    "kkkkkkkkkkkkkkkk",
    "kmMMMMMMMMMMMMmk",
    "kMmkkkkkkkkkkmMk",
    "kMmkddddddddkmMk",
    "kMmkddddddddkmMk",
    "kMmkddddddddkmMk",
    "kMmkddddddddkmMk",
    "kMmkddddddddkmMk",
    "kMmkddddddddkmMk",
    "kMmkddddddddkmMk",
    "kMmkddddddddkmMk",
    "kMmkddddddddkmMk",
    "kMmkddddddddkmMk",
    "kMmkddddddddkmMk",
    "kmMMMMMMMMMMMMmk",
    "kkkkkkkkkkkkkkkk",
]
I_EXIT = [   # totem gateway
    "....yyyyyyyy....",
    "...yooooooooy...",
    "..yoolllllooy...",
    "..yolGGGGGloy...",
    ".yolGGccGGGloy..",
    ".yolGcwwcGGloy..",
    ".yolGcwwcGGloy..",
    ".yolGGccGGGloy..",
    ".yolGGGGGGGloy..",
    ".yolGGGGGGGloy..",
    ".yolGGGGGGGloy..",
    "..yolGGGGGloy...",
    "..yoolllllooy...",
    "...yooooooooy...",
    "....yyyyyyyy....",
    "................",
]
def pad(c1, c2):
    return [
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "..kkkkkkkkkkkk..",
        ".k@@@@@@@@@@@@k.",
        "k@@%%@@@@%%@@@@k",
        "k@%%%%@@%%%%@@@k",
        "k@@%%@@@@%%@@@@k",
        "k@@@@@@@@@@@@@@k",
        "kkkkkkkkkkkkkkkk",
        "................",
    ]
def recolor2(rows, a, b):
    return [r.replace('@', a).replace('%', b) for r in rows]

I_SWITCH_OFF = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "......kk........",
    "....kkAAkk......",
    "...kAAAAAAk.....",
    "...kAaaaaAk.....",
    "..kAAAAAAAAk....",
    "..kaaaaaaaak....",
    "..kAAAAAAAAk....",
    "..kkkkkkkkkk....",
    "................",
    "................",
    "................",
]
I_SWITCH_ON = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "...kAAAAAAk.....",
    "...kyyyyyyk.....",
    "..kAAAAAAAAk....",
    "..kyyyyyyyyk....",
    "..kAAAAAAAAk....",
    "..kkkkkkkkkk....",
    "................",
    "................",
]
P_SHOT = [
    "........",
    "..pppp..",
    ".pwwwwp.",
    "pwwppwwp",
    "pwwppwwp",
    ".pwwwwp.",
    "..pppp..",
    "........",
]
P_SPARK = [
    "........",
    "...yy...",
    "..ywwy..",
    ".ywwwwy.",
    ".ywwwwy.",
    "..ywwy..",
    "...yy...",
    "........",
]

ARCH_LOCKED = [
    "..AAAAAAAAAAAA..",
    ".AaaaaaaaaaaaaA.",
    "AaaAAAAAAAAAaaA.",
    "AaAkkkkkkkkkkAaA",
    "AaAkddddddddkAaA",
    "AaAkdMMMMMMdkAaA",
    "AaAkdMmmmmMdkAaA",
    "AaAkdMmyymMdkAaA",
    "AaAkdMmyymMdkAaA",
    "AaAkdMmmmmMdkAaA",
    "AaAkdMMMMMMdkAaA",
    "AaAkddddddddkAaA",
    "AaAkkkkkkkkkkAaA",
    "AaaaaaaaaaaaaaaA",
    "AAAAAAAAAAAAAAAA",
    "kkkkkkkkkkkkkkkk",
]
ARCH_OPEN = [
    "..AAAAAAAAAAAA..",
    ".AaaaaaaaaaaaaA.",
    "AaaAAAAAAAAAaaA.",
    "AaAkkkkkkkkkkAaA",
    "AaAkddddddddkAaA",
    "AaAkdnnnnnndkAaA",
    "AaAkdnmmmmndkAaA",
    "AaAkdnmyyMndkAaA",
    "AaAkdnmyyMndkAaA",
    "AaAkdnmMMmndkAaA",
    "AaAkdnnnnnndkAaA",
    "AaAkddddddddkAaA",
    "AaAkkkkkkkkkkAaA",
    "AaaaaaaaaaaaaaaA",
    "AAAAAAAAAAAAAAAA",
    "kkkkkkkkkkkkkkkk",
]
ARCH_CLEARED = [
    "..AAAAAAAAAAAA..",
    ".AaaaaaaaaaaaaA.",
    "AaaAAAAAAAAAaaA.",
    "AaAkkkkkkkkkkAaA",
    "AaAkddddddddkAaA",
    "AaAkdGGGGGGdkAaA",
    "AaAkdGllllGdkAaA",
    "AaAkdGlwwlGdkAaA",
    "AaAkdGlwwlGdkAaA",
    "AaAkdGllllGdkAaA",
    "AaAkdGGGGGGdkAaA",
    "AaAkddddddddkAaA",
    "AaAkkkkkkkkkkAaA",
    "AaaaaaaaaaaaaaaA",
    "AAAAAAAAAAAAAAAA",
    "kkkkkkkkkkkkkkkk",
]


def build_sprites():
    sheet("kaya_human", [K_IDLE, K_RUN1, K_RUN2, K_RUN3, K_JUMP, K_CLIMB1, K_CLIMB2, K_HURT], 16, 24)
    sheet("kaya_frog", [F_IDLE, F_JUMP], 16, 16)
    sheet("kaya_fish", [FI_1, FI_2], 16, 16)
    sheet("kaya_bird", [B_1, B_2], 16, 16)
    sheet("enemy_walker", [E_WALKER1, E_WALKER2], 16, 16)
    sheet("enemy_jumper", [E_JUMPER1, E_JUMPER2], 16, 16)
    sheet("enemy_shooter", [E_SHOOTER1, E_SHOOTER2], 16, 16)
    sheet("enemy_swimmer", [E_SWIMMER1, E_SWIMMER2], 16, 16)
    sheet("blade", [I_BLADE1, I_BLADE2], 16, 16)
    sheet("pickups", [I_GEM, I_HEART,
                      recolor(key('y'), 'y'), recolor(key('r'), 'r'), recolor(key('c'), 'c')], 16, 16)
    sheet("props", [I_DOOR_CLOSED, I_DOOR_OPEN, I_EXIT, I_SWITCH_OFF, I_SWITCH_ON,
                    recolor2(pad(0, 0), 'G', 'l'),   # frog pad
                    recolor2(pad(0, 0), 'b', 'c'),   # fish pad
                    recolor2(pad(0, 0), 'A', 'w'),   # bird pad
                    ARCH_LOCKED, ARCH_OPEN, ARCH_CLEARED],
          16, 16)
    sheet("projectiles", [P_SHOT, P_SPARK], 8, 8)
    print("sprites written")

# ---------------------------------------------------------------- font
GLYPHS = {
 'A':["..##..",".#..#.","#....#","######","#....#","#....#","#....#",'......'],
 'B':["#####.","#....#","#....#","#####.","#....#","#....#","#####.",'......'],
 'C':[".####.","#....#","#.....","#.....","#.....","#....#",".####.",'......'],
 'D':["#####.","#....#","#....#","#....#","#....#","#....#","#####.",'......'],
 'E':["######","#.....","#.....","#####.","#.....","#.....","######",'......'],
 'F':["######","#.....","#.....","#####.","#.....","#.....","#.....",'......'],
 'G':[".####.","#....#","#.....","#..###","#....#","#....#",".####.",'......'],
 'H':["#....#","#....#","#....#","######","#....#","#....#","#....#",'......'],
 'I':[".####.","..##..","..##..","..##..","..##..","..##..",".####.",'......'],
 'J':["....##","....##","....##","....##","#...##","#...##",".####.",'......'],
 'K':["#....#","#...#.","#..#..","###...","#..#..","#...#.","#....#",'......'],
 'L':["#.....","#.....","#.....","#.....","#.....","#.....","######",'......'],
 'M':["#....#","##..##","######","#.##.#","#....#","#....#","#....#",'......'],
 'N':["#....#","##...#","#.#..#","#..#.#","#...##","#....#","#....#",'......'],
 'O':[".####.","#....#","#....#","#....#","#....#","#....#",".####.",'......'],
 'P':["#####.","#....#","#....#","#####.","#.....","#.....","#.....",'......'],
 'Q':[".####.","#....#","#....#","#....#","#..#.#","#...#.",".###.#",'......'],
 'R':["#####.","#....#","#....#","#####.","#..#..","#...#.","#....#",'......'],
 'S':[".#####","#.....","#.....",".####.",".....#",".....#","#####.",'......'],
 'T':["######","..##..","..##..","..##..","..##..","..##..","..##..",'......'],
 'U':["#....#","#....#","#....#","#....#","#....#","#....#",".####.",'......'],
 'V':["#....#","#....#","#....#","#....#","#....#",".#..#.","..##..",'......'],
 'W':["#....#","#....#","#....#","#.##.#","######","##..##","#....#",'......'],
 'X':["#....#",".#..#.","..##..","..##..","..##..",".#..#.","#....#",'......'],
 'Y':["#....#","#....#",".#..#.","..##..","..##..","..##..","..##..",'......'],
 'Z':["######","....#.","...#..","..#...",".#....","#.....","######",'......'],
 '0':[".####.","#...##","#..#.#","#.#..#","##...#","#....#",".####.",'......'],
 '1':["..##..",".###..","..##..","..##..","..##..","..##..",".####.",'......'],
 '2':[".####.","#....#",".....#","..###.",".#....","#.....","######",'......'],
 '3':["#####.",".....#",".....#","..###.",".....#",".....#","#####.",'......'],
 '4':["#...#.","#...#.","#...#.","######","....#.","....#.","....#.",'......'],
 '5':["######","#.....","#####.",".....#",".....#","#....#",".####.",'......'],
 '6':[".####.","#.....","#.....","#####.","#....#","#....#",".####.",'......'],
 '7':["######",".....#","....#.","...#..","..#...","..#...","..#...",'......'],
 '8':[".####.","#....#","#....#",".####.","#....#","#....#",".####.",'......'],
 '9':[".####.","#....#","#....#",".#####",".....#",".....#",".####.",'......'],
 '.':["......","......","......","......","......","..##..","..##..",'......'],
 ',':["......","......","......","......","..##..","..##..",".##...",'......'],
 ':':["......","..##..","..##..","......","..##..","..##..","......",'......'],
 '-':["......","......","......","######","......","......","......",'......'],
 '!':["..##..","..##..","..##..","..##..","..##..","......","..##..",'......'],
 '?':[".####.","#....#",".....#","...##.","..#...","......","..##..",'......'],
 "'":["..##..","..##..","......","......","......","......","......",'......'],
 '/':["....#.","...#..","...#..","..#...",".#....",".#....","#.....",'......'],
 '%':["#....#","#...#.","...#..","..#...",".#....","#...##","#...##",'......'],
 '+':["......","..##..","..##..","######","..##..","..##..","......",'......'],
 '(':["...##.","..#...",".#....",".#....",".#....","..#...","...##.",'......'],
 ')':[".##...","...#..","....#.","....#.","....#.","...#..",".##...",'......'],
 '*':["......","#..#..",".###..","######",".###..","#..#..","......",'......'],
 '=':["......","......","######","......","######","......","......",'......'],
 '>':["#.....","..#...","....#.",".....#","....#.","..#...","#.....",'......'],
 '<':[".....#","...#..",".#....","#.....",".#....","...#..",".....#",'......'],
 ' ':["......","......","......","......","......","......","......",'......'],
}
FONT_ORDER = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def build_font():
    """8x8 cell bitmap font laid out as a 16-column ASCII grid from space (32)."""
    cw, chh, cols = 8, 8, 16
    codes = list(range(32, 32 + 64))
    rows = (len(codes) + cols - 1) // cols
    img = Image.new("RGBA", (cols * cw, rows * chh), (0, 0, 0, 0))
    for i, code in enumerate(codes):
        ch = chr(code)
        g = GLYPHS.get(ch)
        if not g:
            continue
        ox, oy = (i % cols) * cw, (i // cols) * chh
        for y, row in enumerate(g):
            for x, c in enumerate(row):
                if c == '#':
                    img.putpixel((ox + x + 1, oy + y + 1), PAL['w'])
    img.save(os.path.join(FONTS, "font8.png"))
    print("font8.png (%d glyphs)" % len(GLYPHS))

# ---------------------------------------------------------------- title art
def build_logo():
    """Title logo: the 8x8 font blown up 5x with a hard dark outline and a
    two-tone vertical fill, so it reads as chunky VGA lettering."""
    text = "KAYA"
    scale = 5
    off = 2                      # shadow offset in final pixels
    w = len(text) * 8 * scale
    h = 8 * scale
    img = Image.new("RGBA", (w + off + 4, h + off + 4), (0, 0, 0, 0))

    def stamp(colour_fn, dx, dy):
        for i, ch in enumerate(text):
            g = GLYPHS.get(ch)
            if not g:
                continue
            for y, row in enumerate(g):
                for x, c in enumerate(row):
                    if c != '#':
                        continue
                    for sy in range(scale):
                        for sx in range(scale):
                            px = dx + (i * 8 + x) * scale + sx
                            py = dy + y * scale + sy
                            if 0 <= px < img.width and 0 <= py < img.height:
                                img.putpixel((px, py), colour_fn(y * scale + sy))

    # 1) dark green drop shadow, 2) black outline ring, 3) two-tone fill
    stamp(lambda _y: PAL['g'], 2 + off, 2 + off)
    for ox, oy in ((1, 2), (3, 2), (2, 1), (2, 3)):
        stamp(lambda _y: PAL['k'], ox, oy)
    stamp(lambda yy: PAL['y'] if yy < h * 0.55 else PAL['o'], 2, 2)
    img.save(os.path.join(SPRITES, "logo.png"))
    print("logo.png")


# ---------------------------------------------------------------- backdrops
def _lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(4))


def canopy_layer(img, base_y, colour, seed, amp=14, step=9, wrap=False):
    """Rounded blobby treeline silhouette across the full width.

    `wrap=True` makes the silhouette repeat seamlessly, which the scrolling
    parallax layers need."""
    rnd = random.Random(seed)
    W, H = img.size
    tops = []
    x = 0
    while x < W:
        r = rnd.randint(step - 2, step + 4)
        cy = base_y + rnd.randint(-amp, amp // 2)
        tops.append((x, cy, r))
        x += rnd.randint(step - 3, step + 3)
    for px in range(W):
        top = H
        for (cx, cy, r) in tops:
            dx = px - cx
            if wrap:
                dx = (dx + W // 2) % W - W // 2
            if abs(dx) <= r:
                yy = cy - int((r * r - dx * dx) ** 0.5)
                top = min(top, yy)
        for py in range(max(0, top), H):
            img.putpixel((px, py), colour)


def build_title_bg():
    W, H = 400, 240
    img = Image.new("RGBA", (W, H), PAL['d'])
    sky_top = (0x1b, 0x2a, 0x4a, 255)
    sky_bot = (0xe0, 0x8c, 0x3a, 255)
    for y in range(H):
        t = min(1.0, y / (H * 0.72))
        col = _lerp(sky_top, sky_bot, t ** 1.4)
        for x in range(W):
            img.putpixel((x, y), col)
    cx, cy, r = 300, 150, 34
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if 0 <= x < W and 0 <= y < H and (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                img.putpixel((x, y), (0xf2, 0xd5, 0x65, 255))
    rnd = random.Random(9)
    for _ in range(50):
        x, y = rnd.randrange(W), rnd.randrange(60)
        img.putpixel((x, y), PAL['w'])
    canopy_layer(img, 176, (0x1e, 0x53, 0x4a, 255), 101, amp=12, step=11)
    canopy_layer(img, 198, (0x14, 0x47, 0x2e, 255), 202, amp=14, step=13)
    canopy_layer(img, 222, (0x0d, 0x2c, 0x20, 255), 303, amp=10, step=15)
    rnd = random.Random(77)
    for _ in range(16):
        x = rnd.randrange(W)
        ln = rnd.randrange(20, 90)
        for y in range(ln):
            xx = x + int(2 * math.sin(y / 7.0))
            if 0 <= xx < W:
                img.putpixel((xx, y), (0x14, 0x47, 0x2e, 255))
                if y % 9 == 0 and 0 <= xx + 1 < W:
                    img.putpixel((xx + 1, y), (0x2a, 0x7a, 0x3f, 255))
    img.save(os.path.join(SPRITES, "title_bg.png"))
    print("title_bg.png")


def build_parallax():
    """Two scrolling backdrop strips (400x240 = exactly one screen each).

    Both tile seamlessly left/right; vertically they are screen-locked so a tall
    level shows the same depth on every screen instead of a seam. The far layer
    carries a full-height forest so no part of the screen is a flat fill."""
    W, H = 400, 240

    # ---------------- far: hazy deep forest, full height
    far = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for y in range(H):
        t = y / H
        col = _lerp((0x15, 0x2c, 0x3e, 255), (0x0e, 0x2a, 0x26, 255), t ** 0.7)
        for x in range(W):
            far.putpixel((x, y), col)
    rnd = random.Random(88)
    # distant trunks, thin and low-contrast, spread over the whole height
    for _ in range(26):
        x = rnd.randrange(W)
        w = rnd.randrange(2, 5)
        top = rnd.randrange(0, 70)
        shade = rnd.choice([(0x18, 0x38, 0x3a, 255), (0x1c, 0x40, 0x3c, 255),
                            (0x12, 0x30, 0x30, 255)])
        for yy in range(top, H):
            for k in range(w):
                far.putpixel(((x + k) % W, yy), shade)
    # canopy line high up, so it frames rather than fills
    canopy_layer_band(far, 34, 26, (0x11, 0x2c, 0x2c, 255), 501, amp=14, step=15)
    # horizontal mist bands break up the middle
    for band, alpha in ((96, 0.22), (150, 0.16), (198, 0.12)):
        for y in range(band, band + 14):
            f = 1.0 - abs((y - band) - 7) / 7.0
            for x in range(W):
                base = far.getpixel((x, y))
                far.putpixel((x, y), _lerp(base, (0x2e, 0x62, 0x58, 255), alpha * f))
    # light shafts slanting down
    for _ in range(6):
        sx = rnd.randrange(W)
        wdt = rnd.randrange(12, 30)
        for y in range(H):
            fade = 1.0 - y / float(H)
            for x in range(sx + y // 3, sx + y // 3 + wdt):
                base = far.getpixel((x % W, y))
                far.putpixel((x % W, y), _lerp(base, (0x46, 0x8c, 0x6e, 255), 0.14 * fade))
    far.save(os.path.join(SPRITES, "bg_far.png"))

    # ---------------- near: chunky readable trunks with leaf clusters
    near = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rnd = random.Random(606)
    for _ in range(6):
        x = rnd.randrange(W)
        w = rnd.randrange(11, 19)
        for yy in range(0, H):
            for k in range(w):
                px = (x + k) % W
                if k in (0, w - 1):
                    shade = (0x07, 0x18, 0x16, 255)
                elif k < 3:
                    shade = (0x0b, 0x22, 0x1e, 255)
                elif k > w - 4:
                    shade = (0x09, 0x1e, 0x1a, 255)
                else:
                    shade = (0x14, 0x36, 0x2c, 255)
                near.putpixel((px, yy), shade)
        # leaf clusters branching off
        for _ in range(5):
            ly = rnd.randrange(20, H - 20)
            side = rnd.choice((-1, 1))
            span = rnd.randrange(10, 26)
            for i in range(span):
                px = (x + w // 2 + side * i) % W
                thick = max(1, 4 - i // 6)
                for dy in range(-thick, thick + 1):
                    yy = ly + dy + i // 5
                    if 0 <= yy < H:
                        near.putpixel((px, yy), (0x11, 0x2e, 0x26, 255))
    canopy_layer_band(near, 0, 26, (0x09, 0x1e, 0x1a, 255), 707, amp=12, step=11)
    near.save(os.path.join(SPRITES, "bg_near.png"))
    print("bg_far.png bg_near.png")


def canopy_layer_band(img, base_y, thickness, colour, seed, amp=14, step=9):
    """Like canopy_layer but only paints a band of `thickness` px below the
    silhouette edge, so it frames the view instead of filling it."""
    rnd = random.Random(seed)
    W, H = img.size
    tops = []
    x = 0
    while x < W:
        r = rnd.randint(step - 2, step + 4)
        cy = base_y + rnd.randint(-amp, amp // 2)
        tops.append((x, cy, r))
        x += rnd.randint(step - 3, step + 3)
    for px in range(W):
        top = H
        for (cx, cy, r) in tops:
            dx = (px - cx + W // 2) % W - W // 2
            if abs(dx) <= r:
                top = min(top, cy - int((r * r - dx * dx) ** 0.5))
        if top >= H:
            continue
        for py in range(max(0, top), min(H, max(0, top) + thickness)):
            img.putpixel((px, py), colour)


def build_store_icons():
    """Store/app icons at every size the export presets ask for, plus a boot
    splash. All derived from the same 128px roundel so they stay consistent."""
    src = Image.open(os.path.join(SPRITES, "icon.png")).convert("RGBA")
    out = os.path.join(ROOT, "export", "icons")
    os.makedirs(out, exist_ok=True)
    for size in (1024, 512, 256, 192, 180, 167, 152, 144, 120, 114, 108, 87,
                 80, 76, 72, 60, 58, 40, 29, 20):
        # Nearest for exact multiples of 128 keeps the pixels crisp; otherwise
        # box-filter so small icons do not alias into mush.
        mode = Image.NEAREST if size % 128 == 0 else Image.LANCZOS
        img = src.resize((size, size), mode)
        if size >= 40:
            flat = Image.new("RGBA", (size, size), (0x0d, 0x2c, 0x20, 255))
            flat.alpha_composite(img)
            img = flat
        img.save(os.path.join(out, "icon_%d.png" % size))
    # Boot splash: the logo centred on the palette background.
    logo = Image.open(os.path.join(SPRITES, "logo.png")).convert("RGBA")
    sp = Image.new("RGBA", (640, 384), (0x0d, 0x0b, 0x0f, 255))
    big = logo.resize((logo.width * 2, logo.height * 2), Image.NEAREST)
    sp.alpha_composite(big, ((sp.width - big.width) // 2, (sp.height - big.height) // 2 - 20))
    sp.save(os.path.join(SPRITES, "splash.png"))
    print("store icons + splash")


def build_icon():
    """128x128 app icon: Kaya's head on a leaf roundel."""
    S = 128
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - S / 2 + 0.5, y - S / 2 + 0.5)
            if d < 60:
                img.putpixel((x, y), PAL['g'])
            if d < 55:
                img.putpixel((x, y), PAL['G'])
            if d < 48:
                img.putpixel((x, y), PAL['d'])
    head = [r[:16] for r in K_IDLE[0:12]]
    tmp = Image.new("RGBA", (16, 12), (0, 0, 0, 0))
    blit(tmp, 0, 0, grid(head))
    tmp = tmp.resize((16 * 6, 12 * 6), Image.NEAREST)
    img.alpha_composite(tmp, ((S - tmp.width) // 2, (S - tmp.height) // 2 - 4))
    img.save(os.path.join(SPRITES, "icon.png"))
    print("icon.png")


def build_boss():
    """THE GROVE WARDEN — a 32x32 carapaced guardian. Three frames:
    0 idle, 1 reared up (wind-up / firing), 2 staggered (damage flash pose)."""
    W = H = 32

    def ellipse(px, cx, cy, rx, ry, col):
        for y in range(H):
            for x in range(W):
                if 0 <= y < H and ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    px[y][x] = col

    def put(px, x, y, col):
        if 0 <= x < W and 0 <= y < H:
            px[y][x] = col

    def outline(px, col='k'):
        out = [row[:] for row in px]
        for y in range(H):
            for x in range(W):
                if px[y][x] != '.':
                    continue
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and px[yy][xx] not in ('.', 'k'):
                        out[y][x] = col
                        break
        return out

    def make(lift, mouth_open, hurt):
        px = [['.'] * W for _ in range(H)]
        body = 'r' if hurt else 'p'
        shell = 'o' if hurt else 'n'
        b = 3 - lift                       # everything rises when it rears up

        # six legs, behind the body
        for (sx, dir_) in ((9, -1), (23, 1)):
            for k, ly in enumerate((b + 14, b + 19, b + 24)):
                for i in range(6):
                    put(px, sx + dir_ * i, ly + i - k, 'd')
                    put(px, sx + dir_ * i, ly + i - k + 1, 'k')

        # abdomen
        ellipse(px, 16, b + 21, 12, 8, body)
        ellipse(px, 16, b + 21, 9, 6, shell)
        for i, rx in enumerate((7, 4)):
            ellipse(px, 16, b + 20 + i * 2, rx, 3 - i, body)

        # thorax
        ellipse(px, 16, b + 12, 9, 5, body)
        ellipse(px, 16, b + 12, 6, 3, shell)

        # head
        ellipse(px, 16, b + 7, 7, 5, shell)
        ellipse(px, 16, b + 8, 5, 3, body)

        # eyes
        for ex in (12, 20):
            ellipse(px, ex, b + 6, 2, 2, 'w' if hurt else 'y')
            put(px, ex, b + 6, 'k')
            put(px, ex, b + 7, 'k')

        # mandibles under the head
        for i in range(5):
            spread = i if mouth_open else i // 3
            put(px, 12 - spread, b + 11 + i, 'A')
            put(px, 20 + spread, b + 11 + i, 'A')
            if i < 3:
                put(px, 12 - spread, b + 11 + i + 1, 'a')
                put(px, 20 + spread, b + 11 + i + 1, 'a')

        # crown horn
        for i in range(5):
            put(px, 16, b + 1 + i, 'y')
            put(px, 15, b + 1 + i, 'o')
            if i > 2:
                put(px, 13 - (i - 3), b + 2 + i, 'o')
                put(px, 19 + (i - 3), b + 2 + i, 'o')

        return ["".join(r) for r in outline(px)]

    sheet("boss_grove", [make(0, False, False), make(2, True, False), make(0, True, True)],
          32, 32)
    print("boss_grove.png")


if __name__ == "__main__":
    build_tileset()
    build_sprites()
    build_font()
    build_logo()
    build_title_bg()
    build_parallax()
    build_icon()
    build_boss()
    build_store_icons()
    print("done")
