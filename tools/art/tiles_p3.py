"""Kaya Refit phase 3: the tile pass.

Kaya is 40 px now and modelled — lit by `auto_shade`, inked by the selective
outline. The tiles under her were authored for a 16 px hero, and next to her
their edges are the weakest thing on the screen: a top face lifts one ramp step,
an underside drops one, and at 1x neither reads as an edge. So this module does
three things, all of them on top of what `tiles.py` already paints, and none of
them anywhere near collision (a tile's id, size and flags never change):

  * **the refit rim** — absolute rather than relative edge light. An exposed top
    gets a lip on a named ramp step with sparse glints above it, an exposed
    underside goes to the bottom of its ramp, the shadow cheek drops a step,
    and a convex corner is chipped. Absolute steps are the point: a relative
    +1 on a textured fill moves noise to brighter noise, which is why the
    phase C course is invisible at 1x.
  * **accent paintings** — extra paintings of the commonest exposed cases (a
    floor top, a one-tile-thick strip) carrying one discrete thing each: a
    pebble, a tuft, a chip out of the lip. Rarer than the plain ones, so a long
    floor gets an event every few tiles instead of a stamp.
  * **contact shadows** — a small sheet of ink at partial alpha that the
    foreground renderer lays into empty cells under and beside solid ground,
    wherever there is a background tile to receive it. See
    `src/world/tile_variants.gd::contact_bits()`.

Light is from the upper left, as everywhere else in tools/art.
"""
import random

from PIL import Image

from .palette import INK, RAMPS, put

TS = 16
BIT_N, BIT_NE, BIT_E, BIT_SE = 1, 2, 4, 8
BIT_S, BIT_SW, BIT_W, BIT_NW = 16, 32, 64, 128


def step_at(img, x, y, ramp):
    """Ramp-step index at (x, y), or None if the pixel is not on that ramp."""
    c = img.getpixel((x, y))
    if c[3] == 0:
        return None
    for i, s in enumerate(RAMPS[ramp]):
        if tuple(s) == c[:3]:
            return i
    return None


def _clamp(i):
    return max(0, min(len(RAMPS["stone"]) - 1, i))


# ------------------------------------------------------------------ the rim
#: Per material: the ramp the lip is painted on, the step of the lip itself,
#: the glint chance on the lip, the step the underside drops to, and whether a
#: convex corner is chipped. The lip step is chosen per world against its own
#: fill, so a dark world's lip is dark too — it only has to beat its own body,
#: never Kaya. `cap` marks materials whose top is painted by their own builder
#: (sod, algae, sun crust, deeps crust, hot glass): those keep their cap and
#: only get glints on it.
RIM = {
    "earth":   dict(ramp="dirt", lip=5, glint=0.22, under=0, chip=True),
    "stone":   dict(ramp="stone", lip=5, glint=0.30, under=0, chip=True),
    "ruin":    dict(ramp="stone", lip=5, glint=0.26, under=0, chip=True),
    "heights": dict(ramp="dirt", lip=5, glint=0.20, under=0, chip=True),
    "deeps":   dict(ramp="dirt", lip=5, glint=0.18, under=0, chip=True),
    "nest":    dict(ramp="stone", lip=3, glint=0.16, under=0, chip=True,
                    glint_ramp="purple", glint_step=5),
}

#: Glints on a capped top — the cap is already the brightest thing on the
#: tile, so the glint is a single step above it on the cap's own ramp.
CAP_GLINT = {
    2: ("grass", 6, 0.30),
    4: ("cloth", 5, 0.18),
    221: ("water", 6, 0.12),
    241: ("metal", 6, 0.20),
    261: ("dirt", 5, 0.25),
    281: ("ember", 6, 0.22),
}


