"""The app icon: the owner's picture of Kaya (assets/title/kaya.png, the same
one the title screen shows) from the chest up, in front of the title screen's
own sunset and moon.

She is not redrawn. Her picture is enlarged so that each of its pixels stays a
crisp square with a clean edge (nearest-neighbour up, then an area filter down
to the target size), which is as sharp as the picture itself allows. The sky's
colours are read from assets/sprites/title_bg.png, so the icon and the title
can never drift apart.

Writes export/icons/icon_master.png (1024x1024, RGB, no alpha: iOS wants a
flat square and rounds the corners itself). tools/art/backdrops.py derives
every shipped size from it.

Run: $PYVENV tools/art/app_icon.py   (tools/genart.sh calls build()).
"""
import os

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KAYA = os.path.join(ROOT, "assets", "title", "kaya.png")
TITLE_BG = os.path.join(ROOT, "assets", "sprites", "title_bg.png")
OUT = os.path.join(ROOT, "export", "icons", "icon_master.png")

S = 1024
BUST_ROWS = 286          # rows of her picture shown: hat crown to mid top
BUST_W = 936             # her hat brim's width on the icon
BUST_TOP = 74
CELL = 8                 # the sky is drawn in blocks this size, like her pixels
MOON = (512, 408, 372)   # centre x, centre y, radius


def _crisp(img, size):
    """Enlarge keeping every source pixel a hard-edged square."""
    k = max(2, -(-size[0] * 3 // img.width))
    big = img.resize((img.width * k, img.height * k), Image.NEAREST)
    return big.resize(size, Image.LANCZOS)


def _sky():
    """The title's sunset bands, top to bottom, and its moon's colours."""
    bg = Image.open(TITLE_BG).convert("RGB")
    w, h = bg.size
    # each row's commonest colour over the right-hand third, which is clear of
    # the moon; the hanging vines and stars are never the commonest. The
    # canopy starts about 62% of the way down, so only the sky is stretched.
    col = []
    for y in range(int(h * 0.60)):
        seen = {}
        for x in range(int(w * 0.66), w):
            c = bg.getpixel((x, y))
            seen[c] = seen.get(c, 0) + 1
        col.append(max(seen, key=seen.get))
    n = S // CELL
    small = Image.new("RGB", (n, n))
    px = small.load()
    for y in range(n):
        # the commonest colour of the rows this block covers, so a one-row
        # dither line in the title never becomes a stripe here
        a = y * len(col) // n
        span = col[max(0, a - 3):a + 4]
        c = max(set(span), key=span.count)
        for x in range(n):
            px[x, y] = c
    # the moon: its face and rim, read from the title's own
    counts = {}
    for y in range(int(h * 0.45), int(h * 0.62)):
        for x in range(int(w * 0.40), int(w * 0.62)):
            c = bg.getpixel((x, y))
            if c[0] > 220 and c[1] > 190:
                counts[c] = counts.get(c, 0) + 1
    tones = sorted(counts, key=counts.get, reverse=True)
    face = tones[0] if tones else (253, 240, 180)
    rim = next((c for c in tones[1:] if abs(c[2] - face[2]) > 30), (244, 206, 96))
    cx, cy, r = (v / CELL for v in MOON)
    for y in range(n):
        for x in range(n):
            d = ((x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2) ** 0.5
            if d < r - 2.2:
                px[x, y] = face
            elif d < r:
                px[x, y] = rim
    return small.resize((S, S), Image.NEAREST)


def build():
    icon = _sky().convert("RGBA")
    src = Image.open(KAYA).convert("RGBA")
    bust = src.crop((0, 0, src.width, BUST_ROWS))
    h = round(BUST_ROWS * BUST_W / src.width)
    bust = _crisp(bust, (BUST_W, h))
    x, y = (S - BUST_W) // 2, BUST_TOP
    # a soft shadow so she stands off the moon
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sh = Image.new("RGBA", bust.size, (40, 14, 46, 150))
    sh.putalpha(bust.split()[3].point(lambda v: v * 150 // 255))
    shadow.alpha_composite(sh, (x + 10, y + 14))
    icon.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)))
    icon.alpha_composite(bust, (x, y))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    icon.convert("RGB").save(OUT)
    print("icon_master.png  %dx%d" % icon.size)
    return icon.convert("RGB")


SIZES = (1024, 512, 256, 192, 180, 167, 152, 144, 120, 114, 108, 87,
         80, 76, 72, 60, 58, 40, 29, 20)
IOS_SET = os.path.join(ROOT, "ios", "KayaOfTheCanopy", "Images.xcassets", "AppIcon.appiconset")


def write_all():
    """The master, then every size that ships, each reduced from the master in
    one step with an area filter (never from another reduced size):
    export/icons/icon_<n>.png for the export presets, the project icon
    assets/sprites/icon.png, and the committed Xcode project's icon set."""
    master = build()
    out = os.path.dirname(OUT)
    for n in SIZES:
        master.resize((n, n), Image.LANCZOS).save(os.path.join(out, "icon_%d.png" % n))
    master.resize((128, 128), Image.LANCZOS).save(
        os.path.join(ROOT, "assets", "sprites", "icon.png"))
    if os.path.isdir(IOS_SET):
        for fn in sorted(os.listdir(IOS_SET)):
            if fn.startswith("Icon-") and fn.endswith(".png"):
                n = int(fn[5:-4].split("-")[0])
                master.resize((n, n), Image.LANCZOS).save(os.path.join(IOS_SET, fn))
    print("app icon: %d export sizes, icon.png, ios icon set" % len(SIZES))


if __name__ == "__main__":
    write_all()
