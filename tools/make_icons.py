#!/usr/bin/env python3
"""PWA icons for رحلة العمرة: a deep-navy tile with a simple Kaaba (black cube, gold band and
door) under a soft warm glow and a thin gold ring — the concept's colours.
    python3 tools/make_icons.py      # → public/icons/*.png
Drawn with Pillow at 4× and down-sampled; "maskable" keeps the art inside the 80 % safe zone."""
import os
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'public/icons'); os.makedirs(OUT, exist_ok=True)
S = 2048
NAVY_IN, NAVY_OUT, GOLD, GOLD_HI = (52, 74, 120), (20, 30, 52), (212, 168, 77), (246, 220, 152)

def tile(maskable):
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    bg = Image.new('RGBA', (S, S))
    px = bg.load(); cx, cy, R = S / 2, S * 0.42, S * 0.75
    for y in range(0, S, 4):
        for x in range(0, S, 4):
            t = min(1, ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 / R)
            c = tuple(int(NAVY_IN[i] + (NAVY_OUT[i] - NAVY_IN[i]) * t) for i in range(3)) + (255,)
            for dy in range(4):
                for dx in range(4): px[x + dx, y + dy] = c
    mask = Image.new('L', (S, S), 0); md = ImageDraw.Draw(mask)
    if maskable: md.rectangle([0, 0, S, S], fill=255)
    else: md.rounded_rectangle([32, 32, S - 32, S - 32], radius=int(S * 0.22), fill=255)
    img.paste(bg, (0, 0), mask)
    # warm glow
    glow = Image.new('RGBA', (S, S), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    gd.ellipse([S * 0.18, S * 0.2, S * 0.82, S * 0.84], fill=(255, 205, 120, 90))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(S * 0.06)))
    d = ImageDraw.Draw(img)
    k = 0.8 if maskable else 1.0                     # shrink into the safe zone
    def P(x, y): return (S / 2 + (x - 0.5) * S * k, S / 2 + (y - 0.5) * S * k)
    # gold ring
    r = 0.39
    d.ellipse([*P(0.5 - r, 0.5 - r), *P(0.5 + r, 0.5 + r)], outline=GOLD + (255,), width=int(S * 0.012 * k))
    # Kaaba: two visible faces of a cube (front-left darker, front-right lighter) + top
    top = [P(0.5, 0.26), P(0.75, 0.35), P(0.5, 0.44), P(0.25, 0.35)]
    left = [P(0.25, 0.35), P(0.5, 0.44), P(0.5, 0.74), P(0.25, 0.65)]
    right = [P(0.5, 0.44), P(0.75, 0.35), P(0.75, 0.65), P(0.5, 0.74)]
    d.polygon(top, fill=(38, 38, 44, 255)); d.polygon(left, fill=(14, 14, 17, 255)); d.polygon(right, fill=(24, 24, 28, 255))
    # gold band (hizam) on both faces
    for a, b, h in [((0.25, 0.42), (0.5, 0.51), 0.045), ((0.5, 0.51), (0.75, 0.42), 0.045)]:
        d.polygon([P(*a), P(*b), P(b[0], b[1] + h), P(a[0], a[1] + h)], fill=GOLD + (255,))
    d.line([P(0.25, 0.42), P(0.5, 0.51), P(0.75, 0.42)], fill=GOLD_HI + (255,), width=int(S * 0.005 * k))
    # gold door on the right face
    d.polygon([P(0.56, 0.56), P(0.64, 0.53), P(0.64, 0.66), P(0.56, 0.69)], fill=GOLD + (255,))
    # edge highlight
    d.line([P(0.5, 0.44), P(0.5, 0.74)], fill=(70, 70, 80, 255), width=int(S * 0.004 * k))
    return img

for name, m in [('icon', False), ('maskable', True)]:
    big = tile(m)
    for size in (192, 512):
        big.resize((size, size), Image.LANCZOS).save(os.path.join(OUT, f'{name}-{size}.png'), optimize=True)
tile(False).resize((180, 180), Image.LANCZOS).save(os.path.join(OUT, 'apple-touch-icon.png'))
tile(False).resize((32, 32), Image.LANCZOS).save(os.path.join(OUT, 'favicon-32.png'))
print('icons →', OUT, sorted(os.listdir(OUT)))
