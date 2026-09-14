"""Sprites: Kaya and her forms, enemies, the boss, pickups, props, projectiles.

The silhouettes are still authored as ASCII grids — that is the readable part
and it is what the animation and hitbox work depends on. What changed in phase 1
is that no grid is rendered flat any more: every one goes through
`palette.auto_shade()`, which takes the character map below, measures how far
each pixel sits from the edge of the silhouette and re-lights it from the upper
left. The prototype's first finding was that this alone gives sprites real
volume for no authoring effort, and it holds.

`depth` is the one dial worth understanding: 3 for organic bodies that should
read as round, 1 for architecture (doors, arches, plates) where a rim light is
right and a pillow shade is not.
"""
import os
import random

from PIL import Image

from .palette import SPRITES, auto_shade, blit, grid, sheet

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


# ---------------------------------------------------------------- materials
# Character -> (ramp, base level). auto_shade() takes it from there.
KAYA = {'s': ("skin", 2.6), 'w': ("metal", 6.0),
        'm': ("dirt", 1.5), 'M': ("dirt", 3.0),
        'G': ("cloth", 2.3), 'l': ("cloth", 4.0),
        'y': ("gold", 4.0), 'r': ("ember", 3.2)}
FROG = {'g': ("foliage", 1.6), 'G': ("grass", 2.0),
        'l': ("grass", 3.5), 'w': ("metal", 6.0)}
FISH = {'o': ("gold", 1.8), 'y': ("gold", 3.4)}
BIRD = {'y': ("gold", 4.3), 'o': ("gold", 2.8),
        'r': ("ember", 3.2), 'w': ("metal", 6.0)}
WALKER = {'p': ("purple", 2.2), 'r': ("ember", 3.4)}
JUMPER = {'r': ("ember", 2.6), 'y': ("gold", 4.6)}
SHOOTER = {'p': ("purple", 2.6), 'w': ("metal", 5.2), 'y': ("gold", 4.4),
           'G': ("grass", 2.1), 'l': ("grass", 3.9), 'g': ("foliage", 1.5)}
SWIMMER = {'c': ("water", 4.6), 'w': ("metal", 6.0)}
BOSS = {'p': ("purple", 2.0), 'r': ("ember", 3.0), 'n': ("water", 2.0),
        'o': ("gold", 3.2), 'd': ("purple", 0.6), 'w': ("metal", 6.0),
        'y': ("gold", 4.8), 'A': ("metal", 4.2), 'a': ("metal", 2.2)}

BLADE = {'A': ("metal", 1.8), 'w': ("metal", 5.8)}
GEM = {'c': ("water", 5.2), 'b': ("water", 3.4), 'w': ("metal", 6.0)}
HEART = {'r': ("ember", 2.8), 'w': ("metal", 6.0)}
KEYS = {'y': ("gold", 4.6), 'r': ("ember", 3.6), 'c': ("water", 5.0)}
# Architecture: flat faces with a rim light, so depth=1 when these are used.
DOOR = {'m': ("wood", 1.8), 'M': ("wood", 3.8), 'y': ("gold", 4.6),
        'd': ("water", 0.4)}
TOTEM = {'y': ("gold", 4.8), 'o': ("gold", 3.0), 'l': ("grass", 4.2),
         'G': ("grass", 2.4), 'c': ("water", 5.0), 'w': ("metal", 6.0)}
SWITCH = {'A': ("metal", 4.4), 'a': ("metal", 2.2), 'y': ("gold", 5.0)}
PADS = {'G': ("grass", 2.4), 'l': ("grass", 4.2), 'b': ("water", 3.4),
        'c': ("water", 5.4), 'A': ("metal", 3.6), 'w': ("metal", 6.0)}
ARCH = dict(DOOR)
ARCH.update({'A': ("metal", 4.4), 'a': ("metal", 2.6), 'n': ("water", 2.4),
             'G': ("grass", 2.6), 'l': ("grass", 4.2), 'w': ("metal", 6.0)})

P_SHOT_MAP = {'p': ("purple", 3.0), 'w': ("metal", 6.0)}
P_SPARK_MAP = {'y': ("gold", 4.4), 'w': ("metal", 6.0)}


def lit(cells, mapping, **kw):
    return [auto_shade(c, mapping, **kw) for c in cells]


def build_sprites():
    # Kaya's limbs are three pixels wide; the default occlusion term would
    # push their shaded column down two whole ramp steps and read as mud.
    sheet("kaya_human", lit([K_IDLE, K_RUN1, K_RUN2, K_RUN3, K_JUMP,
                             K_CLIMB1, K_CLIMB2, K_HURT], KAYA, dark=0.75), 16, 24)
    sheet("kaya_frog", lit([F_IDLE, F_JUMP], FROG), 16, 16)
    sheet("kaya_fish", lit([FI_1, FI_2], FISH), 16, 16)
    sheet("kaya_bird", lit([B_1, B_2], BIRD), 16, 16)
    sheet("enemy_walker", lit([E_WALKER1, E_WALKER2], WALKER), 16, 16)
    sheet("enemy_jumper", lit([E_JUMPER1, E_JUMPER2], JUMPER), 16, 16)
    sheet("enemy_shooter", lit([E_SHOOTER1, E_SHOOTER2], SHOOTER), 16, 16)
    sheet("enemy_swimmer", lit([E_SWIMMER1, E_SWIMMER2], SWIMMER), 16, 16)
    sheet("blade", lit([I_BLADE1, I_BLADE2], BLADE, depth=1), 16, 16)
    sheet("pickups", lit([I_GEM], GEM, depth=2)
                     + lit([I_HEART], HEART, depth=2)
                     + lit([recolor(key('y'), 'y'), recolor(key('r'), 'r'),
                            recolor(key('c'), 'c')], KEYS, depth=2), 16, 16)
    sheet("props", lit([I_DOOR_CLOSED, I_DOOR_OPEN], DOOR, depth=1)
                   + lit([I_EXIT], TOTEM, depth=2)
                   + lit([I_SWITCH_OFF, I_SWITCH_ON], SWITCH, depth=1)
                   + lit([recolor2(pad(0, 0), 'G', 'l'),      # frog pad
                          recolor2(pad(0, 0), 'b', 'c'),      # fish pad
                          recolor2(pad(0, 0), 'A', 'w')],     # bird pad
                         PADS, depth=1)
                   + lit([ARCH_LOCKED, ARCH_OPEN, ARCH_CLEARED], ARCH, depth=1),
          16, 16)
    sheet("projectiles", lit([P_SHOT], P_SHOT_MAP, depth=2)
                         + lit([P_SPARK], P_SPARK_MAP, depth=2), 8, 8)
    print("sprites written")


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

    sheet("boss_grove",
          lit([make(0, False, False), make(2, True, False), make(0, True, True)],
              BOSS), 32, 32)
    print("boss_grove.png")

