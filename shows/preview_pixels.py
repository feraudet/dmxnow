"""Planche d'aperçu des conduites d'un ruban adressable : une vignette par conduite, le
ruban en largeur (pixel 1 à gauche), le temps vers le bas (4 s par défaut).

    PYTHONPATH=pi enclosure/.venv/bin/python shows/preview_pixels.py shows/pixels/*.dxs \\
        -o docs/figures/conduites-pixels.png
"""
from __future__ import annotations

import argparse
import os

from PIL import Image, ImageDraw, ImageFont

from dmxnow.show import Show

GAMMA = 2.2


def panel(s: Show, order: str, seconds: float, frame_ms: int = 25) -> Image.Image:
    n = len(s.channels) // 3
    rows = int(seconds * 1000 / frame_ms)
    img = Image.new("RGB", (n, rows))
    idx = {c: order.index(c) for c in "RGB"}
    for y in range(rows):
        v = s.render(y * frame_ms)
        for x in range(n):
            px = v[3 * x:3 * x + 3]
            # back to what the eye sees (the show values are gamma-encoded duty cycles)
            img.putpixel((x, y), tuple(int(255 * (px[idx[c]] / 255) ** (1 / GAMMA)) for c in "RGB"))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--order", default="RBG")
    ap.add_argument("--seconds", type=float, default=4)
    ap.add_argument("--cols", type=int, default=4)
    a = ap.parse_args()
    shows = [(os.path.splitext(os.path.basename(f))[0], Show.decode(open(f, "rb").read())) for f in sorted(a.files)]
    w, h, label = 200, 240, 22
    rows = (len(shows) + a.cols - 1) // a.cols
    sheet = Image.new("RGB", (a.cols * (w + 10) + 10, rows * (h + label + 10) + 10), (236, 240, 241))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    for k, (name, s) in enumerate(shows):
        x0, y0 = 10 + (k % a.cols) * (w + 10), 10 + (k // a.cols) * (h + label + 10)
        draw.text((x0, y0), name, fill=(44, 62, 80), font=font)
        sheet.paste(panel(s, a.order, a.seconds).resize((w, h), Image.NEAREST), (x0, y0 + label))
    sheet.save(a.output)
    print("written", a.output)


if __name__ == "__main__":
    main()
