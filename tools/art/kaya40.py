"""Kaya at 40 px: a posable puppet instead of hand-drawn grids.

The old Kaya is 16x24 and every one of her 39 frames is a hand-written grid.
At 40 px that stops scaling, and worse, it stops being consistent: a hat brim
drawn by hand in frame 3 and again in frame 30 will not be the same brim. So
she is built from parts -- head, hair, hat, torso, shorts, two arms, two legs
-- positioned by joint angles, rasterised into the same character-grid format
the rest of tools/art uses, and then lit by `auto_shade` and outlined by the
sheet's selective outline like every other sprite. A pose is data; a new
animation is a list of angles, not a new drawing.

Design cues, not copied pixels: wide straw hat with a ribbon, long dark wavy
hair, green crop top, yellow fringed shorts, a bead necklace, green ankle
bands, red sandals. About 5.5 heads tall -- at 40 px a 7-head figure would get
a five-pixel face, too small to read on a phone.

The cell is 32x40 and her feet sit on row 39, centred on column 16, so the
unchanged 10x22 hitbox sits at her feet (data/forms/human.json: ox 11, oy 18).
The sprite is deliberately taller than the hitbox; the stoop frames are what
she is drawn as under a ceiling lower than that, and src/player/kaya_pose.gd
decides when. tools/clipgate.sh proves the decision against every proof tape.

`frames()` is the sheet, in the order data/forms/human.json indexes it.
"""

import math

from PIL import Image

from . import palette

W, H = 32, 40
FOOT_Y = 39.0
CX = 16.0

# Every stoop and swim frame must fit in two tiles, with a pixel to spare:
# opaque rows 9..39. The spare pixel is for rounding -- the physics position is
# a float and the sprite is drawn at it rounded, so a body resting 0.9 px off
# the floor of a 32 px tunnel is drawn a pixel high (measured: ruins_4, frame
# 1139). Asserted in frames(); tools/clipgate.sh measures it against real rock.
STOOP_TOP = H - 31

# char -> (ramp, base level). Upper case is the far side of the body, one to
# two steps down, so a limb behind her reads as behind her.
MAT = {
    's': ("skin", 2.9), 'S': ("skin", 1.9),
    'h': ("hair", 2.6), 'H': ("hair", 1.5),
    'a': ("straw", 3.6), 'A': ("straw", 2.4),
    'n': ("dirt", 1.8),                 # hat ribbon
    't': ("cloth", 3.1), 'T': ("cloth", 2.1),
    'y': ("gold", 5.0), 'Y': ("gold", 3.9),
    'b': ("ember", 4.8),                # beads
    'o': ("gold", 5.2),                 # earring
    'g': ("cloth", 2.6), 'G': ("cloth", 1.6),
    'r': ("ember", 3.0), 'R': ("ember", 2.0),
    'w': ("metal", 6.0),
    'e': ("hair", 1.6),                 # iris
    'l': ("ember", 3.9),                # lips
    'c': ("skin", 4.6),                 # cheek light
}


class Canvas:
    def __init__(self):
        self.g = [['.'] * W for _ in range(H)]

    def _set(self, x, y, ch):
        if 0 <= x < W and 0 <= y < H:
            self.g[y][x] = ch

    def capsule(self, a, b, r0, ch, r1=None):
        """A limb: every pixel whose centre lies within the (tapering) radius."""
        r1 = r0 if r1 is None else r1
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy or 1e-9
        rr = max(r0, r1)
        for y in range(int(min(ay, by) - rr - 1), int(max(ay, by) + rr + 2)):
            for x in range(int(min(ax, bx) - rr - 1), int(max(ax, bx) + rr + 2)):
                px, py = x + 0.5, y + 0.5
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
                qx, qy = ax + t * dx, ay + t * dy
                r = r0 + (r1 - r0) * t
                if (px - qx) ** 2 + (py - qy) ** 2 <= r * r:
                    self._set(x, y, ch)

    def ellipse(self, c, rx, ry, ch, clip=None):
        cx, cy = c
        for y in range(int(cy - ry - 1), int(cy + ry + 2)):
            for x in range(int(cx - rx - 1), int(cx + rx + 2)):
                px, py = x + 0.5, y + 0.5
                if ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 <= 1.0:
                    if clip is None or clip(px, py):
                        self._set(x, y, ch)

    def px(self, x, y, ch):
        self._set(int(math.floor(x)), int(math.floor(y)), ch)

    def outline(self):
        """One-pixel ink around the whole silhouette; selout softens it later."""
        out = [row[:] for row in self.g]
        for y in range(H):
            for x in range(W):
                if self.g[y][x] != '.':
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H and self.g[ny][nx] not in '.k':
                        out[y][x] = 'k'
                        break
        self.g = out

    def rows(self):
        return ["".join(r) for r in self.g]


