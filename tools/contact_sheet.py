#!/usr/bin/env python3
"""Scales up generated art into one reviewable contact sheet."""
import os, sys
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files = [
    ("assets/tiles/tileset.png", 4),
    ("assets/sprites/kaya_human.png", 4),
    ("assets/sprites/kaya_frog.png", 4),
    ("assets/sprites/kaya_fish.png", 4),
    ("assets/sprites/kaya_bird.png", 4),
    ("assets/sprites/enemy_walker.png", 4),
    ("assets/sprites/enemy_jumper.png", 4),
    ("assets/sprites/enemy_shooter.png", 4),
    ("assets/sprites/enemy_swimmer.png", 4),
    ("assets/sprites/blade.png", 4),
    ("assets/sprites/pickups.png", 4),
    ("assets/sprites/props.png", 4),
    ("assets/fonts/font8.png", 3),
    ("assets/sprites/logo.png", 1),
]
imgs = []
for f, s in files:
    p = os.path.join(ROOT, f)
    if not os.path.exists(p):
        continue
    im = Image.open(p).convert("RGBA")
    im = im.resize((im.width * s, im.height * s), Image.NEAREST)
    imgs.append(im)
W = max(i.width for i in imgs) + 16
H = sum(i.height + 10 for i in imgs) + 10
out = Image.new("RGBA", (W, H), (24, 26, 34, 255))
y = 6
for im in imgs:
    out.alpha_composite(im, (8, y))
    y += im.height + 10
out.save(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "shots", "art_contact_sheet.png"))
print("ok")
