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
def side(p, ink=True):
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

    if ink:
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


# ------------------------------------------------------------ the overworld
# The hub is a top-down map at the old 16 px scale, where a 40 px Kaya would
# stand taller than the huts. So she is drawn there from the SAME poses, the
# body scaled before it is inked: the material grid is point-sampled down
# about the feet, then given its one-pixel outline at the new size, so the
# line stays crisp instead of being a shrunken copy of a thicker one.
HUB_W, HUB_H = 24, 28
HUB_SCALE = 0.68


def _shrink(rows, scale=HUB_SCALE, w=HUB_W, h=HUB_H):
    c = Canvas()
    c.g = [['.'] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            sx = int((x + 0.5 - w * 0.5) / scale + CX)
            sy = int((y + 0.5 - h) / scale + FOOT_Y + 1.0)
            if 0 <= sx < W and 0 <= sy < H:
                c.g[y][x] = rows[sy][sx]
    # Canvas.outline() walks the module-wide W x H; this grid is smaller.
    out = [row[:] for row in c.g]
    for y in range(h):
        for x in range(w):
            if c.g[y][x] != '.':
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and c.g[ny][nx] not in '.k':
                    out[y][x] = 'k'
                    break
    return ["".join(r) for r in out]


def hub_frames():
    """Frame order the overworld reads (src/hub/hub_player.gd): 0 idle,
    1 breath, 2-9 the run cycle."""
    poses = [idle_pose(0), idle_pose(2)] + [run_pose(i) for i in range(8)]
    return [_shrink(side(p, ink=False)) for p in poses]


def hub_cells():
    return [palette.auto_shade(r, MAT, rate=0.45, lit=0.9, dark=0.8) for r in hub_frames()]


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


# ================================================================ HD (2x)
# docs/plan-hd.md, phase H0 look sample: Kaya drawn natively at two texels per
# world unit, in a 64x80 cell. Nothing above this line changes; nothing in the
# game reads what is below it yet (tools/art/hd_look.py does).
#
# The poses are the SAME dicts, solved by the same _limb/_leg in world units:
# `HDCanvas` takes 1x coordinates and rasterises them at HD_SCALE, so a run
# frame at 2x is the run frame at 1x, only sampled twice as finely. What is new
# is everything a 32x40 cell could not hold, drawn in native texels: a face
# with a lidded eye, iris and catch-light, brow, nose and lips; hair as strands
# with a sheen; a woven hat with a ribbon and trailing tails; a hem and creases
# on the top; tassels on the shorts; a thumb; wrapped ankle bands and crossed
# sandal straps; and hand anti-aliasing on the outline's stair-steps.

HD_SCALE = 2
HW, HH = W * HD_SCALE, H * HD_SCALE

# 1x materials plus the ones only 2x has room for.
MAT_HD = dict(MAT)
MAT_HD.update({
    'i': ("hair", 4.4), 'I': ("hair", 3.0),      # sheen (near / far hair)
    'j': ("hair", 1.2), 'J': ("hair", 0.4),      # strand grooves
    'v': ("straw", 2.3),                         # weave shadow
    'x': ("straw", 5.6),                         # sunlit brim lip
    'V': ("straw", 1.3),                         # deep underside
    'N': ("dirt", 3.6),                          # ribbon highlight
    'u': ("cloth", 4.6),                         # hem, lit
    'U': ("cloth", 1.4),                         # crease
    'q': ("gold", 2.9),                          # shorts crease / tassel shade
    'B': ("ember", 6.0),                         # bead catch-light
    'L': ("ember", 2.2),                         # mouth corner
    'E': ("hair", 0.2),                          # pupil
    'z': ("skin", 1.2),                          # nostril, lid crease
    'p': ("ember", 4.0),                         # sandal strap
})


class HDCanvas(Canvas):
    """A Canvas whose drawing calls take 1x coordinates. `t()` and `over()`
    work in native texels, for the details that only exist at this size."""

    def __init__(self, s=HD_SCALE):
        self.s = s
        self.w, self.h = W * s, H * s
        self.g = [['.'] * self.w for _ in range(self.h)]

    def _set(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = ch

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.g[y][x]
        return '.'

    def capsule(self, a, b, r0, ch, r1=None, only=None):
        s = self.s
        r1 = r0 if r1 is None else r1
        ax, ay, bx, by = a[0] * s, a[1] * s, b[0] * s, b[1] * s
        r0, r1 = r0 * s, r1 * s
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
                    if only is None or self.get(x, y) in only:
                        self._set(x, y, ch)

    def ellipse(self, c, rx, ry, ch, clip=None, only=None):
        s = self.s
        cx, cy, rx, ry = c[0] * s, c[1] * s, rx * s, ry * s
        for y in range(int(cy - ry - 1), int(cy + ry + 2)):
            for x in range(int(cx - rx - 1), int(cx + rx + 2)):
                px, py = x + 0.5, y + 0.5
                if ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 <= 1.0:
                    if clip is None or clip(px / s, py / s):
                        if only is None or self.get(x, y) in only:
                            self._set(x, y, ch)

    def px(self, x, y, ch):
        self._set(int(math.floor(x * self.s)), int(math.floor(y * self.s)), ch)

    def t(self, x, y, ch, only=None):
        """One native texel."""
        x, y = int(math.floor(x)), int(math.floor(y))
        if only is None or self.get(x, y) in only:
            self._set(x, y, ch)

    def stroke(self, pts, ch, only=None):
        """A one-texel line through native points (strands, creases, grain)."""
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
            for k in range(n + 1):
                u = k / max(n, 1)
                self.t(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, ch, only)

    def outline(self):
        out = [row[:] for row in self.g]
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] != '.':
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if self.get(x + dx, y + dy) not in '.k':
                        out[y][x] = 'k'
                        break
        # Weighted line: a second ink texel on the shadow side (right and
        # below, away from the light). A 1-texel line at 2x is half a world
        # unit, and against the 1x sprite she read as drawn in pencil; this
        # restores the 1x line's weight where the form turns away from the
        # light and keeps it fine where the light catches her.
        self.g = out
        out = [row[:] for row in self.g]
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] != '.':
                    continue
                for dx, dy in ((-1, 0), (0, -1)):
                    if (self.get(x + dx, y + dy) == 'k'
                            and self.get(x + 2 * dx, y + 2 * dy) not in '.k'):
                        out[y][x] = 'k'
                        break
        self.g = out


HAIR_ANY = 'hHij IJ'.replace(' ', '')