def _limb(c, root, a1, l1, a2, l2, r1, r2, ch, rim=None):
    """Two-segment limb from `root`; angles in degrees from straight down,
    positive swings the far end forward (+x, the way she faces). `rim` draws a
    one-pixel shadow band first so a limb in front of skin still separates."""
    k = (root[0] + math.sin(math.radians(a1)) * l1,
         root[1] + math.cos(math.radians(a1)) * l1)
    e = (k[0] + math.sin(math.radians(a1 + a2)) * l2,
         k[1] + math.cos(math.radians(a1 + a2)) * l2)
    if rim:
        c.capsule(root, k, r1 + 0.55, rim, r1 * 0.9 + 0.55)
        c.capsule(k, e, r1 * 0.9 + 0.55, rim, r2 + 0.55)
    c.capsule(root, k, r1, ch, r1 * 0.9)
    c.capsule(k, e, r1 * 0.9, ch, r2)
    c.ellipse(e, r2 + 0.35, r2 + 0.35, ch)          # hand
    return k, e


HAT_RIDE = 1.0             # px the hat sits above where the head would put it

THIGH, SHIN = 7.5, 7.6      # hip to sole is ~15 px; longer bones buckle the knee
# Within this much of full reach a leg is drawn dead straight instead of being
# solved: a standing knee bent by a pixel reads as a tired, sagging stance, and
# that was one of the four things the phase-0 puppet was marked down for.
STRAIGHT_SLACK = 1.1


def _leg(c, hip, foot, ch, rim=None, bend=1):
    """Two-bone IK. The knee bends toward `bend` (+1 forward / -1 back, or
    outward in the front view), and the foot lands where told."""
    dx, dy = foot[0] - hip[0], foot[1] - hip[1]
    reach = math.hypot(dx, dy)
    if reach >= THIGH + SHIN - STRAIGHT_SLACK:
        u = (dx / max(reach, 1e-6), dy / max(reach, 1e-6))
        knee = (hip[0] + u[0] * reach * THIGH / (THIGH + SHIN),
                hip[1] + u[1] * reach * THIGH / (THIGH + SHIN))
        ankle = (hip[0] + u[0] * min(reach, THIGH + SHIN),
                 hip[1] + u[1] * min(reach, THIGH + SHIN))
    else:
        a = math.atan2(dy, dx)
        cos_k = (THIGH ** 2 + reach ** 2 - SHIN ** 2) / (2 * THIGH * max(reach, 1e-6))
        sgn = 1.0 if bend >= 0 else -1.0
        k_ang = a - sgn * math.acos(max(-1.0, min(1.0, cos_k)))
        knee = (hip[0] + math.cos(k_ang) * THIGH, hip[1] + math.sin(k_ang) * THIGH)
        if abs(bend) < 1.0:
            # Foreshortened: a knee bending toward the camera moves sideways
            # only a fraction of what it would in profile, and the thigh looks
            # shorter rather than splayed. Lerp toward the straight line.
            t = THIGH / (THIGH + SHIN)
            line = (hip[0] + dx * t, hip[1] + dy * t)
            knee = (line[0] + (knee[0] - line[0]) * abs(bend),
                    line[1] + (knee[1] - line[1]) * abs(bend))
        ankle = foot
    if rim:
        c.capsule(hip, knee, 2.95, rim, 2.4)
        c.capsule(knee, ankle, 2.4, rim, 1.9)
    c.capsule(hip, knee, 2.3, ch, 1.75)
    c.capsule(knee, ankle, 1.75, ch, 1.25)
    return ankle


def _foot(c, ankle, near, lift_toe=0.0, point=0.0):
    """Ankle band and sandal. `point` > 0 points the toe down (airborne)."""
    band = 'g' if near else 'G'
    sole = 'r' if near else 'R'
    c.capsule((ankle[0] - 0.2, ankle[1] - 2.0), (ankle[0], ankle[1] - 0.9), 1.55, band)
    tx = ankle[0] + 3.0 * math.cos(math.radians(point * 60))
    ty = ankle[1] + 0.3 - lift_toe + 3.0 * math.sin(math.radians(point * 60))
    c.capsule(ankle, (tx, ty), 1.05, sole)


def _brim(c, cx, cy, rx, tilt, ch_top='a', ch_under='A'):
    """A wide brim seen slightly from above: a lit top face over a dark underside,
    tilted by `tilt` pixels across its half-width."""
    for x in range(int(cx - rx - 1), int(cx + rx + 2)):
        u = (x + 0.5 - cx) / rx
        if abs(u) > 1.0:
            continue
        depth = 1.9 * math.sqrt(1 - u * u)           # thicker in the middle
        yc = cy - tilt * u
        for y in range(int(yc - depth), int(yc + depth) + 1):
            if abs(y + 0.5 - yc) <= depth:
                c._set(x, y, ch_top if y + 0.5 < yc + 0.3 else ch_under)


def _hat(c, hx, hy, tilt, sway=0.0, back=False, rx=10.4, lift=0.0):
    hy = hy - lift
    c.ellipse((hx - 0.2, hy - 4.6), 3.8, 2.7, 'a', clip=lambda x, y: y < hy - 3.1)
    c.capsule((hx - 3.7, hy - 3.6), (hx + 3.5, hy - 3.6), 0.65, 'n')     # ribbon band
    _brim(c, hx, hy - 2.7, rx, tilt)
    if back:
        c.capsule((hx + 0.4, hy - 3.4), (hx - 1.8 - sway, hy + 1.6), 0.7, 'n')
        c.capsule((hx + 1.0, hy - 3.4), (hx + 2.6, hy + 1.0), 0.7, 'n')


