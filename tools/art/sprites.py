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
#
# Phase 4 rebuilt the run as a real eight-frame cycle, so the frames below are
# *composed* rather than each drawn whole: one head, three arm swings, and a
# handful of leg blocks. `_kaya()` stacks head + torso + legs and checks the
# result is still 16x24, which is what catches a mistyped row.
#
# The vertical bob is the thing that buys weight. A run cycle at this size
# cannot move the body up — the head is already flush with the top of the frame
# — so the pose heights are expressed as how far the body sinks: 0 at push-off,
# 1 at the contact, 2 at the lowest point of the absorb. The feet still reach
# row 23 on every grounded frame, because that row is where the hitbox ends.
#
# Chars: s/m/M are the near limb (skin, boot shadow, boot light); S/n/N are the
# same three on the *far* limb, two ramp steps darker. Without that separation
# an eight-frame cycle reads as one leg flickering.
K_BLANK = "................"

K_HEAD = [
    "......kkkkk.....",
    ".....kmmmmmk....",
    "....kmMMMMMmk...",
    "....kmMsssMmk...",
    "....kMsssssMk...",
    "....kskwskwsk...",
    "....kssssssskk..",
    ".....kskkkskmk..",
    "....kkksssskkk..",
]
# Snapped back and away from the blow, eyes shut, mouth open, hair thrown
# forward — used by the hurt pose only.
K_HEAD_HURT = [
    "...kkkkk........",
    "..kmmmmmk.......",
    ".kmMMMMMmkk.....",
    ".kmMsssMmkmk....",
    ".kMsssssMkmmk...",
    ".kskksskskmk....",
    ".kssssssskkk....",
    "..kskkkskmk.....",
    "..kkkssskkk.....",
]

# ---- torsos. Rows 9-15: shoulders, satchel strap, satchel, belt, hips.
# The arm swing lives here: `BACK` reaches behind (near hand at the left edge,
# far hand forward), `FWD` reaches ahead, `UP` throws both hands past the head.
K_T_MID = [
    "...klGGGGGGGlk..",
    "..klGGlGGGlGGlk.",
    "..klGGGGGGGGGlk.",
    "..kMGGGGGGGGGMk.",
    "...kGGGGGGGGGk..",
    "...kyyyyyyyyyk..",
    "....kGGGGGGGk...",
]
K_T_BACK = [
    "...klGGGGGGGlk..",
    "..kllllGGGlGGlk.",
    ".ksssGGGGGGGGlk.",
    "ksskGGGGGGGGGMk.",
    ".kkkGGGGGGGGGk..",
    "...kyyyyyyyyyk..",
    "....kGGGGGGGk...",
]
K_T_FWD = [
    "...klGGGGGGGlk..",
    "..klGGlGGGllllk.",
    "..klGGGGGGGsssk.",
    "..kMGGGGGGGGGssk",
    "...kGGGGGGGGGkk.",
    "...kyyyyyyyyyk..",
    "....kGGGGGGGk...",
]
# Arms thrown up. The elbow sits level with the ear, so this pose has to
# rewrite the two head rows it reaches into; `_kaya()` takes it as a head
# override and pairs it with K_T_UP.
K_HEAD_UP = [
    "......kkkkk.....",
    ".....kmmmmmk....",
    "....kmMMMMMmk...",
    "....kmMsssMmk...",
    "....kMsssssMk...",
    "....kskwskwsk...",
    "....kssssssskk..",
    "ksk..kskkkskmksk",
    ".kskkkksssskkksk",
]
K_T_UP = [
    ".ksklGGGGGGGlksk",
    ".kklGGlGGGlGGlkk",
    "..klGGGGGGGGGlk.",
    "..kMGGGGGGGGGMk.",
    "...kGGGGGGGGGk..",
    "...kyyyyyyyyyk..",
    "....kGGGGGGGk...",
]
# Arms straight out for balance: the apex of a jump, the landing, and the hurt
# pose. Unlike K_T_UP it stays clear of the head, so it composes with any of
# them.
K_T_OUT = [
    "kssklGGGGGGGlksk",
    ".kklGGlGGGlGGlkk",
    "..klGGGGGGGGGlk.",
    "..kMGGGGGGGGGMk.",
    "...kGGGGGGGGGk..",
    "...kyyyyyyyyyk..",
    "....kGGGGGGGk...",
]

