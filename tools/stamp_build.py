#!/usr/bin/env python3
"""Writes data/build_info.json so a running build can say what it is.

Three separate reports have been ambiguous between "the fix does not work" and
"you are playing an older build". Rendering the commit on the title screen
settles that in one glance instead of a round trip.
"""
import json, os, subprocess, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def sh(*a):
    try:
        return subprocess.check_output(a, cwd=ROOT, text=True).strip()
    except Exception:
        return "?"

info = {
    "commit": sh("git", "rev-parse", "--short", "HEAD"),
    "branch": sh("git", "rev-parse", "--abbrev-ref", "HEAD"),
    "built": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    "dirty": bool(sh("git", "status", "--porcelain")),
}
path = os.path.join(ROOT, "data", "build_info.json")
with open(path, "w") as f:
    json.dump(info, f, indent=2)
    f.write("\n")
print("build %s%s (%s)" % (info["commit"], "+dirty" if info["dirty"] else "", info["built"]))