def _face_side(c, hx, hy, eyes=True):
    """Profile face, looking right. At this size every pixel is a feature, so
    each one is placed rather than drawn: a lidded eye -- white, black pupil,
    the lid line over both and a lash flicking forward off it -- the nose
    breaking the outline with a nostril shadow under it, a lit cheek, two
    pixels of mouth and the hoop earring. The phase-0 face was the same idea
    with the brow and lash hidden under the brim and a one-pixel mouth."""
    if eyes:
        c.px(hx + 1.0, hy - 0.4, 'k')
        c.px(hx + 2.0, hy - 0.4, 'k')                               # lid line
        c.px(hx + 3.0, hy - 0.9, 'k')                               # lash flick
        c.px(hx + 1.0, hy + 0.6, 'w')
        c.px(hx + 2.0, hy + 0.6, 'k')                               # pupil
    else:
        c.px(hx + 1.0, hy + 0.4, 'k')
        c.px(hx + 2.0, hy + 0.4, 'k')                               # shut
    c.px(hx + 1.4, hy - 1.8, 'h')
    c.px(hx + 2.4, hy - 1.8, 'h')                                   # brow
    c.px(hx + 3.9, hy + 0.9, 's')                                   # nose
    c.px(hx + 3.0, hy + 1.6, 'S')                                   # nostril shadow
    c.px(hx + 1.2, hy + 1.8, 'c')                                   # cheek
    c.px(hx + 1.9, hy + 2.7, 'l')
    c.px(hx + 2.8, hy + 2.7, 'l')                                   # lips
    c.px(hx - 0.6, hy + 1.6, 'o')                                   # hoop


def _slung_hat(c, sh, hx, hy):
    """The hat pushed off and hanging down her back on its cord, seen edge-on:
    a sliver of straw behind the shoulders, the crown a bump on it, and the cord
    across her throat. This is how she is drawn where the brim cannot fit -- a
    shaft one tile wide is 16 px and the brim on her head is 21."""
    bx = sh[0] - 4.0
    c.ellipse((bx, sh[1] + 3.6), 1.5, 8.0, 'A')
    c.ellipse((bx + 0.8, sh[1] + 3.6), 1.1, 3.2, 'a')
    c.capsule((hx + 0.6, hy + 3.2), (bx + 0.6, sh[1] - 1.4), 0.45, 'n')


# --------------------------------------------------------------- side view
def side(p):
    """Profile facing right. `p` is a pose dict; missing keys take the stand."""
    q = dict(STAND)
    q.update(p)
    c = Canvas()
    hip = (CX + q["hip_dx"], 23.0 + q["bob"])
    sh = (hip[0] + q["lean"], hip[1] - 9.4 * q["torso"])
    # The head sits a pixel lower than the phase-0 puppet's and the hat does
    # not move with it: under a 21 px brim the face had six rows, and the brow
    # and lashes were drawn underneath the straw. HAT_RIDE keeps the hat where
    # the approved silhouette had it.
    hx, hy = sh[0] + 1.2 + q["head_dx"], sh[1] - 5.6 + HAT_RIDE + q["head_dy"]
    sway, wave = q["sway"], q["wave"]
    fn = (hip[0] + q["near_fx"], FOOT_Y - 0.8 - q["near_lift"])
    ff = (hip[0] + q["far_fx"], FOOT_Y - 0.8 - q["far_lift"])

    # far arm and far leg, behind everything
    _limb(c, (sh[0] - 0.6, sh[1] + 0.9), q["far_sh"], 6.0, q["far_el"], 5.6, 1.4, 1.1, 'S')
    _foot(c, _leg(c, (hip[0] - 0.6, hip[1]), ff, 'S', bend=q["far_bend"]),
          False, q["far_toe"], q["far_point"])

    # hair down the back: a heavy wavy mass, swinging with `sway`, lifting
    # off the shoulders with `float` (falling, swimming)
    hair_len = q["hair_len"]
    for i in range(12):
        t = i / 11.0
        y = hy - 1.0 + t * hair_len - t * t * q["float"]
        x = hx - 2.6 - t * (2.2 + sway) + math.sin(t * 5.5 + wave) * 0.9
        c.ellipse((x, y), 3.9 - t * 1.7, 2.1, 'H')

    # near leg, rimmed so it separates from the far one; drawn before the
    # shorts so the hem covers the top of both thighs
    _foot(c, _leg(c, (hip[0] + 0.8, hip[1] + 0.6), fn, 's', rim='S', bend=q["near_bend"]),
          True, q["near_toe"], q["near_point"])

    # torso: bare midriff between the crop top and the shorts
    c.capsule((sh[0], sh[1] + 2.5), hip, 2.2, 's', 2.6)
    c.ellipse((sh[0] + 0.9, sh[1] + 2.9), 3.3, 3.1, 't')          # crop top
    c.capsule((sh[0] - 0.3, sh[1] - 0.2), (sh[0] + 0.9, sh[1] + 1.2), 0.6, 't')  # strap
    c.capsule((sh[0] + 0.3, sh[1] - 2.0), (sh[0] + 0.7, sh[1] + 0.6), 1.25, 's')  # neck
    srx, sry = q["shorts_rx"], 3.1
    c.ellipse((hip[0] + 0.2 + q["shorts_dx"], hip[1] + 0.6), srx, sry,
              'Y' if q["shorts_shade"] else 'y')                     # shorts
    c.capsule((hip[0] - srx + 0.4, hip[1] - 1.8), (hip[0] + 3.8, hip[1] - 1.8), 0.55, 'Y')
    for fx in range(-4, 5):                                         # fringe
        if fx % 2 == 0 and fx > -srx:
            c.px(hip[0] + fx, hip[1] + 3.7, 'Y')

    c.ellipse((hip[0] + 0.8, hip[1] + 1.4), 3.0, 2.3, 'y')          # near shorts leg

    # head and face
    c.ellipse((hx, hy), 3.7, 4.1, 's')
    c.ellipse((hx - 1.4, hy - 1.2), 3.2, 3.2, 'h',
              clip=lambda x, y: x < hx + 0.3 or y < hy - 2.6)      # hair over crown
    c.capsule((hx - 3.0, hy - 1.0), (hx - 3.4 - sway * 0.3, hy + 5.0), 1.7, 'h')  # lock by the ear
    _face_side(c, hx, hy, eyes=q["eyes"])
    for i, bx in enumerate((-0.4, 0.8, 2.0, 3.0)):                  # beads
        c.px(sh[0] + bx, sh[1] + 0.2 + (0.6 if i in (1, 2) else 0), 'b')
    if q["hat"] == "slung":
        _slung_hat(c, sh, hx, hy)
    else:
        _hat(c, hx, hy, q["hat_tilt"], sway, lift=q["hat_lift"] + HAT_RIDE)

    # near arm last, over the torso
    _limb(c, (sh[0] - 0.9, sh[1] + 1.0), q["near_sh"], 6.0, q["near_el"], 5.6, 1.2, 1.0, 's', rim='S')

    c.outline()
    return c.rows()