# ---- leg blocks, authored for the near leg forward. `_swap()` derives the
# opposite half of the cycle by exchanging the near and far materials, which is
# what keeps frames 2-5 and 6-9 the same length of stride.
L_CONTACT = [                       # full stride, both feet planted (sink 1)
    "...kSSSksssk....",
    "..kSSSk.ksssk...",
    ".kSSSk...ksssk..",
    "kSSSk.....ksssk.",
    "knnnk.....kmmmk.",
    "knNNk.....kmMMmk",
    "kkkkk.....kkkkkk",
]
L_DOWN = [                          # absorb: knees bent, feet in (sink 2)
    "...kSSkksssk....",
    "..kSSk..ksssk...",
    "..kSSk..ksssk...",
    "..knnk..kmmmk...",
    ".knNNk..kmMMmk..",
    ".kkkkk..kkkkkk..",
]
L_PASS = [                          # swing leg passes the support leg (sink 0)
    "....kssk.kSSk...",
    "....kssk.kSSk...",
    "....kssk..kSSk..",
    "....kssk..knnk..",
    "....kmmk..kNNk..",
    "...kmMMk..kkkk..",
    "...kmmmk........",
    "...kkkkk........",
]
L_UP = [                            # toe-off, far knee driven up (sink 0)
    ".....kssk.kSSk..",
    "....kssk..kSSk..",
    "...kssk...knnk..",
    "..kssk....kNNk..",
    "..kmmk....kkkk..",
    ".kmMMk..........",
    ".kmmmk..........",
    ".kkkkk..........",
]
L_CROUCH = [                        # jump anticipation, deepest (sink 3)
    "...kSSkksssk....",
    "..kSSk..ksssk...",
    "..knnk..kmmmk...",
    ".knNNk..kmMMmk..",
    ".kkkkk..kkkkkk..",
]
L_LAUNCH = [                        # legs together, driving straight down
    "....kSSkkssk....",
    "....kSSk.kssk...",
    "....kSSk.kssk...",
    "....kSSk.kssk...",
    "....knnk.kmmk...",
    "...knNNk.kmMMk..",
    "...knnnk.kmmmk..",
    "...kkkkk.kkkkk..",
]
L_RISE = [                          # far leg tucking up, near leg trailing
    "...kSSkkssk.....",
    "..kSSk..kssk....",
    "..kSSk..kssk....",
    "..knnk..kssk....",
    ".knNNk..kmmk....",
    ".kkkkk..kmMMk...",
    "........kmmmk...",
    "........kkkkk...",
]
L_APEX = [                          # both legs tucked
    "...kSSkkssk.....",
    "..kSSk..kssk....",
    "..knnk..kssk....",
    ".knNNk..kmmk....",
    ".kkkkk.kmMMk....",
    ".......kmmmk....",
    ".......kkkkk....",
    "................",
]
L_FALL = [                          # legs trailing, far knee up behind
    "....ksskSSk.....",
    "....ksskkSSk....",
    "....kssk.kSSk...",
    "....kssk.knnk...",
    "....kmmk.kNNk...",
    "...kmMMk.kkkk...",
    "...kmmmk........",
    "...kkkkk........",
]
L_LAND = [                          # impact squash: wide, low, knees out
    ".kSSSkkssssk....",
    "kSSk.....ksssk..",
    "knnk.....kmmmk..",
    "knNk.....kmMMk..",
    "kkkk.....kkkkk..",
]
L_STAND = [                         # idle / climb: feet together under the hips
    "....ksssksssk...",
    "....kssskssssk..",
    "....kssskssssk..",
    "....kssskssssk..",
    "...kmmmkkmmmmk..",
    "..kmMMmkkmMMMmk.",
    "..kmmmmkkmmmmmk.",
    "..kkkkk..kkkkkk.",
]
L_HURT = [                          # knocked off balance, front leg lifting
    "..ksssk.ksssk...",
    ".ksssk...kssk...",
    ".kssk.....kssk..",
    "kmmk......kmmk..",
    "kmMmk....kmMMk..",
    "kmmmk....kmmmk..",
    ".kkk......kkkk..",
    "................",
]

_NEAR_FAR = str.maketrans("smMSnN", "SnNsmM")


def _swap(rows):
    """The same pose with the near and far limbs exchanged."""
    return [r.translate(_NEAR_FAR) for r in rows]


def _kaya(torso, legs, sink=0, head=None):
    """Stack head + torso + legs into one 16x24 cell.

    `sink` is how far the whole body drops into the frame; the leg block is
    correspondingly shorter, so the feet stay on row 23 where the hitbox ends.
    """
    rows = [K_BLANK] * sink + (head or K_HEAD) + torso + legs
    assert len(rows) == 24, "Kaya cell is %d rows, not 24" % len(rows)
    for i, r in enumerate(rows):
        assert len(r) == 16, "Kaya row %d is %d wide" % (i, len(r))
    return rows


# Frame order is load-bearing: 0 is the idle every still shot and the hub use,
# and 2..9 is the run cycle, referenced as a contiguous range by both
# data/forms/human.json and src/hub/hub_player.gd.
K_IDLE = _kaya(K_T_MID, L_STAND)
K_IDLE_B = ([K_BLANK] + K_HEAD + K_T_MID[1:] + L_STAND)   # one-pixel breath
# Arms swing against the legs: back, back, through, forward for the half of the
# cycle with the near leg leading, then the mirror of it.
K_RUN_POSES = [
    (K_T_BACK, L_CONTACT, 1, False), (K_T_BACK, L_DOWN, 2, False),
    (K_T_MID, L_PASS, 0, False), (K_T_FWD, L_UP, 0, False),
    (K_T_FWD, L_CONTACT, 1, True), (K_T_FWD, L_DOWN, 2, True),
    (K_T_MID, L_PASS, 0, True), (K_T_BACK, L_UP, 0, True),
]
K_RUN = [_kaya(_t, _swap(_l) if _sw else _l, _s)
         for _t, _l, _s, _sw in K_RUN_POSES]