def _hair_strands(c, hx, hy, q):
    """The back mass as strands: grooves follow the same wave the mass was
    built on, offset across its width, and a sheen rides the upper-left of
    each lock. Drawn only over hair, so the silhouette is the 1x silhouette."""
    s = c.s
    hair_len, sway, wave = q["hair_len"], q["sway"], q["wave"]
    for lane, (off, ch) in enumerate(((-2.4, 'J'), (-0.9, 'J'), (0.7, 'J'),
                                      (-1.6, 'I'), (0.1, 'I'))):
        pts = []
        for i in range(25):
            t = i / 24.0
            y = hy - 0.6 + t * hair_len - t * t * q["float"]
            x = (hx - 2.6 - t * (2.2 + sway) + math.sin(t * 5.5 + wave) * 0.9
                 + off * (1.0 - 0.55 * t))
            if ch == 'I' and math.sin(t * 5.5 + wave) < -0.2:
                pts.append(None)                # sheen only on the bulge
                continue
            pts.append((x * s, y * s))
        run = []
        for p in pts + [None]:
            if p is None:
                if len(run) > 1:
                    c.stroke(run, ch, only='H')
                run = []
            else:
                run.append(p)


def _crown_strands(c, hx, hy):
    """Hair over the crown, combed back from a parting above the brow: a
    sheen arc and three grooves fanning toward the nape."""
    s = c.s
    X, Y = hx * s, hy * s
    for k, (dy, ch) in enumerate(((-4.6, 'i'), (-3.4, 'j'), (-1.6, 'j'), (0.4, 'j'))):
        pts = [(X + 1.5 - j * 1.6, Y + dy + j * (0.35 + 0.18 * k) + (j * j) * 0.05)
               for j in range(7)]
        c.stroke(pts, ch, only='h')
    c.stroke([(X - 1.0, Y - 5.5), (X - 4.0, Y - 4.2)], 'i', only='h')


def _face_hd(c, hx, hy, eyes=True):
    """Profile face in native texels, looking right. The 1x face spent one
    pixel per feature; here each is a small shape: an almond eye with a lid
    line, a lash flick, white, a two-texel iris with a pupil and catch-light;
    an arched brow; a nose that breaks the outline with a nostril; lips with
    a dark corner; a cheek; an ear with the hoop hanging from it."""
    s = c.s
    X, Y = int(math.floor(hx * s)), int(math.floor(hy * s))
    T = c.t
    if eyes:
        for dx in (2, 3, 4, 5):
            T(X + dx, Y - 1, 'k')                      # upper lid
        T(X + 6, Y - 2, 'k')                           # lash flick
        T(X + 2, Y, 'w')
        T(X + 3, Y, 'e')
        T(X + 4, Y, 'E')                               # iris + pupil
        T(X + 3, Y + 1, 'e')
        T(X + 4, Y + 1, 'e')
        T(X + 2, Y + 1, 'w')
        T(X + 5, Y, 'w')                               # catch-light / white
        T(X + 2, Y + 2, 'z')                           # lower lid crease
        T(X + 3, Y + 2, 'z')
    else:
        for dx in (2, 3, 4, 5):
            T(X + dx, Y + (1 if dx in (3, 4) else 0), 'k')
    for (dx, dy) in ((1, -3), (2, -4), (3, -4), (4, -4), (5, -3)):
        T(X + dx, Y + dy, 'h')                         # brow
    # The profile, texel by texel: the round head ellipse is flattened into
    # a face -- bridge, nose tip one texel proud, nostril, upper lip, the
    # mouth line, lower lip, chin.
    for (dx, dy, ch) in ((7, 0, 's'), (7, 1, 's'), (7, 2, 's'), (8, 2, 's'),
                         (7, 3, 's'), (6, 4, 'l'), (5, 4, 'l'), (6, 5, 'L'),
                         (5, 5, 'L'), (5, 6, 'l'), (6, 6, 's'), (5, 7, 's'),
                         (4, 7, 's'), (4, 8, 'S')):
        T(X + dx, Y + dy, ch)
    T(X + 6, Y + 3, 'z')                               # nostril
    c.stroke([(X - 1, Y + 8), (X + 3, Y + 9)], 'S', only='s')  # under the jaw
    T(X + 7, Y + 4, '.')                               # under the nose
    T(X + 3, Y + 3, 'c')
    T(X + 4, Y + 3, 'c')                               # cheek light
    T(X - 2, Y + 1, 'S')
    T(X - 1, Y + 1, 'S')
    T(X - 2, Y + 2, 'S')                               # ear
    T(X - 2, Y + 3, 'o')
    T(X - 3, Y + 4, 'o')
    T(X - 2, Y + 5, 'o')                               # hoop


