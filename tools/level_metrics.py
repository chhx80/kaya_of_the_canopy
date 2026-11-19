#!/usr/bin/env python3
"""Per-section numbers for a level authored in Sections (tools/worlds/jungle_1.py).

    $PYVENV tools/level_metrics.py jungle_1

Reads the proof tape (proofs/<id>.tape.json) and splits its frames by the
section each hop arrives in, then counts that section's enemies. Prints route
seconds, enemies, enemies per route-minute, and the longest stretch of route
between two checkpoints (docs/plan-longer-levels.md asks for no more than
about 25 s).

Route seconds are the PROVER's seconds: a perfect player who is never hit and
never waits. A first play is several times longer.
"""
import importlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))


def main(level_id):
    mod = importlib.import_module("worlds.%s" % level_id)
    g, _k = getattr(mod, level_id)()
    sections = g.sections
    owner = {}
    for s in sections:
        for m in s.route:
            owner[m] = s.key
    checkpoints = [c for s in sections for c in s.checkpoints]
    tape = json.load(open(os.path.join(ROOT, "proofs/%s.tape.json" % level_id)))
    fps = float(tape.get("fps", 60))
    frames = {s.key: 0 for s in sections}
    since_cp, worst_gap, worst_at, at_cp = 0, 0, "", "spawn"
    total = 0
    for hop in tape["hops"]:
        n = sum(int(f["n"]) for f in hop["frames"])
        total += n
        frames[owner.get(hop["to"], sections[-1].key)] += n
        since_cp += n
        if hop["to"] in checkpoints or hop["to"] == "exit":
            if since_cp > worst_gap:
                worst_gap, worst_at = since_cp, "%s -> %s" % (at_cp, hop["to"])
            print("  %-6s -> %-6s %5.1f s" % (at_cp, hop["to"], since_cp / fps))
            since_cp, at_cp = 0, hop["to"]
    print()
    print("%-4s %-16s %7s %8s %10s  %s" % ("", "section", "route s", "enemies",
                                         "per min", "kinds"))
    for s in sections:
        sec = frames[s.key] / fps
        kinds = {}
        for e in s.enemies:
            kinds[e[6:]] = kinds.get(e[6:], 0) + 1
        print("%-4s %-16s %7.1f %8d %10.1f  %s" % (
            s.key, s.title, sec, len(s.enemies),
            len(s.enemies) / sec * 60.0 if sec else 0.0,
            ", ".join("%d %s" % (v, k) for k, v in sorted(kinds.items()))))
    n_en = sum(len(s.enemies) for s in sections)
    print("%-4s %-16s %7.1f %8d %10.1f" % ("", "WHOLE LEVEL", total / fps, n_en,
                                         n_en / (total / fps) * 60.0))
    print("longest stretch between checkpoints: %.1f s (%s)" % (worst_gap / fps, worst_at))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "jungle_1")