K_CROUCH = _kaya(K_T_BACK, L_CROUCH, 3)
K_LAUNCH = _kaya(K_T_UP, L_LAUNCH, 0, head=K_HEAD_UP)
K_RISE = _kaya(K_T_UP, L_RISE, 0, head=K_HEAD_UP)
K_APEX = _kaya(K_T_OUT, L_APEX, 0)
K_FALL = _kaya(K_T_UP, L_FALL, 0, head=K_HEAD_UP)
K_LAND = _kaya(K_T_OUT, L_LAND, 3)
K_HURT = _kaya(K_T_OUT, L_HURT, 0, head=K_HEAD_HURT)

# Climbing: both hands overhead on the vine, eyes on it rather than on the
# camera, and the legs alternating. It reuses the arms-up torso, so the grip is
# attached to the shoulders instead of floating beside them.
K_HEAD_CLIMB = K_HEAD_UP[:5] + ["....kskkskksk..."] + K_HEAD_UP[6:]
L_CLIMB_A = [                       # near knee drawn up, far leg straight
    "....kssskSSSk...",
    "....ksssk.kSSk..",
    "....ksssk.kSSk..",
    "....ksssk.knnk..",
    "...kmmmk..kNNk..",
    "...kmMMk..kkkk..",
    "...kmmmk........",
    "...kkkkk........",
]
K_CLIMB1 = _kaya(K_T_UP, L_CLIMB_A, 0, head=K_HEAD_CLIMB)
K_CLIMB2 = _kaya(K_T_UP, L_STAND, 0, head=K_HEAD_CLIMB)
K_CLIMB3 = _kaya(K_T_UP, _swap(L_CLIMB_A), 0, head=K_HEAD_CLIMB)


# Everything from here down is 16x16, and authored through `cell()` so a row
# only has to carry the pixels that are actually lit — trailing transparency is
# filled in, and a row that runs long fails the build instead of silently
# shifting a silhouette by a pixel.


def cell(rows, w=16, h=16):
    for i, r in enumerate(rows):
        assert len(r) <= w, "row %d is %d wide, max %d" % (i, len(r), w)
    assert len(rows) <= h, "%d rows, max %d" % (len(rows), h)
    out = [r + "." * (w - len(r)) for r in rows]
    return out + ["." * w] * (h - len(out))


def mirror(rows):
    """Flip a cell left-to-right.

    The fish and the piranha were both drawn head-left, but `flip_h` is keyed
    off `facing`, so facing right drew them swimming backwards. They are
    authored head-left here — it is the easier read — and mirrored on the way
    out so the unflipped frame faces right like every other sprite.
    """
    return [r[::-1] for r in rows]


# --- frog form (16x16). Idle, breath, the leap crouch, the leap, the reach on
# the way down, and the wall cling.
F_IDLE = cell([
    "",
    "",
    "...gg......gg",
    "..gllg....gllg",
    "..glwlgggglwlg",
    "..gllllllllllg",
    "..glllllllllllg",
    ".gllGllllllGllg",
    ".gllllllllllllg",
    ".gllGGllllGGllg",
    ".gGllllllllllGg",
    ".gglllllllllggg",
    "gglgggllllgggglg",
    "glggg.gggg.ggglg",
    "gg.............g",
])
F_BREATHE = cell([
    "",
    "",
    "...gg......gg",
    "..gllg....gllg",
    "..glglgggglglg",
    "..gllllllllllg",
    ".glllllllllllllg",
    ".gllGllllllGllg",
    "gllllllllllllllg",
    ".gllGGllllGGllg",
    ".gGllllllllllGg",
    ".gglllllllllggg",
    "gglgggllllgggglg",
    "glggg.gggg.ggglg",
    "gg.............g",
])
F_CROUCH = cell([
    "",
    "",
    "",
    "...gg......gg",
    "..gllg....gllg",
    "..glwlgggglwlg",
    ".glllllllllllllg",
    ".gllGllllllGllg",
    "gllllllllllllllg",
    "gllGGllllllGGllg",
    "gGllllllllllllGg",
    "ggllllllllllllgg",
    "gglgggllllggglgg",
    "gg.gggllllggg.gg",
    "g...gg....gg...g",
])
F_LEAP = cell([
    "...gg......gg",
    "..gllg....gllg",
    "..glwlgggglwlg",
    "..gllllllllllg",
    "..glllllllllllg",
    ".gllGllllllGllg",
    ".gllllllllllllg",
    ".gllGGllllGGllg",
    ".gGllllllllllGg",
    ".gglllllllllggg",
    "gglgggllllgggglg",
    "glgg.gllllg.gglg",
    "gg....gggg....gg",
])
F_REACH = cell([
    "",
    "...gg......gg",
    "..gllg....gllg",
    "..glwlgggglwlg",
    "..gllllllllllg",
    "..glllllllllllg",
    ".gllGllllllGllg",
    ".gllllllllllllg",
    ".gllGGllllGGllg",
    ".gGllllllllllGg",
    "gggllllllllllgg",
    "glg.gglllllgg.g",
    "gg...gg.gg..gg",
    "g...gg....gg..g",
    "...gg......gg",
])
F_CLING = cell([
    "",
    "..gg........gg",
    ".gllg......gllg",
    ".glwlgggggglwlg",
    ".gllllllllllllg",
    "gllllllllllllllg",
    "gllGllllllllGllg",
    "gllllllllllllllg",
    "gllGGllllllGGllg",
    "gGllllllllllllGg",
    "ggllllllllllllgg",
    "glgggllllllggglg",
    "gg.gg.gggg.gg.gg",
    "g..gg......gg..g",
])

