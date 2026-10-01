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

# ---- Phase A, docs/plan-art-motion.md: the turn. New poses are built the same
# way the run cycle is — recomposing the existing head/torso/leg blocks into
# combinations the first 20 frames never used — except for the half-turn's
# head, which is genuinely new: every other frame in this sheet is drawn in
# profile, and the half-turn is the one beat that has to look at the camera.
#
# Eyes brought together and centred rather than offset toward the leading
# edge (as K_HEAD's profile eyes are), and the hairline swept off-centre, so
# the frame reads as a body caught mid-pivot rather than a second idle pose.
K_HEAD_TURN = list(K_HEAD)
K_HEAD_TURN[0] = ".....kkkkk......"    # hair caught mid-swing, off the part
K_HEAD_TURN[5] = "....kswkkwsk...."    # both eyes toward the camera, a two-
                                       # pixel nose bridge keeping them apart

# plant: braced backward lean, wide low stance (shared with the land pose's
# legs, but K_T_BACK's trailing arm reads as resisting rather than absorbing).
K_TURN_PLANT = _kaya(K_T_BACK, L_LAND, 3)
# half-turn: the pivot itself, face-on. Also played alone (held, no loop) for
# an airborne or slow-speed reversal — see RenderFacingFSM.turn_frame_index().
K_TURN_HALF = _kaya(K_T_BACK, L_PASS, 0, head=K_HEAD_TURN)
# skid: full lean-back over a dug-in crouch.
K_SKID = _kaya(K_T_OUT, L_CROUCH, 3)
# push: shouldering a breakable wall. Two frames of the same forward drive the
# run cycle already has the vocabulary for, cycling slowly while tick_break()
# runs rather than striding.
K_PUSH1 = _kaya(K_T_FWD, L_CONTACT, 1)
K_PUSH2 = _kaya(K_T_FWD, L_DOWN, 2)
# throw: the wind-up (reaching into the swing) and the follow-through (arms
# thrown up and out, same silhouette family as the jump arc's K_T_UP beats).
K_THROW1 = _kaya(K_T_FWD, L_STAND, 0)
K_THROW2 = _kaya(K_T_UP, L_STAND, 0, head=K_HEAD_UP)
# catch: arms out to take the blade back, planted.
K_CATCH = _kaya(K_T_OUT, L_STAND, 0)
# idle fidget: a small weight-shift, a settle, a stretch -- three beats, no
# loop, back to idle. See RenderFacingFSM's sibling timers in player.gd.
K_FIDGET1 = _kaya(K_T_BACK, L_STAND, 0)
K_FIDGET2 = _kaya(K_T_MID, L_CONTACT, 1)
K_FIDGET3 = _kaya(K_T_UP, L_APEX, 0, head=K_HEAD_UP)

# ---- Phase F, docs/plan-art-motion.md: the idle dance. An original eight-beat
# routine -- hip-sway into a two-step, an arm-wave, a little spin, settling
# back toward camera -- built the same way every frame since the run cycle
# has been: recomposing the existing head/torso/leg vocabulary into
# combinations the first 31 frames never used, never drawing a new limb.
# Player.gd plays this list twice through at 8fps (see data/forms/human.json)
# and purely reads velocity/input/time to pick it; nothing here ever writes
# `facing` or any physics state.
K_DANCE1 = _kaya(K_T_BACK, L_CONTACT, 1)             # weight shifts right
K_DANCE2 = _kaya(K_T_MID, L_DOWN, 2)                 # dips into the sway
K_DANCE3 = _kaya(K_T_FWD, _swap(L_CONTACT), 1)       # weight shifts left
K_DANCE4 = _kaya(K_T_MID, _swap(L_DOWN), 2)          # dips the other way
K_DANCE5 = _kaya(K_T_UP, L_APEX, 0, head=K_HEAD_UP)  # the arm-wave, a little hop
K_DANCE6 = _kaya(K_T_OUT, L_PASS, 0)                 # the spin begins, legs crossing
K_DANCE7 = _kaya(K_T_BACK, _swap(L_PASS), 0)         # the spin continues
K_DANCE8 = _kaya(K_T_MID, L_STAND, 0, head=K_HEAD_TURN)  # settle, face-on, back to idle


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
_F_CLING_ROWS = [
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
]
F_CLING = cell(_F_CLING_ROWS)
# Phase B, docs/plan-art-motion.md: the breathing cling's second beat, built
# the same way the human idle's one-pixel breath (K_IDLE_B) is -- drop the
# leading blank row so the whole frog lifts one pixel, a chest-rising inhale.
F_CLING_B = cell(_F_CLING_ROWS[1:])

# Phase B: the apex tuck -- legs pulled up tight at the top of the hop,
# between the leap (toe-off) and the reach (stretching for the landing).
# Shares F_IDLE's head and body rows (the frog's silhouette does not change
# above the hips mid-air) and replaces only the legs with a tight tuck.
F_APEX = cell([
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
    "ggglllllllllggg",
    ".ggg.gggg.ggg..",
])

