#!/usr/bin/env python3
"""The ramp hue audit — phase C, docs/plan-art-motion.md.

A pixel-art rule of thumb that `palette.py`'s ramps have never been checked
against: **shadows shift cool, highlights shift warm**. A ramp that only gets
darker or lighter without rotating its hue reads as one colour under a dimmer
— flat, like a brightness slider rather than like light actually falling on a
material. A ramp that rotates the *wrong* way (warmer in the shadow, cooler on
the highlight) reads as actively wrong the moment you look for it.

This is a measurement, not an opinion: every step is converted to HSV, and
each ramp is scored by whether its darkest step sits closer to a reference
*cool* hue (240 degrees, blue) than its brightest step does, and whether its
brightest step sits closer to a reference *warm* hue (45 degrees, amber) than
its darkest step does. Both have to hold, and the total hue rotation has to
clear a small floor — a ramp that drifts a tenth of a degree "passes" the
directional test by not failing it, which is not the same as having been lit.

Run standalone:

    tools/art/ramp_audit.py             prints the table and the verdict

There is no `--apply`: nothing here writes to `palette.py`. A flagged ramp is
fixed by hand, directly in `RAMPS`, the same conservative way the audit itself
was used to fix `stone` — small, deliberate moves on the steps the table
names, re-run through this script until the verdict clears. Automating the
edit was considered and rejected: ramps are read by this project in dozens of
places well beyond art generation (data/ambience.json tints, the palette
manifest, `assets/palette.json`), each ramp carries a hand-written comment
explaining its role, and a script that rewrites RAMPS in place would have to
reproduce both — the source of truth stays one plain dict a person edits.
"""
import colorsys
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from art.palette import RAMPS  # noqa: E402

WARM_HUE = 45.0 / 360.0   # amber
COOL_HUE = 240.0 / 360.0  # blue
MIN_DRIFT_DEG = 4.0       # below this, a ramp is "merely darkening"


def _hsv(rgb):
    r, g, b = (c / 255.0 for c in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h, s, v


def _hue_dist(a, b):
    """Shortest distance between two hues on the colour wheel, in turns (0..0.5)."""
    d = abs(a - b) % 1.0
    return min(d, 1.0 - d)


def _circular_drift_deg(h0, h1):
    """Signed shortest rotation from h0 to h1, in degrees (-180..180]."""
    d = (h1 - h0 + 0.5) % 1.0 - 0.5
    return d * 360.0


def audit_ramp(name):
    steps = RAMPS[name]
    hues = [_hsv(c)[0] for c in steps]
    lo, hi = hues[0], hues[-1]
    drift = _circular_drift_deg(lo, hi)
    # "closer to cool" / "closer to warm", shadow vs highlight.
    shadow_cooler = _hue_dist(lo, COOL_HUE) < _hue_dist(hi, COOL_HUE)
    highlight_warmer = _hue_dist(hi, WARM_HUE) < _hue_dist(lo, WARM_HUE)
    flat = abs(drift) < MIN_DRIFT_DEG
    flagged = flat or not (shadow_cooler and highlight_warmer)
    return {
        "name": name,
        "hues_deg": [round(h * 360.0, 1) for h in hues],
        "shadow_hue": round(lo * 360.0, 1),
        "highlight_hue": round(hi * 360.0, 1),
        "drift_deg": round(drift, 1),
        "shadow_cooler": shadow_cooler,
        "highlight_warmer": highlight_warmer,
        "flat": flat,
        "flagged": flagged,
    }


def print_table():
    rows = [audit_ramp(n) for n in sorted(RAMPS)]
    print("%-10s %8s %8s %9s  %-11s %-14s  %s"
          % ("ramp", "shadow", "highlt", "drift", "shadow->cool", "highlt->warm", "verdict"))
    for r in rows:
        verdict = "FLAGGED (merely darkens)" if r["flat"] else (
            "FLAGGED (wrong direction)" if r["flagged"] else "ok")
        print("%-10s %7.1f° %7.1f° %8.1f°  %-11s %-14s  %s"
              % (r["name"], r["shadow_hue"], r["highlight_hue"], r["drift_deg"],
                 str(r["shadow_cooler"]), str(r["highlight_warmer"]), verdict))
    flagged = [r["name"] for r in rows if r["flagged"]]
    print()
    print("%d/%d ramps flagged: %s" % (len(flagged), len(rows), ", ".join(flagged) or "none"))
    return rows


if __name__ == "__main__":
    print_table()