# --- fish form (16x16). Four beats of tail, plus a bite and a beached flop.
FI_TAIL_MID = cell([
    "",
    "",
    "......oooo....o",
    "....ooyyyyoo..oo",
    "..ooyyyyyyyyooyo",
    ".oykyyyyyyyyyoyo",
    ".oyyyyyyyyyyyoyo",
    ".oyyoooyyyyyyoyo",
    ".ooyyyyyyyyyyoyo",
    "..ooyyyyyyyyooyo",
    "....ooyyyyoo..oo",
    "......oooo....o",
])
FI_TAIL_UP = cell([
    "..............oo",
    ".............ooo",
    "......oooo...oyo",
    "....ooyyyyoo.oyo",
    "..ooyyyyyyyyooo",
    ".oykyyyyyyyyyoo",
    ".oyyyyyyyyyyyoo",
    ".oyyoooyyyyyyo",
    ".ooyyyyyyyyyyo",
    "..ooyyyyyyyyoo",
    "....ooyyyyoo",
    "......oooo",
])
FI_TAIL_MID2 = cell([
    "",
    "",
    "......oooo...oo",
    "....ooyyyyoo.ooo",
    "..ooyyyyyyyyooyo",
    ".oykyyyyyyyyyoyo",
    ".okyyyyyyyyyyoyo",
    ".oyyoooyyyyyyoyo",
    ".ooyyyyyyyyyyoyo",
    "..ooyyyyyyyyooo",
    "....ooyyyyoo.oo",
    "......oooo",
])
FI_TAIL_DOWN = cell([
    "",
    "",
    "......oooo",
    "....ooyyyyoo",
    "..ooyyyyyyyyoo",
    ".oykyyyyyyyyyoo",
    ".oyyyyyyyyyyyoo",
    ".oyyoooyyyyyyo",
    ".ooyyyyyyyyyyo",
    "..ooyyyyyyyyooo",
    "....ooyyyyoo.oyo",
    "......oooo...oyo",
    ".............ooo",
    "..............oo",
])
FI_BITE = cell([
    "",
    "",
    "......oooo",
    "....ooyyyyoo..o",
    "..ooyyyyyyyyooo",
    "ooykyyyyyyyyyooo",
    "kkyyyyyyyyyyyoo",
    "kkyyoooyyyyyoooo",
    "ooyyyyyyyyyyyooo",
    "..ooyyyyyyyyyoo",
    "....ooyyyyoo..o",
    "......oooo",
])
FI_FLOP = cell([
    "",
    "....oooo",
    "..ooyyyyoo",
    ".oyyyyyyyyoo",
    "okyyyyyyyyyyoo",
    "kkyyoooyyyyyyoo",
    "ooyyyyyyyyyyyooo",
    ".ooyyyyyyyyyyoo",
    "..ooyyyyyyyyoo",
    "....ooyyyyoo",
    "......oooo",
])

# --- bird form (16x16). A four-beat flap, a glide and a folded perch.
B_UP = cell([
    "",
    "",
    "....kk",
    "..kkyykk",
    ".kyyyyyykk",
    "kyyoooooyykk",
    ".kkoorrrrrrok",
    "...kkrrrkwrok",
    ".....krrrrykk",
    "......kkrryk",
    "........kkk",
    "........yy",
    "........kk",
])
B_MIDA = cell([
    "",
    "",
    "",
    "..kk",
    ".kyykkkk",
    "kyyoooooyykk",
    ".kkoorrrrrrok",
    "...kkrrrkwrok",
    ".....krrrrykk",
    "......kkrryk",
    "........kkk",
    "........yy",
    "........kk",
])
B_DOWN = cell([
    "",
    "",
    "",
    "",
    "........kk",
    "......kkyyk",
    "....kkyyoookk",
    "..kkyyoorrrrok",
    "kkyyoorrrkwrok",
    ".kkoorrrrrykk",
    "...kkrrrryk",
    ".....kkkkk",
    "........yy",
    "........kk",
])
B_MIDB = cell([
    "",
    "",
    "",
    "",
    "",
    "..kkkkyyookk",
    "kkyyyyoorrrrok",
    ".kkyyorrrkwrok",
    "..kkoorrrrrykk",
    "....kkrrrryk",
    "......kkkkk",
    "........yy",
    "........kk",
])
B_GLIDE = cell([
    "",
    "",
    "",
    "",
    "kkkk",
    "kyyyykkkkk",
    ".kyyoooooyykk",
    "..kkoorrrkwrok",
    "....kkrrrrrykk",
    "......kkrryk",
    "........kkk",
    "........yy",
    "........kk",
])
B_PERCH = cell([
    "",
    "",
    "",
    "....kkkk",
    "...kyyyyk",
    "...kyyoookkk",
    "...kyorrrrrok",
    "...kkorrkwrok",
    "....kkrrrrykk",
    ".....kkrrryk",
    "......kkkkk",
    "........yy",
    "........kk",
])

