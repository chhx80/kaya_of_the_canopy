"""Kaya's three animal forms, redrawn to stand next to the 40 px Kaya.

The old frog, fish and bird were 16x16 hand-written grids from the first art
pass. Beside the 40 px puppet (tools/art/kaya40.py) they read as somebody else's
animals, so they are rebuilt the way she is: parts placed by coordinates,
rasterised into the character-grid format, inked, then lit by `auto_shade` with
her own settings and outlined by the sheet's selective outline.

Each one is HER, transformed, and carries her outfit so a player never wonders
whose frog that is:

  * frog -- her green top as the skin, her yellow shorts as the throat and
    belly, the bead necklace at the throat, and her straw hat, shrunk, between
    the eyes;
  * fish -- yellow body (the shorts), green back and fins (the top), the beads
    as a gill line, and the little hat riding on its head;
  * bird -- green body, yellow breast, red feet for the sandals, her long dark
    hair as the tail plumes, and the hat.

Collision does not change, so the drawing has to live with a small hitbox
(frog 12x11, fish 14x9, bird 12x9). Rules every frame keeps, asserted in
`frames_*()` and again by tests/test_forms40.gd against the shipped sheets:

  * nothing below the hitbox -- the feet ARE its bottom row (a frog on a floor,
    a beached fish, a perched bird all have rock right there);
  * at most `MAX_RISE` px above it, so every form still fits a one-tile (16 px)
    tunnel with the pixel of rounding spare kaya40 keeps for the same reason;
  * the frog's cling frames draw nothing outside the hitbox's columns, because
    a wall is flush with it there.

Sideways overhang past a wall, and a rise under a low ceiling while airborne,
are handled the way they are for her: the generator writes a `.bounds.json`
beside each sheet and the form's `pose` block hands it to src/player/kaya_pose.gd,
which nudges the drawn frame off the rock. tools/clipgate.sh --all-forms proves
it against every proof tape.
"""

import json
import math
import os

from PIL import Image

from . import palette

# char -> (ramp, base level), the same materials and levels as kaya40.MAT so a
# frog's green is literally the green of her top.
MAT = {
    'g': ("cloth", 2.9), 'G': ("cloth", 1.9),      # her top: skin, back, fins
    'd': ("cloth", 1.4),                            # spots, far limbs' shadow
    'y': ("gold", 5.0), 'Y': ("gold", 3.9),         # her shorts: belly, body
    'a': ("straw", 3.6), 'A': ("straw", 2.4),       # the hat
    'n': ("dirt", 1.8),                             # hat ribbon
    'b': ("ember", 4.8),                            # beads
    'r': ("ember", 3.0), 'R': ("ember", 2.0),       # sandals: bird feet, tongue
    'h': ("hair", 2.6), 'H': ("hair", 1.5),         # her hair: the bird's tail
    'w': ("metal", 6.0),                            # eye white
    'e': ("hair", 1.6),                             # iris
}

# Every form keeps this much headroom spare in a one-tile tunnel: 16 px of
# space, minus the pixel the rounded render position can add (see kaya40's
# STOOP_TOP), minus the hitbox height, is the most a frame may rise above it.
TUNNEL = 16
ROUNDING = 1


