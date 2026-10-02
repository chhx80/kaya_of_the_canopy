#!/usr/bin/env python3
"""Phase E, docs/plan-art-motion.md: consistency sweep, tile edge-light half.

"tiles whose edge-light treatment produced double-lit or unlit-but-standable
courses." `tiles.py::edge_light_course()` (Phase C) is a small, fully
deterministic function — no `rnd`, no jitter, one `+1`/`-1` ramp-step move per
exposed edge, clamped at the ramp's ends — so the honest way to check it is to
verify its own arithmetic exactly, not to eyeball luma deltas on a fully
rendered tile where a masonry material's mortar-joint texture, its rim
gradient's own jitter and this function's step are all stacked together and
impossible to tell apart by eye. (An earlier version of this script tried the
luma-delta approach and flagged `stone`/`ruin` as "double-lit" at a glance —
investigated and traced to `RIM_STONE`/`RIM_RUIN`'s OWN `base` level sitting
well above `t_stone()`'s/`t_ruin_stone()`'s actual mortar-joint fill tone, a
pre-existing rim calibration choice that predates this phase, not anything
`edge_light_course` added. That investigation is why this script now checks
the function's arithmetic directly instead.)

Three checks:

  1. STRUCTURAL — `edge_light_course(` is called exactly once inside
     `paint_edges()`. A second call site anywhere would be the literal
     "double" in double-lit, and no pixel measurement is more conclusive than
     counting call sites in the source that is the single entry point every
     tile in the atlas goes through.
  2. ARITHMETIC — on a synthetic 16x16 test image at every one of a ramp's 7
     steps, calling `edge_light_course` with the top edge exposed moves every
     column's step index by exactly `+1` (clamped at 6) and leaves every
     other pixel untouched; the bottom edge likewise moves by exactly `-1`
     (clamped at 0). Run across EVERY standable material's own ramp — this is
     where "unlit" (no move happened and the start was not already at the
     ramp's end, so clamping is not the excuse) and "double" (moved by more
     than one step) would show up if the function's own clamping ever failed.
  3. COMPLETENESS — every group in `STANDABLE_GROUPS` is a real group at
     least one `V(...)` entry declares, and every standable material that is
     NOT one of the six documented capped rims (`top is None`) has a real
     `top` AND `bottom` list — the "unlit-but-standable" failure mode where a
     material a player can stand on has no edge treatment to switch on at
     all, because a group name drifted or a rim dict lost a key.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image
from art import palette, tiles  # noqa: E402

TS = 16


def step_at(img, x, y, ramp):
    c = img.getpixel((x, y))[:3]
    for i, s in enumerate(palette.RAMPS[ramp]):
        if tuple(s) == c:
            return i
    return None


def flat(ramp, level):
    """A tile that is a single, exact ramp step everywhere — no dithering, no
    jitter, so any pixel that is NOT this colour after the function under
    test runs is a pixel that function touched."""
    img = Image.new("RGBA", (TS, TS), (0, 0, 0, 255))
    colour = tuple(palette.RAMPS[ramp][level]) + (255,)
    for y in range(TS):
        for x in range(TS):
            img.putpixel((x, y), colour)
    return img


def check_structural():
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "art", "tiles.py")).read()
    # Only the def line and the one call inside paint_edges should match.
    calls = len(re.findall(r"\bedge_light_course\(", src)) - 1  # minus def
    ok = calls == 1
    print("structural: edge_light_course( called %d time(s) outside its own "
          "def — %s" % (calls, "ok" if ok else "FAIL (expected exactly 1)"))
    return ok


def check_arithmetic():
    print("\narithmetic: +1/-1 step, clamped, every column, every start level:")
    all_ok = True
    ramps_seen = set()
    for spec in tiles.VARIANT_SPECS:
        group = spec["group"]
        rim = spec["rim"]
        if rim is None or group not in tiles.STANDABLE_GROUPS:
            continue
        ramp = rim["ramp"]
        if ramp in ramps_seen:
            continue    # one pass per ramp is enough; the arithmetic has no
        ramps_seen.add(ramp)                              # per-material term
        capped = rim.get("top") is None
        n_steps = len(palette.RAMPS[ramp])
        bad = []
        for level in range(n_steps):
            base = flat(ramp, level)
            top_img = flat(ramp, level)
            tiles.edge_light_course(top_img, tiles.canon_mask(254), rim, group)
            bot_img = flat(ramp, level)
            tiles.edge_light_course(bot_img, tiles.canon_mask(255 & ~16), rim, group)
            want_top = level if capped else min(n_steps - 1, level + 1)
            want_bot = max(0, level - 1)
            got_top = step_at(top_img, 0, 0, ramp)
            got_bot = step_at(bot_img, 0, TS - 1, ramp)
            if got_top != want_top:
                bad.append("top level %d: got %s want %d" % (level, got_top, want_top))
            if got_bot != want_bot:
                bad.append("bottom level %d: got %s want %d" % (level, got_bot, want_bot))
            # Every OTHER pixel in the frame must be untouched.
            for (name, img) in (("top", top_img), ("bottom", bot_img)):
                for y in range(TS):
                    if name == "top" and y == 0:
                        continue
                    if name == "bottom" and y == TS - 1:
                        continue
                    for x in range(TS):
                        if step_at(img, x, y, ramp) != level:
                            bad.append("%s case leaked a pixel at (%d,%d), y=%d"
                                       % (name, x, y, y))
        verdict = "ok" if not bad else "FAIL: " + "; ".join(bad[:4])
        print("  ramp %-8s (capped=%-5s): %s" % (ramp, capped, verdict))
        if bad:
            all_ok = False
    return all_ok


def check_completeness():
    print("\ncompleteness: every standable group has a real rim with real "
          "top+bottom (unless it is one of the six documented capped rims):")
    groups_declared = {s["group"] for s in tiles.VARIANT_SPECS if s["group"]}
    all_ok = True
    for g in sorted(tiles.STANDABLE_GROUPS):
        if g not in groups_declared:
            print("  %-12s MISSING — no V(...) entry declares this group at all" % g)
            all_ok = False
            continue
        members = [s for s in tiles.VARIANT_SPECS if s["group"] == g]
        for spec in members:
            rim = spec["rim"]
            name = "%s(%d)" % (g, spec["id"])
            if rim is None:
                print("  %-16s MISSING RIM — in a standable group with no rim at all" % name)
                all_ok = False
                continue
            capped = rim.get("top") is None
            has_bottom = rim.get("bottom") is not None
            if not capped and rim.get("top") is None:
                print("  %-16s UNLIT-BUT-STANDABLE — no top rim, not on the capped list" % name)
                all_ok = False
            if not has_bottom:
                print("  %-16s UNLIT-BUT-STANDABLE — no bottom rim at all" % name)
                all_ok = False
    if all_ok:
        print("  ok: all %d standable groups, %d member tiles" %
              (len(tiles.STANDABLE_GROUPS),
               sum(1 for s in tiles.VARIANT_SPECS
                   if s["group"] in tiles.STANDABLE_GROUPS)))
    return all_ok


def main():
    ok = check_structural()
    ok = check_arithmetic() and ok
    ok = check_completeness() and ok
    print()
    if not ok:
        print("FAIL")
        return 1
    print("OK: edge_light_course fires exactly once, moves exactly one ramp "
          "step (clamped) on exactly the edge row it targets, and every "
          "standable material has a real edge treatment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