# Phase B: the tongue-blink idle -- F_BREATHE with the tongue flicked out
# across the mouth row.
F_TONGUE = cell([
    "",
    "",
    "...gg......gg",
    "..gllg....gllg",
    "..glglgggglglg",
    "..gllllllllllg",
    ".glllllllllllllg",
    ".gllGllllllGllg",
    "gllllrrllllllllg",
    ".gllGGllllGGllg",
    ".gGllllllllllGg",
    ".gglllllllllggg",
    "gglgggllllgggglg",
    "glggg.gggg.ggglg",
    "gg.............g",
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
_B_GLIDE_ROWS = [
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
]
B_GLIDE = cell(_B_GLIDE_ROWS)
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
# Phase B, docs/plan-art-motion.md: the glide's feather-ruffle second beat --
# the wing rows shifted one pixel, the body and feet held still, the same
# economy the dropper's shiver (tools/art/sprites_enemies_v2.py) shifts a
# whole body by.
B_GLIDE2 = cell([
    "",
    "",
    "",
    "",
    ".kkkk",
    ".kyyyykkkk",
    "..kyyoooooyyk",
    "..kkoorrrkwrok",
    "....kkrrrrrykk",
    "......kkrryk",
    "........kkk",
    "........yy",
    "........kk",
])
# Phase B: the perch's head-tilt second beat -- the head cap shifted one
# pixel right against the still body.
B_PERCH2 = cell([
    "",
    "",
    "",
    ".....kkkk",
    "....kyyyyk",
    "...kyyoookkk",
    "...kyorrrrrok",
    "...kkorrkwrok",
    "....kkrrrrykk",
    ".....kkrrryk",
    "......kkkkk",
    "........yy",
    "........kk",
])


def _row_shift(row, n):
    """`row` translated `n` pixels right (left if negative), clipped to width.

    The same trick tools/art/sprites_enemies_v2.py's dropper shiver uses to
    animate a whole silhouette by translation rather than redrawing it.
    """
    if n < 0:
        return row[-n:] + "." * -n
    if n > 0:
        return "." * n + row[:-n]
    return row


# Phase B, docs/plan-art-motion.md: the banking turn pair -- the bird is the
# form where turning reads most, so it banks into the new direction rather
# than holding a static half-turn frame (see RenderFacingFSM's `flying`
# parameter). Built by translating the glide silhouette, which is already the
# wings-spread pose a bank naturally extends from.
B_TURN1 = cell([_row_shift(r, -1) for r in _B_GLIDE_ROWS])
B_TURN2 = cell([_row_shift(r, 1) for r in _B_GLIDE_ROWS])

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
        'l': ("grass", 3.5), 'w': ("metal", 6.0),
        'r': ("ember", 3.0)}        # Phase B: the tongue-blink idle frame
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

#: THE STORMCREST. Stone plumage so the bird is not a second purple animal, and
#: three plume characters rather than three maps: the crest and the wing bars
#: are what change colour between phases, and they are a *character* choice in
#: `build_boss_stormcrest()`, which keeps one mapping honest for all 18 frames.
STORM = {'a': ("stone", 2.2), 'A': ("stone", 4.8), 'd': ("stone", 0.5),
         'w': ("metal", 6.0), 'y': ("gold", 4.8), 'o': ("gold", 3.2),
         'r': ("ember", 3.0)}

#: THE TIDE MAW. One mapping for all 18 frames, as the Stormcrest does, with the
#: *character* carrying the phase: 'b' is the drowned blue of EBB, 'c' the lit
#: cyan of FLOOD, 'r' the ember of UNDERTOW. The lure and the eye move up the
#: same three ramps the tide tiles are drawn on, because this animal is meant to
#: read as being made of the water it is standing in.
#:
#: Whole-numbered bases, which is unusual in this file and deliberate: see the
#: note over the sheet() call in build_boss_tide_maw().
TIDE = {'b': ("water", 4.0), 'c': ("water", 5.0), 'r': ("ember", 3.0),
        'n': ("water", 1.0), 'l': ("water", 6.0),
        'y': ("gold", 5.0), 'o': ("gold", 4.0),
        'w': ("metal", 6.0), 'a': ("metal", 5.0)}

#: THE BROOD QUEEN. One mapping for all 18 frames, as the other three bosses
#: have, with the *character* carrying the phase and — uniquely in this game —
#: the character also carrying the POSE. src/enemies/brood_queen.gd draws her at
#: `dark_alpha` on every frame she is not attacking, so the three attack poses
#: are authored on 'w' and 'l' and the crawl on 'n' and 'b'. At 12% alpha the
#: difference between metal 6 and skin 1 is the difference between a flash of a
#: body and nothing at all.
#:
#: She is pale because the fiction is a queen who vanishes into the dark: the
#: base is the `skin` ramp, which is the one ramp in the game with a bone-white
#: top step, and the brood-light between her segments climbs `gold` into `ember`
#: as the fight goes on.
QUEEN = {'n': ("skin", 1.0), 'b': ("skin", 3.0), 'l': ("skin", 5.0),
         'a': ("stone", 3.0), 'w': ("metal", 6.0),
         'y': ("gold", 5.0), 'o': ("gold", 3.0), 'r': ("ember", 5.0)}

#: THE OBSIDIAN HEART. One mapping for all 18 frames, as the other four bosses
#: have, with the *character* carrying the phase. This is the only boss in the
#: game that is not an animal, and the map says so: the shell is drawn on the
#: bottom two steps of `purple` — the darkest near-black in the ramp table that
#: is still a colour — with a cold `water` sheen for the rim of a glass edge,
#: and everything that is alight climbs `gold` into `ember`.
#:
#: Whole-numbered bases, the Tide Maw's setting and the Brood Queen's: one very
#: large flat mass, where a fractional ramp level dithers into a checkerboard.
OBSIDIAN = {'g': ("purple", 0.0), 'G': ("purple", 2.0), 'h': ("water", 4.0),
            'w': ("metal", 6.0),
            'o': ("gold", 3.0), 'y': ("gold", 5.0),
            'r': ("ember", 3.0), 'R': ("ember", 5.0)}

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
    # jump arc (anticipate, launch, rise, apex, fall, land), 16-18 climb, 19
    # hurt, 20-21 turn (plant, half-turn), 22 skid, 23-24 push, 25-26 throw,
    # 27 catch, 28-30 idle fidget (Phase A), 31-38 the idle dance (Phase F).
    sheet("kaya_human",
          lit([K_IDLE, K_IDLE_B] + K_RUN
              + [K_CROUCH, K_LAUNCH, K_RISE, K_APEX, K_FALL, K_LAND,
                 K_CLIMB1, K_CLIMB2, K_CLIMB3, K_HURT,
                 K_TURN_PLANT, K_TURN_HALF, K_SKID, K_PUSH1, K_PUSH2,
                 K_THROW1, K_THROW2, K_CATCH,
                 K_FIDGET1, K_FIDGET2, K_FIDGET3,
                 K_DANCE1, K_DANCE2, K_DANCE3, K_DANCE4,
                 K_DANCE5, K_DANCE6, K_DANCE7, K_DANCE8], KAYA, dark=0.75),
          16, 24, selout=True)
    # 0 idle, 1 breath, 2 crouch (anticipation; also reused as the turn frame),
    # 3 leap (also reused as the wall-kick flash), 4 reach, 5 cling, 6 apex
    # (mid-air tuck), 7 tongue-blink idle, 8 cling breathe. 6-8 are Phase B,
    # docs/plan-art-motion.md.
    sheet("kaya_frog", lit([F_IDLE, F_BREATHE, F_CROUCH, F_LEAP,
                            F_REACH, F_CLING, F_APEX, F_TONGUE,
                            F_CLING_B], FROG), 16, 16, selout=True)
    # 0-3 the swim beat, 4 bite, 5 flop. Mirrored so the unflipped cell faces
    # right, which is the direction `facing == 1` draws.
    sheet("kaya_fish", lit([mirror(c) for c in
                            (FI_TAIL_MID, FI_TAIL_UP, FI_TAIL_MID2,
                             FI_TAIL_DOWN, FI_BITE, FI_FLOP)], FISH), 16, 16, selout=True)
    # 0-3 the flap beat, 4 glide, 5 perch, 6 glide ruffle, 7 perch head-tilt,
    # 8-9 the banking turn pair. 6-9 are Phase B, docs/plan-art-motion.md.
    sheet("kaya_bird", lit([B_UP, B_MIDA, B_DOWN, B_MIDB,
                            B_GLIDE, B_PERCH, B_GLIDE2, B_PERCH2,
                            B_TURN1, B_TURN2], BIRD), 16, 16, selout=True)
    sheet("enemy_walker", lit([walker(i) for i in range(4)], WALKER), 16, 16,
          selout=True)
    # 0 idle, 1-2 the telegraph, 3 airborne, 4 the landing squash
    sheet("enemy_jumper", lit([E_J_IDLE, E_J_CROUCH, E_J_COIL,
                               E_J_AIR, E_J_LAND], JUMPER), 16, 16, selout=True)
    # 0 closed, 1-3 the telegraph, 4 the spit
    sheet("enemy_shooter", lit([E_S_IDLE, E_S_STIR, E_S_INHALE,
                                E_S_SWELL, E_S_FIRE], SHOOTER), 16, 16, selout=True)
    sheet("enemy_swimmer", lit([mirror(cell(c)) for c in
                                (E_SW_MID, E_SW_UP, E_SW_BITE, E_SW_DOWN)],
                               SWIMMER), 16, 16, selout=True)
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
    sheet("boss_grove", lit(cells, BOSS), 48, 48, selout=True)
    print("boss_grove.png  %d frames" % len(cells))


def build_boss_stormcrest():
    """THE STORMCREST — 48x48, six frames per fight phase, heights_5.

    A hook-beaked ridge raptor. It is drawn **facing left**, which is the
    convention the fish sheet already set for an asymmetric animal, and
    `Enemy.draw()` mirrors it for the other direction.

    Frame order is the contract with data/enemies/stormcrest.json, which names
    the six poses `<pose>_p1/_p2/_p3`, and src/enemies/stormcrest.gd picks the
    suffix for the phase it is in:

        0 idle (perched)  1-2 the stalk  3 windup  4 airborne  5 landing splay

    The fight's one idea is that it is only vulnerable while it is *roosting*,
    so the art has one job above all others: the player must be able to tell,
    across the width of a screen and in a fifth of a second, whether the animal
    is up or down. Everything below serves that.

      * **Airborne is a diagonal.** Frame 4 is the whole body rotated nose-down
        through 34 degrees with the legs tucked away. No other frame is off the
        horizontal, so the silhouette alone answers the question.
      * **Roosting is legs.** Frames 0, 1, 2, 3 and 5 are the only ones that
        draw legs and talons standing on the floor row.

    Phases differ in silhouette as well as in value, the rule
    jungle-platformer-plan.md set for the Grove Warden ("visually distinct
    phases rather than a colour swap"): the crest lengthens and fans wider, the
    wing span grows and the tail draws out, phase by phase. Value carries the
    rest — stone-grey plumage lit white in EYRIE, bleached with a gold crest in
    SQUALL, storm-dark with an ember crest and a red eye in TEMPEST — and it
    is what the screenshots read at 400x240.
    """
    import math

    W = H = 48
    FLOOR = 46
    CX, CY = 24, 24

    # ---- per phase: how the bird is built, and which character its plumage is
    # drawn in. `body`/`belly` are the two plumage masses, `plume` the crest and
    # the wing bars, `eye` the one pixel the player looks for.
    PHASES = [
        dict(name="EYRIE", body='a', belly='A', plume='w', eye='y',
             crest=7, fan=5, span=16, tail=11, ember=0),
        dict(name="SQUALL", body='A', belly='w', plume='y', eye='y',
             crest=9, fan=6, span=18, tail=13, ember=0),
        dict(name="TEMPEST", body='d', belly='a', plume='o', eye='r',
             crest=11, fan=7, span=20, tail=15, ember=1),
    ]
    # dy      how far the mass sits off its perched height
    # ang     nose-down rotation of the whole animal, in degrees
    # open    how far the wing is held off the body, 0 folded .. 1 spread
    # step    the stalking leg slide
    # fanned  extra spread on the crest
    # legs    whether feet are on the floor at all
    POSES = [
        dict(dy=0, ang=0, open=0.0, step=0, fanned=0.0, legs=1),   # idle
        dict(dy=1, ang=0, open=0.2, step=3, fanned=0.2, legs=1),   # stalk A
        dict(dy=0, ang=0, open=0.3, step=-3, fanned=0.0, legs=1),  # stalk B
        dict(dy=4, ang=0, open=0.5, step=0, fanned=1.0, legs=1),   # windup
        dict(dy=-8, ang=34, open=1.0, step=0, fanned=0.6, legs=0),  # airborne
        dict(dy=2, ang=0, open=1.0, step=5, fanned=0.8, legs=1),   # landing
    ]

    def make(ph, pose):
        px = [['.'] * W for _ in range(H)]
        rad = math.radians(pose["ang"])
        ca, sa = math.cos(rad), math.sin(rad)

        def put(x, y, c):
            """Plot in body space: rotated about the mass, then to the grid."""
            dx, dy = x - CX, y - CY
            gx = int(round(CX + dx * ca - dy * sa))
            gy = int(round(CY + dx * sa + dy * ca))
            if 0 <= gx < W and 0 <= gy < H:
                px[gy][gx] = c

        def raw(x, y, c):
            """Plot straight to the grid — for the legs, which do not rotate."""
            if 0 <= int(x) < W and 0 <= int(y) < H:
                px[int(y)][int(x)] = c

        def ellipse(cx, cy, rx, ry, c):
            # Half-pixel steps: a rotated forward-mapped fill drops pixels at
            # the diagonal otherwise, and frame 4 is nothing but diagonal.
            n = int(max(rx, ry) * 4) + 4
            for j in range(-n, n + 1):
                for i in range(-n, n + 1):
                    x, y = cx + i * 0.5, cy + j * 0.5
                    if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                        put(x, y, c)

        def line(x0, y0, x1, y1, c, thick=1):
            n = int(max(abs(x1 - x0), abs(y1 - y0), 1) * 2)
            for i in range(n + 1):
                x = x0 + (x1 - x0) * i / n
                y = y0 + (y1 - y0) * i / n
                for t in range(thick):
                    put(x, y + t, c)

        def stroke(x0, y0, x1, y1, w0, w1, c):
            """A limb: a line with a width that tapers from end to end.

            Everything on a bird that is not a ball is one of these — the wing,
            the tail wedge, the legs — and drawing them as tapered masses
            rather than as lines is the difference between a raptor and a hen.
            """
            dx, dy = x1 - x0, y1 - y0
            ln = max(math.hypot(dx, dy), 0.001)
            nx, ny = -dy / ln, dx / ln              # the perpendicular
            n = int(ln * 2) + 1
            for i in range(n + 1):
                t = i / n
                x, y = x0 + dx * t, y0 + dy * t
                wd = w0 + (w1 - w0) * t
                m = int(wd * 2) + 1
                for s in range(-m, m + 1):
                    if abs(s * 0.5) <= wd:
                        put(x + nx * s * 0.5, y + ny * s * 0.5, c)

        body, belly, plume = ph["body"], ph["belly"], ph["plume"]
        base = FLOOR - 8 + pose["dy"]               # underside of the breast
        bx, by = CX + 2, base - 7                   # the mass
        hx, hy = CX - 9, by - 9                     # the head
        openness = pose["open"]

        # ---- tail: a solid wedge off the back, low, drawn first so the wing
        # covers its root. It lengthens phase by phase and is the second thing
        # that separates a TEMPEST silhouette from an EYRIE one.
        tl = ph["tail"]
        stroke(bx + 5, by + 3, bx + 5 + tl, by + 6, 2.0, 4.5, body)
        for i in range(3):
            line(bx + 7, by + 3 + i * 1.5, bx + 5 + tl, by + 4 + i * 2.6, plume)

        # ---- the mass, and the pale breast the eye tracks in flight. The body
        # is an egg lying forward, not a sphere: the breast is the low left.
        ellipse(bx, by, 11, 8, body)
        ellipse(bx - 4, by + 2, 7, 6, belly)

        # ---- wing. Folded it is a plate lying along the back; spread it swings
        # up and back, and a rank of primaries runs off the tip. This is the
        # whole read of frames 4 and 5, and the bars are the plume colour, so
        # the phase is legible on a bird that is nothing but wing.
        span = ph["span"] * (0.55 + 0.45 * openness)
        wx, wy = bx - 2, by - 5
        ang = -0.10 - 0.85 * openness               # radians, up and back
        tipx = wx + math.cos(ang) * span
        tipy = wy + math.sin(ang) * span
        stroke(wx, wy, tipx, tipy, 5.0, 2.2, body)
        stroke(wx, wy + 1, wx + (tipx - wx) * 0.5, wy + (tipy - wy) * 0.5,
               3.5, 2.0, belly)
        for i in range(4):
            t = 0.6 + i * 0.13
            fx = wx + (tipx - wx) * t
            fy = wy + (tipy - wy) * t
            line(fx, fy, fx + (3 + i * 1.5) * (0.5 + openness),
                 fy + 1 + i * 0.9, plume)

        # ---- head, beak and eye. The beak is a hook — a gold wedge with the
        # tip bent down — and it is the only part of the animal that points at
        # the player.
        ellipse(hx, hy, 6, 5, body)
        ellipse(hx - 1, hy + 2, 4, 3, belly)
        stroke(hx - 3, hy + 1, hx - 10, hy + 1, 3.0, 1.2, 'o')
        stroke(hx - 9, hy + 1, hx - 8, hy + 4, 1.4, 0.6, 'o')
        put(hx - 10, hy + 2, 'k')
        for ex in (hx - 3, hx - 2):
            put(ex, hy - 1, ph["eye"])
        put(hx - 3, hy - 1, 'k')

        # ---- the crest: a fan of feathers off the crown, swept back over the
        # shoulders. This is the animal's name, so it is the largest thing on
        # the head and it grows every phase.
        cl = ph["crest"]
        spread = 0.55 + 0.35 * pose["fanned"]
        for i in range(ph["fan"]):
            t = (i / max(1, ph["fan"] - 1)) - 0.5
            line(hx - 1 + i * 0.6, hy - 4,
                 hx - 1 + i * 0.6 + cl * spread * (0.5 + t),
                 hy - 4 - cl * (1.0 - abs(t) * 0.5), plume)

        # ---- ember showing through a storm-dark bird, so TEMPEST is not just
        # a dark shape on a grey wall.
        if ph["ember"]:
            for (x0, y0, x1, y1) in ((-6, -2, -1, 2), (0, -5, 5, -2),
                                     (-3, 4, 3, 6)):
                line(bx + x0, by + y0, bx + x1, by + y1, 'r')

        # ---- legs and talons, and only when it is down. Straight to the grid:
        # a rotated bird still stands on level ground, and in the one frame
        # where it does not, it has no legs out at all.
        if pose["legs"]:
            for side, off in ((-1, -5), (1, 1)):
                fx = int(bx + off + side * pose["step"] * 0.5)
                for y in range(int(base) + 2, FLOOR + 1):
                    raw(fx, y, 'o')
                    raw(fx + 1, y, 'o')
                for t in range(-3, 4):              # the talons
                    raw(fx + t, FLOOR + 1, 'o')
                raw(fx - 4, FLOOR, 'o')
                raw(fx + 4, FLOOR, 'o')

        # ---- ink outline, the last pass, exactly as the Warden does it.
        out = [row[:] for row in px]
        for y in range(H):
            for x in range(W):
                if px[y][x] != '.':
                    continue
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and px[yy][xx] not in ('.', 'k'):
                        out[y][x] = 'k'
                        break
        return ["".join(r) for r in out]

    cells = [make(ph, pose) for ph in PHASES for pose in POSES]
    sheet("boss_stormcrest", lit(cells, STORM), 48, 48, selout=True)
    print("boss_stormcrest.png  %d frames" % len(cells))


def build_boss_tide_maw():
    """THE TIDE MAW — 48x48, six frames per fight phase, ruins_5.

    An anglerfish beached in a flooded cistern: a heavy trunk running off the
    bottom-left corner of the frame, a blunt skull, a lure on a stalk arcing up
    over the head, and a gape that is half the animal. It is drawn **facing
    right**, which is the sheet convention `Enemy.draw()` assumes (`flip_h` when
    `facing < 0`), and unlike the Stormcrest it needs no rotation: every pose is
    the same animal with the jaw hinged open by a different amount.

    Frame order is the contract with data/enemies/tide_maw.json, which names the
    six poses `<pose>_p1/_p2/_p3`, and src/enemies/tide_maw.gd picks the suffix
    for the phase it is in:

        0 idle  1-2 the walk  3 windup  4 airborne  5 landing

    The fight's one idea is the tide: the arena floods and drains under the
    player, and the boss is the thing that is doing it. So the art has two jobs.

      * **The gape is the telegraph.** `gape` is the half-height of the mouth at
        its tip, and it runs 4 px at rest to 13 px airborne. That is the widest
        silhouette change in the sheet and it is on the half of the animal the
        player is standing in front of, so a slam reads before it lands.
      * **The lure is the phase.** The bulb is the brightest pixel in the frame
        and the only one that changes hue between phases — cyan in EBB, gold in
        FLOOD, ember-orange in UNDERTOW — so the fight state is legible from a
        single 3x3 blob at the top of the frame even when the body is in shadow.

    Phases differ in silhouette as well as in value, the rule the plan set for
    the Grove Warden: the jaw lengthens, the resting gape opens, gill rakers cut
    into the cheek and UNDERTOW grows barbels off the chin. Value carries the
    rest, up the water ramp and then off it: drowned blue, lit cyan, ember.
    """
    import math

    W = H = 48
    FLOOR = 47
    # The head sits left of centre and low, because the mouth is what has to
    # have room. Everything below is measured off this one point.
    HX = 16

    PHASES = [
        dict(name="EBB", body='b', lure='l', eye='l',
             jaw=20, gape=0, gills=0, barb=0),
        dict(name="FLOOD", body='c', lure='y', eye='w',
             jaw=22, gape=1, gills=3, barb=0),
        dict(name="UNDERTOW", body='r', lure='o', eye='y',
             jaw=24, gape=2, gills=4, barb=1),
    ]
    # dy     how far the whole animal sits off its resting height
    # gape   half-height of the mouth at the tip, before the phase's own bonus
    # tilt   where the tip of the mouth points, + is down
    # stalk  how much of the lure's arc is extended, 0 folded .. 1 full
    # swing  sideways drift of the bulb, so the lure is never quite still
    POSES = [
        dict(dy=0, gape=5, tilt=0, stalk=1.0, swing=0),     # idle
        dict(dy=-1, gape=5, tilt=0, stalk=1.0, swing=1),    # walk A
        dict(dy=0, gape=4, tilt=1, stalk=0.95, swing=-1),   # walk B
        dict(dy=-4, gape=4, tilt=1, stalk=0.28, swing=0),   # windup
        dict(dy=-3, gape=13, tilt=-3, stalk=1.0, swing=2),  # airborne
        dict(dy=3, gape=10, tilt=4, stalk=0.9, swing=-2),   # landing
    ]

    def make(ph, pose):
        px = [['.'] * W for _ in range(H)]

        def put(x, y, c):
            x, y = int(round(x)), int(round(y))
            if 0 <= x < W and 0 <= y < H:
                px[y][x] = c

        def ellipse(cx, cy, rx, ry, c):
            for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
                for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                    if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                        put(x, y, c)

        def stroke(x0, y0, x1, y1, w0, w1, c):
            """A tapered mass — the trunk and the two jaws are all one of these.

            Same helper the Stormcrest's wing uses, and for the same reason: a
            fish drawn out of lines is a skeleton, a fish drawn out of tapered
            masses is an animal.
            """
            dx, dy = x1 - x0, y1 - y0
            ln = max(math.hypot(dx, dy), 0.001)
            nx, ny = -dy / ln, dx / ln          # the unit perpendicular
            n = int(ln * 2) + 1
            for i in range(n + 1):
                t = i / n
                x, y = x0 + dx * t, y0 + dy * t
                wd = w0 + (w1 - w0) * t
                m = int(wd * 2) + 1
                for s in range(-m, m + 1):
                    if abs(s * 0.5) <= wd:
                        put(x + nx * s * 0.5, y + ny * s * 0.5, c)

        def wedge(ax, ay, bx, by, cx, cy, c):
            """The mouth cavity: the triangle hinge -> upper tip -> lower tip,
            filled in ink so it cuts back through the skull rather than sitting
            on top of it."""
            lo_y, hi_y = int(min(ay, by, cy)), int(max(ay, by, cy))
            lo_x, hi_x = int(min(ax, bx, cx)), int(max(ax, bx, cx))
            for y in range(lo_y - 1, hi_y + 2):
                for x in range(lo_x - 1, hi_x + 2):
                    d1 = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
                    d2 = (cx - bx) * (y - by) - (cy - by) * (x - bx)
                    d3 = (ax - cx) * (y - cy) - (ay - cy) * (x - cx)
                    if not ((d1 < 0 or d2 < 0 or d3 < 0)
                            and (d1 > 0 or d2 > 0 or d3 > 0)):
                        put(x, y, c)

        body, lure, eye = ph["body"], ph["lure"], ph["eye"]
        hy = 18 + pose["dy"]                        # the skull
        jx, jy = HX + 4, hy + 2                     # the jaw hinge
        length = ph["jaw"]
        gape = pose["gape"] + ph["gape"]
        tipx = min(W - 3, jx + length)
        tipy = jy + pose["tilt"]

        # ---- the trunk, first and behind everything: one tapered mass leaving
        # the frame at the bottom-left, so the animal is always bigger than the
        # 48x48 it is drawn in and the arena never contains all of it.
        stroke(HX + 2, hy + 3, 1, FLOOR + 9, 7.5, 10.0, body)

        # ---- the skull. Blunt, wider than it is tall, and sitting forward of
        # the trunk so the two masses do not read as one sausage.
        ellipse(HX, hy, 9, 8, body)
        ellipse(HX + 3, hy - 1, 7, 7, body)

        # ---- the operculum: an ink break down the back of the cheek. Two
        # masses in one material have no edge between them for auto_shade() to
        # light, so the head is separated by hand or it is not separated.
        for i in range(11):
            t = i / 10.0
            put(HX - 8 + t * 2.0, hy - 6 + i, 'k')

        # ---- the mouth. Cavity first, then the two jaws over its edges, so the
        # jaws stay solid however far the gape opens.
        wedge(jx - 3, jy, tipx, tipy - gape, tipx, tipy + gape, 'k')
        stroke(jx - 4, jy - 4, tipx, tipy - gape - 1, 2.6, 1.2, body)
        stroke(jx - 4, jy + 4, tipx, tipy + gape + 1, 3.0, 1.6, body)

        # ---- teeth. Two staggered ranks per jaw, spaced so that the mouth
        # reads as a comb rather than as a hole even at a fifth of a second.
        for i in range(6):
            t = 0.18 + i * 0.15
            ux = jx + (tipx - jx) * t
            uy = jy + (tipy - gape - jy) * t
            ly = jy + (tipy + gape - jy) * t
            put(ux, uy + 1, 'w')
            put(ux, uy + 2, 'a')
            put(ux, ly - 1, 'w')
            put(ux, ly - 2, 'a')

        # ---- gill rakers, cut into the cheek. FLOOD grows them, UNDERTOW grows
        # one more: the animal is opening up as the fight goes on.
        for i in range(ph["gills"]):
            x = HX - 6 + i * 2
            for y in range(hy - 3, hy + 3):
                put(x, y, 'k')

        # ---- barbels, UNDERTOW only: two feelers off the chin that trail back
        # under the trunk and make the last phase unmistakable in silhouette.
        if ph["barb"]:
            for i in range(2):
                stroke(jx - 5 + i * 3, jy + 7, jx - 13 + i * 2,
                       jy + 13 + i * 3, 1.2, 0.5, body)

        # ---- the eye: a block in an ink socket, with a white catchlight and no
        # pupil. It is the second-brightest thing in the frame and it never
        # blinks, which is most of why the animal reads as dead-eyed.
        ex, ey = HX + 2, hy - 5
        ellipse(ex, ey, 3, 3, 'k')
        ellipse(ex, ey, 2, 2, eye)
        put(ex + 1, ey - 1, 'w')

        # ---- the illicium: a thin stalk off the crown arcing up and forward,
        # with the bulb hanging over the mouth where the prey is meant to look.
        s = pose["stalk"]
        arc = ((0, -2), (1, -4), (3, -6), (6, -7), (10, -7))
        bx, by = HX - 4, hy - 9
        prev = (bx, by)
        for i, (ox, oy) in enumerate(arc):
            if (i + 1) / len(arc) > s:
                break
            nxt = (bx + ox * s + pose["swing"] * (i / len(arc)), by + oy * s)
            stroke(prev[0], prev[1], nxt[0], nxt[1], 0.9, 0.9, body)
            prev = nxt
        # The bulb is the brightest thing in the frame and the one the player
        # tracks, so it is drawn twice: the lure colour over a ring of it, which
        # at 48x48 is the difference between a lamp and a stray pixel.
        ellipse(prev[0] + 2, prev[1] - 1, 3.2, 3.0, lure)
        ellipse(prev[0] + 2, prev[1] - 1, 1.0, 1.0, 'w' if lure != 'w' else 'y')
        put(prev[0] + 3, prev[1] - 2, 'w')

        # ---- ink outline, the last pass, exactly as the other two bosses.
        out = [row[:] for row in px]
        for y in range(H):
            for x in range(W):
                if px[y][x] != '.':
                    continue
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and px[yy][xx] not in ('.', 'k'):
                        out[y][x] = 'k'
                        break
        return ["".join(r) for r in out]

    cells = [make(ph, pose) for ph in PHASES for pose in POSES]
    # depth/rate/lit/dark all whole numbers, which is the one place this animal
    # differs from the other two bosses: its masses are large and flat, and a
    # fractional ramp level is drawn as a dither, so the default 0.7/1.1/0.95
    # puts a checkerboard across half the frame. Whole steps give the four flat
    # tones the rest of the ruins art is drawn in.
    sheet("boss_tide_maw",
          lit(cells, TIDE, depth=2, rate=1.0, lit=1.0, dark=1.0), 48, 48,
          selout=True)
    print("boss_tide_maw.png  %d frames" % len(cells))



def build_boss_brood_queen():
    """THE BROOD QUEEN — 48x48, six frames per fight phase, deeps_5.

    A termite queen: a physogastric abdomen the size of the rest of her put
    together, dragged along by a small armoured thorax and a head that is mostly
    mandibles. She is drawn **facing right** — abdomen at the left of the frame,
    jaws leaving it at the right — which is the sheet convention
    `Enemy._update_anim()` assumes (`flip_h` when `facing < 0`).

    Frame order is the contract with data/enemies/brood_queen.json, which names
    the six poses `<pose>_p1/_p2/_p3`, and src/enemies/brood_queen.gd picks the
    suffix for the phase it is in:

        0 idle   1-2 the crawl   3 windup   4 the burrow charge   5 the slam

    **The brightness is the mechanic, not the mood.** This is the one boss in the
    game that is not always drawn: `brood_queen.gd` fades her sprite towards
    `dark_alpha` on every frame she is not attacking, and back to full on the
    frames she is. So the three *attack* poses — windup, charge, slam — carry a
    rim of the brightest character in the map along the abdomen's crown, the
    thorax plate and the jaws, and the crawl beats carry none. At 12 % alpha over
    a dark chamber the crawl is a suggestion and the slam is a white-hot flash of
    a body, which is the fight's sentence made out of pixels rather than a tint.

    Phases differ in silhouette as well as in value, the rule the plan set for
    the Grove Warden:

      BROOD   smooth and banded, jaws nearly shut, head low. Bone against earth.
      SWARM   the bands have parted — brood-light shows between them — three egg
              blisters have swollen under the flank and the jaws are open.
      HATCH   the abdomen has split. Ember light pours out of four ruptured
              segments, grub spines have erupted along the back, and the jaws do
              not close again.

    The 40x46 collision box sits at (4, 2) in the frame, which is the
    Stormcrest's box and is measured rather than chosen: a body standing on
    deeps_5's one-way shelf has its chest at y=383..395, and a 46 px body
    standing on the arena floor spans y=386..432, so the blade reaches her from a
    shelf AND her body reaches a body standing on one. A refuge that is safe from
    the boss forever is a corner to camp in.
    """
    import math

    W = H = 48
    FLOOR = 46
    ## The abdomen's centre and half-extents. Everything is measured off this one
    ## point, because the abdomen is four fifths of the animal and the head gets
    ## the room that is left.
    ##
    ## She is drawn this big on purpose. The first cut of this sheet put a 34 px
    ## animal inside a 46 px hurtbox, which is the Grove Warden's own recorded
    ## mistake — "a hurtbox larger than the thing that hurts you is the worst
    ## kind of unfair" — so the abdomen was grown until the drawn pixels span
    ## rows 3..47 of the frame and the dorsal tubercles below exist to carry the
    ## crown of it the last few rows.
    AX0, AY0 = 17.0, 27.0
    ARX, ARY = 15.5, 15.0

    # body    the abdomen wall
    # seg     the ink-adjacent band colour
    # glow    what shows BETWEEN the bands: the phase, in one colour
    # plate   the thorax and head capsule
    # jaw     the mandibles
    # split   None, or the colour pouring out of a ruptured segment
    PHASES = [
        dict(name="BROOD", body='b', seg='n', glow='n', plate='a', jaw='a',
             split=None, blisters=0, spines=0, gape=2),
        dict(name="SWARM", body='l', seg='b', glow='y', plate='b', jaw='y',
             split=None, blisters=3, spines=0, gape=4),
        dict(name="HATCH", body='l', seg='b', glow='r', plate='y', jaw='r',
             split='r', blisters=3, spines=5, gape=7),
    ]
    # dy      how far the whole animal sits off its resting height
    # arch    how much the abdomen is hunched, + is up
    # reach   how far the head is thrust forward (+ is toward the jaws)
    # legs    the leg phase, -1 / 0 / +1
    # lit     the highlight character for THIS pose, or None. The three attack
    #         poses are the lit ones; see the docstring.
    # dust    how many flung specks of earth sit under her
    POSES = [
        dict(dy=0, arch=0, reach=0, legs=0, lit=None, dust=0),     # idle
        dict(dy=-1, arch=1, reach=1, legs=-1, lit=None, dust=0),   # crawl A
        dict(dy=0, arch=-1, reach=-1, legs=1, lit=None, dust=0),   # crawl B
        dict(dy=-3, arch=4, reach=-2, legs=0, lit='w', dust=3),    # windup
        dict(dy=1, arch=-2, reach=4, legs=1, lit='w', dust=6),     # charge
        dict(dy=2, arch=-3, reach=1, legs=-1, lit='w', dust=8),    # slam
    ]

    def make(ph, pose):
        px = [['.'] * W for _ in range(H)]

        def put(x, y, c):
            x, y = int(round(x)), int(round(y))
            if 0 <= x < W and 0 <= y < H:
                px[y][x] = c

        def ellipse(cx, cy, rx, ry, c):
            for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
                for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                    if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                        put(x, y, c)

        def stroke(x0, y0, x1, y1, w0, w1, c):
            """A tapered mass. The same helper the Stormcrest's wing and the
            Maw's jaw are built from, and for the same reason: an animal drawn
            out of lines is a skeleton, one drawn out of masses is an animal."""
            dx, dy_ = x1 - x0, y1 - y0
            ln = max(math.hypot(dx, dy_), 0.001)
            nx, ny = -dy_ / ln, dx / ln
            n = int(ln * 2) + 1
            for i in range(n + 1):
                t = i / n
                x, y = x0 + dx * t, y0 + dy_ * t
                wd = w0 + (w1 - w0) * t
                m = int(wd * 2) + 1
                for s in range(-m, m + 1):
                    if abs(s * 0.5) <= wd:
                        put(x + nx * s * 0.5, y + ny * s * 0.5, c)

        body, seg, glow = ph['body'], ph['seg'], ph['glow']
        lit_c = pose['lit']
        dy = pose['dy']
        AX, AY = AX0, AY0 + dy - pose['arch'] * 0.6

        # ---- the ovipositor first, behind everything: a tapered tail leaving
        # the frame at the bottom-left, so the animal is always bigger than the
        # 48x48 she is drawn in and the arena never contains all of her.
        stroke(AX - 9, AY + 6, -4, FLOOR + dy, 5.0, 2.5, seg)

        # ---- the abdomen.
        ellipse(AX, AY, ARX, ARY, body)
        ellipse(AX - 1, AY + 2, ARX - 2.0, ARY - 1.5, body)

        # ---- four dorsal tubercles along the crown. Every phase has them: they
        # are what makes the top of the silhouette a row of humps rather than an
        # arc, and they are what carries the drawn animal up to the top of its
        # own hurtbox.
        for i in range(4):
            t = -0.48 + i * 0.32
            tx = AX + ARX * t
            ty = AY - ARY * (1.0 - t * t) ** 0.5
            ellipse(tx, ty, 4.6, 5.2, body)
            put(tx - 1, ty - 4, seg)

        # ---- six segment bands, bowed round the body, ink with the phase's
        # brood-light showing behind each one. This is the only place the colour
        # of the fight appears at rest, and it is deliberately thin: at 400x240 a
        # queen who is one flat mass reads as a boulder until the bands catch.
        for i in range(5):
            t = -0.56 + i * 0.28
            for j in range(-16, 17):
                v = j / (ARY * 0.88)
                if t * t + v * v > 0.92:
                    continue
                bow = 2.0 * (1.0 - v * v)
                sx = AX + ARX * t + bow
                put(sx, AY + j, 'k')
                put(sx + 1, AY + j, glow if i % 2 else seg)

        # ---- the ruptures. HATCH only: four segments have failed outright and
        # what is inside is what lights the chamber. Drawn over the bands, so the
        # abdomen visibly comes apart instead of changing hue.
        if ph['split'] is not None:
            for i in range(4):
                sx = AX + ARX * (-0.46 + i * 0.28)
                sy = AY - 5 + (i % 2) * 9
                ellipse(sx, sy, 2.8, 4.0, 'k')
                ellipse(sx, sy, 1.5, 2.6, ph['split'])

        # ---- egg blisters under the flank, SWARM and HATCH: three lumps that
        # change the silhouette, which is the phase rule.
        for i in range(ph['blisters']):
            bx = AX - 7 + i * 7
            ellipse(bx, AY + ARY - 1, 3.6, 3.2, body)
            put(bx - 1, AY + ARY - 2, glow)

        # ---- grub spines, HATCH only: a ridge erupting along the back, so the
        # last phase is unmistakable in pure silhouette.
        for i in range(ph['spines']):
            bx = AX - 9 + i * 5
            stroke(bx, AY - ARY + 2, bx - 1, AY - ARY - 6 - (i % 2) * 3,
                   1.7, 0.4, ph['glow'])

        # ---- the thorax: the hinge between the enormous back end and the small
        # front one, and an ink break so the two do not read as one sausage.
        TX = AX + ARX + 3.0 + pose['reach'] * 0.5
        TY = AY + 4.0 + pose['arch'] * 0.3
        ellipse(TX, TY, 6.8, 7.4, ph['plate'])
        ellipse(TX - 2, TY, 5.2, 6.2, body)
        for j in range(-7, 8):
            put(TX - 5.5, TY + j, 'k')

        # ---- six legs, three a side, short and splayed under the thorax and the
        # front of the abdomen. The far rank is a step out of phase and a shade
        # down, which is what makes the crawl read as a crawl and not a slide.
        for far in (1, 0):
            c = seg if far else ph['plate']
            for i in range(3):
                lx = TX - 3 - i * 7
                sw = (pose['legs'] if far else -pose['legs']) * (1 + i)
                knee_y = AY + ARY + 1 + far
                stroke(lx, AY + ARY - 3, lx + 3 + sw, knee_y, 2.0, 1.1, c)
                stroke(lx + 3 + sw, knee_y, lx + sw * 2, FLOOR + dy - far * 2,
                       1.3, 0.7, c)

        # ---- the head capsule and the mandibles: the one part of her that is a
        # weapon, and the part the charge leads with.
        hx = TX + 7.0 + pose['reach']
        hy = TY + 1.0
        # The neck first, so a head thrust four pixels forward on the charge
        # frame is still attached to the animal it belongs to.
        stroke(TX + 2, TY + 0.5, hx, hy, 5.0, 4.4, body)
        ellipse(hx, hy, 6.0, 5.6, ph['plate'])
        ellipse(hx - 1, hy - 1, 4.0, 3.8, body)
        # Blind, like the real animal: two pits where eyes would be, lit from
        # inside by the same brood-light as the segments. The queen never looks
        # at you, and that is most of why she is frightening.
        for s in (-1, 1):
            ellipse(hx - 1, hy + s * 2.6, 1.7, 1.5, 'k')
            put(hx - 1, hy + s * 2.6, glow)
        # Two mandibles, hinged at the cheek, opening by `gape` as the fight goes
        # on and by two more on every attack frame. This is the widest part of
        # the silhouette and the thing a player reads a charge off.
        gape = ph['gape'] + (2 if lit_c else 0)
        for s in (-1, 1):
            tipx = min(W - 2, hx + 9)
            stroke(hx + 3, hy + s * 2, tipx, hy + s * (1 + gape), 2.4, 1.0,
                   ph['jaw'])
            put(tipx, hy + s * (1 + gape), 'w')
            put(tipx - 1, hy + s * (1 + gape), 'w')

        # ---- flung earth. The windup, the charge and the slam throw the floor
        # about, and these specks are the part of the telegraph that survives at
        # ANY alpha, because they sit on the ground rather than on her.
        for i in range(pose['dust']):
            a = 0.30 + i * 0.38
            r = 4 + i * 3
            put(hx + 4 + r * math.cos(a), FLOOR + dy - r * math.sin(a) * 0.55,
                ph['jaw'])

        # ---- the pose highlight: a rim of the brightest character in the map
        # over the abdomen's crown and the thorax. Drawn last so nothing buries
        # it, and it is the whole reason this sheet is authored per-pose.
        if lit_c is not None:
            for i in range(30):
                t = i / 29.0
                a = math.pi * (1.06 + t * 0.62)
                put(AX + ARX * math.cos(a), AY + ARY * math.sin(a), lit_c)
                put(AX + (ARX - 1.4) * math.cos(a), AY + (ARY - 1.3) * math.sin(a),
                    lit_c)
            ellipse(TX - 1, TY - 4, 3.4, 1.6, lit_c)

        # ---- ink outline, the last pass, exactly as the other three bosses.
        out = [row[:] for row in px]
        for y in range(H):
            for x in range(W):
                if px[y][x] != '.':
                    continue
                for ddy, ddx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = y + ddy, x + ddx
                    if 0 <= yy < H and 0 <= xx < W and px[yy][xx] not in ('.', 'k'):
                        out[y][x] = 'k'
                        break
        return ["".join(r) for r in out]

    cells = [make(ph, pose) for ph in PHASES for pose in POSES]
    # depth=2 and whole-numbered rates, the Tide Maw's setting and for its
    # reason: this animal is one very large flat mass, and a fractional ramp
    # level is drawn as a dither, which puts a checkerboard across half of a
    # 26 px abdomen.
    sheet("boss_brood_queen",
          lit(cells, QUEEN, depth=2, rate=1.0, lit=1.0, dark=1.0), 48, 48,
          selout=True)
    print("boss_brood_queen.png  %d frames" % len(cells))


def build_boss_obsidian_heart():
    """THE OBSIDIAN HEART — 48x48, six frames per fight phase, nest_5.

    The final boss of the game, and the only one that is not an animal: a heart
    of black volcanic glass the size of a bull, ember-lit from the inside,
    walking the floor of the nest on four stubby glass roots. It is drawn
    **facing right** — the cleft between its lobes leans right, the roots step
    right — which is the sheet convention `Enemy._update_anim()` assumes
    (`flip_h` when `facing < 0`).

    Frame order is the contract with data/enemies/obsidian_heart.json, which
    names the six poses `<pose>_p1/_p2/_p3`, and src/enemies/obsidian_heart.gd
    picks the suffix for the phase it is in:

        0 idle   1-2 the walk   3 windup   4 the leap   5 the slam

    **The glass is the phase.** The other four bosses change silhouette between
    phases; this one changes how much of itself is still opaque. SEALED is a
    closed stone with two cold seams and a coal somewhere behind it. INVERTED
    has split along those seams — gold light in the cracks, the cleft gaping,
    three shards knocked loose and riding beside it. MOLTEN has lost the fight
    to keep itself shut: the core is a hole of ember light, the cracks run to
    the rim, and the shell survives only as a rind around the outside.

    That is the sheet's whole job. The mechanic underneath it is the arena
    reconfiguring, which is made of tiles and cannot be drawn here — so what the
    sprite has to carry is the reason the room keeps changing, and a stone
    coming apart from the inside is that reason in one frame.

    The 40x46 collision box sits at (4, 2) in the frame, which is the Brood
    Queen's box and is measured rather than chosen, for the same reason: a body
    standing on nest_5's one-way shelf has its chest at y=383..395, and a 46 px
    body standing on the arena floor spans y=386..432, so the blade reaches it
    from a shelf AND its body reaches a body standing on one. A refuge that is
    safe from the boss forever is a corner to camp in.
    """
    import math

    W = H = 48
    ## The heart itself, measured once. Two lobes and a point; everything else
    ## hangs off these three numbers. Drawn to span rows 2..45 of the frame,
    ## because a 34 px animal inside a 46 px hurtbox is the Grove Warden's
    ## recorded mistake and this is the last boss in the game to repeat it.
    CX = 23.5
    LOBE_Y, LOBE_R, LOBE_DX = 16.0, 10.6, 8.2
    POINT_Y = 45.0

    # shell   the opaque glass
    # seam    the colour of a closed crack
    # crack   the colour of an open one
    # core    what is burning behind it
    # rim     the character that carries the rim light on the crown
    # gape    how far the cleft between the lobes is forced open, in px
    # core_r  the radius of the burning core
    # crack_n how many cracks run out of the core
    # crack_w how wide each one is, in pixels: the phase's silhouette change
    # shards  loose pieces riding beside it
    PHASES = [
        dict(name="SEALED", shell='g', seam='G', crack='h', core='o',
             rim='h', gape=1.0, core_r=3.8, crack_n=3, crack_w=1, shards=0),
        dict(name="INVERTED", shell='G', seam='h', crack='y', core='r',
             rim='w', gape=3.0, core_r=5.6, crack_n=5, crack_w=2, shards=3),
        dict(name="MOLTEN", shell='g', seam='y', crack='R', core='y',
             rim='w', gape=5.2, core_r=6.6, crack_n=7, crack_w=3, shards=5),
    ]
    # dy      how far the whole body sits off its resting height
    # squash  + is squat and wide, - is stretched and narrow
    # lean    how far the crown is thrown forward (+ is toward the facing)
    # roots   the leg phase, -1 / 0 / +1
    # flare   how much the core is overdriven for THIS pose. The three attack
    #         poses are the flared ones, which is the telegraph: this boss
    #         brightens before it hits you and the nest changes with it.
    # dust    flung glass chips under it
    POSES = [
        dict(dy=0, squash=0.0, lean=0.0, roots=0, flare=0.0, dust=0),   # idle
        dict(dy=-1, squash=-0.4, lean=0.6, roots=-1, flare=0.0, dust=0),  # walk A
        dict(dy=0, squash=0.5, lean=-0.4, roots=1, flare=0.0, dust=1),   # walk B
        dict(dy=-2, squash=1.6, lean=-1.8, roots=0, flare=1.0, dust=3),  # windup
        dict(dy=-4, squash=-1.8, lean=2.4, roots=1, flare=1.5, dust=5),  # leap
        dict(dy=2, squash=2.4, lean=0.8, roots=-1, flare=2.0, dust=8),   # slam
    ]

    def make(ph, pose):
        px = [['.'] * W for _ in range(H)]

        def put(x, y, c):
            x, y = int(round(x)), int(round(y))
            if 0 <= x < W and 0 <= y < H:
                px[y][x] = c

        def at(x, y):
            x, y = int(round(x)), int(round(y))
            if 0 <= x < W and 0 <= y < H:
                return px[y][x]
            return None

        dy = pose["dy"]
        sq = pose["squash"]
        lean = pose["lean"]
        # Squash is volume-preserving, near enough: wider by as much as it is
        # shorter, so a slam reads as weight landing and not as a smaller boss.
        rx = LOBE_R + sq * 0.55
        ry = LOBE_R - sq * 0.55
        top = LOBE_Y + dy
        bottom = POINT_Y + dy + sq * 0.8
        gape = ph["gape"]

        def inside(x, y):
            """The heart, as one implicit shape.

            Two lobes and the wedge under them, with `lean` shearing the whole
            thing toward the facing as it rises — which is what makes the
            windup read as a body gathering rather than a stone sliding.
            """
            shear = lean * (bottom - y) / max(1.0, bottom - (top - ry))
            xs = x - shear
            hit = False
            for sgn in (-1.0, 1.0):
                lcx = CX + sgn * (LOBE_DX + gape * 0.5)
                if ((xs - lcx) / rx) ** 2 + ((y - top) / ry) ** 2 <= 1.0:
                    hit = True
            # The wedge: full width at the lobes' waist, tapering to the point.
            wy0 = top
            if not hit and wy0 <= y <= bottom:
                t = (y - wy0) / max(1.0, bottom - wy0)
                half = (LOBE_DX + gape * 0.5 + rx) * (1.0 - t * t)
                if abs(xs - CX) <= half:
                    hit = True
            if not hit:
                return False
            # And the CLEFT cut back out of the crown: a V between the lobes,
            # widening with the phase. Without it the two lobes merge into one
            # dome and the thing reads as an egg — and the cleft is also the
            # line the seams run down and the line the glass splits along, so
            # it has to be a hole in the silhouette and not a drawn mark.
            notch_top = top - ry
            notch_bot = top + 1.5 + gape
            if notch_top <= y <= notch_bot:
                t = (y - notch_top) / max(1.0, notch_bot - notch_top)
                if abs(xs - CX) <= (2.2 + gape) * (1.0 - t * t):
                    return False
            return True

        # ---- the shell -------------------------------------------------
        for y in range(H):
            for x in range(W):
                if inside(x, y):
                    put(x, y, ph["shell"])

        # ---- the roots. Four stubby glass feet, two near and two far, so the
        # walk beats read at a glance and the body does not float.
        root_y = bottom - 1
        for i, ox in enumerate((-9.0, -3.0, 3.0, 9.0)):
            step = pose["roots"] * (1 if i % 2 == 0 else -1)
            for j in range(3):
                put(CX + ox + step * 0.6, root_y + j, ph["shell"])
                put(CX + ox + step * 0.6 + 1, root_y + j, ph["seam"])

        # ---- the crown rim. The lit edge of a glass body is the only thing
        # that says "glass" rather than "rock", so it is drawn and not left to
        # auto_shade.
        for sgn in (-1.0, 1.0):
            lcx = CX + sgn * (LOBE_DX + gape * 0.5)
            for a in range(-160, 20, 6):
                th = math.radians(a)
                x = lcx + math.cos(th) * (rx - 0.6) + lean * 0.8
                y = top + math.sin(th) * (ry - 0.6)
                if at(x, y) is not None and at(x, y) != '.':
                    put(x, y, ph["rim"])

        # ---- the core --------------------------------------------------
        # A hole of fire behind the glass. Its rim is deliberately jagged
        # rather than circular: a clean circle in the middle of a heart reads
        # as a clock face, which is what the first cut of this sheet drew.
        core_y = top + ry * 0.55
        cr = ph["core_r"] + pose["flare"]
        for y in range(H):
            for x in range(W):
                if px[y][x] == '.':
                    continue
                ddx, ddy = x - CX, y - core_y
                th = math.atan2(ddy, ddx)
                jag = 1.0 + 0.17 * math.sin(th * 5.0 + 1.3) + 0.10 * math.sin(th * 9.0)
                d = math.hypot(ddx, ddy) / max(1.0, cr * jag)
                if d <= 1.0:
                    put(x, y, ph["core"])
                elif d <= 1.0 + 2.0 / max(1.0, cr):
                    put(x, y, ph["crack"])

        # A RIND of unbroken glass around the outside, which nothing burning
        # may cross. Without it the widest phase's cracks reach the outline and
        # the heart stops reading as a heart: measured, MOLTEN at crack_w 3 and
        # nine cracks was a gold splat with a purple fringe. This is the one
        # rule that keeps the boss obsidian in the phase where it is losing.
        RIND = 3
        rind = [[False] * W for _ in range(H)]
        for y in range(H):
            for x in range(W):
                if px[y][x] == '.':
                    continue
                for ddy in range(-RIND, RIND + 1):
                    for ddx in range(-RIND, RIND + 1):
                        if at(x + ddx, y + ddy) in (None, '.'):
                            rind[y][x] = True
                            break
                    if rind[y][x]:
                        break

        # ---- the cracks. Radial, out of the core, `crack_n` of them, at fixed
        # angles so the sheet is reproducible: nothing in this file may be
        # random, because tools/gen_art.py has to be byte-identical run to run.
        #
        # They are drawn `crack_w` pixels wide, and that is the phase's whole
        # silhouette change. A one-pixel crack in a 40 px stone is a scratch;
        # three pixels of ember light running to the rim is a stone losing. The
        # shell is never filled in wholesale — an all-gold heart stopped being
        # obsidian, which is the one thing this boss is named for.
        for i in range(ph["crack_n"]):
            th = math.radians(-90.0 + (360.0 / max(1, ph["crack_n"])) * i + 18.0)
            nx, ny = math.cos(th), math.sin(th)
            length = cr + 6.0 + ph["crack_w"] * 2.0
            wob = 0.0
            for s in range(int(cr), int(length)):
                wob += 0.40 * math.sin(s * 0.9 + i * 2.1)
                x = CX + nx * s + wob
                y = core_y + ny * s
                if at(x, y) in (None, '.'):
                    break
                # Across the crack, not along it: the perpendicular is what
                # gives it width without turning it into a wedge.
                for k in range(ph["crack_w"]):
                    off = k - (ph["crack_w"] - 1) * 0.5
                    cx2, cy2 = x - ny * off, y + nx * off
                    ix, iy = int(round(cx2)), int(round(cy2))
                    if at(cx2, cy2) in (None, '.'):
                        continue
                    if 0 <= ix < W and 0 <= iy < H and rind[iy][ix]:
                        continue
                    # Hot in the middle, cooling at the lips, so a wide crack
                    # reads as depth rather than as a painted stripe.
                    hot = abs(off) < 0.6 and s < length - 3
                    put(cx2, cy2, ph["core"] if hot else ph["crack"])

        # ---- the seams. Two cold lines down the cleft, always, in every phase:
        # they are what INVERTED and MOLTEN are splitting ALONG, so they have to
        # be visible while they are still shut.
        for j in range(int(top - ry * 0.2), int(bottom - 2)):
            t = (j - (top - ry * 0.2)) / max(1.0, bottom - 2 - (top - ry * 0.2))
            for sgn in (-1.0, 1.0):
                x = CX + sgn * (1.6 + gape * 0.5) * (1.0 - t * 0.7)
                if at(x, j) not in (None, '.'):
                    put(x, j, ph["seam"])

        # ---- loose shards, riding beside it once the shell has opened.
        for i in range(ph["shards"]):
            th = math.radians(-118.0 + 236.0 * (i / max(1, ph["shards"] - 1) if ph["shards"] > 1 else 0.5))
            r = rx + 6.0 + (i % 2) * 3.0
            sx = CX + math.cos(th) * r + lean
            sy = core_y + math.sin(th) * r * 0.82
            # A shard, not a dot: a three-pixel wedge with a lit lip, so a
            # piece of the boss that has come off reads as broken glass.
            put(sx, sy, ph["shell"])
            put(sx + 1, sy, ph["shell"])
            put(sx, sy + 1, ph["shell"])
            put(sx + 1, sy - 1, ph["seam"])
            put(sx - 1, sy + 1, ph["crack"])

        # ---- flung chips, under it, on the poses that land.
        for i in range(pose["dust"]):
            x = CX - 15.0 + i * 4.3
            y = bottom - 1 + (i % 2)
            if at(x, y) in (None, '.'):
                put(x, y, ph["seam"])

        # ---- ink outline, the last pass, exactly as the other four bosses.
        out = [row[:] for row in px]
        for y in range(H):
            for x in range(W):
                if px[y][x] != '.':
                    continue
                for ddy, ddx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = y + ddy, x + ddx
                    if 0 <= yy < H and 0 <= xx < W and px[yy][xx] not in ('.', 'k'):
                        out[y][x] = 'k'
                        break
        return ["".join(r) for r in out]

    cells = [make(ph, pose) for ph in PHASES for pose in POSES]
    # depth=2 and whole-numbered rates, THE TIDE MAW's setting and the Brood
    # Queen's, for their reason: this is one very large flat mass, and a
    # fractional ramp level is drawn as a dither, which puts a checkerboard
    # across half of a 40 px stone.
    sheet("boss_obsidian_heart",
          lit(cells, OBSIDIAN, depth=2, rate=1.0, lit=1.0, dark=1.0), 48, 48,
          selout=True)
    print("boss_obsidian_heart.png  %d frames" % len(cells))
