"""20 conduites pour un ruban adressable (WS2811) derrière un décodeur DMX (SP201E).

Le ruban de référence : WS2811 24 V, 10 m, 100 pixels de 6 LED, couleurs dans l'ordre
R, B, G, décodeur réglé sur l'adresse 41 (docs/cablage.md §4 bis). Chaque pixel prend
3 canaux de la ligne DMX : les conduites pilotent les canaux absolus 41 à 340.

Le nœud ne fait qu'un fondu linéaire d'une image clé à la suivante. Un mouvement le long
du ruban se fait donc en décalant le motif d'un pixel par image clé : le fondu entre deux
images donne un déplacement continu. Les motifs qui défilent sont périodiques le long du
ruban (période de 20 à 50 pixels) : la boucle tient en autant d'images que la période.

    PYTHONPATH=pi python3 shows/ruban_pixels.py                      # les 20, dans shows/pixels/
    PYTHONPATH=pi python3 shows/ruban_pixels.py --only arc-en-ciel   # une seule
    PYTHONPATH=pi python3 shows/ruban_pixels.py --brightness 50      # moitié moins lumineux
    dmxnow show deploy shows/pixels/01-arc-en-ciel.dxs node-2442B0
"""
from __future__ import annotations

import argparse
import colorsys
import math
import os
import random

from dmxnow.show import Show, abs_slot

HERE = os.path.dirname(os.path.abspath(__file__))
GAMMA = 2.2          # the eye sees the LED duty cycle as roughly value ** (1 / 2.2)

Pixel = tuple[float, float, float]   # r, g, b from 0 to 1
Frame = list[Pixel]


def hsv(h: float, s: float = 1.0, v: float = 1.0) -> Pixel:
    return colorsys.hsv_to_rgb(h % 1.0, s, v)


def scale(c: Pixel, k: float) -> Pixel:
    return (c[0] * k, c[1] * k, c[2] * k)


def add(a: Pixel, b: Pixel) -> Pixel:
    return (min(1.0, a[0] + b[0]), min(1.0, a[1] + b[1]), min(1.0, a[2] + b[2]))


def mix(a: Pixel, b: Pixel, t: float) -> Pixel:
    return tuple(x + (y - x) * t for x, y in zip(a, b))


BLACK: Pixel = (0.0, 0.0, 0.0)


def scroll(pattern: list[Pixel], n: int, step_ms: int, direction: int = 1) -> list[tuple[int, Frame]]:
    """One keyframe per pixel of shift: the pattern repeats along the strip and moves one
    pixel per keyframe, so the loop is as long as the pattern."""
    p = len(pattern)
    return [(step_ms, [pattern[(i - direction * k) % p] for i in range(n)]) for k in range(p)]


def comet(length: int, tail: int, color: Pixel) -> list[Pixel]:
    """Head at 0, tail behind it (towards lower positions once it moves up)."""
    out = [BLACK] * length
    for t in range(tail):
        out[(-t) % length] = scale(color, (1 - t / tail) ** 2)
    return out


# --- the 20 shows: each returns (name, keyframes) ----------------------------------------

def arc_en_ciel(n, rng):
    return scroll([hsv(x / 50) for x in range(50)], n, 60)


def fondu_couleurs(n, rng):
    return [(1500, [hsv(k / 12)] * n) for k in range(12)]


def comete(n, rng):
    return scroll(comet(25, 10, (1.0, 0.45, 0.0)), n, 40)


def scanner(n, rng):
    out = []
    path = list(range(0, n, 3)) + list(range(n - 1, 0, -3))
    for pos in path:
        out.append((30, [scale((1.0, 0.0, 0.0), max(0.0, 1 - abs(i - pos) / 4)) for i in range(n)]))
    return out


def respiration(n, rng):
    return [(500, [scale((0.0, 0.25, 1.0), 0.06 + 0.94 * (0.5 - 0.5 * math.cos(2 * math.pi * k / 8)))] * n)
            for k in range(8)]


