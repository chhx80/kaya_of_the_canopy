#!/usr/bin/env python3
"""Hashes everything that ends up inside the exported .pck.

Used to detect a committed ios/KayaOfTheCanopy.pck that has fallen behind the
source. Deliberately excludes generated/derived trees so the hash only moves
when the game actually changes.
"""
import hashlib, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCLUDE = ["src", "data", "levels", "assets", "project.godot"]
SKIP_SUFFIX = (".import", ".uid")

h = hashlib.sha256()
for entry in INCLUDE:
    p = os.path.join(ROOT, entry)
    if os.path.isfile(p):
        h.update(entry.encode())
        h.update(open(p, "rb").read())
        continue
    for root, dirs, files in os.walk(p):
        dirs.sort()
        for f in sorted(files):
            if f.endswith(SKIP_SUFFIX) or f.startswith("."):
                continue
            fp = os.path.join(root, f)
            h.update(os.path.relpath(fp, ROOT).encode())
            h.update(open(fp, "rb").read())
print(h.hexdigest())
