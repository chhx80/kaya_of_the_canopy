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
unchanged 10x22 hitbox stays where it was relative to her feet. The sprite is
deliberately taller than the hitbox; see the stoop pose for low ceilings.
"""

import math

from PIL import Image

from . import palette

W, H = 32, 40
FOOT_Y = 39.0
CX = 16.0

# Two ramps the palette did not have. Dark -> light, seven steps, ordered by
# luminance like every other ramp so dithering between steps stays smooth.
# Hair rotates toward a warm red-brown as it brightens; straw toward a pale
# cream, so the hat reads as woven grass rather than as gold metal.
EXTRA_RAMPS = {
    "hair":  [(0x14, 0x0a, 0x08), (0x22, 0x11, 0x0b), (0x33, 0x19, 0x10),
              (0x48, 0x24, 0x16), (0x60, 0x32, 0x1d), (0x7c, 0x43, 0x26),
              (0x9a, 0x58, 0x33)],
    "straw": [(0x3a, 0x26, 0x10), (0x5c, 0x3d, 0x18), (0x86, 0x5c, 0x24),
              (0xb0, 0x82, 0x36), (0xd4, 0xa8, 0x4c), (0xea, 0xc9, 0x72),
              (0xf8, 0xe6, 0xa6)],
}
for _k, _v in EXTRA_RAMPS.items():
    palette.RAMPS.setdefault(_k, _v)

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
    'l': ("ember", 3.9),                # lips
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
        self._set(int(x), int(y), ch)

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


THIGH, SHIN = 7.5, 7.6      # hip to sole is ~15 px; longer bones buckle the knee


def _leg(c, hip, foot, ch, rim=None):
    """Two-bone IK: the knee always bends forward, the foot lands where told."""
    dx, dy = foot[0] - hip[0], foot[1] - hip[1]
    d = min(math.hypot(dx, dy), THIGH + SHIN - 0.05)
    a = math.atan2(dy, dx)
    cos_k = (THIGH ** 2 + d ** 2 - SHIN ** 2) / (2 * THIGH * d)
    k_ang = a - math.acos(max(-1.0, min(1.0, cos_k)))   # minus: knee toward +x
    knee = (hip[0] + math.cos(k_ang) * THIGH, hip[1] + math.sin(k_ang) * THIGH)
    ankle = (knee[0] + (foot[0] - knee[0]) * SHIN / max(math.hypot(foot[0] - knee[0], foot[1] - knee[1]), 1e-6),
             knee[1] + (foot[1] - knee[1]) * SHIN / max(math.hypot(foot[0] - knee[0], foot[1] - knee[1]), 1e-6))
    if rim:
        c.capsule(hip, knee, 2.95, rim, 2.4)
        c.capsule(knee, ankle, 2.4, rim, 1.9)
    c.capsule(hip, knee, 2.3, ch, 1.75)
    c.capsule(knee, ankle, 1.75, ch, 1.25)
    return ankle


def _foot(c, ankle, near, lift_toe=0.0):
    band = 'g' if near else 'G'
    sole = 'r' if near else 'R'
    c.capsule((ankle[0] - 0.2, ankle[1] - 2.0), (ankle[0], ankle[1] - 0.9), 1.55, band)
    c.capsule(ankle, (ankle[0] + 3.0, ankle[1] + 0.3 - lift_toe), 1.05, sole)


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


def _hat(c, hx, hy, tilt, sway=0.0, back=False, rx=10.4):
    c.ellipse((hx - 0.2, hy - 4.6), 3.8, 2.7, 'a', clip=lambda x, y: y < hy - 3.1)
    c.capsule((hx - 3.7, hy - 3.6), (hx + 3.5, hy - 3.6), 0.65, 'n')     # ribbon band
    _brim(c, hx, hy - 2.7, rx, tilt)
    if back:
        c.capsule((hx + 0.4, hy - 3.4), (hx - 1.8 - sway, hy + 1.6), 0.7, 'n')
        c.capsule((hx + 1.0, hy - 3.4), (hx + 2.6, hy + 1.0), 0.7, 'n')


# --------------------------------------------------------------- side view
def side(p):
    """Profile facing right. `p` is a pose dict; missing keys take the stand."""
    q = dict(STAND)
    q.update(p)
    c = Canvas()
    hip = (CX + q["hip_dx"], 23.0 + q["bob"])
    sh = (hip[0] + q["lean"], hip[1] - 9.4 * q["torso"])
    hx, hy = sh[0] + 1.2 + q["head_dx"], sh[1] - 5.6 + q["head_dy"]
    sway, wave = q["sway"], q["wave"]
    fn = (hip[0] + q["near_fx"], FOOT_Y - 0.8 - q["near_lift"])
    ff = (hip[0] + q["far_fx"], FOOT_Y - 0.8 - q["far_lift"])

    # far arm and far leg, behind everything
    _limb(c, (sh[0] - 0.6, sh[1] + 0.9), q["far_sh"], 6.0, q["far_el"], 5.6, 1.4, 1.1, 'S')
    _foot(c, _leg(c, (hip[0] - 0.6, hip[1]), ff, 'S'), False, q["far_toe"])

    # hair down the back: a heavy wavy mass, swinging with `sway`
    for i in range(12):
        t = i / 11.0
        y = hy - 1.0 + t * 13.5
        x = hx - 2.6 - t * (2.2 + sway) + math.sin(t * 5.5 + wave) * 0.9
        c.ellipse((x, y), 3.9 - t * 1.7, 2.1, 'H')

    # near leg, rimmed so it separates from the far one; drawn before the
    # shorts so the hem covers the top of both thighs
    _foot(c, _leg(c, (hip[0] + 0.8, hip[1] + 0.6), fn, 's', rim='S'), True, q["near_toe"])

    # torso: bare midriff between the crop top and the shorts
    c.capsule((sh[0], sh[1] + 2.5), hip, 2.2, 's', 2.6)
    c.ellipse((sh[0] + 0.9, sh[1] + 2.9), 3.3, 3.1, 't')          # crop top
    c.capsule((sh[0] - 0.3, sh[1] - 0.2), (sh[0] + 0.9, sh[1] + 1.2), 0.6, 't')  # strap
    c.capsule((sh[0] + 0.3, sh[1] - 2.0), (sh[0] + 0.7, sh[1] + 0.6), 1.25, 's')  # neck
    c.ellipse((hip[0] + 0.2, hip[1] + 0.6), 4.2, 3.1, 'y')          # shorts
    c.capsule((hip[0] - 3.8, hip[1] - 1.8), (hip[0] + 3.8, hip[1] - 1.8), 0.55, 'Y')  # waistband
    for fx in range(-4, 5):                                         # fringe
        if fx % 2 == 0:
            c.px(hip[0] + fx, hip[1] + 3.7, 'Y')

    c.ellipse((hip[0] + 0.8, hip[1] + 1.4), 3.0, 2.3, 'y')          # near shorts leg

    # head and face
    c.ellipse((hx, hy), 3.7, 4.1, 's')
    c.ellipse((hx - 1.4, hy - 1.2), 3.2, 3.2, 'h',
              clip=lambda x, y: x < hx + 0.3 or y < hy - 2.6)      # hair over crown
    c.capsule((hx - 3.0, hy - 1.0), (hx - 3.4 - sway * 0.3, hy + 5.0), 1.7, 'h')  # lock by the ear
    c.px(hx + 1.2, hy - 0.4, 'w')
    c.px(hx + 2.2, hy - 0.4, 'k')
    c.px(hx + 2.2, hy + 0.6, 'k')                                   # eye, two px tall
    c.px(hx + 1.6, hy - 1.9, 'h')
    c.px(hx + 2.6, hy - 1.9, 'h')                                   # brow
    c.px(hx + 3.9, hy + 0.9, 's')                                   # nose
    c.px(hx + 3.0, hy + 2.5, 'l')                                   # lips
    c.px(hx - 0.6, hy + 1.6, 'o')                                   # hoop
    for i, bx in enumerate((-0.4, 0.8, 2.0, 3.0)):                  # beads
        c.px(sh[0] + bx, sh[1] + 0.2 + (0.6 if i in (1, 2) else 0), 'b')
    _hat(c, hx, hy, q["hat_tilt"], sway)

    # near arm last, over the torso
    _limb(c, (sh[0] - 0.9, sh[1] + 1.0), q["near_sh"], 6.0, q["near_el"], 5.6, 1.2, 1.0, 's', rim='S')

    c.outline()
    return c.rows()


STAND = dict(bob=0.0, hip_dx=0.0, lean=0.4, torso=1.0, head_dx=0.0, head_dy=0.0,
             sway=0.0, wave=0.0, hat_tilt=0.0,
             near_fx=2.0, near_lift=0.0, near_toe=0.0,
             far_fx=-1.6, far_lift=0.0, far_toe=0.0,
             near_sh=-4, near_el=14, far_sh=6, far_el=12)

# Eight-frame run as foot targets: contact, down, pass, push, toe-off,
# recovery, high pass, reach. The far foot runs half a cycle behind.
_FX = [7.0, 3.5, 0.0, -4.0, -7.5, -4.0, 1.5, 5.5]
_FL = [0.3, 0.0, 0.0, 0.4, 2.2, 5.5, 5.5, 2.4]
_FT = [1.2, 0.0, 0.0, -0.6, -1.4, 0.0, 0.6, 1.4]
_BOB = [1.2, 1.8, 0.6, 0.0, 1.2, 1.8, 0.6, 0.0]


def run_pose(i):
    j = (i + 4) % 8
    ph = i / 8 * 2 * math.pi
    return dict(bob=_BOB[i], lean=1.8, sway=1.6 + 0.6 * math.sin(ph), wave=ph,
                hat_tilt=0.4 + 0.2 * math.sin(ph * 2),
                near_fx=_FX[i], near_lift=_FL[i], near_toe=_FT[i],
                far_fx=_FX[j], far_lift=_FL[j], far_toe=_FT[j],
                near_sh=-_FX[i] * 4.0, near_el=70, far_sh=-_FX[j] * 4.0, far_el=70)


def idle_pose(i):
    breath = (0.0, 0.5, 1.0, 0.5)[i % 4]
    return dict(bob=breath * 0.6, sway=breath * 0.5, wave=i * 0.9,
                hat_tilt=0.2 * breath, near_sh=-4 + breath * 2)


# Low ceiling: the whole silhouette must fit two tiles (32 px), so the hips
# drop, the knees take it, the back leans in and the hat tips forward.
STOOP = dict(bob=6.5, hip_dx=-1.0, lean=3.6, torso=0.92, head_dx=0.8, head_dy=1.2,
             hat_tilt=-0.9, sway=0.6,
             near_fx=4.0, far_fx=-2.6, near_sh=24, near_el=40, far_sh=18, far_el=40)


# -------------------------------------------------------- front and back
def front(back=False):
    c = Canvas()
    hip_y, sh_y = 23.0, 13.6
    hx, hy = CX, 8.0
    if back:   # hair behind everything in the back view would hide nothing
        pass
    else:      # long hair falling behind the shoulders, visible either side
        c.capsule((CX - 3.8, hy), (CX - 4.6, 20.0), 2.2, 'H', 1.6)
        c.capsule((CX + 3.8, hy), (CX + 4.6, 20.0), 2.2, 'H', 1.6)
    for sx, near in ((-2.2, False), (2.2, True)):
        ch = 's' if near else 'S'
        a = _leg(c, (CX + sx, hip_y + 0.8), (CX + sx * 1.15, FOOT_Y - 0.8), ch)
        c.capsule((a[0], a[1] - 2.0), (a[0], a[1] - 0.9), 1.55, 'g' if near else 'G')
        c.capsule((a[0] - 0.8, a[1] + 0.2), (a[0] + 0.8, a[1] + 0.2), 1.05, 'r')
    c.capsule((CX, sh_y + 2.5), (CX, hip_y), 3.0, 's', 3.3)
    c.ellipse((CX, sh_y + 2.8), 4.4, 3.2, 't' if not back else 's')
    if back:
        c.capsule((CX - 4.0, sh_y + 3.0), (CX + 4.0, sh_y + 3.0), 1.4, 't')
    else:
        c.capsule((CX - 1.6, sh_y - 0.4), (CX - 1.2, sh_y + 1.0), 0.55, 't')
        c.capsule((CX + 1.6, sh_y - 0.4), (CX + 1.2, sh_y + 1.0), 0.55, 't')
    c.ellipse((CX, hip_y + 0.6), 4.9, 3.1, 'y')
    c.capsule((CX - 4.6, hip_y - 1.8), (CX + 4.6, hip_y - 1.8), 0.55, 'Y')
    for fx in range(-5, 6):
        if fx % 2 == 0:
            c.px(CX + fx, hip_y + 3.7, 'Y')
    for sx in (-1, 1):
        _limb(c, (CX + 4.4 * sx, sh_y + 1.0), -7 * sx, 6.0, -5 * sx, 5.6, 1.45, 1.15, 's')
    c.capsule((CX, sh_y - 2.0), (CX, sh_y + 0.4), 1.3, 's')
    if back:
        c.ellipse((hx, hy), 3.9, 4.2, 'h')
        for i in range(10):                                         # hair down the back
            t = i / 9.0
            c.ellipse((CX + math.sin(t * 5) * 0.6, hy + 2 + t * 12), 4.6 - t * 1.4, 2.2, 'h')
    else:
        c.ellipse((hx, hy), 3.7, 4.1, 's')
        c.ellipse((hx, hy - 2.4), 3.9, 2.0, 'h', clip=lambda x, y: y < hy - 1.0)
        c.capsule((hx - 3.4, hy - 1.5), (hx - 3.6, hy + 4.0), 1.2, 'h')
        c.capsule((hx + 3.4, hy - 1.5), (hx + 3.6, hy + 4.0), 1.2, 'h')
        for ex in (-1.6, 1.0):
            c.px(hx + ex, hy - 0.2, 'w')
            c.px(hx + ex + 0.9, hy - 0.2, 'k')
            c.px(hx + ex + 0.9, hy + 0.8, 'k')
        c.px(hx - 0.6, hy + 2.6, 'l')
        c.px(hx + 0.4, hy + 2.6, 'l')
        for bx in (-1.6, -0.5, 0.6, 1.7):
            c.px(CX + bx, sh_y + 0.3 + (0.5 if abs(bx) < 1 else 0), 'b')
        c.px(hx - 3.8, hy + 1.4, 'o')
        c.px(hx + 3.6, hy + 1.4, 'o')
    _hat(c, hx, hy, 0.0, back=back)
    c.outline()
    return c.rows()


def render(rows, scale=1):
    img = palette.auto_shade(rows, MAT, rate=0.45, lit=0.9, dark=0.8)
    palette.selective_outline(img)          # in place
    if scale != 1:
        img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    return img


def mirror(rows):
    return [r[::-1] for r in rows]
