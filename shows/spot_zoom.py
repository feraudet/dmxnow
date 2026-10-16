"""Conduite « spot zoom » pour le projecteur Eurolite LED IP PAR-64 COB 3000K 100W Zoom.

Projecteur en mode 4 canaux à l'adresse 1 (docs/cablage.md §3) : canal 1 gradateur,
2 stroboscope, 3 zoom, 4 courbe de gradation. En boucle de 20 s : le projecteur monte
de 0 à plein feu en ouvrant son zoom (8 s), reste à fond 2 s, redescend en refermant le
zoom (8 s), reste éteint 2 s. Stroboscope à 0 (LED allumée), courbe du menu (canal 4 à 0).

    PYTHONPATH=pi python3 shows/spot_zoom.py            # shows/spot-zoom.dxs
    PYTHONPATH=pi python3 shows/spot_zoom.py --addr 10  # projecteur à l'adresse 10
    dmxnow show deploy shows/spot-zoom.dxs node-2442B0
"""
from __future__ import annotations

import argparse
import os

from dmxnow.show import Show, abs_slot

HERE = os.path.dirname(os.path.abspath(__file__))


def build(args) -> Show:
    s = Show("spot-zoom", [abs_slot(args.addr + k) for k in range(4)], resume_s=args.resume_s)
    off, full = [0, 0, 0, 0], [255, 0, 255, 0]   # dimmer, strobe (LED on), zoom, curve from the menu
    s.step(2000, off)    # back to keyframe 0: stays off 2 s
    s.step(8000, full)   # up to full, zoom opening
    s.step(2000, full)   # hold
    s.step(8000, off)    # down, zoom closing
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-o", "--output", default=os.path.join(HERE, "spot-zoom.dxs"))
    ap.add_argument("--addr", type=int, default=1, help="projector DMX address (default 1)")
    ap.add_argument("--resume-s", type=int, default=5, help="seconds without DMX before the show resumes")
    args = ap.parse_args()
    s = build(args)
    with open(args.output, "wb") as f:
        f.write(s.encode())
    print(s.describe())
    print("written", os.path.relpath(args.output))


if __name__ == "__main__":
    main()