STAND = dict(hat="head", bob=0.0, hip_dx=0.0, lean=0.4, torso=1.0, head_dx=0.0, head_dy=0.0,
             sway=0.0, wave=0.0, hat_tilt=0.0, hat_lift=0.0, float=0.0,
             hair_len=13.5, eyes=True, shorts_rx=4.2, shorts_dx=0.0, shorts_shade=False,
             near_fx=2.0, near_lift=0.0, near_toe=0.0, near_point=0.0, near_bend=1,
             far_fx=-1.6, far_lift=0.0, far_toe=0.0, far_point=0.0, far_bend=1,
             near_sh=-4, near_el=14, far_sh=6, far_el=12)

# Eight-frame run as foot targets: contact, down, pass, push, toe-off,
# recovery, high pass, reach. The far foot runs half a cycle behind.
_FX = [7.0, 3.5, 0.0, -4.0, -7.5, -4.0, 1.5, 5.5]
_FL = [0.3, 0.0, 0.0, 0.4, 2.2, 5.5, 5.5, 2.4]
_FT = [1.2, 0.0, 0.0, -0.6, -1.4, 0.0, 0.6, 1.4]
_BOB = [1.2, 1.8, 0.6, 0.0, 1.2, 1.8, 0.6, 0.0]
# Arms pump against the legs, and the elbow is not a constant: a swing forward
# folds the forearm up to the chest, a swing back opens it out behind her. The
# phase-0 run held the elbow at 70 degrees on every frame, which is what read
# as stiff. Shoulder angle leads the opposite leg by one frame (`_ARM_LEAD`), so
# the arm is already on its way back when the foot plants.
_ARM_LEAD = 1


def _arm(i):
    fx = _FX[(i + _ARM_LEAD) % 8]
    sh = -fx * 6.0                                   # +-45 degrees
    fwd = max(0.0, sh) / 45.0
    el = 35 + 70 * fwd                               # 35 open .. 105 folded
    return sh, el


def run_pose(i):
    j = (i + 4) % 8
    ph = i / 8 * 2 * math.pi
    nsh, nel = _arm(i)
    fsh, fel = _arm(j)
    return dict(bob=_BOB[i], lean=1.8, sway=1.6 + 0.6 * math.sin(ph), wave=ph,
                hat_tilt=0.4 + 0.2 * math.sin(ph * 2), head_dy=_BOB[i] * -0.25,
                near_fx=_FX[i], near_lift=_FL[i], near_toe=_FT[i],
                far_fx=_FX[j], far_lift=_FL[j], far_toe=_FT[j],
                near_sh=nsh, near_el=nel, far_sh=fsh, far_el=fel)


def idle_pose(i):
    breath = (0.0, 1.0)[i % 2]
    return dict(bob=breath * 0.6, sway=breath * 0.5, wave=i * 0.9,
                hat_tilt=0.2 * breath, near_sh=-4 + breath * 2)


# Low ceiling. The whole silhouette must fit two tiles (32 px). The phase-0
# stoop dropped the hips six pixels behind folded knees, which pushed the
# shorts -- the brightest thing on her -- out behind her as the biggest shape on
# the sprite. This one is a duck rather than a squat: the hips stay over the
# feet, the knees take some of it, the back pitches forward and the head leads
# with the hat tipped down over it. The shorts are drawn narrower and in their
# shadow tone, because from this angle you see the underside of them.
STOOP = dict(bob=6.0, hip_dx=-0.6, lean=3.4, torso=0.8, head_dx=1.2, head_dy=1.6,
             hat_tilt=-1.2, sway=0.4, hair_len=11.0, shorts_rx=3.8, shorts_shade=True,
             near_fx=3.6, far_fx=-2.0, near_sh=28, near_el=30, far_sh=22, far_el=34)