# ---------------------------------------------------------------- enemies
# --- the bark beetle. Four legs positions, and the shell drops a pixel on the
# two frames where the weight is on the near legs, which is the whole trick.
E_W_BODY = [
    "...kkkkkkkkkk",
    "..kpppppppppk",
    ".kpprpppprppk",
    ".kppppppppppk",
    "kprppppppprpppk",
    "kppppppppppppkk",
    "kpppkppppkpppk",
    ".kppppppppppk",
    "..kkkkkkkkkk",
]
E_W_FEELERS = [
    ["..k.........k", "...k.......k"],
    [".k...........k", "..k.........k"],
]
E_W_LEGS = [
    ["..q.q.q..q.q.q", ".kk.kk....kk.kk"],
    [".q.q..q.q..q.q", "kk..kk...kk...kk"],
    ["...q.q..q.q.q", "..kk..kk...kk.k"],
    [".q..q.q...q.q.q", "kk.kk...kk...kk"],
]


def walker(i):
    """Beetle frame `i`. On alternate frames the shell sinks a pixel and the
    legs lose their top row, so the weight shifts without the feet leaving the
    floor — which is the difference between a bob and a slide."""
    drop = i % 2
    return cell(["."] * drop + E_W_FEELERS[drop] + E_W_BODY + E_W_LEGS[i][drop:])


# --- the spine hopper. idle -> crouch -> coil is a visible three-step
# telegraph; `wind_up` in data/enemies/jumper.json is 0.42s, which is exactly
# three frames at 7fps.
E_J_IDLE = cell([
    "",
    "",
    "",
    "......rr",
    "...r.rrrr.r",
    "...rrrrrrrr",
    "..rrryrrryrr",
    "..rrrrrrrrrr",
    ".rrrrkkkkrrrr",
    ".rrrrrrrrrrrr",
    "..rrrrrrrrrr",
    "...rrrrrrrr",
    "...kk....kk",
    "..kkk....kkk",
])
E_J_CROUCH = cell([
    "",
    "",
    "",
    "",
    "...r..rr..r",
    "..rrrrrrrrrr",
    "..rrryrrryrr",
    ".rrrrrrrrrrrr",
    ".rrrrkkkkrrrr",
    "rrrrrrrrrrrrrr",
    ".rrrrrrrrrrrr",
    "..rrrrrrrrrr",
    "..kk......kk",
    ".kkk......kkk",
])
E_J_COIL = cell([
    "",
    "",
    "",
    "",
    "",
    "r.r..rr..r.r",
    ".rrrrrrrrrrr",
    ".rryyrrrryyr",
    "rrrrrrrrrrrrr",
    "rrrrkkkkkrrrrr",
    "rrrrrrrrrrrrrr",
    ".rrrrrrrrrrrr",
    ".kk........kk",
    "kkk........kkk",
])
E_J_AIR = cell([
    "",
    "......rr",
    "...r.rrrr.r",
    "...rrrrrrrr",
    "..rrryrrryrr",
    "..rrrrrrrrrr",
    ".rrrrkkkkrrrr",
    ".rrrrrrrrrrrr",
    "..rrrrrrrrrr",
    "...rrrrrrrr",
    "..kk......kk",
    ".kkk......kkk",
])
E_J_LAND = cell([
    "",
    "",
    "",
    "",
    "",
    "..r..rr..r",
    "..rrrrrrrrrr",
    ".rrryrrryrrr",
    "rrrrrrrrrrrrrr",
    "rrrrkkkkkrrrrr",
    ".rrrrrrrrrrrr",
    "..kk......kk",
    ".kkk......kkk",
])