def _brim_hd(c, cx, cy, rx, tilt):
    """The brim in native texels: a lit top face with the weave running round
    it in rings, a sunlit lip on the light side, a deep underside, and a
    frayed edge where a few straws stick out."""
    s = c.s
    CX_, CY_, RX = cx * s, cy * s, rx * s
    for x in range(int(CX_ - RX - 1), int(CX_ + RX + 2)):
        u = (x + 0.5 - CX_) / RX
        if abs(u) > 1.0:
            continue
        depth = 1.9 * s * math.sqrt(1 - u * u)
        yc = CY_ - tilt * s * u
        col = [y for y in range(int(yc - depth) - 1, int(yc + depth) + 2)
               if abs(y + 0.5 - yc) <= depth]
        for y in col:
            top = y + 0.5 < yc + 0.6
            if top:
                ch = 'a'
                # weave: rings across the face, stitched every third texel
                ring = (y + 0.5 - (yc - depth)) / max(2 * depth, 1e-6)
                if abs(ring - 0.35) < 0.08 and x % 3 != 0:
                    ch = 'v'
                elif x % 4 == (y % 2) * 2 and ring < 0.3:
                    ch = 'v'
            else:
                ch = 'V' if y == col[-1] else 'A'
            c._set(x, y, ch)
        if col:
            c._set(x, col[0], 'x' if u < 0.35 else 'a')        # lip
            if x % 7 == 3 and abs(u) > 0.7:                    # frayed straw
                c._set(x + (1 if u > 0 else -1), col[len(col) // 2], 'A')


def _hat_hd(c, hx, hy, tilt, sway=0.0, lift=0.0, rx=10.4, tails=True, knot=-3.0):
    """`tails=False` for the front view, where the ribbon hangs behind her;
    `knot` is where the bow sits along the band (1x units from the crown)."""
    s = c.s
    hy = hy - lift
    # Ribbon tails first, so the brim overlaps where they leave the band.
    if tails:
        c.capsule((hx - 3.2, hy - 3.2), (hx - 5.4 - sway * 0.9, hy + 1.6), 0.55, 'n', 0.45)
        c.capsule((hx - 2.6, hy - 3.2), (hx - 4.0 - sway * 0.6, hy + 2.6), 0.5, 'n', 0.4)
    c.ellipse((hx - 0.2, hy - 4.6), 3.8, 2.7, 'a', clip=lambda x, y: y < hy - 3.1)
    # crown weave: a diagonal over-under lattice
    for y in range(int((hy - 7.6) * s), int((hy - 3.1) * s) + 1):
        for x in range(int((hx - 4.2) * s), int((hx + 3.8) * s) + 1):
            if ((x + y) % 4 == 0) or ((x - y) % 4 == 0 and (x + y) % 2 == 0):
                c.t(x, y, 'v', only='a')
    c.capsule((hx - 3.7, hy - 3.6), (hx + 3.5, hy - 3.6), 0.65, 'n')     # band
    c.stroke([((hx - 3.3) * s, (hy - 4.1) * s), ((hx + 3.1) * s, (hy - 4.1) * s)],
             'N', only='n')
    c.ellipse((hx + knot, hy - 3.6), 0.85, 0.75, 'n')                   # knot
    _brim_hd(c, hx, hy - 2.7, rx, tilt)


def _foot_hd(c, ankle, near, lift_toe=0.0, point=0.0):
    """Wrapped ankle band (two turns of cord and a bead), a sandal with a
    sole, and two straps crossing the instep."""
    s = c.s
    band, sole = ('g', 'r') if near else ('G', 'R')
    c.capsule((ankle[0] - 0.2, ankle[1] - 2.1), (ankle[0], ankle[1] - 0.8), 1.55, band)
    ax, ay = ankle[0] * s, ankle[1] * s
    for k in (-3, -1):                                       # cord turns
        c.stroke([(ax - 3, ay + k + 1), (ax + 3, ay + k)], 'G' if near else 'U',
                 only=band)
    tx = ankle[0] + 3.0 * math.cos(math.radians(point * 60))
    ty = ankle[1] + 0.3 - lift_toe + 3.0 * math.sin(math.radians(point * 60))
    c.capsule(ankle, (tx, ty), 1.05, 's' if near else 'S')    # bare foot
    c.capsule((ankle[0] - 0.3, ankle[1] + 0.75), (tx + 0.2, ty + 0.75), 0.55, sole)
    if near:
        mx, my = (ankle[0] + tx) * 0.5 * s, (ankle[1] + ty) * 0.5 * s
        c.stroke([(mx - 2, my - 2), (mx + 1, my + 1)], 'p', only='s')
        c.stroke([(mx + 2, my - 2), (mx - 1, my + 1)], 'p', only='s')
        c.t(ax + 2, ay - 4, 'b', only=band)                  # bead


def _hand_hd(c, root, a1, l1, a2, l2, ch, rim=None, r1=1.2, r2=1.0, thumb=1):
    """`_limb`, then a hand with a thumb: the 1x hand is a round blob.
    `thumb` -1 puts the thumb on the other side (the front view's right hand)."""
    k, e = _limb(c, root, a1, l1, a2, l2, r1, r2, ch, rim=rim)
    ang = math.radians(a1 + a2)
    d = (math.sin(ang), math.cos(ang))
    side_ = (d[1] * thumb, -d[0] * thumb)     # toward her front
    c.capsule(e, (e[0] + d[0] * 1.6 + side_[0] * 0.2, e[1] + d[1] * 1.6 + side_[1] * 0.2),
              1.0, ch, 0.75)                  # fingers, longer than the palm blob
    c.capsule((e[0] + side_[0] * 0.7, e[1] + side_[1] * 0.7),
              (e[0] + side_[0] * 1.4 + d[0] * 0.6, e[1] + side_[1] * 1.4 + d[1] * 0.6),
              0.45, ch)                       # thumb
    s = c.s
    fx, fy = (e[0] + d[0] * 1.0) * s, (e[1] + d[1] * 1.0) * s
    c.stroke([(fx - side_[0] * 0.5, fy - side_[1] * 0.5),
              (fx + d[0] * 1.5 - side_[0] * 0.5, fy + d[1] * 1.5 - side_[1] * 0.5)],
             'S' if ch == 's' else 'z', only=ch)   # the line between fingers
    return k, e


def side_hd(p, ink=True):
    """`side()` at HD_SCALE with the 2x detail passes. Same pose dict."""
    q = dict(STAND)
    q.update(p)
    c = HDCanvas()
    s = c.s
    hip = (CX + q["hip_dx"], 23.0 + q["bob"])
    sh = (hip[0] + q["lean"], hip[1] - 9.4 * q["torso"])
    hx, hy = sh[0] + 1.2 + q["head_dx"], sh[1] - 5.6 + HAT_RIDE + q["head_dy"]
    sway, wave = q["sway"], q["wave"]
    fn = (hip[0] + q["near_fx"], FOOT_Y - 0.8 - q["near_lift"])
    ff = (hip[0] + q["far_fx"], FOOT_Y - 0.8 - q["far_lift"])

    _hand_hd(c, (sh[0] - 0.6, sh[1] + 0.9), q["far_sh"], 6.0, q["far_el"], 5.6, 'S')
    _foot_hd(c, _leg(c, (hip[0] - 0.6, hip[1]), ff, 'S', bend=q["far_bend"]),
             False, q["far_toe"], q["far_point"])

    hair_len = q["hair_len"]
    for i in range(12):
        t = i / 11.0
        y = hy - 1.0 + t * hair_len - t * t * q["float"]
        x = hx - 2.6 - t * (2.2 + sway) + math.sin(t * 5.5 + wave) * 0.9
        c.ellipse((x, y), 3.9 - t * 1.7, 2.1, 'H')
    # wispy ends: three tapering points instead of a round bottom
    tip_t = 1.0
    ty = hy - 1.0 + tip_t * hair_len - q["float"]
    tx = hx - 2.6 - (2.2 + sway) + math.sin(5.5 + wave) * 0.9
    for k, (dx, ln) in enumerate(((-1.2, 2.4), (0.0, 3.0), (1.0, 2.0))):
        c.capsule((tx + dx, ty), (tx + dx - sway * 0.4 - 0.4, ty + ln - q["float"] * 0.3),
                  0.7, 'H', 0.2)
    _hair_strands(c, hx, hy, q)

    _foot_hd(c, _leg(c, (hip[0] + 0.8, hip[1] + 0.6), fn, 's', rim='S', bend=q["near_bend"]),
             True, q["near_toe"], q["near_point"])

    c.capsule((sh[0], sh[1] + 2.5), hip, 2.2, 's', 2.6)
    # navel and the soft shadow under the ribs
    c.t((hip[0] + 1.6) * s, (hip[1] - 3.2) * s, 'S', only='s')
    c.ellipse((sh[0] + 0.9, sh[1] + 2.9), 3.3, 3.1, 't')
    c.capsule((sh[0] - 0.3, sh[1] - 0.2), (sh[0] + 0.9, sh[1] + 1.2), 0.6, 't')
    # crop top: a lit hem, a gather under the bust and two creases
    TX, TY = (sh[0] + 0.9) * s, (sh[1] + 2.9) * s
    for x in range(int(TX - 7), int(TX + 7)):
        for y in range(int(TY + 2), int(TY + 8)):
            if c.get(x, y) == 't' and c.get(x, y + 1) not in 'tu':
                c.t(x, y, 'u')
                c.t(x, y - 1, 'U' if x % 3 == 0 else 't', only='t')
    c.stroke([(TX + 1, TY - 2), (TX + 4, TY + 1)], 'U', only='t')
    c.stroke([(TX - 2, TY + 0), (TX + 1, TY + 3)], 'U', only='t')
    c.capsule((sh[0] + 0.3, sh[1] - 2.0), (sh[0] + 0.7, sh[1] + 0.6), 1.25, 's')

    srx, sry = q["shorts_rx"], 3.1
    c.ellipse((hip[0] + 0.2 + q["shorts_dx"], hip[1] + 0.6), srx, sry,
              'Y' if q["shorts_shade"] else 'y')
    c.capsule((hip[0] - srx + 0.4, hip[1] - 1.8), (hip[0] + 3.8, hip[1] - 1.8), 0.55, 'Y')
    c.ellipse((hip[0] + 0.8, hip[1] + 1.4), 3.0, 2.3, 'y')
    # waistband stitching and a fold where the near leg bends
    wy = int((hip[1] - 1.8) * s)
    for x in range(int((hip[0] - srx + 0.8) * s), int((hip[0] + 3.6) * s), 3):
        c.t(x, wy, 'o', only='Y')
    c.stroke([((hip[0] + 0.2) * s, (hip[1] - 0.6) * s),
              ((hip[0] + 2.2) * s, (hip[1] + 1.6) * s)], 'q', only='y')
    # fringe: separate tassels, alternating length, swinging with the stride
    fy = (hip[1] + 3.3) * s
    swing = -sway * 0.6
    for k, fx in enumerate(range(int((hip[0] - srx + 0.6) * s), int((hip[0] + 4.2) * s), 2)):
        ln = 3 if k % 2 == 0 else 2
        c.stroke([(fx, fy), (fx + swing, fy + ln)], 'Y' if k % 2 else 'q')

    c.ellipse((hx, hy), 3.7, 4.1, 's')
    c.ellipse((hx - 1.4, hy - 1.2), 3.2, 3.2, 'h',
              clip=lambda x, y: x < hx + 0.3 or y < hy - 2.6)
    c.capsule((hx - 3.0, hy - 1.0), (hx - 3.4 - sway * 0.3, hy + 5.0), 1.7, 'h')
    # a fringe lock falling to the brow line
    c.capsule((hx + 0.8, hy - 2.8), (hx + 1.6, hy - 1.5), 0.55, 'h', 0.25)
    _crown_strands(c, hx, hy)
    c.stroke([((hx - 3.0) * s, (hy - 0.4) * s), ((hx - 3.6 - sway * 0.3) * s, (hy + 4.8) * s)],
             'j', only='h')
    _face_hd(c, hx, hy, eyes=q["eyes"])
    # beads on a cord: each bead a lit dome
    for i, bx in enumerate((-0.4, 0.8, 2.0, 3.0)):
        by = sh[1] + 0.2 + (0.6 if i in (1, 2) else 0)
        c.ellipse((sh[0] + bx + 0.25, by + 0.25), 0.62, 0.62, 'b')
        c.t((sh[0] + bx) * s, (by) * s, 'B')
    if q["hat"] == "slung":
        _slung_hat_hd(c, sh, hx, hy)
    else:
        _hat_hd(c, hx, hy, q["hat_tilt"], sway, lift=q["hat_lift"] + HAT_RIDE)

    _hand_hd(c, (sh[0] - 0.9, sh[1] + 1.0), q["near_sh"], 6.0, q["near_el"], 5.6, 's', rim='S')

    if ink:
        c.outline()
    return c.rows()


def _hand_aa(img):
    """Hand anti-aliasing on the ink line. Where the outline turns a stair-step
    corner -- an ink texel with material on two perpendicular sides -- the ink
    is swapped for the darkest step of the material it hugs. At 1x this would
    eat the line; at 2x it rounds a curve the way a pixel artist rounds it.
    Returns the number of texels changed."""
    w, h = img.size
    px = img.load()
    ink = palette.INK
    lookup = {c: (n, i) for n, steps in palette.RAMPS.items() for i, c in enumerate(steps)}

    def mat(x, y):
        if 0 <= x < w and 0 <= y < h:
            p = px[x, y]
            if p[3] and p[:3] != ink:
                return lookup.get(p[:3])
        return None

    def clear(x, y):
        return not (0 <= x < w and 0 <= y < h) or px[x, y][3] == 0

    edits = []
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            if p[3] == 0 or p[:3] != ink:
                continue
            n, s_, e, w_ = mat(x, y - 1), mat(x, y + 1), mat(x + 1, y), mat(x - 1, y)
            for a, b, oa, ob in ((n, e, (0, 1), (-1, 0)), (n, w_, (0, 1), (1, 0)),
                                 (s_, e, (0, -1), (-1, 0)), (s_, w_, (0, -1), (1, 0))):
                if a and b and clear(x + oa[0], y + oa[1]) and clear(x + ob[0], y + ob[1]):
                    ramp, i = min((a, b), key=lambda m: m[1])
                    edits.append((x, y, palette.step(ramp, max(0, i - 2)) + (255,)))
                    break
    for x, y, col in edits:
        px[x, y] = col
    return len(edits)


def shade_hd(rows, mapping, depth=6, rate=0.24, lit=(0.9, 0.45), dark=(0.8, 0.35),
             light=palette.LIGHT):
    """`palette.auto_shade` for HD cells, with two differences. Levels are
    rounded to whole ramp steps instead of Bayer-dithered: over four times the
    texels a dither reads as a checkerboard on her skin, which is the same
    finding that made tiles go to CLEAN_FILL. And the rim light and the
    occlusion are two texels deep, stepping down, so the lit edge is as wide in
    world units as it was at 1x but now has a gradient inside it."""
    h, w = len(rows), len(rows[0])
    mat = [[rows[y][x] in mapping for x in range(w)] for y in range(h)]
    body = [[mat[y][x] or rows[y][x] == 'k' for x in range(w)] for y in range(h)]

    def in_body(x, y):
        return 0 <= x < w and 0 <= y < h and body[y][x]

    def in_mat(x, y):
        return 0 <= x < w and 0 <= y < h and mat[y][x]

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y in range(h):
        for x in range(w):
            ch = rows[y][x]
            if not mat[y][x]:
                if ch == 'k':
                    img.putpixel((x, y), palette.INK + (255,))
                continue
            d = 0
            while d < depth + 1:
                d += 1
                ring = [(x + dx, y + dy) for dx in range(-d, d + 1) for dy in (-d, d)]
                ring += [(x + dx, y + dy) for dy in range(-d + 1, d) for dx in (-d, d)]
                if any(not in_body(px, py) for px, py in ring):
                    break
            ramp, base = mapping[ch]
            lvl = base + (min(d, depth) - 1) * rate
            for k in (1, 2):
                if not in_mat(x + light[0] * k, y + light[1] * k):
                    lvl += lit[k - 1]
                    break
            for k in (1, 2):
                if not in_mat(x - light[0] * k, y - light[1] * k):
                    lvl -= dark[k - 1]
                    break
            img.putpixel((x, y), palette.step(ramp, lvl) + (255,))
    return img


def render_hd(rows):
    """Light, hand-AA and selout one HD frame. Volume is measured over twice
    as many texels, so the depth doubles and the rate halves: she is as round
    as at 1x, only more finely stepped."""
    img = shade_hd(rows, MAT_HD)
    _hand_aa(img)
    palette.selective_outline(img)
    return img


def _poses_of(builder):
    """The pose dicts a frame builder (`_jump`, ...) passes to side(), without
    drawing them: lets the HD sheet reuse the 1x choreography verbatim."""
    global side
    got = []
    real = side
    side = lambda p, ink=True: got.append(p) or []      # noqa: E731
    try:
        builder()
    finally:
        side = real
    return got


def hd_frames():
    """The look-sample sheet: 0-1 idle, 2-9 run, 10-15 jump, 16 stoop,
    17-22 stoop walk -- the same order and indices as the 1x sheet's first
    16 frames, then the stoop set."""
    poses = [idle_pose(i) for i in range(2)] + [run_pose(i) for i in range(8)]
    poses += _poses_of(_jump)
    poses += [STOOP] + [stoop_walk(i) for i in range(6)]
    cells = [side_hd(p) for p in poses]
    for i in range(16, 23):                     # still fits two tiles
        top = min(y for y, r in enumerate(cells[i]) if r.strip('.'))
        assert top >= STOOP_TOP * HD_SCALE, "hd stoop %d starts on row %d" % (i, top)
    return cells, poses


def hd_cells():
    return [render_hd(r) for r in hd_frames()[0]]


# ================================================================ HD: H1
# docs/plan-hd.md, phase H1: the whole sheet at 2x. The look sample above drew
# the side view; this adds the views it did not -- facing the camera and facing
# away (climb, half-turn, the dance's spin) and the hat slung on its cord (the
# narrow set) -- and assembles all 59 frames from the 1x choreography itself.
#
# The world-unit silhouette is the 1x one. `frames()` and its tests, the pose
# data in data/forms/human.json, src/player/kaya_pose.gd and tools/clipgate.sh
# were all proved against the 1x frames, so each HD frame is clipped to its 1x
# frame's opaque units (`_clip_to`) and the cut edge re-inked. What the clip
# trims is a half-unit of shadow-side line or a hair tip that would have
# reached one unit past the 1x line; nothing inside the silhouette changes.

def _eyes_front(c, X, Y, eyes=True):
    """Two almond eyes in native texels, `X` the face's centre line (float) and
    `Y` the eye row: a lid line with an outer lash, white, iris, pupil, and a
    lower-lid crease. Shut, each is a downturned curve of lash."""
    T = c.t
    for side_ in (-1, 1):
        # four texels per eye, outer corner first; the pupils sit toward the
        # nose, so she looks at the camera rather than past it
        xs = [int(math.floor(X + side_ * (5.5 - i))) for i in range(4)]
        if eyes:
            for x in xs:
                T(x, Y - 1, 'k')                       # upper lid
            T(xs[0] + (-side_), Y - 2, 'k')            # lash flick
            T(xs[0], Y, 'w')
            T(xs[1], Y, 'e')
            T(xs[2], Y, 'E')
            T(xs[3], Y, 'w')
            T(xs[1], Y + 1, 'e')
            T(xs[2], Y + 1, 'e')
            T(xs[1], Y + 2, 'z')
            T(xs[2], Y + 2, 'z')
        else:
            T(xs[0], Y, 'k')
            T(xs[1], Y + 1, 'k')
            T(xs[2], Y + 1, 'k')
            T(xs[3], Y, 'k')
            T(xs[0] + (-side_), Y - 1, 'k')            # lash


def _face_front_hd(c, hx, hy, eyes=True, smile=False):
    """The face seen from the front: eyes, a nose drawn as one light and one
    shadow texel (the light is upper left), cheeks, lips with a darker parting
    and lifted corners when she smiles, and the hoops hanging under the hair."""
    s = c.s
    X, Y = hx * s, int(math.floor(hy * s))
    T = c.t
    _eyes_front(c, X, Y, eyes)
    cx = int(math.floor(X))
    T(cx - 1, Y + 2, 'c')                              # bridge light
    T(cx, Y + 3, 'z')                                  # nostril shadow
    T(cx - 1, Y + 3, 's')
    for dx in (-5, -4, 3, 4):                          # cheeks
        T(cx + dx, Y + 3, 'c')
    for dx in (-1, 0):
        T(cx + dx, Y + 5, 'L')                         # parting
        T(cx + dx, Y + 6, 'l')                         # lower lip
    T(cx - 2, Y + 5, 'l')
    T(cx + 1, Y + 5, 'l')                              # upper lip
    if smile:
        T(cx - 3, Y + 4, 'L')
        T(cx + 2, Y + 4, 'L')                          # lifted corners
    c.stroke([(cx - 3, Y + 8), (cx + 2, Y + 8)], 'S', only='s')   # under the chin
    for sx in (-1, 1):                                 # hoops below the ear
        ex = int(math.floor(X + sx * 7.4))
        T(ex, Y + 3, 'o')
        T(ex + sx, Y + 4, 'o')
        T(ex, Y + 5, 'o')
        T(ex - sx, Y + 4, 'B' if sx < 0 else 'o')


def _hair_front_hd(c, hx, hy, sway):
    """Locks either side of the face and the mass behind the shoulders, as
    strands: a groove down each lock and a sheen on its lit (left) side."""
    s = c.s
    for sx in (-1, 1):
        x0, x1 = (hx + 3.4 * sx) * s, (hx + 3.6 * sx) * s
        c.stroke([(x0 - sx, (hy - 1.2) * s), (x1 - sx, (hy + 3.8) * s)], 'j', only='h')
        c.stroke([(x0 - 1, (hy - 1.0) * s), (x1 - 1, (hy + 2.6) * s)], 'i', only='h')
        # the mass behind the shoulders
        bx0, bx1 = (hx + 3.8 * sx) * s, (hx + 4.6 * sx - sway) * s
        for off, ch in ((0.0, 'J'), (1.6 * sx, 'J'), (-1.4 * sx, 'I')):
            c.stroke([(bx0 + off, hy * s + 4), (bx1 + off, (20.0 - 0.8) * s + (hy - 8.0) * s)],
                     ch, only='H')
    # a fringe under the brim: three locks combed from a parting off-centre
    X, Y = hx * s, hy * s
    for k, dx in enumerate((-4.5, -1.5, 2.5)):
        c.stroke([(X + dx, Y - 4), (X + dx - 1.5, Y - 2)], 'h')
        c.t(X + dx - 1, Y - 3, 'i' if k < 2 else 'j', only='h')


def _hair_back_hd(c, hx, hy, sway):
    """The hair from behind: the 1x mass, with the grooves running from the
    crown down its length (bending with the sway) and a sheen down the lit
    side. The ends taper into points instead of a round bottom."""
    s = c.s
    for off, ch in ((-2.6, 'j'), (-0.9, 'j'), (0.8, 'j'), (2.4, 'j'),
                    (-1.8, 'i'), (0.0, 'i')):
        pts = []
        for i in range(25):
            t = i / 24.0
            x = hx + math.sin(t * 5) * 0.6 - sway * t + off * (1.0 - 0.3 * t)
            y = hy - 2.6 + t * 15.0
            if ch == 'i' and (t < 0.15 or math.sin(t * 5) > 0.5):
                continue
            pts.append((x * s, y * s))
        c.stroke(pts, ch, only='h')
    tx, ty = hx - sway, hy + 2 + 12 + 1.6
    for dx, ln in ((-2.2, 1.6), (-0.6, 2.4), (1.0, 2.0), (2.4, 1.2)):
        c.capsule((tx + dx, ty - 0.6), (tx + dx - sway * 0.3, ty + ln), 0.7, 'h', 0.2)


def _hat_back_hd(c, hx, hy, tilt, sway):
    """The hat from behind: woven crown, band, brim -- and the bow at the back
    with both tails hanging down over the hair, swinging with it."""
    s = c.s
    _hat_hd(c, hx, hy, tilt, sway, tails=False, knot=-0.2)
    for x0, x1, y1 in ((hx - 0.4, hx - 2.0 - sway, hy + 1.8), (hx + 0.2, hx + 1.8 - sway * 0.6,
                                                                hy + 1.2)):
        c.capsule((x0, hy - 2.4), (x1, y1), 0.6, 'n', 0.45)
        c.stroke([(x0 * s - 1, (hy - 2.0) * s), (x1 * s - 1, y1 * s - 1)], 'N', only='n')
        c.t(x1 * s, y1 * s + 1, 'V')                   # cut end, frayed
    c.ellipse((hx - 0.1, hy - 3.4), 1.0, 0.8, 'n')    # the bow
    c.t((hx - 0.4) * s, (hy - 3.8) * s, 'N', only='n')


def _foot_front_hd(c, a, near, back=False):
    """Ankle band and sandal seen from the front (or the heel from behind)."""
    s = c.s
    band = 'g' if near else 'G'
    c.capsule((a[0], a[1] - 2.0), (a[0], a[1] - 0.9), 1.55, band)
    ax, ay = a[0] * s, a[1] * s
    for k in (-3, -1):
        c.stroke([(ax - 3, ay + k + (0 if back else 1)), (ax + 3, ay + k)],
                 'G' if near else 'U', only=band)
    if back:
        c.capsule((a[0] - 0.7, a[1] + 0.2), (a[0] + 0.7, a[1] + 0.2), 1.05, 'r')
        c.capsule((a[0] - 0.5, a[1] - 0.2), (a[0] + 0.5, a[1] - 0.2), 0.6, 's' if near else 'S')
        c.stroke([(ax - 2, ay + 2), (ax + 1, ay + 2)], 'R', only='r')   # heel of the sole
        return
    c.capsule((a[0] - 0.8, a[1] + 0.2), (a[0] + 0.8, a[1] + 0.2), 1.05, 'r')
    c.capsule((a[0] - 0.55, a[1] - 0.1), (a[0] + 0.55, a[1] - 0.1), 0.7, 's' if near else 'S')
    c.stroke([(ax - 2, ay - 1), (ax + 1, ay + 1)], 'p', only='sS')
    c.stroke([(ax + 1, ay - 1), (ax - 2, ay + 1)], 'p', only='sS')
    c.t(ax - 1, ay - 4, 'b', only=band)                # bead


def front_hd(p=None, back=False):
    """`front()` at HD_SCALE: the same geometry, with a face, hair strands, a
    woven hat, the crop top's hem and tie, stitched shorts with tassels, hands
    and sandals drawn in native texels."""
    q = dict(FRONT)
    q.update(p or {})
    back = back or q["back"]
    c = HDCanvas()
    s = c.s
    hip_y, sh_y = 23.0 + q["bob"], 13.6 + q["bob"]
    cx = CX + q["hip_dx"]
    hx, hy = CX + q["hip_dx"] * 0.4, 8.0 + q["bob"]
    sway = q["sway"]
    if not back:
        c.capsule((hx - 3.8, hy), (hx - 4.6 - sway, 20.0 + q["bob"]), 2.2, 'H', 1.6)
        c.capsule((hx + 3.8, hy), (hx + 4.6 - sway, 20.0 + q["bob"]), 2.2, 'H', 1.6)
    for sx, near in ((-1, False), (1, True)):
        ch = 's' if near else 'S'
        fx = q["r_fx"] if sx > 0 else q["l_fx"]
        lift = q["r_lift"] if sx > 0 else q["l_lift"]
        a = _leg(c, (cx + 2.2 * sx, hip_y + 0.8),
                 (cx + 2.5 * sx + fx, FOOT_Y - 0.8 - lift), ch,
                 bend=sx * (0.9 if lift > 2.0 else 0.3))
        _foot_front_hd(c, a, near, back)
        # the kneecap: a light texel over a shadow one
        kx, ky = (cx + 2.3 * sx + fx * 0.5) * s, (hip_y + 0.8 + (FOOT_Y - 0.8 - lift - hip_y) * 0.47) * s
        c.t(kx, ky, 'c' if near else 's', only=ch)
        c.t(kx, ky + 1, 'S' if near else 'z', only=ch)
    c.capsule((cx, sh_y + 2.5), (cx, hip_y), 3.0, 's', 3.3)
    c.ellipse((cx, sh_y + 2.8), 4.4, 3.2, 't' if not back else 's')
    TX, TY = cx * s, (sh_y + 2.8) * s
    if back:
        # spine and shoulder blades, then the top's back band tied in a bow
        c.stroke([(TX, TY - 3), (TX + 0.5, (hip_y - 1.4) * s)], 'S', only='s')
        for sx in (-1, 1):
            c.stroke([(TX + sx * 3, TY - 3), (TX + sx * 5, TY - 1)], 'S', only='s')
        c.capsule((cx - 4.0, sh_y + 3.0), (cx + 4.0, sh_y + 3.0), 1.4, 't')
        BY = (sh_y + 3.0) * s
        c.stroke([(TX - 8, BY - 2), (TX + 8, BY - 2)], 'u', only='t')    # lit edge
        c.stroke([(TX - 8, BY + 2), (TX + 8, BY + 2)], 'U', only='t')
        c.ellipse((cx - 0.9, sh_y + 3.0), 1.0, 1.1, 'T')
        c.ellipse((cx + 0.9, sh_y + 3.0), 1.0, 1.1, 'T')                 # bow loops
        c.t(TX - 2, BY - 1, 'u', only='T')
        c.t(TX + 1, BY - 1, 'u', only='T')
        c.ellipse((cx, sh_y + 3.0), 0.5, 0.6, 'U')                       # knot
        c.stroke([(TX - 1, BY + 2), (TX - 3, BY + 6)], 't')
        c.stroke([(TX, BY + 2), (TX + 2, BY + 5)], 't')                  # tails
    else:
        c.capsule((cx - 1.6, sh_y - 0.4), (cx - 1.2, sh_y + 1.0), 0.55, 't')
        c.capsule((cx + 1.6, sh_y - 0.4), (cx + 1.2, sh_y + 1.0), 0.55, 't')
        # hem lit along the bottom, a gather between the cups, side creases
        for x in range(int(TX - 9), int(TX + 9)):
            for y in range(int(TY), int(TY + 8)):
                if c.get(x, y) == 't' and c.get(x, y + 1) not in 'tu':
                    c.t(x, y, 'u')
                    c.t(x, y - 1, 'U' if x % 3 == 1 else 't', only='t')
        c.stroke([(TX, TY - 3), (TX, TY + 2)], 'U', only='t')
        c.t(TX - 1, TY - 3, 'u', only='t')
        for sx in (-1, 1):
            c.stroke([(TX + sx * 3, TY - 1), (TX + sx * 6, TY + 2)], 'U', only='t')
            c.t(TX + sx * 3 - 1, TY - 4, 'u', only='t')                  # strap light
        c.t(cx * s, (hip_y - 2.6) * s, 'S', only='s')                     # navel
    c.ellipse((cx, hip_y + 0.6), 4.9, 3.1, 'y')
    c.capsule((cx - 4.6, hip_y - 1.8), (cx + 4.6, hip_y - 1.8), 0.55, 'Y')
    WY = int((hip_y - 1.8) * s)
    for x in range(int((cx - 4.2) * s), int((cx + 4.4) * s), 3):
        c.t(x, WY, 'o', only='Y')                                         # stitching
    c.stroke([(cx * s, WY + 2), (cx * s, (hip_y + 2.4) * s)], 'q', only='y')   # seam
    for sx in (-1, 1):
        c.stroke([((cx + 2.2 * sx) * s, (hip_y + 1.0) * s),
                  ((cx + 3.6 * sx) * s, (hip_y + 2.6) * s)], 'q', only='y')
    fy = (hip_y + 3.3) * s
    for k, fx in enumerate(range(int((cx - 4.6) * s), int((cx + 4.8) * s), 2)):
        ln = 3 if k % 2 == 0 else 2
        c.stroke([(fx, fy), (fx - sway * 0.6, fy + ln)], 'Y' if k % 2 else 'q')
    c.capsule((hx, sh_y - 2.0), (cx, sh_y + 0.4), 1.3, 's')
    arms = ((-1, q["l_sh"], q["l_el"]), (1, q["r_sh"], q["r_el"]))
    if not back:
        for sx, a, e in arms:
            _hand_hd(c, (cx + 4.4 * sx, sh_y + 1.0), a * sx, 6.0, e * sx, 5.6, 's',
                     r1=1.45, r2=1.15, thumb=-sx)
    if back:
        c.ellipse((hx, hy), 3.9, 4.2, 'h')
        for i in range(10):
            t = i / 9.0
            c.ellipse((hx + math.sin(t * 5) * 0.6 - sway * t, hy + 2 + t * 12),
                      4.6 - t * 1.4, 2.2, 'h')
        _hair_back_hd(c, hx, hy, sway)
    else:
        c.ellipse((hx, hy), 3.7, 4.1, 's')
        c.ellipse((hx, hy - 2.4), 3.9, 2.0, 'h', clip=lambda x, y: y < hy - 1.0)
        c.capsule((hx - 3.4, hy - 1.5), (hx - 3.6, hy + 4.0), 1.2, 'h')
        c.capsule((hx + 3.4, hy - 1.5), (hx + 3.6, hy + 4.0), 1.2, 'h')
        _hair_front_hd(c, hx, hy, sway)
        _face_front_hd(c, hx, hy, q["eyes"], q["smile"])
        for bx in (-1.6, -0.5, 0.6, 1.7):
            by = sh_y + 0.3 + (0.5 if abs(bx) < 1 else 0)
            c.ellipse((cx + bx + 0.25, by + 0.25), 0.62, 0.62, 'b')
            c.t((cx + bx) * s, by * s, 'B')
    if back:
        _hat_back_hd(c, hx, hy, q["hat_tilt"], sway)
        for sx, a, e in arms:
            _hand_hd(c, (cx + 4.4 * sx, sh_y + 1.0), a * sx, 6.0, e * sx, 5.6,
                     's' if sx > 0 else 'S', r1=1.45, r2=1.15, thumb=sx)
    else:
        _hat_hd(c, hx, hy, q["hat_tilt"], tails=False, knot=2.6)
    c.outline()
    return c.rows()


def _slung_hat_hd(c, sh, hx, hy):
    """`_slung_hat` in native texels: the brim edge-on behind her shoulders
    with its weave rings and a sunlit lip, the crown a woven bump with the
    ribbon round its base, and the cord across her throat with a toggle."""
    s = c.s
    bx = sh[0] - 4.0
    c.ellipse((bx, sh[1] + 3.6), 1.5, 8.0, 'A')
    c.ellipse((bx + 0.8, sh[1] + 3.6), 1.1, 3.2, 'a')
    X0, Y0, Y1 = bx * s, (sh[1] + 3.6 - 8.0) * s, (sh[1] + 3.6 + 8.0) * s
    for y in range(int(Y0), int(Y1) + 1):
        if y % 3 == 0:                                     # weave rings, edge-on
            c.stroke([(X0 - 3, y), (X0 + 1, y + 1)], 'v', only='A')
        c.t(X0 - 2 if abs(y - (Y0 + Y1) / 2) < 12 else X0 - 1, y, 'x', only='A')   # lip
        c.t(X0 + 2, y, 'V', only='A')                      # the brim's shadow side
    CX_, CY_ = (bx + 0.8) * s, (sh[1] + 3.6) * s
    for y in range(int(CY_ - 6), int(CY_ + 7)):
        for x in range(int(CX_ - 2), int(CX_ + 3)):
            if (x + y) % 3 == 0:
                c.t(x, y, 'v', only='a')
    c.stroke([(CX_ - 2, CY_ - 6), (CX_ - 2, CY_ + 6)], 'n', only='aA')   # band
    c.stroke([(CX_ - 1, CY_ - 5), (CX_ - 1, CY_ - 1)], 'N', only='a')
    c.capsule((hx + 0.6, hy + 3.2), (bx + 0.6, sh[1] - 1.4), 0.45, 'n')
    c.stroke([((hx + 0.6) * s, (hy + 3.2) * s - 1), ((bx + 0.6) * s, (sh[1] - 1.4) * s - 1)],
             'N', only='n')
    c.ellipse((hx + 0.6, hy + 3.4), 0.55, 0.55, 'b')       # toggle
    c.t((hx + 0.6) * s - 1, (hy + 3.4) * s - 1, 'B')


def _calls():
    """`frames()` as the calls that draw it, in sheet order: ("side", pose)
    or ("front", pose, back). The HD sheet replays exactly these, so its
    choreography IS the 1x choreography. Also returns the 1x rows."""
    global side, front
    real_side, real_front = side, front
    got = []

    def rec_side(p, ink=True):
        got.append(("side", p))
        return real_side(p, ink)

    def rec_front(p=None, back=False):
        got.append(("front", p or {}, back))
        return real_front(p, back)

    side, front = rec_side, rec_front
    try:
        one = frames()
    finally:
        side, front = real_side, real_front
    assert len(got) == FRAME_COUNT, len(got)
    return got, one


def _clip_to(rows, rows_1x, s=HD_SCALE):
    """Keep only texels whose world unit is opaque in the 1x frame, and re-ink
    material the cut left bare. Returns (rows, texels cut)."""
    g = [list(r) for r in rows]
    h, w = len(g), len(g[0])
    cut = 0
    for y in range(h):
        for x in range(w):
            if g[y][x] != '.' and rows_1x[y // s][x // s] == '.':
                g[y][x] = '.'
                cut += 1
    out = [r[:] for r in g]
    for y in range(h):
        for x in range(w):
            if g[y][x] in '.k':
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < w and 0 <= ny < h) or g[ny][nx] == '.':
                    out[y][x] = 'k'
                    break
    return ["".join(r) for r in out], cut


def units(rows, s=HD_SCALE):
    """An HD frame as world units: a unit is drawn if any of its texels is
    (the same rule tools/clipgate.sh and KayaPose.bounds_to_world use)."""
    h, w = len(rows) // s, len(rows[0]) // s
    return [["." if all(rows[y * s + j][x * s + i] == '.' for j in range(s) for i in range(s))
             else "#" for x in range(w)] for y in range(h)]


def sheet_frames():
    """All 59 frames at HD_SCALE, in the order data/forms/human.json indexes
    them, each inside its 1x frame's world-unit silhouette. Asserts the same
    things `frames()` asserts, measured in world units."""
    calls, one = _calls()
    out = []
    for i, call in enumerate(calls):
        if call[0] == "side":
            p = call[1]
            rows = side_hd(p)
        else:
            rows = front_hd(call[1], call[2])
        rows, _ = _clip_to(rows, one[i])
        out.append(rows)
    for i in NARROW_FRAMES:
        xs = [x for r in units(out[i]) for x, ch in enumerate(r) if ch != '.']
        assert max(xs) - min(xs) + 1 <= NARROW_W, "hd narrow frame %d" % i
    for i in list(STOOP_FRAMES) + list(SWIM_FRAMES) + [58]:
        top = min(y for y, r in enumerate(units(out[i])) if '#' in r)
        assert top >= STOOP_TOP, "hd frame %d starts on unit row %d" % (i, top)
    return out


def light_hd(rows):
    """Lit and hand-AA'd, without selout: `palette.sheet(selout=True)` runs
    that once over the packed sheet, as it does for every character sheet."""
    img = shade_hd(rows, MAT_HD)
    _hand_aa(img)
    return img


def sheet_cells():
    """kaya_human at HD_SCALE, ready for `palette.sheet(..., selout=True)`."""
    return [light_hd(r) for r in sheet_frames()]


# The hub at 2x: the same poses, drawn at 2x without ink, shrunk to 48x56
# texels about the feet, inked there, and clipped to the 1x hub silhouette.
# A plain point-sample drops a third of every one-texel line, so the sample
# takes the face's features if any falls in its footprint.
HUB_KEEP = "kElB"


def _shrink_hd(rows, scale=HUB_SCALE, w=HUB_W * HD_SCALE, h=HUB_H * HD_SCALE):
    s = HD_SCALE
    c = HDCanvas()
    c.w, c.h = w, h
    c.g = [['.'] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            fx0 = (x - w * 0.5) / scale + CX * s
            fy0 = (y - h) / scale + (FOOT_Y + 1.0) * s
            fx1, fy1 = fx0 + 1 / scale, fy0 + 1 / scale
            pick = None
            for sy in range(int(math.floor(fy0)), int(math.ceil(fy1))):
                for sx in range(int(math.floor(fx0)), int(math.ceil(fx1))):
                    if 0 <= sx < W * s and 0 <= sy < H * s and rows[sy][sx] in HUB_KEEP:
                        pick = rows[sy][sx]
            sx, sy = int((fx0 + fx1) / 2), int((fy0 + fy1) / 2)
            if pick is None and 0 <= sx < W * s and 0 <= sy < H * s:
                pick = rows[sy][sx]
            if pick is not None:
                c.g[y][x] = pick
    c.outline()
    return c.rows()


def hub_sheet_frames():
    one = hub_frames()
    poses = [idle_pose(0), idle_pose(2)] + [run_pose(i) for i in range(8)]
    return [_clip_to(_shrink_hd(side_hd(p, ink=False)), one[i])[0] for i, p in enumerate(poses)]


def hub_sheet_cells():
    return [light_hd(r) for r in hub_sheet_frames()]


def write_bounds_hd(sheet_path, fw=W, fh=H, s=HD_SCALE):
    """`write_bounds` for the native sheet: per frame, per TEXEL row, the first
    and last opaque texel column, with `"scale"` so src/player/kaya_pose.gd
    folds them into world units (bounds_to_world). frame_w/frame_h stay in
    world units, like data/forms/human.json."""
    import json
    import os
    img = Image.open(sheet_path).convert("RGBA")
    a = img.getchannel("A").load()
    cw = fw * s
    n = img.width // cw
    out = []
    for f in range(n):
        rows = []
        for y in range(fh * s):
            xs = [x for x in range(cw) if a[f * cw + x, y] > 0]
            rows.append([xs[0], xs[-1]] if xs else [-1, -1])
        out.append(rows)
    doc = {"_comment": "Generated by tools/art/kaya40.py from kaya_human.png. Do not edit. "
                       "Texel rows at `scale` texels per world unit.",
           "frame_w": fw, "frame_h": fh, "scale": s, "rows": out}
    path = os.path.splitext(sheet_path)[0] + ".bounds.json"
    with open(path, "w") as fh_:
        json.dump(doc, fh_, separators=(",", ":"))
        fh_.write("\n")


def hd_render_all():
    """Every sheet frame lit, hand-AA'd and selout'd on its own: for previews."""
    out = []
    for img in sheet_cells():
        palette.selective_outline(img)
        out.append(img)
    return out