# The stooped shuffle: short steps, small lifts, a low and level head.
_SFX = [3.6, 1.4, -1.0, -3.0, -1.4, 1.8]
_SFL = [0.0, 0.0, 0.0, 0.8, 2.2, 1.6]


def stoop_walk(i):
    j = (i + 3) % 6
    q = dict(STOOP)
    q.update(bob=STOOP["bob"] + (0.0, 0.4, 0.0, 0.0, 0.4, 0.0)[i], wave=i,
             near_fx=_SFX[i] + 0.6, near_lift=_SFL[i],
             far_fx=_SFX[j] - 0.8, far_lift=_SFL[j],
             near_sh=28 - _SFX[i] * 6, far_sh=22 - _SFX[j] * 6)
    return q


# -------------------------------------------------------- front and back
FRONT = dict(bob=0.0, hip_dx=0.0, back=False, hat_tilt=0.0, sway=0.0,
             l_sh=-7, l_el=-5, r_sh=-7, r_el=-5,      # outward, degrees from down
             l_fx=0.0, r_fx=0.0, l_lift=0.0, r_lift=0.0,
             eyes=True, smile=False)


def front(p=None, back=False):
    """Facing the camera (or, with back=True, facing away). Arms and legs take
    angles measured outward from straight down, so one table drives both."""
    q = dict(FRONT)
    q.update(p or {})
    back = back or q["back"]
    c = Canvas()
    hip_y, sh_y = 23.0 + q["bob"], 13.6 + q["bob"]
    cx = CX + q["hip_dx"]
    hx, hy = CX + q["hip_dx"] * 0.4, 8.0 + q["bob"]
    if not back:      # long hair falling behind the shoulders, visible either side
        c.capsule((hx - 3.8, hy), (hx - 4.6 - q["sway"], 20.0 + q["bob"]), 2.2, 'H', 1.6)
        c.capsule((hx + 3.8, hy), (hx + 4.6 - q["sway"], 20.0 + q["bob"]), 2.2, 'H', 1.6)
    for sx, near in ((-1, False), (1, True)):
        ch = 's' if near else 'S'
        fx = q["r_fx"] if sx > 0 else q["l_fx"]
        lift = q["r_lift"] if sx > 0 else q["l_lift"]
        a = _leg(c, (cx + 2.2 * sx, hip_y + 0.8),
                 (cx + 2.5 * sx + fx, FOOT_Y - 0.8 - lift), ch,
                 bend=sx * (0.9 if lift > 2.0 else 0.3))
        c.capsule((a[0], a[1] - 2.0), (a[0], a[1] - 0.9), 1.55, 'g' if near else 'G')
        c.capsule((a[0] - 0.8, a[1] + 0.2), (a[0] + 0.8, a[1] + 0.2), 1.05, 'r')
    c.capsule((cx, sh_y + 2.5), (cx, hip_y), 3.0, 's', 3.3)
    c.ellipse((cx, sh_y + 2.8), 4.4, 3.2, 't' if not back else 's')
    if back:
        c.capsule((cx - 4.0, sh_y + 3.0), (cx + 4.0, sh_y + 3.0), 1.4, 't')
    else:
        c.capsule((cx - 1.6, sh_y - 0.4), (cx - 1.2, sh_y + 1.0), 0.55, 't')
        c.capsule((cx + 1.6, sh_y - 0.4), (cx + 1.2, sh_y + 1.0), 0.55, 't')
    c.ellipse((cx, hip_y + 0.6), 4.9, 3.1, 'y')
    c.capsule((cx - 4.6, hip_y - 1.8), (cx + 4.6, hip_y - 1.8), 0.55, 'Y')
    for fx in range(-5, 6):
        if fx % 2 == 0:
            c.px(cx + fx, hip_y + 3.7, 'Y')
    c.capsule((hx, sh_y - 2.0), (cx, sh_y + 0.4), 1.3, 's')
    arms = ((-1, q["l_sh"], q["l_el"]), (1, q["r_sh"], q["r_el"]))
    if not back:
        for sx, a, e in arms:
            _limb(c, (cx + 4.4 * sx, sh_y + 1.0), a * sx, 6.0, e * sx, 5.6, 1.45, 1.15, 's')
    if back:
        c.ellipse((hx, hy), 3.9, 4.2, 'h')
        for i in range(10):                                         # hair down the back
            t = i / 9.0
            c.ellipse((hx + math.sin(t * 5) * 0.6 - q["sway"] * t, hy + 2 + t * 12),
                      4.6 - t * 1.4, 2.2, 'h')
    else:
        c.ellipse((hx, hy), 3.7, 4.1, 's')
        c.ellipse((hx, hy - 2.4), 3.9, 2.0, 'h', clip=lambda x, y: y < hy - 1.0)
        c.capsule((hx - 3.4, hy - 1.5), (hx - 3.6, hy + 4.0), 1.2, 'h')
        c.capsule((hx + 3.4, hy - 1.5), (hx + 3.6, hy + 4.0), 1.2, 'h')
        for ex in (-1.6, 1.0):
            if q["eyes"]:
                c.px(hx + ex, hy - 0.6, 'k')
                c.px(hx + ex + 0.9, hy - 0.6, 'k')                  # lid line
                c.px(hx + ex, hy + 0.4, 'w')
                c.px(hx + ex + 0.9, hy + 0.4, 'e')                  # iris
            else:
                c.px(hx + ex, hy + 0.2, 'k')
                c.px(hx + ex + 0.9, hy + 0.2, 'k')
        c.px(hx - 3.0, hy - 2.0, 'h')
        c.px(hx + 2.4, hy - 2.0, 'h')                               # brows
        c.px(hx - 2.0, hy + 1.6, 'c')
        c.px(hx + 2.1, hy + 1.6, 'c')                               # cheeks
        c.px(hx - 0.6, hy + 2.6, 'l')
        c.px(hx + 0.4, hy + 2.6, 'l')
        if q["smile"]:
            c.px(hx - 1.6, hy + 2.1, 'S')
            c.px(hx + 1.4, hy + 2.1, 'S')
        for bx in (-1.6, -0.5, 0.6, 1.7):
            c.px(cx + bx, sh_y + 0.3 + (0.5 if abs(bx) < 1 else 0), 'b')
        c.px(hx - 3.8, hy + 1.4, 'o')
        c.px(hx + 3.6, hy + 1.4, 'o')
    _hat(c, hx, hy, q["hat_tilt"], back=back)
    if back:   # seen from behind, the arms are in front of her and over the brim
        for sx, a, e in arms:
            _limb(c, (cx + 4.4 * sx, sh_y + 1.0), a * sx, 6.0, e * sx, 5.6, 1.45, 1.15,
                  's' if sx > 0 else 'S')
    c.outline()
    return c.rows()


