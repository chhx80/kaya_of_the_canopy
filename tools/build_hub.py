#!/usr/bin/env python3
"""Builds staging/hub_v2.json — the 25-door overworld (M6).

Standalone on purpose. `tools/build_levels.py` owns the five-door 50x15 hub and
is not touched by this file; nothing here imports from it, so the two can be
merged without either script moving.

The map is 50x30 (2x2 screens of 25x15) and holds 25 gateways in five clusters,
one per world. It is top-down, so there is no gravity and none of the
platformer reachability rules apply — which is exactly why this script carries
its own proof. `prove_walkable()` floods the space of *player positions*, not
the space of tiles, using the same 10x10 box, the same tile solidity and the
same spawn/return offsets the running game uses. A gateway nobody can walk to
is the top-down version of a shaft capped across its full width, and that class
of bug has shipped here six times.

The proof runs before the JSON is written. A map that fails it is not emitted.

    tools/env.sh must exist; run as:  $PYVENV tools/build_hub.py
"""
import json
import os
import sys
from collections import deque

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVELS = os.path.join(ROOT, "levels")
TS = 16
W, H = 50, 30
SCREEN_W, SCREEN_H = 25, 15

# --- the three numbers the running game decides, copied from the shipping code.
# tests/test_hub_walkable.gd asserts these are still what src/hub/*.gd says.
PLAYER_BOX = (10, 10)            # HubPlayer._ready():  box = Vector2(10, 10)
SPAWN_OFFSET = (3, 5)            # overworld.gd:        player.pos = p + Vector2(3, 5)
RETURN_OFFSET = (3, 20)          # overworld.gd:        player.pos = d.pos + Vector2(3, 20)
DOOR_GROW = 6                    # overworld.gd:        d.aabb().grow(6.0)
DOOR_SIZE = 16                   # HubDoor.SIZE

EPS = 0.001                      # TileCollision.EPS, so tile_range() matches


# ---------------------------------------------------------------- tile facts
def solid_chars():
    """Which legend characters are solid, read from the game's own data files.

    Deriving this instead of hardcoding it means the prover cannot disagree
    with TileWorld.is_solid() about what a wall is.
    """
    with open(os.path.join(ROOT, "data", "level_legend.json")) as f:
        legend = json.load(f)["legend"]
    with open(os.path.join(ROOT, "data", "tiles.json")) as f:
        tiles = json.load(f)["tiles"]
    out = set()
    for ch, tid in legend.items():
        t = tiles.get(str(tid), {})
        if not t.get("solid", False):
            continue
        if "switch_group" in t:
            # Switch blocks are solid only in one group state. The hub has no
            # switches, so refusing them outright keeps the map honest.
            continue
        out.add(ch)
    return out


SOLID = solid_chars()


