#!/usr/bin/env python3
"""Authoring tool for levels/*.json.

The JSON it writes is the source of truth the game loads — this script just
makes it practical to lay out a 50x30 char grid without miscounting columns.
Edit a level here, run tools/genlevels.sh, and the JSON is regenerated.

A level also declares its intended solution here, with mark() and route(), and
that declaration is serialised alongside the grid (ADR 005). It is a claim, not
a proof: tools/prove.sh is what plays the route with the shipping movement code.
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVELS = os.path.join(ROOT, "levels")
os.makedirs(LEVELS, exist_ok=True)

SCREEN_W, SCREEN_H = 25, 15   # tiles per screen at 400x240 / 16px

## Waypoints the route may end at. A route that stops anywhere else does not
## describe finishing the level, so it is rejected rather than proved.
TERMINAL_WAYPOINTS = ("exit", "boss_exit")


def _tile_flags():
    """char -> gameplay flags, straight from the two files the game reads.

    Only used to sanity-check marks; the level JSON still carries characters.
    """
    tiles = json.load(open(os.path.join(ROOT, "data/tiles.json")))["tiles"]
    legend = json.load(open(os.path.join(ROOT, "data/level_legend.json")))["legend"]
    return {ch: tiles.get(str(tid), {}) for ch, tid in legend.items()}


class Grid:
    def __init__(self, w, h, fill="."):
        self.w, self.h = w, h
        self.fg = [[fill] * w for _ in range(h)]
        self.bg = [["."] * w for _ in range(h)]
        self.entities = []
        ## ADR 005: the intended solution, declared beside the geometry.
        self.marks = {}
        self.hops = []

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

    # -- the declared route (ADR 005) ---------------------------------------
    def mark(self, name, x, y):
        """Name a tile so route() can point at somewhere that is not an entity.

        (x, y) uses the same convention as an entity: the tile the player's
        body occupies while standing there, i.e. the tile directly above the
        floor -- exactly where player_spawn sits. Marks serialise to
        levels/<id>.json as {"marks": {"<name>": {"x": .., "y": ..}}}.
        """
        if name in self.marks:
            raise ValueError("mark '%s' is declared twice" % name)
        if name == "spawn":
            raise ValueError("'spawn' is reserved; it always means player_spawn")
        if not (0 <= x < self.w and 0 <= y < self.h):
            raise ValueError("mark '%s' at (%d,%d) is off the %dx%d grid"
                             % (name, x, y, self.w, self.h))
        self.marks[name] = {"x": x, "y": y}

    def route(self, from_id, to_id, form="human"):
        """Declare one hop of the intended solution.

        Hops chain: the first leaves "spawn", each later one leaves where the
        previous arrived, and the last arrives at an exit. tools/prove.sh seeds
        the real Actor at `from_id` in `form` and searches for `to_id` with the
        shipping movement code. Nothing here is proof -- it is the claim the
        prover is asked to check.
        """
        if from_id == to_id:
            raise ValueError("route hop '%s' -> '%s' goes nowhere" % (from_id, to_id))
        self.hops.append({"from": from_id, "to": to_id, "form": form})

    def _waypoints(self):
        """Every id route() is allowed to name, and why."""
        counts = {}
        for e in self.entities:
            counts[e["type"]] = counts.get(e["type"], 0) + 1
        ids = {"spawn"}
        for name in self.marks:
            if name in counts:
                raise ValueError(
                    "mark '%s' collides with an entity type of the same name" % name)
            ids.add(name)
        # An entity type only names a waypoint when there is exactly one of it;
        # "gem" would otherwise mean sixteen different places.
        ambiguous = set()
        for t, n in counts.items():
            if t == "player_spawn":
                continue
            if n == 1:
                ids.add(t)
            else:
                ambiguous.add(t)
        return ids, ambiguous

    def _check_route(self, level_id, topdown):
        """Fail generation on a route that cannot mean what it says.

        These are cheap statements about the declaration, not about whether the
        level can be played -- only tools/prove.sh answers that.
        """
        if not self.hops:
            return
        known, ambiguous = self._waypoints()
        for h in self.hops:
            for end in ("from", "to"):
                wp = h[end]
                if wp in ambiguous:
                    raise ValueError(
                        "%s: route names '%s', but the level has several of them"
                        % (level_id, wp))
                if wp not in known:
                    raise ValueError(
                        "%s: route names '%s', which is neither 'spawn', a mark, "
                        "nor an entity in the level" % (level_id, wp))
            form_path = os.path.join(ROOT, "data/forms/%s.json" % h["form"])
            if not os.path.exists(form_path):
                raise ValueError("%s: route hop '%s' -> '%s' asks for form '%s', "
                                 "which has no data/forms entry"
                                 % (level_id, h["from"], h["to"], h["form"]))
        if self.hops[0]["from"] != "spawn":
            raise ValueError("%s: the route must start at 'spawn', not '%s'"
                             % (level_id, self.hops[0]["from"]))
        for a, b in zip(self.hops, self.hops[1:]):
            if b["from"] != a["to"]:
                raise ValueError(
                    "%s: route breaks between '%s' and '%s' -- a hop has to start "
                    "where the one before it arrived, or the prover teleports"
                    % (level_id, a["to"], b["from"]))
        last = self.hops[-1]["to"]
        if last not in TERMINAL_WAYPOINTS:
            raise ValueError(
                "%s: the route ends at '%s'; it has to end at one of %s or it "
                "does not describe finishing the level"
                % (level_id, last, ", ".join(TERMINAL_WAYPOINTS)))
        if topdown:
            return
        # A waypoint the player cannot physically occupy is a typo that would
        # cost a whole prover run to discover. Two tiles, because the human
        # hitbox is 22px.
        flags = _tile_flags()
        for name, m in sorted(self.marks.items()):
            for dy in (0, -1):
                y = m["y"] + dy
                if y < 0:
                    raise ValueError("%s: mark '%s' has no headroom above the grid"
                                     % (level_id, name))
                f = flags.get(self.fg[y][m["x"]], {})
                if f.get("solid"):
                    raise ValueError("%s: mark '%s' at (%d,%d) is inside solid tile "
                                     "'%s' at row %d"
                                     % (level_id, name, m["x"], m["y"],
                                        self.fg[y][m["x"]], y))
            f = flags.get(self.fg[m["y"]][m["x"]], {})
            if f.get("hazard"):
                raise ValueError("%s: mark '%s' at (%d,%d) sits on a hazard"
                                 % (level_id, name, m["x"], m["y"]))

    # -- output -------------------------------------------------------------
    def to_dict(self, level_id, name, music="", next_level="", topdown=False):
        self._check_route(level_id, topdown)
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
            "marks": self.marks,
            "route": self.hops,
        }


def write(level_id, grid, name, music="", next_level="", topdown=False):
    path = os.path.join(LEVELS, level_id + ".json")
    with open(path, "w") as f:
        json.dump(grid.to_dict(level_id, name, music, next_level, topdown), f, indent=1)
        f.write("\n")
    print("%-16s %dx%d tiles  %d entities  %d route hop(s)" % (
        level_id + ".json", grid.w, grid.h, len(grid.entities), len(grid.hops)))
