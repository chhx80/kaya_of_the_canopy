#!/usr/bin/env python3
"""Authoring tool for levels/*.json.

The JSON it writes is the source of truth the game loads — this script just
makes it practical to lay out a 50x30 char grid without miscounting columns.
Edit a level here, run tools/genlevels.sh, and the JSON is regenerated.
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVELS = os.path.join(ROOT, "levels")
os.makedirs(LEVELS, exist_ok=True)

SCREEN_W, SCREEN_H = 25, 15   # tiles per screen at 400x240 / 16px


class Grid:
    def __init__(self, w, h, fill="."):
        self.w, self.h = w, h
        self.fg = [[fill] * w for _ in range(h)]
        self.bg = [["."] * w for _ in range(h)]
        self.entities = []

    # -- primitives ---------------------------------------------------------
    def put(self, x, y, ch, layer="fg"):
        if 0 <= x < self.w and 0 <= y < self.h:
            (self.fg if layer == "fg" else self.bg)[y][x] = ch

    def rect(self, x, y, w, h, ch, layer="fg"):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.put(xx, yy, ch, layer)

    def hline(self, x, y, w, ch, layer="fg"):
        self.rect(x, y, w, 1, ch, layer)

    def vline(self, x, y, h, ch, layer="fg"):
        self.rect(x, y, 1, h, ch, layer)

    # -- level idioms -------------------------------------------------------
    def ground(self, x, y, w, depth=None):
        """Grass-capped dirt shelf with rounded edges."""
        depth = depth if depth is not None else self.h - y
        self.hline(x, y, w, "#")
        self.rect(x, y + 1, w, max(0, depth - 1), "d")
        if w > 1:
            self.put(x, y, "#")
            self.put(x + w - 1, y, "#")

    def platform(self, x, y, w):
        self.hline(x, y, w, "=")

    def vine(self, x, y, h):
        self.vline(x, y, h, "|")

    def spikes(self, x, y, w):
        self.hline(x, y, w, "^")

    def crates(self, x, y, n, vertical=False):
        for i in range(n):
            self.put(x + (0 if vertical else i), y - (i if vertical else 0), "c")

    def canopy(self, x, y, w, h):
        """Decorative leaf mass on the background layer."""
        self.rect(x, y, w, h, "L", "bg")

    def trunk(self, x, y, h):
        self.vline(x, y, h, "T", "bg")

    def ent(self, type_, x, y, **props):
        e = {"type": type_, "x": x, "y": y}
        e.update(props)
        self.entities.append(e)

    # -- output -------------------------------------------------------------
    def to_dict(self, level_id, name, music="", next_level="", topdown=False):
        return {
            "id": level_id,
            "name": name,
            "music": music,
            "next_level": next_level,
            "topdown": topdown,
            "screens": [
                (self.w + SCREEN_W - 1) // SCREEN_W,
                (self.h + SCREEN_H - 1) // SCREEN_H,
            ],
            "fg": ["".join(r) for r in self.fg],
            "bg": ["".join(r) for r in self.bg],
            "entities": self.entities,
        }


def write(level_id, grid, name, music="", next_level="", topdown=False):
    path = os.path.join(LEVELS, level_id + ".json")
    with open(path, "w") as f:
        json.dump(grid.to_dict(level_id, name, music, next_level, topdown), f, indent=1)
        f.write("\n")
    print("%-16s %dx%d tiles  %d entities" % (
        level_id + ".json", grid.w, grid.h, len(grid.entities)))