# ---------------------------------------------------------------- the canvas
class Map:
    def __init__(self):
        self.fg = [["."] * W for _ in range(H)]
        self.bg = [["."] * W for _ in range(H)]
        self.entities = []

    def put(self, x, y, ch, layer="fg"):
        if 0 <= x < W and 0 <= y < H:
            (self.fg if layer == "fg" else self.bg)[y][x] = ch

    def rect(self, x, y, w, h, ch, layer="fg"):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.put(xx, yy, ch, layer)

    def trail(self, pts, ch="p", width=2):  # noqa: D401
        """L-shaped background trail through `pts`. Decoration only — the bg
        layer is never collision — but it is what tells a player where to walk."""
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                self.rect(x, y0, 1, width, ch, "bg")
            for y in range(min(y0, y1), max(y0, y1) + 1):
                self.rect(x1, y, width, 1, ch, "bg")

    def ent(self, type_, x, y, **props):
        e = {"type": type_, "x": x, "y": y}
        e.update(props)
        self.entities.append(e)

    def is_solid(self, tx, ty):
        if tx < 0 or tx >= W or ty < 0:
            return True          # TileWorld.flags_at: out of bounds sides are wall
        if ty >= H:
            return False         # ...and below the map is open
        return self.fg[ty][tx] in SOLID

    def to_dict(self):
        return {
            "id": "hub_v2",
            "name": "THE CANOPY",
            "music": "hub",
            "next_level": "",
            "topdown": True,
            "screens": [(W + SCREEN_W - 1) // SCREEN_W, (H + SCREEN_H - 1) // SCREEN_H],
            "fg": ["".join(r) for r in self.fg],
            "bg": ["".join(r) for r in self.bg],
            "entities": self.entities,
        }


# ------------------------------------------------------------------- regions
# Each world owns a rectangle, a ground fill, a trail tile, an obstacle tile
# and an accent. The five ground fills are five different tiles and so are the
# five obstacles, so no two clusters read alike even in a black-and-white
# screenshot.
#
#   nest    x  2..47  y  2..7    dark obsidian, metal walkways and blocks, veins
#   deeps   x  2..23  y  9..14   lightless black, brown tunnels and dirt mounds
#   heights x 26..47  y  9..14   brown ash, rock trails, stone crags, vents
#   canopy  x  2..23  y 16..27   green grass, brown trails, trees   <- the spawn
#   ruins   x 26..47  y 16..27   mossy flagstones, blue water
#
# Ground, trail and obstacle are all different from region to region: five
# clusters that read alike are four clusters and a mistake.
#
# Region edges sit on the screen seams (x=25, y=15) wherever they can, so a
# cluster is not split across a screen flip.
REGIONS = {
    "nest":    dict(rect=(2, 2, 46, 6),    ground="r", trail="M", obstacle="M", accent="!"),
    "deeps":   dict(rect=(2, 9, 22, 6),    ground="X", trail="p", obstacle="d", accent="X"),
    "heights": dict(rect=(26, 9, 22, 6),   ground="d", trail="r", obstacle="s", accent="!"),
    "canopy":  dict(rect=(2, 16, 22, 12),  ground="g", trail="p", obstacle="@", accent="g"),
    "ruins":   dict(rect=(26, 16, 22, 12), ground="S", trail="p", obstacle="W", accent="s"),
}

SPAWN = (3, 26)

# level id, label, requires, (x, y), region
DOORS = [
    # --- World 1, Canopy Trail. Ids and labels are the shipped ones.
    ("jungle_1", "CANOPY TRAIL",       "",          (6, 24),  "canopy"),
    ("jungle_2", "ROOT HOLLOW",        "jungle_1",  (11, 21), "canopy"),
    ("jungle_3", "THE WATERWAY",       "jungle_2",  (16, 24), "canopy"),
    ("jungle_4", "SKY BRANCH",         "jungle_3",  (20, 20), "canopy"),
    ("jungle_5", "HEART OF THE GROVE", "jungle_4",  (13, 17), "canopy"),
    # --- World 2, Sunken Ruins. Opens when World 1's boss is down.
    ("ruins_1",  "DROWNED GATE",       "jungle_5",  (29, 24), "ruins"),
    ("ruins_2",  "THE CISTERN",        "ruins_1",   (34, 21), "ruins"),
    ("ruins_3",  "UNDERTOW",           "ruins_2",   (39, 24), "ruins"),
    ("ruins_4",  "THE FLOODED HALL",   "ruins_3",   (44, 20), "ruins"),
    ("ruins_5",  "THE TIDE MAW",       "ruins_4",   (36, 17), "ruins"),
    # --- World 3, Thermal Heights.
    ("heights_1", "UPDRAFT",           "ruins_5",   (29, 12), "heights"),
    ("heights_2", "THE THERMALS",      "heights_1", (33, 10), "heights"),
    ("heights_3", "ASH COLUMN",        "heights_2", (37, 12), "heights"),
    ("heights_4", "THE LONG GLIDE",    "heights_3", (41, 10), "heights"),
    ("heights_5", "THE STORMCREST",    "heights_4", (45, 12), "heights"),
    # --- World 4, Termite Deeps.
    ("deeps_1",  "THE LIGHTLESS",      "heights_5", (5, 12),  "deeps"),
    ("deeps_2",  "CHEW THROUGH",       "deeps_1",   (9, 10),  "deeps"),
    ("deeps_3",  "THE GALLERIES",      "deeps_2",   (13, 12), "deeps"),
    ("deeps_4",  "SPORE LIGHT",        "deeps_3",   (17, 10), "deeps"),
    ("deeps_5",  "THE BROOD QUEEN",    "deeps_4",   (21, 12), "deeps"),
    # --- World 5, The Obsidian Nest.
    ("nest_1",   "BLACK GLASS",        "deeps_5",   (7, 5),   "nest"),
    ("nest_2",   "THE SWITCHYARD",     "nest_1",    (15, 3),  "nest"),
    ("nest_3",   "FOUR SHAPES",        "nest_2",    (24, 5),  "nest"),
    ("nest_4",   "THE LAST ASCENT",    "nest_3",    (33, 3),  "nest"),
    ("nest_5",   "THE OBSIDIAN HEART", "nest_4",    (41, 5),  "nest"),
]

# Solid clumps inside each region: (x, y, w, h). They shape the walk without
# ever sealing it — prove_walkable() is what decides whether that is true.
CLUMPS = {
    "canopy": [(2, 16, 2, 2), (8, 18, 2, 2), (3, 21, 2, 2), (17, 17, 3, 2),
               (21, 24, 2, 3), (14, 26, 3, 2), (9, 23, 2, 2), (6, 16, 1, 1),
               (22, 16, 2, 2), (2, 26, 1, 2)],
    "ruins":  [(30, 18, 3, 2), (41, 23, 3, 3), (26, 20, 2, 2), (33, 25, 2, 2),
               (45, 25, 2, 2), (38, 16, 2, 2), (27, 16, 2, 1), (46, 16, 2, 2),
               (26, 27, 3, 1)],
    "heights": [(26, 9, 1, 1), (35, 9, 2, 1), (31, 14, 2, 1), (39, 14, 2, 1),
                (46, 9, 2, 1), (27, 13, 1, 2), (44, 14, 1, 1)],
    "deeps":  [(3, 9, 1, 1), (11, 9, 2, 1), (15, 14, 2, 1), (19, 9, 1, 1),
               (22, 9, 2, 1), (2, 13, 1, 2), (7, 12, 1, 1)],
    "nest":   [(3, 2, 1, 2), (11, 6, 2, 1), (19, 2, 2, 2), (28, 6, 2, 1),
               (36, 2, 2, 2), (45, 6, 2, 1), (23, 2, 1, 1), (46, 2, 2, 2)],
}

# Where a region wall is cut so you can cross. Two tiles wide everywhere: the
# player box is 10 px, a one-tile gap is 16 px, and a one-tile gap is precisely
# the kind of margin this project has shipped bugs on.
RIDGE_GAPS = [(6, 2), (42, 2)]          # x, width — on rows 8 and 15
SEAM_GAPS = [(12, 2), (22, 2)]          # y, height — on columns 24..25


def build():
    m = Map()

    # ---- ground fill. Every tile of the background gets a ground, including
    # the rows and columns the region walls stand on: those walls are cut open
    # to let you cross, and an uncovered background tile renders as a black
    # hole in the middle of the gap you are supposed to walk through.
    def ground_at(x, y):
        if y <= 7:
            return REGIONS["nest"]["ground"]
        if y <= 15:
            return REGIONS["deeps" if x < 25 else "heights"]["ground"]
        return REGIONS["canopy" if x < 25 else "ruins"]["ground"]

    for y in range(H):
        for x in range(W):
            m.put(x, y, ground_at(x, y), "bg")

    # Border, ridges and the vertical seam wall, each drawn in the obstacle
    # tile of the region it belongs to so the boundary reads as that region's
    # edge rather than as a generic wall.
    def wall_row(y, region_of):
        for x in range(0, W):
            m.put(x, y, REGIONS[region_of(x)]["obstacle"])

    def left_right(x):
        return "deeps" if x < 25 else "heights"

    # outer border
    for x in range(W):
        for y in (0, 1):
            m.put(x, y, REGIONS["nest"]["obstacle"])
        for y in (28, 29):
            m.put(x, y, REGIONS["canopy" if x < 25 else "ruins"]["obstacle"])
    for y in range(H):
        side = ("nest" if y < 8 else
                "deeps" if y < 15 else
                "canopy")
        right = ("nest" if y < 8 else
                 "heights" if y < 15 else
                 "ruins")
        for x in (0, 1):
            m.put(x, y, REGIONS[side]["obstacle"])
        for x in (48, 49):
            m.put(x, y, REGIONS[right]["obstacle"])

    wall_row(8, left_right)                                   # nest / middle band
    wall_row(15, lambda x: "canopy" if x < 25 else "ruins")    # middle / bottom band
    for y in range(9, 28):
        region = ("deeps" if y < 15 else "canopy")
        for x in (24, 25):
            m.put(x, y, REGIONS[region]["obstacle"])

    # ---- cut the crossings
    for gx, gw in RIDGE_GAPS:
        for x in range(gx, gx + gw):
            m.put(x, 8, ".")
            m.put(x, 15, ".")
    for gy, gh in SEAM_GAPS:
        for y in range(gy, gy + gh):
            for x in (24, 25):
                m.put(x, y, ".")

    # ---- region clumps
    for name, rects in CLUMPS.items():
        ch = REGIONS[name]["obstacle"]
        for (x, y, w, h) in rects:
            m.rect(x, y, w, h, ch)

    # ---- accents on the background: lava veins, moss, dark earth
    for (x, y, w, h) in [(4, 3, 3, 1), (20, 6, 4, 1), (29, 3, 5, 1), (43, 2, 3, 1),
                         (12, 4, 2, 1), (37, 6, 3, 1)]:
        m.rect(x, y, w, h, REGIONS["nest"]["accent"], "bg")
    for (x, y, w, h) in [(30, 13, 3, 1), (40, 11, 3, 1), (27, 10, 2, 1),
                         (44, 13, 3, 1)]:
        m.rect(x, y, w, h, REGIONS["heights"]["accent"], "bg")
    for (x, y, w, h) in [(28, 22, 2, 2), (43, 18, 3, 1), (32, 17, 2, 1)]:
        m.rect(x, y, w, h, REGIONS["ruins"]["accent"], "bg")

    # ---- the trails, each in its own region's tile. Purely cosmetic — the bg
    # layer is never collision — but they follow the route the prover then has
    # to confirm is real, and they are most of what tells the five clusters
    # apart at a glance.
    def region_trail(name, pts):
        m.trail(pts, REGIONS[name]["trail"])

    region_trail("canopy", [SPAWN, (6, 25), (11, 22), (16, 25), (20, 21),
                            (13, 18), (6, 22), (6, 16)])
    region_trail("canopy", [(6, 22), (22, 22)])
    region_trail("ruins", [(26, 22), (29, 25), (34, 22), (39, 25), (44, 21),
                           (36, 18), (42, 18), (42, 16)])
    region_trail("heights", [(42, 14), (42, 9)])
    region_trail("heights", [(29, 13), (33, 11), (37, 13), (41, 11), (45, 13)])
    region_trail("heights", [(29, 13), (26, 12)])
    region_trail("deeps", [(22, 12), (21, 13), (17, 11), (13, 13), (9, 11),
                           (5, 13), (6, 14)])
    region_trail("deeps", [(6, 9), (6, 13)])
    region_trail("nest", [(7, 7), (7, 6), (15, 4), (24, 6), (33, 4), (41, 6),
                          (42, 6), (42, 7)])

    # ---- inhabitants
    m.ent("player_spawn", SPAWN[0], SPAWN[1])
    for level, label, requires, (x, y), _region in DOORS:
        m.ent("hub_door", x, y, level=level, label=label,
              requires=requires, requires_all=False)
    return m


# ------------------------------------------------------------------ the proof
def _free_mask(m):
    """One byte per candidate player position: can the 10x10 box sit there.

    Tile span is computed the way TileCollision.tile_range() computes it, EPS
    and all, so a box whose right edge lands exactly on a tile boundary is
    judged here the same way the game judges it.
    """
    bw, bh = PLAYER_BOX
    px_w, px_h = W * TS - bw, H * TS - bh
    solid = [[m.is_solid(x, y) for x in range(W)] for y in range(H)]
    free = bytearray((px_w + 1) * (px_h + 1))
    for py in range(px_h + 1):
        ty0 = py // TS
        ty1 = int((py + bh - EPS) // TS)
        row = py * (px_w + 1)
        for px in range(px_w + 1):
            tx0 = px // TS
            tx1 = int((px + bw - EPS) // TS)
            blocked = False
            for ty in range(ty0, ty1 + 1):
                for tx in range(tx0, tx1 + 1):
                    if solid[ty][tx]:
                        blocked = True
                        break
                if blocked:
                    break
            free[row + px] = 0 if blocked else 1
    return free, px_w, px_h


def prove_walkable(m):
    """Flood the reachable player positions from the spawn and report them.

    Movement is one pixel at a time along one axis, which is less than the
    1.23 px a frame of HubPlayer motion covers at full speed, and the actor
    accelerates from rest — so every step this flood takes is a step the real
    character can take. No jump envelope, no model: just the box, the walls,
    and whether the two are ever in the same place.
    """
    free, px_w, px_h = _free_mask(m)
    stride = px_w + 1
    sx = SPAWN[0] * TS + SPAWN_OFFSET[0]
    sy = SPAWN[1] * TS + SPAWN_OFFSET[1]
    if not free[sy * stride + sx]:
        raise SystemExit("hub_v2: the spawn at tile %s is inside a wall" % (SPAWN,))
    seen = bytearray(len(free))
    q = deque([sy * stride + sx])
    seen[sy * stride + sx] = 1
    while q:
        i = q.popleft()
        x, y = i % stride, i // stride
        for j, ok in ((i - 1, x > 0), (i + 1, x < px_w),
                      (i - stride, y > 0), (i + stride, y < px_h)):
            if ok and not seen[j] and free[j]:
                seen[j] = 1
                q.append(j)
    return seen, stride, px_w, px_h


def check_doors(m, seen, stride):
    """Every gateway must pass three checks, and the third is the real one."""
    problems = []
    for level, label, _req, (dx, dy), _region in DOORS:
        # 1. you can stand on the gateway tile
        sx, sy = dx * TS + SPAWN_OFFSET[0], dy * TS + SPAWN_OFFSET[1]
        on_door = seen[sy * stride + sx] if 0 <= sy * stride + sx < len(seen) else 0
        # 2. the tile the game drops you on when you come back out of the level
        rx, ry = dx * TS + RETURN_OFFSET[0], dy * TS + RETURN_OFFSET[1]
        returns = seen[ry * stride + rx] if 0 <= ry * stride + rx < len(seen) else 0
        # 3. some reachable position actually lights the "PRESS JUMP" prompt
        prompt = False
        gx0, gy0 = dx * TS - DOOR_GROW, dy * TS - DOOR_GROW
        gx1, gy1 = dx * TS + DOOR_SIZE + DOOR_GROW, dy * TS + DOOR_SIZE + DOOR_GROW
        bw, bh = PLAYER_BOX
        for py in range(max(0, gy0 - bh + 1), gy1):
            for px in range(max(0, gx0 - bw + 1), gx1):
                i = py * stride + px
                if 0 <= i < len(seen) and seen[i]:
                    prompt = True
                    break
            if prompt:
                break
        if not on_door:
            problems.append("%s: gateway tile (%d,%d) cannot be walked to" % (level, dx, dy))
        if not returns:
            problems.append("%s: the tile the game returns you to, (%d,%d), is not "
                            "walkable — you would come back inside a wall"
                            % (level, dx, dy + 1))
        if not prompt:
            problems.append("%s: no reachable position triggers its prompt" % level)
    return problems


def check_gating():
    """The requires chain: every prerequisite is a gateway on this map, exactly
    one gateway is free, and the chain has no cycle."""
    problems = []
    ids = [d[0] for d in DOORS]
    if len(set(ids)) != len(ids):
        problems.append("duplicate level ids among the gateways")
    free = [d[0] for d in DOORS if d[2] == ""]
    if free != ["jungle_1"]:
        problems.append("exactly one gateway must be open from the start, got %s" % free)
    req = {d[0]: d[2] for d in DOORS}
    for level, r in req.items():
        if r and r not in req:
            problems.append("%s requires '%s', which is not a gateway here" % (level, r))
    for level in req:
        seen, cur = set(), level
        while cur:
            if cur in seen:
                problems.append("the requires chain from %s loops" % level)
                break
            seen.add(cur)
            cur = req.get(cur, "")
    return problems


def main():
    m = build()
    seen, stride, _w, _h = prove_walkable(m)
    problems = check_doors(m, seen, stride) + check_gating()
    if problems:
        for p in problems:
            print("  FAIL %s" % p)
        raise SystemExit("hub_v2 not written: %d problem(s)" % len(problems))

    os.makedirs(LEVELS, exist_ok=True)
    path = os.path.join(LEVELS, "hub_v2.json")
    with open(path, "w") as f:
        json.dump(m.to_dict(), f, indent=1)
        f.write("\n")
    walkable = sum(seen)
    print("hub_v2.json      %dx%d tiles  %d doors  %d entities"
          % (W, H, len(DOORS), len(m.entities)))
    print("                 proved: %d reachable player positions, "
          "all %d gateways walkable" % (walkable, len(DOORS)))


if __name__ == "__main__":
    sys.exit(main())
