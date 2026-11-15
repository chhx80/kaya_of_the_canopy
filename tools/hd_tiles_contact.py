#!/usr/bin/env python3
"""Before/after contact sheets of real game frames (docs/hd-tiles-howto.md).

    $PYVENV tools/hd_tiles_contact.py <before dir> <after dir> <out prefix> [names...]

Each row is one capture: the H0 frame on the left, the same sim frame with the
native tiles on the right, both cropped to the world (the pillarbox removed)
and shown at half device size. A second sheet, <prefix>_detail.png, shows a
crop of every pair at device pixels x2, where the texel detail is visible.
"""
import os
import sys

from PIL import Image, ImageDraw


def world_box(img):
    """The game picture inside the black pillarbox."""
    w, h = img.size
    px = img.convert("RGB").load()
    y = h // 2
    x0 = next(x for x in range(w) if sum(px[x, y]) > 60)
    x1 = next(x for x in range(w - 1, -1, -1) if sum(px[x, y]) > 60)
    return x0, 0, x1 + 1, h


def main():
    before, after, prefix = sys.argv[1:4]
    names = sys.argv[4:] or sorted(f for f in os.listdir(after) if f.endswith(".png"))
    pairs = []
    for n in names:
        a = Image.open(os.path.join(before, n)).convert("RGB")
        b = Image.open(os.path.join(after, n)).convert("RGB")
        box = world_box(b)
        pairs.append((n, a.crop(box), b.crop(box)))
    w, h = pairs[0][1].size
    hw, hh = w // 2, h // 2
    sheet = Image.new("RGB", (hw * 2 + 30, len(pairs) * (hh + 24)), (24, 26, 32))
    d = ImageDraw.Draw(sheet)
    for i, (n, a, b) in enumerate(pairs):
        y = i * (hh + 24)
        d.text((4, y + 4), "%s   H0 (1x upscaled)  |  H1 native 2x tiles" % n, fill=(230, 230, 220))
        sheet.paste(a.resize((hw, hh), Image.LANCZOS), (0, y + 22))
        sheet.paste(b.resize((hw, hh), Image.LANCZOS), (hw + 30, y + 22))
    sheet.save(prefix + "_frames.png")
    cw, ch = 300, 220
    det = Image.new("RGB", (cw * 4 + 30, len(pairs) * (ch * 2 + 24)), (24, 26, 32))
    d = ImageDraw.Draw(det)
    for i, (n, a, b) in enumerate(pairs):
        y = i * (ch * 2 + 24)
        cx, cy = (w - cw) // 2, (h - ch) // 2 + 120
        d.text((4, y + 4), "%s   device pixels x2: H0 | H1" % n, fill=(230, 230, 220))
        det.paste(a.crop((cx, cy, cx + cw, cy + ch)).resize((cw * 2, ch * 2), Image.NEAREST), (0, y + 22))
        det.paste(b.crop((cx, cy, cx + cw, cy + ch)).resize((cw * 2, ch * 2), Image.NEAREST),
                  (cw * 2 + 30, y + 22))
    det.save(prefix + "_detail.png")
    print(prefix + "_frames.png", prefix + "_detail.png")


if __name__ == "__main__":
    main()