def feu(n, rng):
    frames, heat = [], [rng.random() for _ in range(n)]
    for _ in range(120):
        heat = [0.6 * h + 0.4 * rng.random() for h in heat]
        smooth = [(heat[i - 1] + 2 * heat[i] + heat[(i + 1) % n]) / 4 for i in range(n)]
        frames.append((rng.randint(70, 130), [mix((0.5, 0.02, 0.0), (1.0, 0.55, 0.05), h) for h in smooth]))
    return frames


def etoiles(n, rng, kf=80):
    sky = (0.0, 0.01, 0.05)
    sparks = [(rng.randrange(kf), rng.randrange(n)) for _ in range(kf * 2)]
    frames = []
    for k in range(kf):
        f = [sky] * n
        for t0, i in sparks:
            age = (k - t0) % kf
            if age < 4:
                f[i] = add(f[i], scale((1.0, 0.9, 0.7), 1 - age / 4))
        frames.append((150, f))
    return frames


def ocean(n, rng):
    return scroll([mix((0.0, 0.05, 0.35), (0.1, 0.8, 0.9), (0.5 + 0.5 * math.sin(2 * math.pi * x / 20)) ** 2)
                   for x in range(20)], n, 120)


def soleil_couchant(n, rng):
    stops = [((1.0, 0.75, 0.1), (1.0, 0.35, 0.0)), ((1.0, 0.35, 0.0), (0.8, 0.05, 0.1)),
             ((0.8, 0.05, 0.1), (0.35, 0.0, 0.35)), ((0.35, 0.0, 0.35), (0.02, 0.0, 0.2)),
             ((0.02, 0.0, 0.2), (0.0, 0.0, 0.05)), ((0.6, 0.3, 0.2), (1.0, 0.6, 0.1))]
    return [(8000, [mix(a, b, i / (n - 1)) for i in range(n)]) for a, b in stops]