def refit_rim(img, mask, group, tid, rnd):
    """The refit's edge treatment for one blob case of one standable material.

    Runs after `tiles.paint_edges()` has painted the material's own rim and the
    phase C course, so it only ever *sets* the outermost row or column to a
    named step. A step is never relative here; see the module docstring."""
    spec = RIM.get(group)
    if spec is None:
        return
    ramp = spec["ramp"]
    open_n = not mask & BIT_N
    open_s = not mask & BIT_S
    open_w = not mask & BIT_W
    open_e = not mask & BIT_E
    if open_n:
        cap = CAP_GLINT.get(tid)
        if cap is not None:
            gramp, gstep, chance = cap
            for x in range(TS):
                if rnd.random() < chance:
                    put(img, x, 0, gramp, gstep)
        else:
            lip = spec["lip"]
            for x in range(TS):
                put(img, x, 0, ramp, lip)
                # The second row is the face turning away from the sun: one
                # step down, everywhere, and then a step of shadow under it
                # where the fill was brighter — the lip has a thickness.
                put(img, x, 1, ramp, lip - 1)
                i = step_at(img, x, 2, ramp)
                if i is not None and i >= lip - 1:
                    put(img, x, 2, ramp, lip - 2)
            gramp = spec.get("glint_ramp", ramp)
            gstep = spec.get("glint_step", _clamp(spec["lip"] + 1))
            x = 0
            while x < TS:
                if rnd.random() < spec["glint"]:
                    run = 1 + rnd.randrange(3)
                    for k in range(run):
                        if x + k < TS:
                            put(img, x + k, 0, gramp, gstep)
                    x += run + 1
                else:
                    x += 1
    if open_s:
        for x in range(TS):
            put(img, x, TS - 1, ramp, spec["under"])
            i = step_at(img, x, TS - 2, ramp)
            if i is not None and i > spec["under"] + 1:
                put(img, x, TS - 2, ramp, i - 1)
    if open_e:
        for y in range(TS):
            i = step_at(img, TS - 1, y, ramp)
            if i is not None and i > 0:
                put(img, TS - 1, y, ramp, i - 1)
    if open_w:
        for y in range(1 if open_n else 0, TS):
            i = step_at(img, 0, y, ramp)
            if i is not None and i < spec["lip"]:
                put(img, 0, y, ramp, i + 1)
    if spec["chip"]:
        # A one-pixel chip off every convex corner: the cheapest thing that
        # stops a block reading as a stamped rectangle. Visual only — the
        # collision box is the whole cell and always was.
        clear = (0, 0, 0, 0)
        if open_n and open_w:
            img.putpixel((0, 0), clear)
        if open_n and open_e:
            img.putpixel((TS - 1, 0), clear)
        if open_s and open_w:
            img.putpixel((0, TS - 1), clear)
        if open_s and open_e:
            img.putpixel((TS - 1, TS - 1), clear)


# ------------------------------------------------------------- the accents
# One discrete thing per accent painting, sat on or just under the top face.
# Each is lit from the upper left like everything else: a lit pixel up-left,
# a shadow pixel down-right.
def _pebble(img, rnd, ramp, base, y0=0):
    """A stone sitting in the top face: a lit crown on the lip, a body, and a
    dark seat under it — three rows, so it survives 1x."""
    x = 2 + rnd.randrange(TS - 7)
    w = 3 + rnd.randrange(2)
    for k in range(w):
        put(img, x + k, y0, ramp, min(6, base + 1))
        put(img, x + k, y0 + 1, ramp, base)
        put(img, x + k, y0 + 2, ramp, max(0, base - 1))
    put(img, x, y0, ramp, min(6, base + 2))
    put(img, x + 1, y0, ramp, min(6, base + 2))
    for k in range(-1, w + 1):
        put(img, x + k, y0 + 3, ramp, 0)
    put(img, x + w, y0 + 1, ramp, 0)
    put(img, x + w, y0 + 2, ramp, 0)


def _chip(img, rnd, ramp, lip):
    """A bite out of the lip: the course stops, the broken face below is in
    shadow, and the far side of the break catches the light."""
    x = 2 + rnd.randrange(TS - 7)
    w = 3 + rnd.randrange(2)
    for k in range(w):
        put(img, x + k, 0, ramp, 0)
        put(img, x + k, 1, ramp, 1)
        if 0 < k < w - 1:
            put(img, x + k, 2, ramp, 1)
    put(img, x + w, 0, ramp, min(6, lip + 1))
    put(img, x + w, 1, ramp, lip)


def _crack_down(img, rnd, ramp, depth=7):
    x = 3 + rnd.randrange(TS - 6)
    for y in range(0, depth):
        put(img, x, y, ramp, 0)
        if x + 1 < TS:
            put(img, x + 1, y, ramp, 4)
        x = max(1, min(TS - 2, x + rnd.choice((-1, 0, 0, 1))))


def _flower(img, rnd):
    x = 3 + rnd.randrange(TS - 7)
    for y in range(1, 5):
        put(img, x, y, "grass", 3)
    put(img, x, 5, "dirt", 0)
    for dx, dy, st in ((0, 0, 6), (-1, 0, 5), (1, 0, 5), (0, -1, 6), (0, 1, 4)):
        put(img, x + dx, max(0, 1 + dy), "gold", st)