# --- the spitter bloom. The telegraph escalates rather than throbs: the petals
# peel back, the throat darkens as it draws breath, then swells gold a beat
# before the spit. `fire` is the payoff pose and is held for a moment by
# src/enemies/shooter.gd.
E_S_STEM = [
    "...GpGGpG",
    "....GGGGG",
    "...GlGGGlG",
    "....GGGGGG",
    "...GGGGGGGG",
    "..GGGGGGGGGG",
    "..gggggggggg",
]
E_S_IDLE = cell([
    "",
    "....pp..pp",
    "...pwwppwwp",
    "..pwwwwwwwwp",
    "..pwwyyyywwp",
    "..pwwykkywwp",
    "..pwwyyyywwp",
    "..pwwwwwwwwp",
    "...pwwppwwp",
] + E_S_STEM[:1] + ["....GGGGGG"] + E_S_STEM[2:])
E_S_STIR = cell([
    "...pp..pp",
    "..pwwppwwp",
    ".pwwwwwwwwp",
    ".pwwyyyywwp",
    ".pwwykkywwp",
    ".pwwyyyywwp",
    ".pwwwwwwwwpp",
    "..pwwppwwpp",
] + E_S_STEM)
E_S_INHALE = cell([
    "..p...pp...p",
    "..pp.pwwp.pp",
    ".pwwwwwwwwwp",
    ".pwwykkkywwp",
    ".pwykkkkkywp",
    ".pwykkkkkywp",
    ".pwwykkkywwp",
    ".pwwwwwwwwwp",
    "..pwwppwwp",
] + E_S_STEM[:1] + E_S_STEM[2:])
E_S_SWELL = cell([
    "p..p..pp..p..p",
    ".pp.pwwwwp.pp",
    ".pwwwwwwwwwp",
    ".pwyyyyyyywp",
    "pwyyykkkyyywp",
    "pwyykkkkkyywp",
    "pwyyykkkyyywp",
    ".pwyyyyyyywp",
    ".pwwwwwwwwwp",
    "..pwwppwwp",
] + E_S_STEM[:1] + E_S_STEM[2:])
E_S_FIRE = cell([
    "...pp....pp",
    "..pwwp..pwwp",
    ".pwwwwwwwwwp",
    ".pwykkkkkywp",
    "pwykkkkkkkywp",
    "pwykkkkkkkywp",
    "pwykkkkkkkywp",
    ".pwykkkkkywp",
    ".pwwwwwwwwwp",
    "..pwwppwwp",
] + E_S_STEM[:1] + E_S_STEM[2:])

# --- the river piranha. Authored head-left and mirrored by `build_sprites()`,
# same as the fish form.
E_SW_MID = [
    "",
    "",
    "...kkk",
    "..kcccck....kk",
    ".kccccccck.kckk",
    "kcwkcccccckcccck",
    "kckkccccccccccck",
    "kcwwwccccccccck",
    ".kcccccccccck",
    "..kcccccccck",
    "...kkccccck",
    ".....kkkkk",
]
E_SW_UP = [
    "",
    "",
    "...kkk......kk",
    "..kcccck...kckk",
    ".kcccccccckccck",
    "kcwkccccccccccck",
    "kckkcccccccccck",
    "kcwwwcccccccck",
    ".kccccccccccck",
    "..kccccccccck",
    "...kkccccckk",
    ".....kkkkk",
]
E_SW_BITE = [
    "",
    "",
    "...kkk",
    "..kcccck....kk",
    ".kccccccck.kckk",
    "kkwkcccccckcccck",
    "kwkkccccccccccck",
    "kkwwwccccccccck",
    "kkcccccccccck",
    "..kcccccccck",
    "...kkccccck",
    ".....kkkkk",
]
E_SW_DOWN = [
    "",
    "",
    "...kkk",
    "..kcccck...kckk",
    ".kccccccckcccck",
    "kcwkcccccckccck",
    "kckkcccccccccck",
    "kcwwwcccccccckk",
    ".kccccccccccck",
    "..kccccccccck",
    "...kkccccckk",
    ".....kkkkk...kk",
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
        'y': ("gold", 4.0), 'r': ("ember", 3.2),
        # The far limb, one to two ramp steps down. Eight frames of run only
        # read as a cycle if the leg behind the body is visibly behind it.
        'S': ("skin", 1.5), 'n': ("dirt", 0.5), 'N': ("dirt", 1.9)}
FROG = {'g': ("foliage", 1.6), 'G': ("grass", 2.0),
        'l': ("grass", 3.5), 'w': ("metal", 6.0)}
FISH = {'o': ("gold", 1.8), 'y': ("gold", 3.4)}
BIRD = {'y': ("gold", 4.3), 'o': ("gold", 2.8),
        'r': ("ember", 3.2), 'w': ("metal", 6.0)}
