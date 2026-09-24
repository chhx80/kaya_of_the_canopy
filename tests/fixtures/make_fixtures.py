#!/usr/bin/env python3
"""Generate the prover's regression fixtures.

Each fixture reproduces one of the six defects that shipped an unfinishable
level (docs/plan-20-levels.md). The prover must FAIL every one of them.

Two things make these fixtures worth trusting:

**Every broken fixture has a `_fixed` twin.** The twin differs by the smallest
change that makes the level finishable - one row of tiles, one tile of headroom,
one lower bank - and the prover must PASS it. Without the twin a fixture could
be "failing" because of a typo in its route or a misplaced entity, and the
regression test would look green while testing nothing. The pair is what pins
down *why* the fixture fails.

**The rooms are tight.** A broken fixture should not fail because the search ran
out of budget; it should fail because the search exhausted the frontier and
proved there is no route. That only happens when the reachable state space is
small, so every fixture is a corridor cut out of solid rock, with no open sky to
wander around in. tests/test_prover_fixtures.gd asserts the exhaustion, not just
the failure.

    python3 tests/fixtures/make_fixtures.py
"""

import json
import os

DIR = os.path.dirname(os.path.abspath(__file__))

EMPTY, SOLID, ONEWAY, VINE, WATER_TOP, WATER, SPIKE = ".", "s", "=", "|", "~", "w", "^"


class Grid:
    def __init__(self, w, h, fill=SOLID):
        # Rock by default: a fixture carves out only what it needs, which is
        # what keeps the search space small enough to exhaust.
        self.w, self.h = w, h
        self.rows = [[fill] * w for _ in range(h)]
        self.ents = []
        self.route = []

    def box(self, x0, y0, x1, y1, ch):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if 0 <= y < self.h and 0 <= x < self.w:
                    self.rows[y][x] = ch

    def ent(self, type_, x, y, **kw):
        e = {"type": type_, "x": x, "y": y}
        e.update(kw)
        self.ents.append(e)

    def hop(self, a, b, form):
        self.route.append({"from": a, "to": b, "form": form})

    def write(self, name, title):
        doc = {
            "id": name,
            "name": title,
            "music": "",
            "next_level": "",
            "topdown": False,
            "fg": ["".join(r) for r in self.rows],
            "bg": ["." * self.w for _ in range(self.h)],
            "entities": self.ents,
            "route": self.route,
        }
        with open(os.path.join(DIR, name + ".json"), "w") as f:
            json.dump(doc, f, indent=1)
            f.write("\n")


# A player_spawn at tile (x, y) puts Kaya's feet on the *bottom* edge of row y,
# so the floor she stands on is row y + 1 and her 22 px body covers rows y - 1
# and y. Every fixture below is laid out against that.


# --------------------------------------------------------------- (a) vine top
def vine_no_exit(fixed):
    """Defect 1: a vine whose top has no adjacent standable exit.

    The checker called the top of the vine 'reachable' and stopped there.
    Arriving at the top is not the same as being able to leave it: the only
    ledge is eight tiles away across a spike pit, and no jump in the game
    covers that.
    """
    g = Grid(14, 9)
    g.box(1, 1, 12, 6, EMPTY)                # the room
    g.box(1, 7, 3, 7, SOLID)                 # the floor Kaya starts on
    g.box(4, 7, 12, 7, SPIKE)                # and the pit beside it
    g.box(3, 3, 3, 6, VINE)                  # the vine, climbable to row 3
    g.box(11, 3, 12, 3, SOLID)               # the ledge holding the exit
    if fixed:
        g.box(4, 3, 10, 3, SOLID)            # the repair: something to step onto
    # The gap from the vine to the ledge is 102 px of flat jump. Kaya's run tops
    # out at 108 px/s and she is airborne for about 0.68 s, so her reach is
    # roughly 73 px: the gap is beyond her by a margin, not by a pixel.
    g.ent("player_spawn", 3, 6)
    g.ent("exit", 11, 2)
    g.hop("spawn", "exit", "human")
    return g


# ------------------------------------------------------- (b) one-way headroom
def oneway_headroom(fixed):
    """Defect 2: a one-way platform with one tile of headroom.

    A one-way tile is not SOLID, so it was exempt from the pocket check that
    would have caught this. The bridge over the pit has 16 px of clearance and
    Kaya is 22 px, so she can never stand on it.
    """
    g = Grid(14, 10)
    g.box(1, 5, 12, 6, EMPTY)                # the two chambers, two tiles tall
    g.box(1, 7, 3, 7, SOLID)                 # left floor, top edge y = 112
    g.box(10, 7, 12, 7, SOLID)               # right floor, the same height
    g.box(4, 7, 9, 7, ONEWAY)                # the bridge between them
    g.box(4, 8, 9, 8, SPIKE)                 # the pit under it
    # Standing on the bridge Kaya covers rows 5 and 6. A ceiling reaching row 5
    # leaves exactly one tile; leaving row 5 open gives her two and she fits.
    if not fixed:
        g.box(4, 5, 9, 5, SOLID)
    g.ent("player_spawn", 2, 6)
    g.ent("exit", 11, 6)
    g.hop("spawn", "exit", "human")
    return g