# ------------------------------------------------------------- the sheet
def _jump():
    """10-15: anticipate, launch, rise, apex, fall, land. In the air the body
    gathers in from both ends -- knees up, head down -- which is what reads as
    a jump and also keeps the airborne silhouette short under a ceiling."""
    return [
        side(dict(bob=4.0, lean=2.6, torso=0.95, head_dy=0.6, near_fx=3.0, far_fx=-2.4,
                  near_sh=-40, near_el=30, far_sh=-30, far_el=34, sway=0.8)),
        side(dict(bob=-0.6, lean=1.4, near_fx=1.0, far_fx=-3.0, far_lift=2.0,
                  near_point=0.9, far_point=0.9, near_sh=120, near_el=20,
                  far_sh=95, far_el=30, float=1.5)),
        side(dict(bob=1.0, lean=1.2, near_fx=3.6, near_lift=6.0, far_fx=-2.4, far_lift=2.6,
                  far_point=0.8, near_sh=140, near_el=25, far_sh=110, far_el=30,
                  float=2.0)),
        side(dict(bob=2.4, lean=1.0, near_fx=3.0, near_lift=7.4, far_fx=-1.0, far_lift=6.0,
                  near_point=0.4, far_point=0.6, near_sh=80, near_el=50, far_sh=60,
                  far_el=60, float=3.5, sway=0.4, hat_lift=0.6)),
        side(dict(bob=1.4, lean=0.6, near_fx=3.2, near_lift=2.6, far_fx=-2.6, far_lift=4.4,
                  near_point=0.6, far_point=0.8, near_sh=125, near_el=35, far_sh=105,
                  far_el=40, float=5.0, hat_lift=1.0)),
        side(dict(bob=4.6, lean=2.2, torso=0.95, head_dy=0.8, near_fx=3.6, far_fx=-2.6,
                  near_sh=40, near_el=35, far_sh=30, far_el=40, sway=1.2)),
    ]


def _climb():
    """16-18: from behind, one hand reaching up the vine while the knee on the
    other side climbs; 17 is the hands-level pass between them."""
    return [
        front(dict(back=True, bob=1.0, l_sh=168, l_el=-12, r_sh=55, r_el=95,
                   r_lift=5.0, r_fx=-1.0)),
        front(dict(back=True, bob=1.6, l_sh=125, l_el=45, r_sh=125, r_el=45)),
        front(dict(back=True, bob=1.0, r_sh=168, r_el=-12, l_sh=55, l_el=95,
                   l_lift=5.0, l_fx=1.0, sway=0.6)),
    ]


def _swim():
    """Four strokes, body pitched forward, hair streaming out behind: reach,
    sweep, tuck and kick, glide. Low enough to fit two tiles, like the stoop:
    water channels are as often 32 px tall as tunnels are."""
    base = dict(bob=4.8, lean=6.8, torso=0.74, head_dx=0.8, head_dy=1.6, hat_tilt=-0.6,
                hair_len=9.0, float=4.0, sway=4.0, shorts_rx=3.8)
    strokes = [
        dict(near_sh=125, near_el=-5, far_sh=115, far_el=0, near_fx=-6.5, near_lift=4.0,
             far_fx=-8.5, far_lift=6.5, near_point=1.0, far_point=1.0, wave=0.0),
        dict(near_sh=75, near_el=25, far_sh=65, far_el=30, near_fx=-5.0, near_lift=6.5,
             far_fx=-7.0, far_lift=8.0, near_point=0.8, far_point=0.8, wave=1.6),
        dict(near_sh=35, near_el=95, far_sh=30, far_el=100, near_fx=-1.0, near_lift=8.0,
             far_fx=-3.5, far_lift=9.0, near_bend=-1, far_bend=-1, wave=3.2),
        dict(near_sh=95, near_el=40, far_sh=85, far_el=45, near_fx=-8.0, near_lift=5.0,
             far_fx=-9.0, far_lift=7.0, near_point=1.0, far_point=1.0, wave=4.8),
    ]
    out = []
    for s in strokes:
        q = dict(base)
        q.update(s)
        out.append(side(q))
    return out


