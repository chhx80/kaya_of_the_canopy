"""Cuts the owner's title-screen picture of Kaya out of its white background.
Usage: cut_title_kaya.py <source.jpg> <out.png>. The figure itself is not
touched: only the background is made transparent."""
import sys
from collections import deque
from PIL import Image, ImageFilter

def main(src, dst):
    im = Image.open(src).convert("RGB"); w, h = im.size; px = im.load()
    def page(p): return min(p) >= 224 and max(p) - min(p) <= 20
    def pale(p): return min(p) >= 186 and max(p) - min(p) <= 34
    def comps(test):
        lab = [0] * (w * h); out = []
        for sy in range(h):
            for sx in range(w):
                if lab[sy * w + sx] or not test(px[sx, sy]): continue
                lab[sy * w + sx] = 1; q = deque([(sx, sy)]); pts = []; edge = False
                while q:
                    x, y = q.popleft(); pts.append((x, y))
                    if x in (0, w - 1) or y in (0, h - 1): edge = True
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h and not lab[ny * w + nx] and test(px[nx, ny]):
                            lab[ny * w + nx] = 1; q.append((nx, ny))
                out.append((edge, pts))
        return out
    mask = Image.new("L", (w, h), 255); mp = mask.load()
    # the page itself: everything pale that reaches the border
    for edge, pts in comps(page):
        if edge:
            for x, y in pts: mp[x, y] = 0
    # pockets of page between arm, hair and body, and the JPEG-grey slivers of
    # it caught in her hair. Never the whites of her face (eyes, teeth), which
    # all sit inside FACE.
    FACE = (w * 0.30, h * 0.10, w * 0.72, h * 0.27)
    for edge, pts in comps(pale):
        if edge or len(pts) < 4: continue
        if any(FACE[0] <= x <= FACE[2] and FACE[1] <= y <= FACE[3] for x, y in pts): continue
        for x, y in pts: mp[x, y] = 0
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.6))
    out = im.convert("RGBA"); out.putalpha(mask); out = out.crop(out.getbbox())
    out.save(dst); print(out.size)

main(sys.argv[1], sys.argv[2])