def _glass_glint(img, rnd):
    """A conchoidal flake on the glass: a bright edge with its scoop in shadow."""
    x = 2 + rnd.randrange(TS - 7)
    for k in range(5):
        put(img, x + k, k // 2, "purple", 6 if k < 2 else 5)
        put(img, x + k, k // 2 + 1, "stone", 0)


def _ember_seam(img, rnd):
    x = 2 + rnd.randrange(TS - 7)
    for k in range(5):
        put(img, x + k, 1 + (k % 2), "ember", 6 if k == 2 else 5)
        put(img, x + k, 2 + (k % 2), "ember", 2)


def _root_nub(img, rnd):
    """A root breaking the surface: a lit hump with its own shadow."""
    x = 3 + rnd.randrange(TS - 8)
    for k in range(5):
        top = 0 if 1 <= k <= 3 else 1
        put(img, x + k, top, "wood", 5 if k < 3 else 4)
        put(img, x + k, top + 1, "wood", 3)
        put(img, x + k, top + 2, "wood", 0)


#: group -> accent painters, cycled over the accent paintings in order.
ACCENTS = {
    "earth":   [lambda i, r: _pebble(i, r, "stone", 4),
                lambda i, r: _crack_down(i, r, "dirt")],
    "stone":   [lambda i, r: _chip(i, r, "stone", 5),
                lambda i, r: _crack_down(i, r, "stone")],
    "ruin":    [lambda i, r: _chip(i, r, "stone", 5),
                lambda i, r: _crack_down(i, r, "stone", 5)],
    "heights": [lambda i, r: _pebble(i, r, "stone", 4),
                lambda i, r: _chip(i, r, "dirt", 5)],
    "deeps":   [_root_nub,
                lambda i, r: _pebble(i, r, "dirt", 3)],
    "nest":    [_glass_glint, _ember_seam],
}
#: The capped materials get accents that belong on their caps.
CAP_ACCENTS = {
    2: [_flower, lambda i, r: _pebble(i, r, "stone", 4, y0=6)],
    241: [lambda i, r: _pebble(i, r, "stone", 4, y0=2),
          lambda i, r: _chip(i, r, "metal", 5)],
    261: [_root_nub, lambda i, r: _pebble(i, r, "dirt", 3, y0=2)],
    281: [_ember_seam, _glass_glint],
}


def accent(img, group, tid, k, seed):
    """Paint the k-th accent of a material onto an already edged tile."""
    painters = CAP_ACCENTS.get(tid) or ACCENTS.get(group)
    if not painters:
        return
    painters[k % len(painters)](img, random.Random(seed))


# ------------------------------------------------------ the inked objects
# The legibility sheet (tools/p3_tiles_legend.py) measured the ladders 12-24
# luma off their walls and the Nest's shards 18 — a climbable or a hazard as
# quiet as the wall it hangs on. The fix is the 40 px Kaya's own language:
# she is inked and the scenery is not, so every tile a player has to *act* on
# — climb it, land on it, avoid it — is inked too. A one-step lift on its own
# ramp, then a 1 px ink halo wherever its silhouette meets empty cell. Solid
# ground and walls stay un-inked, which is what keeps "thing" apart from
# "place".
LADDERS = (6, 229, 248, 268, 288)
ONE_WAYS = (5, 19, 226, 246, 266, 286)
HAZARDS = (9, 227, 247, 267, 287)
INKED = frozenset(LADDERS + ONE_WAYS + HAZARDS)


def _lookup():
    out = {}
    for name, steps in RAMPS.items():
        for i, c in enumerate(steps):
            out[tuple(c)] = (name, i)
    return out


_LOOKUP = _lookup()


def ink_interactive(img):
    """In place: lift every ramp pixel one step, then ink the silhouette."""
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            if p[3] == 0:
                continue
            key = _LOOKUP.get(p[:3])
            if key is None:
                continue
            ramp, i = key
            if i < len(RAMPS[ramp]) - 1:
                px[x, y] = tuple(RAMPS[ramp][i + 1]) + (p[3],)
    halo = []
    for y in range(h):
        for x in range(w):
            if px[x, y][3] != 0:
                continue
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    q = px[nx, ny]
                    if q[3] != 0 and q[:3] != INK:
                        halo.append((x, y))
                        break
    for x, y in halo:
        px[x, y] = INK + (255,)
    return img


# ------------------------------------------------------- contact shadows
#: The cells of assets/tiles/contact_shadow.png, in order. `n` is cast down
#: from a solid above, `w` sideways from a solid to the left, `nw` is the
#: corner a solid up-left throws when neither side neighbour is solid, `s` and
#: `e` are the ambient occlusion where a background meets ground below it or a
#: wall to its right. Light is upper-left, so the cast pair is deep and the
#: occlusion pair is shallow.
SHADOW_CELLS = ("n", "w", "nw", "s", "e")
#: Alpha per pixel row/column of depth into the receiving cell.
SHADOW_DEPTH = {
    "n": (0.62, 0.44, 0.28, 0.14),
    "w": (0.50, 0.30, 0.14),
    "s": (0.34, 0.16),
    "e": (0.22, 0.08),
}
#: The corner falloff: alpha by Manhattan distance from the corner pixel.
SHADOW_CORNER = (0.52, 0.34, 0.18, 0.08)


def contact_shadow_sheet():
    img = Image.new("RGBA", (TS * len(SHADOW_CELLS), TS), (0, 0, 0, 0))
    for c, name in enumerate(SHADOW_CELLS):
        ox = c * TS
        for y in range(TS):
            for x in range(TS):
                a = 0.0
                if name == "n" and y < len(SHADOW_DEPTH["n"]):
                    a = SHADOW_DEPTH["n"][y]
                elif name == "w" and x < len(SHADOW_DEPTH["w"]):
                    a = SHADOW_DEPTH["w"][x]
                elif name == "s" and TS - 1 - y < len(SHADOW_DEPTH["s"]):
                    a = SHADOW_DEPTH["s"][TS - 1 - y]
                elif name == "e" and TS - 1 - x < len(SHADOW_DEPTH["e"]):
                    a = SHADOW_DEPTH["e"][TS - 1 - x]
                elif name == "nw" and x + y < len(SHADOW_CORNER):
                    a = SHADOW_CORNER[x + y]
                if a > 0.0:
                    img.putpixel((ox + x, y), INK + (int(round(a * 255)),))
    return img


def contact_shadow_manifest():
    return {
        "_comment": ("Kaya Refit phase 3. Ink at partial alpha, laid by the "
                     "foreground renderer into an empty foreground cell with "
                     "a background tile behind it, on the sides where static "
                     "solid ground touches it. Drawing only; collision never "
                     "sees it."),
        "texture": "res://assets/tiles/contact_shadow.png",
        "cells": {name: i for i, name in enumerate(SHADOW_CELLS)},
    }


# ------------------------------------------------------------ heights air
def _patch(img, ramp, step, cx, cy, rx, ry):
    """A crisp elliptical patch on one whole ramp step, wrapped across the
    cell edges so the fill tiles. Whole steps on purpose: a fractional level
    resolves through the Bayer matrix, and a checkerboard over a screen of
    flat fill is the most visible thing on it (tiles.t_heights_air)."""
    for y in range(TS):
        for x in range(TS):
            for ox in (-TS, 0, TS):
                for oy in (-TS, 0, TS):
                    nx = (x - cx - ox) / rx
                    ny = (y - cy - oy) / ry
                    if nx * nx + ny * ny <= 1.0:
                        put(img, x, y, ramp, step)


def t_heights_air_refit(seed):
    """THERMAL HEIGHTS' gallery fill, re-valued for the 40 px Kaya.

    It was `metal` 5 (luma 177, saturation 0.09, warm), and under heights'
    gold ambient tint that lands at luma ~144: the same value and the same
    hue family as her straw hat, and measured (tools/p3_tiles_sheets.py
    kaya) the hat stood 4-40 luma above it. It now sits on `stone` 4, cool
    (saturation 0.12), with paler `stone` 5 wind streaks, and the hat stands
    clear of it in value and far clear of it in saturation, while the wall
    stays paler than the warm rock in front of it, so solid still reads as
    solid. A first pass on `stone` 5 only got the run frame to +28.
    """
    rnd = random.Random(seed)
    img = Image.new("RGBA", (TS, TS), (0, 0, 0, 255))
    for y in range(TS):
        for x in range(TS):
            put(img, x, y, "stone", 4)
    # Haze as thin wind streaks rather than blots: a streak reads as air
    # moving across the gallery, a blot as camouflage paint.
    for _ in range(2):
        _patch(img, "stone", 5, rnd.uniform(0, TS), rnd.uniform(0, TS),
               rnd.uniform(2.5, 4.0), 0.75)
    for _ in range(4):
        put(img, rnd.randrange(TS), rnd.randrange(TS), "stone", 3)
    return img


def t_heights_cloud_refit(seed):
    """The cloud accent, re-valued with the air it floats in. A cloud is the
    brightest thing in the gallery, so its cores reach `stone` 6, but its body
    sits on `stone` 5 over a `stone` 3 underside and never on white."""
    rnd = random.Random(seed)
    img = t_heights_air_refit(seed + 7)
    for _ in range(3):
        cx, cy = rnd.uniform(0, TS), rnd.uniform(0, TS)
        rx, ry = rnd.uniform(3.0, 4.5), rnd.uniform(1.6, 2.4)
        _patch(img, "stone", 3, cx + 1, cy + 1, rx, ry)
        _patch(img, "stone", 5, cx, cy, rx, ry)
        _patch(img, "stone", 6, cx - 1, cy - 1, rx * 0.5, ry * 0.5)
    return img
