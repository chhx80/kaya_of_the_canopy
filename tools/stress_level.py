#!/usr/bin/env python3
"""Synthetic large levels for measuring what level SIZE costs (docs/plan-longer-levels.md).

Not shipped: it writes to tests/fixtures/, which LevelLoader.list_levels()
never globs, and the game plays one only when asked by path
(`Game.goto_level("res://tests/fixtures/stress_200x45_jungle.json")`).

    $PYVENV tools/stress_level.py                  # the standard set
    $PYVENV tools/stress_level.py 200 45 deeps     # one

Every size is built by the same code, section by section (one 25-column
screen-width section after another), so a 50x30 and a 200x45 differ in area
and in nothing else per screen: the same density of terrain, background,
emissive tiles, enemies, gems and checkpoints. That is what makes a frame-time
comparison between them a measurement of size.

Each level carries a declared route (spawn -> a mark per section -> exit, via
its checkpoints), so tools/prove.sh --level-file can prove it and
tools/levelstats.sh can measure it: the large-level fixture doubles as the
end-to-end test that the prover and the stats tool work past 120 columns.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_levels import Grid, ROOT          # noqa: E402

OUT = os.path.join(ROOT, "tests", "fixtures")
SEC = 25                                   # columns per section: one screen wide

#: The standard set: the pilot's shape, today's shape, and the dark world's
#: worst case (emissive scan, lantern, shade) at the pilot's shape.
STANDARD = [(200, 45, "jungle"), (50, 30, "jungle"), (200, 45, "deeps"), (50, 30, "deeps")]

#: An emissive tile per world, for the light layer's scan (data/ambience.json
#: gives the deeps fixtures 214, the luminous wall, as an emitter).
GLOW = {"deeps": "O", "jungle": None}


def floor_row(h, s):
    """The walking floor of section `s`: steps of two tiles, up then down, so
    the route climbs and falls and the camera has vertical work to do."""
    base = h - 4
    return base - 2 * (0, 1, 2, 1)[s % 4]


def build(w, h, tileset):
    g = Grid(w, h, tileset=tileset)
    sections = w // SEC
    g.rect(0, 0, w, h, "L", "bg")                      # background everywhere
    g.rect(0, 0, w, 2, "S")                            # ceiling
    g.rect(0, 0, 1, h, "S")
    g.rect(w - 1, 0, 1, h, "S")
    checkpoints = []
    for s in range(sections):
        x0 = s * SEC
        fy = floor_row(h, s)
        g.ground(x0, fy, SEC)
        # a two-wide pit with spikes at the bottom, mid-section (not in the
        # first section, where Kaya spawns)
        if s > 0:
            g.rect(x0 + 12, fy, 2, h - fy, ".")
            g.spikes(x0 + 12, h - 1, 2)
        # a one-way shelf with gems over the first half
        g.platform(x0 + 3, fy - 4, 5)
        for gx in (x0 + 4, x0 + 6):
            g.ent("gem", gx, fy - 5)
        # upper storeys: solid ledges and a vine, so the whole height has tiles
        for ly in range(4, fy - 6, 6):
            g.ground(x0 + 15, ly, 6, depth=2)
            g.vine(x0 + 18, ly + 2, 3)
            g.ent("gem", x0 + 16, ly - 1)
        g.trunk(x0 + 21, 2, fy - 2)
        # a crate on the shelf (breakable art, off the route)
        g.crates(x0 + 7, fy - 5, 1)
        if GLOW.get(tileset):
            g.hline(x0 + 9, 2, 4, GLOW[tileset])        # a lit run under the ceiling
        # enemies: two a section, as the 5x levels are budgeted
        if s > 0:
            g.ent("enemy_walker", x0 + 18, fy - 1)
            g.ent("enemy_flyer", x0 + 8, fy - 6)
        g.mark("sec%d" % s, x0 + 20, fy - 1)
        if s % 2 == 1 and s < sections - 1:
            g.checkpoint(x0 + 22, fy - 1)
            checkpoints.append(s)
    g.ent("player_spawn", 2, floor_row(h, 0) - 1)
    g.ent("exit", w - 3, floor_row(h, sections - 1) - 1)
    # the route: a hop per section, through every checkpoint by its index
    prev = "spawn"
    k = 0
    for s in range(sections):
        g.route(prev, "sec%d" % s)
        prev = "sec%d" % s
        if s in checkpoints:
            cid = "checkpoint" if len(checkpoints) == 1 else "checkpoint#%d" % k
            g.route(prev, cid)
            prev = cid
            k += 1
    g.route(prev, "exit")
    return g


def write(w, h, tileset):
    lid = "stress_%dx%d_%s" % (w, h, tileset)
    g = build(w, h, tileset)
    path = os.path.join(OUT, lid + ".json")
    with open(path, "w") as f:
        json.dump(g.to_dict(lid, "STRESS %dx%d" % (w, h)), f, indent=1)
        f.write("\n")
    print("%s  %dx%d tiles, %d entities, %d hops" % (os.path.relpath(path, ROOT), w, h,
                                                   len(g.entities), len(g.hops)))


if __name__ == "__main__":
    if len(sys.argv) == 4:
        write(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])
    else:
        for args in STANDARD:
            write(*args)