# ------------------------------------------------------------ (c) short door
def short_door(fixed):
    """Defect 3: a door one tile tall for a 22 px player.

    The door opened, so the tile was clear, so the checker passed it. What it
    never asked was whether a 22 px body fits in the passage the door sits in.
    Kaya collects the key, walks up to the wall, and stops short of a door she
    can see through and never enter.
    """
    g = Grid(14, 9)
    g.box(1, 5, 12, 6, EMPTY)                # the two chambers
    g.box(1, 7, 12, 7, SOLID)                # one continuous floor
    g.box(6, 5, 8, 6, SOLID)                 # the dividing wall
    g.box(6, 6, 8, 6, EMPTY)                 # with a one-tile passage through it
    if fixed:
        g.box(6, 5, 8, 5, EMPTY)             # the repair: make it two tiles
    g.ent("player_spawn", 2, 6)
    g.ent("key_yellow", 4, 6)
    g.ent("door_yellow", 7, 6)
    g.ent("exit", 11, 6)
    g.hop("spawn", "key_yellow", "human")
    g.hop("key_yellow", "door_yellow", "human")
    g.hop("door_yellow", "exit", "human")
    return g


BANK_BROKEN = 3      # two tiles proud of the water - out of reach
BANK_FIXED = 4       # one tile proud - clears, and that one tile is the margin


# ---------------------------------------------------------------- (d) the bank
def fish_bank(fixed):
    """Defect 4: a fish that cannot clear the bank out of the water.

    The hop height was never compared to the bank. data/forms/fish.json gives
    surface_hop -210 px/s against gravity 900, so a fish breaking the surface
    gets roughly 24 px of rise - which clears a bank one tile proud of the
    water and not one two tiles proud. BANK_* are measured, not guessed; the
    margin is recorded in REPORT.md.
    """
    g = Grid(14, 10)
    g.box(1, 1, 12, 8, EMPTY)
    g.box(1, 5, 3, 8, SOLID)                 # the ledge Kaya starts on
    g.box(4, 5, 9, 5, WATER_TOP)             # surface at y = 80
    g.box(4, 6, 9, 8, WATER)
    bank = BANK_FIXED if fixed else BANK_BROKEN
    g.box(10, bank, 12, 8, SOLID)
    g.ent("player_spawn", 2, 4)
    g.ent("pad_fish", 6, 7)
    g.ent("exit", 11, bank - 1)
    g.hop("spawn", "pad_fish", "human")
    g.hop("pad_fish", "exit", "fish")
    return g


# ------------------------------------------------------------- (e) sealed in
def sealed_spawn(fixed):
    """Defect 5: a spawn sealed behind a wall.

    Jumps only ever checked the destination, never whether anything stood in
    between, so a level could put the exit somewhere no body could travel to.
    The wall here is twenty tiles tall and there is no way over, under or
    through it.
    """
    g = Grid(14, 23)
    g.box(1, 17, 12, 20, EMPTY)              # two chambers, four tiles tall
    g.box(1, 21, 12, 21, SOLID)              # the floor under both
    g.box(6, 1, 6, 20, SOLID)                # a wall twenty tiles tall
    if fixed:
        g.box(6, 19, 6, 20, EMPTY)           # the repair: a two-tile doorway
    g.ent("player_spawn", 3, 20)
    g.ent("exit", 9, 20)
    g.hop("spawn", "exit", "human")
    return g


# ------------------------------------------------------------- (f) capped shaft
def capped_shaft(fixed):
    """Defect 6: a shaft capped across its full width by a solid slab.

    Vertical moves were never checked at all, so a lid over the whole shaft
    read as open sky. The frog's real apex is 5.34 tiles - plenty to reach the
    lid, and no help whatsoever in getting past it. Its head stops one tile
    short of the exit and stays there.
    """
    g = Grid(14, 12)
    g.box(5, 1, 7, 9, EMPTY)                 # the shaft, three tiles wide
    g.box(1, 10, 12, 10, SOLID)              # its floor
    g.box(5, 6, 7, 6, SOLID)                 # the lid, right across it
    if fixed:
        g.box(5, 6, 6, 6, EMPTY)             # the repair: a gap to hop through
    # The pad sits under the gap, not across the shaft from it. Greedy
    # best-first on manhattan distance cannot see that stepping sideways is
    # what unlocks the climb, so a pad on the far wall turns a four-expansion
    # hop into a four-thousand-expansion one. Route waypoints belong on the
    # natural path — see REPORT.md.
    g.ent("player_spawn", 7, 9)
    g.ent("pad_frog", 5, 9)
    g.ent("exit", 6, 5)
    g.hop("spawn", "pad_frog", "human")
    g.hop("pad_frog", "exit", "frog")
    return g


# ------------------------------------------------------ (g) silence is not a pass
def no_route(declared):
    """ADR 005: a level with no `route` fails the gate.

    This corridor is trivially walkable, which is the point — it fails for the
    one reason that it never said how it was meant to be finished.
    """
    g = Grid(14, 9)
    g.box(1, 5, 12, 6, EMPTY)
    g.box(1, 7, 12, 7, SOLID)
    g.ent("player_spawn", 2, 6)
    g.ent("exit", 11, 6)
    if declared:
        g.hop("spawn", "exit", "human")
    return g


CASES = [
    ("a_vine_no_exit", "VINE WITH NO EXIT", vine_no_exit),
    ("b_oneway_headroom", "ONE-WAY, ONE TILE OF HEADROOM", oneway_headroom),
    ("c_short_door", "A DOOR TOO SHORT TO WALK THROUGH", short_door),
    ("d_fish_bank", "A BANK THE FISH CANNOT CLEAR", fish_bank),
    ("e_sealed_spawn", "SEALED IN", sealed_spawn),
    ("f_capped_shaft", "A SHAFT WITH A LID", capped_shaft),
]


def main():
    for name, title, build in CASES:
        build(False).write(name, title)
        build(True).write(name + "_fixed", title + " (REPAIRED)")
        print("wrote", name, "and", name + "_fixed")
    no_route(False).write("g_no_route", "A LEVEL THAT NEVER SAYS HOW")
    print("wrote g_no_route")


if __name__ == "__main__":
    main()