def _dance():
    """31-38: weight right, dip, weight left, dip, the arm-wave hop, the spin
    (front, back) and the settle face-on."""
    return [
        side(dict(hip_dx=-1.2, lean=1.4, near_sh=150, near_el=30, far_sh=30, far_el=60,
                  near_fx=2.6, far_fx=-2.2, sway=-0.6, hat_tilt=0.6)),
        side(dict(bob=2.0, lean=1.0, near_sh=60, near_el=80, far_sh=50, far_el=80,
                  near_fx=2.8, far_fx=-2.4, sway=0.8)),
        side(dict(hip_dx=1.0, lean=-0.4, near_sh=30, near_el=60, far_sh=150, far_el=30,
                  near_fx=1.4, far_fx=-1.6, far_lift=1.0, sway=1.2, hat_tilt=-0.5)),
        side(dict(bob=2.0, lean=1.0, near_sh=70, near_el=70, far_sh=40, far_el=90,
                  near_fx=2.8, far_fx=-2.4, sway=0.4)),
        front(dict(bob=-0.6, l_sh=150, l_el=20, r_sh=150, r_el=20, l_lift=1.0, r_lift=1.0,
                   smile=True)),
        front(dict(hip_dx=1.0, l_sh=60, l_el=60, r_sh=100, r_el=30, r_lift=2.0,
                   sway=0.8, smile=True)),
        front(dict(back=True, hip_dx=-1.0, l_sh=100, l_el=30, r_sh=60, r_el=60,
                   l_lift=2.0, sway=-0.8)),
        front(dict(l_sh=20, l_el=40, r_sh=20, r_el=40, smile=True)),
    ]


# Narrow: the slung hat, and every limb kept inside 16 px. Opaque width is
# asserted in frames(), and the gate proves it against the shafts themselves.
NARROW = dict(hat="slung", hair_len=11.0, sway=-0.6, lean=0.6)
NARROW_W = 16


def _narrow():
    """50 stand, 51-53 climb (reach, pass, reach), 54 rise, 55 fall,
    56-57 swim, 58 crouch. Profile, hat on her back."""
    def n(**kw):
        q = dict(NARROW)
        q.update(kw)
        return side(q)
    return [
        n(near_sh=-2, near_el=10, far_sh=4, far_el=10, near_fx=1.2, far_fx=-1.0),
        n(near_sh=168, near_el=-8, near_fx=2.0, near_lift=4.5, near_toe=0.8,
          far_sh=125, far_el=45, far_fx=-0.6, far_bend=1),
        n(near_sh=140, near_el=30, far_sh=140, far_el=30, near_fx=1.2, near_lift=2.0,
          far_fx=0.0, far_lift=2.0, bob=0.6),
        n(far_sh=168, far_el=-8, far_fx=1.6, far_lift=4.5, near_sh=125, near_el=45,
          near_fx=-0.2),
        n(bob=1.6, near_fx=0.6, near_lift=3.6, far_fx=-1.0, far_lift=2.4, far_point=0.8,
          near_sh=172, near_el=4, far_sh=150, far_el=14, float=2.0),
        n(bob=1.0, near_fx=1.0, near_lift=2.0, far_fx=-1.4, far_lift=3.4,
          near_point=0.6, far_point=0.8, near_sh=158, near_el=18, far_sh=140,
          far_el=28, float=4.5, sway=-1.2),
        n(bob=1.4, near_fx=0.4, near_lift=3.0, far_fx=-1.2, far_lift=1.0,
          near_point=0.8, far_point=0.8, near_sh=150, near_el=20, far_sh=18,
          far_el=24, float=4.0, sway=-1.6),
        n(bob=1.4, near_fx=-0.8, near_lift=1.0, far_fx=0.4, far_lift=3.0,
          near_point=0.8, far_point=0.8, near_sh=18, near_el=24, far_sh=150,
          far_el=20, float=4.0, sway=-2.0, wave=1.5),
        # 58: low AND narrow -- the end of a two-tile tunnel, against its wall,
        # where the stoop's leading head and brim cannot fit. A crouch with the
        # hat slung, inside 16 x 31 px.
        n(bob=6.6, lean=1.6, torso=0.86, head_dx=0.2, head_dy=1.2, hair_len=9.0,
          near_fx=1.6, far_fx=-1.2, near_sh=14, near_el=40, far_sh=8, far_el=36,
          shorts_rx=3.6, shorts_shade=True),
    ]