WALKER = {'p': ("purple", 2.2), 'r': ("ember", 3.4),
          # Legs were ink, and ink legs disappear against dark terrain.
          'q': ("purple", 3.2)}
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
    # Frame order matches data/forms/human.json. 0-1 idle, 2-9 run, 10-15 the
    # jump arc (anticipate, launch, rise, apex, fall, land), 16-18 climb,
    # 19 hurt.
    sheet("kaya_human",
          lit([K_IDLE, K_IDLE_B] + K_RUN
              + [K_CROUCH, K_LAUNCH, K_RISE, K_APEX, K_FALL, K_LAND,
                 K_CLIMB1, K_CLIMB2, K_CLIMB3, K_HURT], KAYA, dark=0.75),
          16, 24)
    # 0 idle, 1 breath, 2 crouch, 3 leap, 4 reach, 5 cling
    sheet("kaya_frog", lit([F_IDLE, F_BREATHE, F_CROUCH, F_LEAP,
                            F_REACH, F_CLING], FROG), 16, 16)
    # 0-3 the swim beat, 4 bite, 5 flop. Mirrored so the unflipped cell faces
    # right, which is the direction `facing == 1` draws.
    sheet("kaya_fish", lit([mirror(c) for c in
                            (FI_TAIL_MID, FI_TAIL_UP, FI_TAIL_MID2,
                             FI_TAIL_DOWN, FI_BITE, FI_FLOP)], FISH), 16, 16)
    # 0-3 the flap beat, 4 glide, 5 perch
    sheet("kaya_bird", lit([B_UP, B_MIDA, B_DOWN, B_MIDB,
                            B_GLIDE, B_PERCH], BIRD), 16, 16)
    sheet("enemy_walker", lit([walker(i) for i in range(4)], WALKER), 16, 16)
    # 0 idle, 1-2 the telegraph, 3 airborne, 4 the landing squash
    sheet("enemy_jumper", lit([E_J_IDLE, E_J_CROUCH, E_J_COIL,
                               E_J_AIR, E_J_LAND], JUMPER), 16, 16)
    # 0 closed, 1-3 the telegraph, 4 the spit
    sheet("enemy_shooter", lit([E_S_IDLE, E_S_STIR, E_S_INHALE,
                                E_S_SWELL, E_S_FIRE], SHOOTER), 16, 16)
    sheet("enemy_swimmer", lit([mirror(cell(c)) for c in
                                (E_SW_MID, E_SW_UP, E_SW_BITE, E_SW_DOWN)],
                               SWIMMER), 16, 16)
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
    """THE GROVE WARDEN — 48x48, six frames per fight phase.

    Phase 3 of the plan asked for "visually distinct phases rather than a colour
    swap", so the three bodies differ in *silhouette*, and the parameters below
    are what differ:

      STOMP  squat and heavy. Wide plated abdomen sitting low over six short
             legs, horns held forward like a battering ram.
      LEAP   reared up on long coiled legs, a third taller, the carapace split
             open along the thorax to show the flight shell underneath.
      FURY   the carapace has failed: a ridge of spines has erupted through the
             back, ember light shows through the cracks, the jaw hangs open and
             the eyes have gone white.

    Within a phase the six frames are idle, two walk beats, the slam crouch,
    the airborne extension and the landing splay. data/enemies/boss_grove.json
    names them <anim>_p1/_p2/_p3 and src/enemies/boss_grove.gd picks the suffix
    for the phase it is in.

    The hitbox is 26x42 at (11, 4) in the frame: the feet still land on row 46,
    the crown still overhangs the top of the box, but the box is now as tall as
    the animal that is drawn (rows 2..47 of every frame, measured) rather than
    the 26 px body core it used to be. That is a fight decision and it is
    recorded here because it is a fact about this art: jungle_5's refuge slabs
    sit two tiles over the arena floor, the blade leaves Kaya's chest at
    y=383..395 from up there, and a 26 px box topping out at y=406 could be
    dodged from but never hit from. See tools/build_levels.py's jungle_5().
    """
    W = H = 48
    FLOOR = 46
    CX = 24

    def put(px, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            px[y][x] = c

    def ellipse(px, cx, cy, rx, ry, c):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    put(px, x, y, c)

    def line(px, x0, y0, x1, y1, c, thick=1):
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            y = y0 + (y1 - y0) * i / n
            for t in range(thick):
                put(px, int(round(x)) + t, int(round(y)), c)

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

    # ---- per phase: how the animal is built, not what colour it is.
    PHASES = [
        # lift  abdomen   thorax   head   leg (out, up, thick)  horn  extras
        dict(lift=0, ab=(15, 10), th=(11, 7), hd=(8, 6),
             leg=(15, 5, 3), spread=1.15, horn=(5, 5), jaw=0,
             spines=0, cracks=0, wings=0),
        dict(lift=7, ab=(12, 9), th=(10, 7), hd=(8, 6),
             leg=(16, 11, 2), spread=1.0, horn=(9, 9), jaw=3,
             spines=0, cracks=0, wings=1),
        dict(lift=4, ab=(14, 10), th=(11, 7), hd=(9, 6),
             leg=(17, 9, 2), spread=1.25, horn=(11, 7), jaw=6,
             spines=1, cracks=1, wings=0),
    ]
    # idle, walk A, walk B, slam crouch, airborne, landing splay
    POSES = [
        dict(dy=0, step=0, jaw=0, coil=1.0),
        dict(dy=0, step=3, jaw=0, coil=1.0),
        dict(dy=1, step=-3, jaw=0, coil=0.9),
        dict(dy=4, step=0, jaw=2, coil=0.6),
        dict(dy=-6, step=0, jaw=3, coil=1.5),
        dict(dy=3, step=6, jaw=3, coil=0.55),
    ]

    def make(ph, pose):
        px = [['.'] * W for _ in range(H)]
        body = 'p'
        shell = 'n'
        base = FLOOR - ph["lift"] + pose["dy"]      # bottom of the abdomen

        ab_rx, ab_ry = ph["ab"]
        th_rx, th_ry = ph["th"]
        hd_rx, hd_ry = ph["hd"]
        ab_cy = base - ab_ry
        th_cy = ab_cy - ab_ry - th_ry + 4
        hd_cy = th_cy - th_ry - hd_ry + 3

        # ---- legs, behind everything. Three pairs, each reaching further back
        # than the last; `step` slides alternate feet for the walk beat.
        out, up, thick = ph["leg"]
        for i, (hy, reach) in enumerate(((-2, 0.72), (2, 0.88), (6, 1.0))):
            for side in (-1, 1):
                step = pose["step"] * (1 if (i + (side > 0)) % 2 else -1)
                hx = CX + side * 5
                hyy = th_cy + hy
                kx = CX + int(side * out * reach * ph["spread"])
                ky = hyy - int(up * pose["coil"] * reach)
                fx = kx + side * 2 + step
                line(px, hx, hyy, kx, ky, 'd', thick)
                line(px, kx, ky, fx, min(FLOOR, FLOOR + pose["dy"]), 'd', thick)
                put(px, fx, min(FLOOR, FLOOR + pose["dy"]), 'k')

        # ---- flight shell: only phase 2 cracks the carapace open, and it is
        # most of why the leap silhouette reads as a different animal.
        if ph["wings"]:
            for side in (-1, 1):
                ellipse(px, CX + side * (th_rx + 4), th_cy + 3, 7, 5, 'o')
                ellipse(px, CX + side * (th_rx + 4), th_cy + 3, 5, 3, 'y')

        # ---- abdomen, with concentric plate courses
        ellipse(px, CX, ab_cy, ab_rx, ab_ry, body)
        ellipse(px, CX, ab_cy, ab_rx - 3, ab_ry - 2, shell)
        for i, r in enumerate((ab_rx - 6, ab_rx - 9)):
            if r > 1:
                ellipse(px, CX, ab_cy + 1 + i * 2, r, max(1, ab_ry - 4 - i * 2), body)

        # ---- thorax
        ellipse(px, CX, th_cy, th_rx, th_ry, body)
        ellipse(px, CX, th_cy, th_rx - 4, th_ry - 3, shell)

        # ---- ember showing through the failed carapace
        if ph["cracks"]:
            for (x0, y0, x1, y1) in ((-9, 2, -3, 7), (2, 1, 8, 6),
                                     (-5, -4, 3, -6), (-2, 9, 4, 12)):
                line(px, CX + x0, ab_cy + y0, CX + x1, ab_cy + y1, 'r')
            line(px, CX - 5, th_cy + 1, CX + 5, th_cy + 2, 'r')

        # ---- the fury ridge, last so nothing paints over it: spines burst
        # out along the shoulder of the abdomen and splay away from the spine.
        if ph["spines"]:
            for t, arc in ((-0.85, 0.53), (-0.5, 0.87), (0.0, 1.0),
                           (0.5, 0.87), (0.85, 0.53)):
                sx = CX + int(ab_rx * t)
                sy = ab_cy - int(ab_ry * arc)
                h = 10 - int(abs(t) * 5)
                line(px, sx, sy, sx + int(t * 6), sy - h, 'o')
                line(px, sx + 1, sy, sx + int(t * 6) + 1, sy - h + 3, 'y')

        # ---- head
        ellipse(px, CX, hd_cy, hd_rx, hd_ry, shell)
        ellipse(px, CX, hd_cy + 1, hd_rx - 3, hd_ry - 3, body)

        # ---- eyes. White in FURY, gold otherwise; the pupil is ink.
        eye = 'w' if ph["spines"] else 'y'
        for ex in (CX - 4, CX + 4):
            ellipse(px, ex, hd_cy - 1, 2, 2, eye)
            put(px, ex, hd_cy - 1, 'k')
            put(px, ex, hd_cy, 'k')

        # ---- mandibles: they hang under the head and splay as the jaw opens
        jaw = ph["jaw"] + pose["jaw"]
        for i in range(5):
            spread = (i * jaw) // 6
            for side in (-1, 1):
                x = CX + side * (3 + spread)
                y = hd_cy + hd_ry - 3 + i
                put(px, x, y, 'A')
                put(px, x + side, y, 'a')

        # ---- crown. STOMP holds it forward, LEAP and FURY splay it wide.
        hlen, hspread = ph["horn"]
        line(px, CX, hd_cy - hd_ry + 1, CX, hd_cy - hd_ry + 1 - hlen, 'y')
        line(px, CX - 1, hd_cy - hd_ry + 1, CX - 1, hd_cy - hd_ry + 2 - hlen, 'o')
        for side in (-1, 1):
            line(px, CX + side * 3, hd_cy - hd_ry + 2,
                 CX + side * (3 + hspread), hd_cy - hd_ry + 2 - hlen, 'o')

        return ["".join(r) for r in outline(px)]

    cells = [make(ph, pose) for ph in PHASES for pose in POSES]
    sheet("boss_grove", lit(cells, BOSS), 48, 48)
    print("boss_grove.png  %d frames" % len(cells))