class Canvas:
    """kaya40.Canvas with its size as a parameter."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.g = [['.'] * w for _ in range(h)]

    def _set(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = ch

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.g[y][x]
        return '.'

    def capsule(self, a, b, r0, ch, r1=None):
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

    def ellipse(self, c, rx, ry, ch, clip=None, rot=0.0):
        cx, cy = c
        cs, sn = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        rr = max(rx, ry)
        for y in range(int(cy - rr - 1), int(cy + rr + 2)):
            for x in range(int(cx - rr - 1), int(cx + rr + 2)):
                px, py = x + 0.5 - cx, y + 0.5 - cy
                u = px * cs + py * sn
                v = -px * sn + py * cs
                if (u / rx) ** 2 + (v / ry) ** 2 <= 1.0:
                    if clip is None or clip(x + 0.5, y + 0.5):
                        self._set(x, y, ch)

    def poly(self, pts, ch):
        """Filled polygon, pixel centres inside (even-odd)."""
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
            py = y + 0.5
            xs = []
            for i in range(len(pts)):
                (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
                if (y0 <= py < y1) or (y1 <= py < y0):
                    xs.append(x0 + (py - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for a, b in zip(xs[::2], xs[1::2]):
                for x in range(int(math.floor(a)), int(math.ceil(b)) + 1):
                    if a <= x + 0.5 <= b:
                        self._set(x, y, ch)

    def px(self, x, y, ch):
        self._set(int(math.floor(x)), int(math.floor(y)), ch)

    def outline(self):
        out = [row[:] for row in self.g]
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] != '.':
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and self.g[ny][nx] not in '.k':
                        out[y][x] = 'k'
                        break
        self.g = out

    def rows(self):
        return ["".join(r) for r in self.g]


# ------------------------------------------------------------- shared parts
def hat(c, x, y, half=4, tilt=0, under=True):
    """Her straw hat, shrunk to a stamp, because at this size every pixel of it
    is a feature: a two-pixel crown, the dark ribbon, a brim `2*half+1` wide
    with a lit top, and a shadowed underside narrower than the brim. (x, y) is
    the brim's centre pixel. `tilt` 1 cocks the front (+x) end of the brim up a
    pixel and the back end down, the way she tips it."""
    x, y = int(round(x)), int(round(y))
    for i in range(-half, half + 1):
        dy = 0
        if tilt and i >= half - 1:
            dy = -tilt
        elif tilt and i <= -half + 1:
            dy = tilt
        c._set(x + i, y + dy, 'a')
        if under and abs(i) <= half - 2:
            c._set(x + i, y + 1, 'A')
    for i in range(-2, 2):
        c._set(x + i, y - 1, 'n')
    for i in range(-2, 1):
        c._set(x + i, y - 2, 'a')


def eye(c, x, y, shut=False, lash=True, lid=True):
    """Her eye -- the one feature that survives the change, placed pixel by
    pixel as kaya40 places hers: the lid line, a white and a black pupil
    looking forward, and the lash flicking off the lid. (x, y) is the white."""
    x, y = int(round(x)), int(round(y))
    if shut:
        c._set(x, y, 'k')
        c._set(x + 1, y, 'k')
        return
    if lid:
        c._set(x, y - 1, 'k')
        c._set(x + 1, y - 1, 'k')
    if lash:
        c._set(x + 2, y - 2, 'k')
    c._set(x, y, 'w')
    c._set(x + 1, y, 'k')


def cells_of(frames, w, h):
    return [palette.auto_shade(r, MAT, rate=0.45, lit=0.9, dark=0.8) for r in frames]


# ===================================================================== frog
# Cell 24x16, facing right. The 12x11 hitbox is centred at the bottom: columns
# 6-17, rows 5-15, feet on row 15.
FROG_W, FROG_H = 24, 16
FROG_BOX = (6, 5, 12, 11)          # ox, oy, w, h -- data/forms/frog.json


def _frog(body_dy=0.0, tilt=0.0, puff=0.0, shut=False, tongue=0, hind="sit",
          front="sit", hat_tilt=0, head_dy=0.0):
    """A frog in profile, sitting the way a frog sits: rump low over a big
    folded thigh, back sloping up to a head carried high, front legs straight
    under the chin. `body_dy` lowers it all (a crouch), `tilt` rotates the
    body nose-up in degrees, `puff` swells the throat; `hind`/`front` pick the
    leg layout of the beat."""
    c = Canvas(FROG_W, FROG_H)
    by = 10.6 + body_dy
    t = math.radians(-tilt)

    def at(x, y):                      # body-space -> cell, about the hip
        dx, dy = x - 9.0, y - by
        return (9.0 + dx * math.cos(t) - dy * math.sin(t),
                by + dx * math.sin(t) + dy * math.cos(t))
    hx, hy = at(16.4, by - 2.2 + head_dy)
    # far legs, in shadow, behind everything
    if front == "sit":
        c.capsule(at(15.2, by + 0.6), (15.0, 15.0), 0.9, 'd')
    if hind == "sit":
        c.capsule((12.0, 15.0), (14.0, 15.0), 0.6, 'd')
    # torso and head
    c.ellipse(at(11.6, by + 0.2), 6.0, 3.6, 'g', rot=-18.0 - tilt)
    c.ellipse((hx, hy), 3.9, 2.7, 'g', rot=-6.0 - tilt * 0.5)
    # her yellow: the throat, and the belly along the bottom
    c.ellipse((hx - 0.4, hy + 2.0 + puff * 0.3), 3.0 + puff * 0.5, 1.3 + puff * 0.7, 'y',
              clip=lambda px, py: py > hy + 1.0)
    bx, bby = at(11.4, by + 2.6)
    c.ellipse((bx, bby), 4.6, 1.4, 'y', clip=lambda px, py: py > bby - 0.6)
    # spots down the back
    for sx, sy in ((10.0, by - 2.4), (12.6, by - 3.2), (7.4, by - 0.8)):
        c.px(*at(sx, sy), 'd')
    # near hind leg
    if hind == "sit":
        c.ellipse(at(8.6, by + 1.6), 3.6, 2.6, 'g', rot=-25.0)
        c.capsule((6.0, 13.8), (5.6, 15.0), 0.8, 'g')
        c.capsule((5.6, 15.0), (12.6, 15.0), 0.7, 'g')
        c.px(*at(9.6, by + 0.6), 'd')                               # knee crease
    elif hind == "kick":
        c.capsule(at(7.6, by + 0.6), at(3.4, by + 2.4), 1.7, 'g', 1.1)
        c.capsule(at(3.4, by + 2.4), at(0.8, by + 3.6), 1.0, 'g', 0.7)
        c.capsule(at(0.8, by + 3.6), at(-0.6, by + 3.2), 0.6, 'g')
    elif hind == "tuck":
        c.ellipse(at(8.8, by + 1.2), 3.6, 2.6, 'g', rot=-25.0)
        c.capsule(at(6.4, by + 3.2), at(11.6, by + 3.6), 0.7, 'g')
    elif hind == "trail":
        c.capsule(at(7.6, by + 0.8), at(3.6, by + 1.6), 1.6, 'g', 1.0)
        c.capsule(at(3.6, by + 1.6), at(4.6, by + 4.2), 0.9, 'g', 0.7)
    # near front leg
    if front == "sit":
        c.capsule(at(16.2, by + 0.6), (17.2, 14.6), 1.0, 'g', 0.8)
        c.capsule((16.6, 15.0), (19.6, 15.0), 0.6, 'g')
    elif front == "reach":
        c.capsule(at(16.0, by + 1.0), at(19.6, by + 2.6), 0.9, 'g', 0.7)
        c.capsule(at(19.6, by + 2.6), at(21.2, by + 2.4), 0.6, 'g')
    elif front == "down":
        c.capsule(at(16.0, by + 1.0), at(17.4, by + 4.4), 0.9, 'g', 0.7)
        c.capsule(at(17.0, by + 4.4), at(19.2, by + 4.4), 0.6, 'g')
    # the eye bump on the crown, her eye in it; mouth; beads on the throat
    ebx, eby = hx + 1.2, hy - 1.8
    c.ellipse((ebx, eby), 1.9, 1.6, 'g')
    eye(c, ebx - 0.6, eby + 0.2, shut=shut)
    c.capsule((hx - 0.4, hy + 1.0), (hx + 3.2, hy + 0.6), 0.3, 'k')
    for k in range(3):
        c.px(hx - 1.8 + k * 1.4, hy + 2.3 + puff * 0.8, 'b')
    if tongue:
        c.capsule((hx + 3.8, hy + 0.9), (hx + 3.8 + tongue, hy + 1.4), 0.5, 'r')
    # the hat, on the back of the head behind the eye bump
    hat(c, hx - 3.4, hy - 2.4, half=3, tilt=hat_tilt)
    c.outline()
    return c.rows()


# The cling, placed pixel by pixel: twelve columns is the hitbox's width, and at
# that size the eye, the brim and the toes on the rock each need a pixel chosen
# rather than rasterised. Columns 0-11 here are cell columns 6-17.
_CLING = [
    "....kkk.....",
    "...kaaak....",
    "..knnnnnk...",
    ".kaaaaaaak..",
    "kgkwAAAggk..",
    "kgggggggggkk",
    ".kkkkgggdggk",
    "..kbybygggk.",
    "..kyyyyggdgk",
    "..kyyyyyggkk",
    "..kyyyyygggk",
    "...kyyyyggk.",
    "...kyyygggkk",
    "....kkkkkkk.",
]


def _frog_cling(breathe=0):
    """Stuck to a wall in mid-air. The game draws this beat with the frame's
    FRONT to the wall -- the render facing still points the way she leapt; the
    clip gate's tapes show it at both walls, flipped and not -- so the toes are
    on the right-hand edge and the head is turned back over the shoulder to look
    out along the wall. Every pixel, ink included, is inside the hitbox's
    columns: the wall is flush with the hitbox, and should the facing ever catch
    up mid-cling the other side would be the wall. `breathe` swells the belly."""
    rows = [r[:] for r in _CLING]
    if breathe:
        rows[7] = "..kbybyyggk."
        rows[11] = "...kyyyyygk."
    ox = FROG_BOX[0]
    top = FROG_H - len(rows)
    out = ['.' * FROG_W for _ in range(top)]
    for r in rows:
        out.append('.' * ox + r + '.' * (FROG_W - ox - len(r)))
    return out


def _frog_shaft(stretch=False):
    """The frog in a one-tile shaft, where a 16 px gap holds a 12 px hitbox and
    no sideways nudge can clear the leap's legs: drawn from behind and a little
    above, climbing -- legs folded under (or pushed straight down mid-kick),
    arms up, the hat on the back of the head. At most `NARROW_W` px wide, the
    same answer kaya40 gives her with the slung hat."""
    c = Canvas(FROG_W, FROG_H)
    cx = 12.0
    top = 7.2 if stretch else 8.4
    c.ellipse((cx, 11.0 + (0 if stretch else 0.6)), 4.2, 3.6 if not stretch else 4.0, 'g')
    if stretch:                                   # kicked down, toes splayed
        c.capsule((cx - 2.4, 13.0), (cx - 3.4, 15.0), 1.0, 'g', 0.7)
        c.capsule((cx + 2.4, 13.0), (cx + 3.4, 15.0), 1.0, 'g', 0.7)
        c.capsule((cx - 3.0, 9.0), (cx - 5.0, 5.6), 0.8, 'g', 0.6)
        c.capsule((cx + 3.0, 9.0), (cx + 5.0, 5.6), 0.8, 'g', 0.6)
    else:                                         # folded, a ball on the wall-kick
        c.ellipse((cx - 3.6, 13.2), 2.2, 1.8, 'g')
        c.ellipse((cx + 3.6, 13.2), 2.2, 1.8, 'g')
        c.capsule((cx - 3.4, 15.0), (cx - 1.4, 15.0), 0.6, 'g')
        c.capsule((cx + 1.4, 15.0), (cx + 3.4, 15.0), 0.6, 'g')
        c.capsule((cx - 3.4, 10.0), (cx - 5.2, 8.0), 0.8, 'g', 0.6)
        c.capsule((cx + 3.4, 10.0), (cx + 5.2, 8.0), 0.8, 'g', 0.6)
    for sx, sy in ((cx - 1.6, 11.0), (cx + 1.4, 12.4), (cx - 0.2, 13.6)):
        c.px(sx, sy, 'd')                         # spots down the back
    c.ellipse((cx, top), 3.0, 2.2, 'g')           # head, from behind
    c.ellipse((cx - 2.2, top - 1.6), 1.4, 1.2, 'g')
    c.ellipse((cx + 2.2, top - 1.6), 1.4, 1.2, 'g')   # the two eye bumps
    c.px(cx - 1.0, top + 1.6, 'b')
    c.px(cx + 0.6, top + 1.8, 'b')                # the necklace's clasp
    hat(c, cx, top - 0.4, half=3, under=False)
    c.outline()
    return c.rows()


def frog_frames():
    """0 idle, 1 breathe, 2 crouch (also the turn frame), 3 leap (also the
    wall-kick flash), 4 reach, 5 cling, 6 apex tuck, 7 tongue-blink idle,
    8 cling breathe, 9 shaft leap, 10 shaft tuck -- the order
    data/forms/frog.json indexes."""
    return [
        _frog(),
        _frog(puff=1.0),
        _frog(body_dy=1.2, tilt=-6.0, head_dy=0.6),
        _frog(body_dy=-0.2, tilt=14.0, hind="kick", front="reach", hat_tilt=1),
        _frog(body_dy=-0.6, tilt=-14.0, hind="trail", front="down"),
        _frog_cling(),
        _frog(body_dy=-0.6, tilt=6.0, hind="tuck", front="down"),
        _frog(shut=True, tongue=2),
        _frog_cling(breathe=1.0),
        _frog_shaft(stretch=True),
        _frog_shaft(),
    ]


FROG_CLING = (5, 8)
# Frames for a one-tile shaft (added after the original nine, so every index
# frog.json already used still means what it meant).
FROG_NARROW = (9, 10)
NARROW_W = 16


# ===================================================================== fish
# Cell 24x14, facing right. The 14x9 hitbox: columns 5-18, rows 5-13.
FISH_W, FISH_H = 24, 14
FISH_BOX = (5, 5, 14, 9)


def _fish(tail=0.0, mouth=0.0, tilt=0.0, fin=0.0, flop=False):
    """`tail` -1..1 swings the tail fan down..up; `mouth` opens the bite;
    `tilt` rotates the body (degrees, nose up positive)."""
    c = Canvas(FISH_W, FISH_H)
    cx, cy = 12.0, 9.6
    t = math.radians(-tilt)

    def rot(x, y):
        dx, dy = x - cx, y - cy
        return (cx + dx * math.cos(t) - dy * math.sin(t),
                cy + dx * math.sin(t) + dy * math.cos(t))
    # tail fan: green, the base at the peduncle, two lobes
    base = rot(5.0, cy)
    tip_u = rot(1.0, cy - 3.6 - tail * 1.4)
    tip_d = rot(1.0, cy + 3.0 - tail * 1.4)
    notch = rot(2.6, cy - tail * 1.2)
    c.poly([base, tip_u, notch, tip_d], 'G')
    # dorsal fin (green, her top) and the far pectoral
    d0, d1, d2 = rot(8.6, cy - 3.4), rot(11.6, cy - 6.6 - fin), rot(14.0, cy - 3.6)
    c.poly([d0, d1, d2], 'G')
    # body: yellow, nose to the right
    c.ellipse((cx, cy), 7.4, 3.7, 'Y', rot=-tilt)
    c.ellipse(rot(13.0, cy + 1.6), 5.4, 1.8, 'y', rot=-tilt)      # belly
    c.ellipse(rot(11.0, cy - 2.4), 5.6, 1.4, 'g', rot=-tilt)      # green back
    # gill line, her beads along it
    for k, gy in enumerate((-1.6, 0.2, 2.0)):
        gx, gy2 = rot(15.2 - abs(gy) * 0.3, cy + gy)
        c.px(gx, gy2, 'b' if k != 1 else 'R')
    # near pectoral fin
    p0, p1 = rot(13.0, cy + 1.0), rot(10.2 + fin * 0.6, cy + 3.0)
    c.capsule(p0, p1, 0.9, 'g', 0.6)
    # eye and mouth
    ex, ey = rot(16.4, cy - 0.8)
    eye(c, ex, ey, shut=flop)
    if mouth > 0:
        m0 = rot(19.4, cy + 0.4)
        c.capsule(m0, rot(16.6, cy + 0.9), 0.4, 'k')
        c.poly([rot(17.4, cy + 0.6), rot(20.2, cy - 0.8 - mouth),
                rot(20.2, cy + 1.6 + mouth * 0.6)], '.')
        c.px(*rot(18.6, cy + 1.6), 'r')
    else:
        c.capsule(rot(18.6, cy + 1.0), rot(17.4, cy + 1.2), 0.3, 'k')
    # the hat rides on the head, just behind the eye
    hx, hy = rot(14.0, cy - 3.6)
    hat(c, hx, hy, half=3, tilt=1 if tilt > 2 else 0)
    c.outline()
    return c.rows()


def _fish_shaft(curl=0.0):
    """The fish in a one-tile shaft: bent into a C with the tail swept up over
    its back, so it fits 16 px with its hat on. `curl` flicks the tail."""
    c = Canvas(FISH_W, FISH_H)
    cx, cy = 12.0, 9.8
    c.poly([(8.0, cy - 1.0), (6.2 - curl, 4.0), (9.6, 6.0 + curl), (11.0, 3.2 - curl * 0.6)],
           'G')                                              # tail, up over the back
    c.ellipse((cx, cy), 5.6, 3.6, 'Y')
    c.ellipse((cx + 1.2, cy + 1.6), 4.0, 1.7, 'y')
    c.ellipse((cx - 0.6, cy - 2.2), 4.0, 1.3, 'g')
    c.capsule((cx + 1.4, cy + 1.0), (cx - 1.0, cy + 2.8), 0.8, 'g', 0.6)
    c.px(cx + 3.0, cy - 1.0, 'b')
    c.px(cx + 3.0, cy + 1.4, 'b')
    eye(c, cx + 3.6, cy - 0.6)
    c.capsule((cx + 5.0, cy + 1.0), (cx + 4.2, cy + 1.2), 0.3, 'k')
    hat(c, cx + 2.0, cy - 4.0, half=3)
    c.outline()
    return c.rows()


def fish_frames():
    """0-3 the swim beat (tail mid, up, mid, down), 4 bite, 5 flop, 6-7 the
    curled shaft swim -- the order data/forms/fish.json indexes. Facing right, which `facing == 1`
    draws."""
    return [
        _fish(tail=0.0),
        _fish(tail=1.0, fin=0.6),
        _fish(tail=0.2, fin=0.3),
        _fish(tail=-1.0, fin=-0.4),
        _fish(mouth=1.0, tail=-0.4, tilt=4.0),
        _fish(tail=1.0, tilt=-10.0, flop=True),
        _fish_shaft(),
        _fish_shaft(curl=1.0),
    ]


FISH_NARROW = (6, 7)


# ===================================================================== bird
# Cell 24x16, facing right. The 12x9 hitbox: columns 6-17, rows 7-15.
BIRD_W, BIRD_H = 24, 16
BIRD_BOX = (6, 7, 12, 9)


def _bird(wing="fold", feet="perch", tail_dy=0.0, head_dx=0.0, head_dy=0.0,
          body_dy=0.0, tilt_head=0.0, ruffle=False, bank=0):
    c = Canvas(BIRD_W, BIRD_H)
    by = 11.4 + body_dy
    hx, hy = 16.4 + head_dx, 8.0 + head_dy + body_dy
    # tail: her long dark hair, three plumes swept back
    for k, (dy, ln) in enumerate(((-0.6, 7.0), (0.6, 7.8), (1.6, 6.2))):
        a = (9.0, by + dy * 0.5)
        b = (9.0 - ln, by + 1.2 + dy + tail_dy)
        c.capsule(a, b, 1.1 if k == 1 else 0.9, 'H' if k != 1 else 'h', 0.6)
    # far wing behind the body
    if wing in ("up", "mid_up"):
        tip = (8.0, 1.2) if wing == "up" else (5.6, 5.0)
        c.poly([(10.0, by - 2.0), tip, (13.6, by - 2.6)], 'G')
    # feet: the sandals' red
    if feet == "perch":
        c.capsule((11.2, by + 2.4), (11.0, 15.0), 0.6, 'r')
        c.capsule((13.4, by + 2.4), (13.6, 15.0), 0.6, 'R')
        c.capsule((10.4, 15.0), (12.4, 15.0), 0.5, 'r')
        c.capsule((13.2, 15.0), (15.0, 15.0), 0.5, 'R')
    elif feet == "tuck":
        c.capsule((11.6, by + 3.0), (9.8, by + 3.6), 0.6, 'r')
    # body: green, yellow breast
    c.ellipse((12.0, by), 5.0, 3.4, 'g', rot=-12.0)
    c.ellipse((14.0, by + 1.2), 3.0, 2.2, 'y', rot=-20.0)
    # head
    c.ellipse((hx, hy), 2.9, 2.7, 'g')
    c.ellipse((hx + 0.6, hy + 1.8), 1.8, 1.0, 'y', clip=lambda px, py: py > hy + 1.0)
    # beak: straw, short and hooked
    c.poly([(hx + 2.4, hy - 0.4), (hx + 5.0, hy + 0.6 + tilt_head * 0.3),
            (hx + 2.4, hy + 1.6)], 'a')
    c.px(hx + 3.0, hy + 0.8, 'A')
    eye(c, hx + 0.6, hy - 0.2)
    c.px(hx - 0.6, hy + 1.8, 'b')
    c.px(hx + 0.6, hy + 2.6, 'b')                                  # necklace
    # near wing
    if wing == "fold":
        c.ellipse((10.8, by - 0.6), 4.0, 2.0, 'G', rot=-10.0)
        c.capsule((7.6, by + 0.2), (12.8, by - 1.8), 0.5, 'g')
        if ruffle:
            c.px(9.0, by - 1.6, 'g')
    elif wing == "up":
        c.poly([(9.0, by - 1.0), (6.4, 1.0), (9.0, 2.4), (13.4, by - 2.2)], 'g')
        c.capsule((9.2, 2.6), (12.0, by - 2.2), 0.4, 'G')
    elif wing == "mid_up":
        c.poly([(8.6, by - 0.8), (2.4, 4.4), (5.4, 6.6), (13.2, by - 1.8)], 'g')
        c.capsule((3.4, 5.4), (10.0, by - 1.2), 0.4, 'G')
    elif wing == "down":
        c.poly([(9.0, by - 1.4), (13.6, by - 2.2), (11.6, 15.0), (8.4, 14.2)], 'g')
        c.capsule((9.6, by), (9.4, 14.0), 0.4, 'G')
    elif wing == "mid_down":
        c.poly([(8.6, by - 1.2), (13.4, by - 2.0), (5.0, 14.4), (2.6, 12.2)], 'g')
        c.capsule((9.0, by), (4.0, 13.2), 0.4, 'G')
    elif wing == "glide":
        # spread, seen edge-on from the side: a long flat blade over the back
        c.poly([(7.0, by - 1.4), (1.6, by - 3.6 - (0.8 if ruffle else 0.0)),
                (4.0, by - 0.6), (13.6, by - 1.2)], 'g')
        c.poly([(11.0, by - 2.2), (20.6, by - 4.4), (15.0, by - 0.8)], 'G')
        if ruffle:
            c.px(3.0, by - 2.0, 'G')
    elif wing == "bank":
        # banking: the near wing swept down toward us, the far one high
        c.poly([(9.4, by - 1.6), (8.4, 1.6 + bank), (12.6, by - 2.6)], 'G')
        c.poly([(10.0, by), (15.0, by - 1.0), (18.6, 14.0 - bank), (12.0, 14.2)], 'g')
    hat(c, hx - 1.4, hy - 2.6, half=3, tilt=1 if tilt_head else 0)
    c.outline()
    return c.rows()


def bird_frames():
    """0-3 the flap beat (up, mid, down, mid), 4 glide, 5 perch, 6 glide ruffle,
    7 perch head-tilt, 8-9 the banking turn pair -- the order data/forms/bird.json
    indexes."""
    return [
        _bird(wing="up", feet="tuck", tail_dy=-0.6),
        _bird(wing="mid_up", feet="tuck"),
        _bird(wing="down", feet="tuck", tail_dy=0.8, body_dy=-1.0),
        _bird(wing="mid_down", feet="tuck", tail_dy=0.4, body_dy=-0.6),
        _bird(wing="glide", feet="tuck", body_dy=-0.4),
        _bird(),
        _bird(wing="glide", feet="tuck", body_dy=-0.4, tail_dy=0.6, ruffle=True),
        _bird(head_dy=0.6, head_dx=-0.4, tilt_head=1.0, ruffle=True),
        _bird(wing="bank", feet="tuck", bank=0),
        _bird(wing="bank", feet="tuck", bank=2, head_dx=-0.6, tail_dy=0.6),
    ]


# ================================================================== checks
def _opaque(rows):
    return [(x, y) for y, r in enumerate(rows) for x, ch in enumerate(r) if ch != '.']


def check(name, frames, box, wall_frames=(), narrow=()):
    """The rules in the module docstring, on the ASCII before lighting."""
    ox, oy, bw, bh = box
    max_rise = TUNNEL - ROUNDING - bh
    for i, rows in enumerate(frames):
        pts = _opaque(rows)
        assert pts, "%s frame %d is empty" % (name, i)
        bottom = max(y for _, y in pts)
        top = min(y for _, y in pts)
        assert bottom <= oy + bh - 1, "%s frame %d draws below its hitbox (row %d)" % (
            name, i, bottom)
        assert oy - top <= max_rise, "%s frame %d rises %d px, max %d" % (
            name, i, oy - top, max_rise)
    for i in wall_frames:
        xs = [x for x, _ in _opaque(frames[i])]
        assert min(xs) >= ox and max(xs) <= ox + bw - 1, (
            "%s cling frame %d leaves the hitbox columns (%d..%d)" % (name, i, min(xs), max(xs)))
    for i in narrow:
        xs = [x for x, _ in _opaque(frames[i])]
        assert max(xs) - min(xs) + 1 <= NARROW_W, "%s narrow frame %d is %d px wide" % (
            name, i, max(xs) - min(xs) + 1)


def frames_frog():
    f = frog_frames()
    check("frog", f, FROG_BOX, FROG_CLING, FROG_NARROW)
    return f


def frames_fish():
    f = fish_frames()
    check("fish", f, FISH_BOX, (), FISH_NARROW)
    return f


def frames_bird():
    f = bird_frames()
    check("bird", f, BIRD_BOX)
    return f


def frog_cells():
    return cells_of(frames_frog(), FROG_W, FROG_H)


def fish_cells():
    return cells_of(frames_fish(), FISH_W, FISH_H)


def bird_cells():
    return cells_of(frames_bird(), BIRD_W, BIRD_H)


def write_bounds(sheet_path, w, h):
    """Per frame, per row, the first and last opaque column of the SHIPPED sheet
    -- the same file kaya40.write_bounds() writes for her, read by
    src/player/kaya_pose.gd through the form's `pose.bounds`."""
    img = Image.open(sheet_path).convert("RGBA")
    out_frames = []
    for f in range(img.width // w):
        rows = []
        for y in range(h):
            xs = [x for x in range(w) if img.getpixel((f * w + x, y))[3] > 0]
            rows.append([xs[0], xs[-1]] if xs else [-1, -1])
        out_frames.append(rows)
    name = os.path.basename(sheet_path)
    out = {"_comment": "Generated by tools/art/forms40.py from %s. Do not edit." % name,
           "frame_w": w, "frame_h": h, "rows": out_frames}
    path = os.path.splitext(sheet_path)[0] + ".bounds.json"
    with open(path, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
        fh.write("\n")


def preview(path, scale=4):
    """A review sheet: the three forms at `scale`, each over a dark swatch."""
    sets = []
    for name, fn, box, wall, w, h in (
            ("frog", frog_frames, FROG_BOX, FROG_CLING, FROG_W, FROG_H),
            ("fish", fish_frames, FISH_BOX, (), FISH_W, FISH_H),
            ("bird", bird_frames, BIRD_BOX, (), BIRD_W, BIRD_H)):
        fr = fn()
        try:
            check(name, fr, box, wall, {"frog": FROG_NARROW, "fish": FISH_NARROW}.get(name, ()))
        except AssertionError as e:
            print("CHECK:", e)
        sets.append((cells_of(fr, w, h), w, h))
    W = max(len(cs) * (w + 2) for cs, w, _ in sets)
    H = sum(h + 2 for _, _, h in sets)
    img = Image.new("RGBA", (W, H), (0x1c, 0x22, 0x22, 255))
    y = 0
    for cs, w, h in sets:
        strip = Image.new("RGBA", (len(cs) * w, h), (0, 0, 0, 0))
        for i, cimg in enumerate(cs):
            strip.alpha_composite(cimg, (i * w, 0))
        palette.selective_outline(strip)
        for i in range(len(cs)):
            img.alpha_composite(strip.crop((i * w, 0, (i + 1) * w, h)), (i * (w + 2), y))
        y += h + 2
    img.resize((W * scale, H * scale), Image.NEAREST).save(path)