def frames():
    """The sheet, in the order data/forms/human.json indexes it.

     0-1  idle               20-21 turn (plant, half-turn)   31-38 dance
     2-9  run                22    skid                      39    stoop
    10-15 jump arc           23-24 push                      40-45 stoop walk
    16-18 climb              25-26 throw                     46-49 swim
    19    hurt               27    catch                     50-58 narrow:
                             28-30 fidget                          slung hat
    """
    cells = [side(idle_pose(i)) for i in range(2)]
    cells += [side(run_pose(i)) for i in range(8)]
    cells += _jump()
    cells += _climb()
    cells.append(side(dict(lean=-1.8, head_dx=-1.0, head_dy=0.4, near_fx=4.6, far_fx=-3.0,
                           far_lift=3.0, near_sh=-70, near_el=-30, far_sh=-110, far_el=-20,
                           sway=-2.0, hat_lift=1.6, hat_tilt=1.2, eyes=False, float=2.0)))
    cells.append(side(dict(bob=3.2, lean=-0.8, near_fx=5.0, far_fx=-1.6, near_sh=-30,
                           near_el=40, far_sh=-20, far_el=40, sway=2.0)))   # turn: plant
    cells.append(front(dict(bob=1.0, l_sh=25, l_el=20, r_sh=25, r_el=20, sway=1.0)))
    cells.append(side(dict(bob=2.6, lean=-1.6, head_dx=-0.6, near_fx=7.0, near_toe=1.4,
                           far_fx=1.0, near_sh=-50, near_el=20, far_sh=-35, far_el=30,
                           sway=-1.4, hat_tilt=0.8)))                      # skid
    for b in (1.0, 2.0):                                                   # push
        cells.append(side(dict(bob=b, lean=5.2, torso=0.92, head_dx=0.6, head_dy=1.0,
                               near_fx=-1.0 - b, far_fx=-5.5 + b, far_lift=0.4 * b,
                               near_sh=82, near_el=8, far_sh=72, far_el=20, sway=1.0)))
    cells.append(side(dict(lean=-0.4, near_fx=1.0, far_fx=-3.0, near_sh=-150,
                           near_el=-40, far_sh=40, far_el=20, sway=0.6)))   # throw: wind
    cells.append(side(dict(lean=2.6, near_fx=4.0, far_fx=-3.0, near_sh=88, near_el=4,
                           far_sh=-30, far_el=20, sway=1.6)))               # throw: release
    cells.append(side(dict(lean=0.8, near_sh=118, near_el=28, far_sh=20, far_el=30)))  # catch
    cells.append(side(dict(near_sh=160, near_el=40, hat_tilt=0.8)))         # fidget: brim
    cells.append(side(dict(near_sh=150, near_el=50, hat_tilt=1.2, head_dy=0.4,
                           hat_lift=0.8)))                                  # fidget: tip
    cells.append(side(dict(near_sh=10, near_el=30, far_sh=10, far_el=20, sway=0.6)))
    cells += _dance()
    cells.append(side(STOOP))
    cells += [side(stoop_walk(i)) for i in range(6)]
    cells += _swim()
    cells += _narrow()
    assert len(cells) == FRAME_COUNT, len(cells)
    for i in NARROW_FRAMES:
        xs = [x for r in cells[i] for x, ch in enumerate(r) if ch != '.']
        assert max(xs) - min(xs) + 1 <= NARROW_W, "narrow frame %d is %d px wide" % (
            i, max(xs) - min(xs) + 1)
    for i in list(STOOP_FRAMES) + list(SWIM_FRAMES) + [58]:
        top = min(y for y, r in enumerate(cells[i]) if r.strip('.'))
        assert top >= STOOP_TOP, "frame %d starts on row %d, needs >= %d" % (
            i, top, STOOP_TOP)
    return cells


FRAME_COUNT = 59
STOOP_FRAMES = range(39, 46)
SWIM_FRAMES = range(46, 50)
NARROW_FRAMES = range(50, 59)


def cells():
    """Every frame lit and ready for `palette.sheet(..., selout=True)`."""
    return [palette.auto_shade(r, MAT, rate=0.45, lit=0.9, dark=0.8) for r in frames()]


def write_bounds(sheet_path):
    """Per frame, per row, the first and last opaque column of the SHIPPED sheet
    (after selout), as `assets/sprites/kaya_human.bounds.json`.

    src/player/kaya_pose.gd needs to know how far each drawn frame reaches past
    the hitbox, at each height, to keep it off a wall. An exported build has no
    PNG to read back -- only the imported texture -- so the generator that drew
    the pixels writes down where they are. A row with nothing in it is [-1, -1].
    """
    import json
    import os
    img = Image.open(sheet_path).convert("RGBA")
    n = img.width // W
    frames = []
    for f in range(n):
        rows = []
        for y in range(H):
            xs = [x for x in range(W) if img.getpixel((f * W + x, y))[3] > 0]
            rows.append([xs[0], xs[-1]] if xs else [-1, -1])
        frames.append(rows)
    out = {"_comment": "Generated by tools/art/kaya40.py from kaya_human.png. Do not edit.",
           "frame_w": W, "frame_h": H, "rows": frames}
    path = os.path.splitext(sheet_path)[0] + ".bounds.json"
    with open(path, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
        fh.write("\n")


def render(rows, scale=1):
    img = palette.auto_shade(rows, MAT, rate=0.45, lit=0.9, dark=0.8)
    palette.selective_outline(img)          # in place
    if scale != 1:
        img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    return img


def mirror(rows):
    return [r[::-1] for r in rows]
