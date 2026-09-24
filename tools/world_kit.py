#!/usr/bin/env python3
"""Authoring shapes for the four new worlds of docs/plan-20-levels.md.

`tools/gen_levels.py` gives us a `Grid` with eighteen methods, all of them
jungle: `ground`, `vine`, `canopy`, `trunk`, `crates`. Twenty levels across
SUNKEN RUINS, THERMAL HEIGHTS, TERMITE DEEPS and THE OBSIDIAN NEST need
different shapes. This module is that vocabulary.

It **wraps** a Grid, it does not subclass or modify one:

    from gen_levels import Grid
    from world_kit import Kit, RUINS

    g = Grid(50, 30)
    k = Kit(g, RUINS)
    k.fill_bg(); k.shell()
    k.flooded_chamber(2, 12, 46, 16, surface=13)
    k.audit()                      # <- raises if any shape is now untraversable
    return g

Three things in here matter more than the shapes.

**1. A helper refuses to draw geometry a human cannot traverse.**
Every historical defect in this project was a step, a lid or a doorway that the
checker believed in and the character could not make. The measured numbers are
in `LIMITS`, with their provenance, and a helper that is asked for a step
outside them raises instead of drawing it.

**2. `audit()` re-checks the finished grid, not the draw call.**
Both of jungle_3's and jungle_5's near-misses were draw ORDER: a ledge written
after a vine overwrote the vine's top two tiles and left a gap nobody could
jump, and the level still "used the helper correctly". So every helper files
*claims* -- this tile must be standable, this shaft must still have a mouth,
this ladder must still have somewhere to step off -- and `audit()` evaluates
them against the grid as it finally stands. Call it last.

**3. What is in here is a filter, not a proof.**
`audit()` is a model, and this project's six shipped defects were all a model
that was nearly right. `tools/prove.sh` playing the level with the shipping
movement code is the proof (ADR 005). The kit's job is to stop the obvious
class of error before the expensive prover starts, and to fail loudly about
what it cannot check at all -- see `Kit.unproven`.

Self-test and proof rooms:

    python3 tools/world_kit.py --selftest
    python3 tools/world_kit.py --emit-proofs
    tools/prove.sh --level-file=res://tests/fixtures/world_kit/<name>.json
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROOF_DIR = os.path.join(ROOT, "tests/fixtures/world_kit")


class WorldKitError(Exception):
    """Raised for geometry the kit will not draw, and by audit() for geometry
    that stopped being traversable after something else was drawn over it."""


# --------------------------------------------------------------- tile lookup
#
# Characters are NOT hardcoded here. The legend that names the new worlds'
# tiles is another agent's file and is still being written, so a palette is
# declared in terms of the tile NAMES in data/tiles.json -- which already
# exist, ids 200-291 -- and the character is resolved at draw time out of
# data/level_legend.json. The instant that file gains a character for
# "ruin_stone", every ruins helper starts emitting ruin_stone. Until then the
# palette falls back to an understudy tile with the same gameplay flags, and
# records the substitution so nothing silently claims to be what it is not.

def _read(rel):
    with open(os.path.join(ROOT, rel)) as f:
        return json.load(f)


class _Tiles:
    def __init__(self):
        raw = _read("data/tiles.json")["tiles"]
        legend = _read("data/level_legend.json")["legend"]
        self.by_name = {}
        self.by_id = {}
        for sid, t in raw.items():
            self.by_id[int(sid)] = t
            if "name" in t:
                self.by_name[t["name"]] = int(sid)
        # A legend may map several characters to one id; first wins, sorted so
        # the choice does not depend on dict order.
        self.char_of_id = {}
        for ch in sorted(legend):
            self.char_of_id.setdefault(int(legend[ch]), ch)
        self.flags_of_char = {ch: raw.get(str(tid), {}) for ch, tid in legend.items()}

    def char_for_name(self, name):
        tid = self.by_name.get(name)
        if tid is None:
            raise WorldKitError(
                "no tile named '%s' in data/tiles.json -- the kit is asking for "
                "a tile that does not exist" % name)
        return self.char_of_id.get(tid)

    def flags_for_name(self, name):
        tid = self.by_name.get(name)
        return self.by_id.get(tid, {}) if tid is not None else {}


_TILES = None


def tiles():
    global _TILES
    if _TILES is None:
        _TILES = _Tiles()
    return _TILES


def reload_tiles():
    """Drop the cache. Only the self-test needs this."""
    global _TILES
    _TILES = None


# ----------------------------------------------------------------- palettes
#
# Roles, not tile names, are what the helpers draw with. The same
# `flooded_chamber` call produces ruin stone in world 2 and jungle stone in a
# test fixture; only the palette changes.

ROLES = (
    "bg",            # background fill for the whole room
    "solid",         # the workhorse solid
    "solid_alt",     # its autotile partner, for banding
    "packed",        # solid fill under a floor (dirt / silt / scree / plate)
    "block",         # a second decorative solid
    "oneway",        # platform: stand on top, pass through from below
    "ladder",        # climbable column
    "hazard",        # touching it hurts
    "water",         # swimmable body
    "water_top",     # its surface row
    "decor",         # background dressing, no collision
    "void",          # dark background, no collision
    "breakable",     # weapon-breakable solid
    "shoulder",      # solid breakable by shouldering into it (break_hold > 0)
    "glowwall",      # the luminous wall TERMITE DEEPS is about
    "rubble",        # cheap breakable fill
    "cur_right", "cur_left", "cur_up", "cur_down",
    "cur_right_fast", "cur_left_fast",
    "updraft", "updraft_strong", "downdraft",
    "gust_right", "gust_left",
    "switch_a_on", "switch_a_off", "switch_b_on", "switch_b_off",
)

## Every world role's stand-in, drawn from the tiles that already have
## characters today. Flags match, so the SHAPE a helper draws is identical and
## can be proved now; only the art and the world's own verb differ.
##
## The current/draft roles are in here for the same reason but they are the one
## place where the stand-in changes what the level MEANS: a channel of plain
## water has the walls of a current channel and none of the push. Substituting
## them is allowed because the walls are worth proving, and every substitution
## is recorded in `Palette.substituted` and re-reported by `Kit.audit()` so a
## proof over a stand-in is never mistaken for a proof of the real thing.
UNDERSTUDY = {
    "bg": "bg_rock",
    "solid": "stone",
    "solid_alt": "stone_mossy",
    "packed": "dirt",
    "block": "metal",
    "oneway": "wood_platform",
    "ladder": "vine",
    "hazard": "spikes",
    "water": "water",
    "water_top": "water_top",
    "decor": "tree_trunk",
    "void": "bg_dark",
    "breakable": "crate",
    "shoulder": "crate",
    "glowwall": "crate",
    "rubble": "crate",
    "cur_right": "water", "cur_left": "water",
    "cur_up": "water", "cur_down": "water",
    "cur_right_fast": "water", "cur_left_fast": "water",
    "updraft": "empty", "updraft_strong": "empty", "downdraft": "empty",
    "gust_right": "empty", "gust_left": "empty",
    "switch_a_on": "switch_block_a_on", "switch_a_off": "switch_block_a_off",
    "switch_b_on": "switch_block_b_on", "switch_b_off": "switch_block_b_off",
}

## Roles whose stand-in keeps the shape but drops the gameplay verb. Named
## separately because `audit()` reports these louder than a recolour.
VERB_ROLES = frozenset(
    r for r in ROLES
    if r.startswith(("cur_", "updraft", "downdraft", "gust_")))


class Palette:
    """role -> tile name, resolved to a character against the live legend."""

    def __init__(self, world, roles):
        self.world = world
        self.roles = dict(roles)
        self.substituted = {}      # role -> (wanted tile name, tile used)

    def name(self, role):
        if role not in ROLES:
            raise WorldKitError("'%s' is not a kit role; expected one of %s"
                                % (role, ", ".join(ROLES)))
        n = self.roles.get(role)
        if n is None:
            raise WorldKitError(
                "palette '%s' declares no tile for role '%s'" % (self.world, role))
        return n

    def char(self, role):
        want = self.name(role)
        ch = tiles().char_for_name(want)
        if ch is not None:
            return ch
        stand_in = UNDERSTUDY.get(role)
        if stand_in is not None:
            ch = tiles().char_for_name(stand_in)
            if ch is not None:
                self.substituted[role] = (want, stand_in)
                return ch
        raise WorldKitError(
            "palette '%s' role '%s' wants tile '%s', which has no character in "
            "data/level_legend.json, and its understudy '%s' has none either. "
            "That legend is another agent's file; see REPORT.md for the list of "
            "tiles this kit needs characters for."
            % (self.world, role, want, stand_in))

    def flags(self, role):
        return tiles().flags_for_name(self.name(role))

    def missing(self):
        """Roles whose declared tile has no character yet. Sorted, so the list
        is a stable thing to paste into a report."""
        out = []
        for role in ROLES:
            if role not in self.roles:
                continue
            want = self.roles[role]
            if tiles().char_for_name(want) is None:
                out.append((role, want))
        return out


JUNGLE = Palette("jungle", {
    "bg": "bg_rock", "solid": "stone", "solid_alt": "stone_mossy",
    "packed": "dirt", "block": "metal", "oneway": "wood_platform",
    "ladder": "vine", "hazard": "spikes", "water": "water",
    "water_top": "water_top", "decor": "tree_trunk", "void": "bg_dark",
    "breakable": "crate", "shoulder": "crate",
    "switch_a_on": "switch_block_a_on", "switch_a_off": "switch_block_a_off",
    "switch_b_on": "switch_block_b_on", "switch_b_off": "switch_block_b_off",
})

RUINS = Palette("sunken_ruins", {
    "bg": "ruin_wall", "solid": "ruin_stone", "solid_alt": "ruin_stone_algae",
    "packed": "ruin_silt", "block": "ruin_grate", "oneway": "ruin_slab",
    "ladder": "kelp", "hazard": "ruin_urchin", "water": "water",
    "water_top": "water_top", "decor": "ruin_column", "void": "ruin_deep",
    "breakable": "ruin_cracked", "shoulder": "cracked_stone",
    "rubble": "rubble",
    "cur_right": "water_current_right", "cur_left": "water_current_left",
    "cur_up": "water_current_up", "cur_down": "water_current_down",
    "cur_right_fast": "water_current_right_fast",
    "cur_left_fast": "water_current_left_fast",
})

HEIGHTS = Palette("thermal_heights", {
    "bg": "heights_wall", "solid": "heights_rock",
    "solid_alt": "heights_rock_sun", "packed": "heights_scree",
    "block": "heights_basalt", "oneway": "heights_plank",
    "ladder": "heights_chain", "hazard": "heights_vent",
    "water": "water", "water_top": "water_top",
    "decor": "heights_stack", "void": "heights_air",
    "breakable": "heights_shell", "shoulder": "cracked_stone",
    "rubble": "rubble",
    "updraft": "updraft", "updraft_strong": "updraft_strong",
    "downdraft": "downdraft",
    "gust_right": "gust_right", "gust_left": "gust_left",
})

DEEPS = Palette("termite_deeps", {
    "bg": "deep_comb", "solid": "deep_earth", "solid_alt": "deep_crust",
    "packed": "deep_packed", "block": "deep_chitin", "oneway": "deep_shelf",
    "ladder": "deep_ladder", "hazard": "deep_spore",
    "water": "water", "water_top": "water_top",
    "decor": "deep_root", "void": "deep_void",
    # deep_glowwall (270) declares no break_hold, so only a WEAPON opens it and
    # the frog and the bird have none. `luminous_wall` (214) carries
    # break_hold 0.4, so any form can shoulder through it. The kit points
    # `glowwall` at the one every form can open and keeps deep_glowwall for
    # decoration; see Kit.glow_wall().
    "glowwall": "luminous_wall",
    "breakable": "deep_glowwall", "shoulder": "termite_wall",
    "rubble": "rubble",
})

NEST = Palette("obsidian_nest", {
    "bg": "nest_wall", "solid": "obsidian", "solid_alt": "obsidian_hot",
    "packed": "nest_plate", "block": "nest_block", "oneway": "nest_ledge",
    "ladder": "nest_chain", "hazard": "nest_shard",
    "water": "water", "water_top": "water_top",
    "decor": "nest_vein", "void": "nest_void",
    "breakable": "nest_crust", "shoulder": "cracked_stone",
    "rubble": "rubble",
    "switch_a_on": "switch_block_a_on", "switch_a_off": "switch_block_a_off",
    "switch_b_on": "switch_block_b_on", "switch_b_off": "switch_block_b_off",
})

PALETTES = {p.world: p for p in (JUNGLE, RUINS, HEIGHTS, DEEPS, NEST)}


# ------------------------------------------------------------------- limits
#
# PROVENANCE, because the whole point of this table is that it is not reasoned:
#
# MEASURED in the running game, recorded in tools/build_levels.py and in the
# tapes under proofs/:
#   * frog apex, jump held to full height ............ 5.34 tiles
#   * frog apex, jump released early (jump_cut 0.5) .. ~4.37 tiles
#     A 4-tile step therefore has about six pixels of margin and lands or
#     misses on rounding. jungle_4 shipped 4-tile rungs; some caught and some
#     dropped the player to the bottom of the shaft. The climb is 3-tile steps
#     now. RISE["frog"] = 3 is that session's conclusion.
#   * human 2-tile steps and 3-tile flat gaps: jungle_1 (spike pit, cols
#     14-16) and jungle_2 (gap at cols 22-24) both prove in proofs/*.tape.json.
#   * bird 6 across and 5 up: jungle_4's perch_2 -> perch_3 hop, 68 frames, in
#     proofs/jungle_4.tape.json. That is the largest bird hop this project has
#     ever proved, so it is the ceiling here rather than a guess at one.
#   * fish onto a 16 px bank: defect 4 was a fish that could not hop a bank.
#     surface_hop -210 against gravity 900 is 24.5 px, so one tile clears and
#     two do not. BANK_RISE = 1.
#
# DERIVED from data/forms/*.json the same way tools/reachability.py does
# (apex = jump_vel^2 / 2*gravity; flat reach = max_run * 2*jump_vel/gravity),
# and then rounded DOWN, because the frog measurement is the standing proof
# that the derivation is optimistic:
#   human  apex 2.78 tiles, flat reach 4.6 -> rise 2, gap 3
#   frog   apex 5.16 tiles, flat reach 3.8 -> rise 3, gap 3
#   bird   apex 2.41 tiles, flat reach 5.5 -> it flaps; see above
#   fish   apex 0.78 tiles, flat reach 0.8 -> it cannot jump on land at all
#
# MEASURED BY THIS FILE'S OWN PROOF ROOMS, with tools/prove.sh --budget=12000
# over tests/fixtures/world_kit/. These are the runs, not a summary of them:
#
#   gap_human_3   PROVED      46 expansions,  1.4 s
#   gap_human_4   PROVED   2,923 expansions,   69 s
#   gap_human_5   PROVED   6,448 expansions,   64 s
#   gap_frog_3    PROVED     101 expansions,  1.7 s
#   gap_frog_4    FAILED  12,000 spent, closest approach 36.1 px
#   gap_frog_6    FAILED  12,000 spent, closest approach 64.0 px
#
# Two conclusions, and they are different from each other:
#
# LIMITS["frog"]["gap"] = 3 is a REAL CEILING. Four tiles fails by over two
# tiles of closest approach. The frog's enormous jump buys height, not
# distance -- max_run 62 against the human's 108 -- so it clears LESS
# horizontally than Kaya on foot, which is the opposite of what the jump looks
# like. This is the one number in the table the prover simply agrees with.
#
# LIMITS["human"]["gap"] = 3 is a MARGIN, not a ceiling. Three, four and five
# tiles all prove. Two reasons to keep 3 anyway:
#
#   * cost. 46 expansions at three tiles, 2,923 at four, 6,448 at five -- 140x
#     for two tiles, because the manhattan frontier dives into the pit (ADR
#     005's addendum, in one room). Across twenty levels that is the difference
#     between a gate that runs and a gate that is switched off.
#   * the prover is a better player than a human. It finds the one jump length
#     that works. jungle_1 records ten hand-tried lengths over a THREE-tile gap
#     that all either fell short or sailed over the shelf beyond, and that is
#     the level a person actually plays. See WIDE_GAP / MIN_LANDING below.
#
# AND THE RISE ROOMS, which say something uncomfortable:
#
#   rise_frog_3   PROVED  2,582 expansions,  33 s   (four 3-tile steps)
#   rise_frog_4   PROVED    913 expansions,   5 s   (four 4-TILE steps)
#   rise_human_3  FAILED 12,000 spent, closest approach 123 px
#   rise_human_2  see the "coarse" note on PROOFS -- every step proves on its
#                 own; the whole climb in one hop does not fit the budget.
#
# So LIMITS["frog"]["rise"] = 3 is NOT the prover's verdict. The prover clears
# four tiles comfortably. It clears four tiles because a best-first search finds
# the one input that works, and the input that works is a jump held to full
# height: apex 5.34 tiles. A jump released early is cut by jump_cut 0.5 and tops
# out near 4.37 -- about six pixels over a 4-tile step -- which is why jungle_4's
# 4-tile rungs caught sometimes and dropped the player to the bottom of the
# shaft other times, in a human's hands.
#
# The kit keeps 3 anyway, and this is the reason to write down rather than the
# number: the prover proves a route EXISTS, and ADR 005 says plainly that it
# does not prove the level is fair to a human. A 4-tile frog step is provable
# and unplayable. That gap is the only thing in this table the gate cannot see,
# so it is the only number here that a prover run must not be allowed to relax.
#
# See REPORT.md section 3 for the rest of the rooms.

LIMITS = {
    #          max rise in tiles, max flat gap in tiles
    "human": {"rise": 2, "gap": 3},
    "frog":  {"rise": 3, "gap": 3},
    "bird":  {"rise": 5, "gap": 6},
    "fish":  {"rise": 1, "gap": 1},
}

## A gap of this many tiles or more needs a landing shelf at least
## MIN_LANDING wide. jungle_1 records ten measured jump lengths from branch_a
## that all either fell into a 3-tile gap or sailed clean over the 4-wide
## platform beyond it: at full run the landing window is narrower than the
## platform, and braking in mid-air overshoots backwards into the gap.
WIDE_GAP = 3
MIN_LANDING = 4

## A body is 22 px tall (data/forms/human.json hitbox h), so it needs two tiles.
## Defect 2 was a one-way platform with one tile of headroom and defect 3 was a
## door one tile tall.
BODY_TILES = 2

## The fish drowns out of water after air_seconds 2.6 and swims at 92 px/s, so
## it covers roughly 240 px -- fifteen tiles -- between breaths in a straight
## line, less when it is weaving. Air pockets further apart than this are a
## drowning, not a level.
AIR_POCKET_SPAN = 14

## flap_cost 12 against max_stamina 100 is eight flaps, and flap_interval 0.24
## spreads them over 1.9 s. A bird crossing that needs more than six perch-to-
## perch hops without a perch to refill on is a stamina failure waiting to
## happen; stamina_regen 46/s only tops up while gliding or perched.
BIRD_HOPS_PER_PERCH = 6


def check_rise(dy, form, what):
    """dy is tiles GAINED (positive = upward). Raises on an impossible step."""
    lim = LIMITS.get(form)
    if lim is None:
        raise WorldKitError("%s: no measured limits for form '%s'" % (what, form))
    if dy > lim["rise"]:
        raise WorldKitError(
            "%s: a %d-tile rise, but the %s tops out at %d. Measured, not "
            "modelled -- see LIMITS in tools/world_kit.py."
            % (what, dy, form, lim["rise"]))


def check_gap(dx, form, what):
    lim = LIMITS.get(form)
    if lim is None:
        raise WorldKitError("%s: no measured limits for form '%s'" % (what, form))
    if dx > lim["gap"]:
        raise WorldKitError(
            "%s: a %d-tile gap, but the %s clears %d. Measured, not modelled -- "
            "see LIMITS in tools/world_kit.py." % (what, dx, form, lim["gap"]))


# -------------------------------------------------------------------- probe

class Probe:
    """Read-only geometry questions about a Grid's fg layer.

    Deliberately a separate object from Kit: audit() asks these questions of
    the grid as it FINALLY stands, long after the helper that drew it ran.
    """

    def __init__(self, grid, switches=None):
        self.g = grid
        # Switch blocks: which group states are in force. None means "treat
        # every switch block as passable", which is what tools/reachability.py
        # does and is the right answer when you do not know the state.
        self.switches = switches
        self._flags = tiles().flags_of_char

    def ch(self, x, y):
        if 0 <= x < self.g.w and 0 <= y < self.g.h:
            return self.g.fg[y][x]
        return None

    def f(self, x, y):
        return self._flags.get(self.ch(x, y), {})

    def solid(self, x, y):
        if x < 0 or x >= self.g.w or y < 0:
            return True                      # walls and ceiling
        if y >= self.g.h:
            return False                     # a bottomless drop, not a floor
        t = self.f(x, y)
        if "switch_group" in t:
            if self.switches is None:
                return False
            return bool(t.get("switch_state")) == bool(
                self.switches.get(int(t["switch_group"]), False))
        return bool(t.get("solid"))

    def oneway(self, x, y):
        return bool(self.f(x, y).get("oneway"))

    def ladder(self, x, y):
        return bool(self.f(x, y).get("ladder"))

    def water(self, x, y):
        return bool(self.f(x, y).get("water"))

    def hazard(self, x, y):
        return bool(self.f(x, y).get("hazard"))

    def clear(self, x, y, tall=BODY_TILES):
        """`tall` tiles of non-solid space with the feet in tile y."""
        return all(not self.solid(x, y - i) for i in range(tall))

    def standable(self, x, y, tall=BODY_TILES):
        if not self.clear(x, y, tall):
            return False
        return (self.solid(x, y + 1) or self.oneway(x, y + 1)
                or self.ladder(x, y) or self.water(x, y))


def path_clear(probe, x1, y1, x2, y2, rise):
    """Can a body actually travel between two standing tiles?

    Rise in the start column to some travel row, cross at that row, drop into
    the destination column. Deliberately the same shape as the check in
    tools/reachability.py, and re-implemented rather than imported because that
    module calls main() at import time. The two cases it exists for are pinned
    in selftest(): a shaft capped across its full width (defect 6) and a wall
    in a column the arc crosses (defect 5).
    """
    step = 1 if x2 >= x1 else -1
    for r in range(max(0, y1 - rise), min(y1, y2) + 1):
        if any(probe.solid(x1, yy) for yy in range(max(0, r - 1), y1)):
            continue
        if any(probe.solid(xi, yy)
               for xi in range(x1 + step, x2 + step, step)
               for yy in (r, r - 1) if yy >= 0):
            continue
        if any(probe.solid(x2, yy) for yy in range(max(0, r - 1), y2 + 1)):
            continue
        return True
    return False


# ---------------------------------------------------------------------- kit

class Kit:
    """Draws world shapes onto a Grid and remembers what it promised.

    Every helper that creates something a player must use files a claim.
    `audit()` checks the claims against the finished grid, which is the only
    moment at which they are true or false -- a later helper can and has drawn
    over an earlier one's vine.
    """

    def __init__(self, grid, palette, form="human"):
        self.g = grid
        self.pal = palette if isinstance(palette, Palette) else PALETTES[palette]
        ## The form the kit assumes for unqualified geometry checks. Helpers
        ## that are about one form (a bird deck, a fish colonnade) take their
        ## own and ignore this.
        self.form = form
        self.claims = []          # (kind, payload, why)
        self.unproven = []        # things tools/prove.sh cannot check at all
        self.notes = []

    # -- palette ------------------------------------------------------------
    def ch(self, role):
        return self.pal.char(role)

    def _claim(self, kind, why, **payload):
        payload["why"] = why
        self.claims.append((kind, payload))

    def _release(self, x, y):
        """Drop the clear/stand claims on one tile.

        Called when a later helper deliberately plugs something an earlier one
        carved -- a breakable wall across a corridor, a switch gate across a
        room. The corridor's claim really has become false, and the difference
        between that and the bug this system exists to catch is intent, which
        only the plugging helper knows.
        """
        keep = []
        for kind, c in self.claims:
            if kind in ("clear", "stand") and c["x"] == x:
                if kind == "stand" and c["y"] == y:
                    continue
                if kind == "clear" and c["y"] - c.get("tall", 1) < y <= c["y"]:
                    continue
            keep.append((kind, c))
        self.claims = keep

    def note(self, msg):
        if msg not in self.notes:
            self.notes.append(msg)

    def cannot_prove(self, msg):
        """Record a shape tools/prove.sh is structurally unable to check.

        Not a warning to be skimmed: a hop declared across one of these will
        fail the gate, so the route has to go round it. The breakable walls of
        TERMITE DEEPS are the whole reason this exists -- tools/solver/sim.gd
        models pads, keys, doors and switches, and nothing at all that breaks
        a tile.
        """
        if msg not in self.unproven:
            self.unproven.append(msg)

    # -- primitives, in palette terms --------------------------------------
    def put(self, x, y, role, layer="fg"):
        self.g.put(x, y, self.ch(role), layer)

    def rect(self, x, y, w, h, role, layer="fg"):
        self.g.rect(x, y, w, h, self.ch(role), layer)

    def clear_rect(self, x, y, w, h):
        self.g.rect(x, y, w, h, ".")

    def fill_bg(self, role="bg"):
        self.rect(0, 0, self.g.w, self.g.h, role, "bg")

    def fill_solid(self, role="solid"):
        """Solid rock everywhere, for a level that is carved rather than built.

        TERMITE DEEPS and the prover both want this: a tunnel cut out of rock
        has a tiny reachable state space, so a failed search exhausts its
        frontier instead of burning its whole budget wandering open sky.
        """
        self.rect(0, 0, self.g.w, self.g.h, role)

    def shell(self, thickness=1, role="solid"):
        """Seal the level's border so nothing walks off the edge of the world."""
        t = thickness
        self.rect(0, 0, self.g.w, t, role)
        self.rect(0, self.g.h - t, self.g.w, t, role)
        self.rect(0, 0, t, self.g.h, role)
        self.rect(self.g.w - t, 0, t, self.g.h, role)

    # -- marks --------------------------------------------------------------
    def mark(self, name, x, y, form=None):
        """Name a standable tile, and promise that it still is one at audit.

        gen_levels.Grid._check_route already rejects a mark inside a solid
        tile. It does NOT check that there is a floor underneath, so a mark in
        mid-air passes generation and costs a whole prover run to discover.
        """
        self.g.mark(name, x, y)
        self._claim("stand", "mark '%s'" % name, x=x, y=y,
                    form=form or self.form)
        return name

    # -- shared shapes ------------------------------------------------------
    def floor(self, x, y, w, depth=None, cap="solid", fill="packed"):
        """A shelf: one capped row at `y`, `depth`-1 rows of fill beneath it."""
        depth = depth if depth is not None else self.g.h - y
        self.rect(x, y, w, 1, cap)
        if depth > 1:
            self.rect(x, y + 1, w, depth - 1, fill)
        return (x, y - 1, w)          # where a body stands on it

    def ledge(self, x, y, w, role="oneway", stand_form=None):
        """A platform you stand on top of at row y-1.

        Claims two tiles of headroom over the whole run, because defect 2 was a
        one-way platform with one tile of clearance: not "solid", so the
        pocket check skipped it, and nobody could ever be on it.
        """
        if w < 1:
            raise WorldKitError("ledge at (%d,%d): width %d" % (x, y, w))
        self.rect(x, y, w, 1, role)
        for xx in range(x, x + w):
            self._claim("clear", "ledge at (%d,%d) w%d" % (x, y, w),
                        x=xx, y=y - 1, tall=BODY_TILES)
        self._claim("stand", "ledge at (%d,%d) w%d" % (x, y, w),
                    x=x + w // 2, y=y - 1, form=stand_form or self.form)
        return (x, y - 1, w)

    def stair(self, x, y, count, rise, run, width, form=None,
              role="oneway", dx=1, unchecked=False):
        """`count` ledges climbing `rise` tiles each, `run` apart.

        The one helper that most directly encodes the lesson: `rise` is checked
        against the form's measured limit before a single tile is drawn, so a
        4-tile frog rung cannot be authored by accident.

        `unchecked=True` skips that check. It exists for exactly one caller --
        the proof rooms in this file, which have to build a staircase one tile
        PAST the limit so the prover can say where the limit actually is. A
        level that passes it is asserting that the table in LIMITS is wrong,
        which is a claim to make with a prover run and not with a keyword.

        Returns the list of (x, stand_row, w) for each ledge, bottom first.
        """
        form = form or self.form
        what = "stair at (%d,%d)" % (x, y)
        if not unchecked:
            check_rise(rise, form, what)
            if run > 0:
                # The horizontal part of a climbing step still has to be
                # reachable.
                check_gap(max(0, run - width), form, what)
        out = []
        cx, cy = x, y
        for i in range(count):
            out.append(self.ledge(cx, cy, width, role=role, stand_form=form))
            if i + 1 < count:
                nx, ny = cx + dx * run, cy - rise
                self._claim("step", "%s rung %d" % (what, i + 1),
                            x1=cx + (width - 1 if dx > 0 else 0), y1=cy - 1,
                            x2=nx + (0 if dx > 0 else width - 1), y2=ny - 1,
                            form=form)
                cx, cy = nx, ny
        return out

    def climb(self, col, top, bottom, landing="right", role="ladder",
              stand_form=None):
        """A climbable column from `top` to `bottom`, with somewhere to step off.

        Defect 1 was a vine with no exit at the top -- reachable on paper via a
        blind mid-air jump. ROOT HOLLOW then shipped one whose nearest ledge
        was an empty column away. So this claims a standable tile DIRECTLY
        beside the top of the column, and `landing` says which side.
        """
        if bottom < top:
            top, bottom = bottom, top
        self.g.rect(col, top, 1, bottom - top + 1, self.ch(role))
        sides = {"right": (1,), "left": (-1,), "both": (-1, 1)}.get(landing)
        if sides is None:
            raise WorldKitError("climb at col %d: landing '%s' is not "
                                "left/right/both" % (col, landing))
        self._claim("ladder_exit", "climb at col %d rows %d-%d" % (col, top, bottom),
                    col=col, top=top, sides=sides,
                    form=stand_form or self.form)
        return col, top, bottom

    def shaft(self, x, w, top, bottom, mouth=None, role="solid"):
        """Two walls `w` apart with a MOUTH in the roof and a way in at the foot.

        Defect 6: SKY BRANCH's chimney was capped across its full width. You
        climbed the whole thing and hit a lid, with the bird pad, the human pad
        and the exit all on the far side of it.

        `mouth` is (x0, x1) inclusive, in absolute columns, and must lie inside
        the shaft. The foot is left open for `mouth_height` tiles on the left
        wall so you can walk in -- jungle_4's left wall used to run to the
        floor and sealed the spawn in a box.
        """
        if w < BODY_TILES:
            raise WorldKitError(
                "shaft at col %d is %d tiles wide; a body is %d tiles and "
                "needs room to stand inside it" % (x, w, BODY_TILES))
        interior = (x + 1, x + w)             # inclusive columns between walls
        if mouth is None:
            mouth = (interior[0], min(interior[0] + 1, interior[1]))
        m0, m1 = mouth
        if m0 < interior[0] or m1 > interior[1] or m1 < m0:
            raise WorldKitError(
                "shaft at col %d: mouth %s is not inside the shaft interior "
                "(cols %d-%d)" % (x, mouth, interior[0], interior[1]))
        # Left wall stops BODY_TILES above the floor, and the foot is CARVED,
        # not merely claimed. jungle_4's left wall ran to the floor and sealed
        # the spawn and the frog pad in a box with the whole rest of the level
        # on the far side of it; a promise the helper does not keep itself is
        # how that happens twice.
        self.rect(x, top, 1, bottom - top + 1 - BODY_TILES, role)
        self.clear_rect(x, bottom - BODY_TILES + 1, 1, BODY_TILES)
        self.rect(x + w + 1, top, 1, bottom - top + 1, role)
        self._claim("mouth", "shaft at col %d rows %d-%d" % (x, top, bottom),
                    x0=interior[0], x1=interior[1], y=top - 1)
        self._claim("clear", "shaft foot at col %d" % x,
                    x=x, y=bottom, tall=BODY_TILES)
        return interior, (m0, m1)

    def doorway(self, x, y, h=BODY_TILES, wide=1):
        """Punch a hole a body actually fits through.

        Defect 3 was a door one tile tall against a 22 px character: the door
        opened, so the tile was clear, so the checker was happy.
        """
        if h < BODY_TILES:
            raise WorldKitError(
                "doorway at (%d,%d) is %d tile(s) tall; a body is %d"
                % (x, y, h, BODY_TILES))
        self.clear_rect(x, y - h + 1, wide, h)
        for xx in range(x, x + wide):
            self._claim("clear", "doorway at (%d,%d)" % (x, y),
                        x=xx, y=y, tall=h)
        return x, y

    def corridor(self, x, y, w, h=BODY_TILES):
        """Carve a horizontal run of clear space, feet on row y."""
        if h < BODY_TILES:
            raise WorldKitError("corridor at (%d,%d) is %d tiles tall; a body "
                                "is %d" % (x, y, h, BODY_TILES))
        self.clear_rect(x, y - h + 1, w, h)
        for xx in range(x, x + w):
            self._claim("clear", "corridor at (%d,%d) w%d" % (x, y, w),
                        x=xx, y=y, tall=h)
        return x, y, w

    def gap(self, x, y, w, form=None, landing_w=None):
        """Declare a jumpable gap between two shelves and check its width.

        `landing_w` is how wide the shelf on the far side is. A gap of
        WIDE_GAP or more onto a narrow shelf is the jungle_1 failure: ten
        measured jump lengths either fell short into the hole or sailed clean
        over the platform beyond it.
        """
        form = form or self.form
        what = "gap at (%d,%d) w%d" % (x, y, w)
        check_gap(w, form, what)
        if w >= WIDE_GAP and landing_w is not None and landing_w < MIN_LANDING:
            raise WorldKitError(
                "%s: a %d-tile gap onto a %d-tile shelf. At full run the "
                "landing window is narrower than the shelf and the jump sails "
                "over it -- jungle_1 measured ten lengths that all missed. "
                "Widen the landing to %d." % (what, w, landing_w, MIN_LANDING))
        self._claim("step", what, x1=x - 1, y1=y, x2=x + w, y2=y, form=form)
        return x, y, w

    # -- the audit ----------------------------------------------------------
    def audit(self, strict_verbs=False):
        """Check every claim against the grid as it now stands.

        Raises WorldKitError listing everything wrong. Call it as the last line
        of a level function: an earlier helper's ladder can be overwritten by a
        later helper's ledge, which is how THE WATERWAY and HEART OF THE GROVE
        both nearly shipped a climb that dead-ended.

        `strict_verbs=True` also fails when a palette role fell back to an
        understudy that drops the world's verb -- a current channel drawn out
        of plain water. Off by default so the shapes stay authorable before the
        legend lands; on in the self-test once it does.
        """
        p = Probe(self.g)
        bad = []
        for kind, c in self.claims:
            why = c["why"]
            if kind == "stand":
                if not p.standable(c["x"], c["y"]):
                    bad.append("%s: (%d,%d) is not standable -- %s"
                               % (why, c["x"], c["y"], self._diagnose(p, c)))
                elif p.hazard(c["x"], c["y"]):
                    bad.append("%s: (%d,%d) sits on a hazard"
                               % (why, c["x"], c["y"]))
            elif kind == "clear":
                if not p.clear(c["x"], c["y"], c["tall"]):
                    blocked = [c["y"] - i for i in range(c["tall"])
                               if p.solid(c["x"], c["y"] - i)]
                    bad.append("%s: (%d,%d) has no %d tiles of headroom; "
                               "solid at row(s) %s"
                               % (why, c["x"], c["y"], c["tall"],
                                  ",".join(str(r) for r in blocked)))
            elif kind == "wet":
                if not p.water(c["x"], c["y"]):
                    bad.append("%s: (%d,%d) is '%s', not water -- a fish route "
                               "runs dry there"
                               % (why, c["x"], c["y"], p.ch(c["x"], c["y"])))
                elif not p.clear(c["x"], c["y"], c["tall"]):
                    bad.append("%s: (%d,%d) has no %d tiles of swimmable room"
                               % (why, c["x"], c["y"], c["tall"]))
            elif kind == "step":
                rise = LIMITS[c["form"]]["rise"]
                if not path_clear(p, c["x1"], c["y1"], c["x2"], c["y2"], rise):
                    bad.append("%s: nothing gets a body from (%d,%d) to (%d,%d) "
                               "as the %s -- something is drawn across the arc"
                               % (why, c["x1"], c["y1"], c["x2"], c["y2"],
                                  c["form"]))
            elif kind == "mouth":
                y = c["y"]
                open_cols = [x for x in range(c["x0"], c["x1"] + 1)
                             if not p.solid(x, y)]
                if not open_cols:
                    bad.append("%s: capped across its full width at row %d. A "
                               "shaft needs a mouth (defect 6)." % (why, y))
            elif kind == "ladder_exit":
                col, top = c["col"], c["top"]
                ok = False
                for y in range(top, min(top + 3, self.g.h)):
                    if not p.ladder(col, y) and y == top:
                        # the column itself was overwritten
                        break
                    for dx in c["sides"]:
                        if p.standable(col + dx, y):
                            ok = True
                if not p.ladder(col, top):
                    bad.append("%s: the top of the column is no longer "
                               "climbable -- something was drawn over it"
                               % why)
                elif not ok:
                    bad.append("%s: nothing standable within 3 rows of the top "
                               "on the %s. A ladder needs a landing (defect 1)."
                               % (why, "/".join("left" if d < 0 else "right"
                                                for d in c["sides"])))
            else:
                raise WorldKitError("audit: unknown claim kind '%s'" % kind)
        if strict_verbs:
            for role, (want, used) in sorted(self.pal.substituted.items()):
                if role in VERB_ROLES:
                    bad.append("palette role '%s' wants '%s' and got '%s': the "
                               "shape is drawn but the verb is gone"
                               % (role, want, used))
        if bad:
            raise WorldKitError(
                "%s: %d claim(s) failed after the grid was finished:\n  %s"
                % (self.pal.world, len(bad), "\n  ".join(bad)))
        return self.report()

    def _diagnose(self, p, c):
        x, y = c["x"], c["y"]
        if p.solid(x, y):
            return "tile '%s' is solid" % p.ch(x, y)
        if not p.clear(x, y):
            return "no headroom: '%s' above it" % p.ch(x, y - 1)
        return "nothing under it: '%s' below" % (p.ch(x, y + 1) or "off-grid")

    def report(self):
        """What the kit could not check, and what it drew with a stand-in."""
        lines = []
        for role, (want, used) in sorted(self.pal.substituted.items()):
            tag = "VERB LOST" if role in VERB_ROLES else "recolour"
            lines.append("  substituted  %-16s %s -> %s  (%s)"
                         % (role, want, used, tag))
        for n in self.notes:
            lines.append("  note         %s" % n)
        for u in self.unproven:
            lines.append("  UNPROVABLE   %s" % u)
        return lines


# ==========================================================================
# The four worlds.
#
# These are free functions taking the Kit as their first argument and attached
# to Kit at the bottom of the file, so each world's vocabulary reads as one
# contiguous block instead of disappearing into a 900-line class body. Both
# call styles work:  k.flooded_chamber(...)  and  world_kit.flooded_chamber(k, ...)
# ==========================================================================

# ------------------------------------------------------- SUNKEN RUINS (w2)

def flooded_chamber(k, x, y, w, h, surface, wall=True, bed=True):
    """A walled chamber, flooded from row `surface` down.

    Interior is cols x..x+w-1, rows y..y+h-1. `surface` is the row that carries
    the water_top tile, so rows surface+1..y+h-1 are open water and rows
    y..surface-1 are the air above it.

    Refuses two shapes outright:

    * water less than two tiles deep. The fish hitbox is 14x9 px, but a
      one-tile channel puts its head in the surface tile and its belly on the
      bed, and there is nowhere to weave. Two tiles is the floor.
    * no air above the surface. The fish drowns in `air_seconds` 2.6 and the
      human wades; a chamber flooded to its own ceiling is a chamber you cannot
      surface in.
    """
    if w < 1 or h < 1:
        raise WorldKitError("flooded_chamber at (%d,%d): %dx%d" % (x, y, w, h))
    if not (y <= surface < y + h):
        raise WorldKitError(
            "flooded_chamber at (%d,%d) %dx%d: surface row %d is outside its "
            "interior (rows %d-%d)" % (x, y, w, h, surface, y, y + h - 1))
    depth = (y + h - 1) - surface + 1
    if depth < 2:
        raise WorldKitError(
            "flooded_chamber at (%d,%d): %d tile(s) of water. A fish needs two "
            "-- one tile puts its head in the surface and its belly on the bed."
            % (x, y, depth))
    if surface == y:
        raise WorldKitError(
            "flooded_chamber at (%d,%d): flooded to its own ceiling, so there "
            "is nowhere to surface. The fish drowns after air_seconds 2.6."
            % (x, y))
    if wall:
        k.rect(x - 1, y - 1, w + 2, h + 2, "solid")
    k.clear_rect(x, y, w, h)
    k.rect(x, surface, w, 1, "water_top")
    k.rect(x, surface + 1, w, depth - 1, "water")
    if bed:
        k.rect(x, y + h, w, 1, "packed")
    return (x, surface, w, depth)


def colonnade(k, x, count, spacing, surface, bed, pattern=None, width=2,
              mark=None, clearance=2):
    """Submerged columns you weave over and under.

    `pattern[i]` is "over" (the column rises from the bed and you pass above
    it) or "under" (it hangs from the roof and you pass below it). Defaults to
    alternating, starting "over" -- THE WATERWAY's shape, which proves.

    `clearance` is how many tiles of open water the pass must leave. Two, for
    the same reason a corridor is two tiles: a one-tile slot is a shape the
    body does not fit through, and the historical version of this bug is
    defect 2.

    Returns the list of mark names in swim order, so the author can chain
    g.route() straight down it.
    """
    if pattern is None:
        pattern = ["over" if i % 2 == 0 else "under" for i in range(count)]
    if len(pattern) != count:
        raise WorldKitError("colonnade at col %d: %d pattern entries for %d "
                            "columns" % (x, len(pattern), count))
    if spacing <= width:
        raise WorldKitError(
            "colonnade at col %d: spacing %d against column width %d leaves no "
            "water between them" % (x, spacing, width))
    names = []
    for i, kind in enumerate(pattern):
        cx = x + i * spacing
        if kind == "over":
            # rises from the bed, stops `clearance` tiles below the surface
            top = surface + clearance
            if top > bed:
                raise WorldKitError(
                    "colonnade column %d at col %d: the water is only %d tiles "
                    "deep, so a column leaving %d tiles of clearance above it "
                    "has no height left" % (i, cx, bed - surface + 1, clearance))
            k.rect(cx, top, width, bed - top + 1, "solid")
            pass_row = surface + 1
        elif kind == "under":
            # hangs from the surface, stops `clearance` tiles above the bed
            bottom = bed - clearance
            if bottom < surface:
                raise WorldKitError(
                    "colonnade column %d at col %d: the water is only %d tiles "
                    "deep, so a hanging column leaving %d tiles of clearance "
                    "below it has no height left"
                    % (i, cx, bed - surface + 1, clearance))
            k.rect(cx, surface, width, bottom - surface + 1, "solid")
            pass_row = bed
        else:
            raise WorldKitError("colonnade column %d: '%s' is not over/under"
                                % (i, kind))
        for xx in range(cx, cx + width):
            k._claim("wet", "colonnade %s column %d at col %d"
                     % (kind, i, cx), x=xx, y=pass_row, tall=clearance)
        if mark:
            name = "%s_%d" % (mark, i + 1)
            # Not k.mark(): a swim waypoint is wet, not standable, so the
            # claim it files is "wet" rather than "stand".
            k.g.mark(name, cx + width // 2, pass_row)
            k._claim("wet", "colonnade mark '%s'" % name,
                     x=cx + width // 2, y=pass_row, tall=clearance)
            names.append(name)
    return names


def current_channel(k, x, y, w, direction, height=BODY_TILES, fast=False,
                    wall=True):
    """A tube of moving water that pushes you along it.

    A current with no way out at the downstream end pins you against the wall
    forever, so this claims the tile just beyond the last one is clear. That is
    the softlock the shape invites, and it is the one worth a claim.

    `direction` is right / left / up / down; `fast` picks the 120 px/s variant,
    which only exists horizontally.
    """
    roles = {"right": "cur_right", "left": "cur_left",
             "up": "cur_up", "down": "cur_down"}
    if direction not in roles:
        raise WorldKitError("current_channel: direction '%s' is not "
                            "right/left/up/down" % direction)
    role = roles[direction]
    if fast:
        if direction not in ("right", "left"):
            raise WorldKitError(
                "current_channel: there is no fast %s current in "
                "data/tiles.json; only right and left have one" % direction)
        role += "_fast"
    if height < BODY_TILES:
        raise WorldKitError("current_channel at (%d,%d) is %d tiles tall; a "
                            "body is %d" % (x, y, height, BODY_TILES))
    vertical = direction in ("up", "down")
    if vertical:
        cols, rows = height, w
        k.rect(x, y, cols, rows, role)
        if wall:
            k.rect(x - 1, y, 1, rows, "solid")
            k.rect(x + cols, y, 1, rows, "solid")
        exit_xy = (x, y - 1) if direction == "up" else (x, y + rows)
    else:
        k.rect(x, y - height + 1, w, height, role)
        if wall:
            k.rect(x, y + 1, w, 1, "solid")
            k.rect(x, y - height, w, 1, "solid")
        exit_xy = (x + w, y) if direction == "right" else (x - 1, y)
    k._claim("clear", "current_channel at (%d,%d) flowing %s needs a way out "
             "downstream" % (x, y, direction),
             x=exit_xy[0], y=exit_xy[1], tall=BODY_TILES)
    if role in k.pal.substituted or roles[direction] in k.pal.substituted:
        k.cannot_prove(
            "current_channel at (%d,%d) flowing %s: the current tile has no "
            "legend character yet, so it was drawn as still water. The channel's "
            "WALLS are provable; the PUSH is not, and a hop that depends on "
            "being carried will not behave as authored."
            % (x, y, direction))
    return exit_xy


def air_pocket(k, x, y, w, h=BODY_TILES, roof=True):
    """A bubble of air under a roof, over water: where the fish resurfaces.

    Consecutive pockets are checked against AIR_POCKET_SPAN -- 92 px/s for
    2.6 s is about fifteen tiles in a straight line and less when weaving, so
    pockets further apart than that are a drowning rather than a level.
    """
    if h < 1:
        raise WorldKitError("air_pocket at (%d,%d): height %d" % (x, y, h))
    k.clear_rect(x, y - h + 1, w, h)
    if roof:
        k.rect(x, y - h, w, 1, "solid")
    for xx in range(x, x + w):
        k._claim("clear", "air_pocket at (%d,%d) w%d" % (x, y, w),
                 x=xx, y=y, tall=h)
    k._claim("wet", "air_pocket at (%d,%d) must be reachable from the water "
             "below it" % (x, y), x=x + w // 2, y=y + 1, tall=1)
    prev = getattr(k, "_last_pocket", None)
    if prev is not None:
        span = abs((x + w // 2) - prev)
        if span > AIR_POCKET_SPAN:
            raise WorldKitError(
                "air_pocket at (%d,%d) is %d tiles from the one before it. The "
                "fish covers about %d tiles between breaths (92 px/s for "
                "air_seconds 2.6) and less when it weaves, so this is a "
                "drowning, not a swim." % (x, y, span, AIR_POCKET_SPAN))
    k._last_pocket = x + w // 2
    return x, y, w


def bank(k, x, y, w, rise=1, depth=None):
    """The step out of the water onto dry land.

    Defect 4 was a fish that could not hop a 16 px bank because the hop height
    was never compared to the bank. surface_hop -210 against gravity 900 is
    24.5 px, so one tile clears and two do not -- `rise` is checked against
    LIMITS["fish"] and there is no argument that gets you a 2-tile bank.
    """
    check_rise(rise, "fish", "bank at (%d,%d)" % (x, y))
    top = y - rise
    # Carve the headroom before drawing the shelf. A bank with rock two tiles
    # above it is land you can see and never stand on, which is defect 3 with
    # the ceiling instead of the door.
    k.clear_rect(x, top - BODY_TILES, w, BODY_TILES)
    k.floor(x, top, w, depth=depth if depth is not None else k.g.h - top)
    k._claim("stand", "bank at (%d,%d) rise %d" % (x, y, rise),
             x=x + w // 2, y=top - 1, form="human")
    k._claim("wet", "bank at (%d,%d) needs water against its foot" % (x, y),
             x=x - 1, y=y, tall=1)
    return x, top - 1, w


# ---------------------------------------------------- THERMAL HEIGHTS (w3)

def updraft_shaft(k, x, w, top, bottom, strong=False, mouth=None):
    """A vertical column of rising air, with a mouth at the top and a way in
    at the foot.

    Built on `Kit.shaft`, so it inherits both of the historical shaft defects:
    it cannot be capped across its full width (defect 6) and its left wall
    stops two tiles above the floor so you can walk in rather than being
    sealed out (defect 5).
    """
    interior, (m0, m1) = k.shaft(x, w, top, bottom, mouth=mouth)
    role = "updraft_strong" if strong else "updraft"
    k.rect(interior[0], top, interior[1] - interior[0] + 1,
           bottom - top + 1, role)
    # The mouth has to stay open air, not draft over a lid.
    k._claim("clear", "updraft_shaft at col %d: the mouth at cols %d-%d"
             % (x, m0, m1), x=m0, y=top - 1, tall=BODY_TILES)
    if role in k.pal.substituted:
        k.cannot_prove(
            "updraft_shaft at col %d rows %d-%d: the updraft tile has no legend "
            "character yet, so the shaft was drawn as empty air. A route that "
            "climbs it is a %d-tile rise with nothing lifting you, which no "
            "form can make." % (x, top, bottom, bottom - top))
    return interior, (m0, m1)


def cloud_deck(k, perches, width=3, role="oneway", mark=None, form="bird"):
    """A chain of perches across open sky.

    `perches` is [(x, top_row), ...] in crossing order; the body stands on
    top_row - 1. Each hop is checked against the largest one this project has
    ever PROVED rather than against a model: proofs/jungle_4.tape.json crosses
    6 tiles across and 5 tiles up from perch_2 to perch_3 in 68 frames, and
    that is LIMITS["bird"].

    A perch also has to be landable, so `width` is at least two tiles: the bird
    hitbox is 12 px wide and a one-tile perch is a coin flip at 104 px/s.
    """
    if width < 2:
        raise WorldKitError(
            "cloud_deck: a %d-tile perch. The bird runs at 104 px/s and its "
            "hitbox is 12 px wide; two tiles is the minimum that is landable "
            "rather than lucky." % width)
    if len(perches) < 2:
        raise WorldKitError("cloud_deck needs at least two perches")
    names = []
    for i, (px, py) in enumerate(perches):
        k.ledge(px, py, width, role=role, stand_form=form)
        if mark:
            names.append(k.mark("%s_%d" % (mark, i + 1), px + width // 2,
                                py - 1, form=form))
        if i:
            qx, qy = perches[i - 1]
            rise = (qy - 1) - (py - 1)
            run = abs(px - qx) - width
            what = "cloud_deck hop %d -> %d" % (i, i + 1)
            if rise > 0:
                check_rise(rise, form, what)
            check_gap(max(0, run), form, what)
            k._claim("step", what,
                     x1=qx + (width - 1 if px > qx else 0), y1=qy - 1,
                     x2=px + (0 if px > qx else width - 1), y2=py - 1,
                     form=form)
    if len(perches) > BIRD_HOPS_PER_PERCH + 1:
        k.note("cloud_deck of %d perches: stamina refills on a perch "
               "(stamina_regen 46/s, perch_regen_bonus 34), so a long deck is "
               "fine -- but %d hops without one is not. Keep the run of "
               "perch-less gaps under %d."
               % (len(perches), BIRD_HOPS_PER_PERCH + 1, BIRD_HOPS_PER_PERCH))
    return names


def wind_gap(k, x, y, w, direction, height=4, form="bird"):
    """A gap crossed on a sideways gust.

    The landing shelf on the far side is the author's; what this draws is the
    moving air in the gap and the claim that both lips are standable. It also
    refuses to pretend: if the gust tile has no character yet the gap is plain
    empty space, and a gap wider than the form's own reach becomes uncrossable,
    which is recorded rather than glossed over.
    """
    role = {"right": "gust_right", "left": "gust_left"}.get(direction)
    if role is None:
        raise WorldKitError("wind_gap: direction '%s' is not right/left"
                            % direction)
    k.clear_rect(x, y - height + 1, w, height)
    k.rect(x, y - height + 1, w, height, role)
    k._claim("stand", "wind_gap at (%d,%d): the near lip" % (x, y),
             x=x - 1, y=y, form=form)
    k._claim("stand", "wind_gap at (%d,%d): the far lip" % (x, y),
             x=x + w, y=y, form=form)
    if role in k.pal.substituted:
        k.cannot_prove(
            "wind_gap at (%d,%d) w%d: the gust tile has no legend character "
            "yet, so the gap is still air. It is now a plain %d-tile gap, and "
            "the %s clears %d."
            % (x, y, w, w, form, LIMITS[form]["gap"]))
    else:
        # With the gust present the crossing is wider than the form's own
        # reach on purpose -- that IS the verb. It still has to be proved.
        if w > LIMITS[form]["gap"]:
            k.note("wind_gap at (%d,%d) is %d tiles, wider than the %s's own "
                   "%d-tile reach: it is only crossable ON the gust, so give "
                   "it its own route hop and let tools/prove.sh answer it."
                   % (x, y, w, form, LIMITS[form]["gap"]))
    return x, y, w


# ------------------------------------------------------ TERMITE DEEPS (w4)

def tunnel(k, points, height=BODY_TILES, ladder_role="ladder", form="human"):
    """Carve a corridor along a polyline of (x, feet_row) waypoints.

    Segments are axis-aligned; a diagonal is rejected rather than guessed at.
    A vertical segment longer than the form's measured rise gets a ladder,
    because a vertical hole taller than you can jump is a hole you fall into
    once, which is defect 1 in a different coat.

    Returns the list of (x, y) corners actually carved.
    """
    if len(points) < 2:
        raise WorldKitError("tunnel needs at least two points")
    if height < BODY_TILES:
        raise WorldKitError("tunnel is %d tiles tall; a body is %d"
                            % (height, BODY_TILES))
    rise = LIMITS[form]["rise"]
    ladders = []
    # Two passes on purpose. A ladder drawn inside the first pass is overwritten
    # by the next segment's carve -- which is precisely the draw-order bug that
    # audit() exists to catch, and the first version of this function had it.
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if x1 != x2 and y1 != y2:
            raise WorldKitError(
                "tunnel segment (%d,%d) -> (%d,%d) is diagonal. Give the "
                "corner its own point so the carve is unambiguous."
                % (x1, y1, x2, y2))
        if y1 == y2:
            lo, hi = min(x1, x2), max(x1, x2)
            k.corridor(lo, y1, hi - lo + 1, height)
        else:
            lo, hi = min(y1, y2), max(y1, y2)
            k.clear_rect(x1, lo - height + 1, 1, hi - lo + height)
            if hi - lo > rise:
                # Taller than the form can jump, so it needs a climb. A
                # vertical hole you cannot get back out of is defect 1 wearing
                # a different hat.
                ladders.append((x1, lo - 1, hi))
            else:
                k._claim("step", "tunnel riser (%d,%d) -> (%d,%d)"
                         % (x1, y1, x2, y2), x1=x1, y1=y1, x2=x2, y2=y2,
                         form=form)
    for col, top, bottom in ladders:
        k.climb(col, top, bottom, landing="right", role=ladder_role,
                stand_form=form)
    return list(points)


def breakable_wall(k, x, y, h, thickness=1, role="shoulder", form="human"):
    """A plug of breakable tiles across a corridor, with room to work at it.

    Two things this checks and one it refuses to pretend about:

    * a standable tile on BOTH sides at the same row, so you can walk up to it
      and shoulder into it rather than having to hit it from mid-air;
    * that the tile chosen is actually shoulder-breakable. Tiles with no
      `break_hold` open only to a weapon, and the frog and the bird have none
      -- a frog room behind a weapon-only wall is a sealed room.

    And: `tools/prove.sh` cannot open it. tools/solver/sim.gd models transform
    pads, keys, doors and switches, and nothing that breaks a tile, so a route
    hop through this plug will fail the gate no matter how well the geometry
    works. That is recorded in Kit.unproven, loudly.
    """
    flags = k.pal.flags(role)
    if not flags.get("breakable"):
        raise WorldKitError(
            "breakable_wall at (%d,%d): palette role '%s' is tile '%s', which "
            "is not breakable at all" % (x, y, role, k.pal.name(role)))
    hold = float(flags.get("break_hold", 0.0) or 0.0)
    k.rect(x, y - h + 1, thickness, h, role)
    for xx in range(x, x + thickness):
        for yy in range(y - h + 1, y + 1):
            k._release(xx, yy)
    k._claim("stand", "breakable_wall at (%d,%d): room to work on the west side"
             % (x, y), x=x - 1, y=y, form=form)
    k._claim("stand", "breakable_wall at (%d,%d): room to work on the east side"
             % (x, y), x=x + thickness, y=y, form=form)
    if hold <= 0.0:
        k.note("breakable_wall at (%d,%d) uses '%s', which declares no "
               "break_hold: only a WEAPON opens it. The frog and the bird have "
               "none, so this wall must not be on a frog or bird route."
               % (x, y, k.pal.name(role)))
    k.cannot_prove(
        "breakable_wall at (%d,%d) %dx%d: tools/solver/sim.gd applies pads, "
        "keys, doors and switches and nothing that breaks a tile, so the "
        "prover cannot pass this plug. Route AROUND it, or the hop fails the "
        "gate." % (x, y, thickness, h))
    return x, y, thickness, h


def glow_wall(k, x, y, h, thickness=1, form="human"):
    """The luminous wall TERMITE DEEPS is about: breaking it lights the room.

    Points at `glowwall`, which the DEEPS palette aims at `luminous_wall`
    (break_hold 0.4) rather than `deep_glowwall` (270), because 270 declares no
    break_hold and so only a weapon opens it -- and the frog, which this world
    leans on, has none.
    """
    out = breakable_wall(k, x, y, h, thickness=thickness, role="glowwall",
                         form=form)
    k.note("glow_wall at (%d,%d): breaking it lights the chamber AND removes "
           "the tiles you were standing behind. Anything the player needs to "
           "stand on must not be part of the wall." % (x, y))
    return out


def dark_chamber(k, x, y, w, h, entrance, glow=None, floor_role="solid",
                 form="human"):
    """A room carved out of rock with exactly one declared way in.

    `entrance` is (x, feet_row) on the chamber's boundary; `glow` is the column
    of a luminous wall to put in the far side. The chamber's floor is drawn, so
    `audit()` can tell a room from a pit.
    """
    k.clear_rect(x, y, w, h)
    k.rect(x, y + h, w, 1, floor_role)
    ex, ey = entrance
    k.doorway(ex, ey, h=BODY_TILES)
    k._claim("stand", "dark_chamber at (%d,%d): its floor" % (x, y),
             x=x + w // 2, y=y + h - 1, form=form)
    if glow is not None:
        glow_wall(k, glow, y + h - 1, min(h, BODY_TILES + 1), form=form)
    k.note("dark_chamber at (%d,%d) %dx%d: darkness is an Ambience light "
           "radius, visual only -- it changes nothing about collision, so "
           "tools/prove.sh proves the same geometry a lit room would. What it "
           "does NOT prove is that a human can see where to go."
           % (x, y, w, h))
    return x, y, w, h


# -------------------------------------------------- THE OBSIDIAN NEST (w5)

def switch_lattice(k, x, y, w, h, group="a", pattern="checker", phase=0):
    """A block field where half the tiles swap solidity when the switch flips.

    `pattern` is "checker" (alternating by x+y), "columns" or "rows". The `_on`
    tile is solid while the group is ON and the `_off` tile while it is OFF, so
    one flip turns the room inside out.

    Nothing is claimed here, because whether a lattice tile is solid is not a
    property of the grid -- it is a property of a configuration. Use
    `reconfig_check()` for that, and read its docstring about what it is and
    is not.
    """
    if group not in ("a", "b"):
        raise WorldKitError("switch_lattice: group '%s' is not a/b" % group)
    on, off = "switch_%s_on" % group, "switch_%s_off" % group
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if pattern == "checker":
                first = (xx + yy + phase) % 2 == 0
            elif pattern == "columns":
                first = (xx + phase) % 2 == 0
            elif pattern == "rows":
                first = (yy + phase) % 2 == 0
            else:
                raise WorldKitError("switch_lattice: pattern '%s' is not "
                                    "checker/columns/rows" % pattern)
            k.put(xx, yy, on if first else off)
    k.note("switch_lattice at (%d,%d) %dx%d on group %s: the level starts with "
           "group 1 ON and group 2 OFF (tools/solver/sim.gd seeds TileWorld "
           "that way), so the '%s' tiles are the ones that are solid at spawn."
           % (x, y, w, h, group,
              on if (group == "a") else off))
    return x, y, w, h


def switch_gate(k, x, y, h, group="a", solid_when="on"):
    """A plug of switch blocks: a door with no key.

    ROOT HOLLOW shipped the trap this is here to avoid -- a switch-block bridge
    whose switch was on the far side of the bridge. Nothing in the geometry
    says so, which is why `reconfig_check` and not this function is what tells
    you.
    """
    if group not in ("a", "b"):
        raise WorldKitError("switch_gate: group '%s' is not a/b" % group)
    if solid_when not in ("on", "off"):
        raise WorldKitError("switch_gate: solid_when '%s' is not on/off"
                            % solid_when)
    role = "switch_%s_%s" % (group, solid_when)
    k.rect(x, y - h + 1, 1, h, role)
    # A gate is a deliberate plug: whatever carved this corridor claimed the
    # tile was clear, and it no longer is.
    for yy in range(y - h + 1, y + 1):
        k._release(x, yy)
    return x, y, h


def reachable_set(k, start, form="human", switches=None):
    """Standable tiles reachable from `start` in one switch configuration.

    A CONSERVATIVE flood fill: walk one tile, climb ladders and water, rise up
    to the form's measured limit, jump up to its measured gap, and fall. It
    understates reach on purpose -- everything it reports as connected really
    is, and something it misses may still be reachable in play.

    **It is a filter, not proof.** Every one of this project's six shipped
    defects was a model that was nearly right (ADR 005). What proves a room is
    tools/prove.sh playing it with the shipping movement code. What this is for
    is answering a question the prover cannot: whether a room is still
    escapable in the OTHER switch configuration, which is a question about four
    whole levels rather than one route.
    """
    if form in ("bird", "fish"):
        raise WorldKitError(
            "reachable_set: '%s' does not walk. The bird flies and the fish "
            "swims, so a ground flood fill would understate one and overstate "
            "the other; tools/prove.sh is what answers those." % form)
    p = Probe(k.g, switches=switches)
    rise, gap = LIMITS[form]["rise"], LIMITS[form]["gap"]
    seen = set()
    stack = [tuple(start)]
    while stack:
        x, y = stack.pop()
        if (x, y) in seen:
            continue
        if not (0 <= x < k.g.w and 0 <= y < k.g.h):
            continue
        if not p.standable(x, y):
            continue
        seen.add((x, y))
        cand = [(x - 1, y), (x + 1, y)]
        if p.ladder(x, y) or p.water(x, y):
            cand += [(x, y - 1), (x, y + 1)]
        for dy in range(1, rise + 1):
            for dx in range(-gap, gap + 1):
                cand.append((x + dx, y - dy))
        for dx in range(-gap, gap + 1):
            cand.append((x + dx, y))
        for dx in range(-gap, gap + 1):
            for dy in range(1, k.g.h):
                nx, ny = x + dx, y + dy
                if not p.clear(nx, ny):
                    break
                if p.standable(nx, ny):
                    cand.append((nx, ny))
                    break
        for c in cand:
            if c not in seen and path_clear(p, x, y, c[0], c[1], rise):
                stack.append(c)
    return seen


## What tools/solver/sim.gd seeds before a switch entity is touched:
## TileWorld's own defaults, group 1 ON and group 2 OFF.
START_SWITCHES = {1: True, 2: False}


def reconfig_check(k, entry, goal, form="human", switches=None):
    """Can you get from `entry` to `goal`, and can you always get back to a
    switch?

    Two questions, both softlocks this world invites:

    1. Is `goal` reachable in at least one of the four switch configurations?
    2. In every configuration reachable from `entry`, is at least one switch
       entity still reachable? A lattice that seals you into a pocket with the
       lever on the far side is ROOT HOLLOW's circular bridge, at scale.

    Raises on failure and returns the per-configuration reachable-set sizes, so
    an author can see a room getting more or less connected as they tune it.
    Filter, not proof -- see reachable_set().
    """
    entities = [(int(e["x"]), int(e["y"]), e["type"]) for e in k.g.entities
                if e["type"] in ("switch_a", "switch_b")]
    configs = [{1: a, 2: b} for a in (True, False) for b in (True, False)]
    if switches is not None:
        configs = [dict(switches)] + [c for c in configs if c != switches]
    sizes = {}
    reached_goal = []
    stranded = []
    for cfg in configs:
        seen = reachable_set(k, entry, form=form, switches=cfg)
        key = (cfg[1], cfg[2])
        sizes[key] = len(seen)
        if tuple(goal) in seen:
            reached_goal.append(key)
        if entities and not any(
                (ex + dx, ey + dy) in seen
                for ex, ey, _t in entities
                for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
            stranded.append(key)
    problems = []
    if not reached_goal:
        problems.append(
            "goal %s is not reachable from %s in ANY of the four switch "
            "configurations (reachable tiles per config: %s)"
            % (tuple(goal), tuple(entry), sizes))
    if stranded:
        problems.append(
            "in config(s) %s no switch is reachable from %s, so the flip that "
            "got you there cannot be undone -- that is a softlock, and it is "
            "the shape ROOT HOLLOW's switch bridge shipped with"
            % (stranded, tuple(entry)))
    if problems:
        raise WorldKitError("reconfig_check: " + "; ".join(problems))
    k.note("reconfig_check from %s to %s: reachable in config(s) %s. This is a "
           "conservative flood fill and NOT a proof -- tools/prove.sh is."
           % (tuple(entry), tuple(goal), reached_goal))
    return sizes


for _fn in (flooded_chamber, colonnade, current_channel, air_pocket, bank,
            updraft_shaft, cloud_deck, wind_gap,
            tunnel, breakable_wall, glow_wall, dark_chamber,
            switch_lattice, switch_gate, reachable_set, reconfig_check):
    setattr(Kit, _fn.__name__, _fn)


# =========================================================================
# Self-test.
#
# Two kinds of case, and the second kind is the point:
#
#   * a shape the kit must draw, and audit() must accept;
#   * a shape the kit must REFUSE, paired with the smallest change that makes
#     it acceptable. tests/fixtures/make_fixtures.py argues this better than I
#     can: without the twin, a "failing" case could be failing for a typo and
#     the test would look green while checking nothing.
# =========================================================================

_FAILS = []
_CHECKS = [0]


def _check(cond, msg):
    _CHECKS[0] += 1
    if not cond:
        _FAILS.append(msg)


def _audits(k, msg):
    """audit() must accept this grid. A raise here is a test failure, not a
    traceback -- the rest of the self-test still has things to say."""
    _CHECKS[0] += 1
    try:
        k.audit()
    except WorldKitError as e:
        _FAILS.append("%s: audit rejected it -- %s" % (msg, e))


def _raises(fn, needle, msg):
    _CHECKS[0] += 1
    try:
        fn()
    except WorldKitError as e:
        if needle.lower() not in str(e).lower():
            _FAILS.append("%s: raised, but not about '%s' -- %s"
                          % (msg, needle, e))
        return
    except Exception as e:                               # noqa: BLE001
        _FAILS.append("%s: raised %s, not WorldKitError -- %s"
                      % (msg, type(e).__name__, e))
        return
    _FAILS.append("%s: drew it without complaint" % msg)


def _grid(w=25, h=15, pal=None, fill_solid=False):
    from gen_levels import Grid
    g = Grid(w, h)
    k = Kit(g, pal or JUNGLE)
    if fill_solid:
        k.fill_solid()
    return g, k


def selftest():
    # ---------------------------------------------------- path_clear, pinned
    # The two cases tools/reachability.py pins, re-pinned here because this
    # module carries its own copy (that one calls main() at import time and so
    # cannot be imported).
    class _Stub:
        def __init__(self, rows):
            self.rows = rows

        def solid(self, x, y):
            if y < 0:
                return False
            if y >= len(self.rows) or x < 0 or x >= len(self.rows[0]):
                return True
            return self.rows[y][x] == "#"

    lid = _Stub(["....", "....", "####", "....", "####"])
    _check(not path_clear(lid, 1, 3, 1, 1, 5), "jumped through a ceiling")
    mouth = _Stub(["....", "....", "#.##", "....", "####"])
    _check(path_clear(mouth, 1, 3, 0, 1, 5), "an open mouth was refused")
    wall = _Stub(["...", ".#.", ".#.", "###"])
    _check(not path_clear(wall, 0, 2, 2, 2, 1), "jumped through a wall")
    _check(path_clear(wall, 0, 2, 2, 2, 3), "a wall low enough was refused")

    # ------------------------------------------------------ the limits table
    for form in ("human", "frog", "bird", "fish"):
        _check(form in LIMITS, "no limits for %s" % form)
    _check(LIMITS["frog"]["rise"] == 3,
           "the frog rise is 3 because a cut jump tops out near 4.37 tiles; "
           "changing it needs a new measurement, not a new opinion")
    _check(LIMITS["fish"]["rise"] == 1,
           "the fish bank is 1 tile: surface_hop -210 against gravity 900 is "
           "24.5 px")

    # ------------------------------------------------------------ the palette
    _check(JUNGLE.missing() == [],
           "the jungle palette must resolve entirely from today's legend, or "
           "nothing in this kit is testable now: %s" % (JUNGLE.missing(),))
    for pal in (RUINS, HEIGHTS, DEEPS, NEST):
        # Either the legend has these tiles or every one of them has an
        # understudy; a role with neither is a helper that cannot run at all.
        for role, want in pal.missing():
            _check(role in UNDERSTUDY,
                   "%s role '%s' (%s) has no character and no understudy"
                   % (pal.world, role, want))
    _raises(lambda: Palette("x", {}).char("solid"),
            "declares no tile", "an empty palette")
    _raises(lambda: JUNGLE.char("nonsense"), "not a kit role",
            "an unknown role")

    # --------------------------------------------------- stair refuses a step
    # The frog measurement, as a test: 3 tiles draws, 4 does not.
    g, k = _grid(30, 20)
    k.floor(0, 18, 30)
    k.stair(2, 17, 4, 3, 4, 3, form="frog")
    _audits(k, "a 3-tile frog stair should audit clean")
    _raises(lambda: _grid(30, 20)[1].stair(2, 17, 4, 4, 4, 3, form="frog"),
            "tops out", "a 4-tile frog stair")
    _raises(lambda: _grid(30, 20)[1].stair(2, 17, 4, 3, 4, 3, form="human"),
            "tops out", "a 3-tile human stair")

    # ------------------------------------------- audit catches a later clobber
    # THE WATERWAY nearly shipped exactly this: a ledge drawn after a vine
    # overwrote the vine's top and left a gap nobody could jump.
    g, k = _grid(20, 20)
    k.floor(0, 18, 20)
    k.floor(12, 8, 6, depth=2)
    k.climb(11, 6, 17, landing="right")
    _audits(k, "a vine flush with a ledge should be fine")

    g, k = _grid(20, 20)
    k.floor(0, 18, 20)
    k.climb(10, 6, 17, landing="right")
    k.floor(9, 5, 6, depth=3)          # drawn AFTER: buries the vine's top
    _raises(k.audit, "no longer climbable", "a vine buried by a later ledge")

    # A ladder whose only neighbour is thin air (defect 1).
    g, k = _grid(20, 20)
    k.floor(0, 18, 20)
    k.climb(10, 4, 17, landing="right")
    _raises(k.audit, "needs a landing", "a vine with nothing at its top")

    # ---------------------------------------------- audit catches a lost mouth
    # The corridor stops at the shaft's east wall: that wall runs to the floor
    # on purpose, and only the west wall leaves a way in (jungle_4's did not,
    # and sealed the spawn in a box).
    g, k = _grid(25, 20, fill_solid=True)
    k.corridor(1, 18, 7)
    k.shaft(8, 4, 6, 18, mouth=(9, 10))
    k.clear_rect(9, 6, 4, 12)
    k.clear_rect(9, 4, 2, 2)           # the mouth is open sky
    _audits(k, "a shaft with a mouth should audit clean")

    g, k = _grid(25, 20, fill_solid=True)
    k.corridor(1, 18, 7)
    k.shaft(8, 4, 6, 18, mouth=(9, 10))
    k.clear_rect(9, 6, 4, 12)          # no mouth cut: a chimney with a lid
    _raises(k.audit, "capped across its full width", "a capped shaft")
    _raises(lambda: _grid(25, 20)[1].shaft(8, 1, 6, 18),
            "needs room to stand", "a one-tile-wide shaft")
    _raises(lambda: _grid(25, 20)[1].shaft(8, 4, 6, 18, mouth=(20, 21)),
            "not inside the shaft", "a mouth outside the shaft")

    # ------------------------------------------------- doorways fit a 22px body
    g, k = _grid(20, 20, fill_solid=True)
    _check(k.doorway(10, 12, h=2) == (10, 12), "a two-tile doorway")
    _raises(lambda: _grid(20, 20, fill_solid=True)[1].doorway(10, 12, h=1),
            "tile(s) tall", "a one-tile doorway (defect 3)")

    # ------------------------------------------------------ gaps and landings
    g, k = _grid(30, 20)
    k.floor(0, 18, 10)
    k.floor(13, 18, 10)
    k.gap(10, 17, 3, form="human", landing_w=10)
    _audits(k, "a 3-tile human gap onto a wide shelf")
    _raises(lambda: _grid(30, 20)[1].gap(10, 17, 4, form="human",
                                         landing_w=10),
            "clears 3", "a 4-tile human gap")
    _raises(lambda: _grid(30, 20)[1].gap(10, 17, 3, form="human",
                                         landing_w=3),
            "sails over it", "a wide gap onto a narrow shelf")

    # ------------------------------------------------------- SUNKEN RUINS
    g, k = _grid(40, 24, pal=RUINS, fill_solid=True)
    k.flooded_chamber(2, 6, 36, 14, surface=10)
    names = k.colonnade(6, 4, 7, surface=10, bed=19, mark="col")
    _check(len(names) == 4, "colonnade should name one waypoint per column")
    _audits(k, "a flooded colonnade should audit clean")
    _raises(lambda: _grid(40, 24, pal=RUINS, fill_solid=True)[1]
            .flooded_chamber(2, 6, 36, 14, surface=19),
            "a fish needs two", "a one-tile-deep flood")
    _raises(lambda: _grid(40, 24, pal=RUINS, fill_solid=True)[1]
            .flooded_chamber(2, 6, 36, 14, surface=6),
            "nowhere to surface", "a chamber flooded to its ceiling")
    # A column that seals the channel is caught by the wet claim, not by luck.
    g, k = _grid(40, 24, pal=RUINS, fill_solid=True)
    k.flooded_chamber(2, 6, 36, 14, surface=10)
    k.colonnade(6, 4, 7, surface=10, bed=19, mark="col")
    k.rect(6, 10, 2, 10, "solid")      # fill the first pass shut
    _raises(k.audit, "not water", "a colonnade column drawn shut afterwards")

    # the bank a fish can actually hop
    g, k = _grid(30, 24, pal=RUINS, fill_solid=True)
    k.flooded_chamber(2, 8, 20, 12, surface=12)
    k.bank(22, 12, 6, rise=1)
    _audits(k, "a 1-tile bank should audit clean")
    _raises(lambda: _grid(30, 24, pal=RUINS, fill_solid=True)[1]
            .bank(22, 12, 6, rise=2),
            "tops out", "a 2-tile bank (defect 4)")

    # air pockets within one lungful
    g, k = _grid(48, 24, pal=RUINS, fill_solid=True)
    k.flooded_chamber(2, 6, 44, 14, surface=10)
    k.air_pocket(4, 9, 3)
    k.air_pocket(16, 9, 3)
    _audits(k, "two pockets twelve tiles apart")
    g, k = _grid(48, 24, pal=RUINS, fill_solid=True)
    k.flooded_chamber(2, 6, 44, 14, surface=10)
    k.air_pocket(4, 9, 3)
    _raises(lambda: k.air_pocket(40, 9, 3), "drowning",
            "two pockets further apart than one lungful")

    # a current with nothing downstream of it
    g, k = _grid(30, 20, pal=RUINS, fill_solid=True)
    k.clear_rect(1, 8, 28, 6)
    k.current_channel(4, 12, 10, "right")
    k.clear_rect(14, 11, 2, 2)
    _audits(k, "a current with a way out")
    g, k = _grid(30, 20, pal=RUINS, fill_solid=True)
    k.current_channel(4, 12, 10, "right")     # solid rock downstream
    _raises(k.audit, "way out downstream", "a current that pins you to a wall")
    _raises(lambda: _grid(30, 20, pal=RUINS)[1]
            .current_channel(4, 12, 10, "up", fast=True),
            "no fast up current", "a fast vertical current")

    # ---------------------------------------------------- THERMAL HEIGHTS
    g, k = _grid(30, 24, pal=HEIGHTS, fill_solid=True)
    k.corridor(1, 22, 7)
    k.updraft_shaft(8, 4, 6, 22, mouth=(9, 10))
    k.clear_rect(9, 4, 2, 2)
    _audits(k, "an updraft shaft with a mouth")

    # the largest bird hop this project has proved, and one tile more
    g, k = _grid(40, 24, pal=HEIGHTS)
    k.floor(0, 22, 40)
    k.cloud_deck([(2, 20), (11, 15), (20, 15)], width=3, mark="perch")
    _audits(k, "a 6-across 5-up bird deck should be fine")
    _raises(lambda: _grid(40, 24, pal=HEIGHTS)[1]
            .cloud_deck([(2, 20), (12, 15)], width=3),
            "clears 6", "a 7-tile bird hop")
    _raises(lambda: _grid(40, 24, pal=HEIGHTS)[1]
            .cloud_deck([(2, 20), (11, 14)], width=3),
            "tops out", "a 6-tile bird rise")
    _raises(lambda: _grid(40, 24, pal=HEIGHTS)[1]
            .cloud_deck([(2, 20), (11, 15)], width=1),
            "landable rather than lucky", "a one-tile perch")

    # ------------------------------------------------------ TERMITE DEEPS
    g, k = _grid(40, 24, pal=DEEPS, fill_solid=True)
    k.tunnel([(2, 20), (20, 20), (20, 10), (36, 10)])
    _audits(k, "an L-shaped tunnel with a ladder in the riser")
    _raises(lambda: _grid(40, 24, pal=DEEPS, fill_solid=True)[1]
            .tunnel([(2, 20), (20, 10)]), "diagonal", "a diagonal tunnel")
    _raises(lambda: _grid(40, 24, pal=DEEPS, fill_solid=True)[1]
            .tunnel([(2, 20), (20, 20)], height=1),
            "a body is", "a one-tile tunnel")

    # a breakable plug with room to work at it, and one without
    g, k = _grid(30, 20, pal=DEEPS, fill_solid=True)
    k.corridor(2, 16, 26)
    k.breakable_wall(14, 16, 2)
    _audits(k, "a plug with standable ground both sides")
    _check(any("prover cannot pass" in u for u in k.unproven),
           "a breakable wall must declare itself unprovable")
    g, k = _grid(30, 20, pal=DEEPS, fill_solid=True)
    k.corridor(2, 16, 12)              # nothing carved east of the plug
    k.breakable_wall(14, 16, 2)
    _raises(k.audit, "east side", "a plug with solid rock behind it")

    g, k = _grid(30, 20, pal=DEEPS, fill_solid=True)
    k.corridor(2, 16, 26)
    k.glow_wall(14, 16, 2)
    _check(k.pal.flags("glowwall").get("break_hold", 0) > 0,
           "the glow wall must be shoulder-breakable: the frog has no weapon")

    g, k = _grid(40, 24, pal=DEEPS, fill_solid=True)
    k.corridor(2, 20, 10)
    k.dark_chamber(14, 14, 16, 6, entrance=(13, 19), glow=20)
    _audits(k, "a dark chamber with a way in")

    # -------------------------------------------------- THE OBSIDIAN NEST
    # A two-row lattice: solid on row 15 while group 1 is ON, on row 16 while
    # it is OFF. The corridor is passable in one configuration and not the
    # other, which is the whole verb of this world in four tiles.
    g, k = _grid(30, 20, pal=NEST, fill_solid=True)
    k.corridor(1, 17, 28)
    k.switch_lattice(10, 15, 8, 2, group="a", pattern="rows", phase=1)
    k.g.ent("switch_a", 3, 17)
    k.g.ent("player_spawn", 2, 17)
    sizes = k.reconfig_check((2, 17), (27, 17))
    _check(len(sizes) == 4, "reconfig_check should try four configurations")
    _check(sizes[(True, False)] > sizes[(False, False)],
           "the lattice should be passable with group 1 ON and shut with it "
           "OFF: %s" % (sizes,))

    # ROOT HOLLOW's circular bridge, at lattice scale: the gate is shut in the
    # configuration you start in, and the only lever is on the far side of it.
    # The goal IS reachable in some configuration, so the naive question passes
    # -- it is the unreachable lever that makes it a softlock.
    g, k = _grid(30, 20, pal=NEST, fill_solid=True)
    k.corridor(1, 17, 28)
    k.switch_gate(14, 17, 3, group="a", solid_when="on")
    k.g.ent("switch_a", 20, 17)
    _raises(lambda: k.reconfig_check((2, 17), (27, 17)),
            "softlock", "a lever stranded behind its own gate")

    print("world_kit selftest: %d checks, %d failed" % (_CHECKS[0], len(_FAILS)))
    for f in _FAILS:
        print("  FAIL  %s" % f)
    return not _FAILS


# =========================================================================
# Proof rooms.
#
# The kit's limits table is only worth something if the prover agrees with it,
# so `--emit-proofs` writes a room per number: one at the limit that must
# PROVE, and a twin past it that must FAIL. Without the failing twin, a passing
# room says nothing about where the edge is.
#
#   python3 tools/world_kit.py --emit-proofs
#   tools/prove.sh --level-file=res://tests/fixtures/world_kit/rise_frog_3.json
#
# Rooms are carved out of solid rock and no larger than they need to be, for
# the reason tests/fixtures/make_fixtures.py gives: a failing room should fail
# because the search exhausted the frontier, not because it ran out of budget
# wandering open sky.
# =========================================================================

def _room(w, h, pal=JUNGLE, form="human"):
    from gen_levels import Grid
    g = Grid(w, h)
    k = Kit(g, pal, form=form)
    k.fill_solid()
    return g, k


def proof_rise(form, rise, seam=False):
    """A staircase of `rise`-tile steps, drawn with `Kit.stair`.

    Drawn with the kit's own helper on purpose. The first version of this room
    hand-placed its rungs with `g.rect`, alternating them left and right of the
    shaft -- which put SIX tiles of horizontal travel between consecutive rungs
    and made the room a test of the human's flat reach instead of its rise.
    `rise_human_2` failed it, at a closest approach of 0.0 px: the search kept
    touching the waypoint in mid-flight and never landed. A proof room that
    measures the wrong axis is the same failure as the six shipped defects, one
    level up, and the fix was to route it through the checks the kit already
    has.

    The steps are adjacent columns (run 3, width 3), so the only thing between
    one stand row and the next is the rise.

    ONE HOP, spawn straight to the exit, also on purpose. The obvious way to
    write this is a hop per rung, and that version found a route for every
    single rung and was then rejected by the prover's own tape check -- because
    a hop seam where the tape holds a button across it makes the search and the
    replay disagree. `seam=True` builds that version; it is committed as
    `rise_human_2_seam` and it is a reproduction of a prover bug, not a
    measurement of a step. See proof_tunnel_seam() for the mechanism.
    """
    rungs = 4
    w = 10 + rungs * 3
    h = 8 + rungs * rise
    g, k = _room(w, h, form=form)
    y = h - 3                                   # feet row on the ground floor
    k.clear_rect(1, y - rungs * rise - 2, w - 2, rungs * rise + 3)
    k.floor(1, y + 1, w - 2, depth=2)
    # unchecked: half of these rooms exist to measure a step the kit refuses
    # to draw, which is the only way to find out whether it is right to refuse.
    steps = k.stair(6, y - rise + 1, rungs, rise, 3, 3, form=form,
                    unchecked=True)
    for i, (sx, sy, _sw) in enumerate(steps[:-1]):
        k.g.mark("rung_%d" % (i + 1), sx + 1, sy)
    top = steps[-1]
    g.ent("player_spawn", 2, y)
    g.ent("exit", top[0] + 1, top[1])
    prev = "spawn"
    if form != "human":
        # A hop cannot declare a form the route has not arrived in: the prover
        # rejects "the hop declares form 'frog' but the route arrives as
        # 'human'". So every non-human room spends its first hop on a pad.
        g.ent("pad_%s" % form, 4, y)
        g.route("spawn", "pad_%s" % form, form="human")
        prev = "pad_%s" % form
    if seam:
        for i in range(rungs - 1):
            g.route(prev, "rung_%d" % (i + 1), form=form)
            prev = "rung_%d" % (i + 1)
    g.route(prev, "exit", form=form)
    return g


def proof_gap(form, gap):
    """Two shelves `gap` tiles apart over a spike pit, with a fair landing.

    Two things about this room were learned the hard way and are the reason it
    looks like this.

    The pit has to be a HOLE. The first version carved only the air above the
    shelves, so the "gap" was solid floor: `gap_human_5` proved a five-tile
    jump the character never made -- it walked across. A room that proves the
    wrong thing is worse than no room, and the verdict looked like good news.

    The pit has to be SPIKED. With an open pit, a failing search spends its
    whole budget wandering around the bottom of the hole -- the manhattan
    heuristic dives into it, exactly as ADR 005's addendum describes -- and
    `gap_human_5` took over 90 seconds without deciding anything. The prover
    prunes any state that touches a hazard, so spikes collapse the reachable
    space to the two shelves and the air between them, and a room that cannot
    be crossed exhausts its frontier in a second instead of timing out. That is
    also the shape jungle_1's spike pit already has.
    """
    h = 15
    g, k = _room(9 + gap + MIN_LANDING + 4, h, form=form)
    y = 9
    k.clear_rect(1, y - 4, g.w - 2, 5)
    k.floor(1, y + 1, 8, depth=2)
    k.floor(9 + gap, y + 1, MIN_LANDING + 3, depth=2)
    k.clear_rect(9, y + 1, gap, 2)
    k.rect(9, y + 3, gap, 1, "hazard")
    g.ent("player_spawn", 2, y)
    g.ent("exit", 9 + gap + 2, y)
    prev = "spawn"
    if form != "human":
        g.ent("pad_%s" % form, 5, y)
        g.route("spawn", "pad_%s" % form, form="human")
        prev = "pad_%s" % form
    g.route(prev, "exit", form=form)
    return g


def proof_colonnade():
    """SUNKEN RUINS: the fish weaves over and under four columns."""
    g, k = _room(44, 24, pal=RUINS, form="fish")
    k.flooded_chamber(2, 8, 40, 12, surface=11)
    names = k.colonnade(8, 4, 7, surface=11, bed=19, mark="col")
    k.clear_rect(2, 6, 4, 5)
    k.floor(2, 11, 4, depth=2)                   # the dry shelf you start on
    k.bank(38, 11, 4, rise=1)
    g.ent("player_spawn", 3, 10)
    g.ent("pad_fish", 5, 10)
    g.ent("exit", 39, 9)
    g.route("spawn", "pad_fish", form="human")
    prev = "pad_fish"
    for n in names:
        g.route(prev, n, form="fish")
        prev = n
    g.route(prev, "exit", form="fish")
    return g


def proof_cloud_deck():
    """THERMAL HEIGHTS: the bird crosses at the largest hop ever proved here."""
    g, k = _room(40, 24, pal=HEIGHTS, form="bird")
    k.clear_rect(1, 2, 38, 21)
    k.floor(1, 22, 6, depth=2)
    names = k.cloud_deck([(8, 20), (17, 15), (26, 15), (33, 11)],
                         width=3, mark="perch")
    g.ent("player_spawn", 3, 21)
    g.ent("pad_bird", 5, 21)
    g.ent("exit", 34, 10)
    g.route("spawn", "pad_bird", form="human")
    prev = "pad_bird"
    for n in names:
        g.route(prev, n, form="bird")
        prev = n
    g.route(prev, "exit", form="bird")
    return g


def proof_tunnel():
    """TERMITE DEEPS: an L of tunnel with a ladder in the riser.

    The breakable plug is deliberately NOT on this route. The prover cannot
    break a tile, so a hop through one fails the gate -- this room proves the
    tunnel and the ladder, which is what the prover can answer.

    The hop seam is on flat floor, not at the top of the ladder. That is not
    taste: a seam at a ladder top makes the prover reject its own tape. See
    `proof_tunnel_seam`.
    """
    g, k = _room(40, 24, pal=DEEPS, form="human")
    k.tunnel([(2, 20), (22, 20), (22, 10), (36, 10)])
    k.g.mark("mid_floor", 10, 20)
    g.ent("player_spawn", 3, 20)
    g.ent("exit", 35, 10)
    g.route("spawn", "mid_floor", form="human")
    g.route("mid_floor", "exit", form="human")
    return g


def proof_tunnel_seam():
    """The same tunnel with the hop seam AT THE TOP OF THE LADDER, which the
    prover rejects -- and the geometry is not why.

    tools/prove.sh reports:

        FAIL deeps_tunnel_seam - the tape does not reproduce the proof
             hop 2/2 riser_top > exit replayed to (534, 154),
             but the search left it at (550, 154)

    Sixteen pixels, one tile. Measured, by emitting three rooms over the same
    geometry:

      * one hop, spawn straight to exit ................. PROVES
      * two hops, seam on flat floor at (10,20) ......... PROVES
      * two hops, seam at the ladder top (23,10) ........ rejected

    So it is the seam, not the shape. `ProverSearch._set_input` derives
    `jump_pressed` / `jump_released` from the PREVIOUS MACRO, and at the start
    of a hop there is no previous macro, so every button the tape holds across
    the seam reads as a fresh press. `prove.gd::_selfcheck` replays the hops
    back to back with `prev` carried across, which is what the integration tier
    and a human thumb both do. The search is therefore optimistic by one edge
    at every hop boundary, and a climb -- where `up` is held continuously and
    `climbing` latches on the press -- is where one edge is worth a whole tile.

    This is a FALSE NEGATIVE, not a hole in the gate: the prover refuses to
    emit a tape it cannot reproduce, which is the right call. The cost is that
    an author gets a pixel-difference message for a level that is fine, and the
    fix is to move the seam. tools/solver/** is another agent's; this room is
    the reproduction, committed so the bug is not rediscovered.
    """
    g, k = _room(40, 24, pal=DEEPS, form="human")
    k.tunnel([(2, 20), (22, 20), (22, 10), (36, 10)])
    k.g.mark("riser_top", 23, 10)
    g.ent("player_spawn", 3, 20)
    g.ent("exit", 35, 10)
    g.route("spawn", "riser_top", form="human")
    g.route("riser_top", "exit", form="human")
    return g


def proof_lattice():
    """THE OBSIDIAN NEST: a switch-block gate you have to flip to pass."""
    g, k = _room(34, 18, pal=NEST, form="human")
    k.corridor(1, 15, 32)
    # Group 2 starts OFF, so switch_b_off is solid at spawn and this gate is
    # shut until switch_b is thrown. The lever is on the near side of it, which
    # is exactly what ROOT HOLLOW's bridge got wrong.
    k.switch_gate(20, 15, 4, group="b", solid_when="off")
    k.g.ent("switch_b", 8, 15)
    k.g.mark("past_gate", 24, 15)
    g.ent("player_spawn", 2, 15)
    g.ent("exit", 30, 15)
    g.route("spawn", "switch_b", form="human")
    g.route("switch_b", "past_gate", form="human")
    g.route("past_gate", "exit", form="human")
    return g


## name -> (builder, verdict), where verdict is what tools/prove.sh is expected
## to do with the room:
##
##   "prove"  exit 0. The shape is authorable and the gate agrees.
##   "fail"   exit 1. The failing twin of a "prove" room, one tile past the
##            limit. Without it, a passing room says nothing about where the
##            edge is -- tests/fixtures/make_fixtures.py makes this argument
##            better than I can.
##   "measure" no expected verdict. Whatever the prover says IS the number.
##   "bug"    fails for a reason that is not the geometry. See the docstring.
##   "coarse" every step in it proves on its own, and the whole climb in one hop
##            exhausts the budget -- ADR 005's "a hop that needs a big budget is
##            a hop that is too coarse". Normally you split it into hops; that is
##            what `rise_human_2_seam` does, and the seam bug then rejects it.
##            So this room is blocked, and BOTH halves of why are committed.
PROOFS = {
    "rise_human_2":     (lambda: proof_rise("human", 2), "coarse"),
    "rise_human_2_seam": (lambda: proof_rise("human", 2, seam=True), "bug"),
    "rise_human_3":     (lambda: proof_rise("human", 3), "fail"),
    "rise_frog_3":      (lambda: proof_rise("frog", 3), "prove"),
    "rise_frog_4":      (lambda: proof_rise("frog", 4), "measure"),
    "rise_frog_6":      (lambda: proof_rise("frog", 6), "fail"),
    "gap_human_3":      (lambda: proof_gap("human", 3), "prove"),
    "gap_human_4":      (lambda: proof_gap("human", 4), "measure"),
    "gap_human_5":      (lambda: proof_gap("human", 5), "measure"),
    "gap_human_7":      (lambda: proof_gap("human", 7), "fail"),
    "gap_frog_3":       (lambda: proof_gap("frog", 3), "prove"),
    "gap_frog_4":       (lambda: proof_gap("frog", 4), "measure"),
    "gap_frog_6":       (lambda: proof_gap("frog", 6), "fail"),
    "ruins_colonnade":  (proof_colonnade, "prove"),
    "heights_deck":     (proof_cloud_deck, "prove"),
    "deeps_tunnel":     (proof_tunnel, "prove"),
    "deeps_tunnel_seam": (proof_tunnel_seam, "bug"),
    "nest_lattice":     (proof_lattice, "prove"),
}

def emit_proofs(outdir=PROOF_DIR):
    os.makedirs(outdir, exist_ok=True)
    written = []
    for name in sorted(PROOFS):
        build, expect = PROOFS[name]
        g = build()
        doc = g.to_dict(name, name.replace("_", " ").upper())
        path = os.path.join(outdir, name + ".json")
        with open(path, "w") as f:
            json.dump(doc, f, indent=1)
            f.write("\n")
        verdict = {"prove": "must PROVE", "fail": "must FAIL",
                   "measure": "measurement",
                   "bug": "known prover bug",
                   "coarse": "blocked: hop too coarse"}[expect]
        print("  %-18s %2dx%-2d  %d hop(s)  %s"
              % (name + ".json", g.w, g.h, len(g.hops), verdict))
        written.append(path)
    print("\n  Prove them one at a time -- a \"must FAIL\" room is supposed to")
    print("  exit 1, so a loop with `set -e` stops on the first one:\n")
    print("    for f in %s/*.json; do" % os.path.relpath(outdir, ROOT))
    print("      tools/prove.sh --budget=12000 --level-file=res://$f; "
          "echo \"$f -> $?\"")
    print("    done")
    return written


def main(argv):
    if "--emit-proofs" in argv:
        emit_proofs()
        return 0
    if "--legend-needs" in argv:
        # The list REPORT.md quotes: every tile this kit draws with that has no
        # character in data/level_legend.json yet.
        want = {}
        for pal in (RUINS, HEIGHTS, DEEPS, NEST):
            for role, tile in pal.missing():
                want.setdefault(tile, []).append("%s.%s" % (pal.world, role))
        for tile in sorted(want):
            tid = tiles().by_name.get(tile)
            print("  %-24s id %-4s %s" % (tile, tid, ", ".join(want[tile])))
        print("\n  %d tile(s) need a legend character." % len(want))
        return 0
    ok = selftest()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
