#!/usr/bin/env python3
"""Conservative reachability check for levels/*.json.

Models the player as 1 tile wide, 2 tiles tall, with the jump envelope derived
from data/forms/human.json. Answers: starting at the spawn, which standable
tiles can you get to, and are the things you must touch among them?

Deliberately GENEROUS about horizontal reach and falls, so anything it reports
as unreachable is very likely genuinely unreachable rather than a modelling
artefact. A 3-tile rise is impossible for this character (apex 2.78 tiles), and
that is the failure this exists to catch.
"""
import json, math, os, sys
from collections import deque

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_flags():
    tiles = json.load(open(os.path.join(ROOT, "data/tiles.json")))["tiles"]
    legend = json.load(open(os.path.join(ROOT, "data/level_legend.json")))["legend"]
    f = {}
    for ch, tid in legend.items():
        t = tiles.get(str(tid), {})
        f[ch] = {
            "solid": bool(t.get("solid")),
            "oneway": bool(t.get("oneway")),
            "ladder": bool(t.get("ladder")),
            "water": bool(t.get("water")),
            "switched": "switch_group" in t,
        }
    return f


def envelope_for(form):
    """Jump reach per form, straight from data/forms/<form>.json."""
    h = json.load(open(os.path.join(ROOT, "data/forms/%s.json" % form)))
    v, g = abs(h.get("jump_vel", 0)), h.get("gravity", 700)
    run = h.get("max_run", 100)
    apex = v * v / (2 * g) if g else 0
    up = {}
    for tiles_up in range(0, 12):
        px = tiles_up * 16
        if px > apex:
            break
        t = (v + math.sqrt(max(0.0, v * v - 2 * g * px))) / g
        up[tiles_up] = int(run * t // 16)
    return up, apex


ENVELOPES = {f: envelope_for(f) for f in ("human", "frog", "fish", "bird")}


class Level:
    def __init__(self, path, flags):
        d = json.load(open(path))
        self.d = d
        self.fg = d["fg"]
        self.h = len(self.fg)
        self.w = len(self.fg[0])
        self.flags = flags
        # Switch blocks can be toggled by the player, so treat them as passable
        # rather than guessing which half is solid at any moment.
        self.doors = {(int(e["x"]), int(e["y"]))
                      for e in d.get("entities", []) if e["type"].startswith("door_")}
        self.pads = {(int(e["x"]), int(e["y"])): e["type"][4:]
                     for e in d.get("entities", []) if e["type"].startswith("pad_")}

    def ch(self, x, y):
        if not (0 <= x < self.w and 0 <= y < self.h):
            return None
        return self.fg[y][x]

    def solid(self, x, y):
        if x < 0 or x >= self.w or y < 0:
            return True
        if y >= self.h:
            return False
        c = self.ch(x, y)
        fl = self.flags.get(c, {})
        if fl.get("switched"):
            return False
        if (x, y) in self.doors or (x, y + 1) in self.doors:
            return False
        return fl.get("solid", False)

    def oneway(self, x, y):
        return self.flags.get(self.ch(x, y), {}).get("oneway", False)

    def ladder(self, x, y):
        return self.flags.get(self.ch(x, y), {}).get("ladder", False)

    def water(self, x, y):
        return self.flags.get(self.ch(x, y), {}).get("water", False)

    def clear(self, x, y):
        """Two tiles of headroom with feet in tile y."""
        return not self.solid(x, y) and not self.solid(x, y - 1)

    def standable(self, x, y):
        if not self.clear(x, y):
            return False
        below = self.solid(x, y + 1) or self.oneway(x, y + 1)
        return below or self.ladder(x, y) or self.water(x, y)


def path_clear(lv, x1, y1, x2, y2):
    """Can the body physically cross the columns between two tiles?

    Without this the model jumps straight THROUGH walls: it only checked that
    the destination was standable. SKY BRANCH shipped with the frog pad sealed
    behind a 20-tile wall and the check passed it, because a 2-tile hop from
    col 10 to col 12 ignored the wall at col 11.

    A crossing is allowed if every column between the two has a 2-tall gap
    somewhere in the band the arc covers.
    """
    if x1 == x2:
        return True
    lo, hi = min(y1, y2), max(y1, y2)
    step = 1 if x2 > x1 else -1
    for xi in range(x1 + step, x2, step):
        if not any(lv.clear(xi, r) for r in range(lo - 2, hi + 1)):
            return False
    return True


def reachable(lv, start_xy, start_form="human"):
    """BFS over (x, y, form). Stepping on a transform pad changes the form, so a
    pad the human can reach unlocks everywhere the new form can go."""
    seen = set()
    start = (start_xy[0], start_xy[1], start_form)
    q = deque([start])
    seen.add(start)
    while q:
        x, y, form = q.popleft()
        up = ENVELOPES[form][0]
        # a pad underfoot or at head height changes the form
        for pad_xy, pad_form in lv.pads.items():
            if abs(pad_xy[0] - x) <= 1 and abs(pad_xy[1] - y) <= 1:
                nxt = (x, y, pad_form)
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        # The bird flies, so its reachability is just a flood fill through clear
        # space -- no jump envelope, no fall scan. Running the full enumeration
        # for it made the state space explode on an open-sky level.
        if form == "bird":
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                c = (nx, ny, form)
                if 0 <= nx < lv.w and 0 <= ny < lv.h and lv.clear(nx, ny) and c not in seen:
                    seen.add(c)
                    q.append(c)
            continue
        # the fish swims freely through water
        if form == "fish":
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if lv.water(nx, ny) and lv.clear(nx, ny):
                        c = (nx, ny, form)
                        if c not in seen:
                            seen.add(c)
                            q.append(c)
        cand = []
        # walk / climb
        for dx in (-1, 1):
            cand.append((x + dx, y))
        if lv.ladder(x, y) or lv.water(x, y):
            cand += [(x, y - 1), (x, y + 1)]
        # jump up
        for dy, reach in up.items():
            if dy == 0:
                continue
            for dx in range(-reach, reach + 1):
                cand.append((x + dx, y - dy))
        # jump across level
        for dx in range(-up.get(0, 4), up.get(0, 4) + 1):
            cand.append((x + dx, y))
        # fall (generous: long falls carry further)
        for dx in range(-6, 7):
            for dy in range(1, lv.h):
                nx, ny = x + dx, y + dy
                if not lv.clear(nx, ny):
                    break
                if lv.standable(nx, ny):
                    cand.append((nx, ny))
                    break
        for cx, cy in cand:
            c = (cx, cy, form)
            if c in seen:
                continue
            if not (0 <= cx < lv.w and 0 <= cy < lv.h):
                continue
            if not lv.standable(cx, cy):
                continue
            if not path_clear(lv, x, y, cx, cy):
                continue
            seen.add(c)
            q.append(c)
    return seen


def ladder_exits(lv):
    """Every climbable column needs somewhere to step OFF, next to the ladder
    itself. A ladder whose only exit is a jump across a gap is reachable on
    paper and miserable in play -- which is exactly how ROOT HOLLOW's vine
    shipped: the nearest ledge was one empty column away, so you had to leave
    the vine in mid-air and cross a gap blind.

    Returns a list of (col, top_row) for ladders with no adjacent exit near the
    top, where the climb actually ends."""
    bad = []
    cols = {}
    for y in range(lv.h):
        for x in range(lv.w):
            if lv.ladder(x, y):
                cols.setdefault(x, []).append(y)
    for x, ys in cols.items():
        top = min(ys)
        # within three tiles of the top, is there anything to step onto?
        ok = False
        for y in range(top, min(top + 3, lv.h)):
            for dx in (-1, 1):
                if lv.standable(x + dx, y):
                    ok = True
        if not ok:
            bad.append((x, top))
    return bad


MUST_REACH = {"exit", "boss_exit", "key_yellow", "key_red", "key_cyan",
              "pad_frog", "pad_fish", "pad_bird", "pad_human",
              "switch_a", "switch_b", "door_yellow", "door_red", "door_cyan"}


def main():
    flags = load_flags()
    for f, (up, apex) in ENVELOPES.items():
        print("  %-6s apex %5.2f tiles   reach %s" % (f, apex / 16, up))
    print()
    bad = 0
    for name in sorted(os.listdir(os.path.join(ROOT, "levels"))):
        if not name.endswith(".json"):
            continue
        path = os.path.join(ROOT, "levels", name)
        d = json.load(open(path))
        if d.get("topdown"):
            continue
        lv = Level(path, flags)
        spawn = next((e for e in d["entities"] if e["type"] == "player_spawn"), None)
        if not spawn:
            continue
        s = (int(spawn["x"]), int(spawn["y"]))
        while s[1] + 1 < lv.h and not lv.standable(*s):
            s = (s[0], s[1] + 1)
        seen = reachable(lv, s)
        problems = []
        for x, top in ladder_exits(lv):
            problems.append(("ladder-with-no-exit", (x, top)))
        for e in d["entities"]:
            if e["type"] not in MUST_REACH:
                continue
            p = (int(e["x"]), int(e["y"]))
            near = any((p[0] + dx, p[1] + dy, f) in seen
                       for dx in (-1, 0, 1) for dy in (-1, 0, 1, 2)
                       for f in ENVELOPES)
            if not near:
                problems.append((e["type"], p))
        label = name.replace(".json", "")
        if problems:
            bad += 1
            print("  %-12s %d unreachable:" % (label, len(problems)))
            for t, p in problems:
                print("      %-14s at tile %s" % (t, p))
        else:
            print("  %-12s all required entities reachable (%d states)"
                  % (label, len(seen)))
    sys.exit(1 if bad else 0)


main()