def police(n, rng):
    red = [(1.0, 0.0, 0.0) if i < n // 2 else BLACK for i in range(n)]
    blue = [(0.0, 0.0, 1.0) if i >= n // 2 else BLACK for i in range(n)]
    out = []
    for side in (red, blue):
        for _ in range(2):
            out += [(0, side), (80, side), (0, [BLACK] * n), (80, [BLACK] * n)]
        out += [(150, [BLACK] * n)]
    return out


def theatre(n, rng):
    amber = (1.0, 0.5, 0.0)
    out = []
    for k in range(3):
        f = [amber if i % 3 == k else BLACK for i in range(n)]
        out += [(0, f), (180, f)]
    return out


def aurore(n, rng, kf=30):
    out = []
    for k in range(kf):
        t = 2 * math.pi * k / kf
        f = []
        for i in range(n):
            x = 2 * math.pi * i / n
            g = 0.5 + 0.5 * math.sin(3 * x + t) * math.cos(2 * x - 2 * t)
            p = 0.5 + 0.5 * math.sin(5 * x - t)
            f.append(add(scale((0.0, 1.0, 0.45), g ** 2), scale((0.45, 0.0, 0.6), (p * (1 - g)) ** 2)))
        out.append((1000, f))
    return out


def croisement(n, rng):
    red, blue = comet(50, 12, (1.0, 0.0, 0.1)), comet(50, 12, (0.0, 0.2, 1.0))
    # blue runs the other way: its head at -k, its tail on the right of the head
    return [(50, [add(red[(i - k) % 50], blue[-(i + k) % 50]) for i in range(n)]) for k in range(50)]


def chaud_froid(n, rng):
    grad = [mix((1.0, 0.45, 0.05), (0.05, 0.6, 1.0), i / (n - 1)) for i in range(n)]
    return [(2500, [scale(c, k) for c in grad]) for k in (1.0, 0.7, 0.4, 0.7)]


def remplissage(n, rng):
    colors = [(0.0, 1.0, 0.2), (0.6, 0.0, 1.0), (1.0, 0.6, 0.0), (0.0, 0.5, 1.0)]
    out = []
    for c, under in zip(colors, colors[-1:] + colors[:-1]):
        for k in range(1, 21):
            out.append((60, [c if i < k * n // 20 else under for i in range(n)]))
        out.append((800, out[-1][1]))
    return out


def lave(n, rng):
    return scroll([mix((0.35, 0.0, 0.0), (1.0, 0.35, 0.0),
                       (0.5 + 0.25 * math.sin(2 * math.pi * x / 50) + 0.25 * math.sin(6 * math.pi * x / 50)) ** 1.5)
                   for x in range(50)], n, 200)


def confettis(n, rng, kf=60):
    drops = [(rng.randrange(kf), rng.randrange(n), rng.random()) for _ in range(kf * 3)]
    out = []
    for k in range(kf):
        f = [BLACK] * n
        for t0, i, h in drops:
            age = (k - t0) % kf
            if age < 6:
                f[i] = add(f[i], hsv(h, 1.0, 1 - age / 6))
        out.append((120, f))
    return out


def noel(n, rng):
    a = [(1.0, 0.0, 0.0) if (i // 5) % 2 == 0 else (0.0, 0.8, 0.0) for i in range(n)]
    b = [(0.0, 0.8, 0.0) if (i // 5) % 2 == 0 else (1.0, 0.0, 0.0) for i in range(n)]
    gold = [(1.0, 0.7, 0.2) if i % 10 == 0 else c for i, c in enumerate(a)]
    return [(1500, a), (2000, a), (300, gold), (1500, b), (2000, b)]


def meteores(n, rng):
    return scroll(comet(33, 8, (0.7, 0.85, 1.0)), n, 30)


def coeur(n, rng):
    shape = [0.25 + 0.75 * math.exp(-((i - n / 2) / (n / 5)) ** 2) for i in range(n)]
    red = (1.0, 0.0, 0.05)

    def at(level):
        return [scale(red, level * s) for s in shape]
    return [(600, at(0.12)), (400, at(0.12)), (110, at(1.0)), (140, at(0.35)), (110, at(0.8)), (300, at(0.12))]


SHOWS = [arc_en_ciel, fondu_couleurs, comete, scanner, respiration, feu, etoiles, ocean, soleil_couchant,
         police, theatre, aurore, croisement, chaud_froid, remplissage, lave, confettis, noel, meteores, coeur]


def show_name(fn) -> str:
    return fn.__name__.replace("_", "-")


def build(fn, args) -> Show:
    rng = random.Random(args.seed)
    frames = fn(args.pixels, rng)
    order = ["RGB".index(c) for c in args.order]
    level = args.brightness / 100
    channels = [abs_slot(args.addr + k) for k in range(3 * args.pixels)]
    s = Show(show_name(fn), channels, resume_s=args.resume_s)
    for dur, frame in frames:
        values = []
        for px in frame:
            values += [255 * (px[o] * level) ** GAMMA for o in order]
        s.step(dur, values)
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-o", "--output", default=os.path.join(HERE, "pixels"), help="output folder")
    ap.add_argument("--only", help="build only this show (e.g. arc-en-ciel)")
    ap.add_argument("--addr", type=int, default=41, help="decoder DMX start channel (default 41)")
    ap.add_argument("--pixels", type=int, default=100, help="pixels on the strip (default 100)")
    ap.add_argument("--order", default="RBG", help="colour order of the strip (default RBG)")
    ap.add_argument("--brightness", type=int, default=100, help="0 to 100 %%")
    ap.add_argument("--resume-s", type=int, default=5, help="seconds without DMX before the show resumes")
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    if sorted(args.order.upper()) != ["B", "G", "R"]:
        ap.error("--order: a permutation of R, G, B")
    args.order = args.order.upper()
    if not 1 <= args.addr or args.addr + 3 * args.pixels - 1 > 512:
        ap.error("--addr and --pixels: the strip must fit in channels 1 to 512")
    os.makedirs(args.output, exist_ok=True)
    for k, fn in enumerate(SHOWS, 1):
        if args.only and show_name(fn) != args.only:
            continue
        s = build(fn, args)
        path = os.path.join(args.output, f"{k:02d}-{show_name(fn)}.dxs")
        with open(path, "wb") as f:
            f.write(s.encode())
        print(f"{os.path.relpath(path)}: {len(s.steps)} keyframes, loop {s.loop_ms / 1000:.1f} s, "
              f"{len(s.encode()) // 1024} ko")


if __name__ == "__main__":
    main()
