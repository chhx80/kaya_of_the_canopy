"""Cuts the owner's title-screen picture of Kaya out of its white background.
Usage: cut_title_kaya.py <source.jpg> <out.png>. The figure itself is not
touched: only the background is made transparent."""
import sys
from collections import deque
from PIL import Image, ImageFilter

def main(src, dst):
    im = Image.open(src).convert("RGB"); w, h = im.size; px = im.load()
    def bg(p): return min(p) >= 224 and max(p) - min(p) <= 20
    lab = [0] * (w * h); comps = []
    for sy in range(h):
        for sx in range(w):
            if lab[sy * w + sx] or not bg(px[sx, sy]): continue
            n = len(comps) + 1; lab[sy * w + sx] = n; q = deque([(sx, sy)]); pts = []; edge = False
            while q:
                x, y = q.popleft(); pts.append((x, y))
                if x in (0, w - 1) or y in (0, h - 1): edge = True
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and not lab[ny * w + nx] and bg(px[nx, ny]):
                        lab[ny * w + nx] = n; q.append((nx, ny))
            comps.append((edge, pts))
    mask = Image.new("L", (w, h), 255); mp = mask.load()
    for edge, pts in comps:
        ys = [p[1] for p in pts]
        # the page, and pockets of page between arm, hair and body; never the
        # small whites of the face (eyes, teeth), which sit in the top fifth
        if edge or (len(pts) >= 6 and min(ys) > h * 0.22):
            for x, y in pts: mp[x, y] = 0
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.6))
    out = im.convert("RGBA"); out.putalpha(mask); out = out.crop(out.getbbox())
    out.save(dst); print(out.size)

main(sys.argv[1], sys.argv[2])
