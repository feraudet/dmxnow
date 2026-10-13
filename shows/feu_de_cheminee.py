"""Conduite « feu de cheminée » pour un ruban RGBW (et, en option, un projecteur DMX).

Le ruban n'est pas adressable : toute sa longueur suit la même couleur. Le feu se fait
donc dans le temps, pas le long du ruban :

- une braise de fond qui monte et descend lentement (quelques secondes) ;
- des flammes qui vacillent vite et irrégulièrement (5 à 10 fois par seconde) ;
- de temps en temps une flambée, de temps en temps un creux ;
- la couleur suit l'intensité : rouge profond quand le feu baisse, jaune orangé quand
  il flambe, une pointe de blanc dans les flambées.

Les images clés tombent à intervalles irréguliers (60 à 140 ms) et le nœud fond
linéairement de l'une à l'autre. La boucle dure 5 minutes et sa fin rejoint son début
sans saut (fondu enchaîné sur les 5 dernières secondes) : la répétition ne se voit pas.

    PYTHONPATH=pi python3 shows/feu_de_cheminee.py                   # shows/feu-de-cheminee.dxs
    PYTHONPATH=pi python3 shows/feu_de_cheminee.py --fixture-rgb 20  # + projecteur RGB en 20-22
    dmxnow show deploy shows/feu-de-cheminee.dxs node-2442B0
"""
from __future__ import annotations

import argparse
import os
import random

from dmxnow.show import Show, abs_slot, rel

HERE = os.path.dirname(os.path.abspath(__file__))


def smooth_noise(rng: random.Random, n: int, step_s: list[float], period_s: float, depth: float) -> list[float]:
    """Random walk low-passed to about period_s, amplitude about +/- depth."""
    out, x, target, left = [], 0.0, 0.0, 0.0
    for dt in step_s:
        left -= dt
        if left <= 0:
            target = rng.uniform(-depth, depth)
            left = rng.uniform(0.5, 1.5) * period_s
        x += (target - x) * min(1.0, dt / (period_s / 3))
        out.append(x)
    return out[:n]


def flame(seconds: float, seed: int) -> tuple[list[int], list[float]]:
    """Durations (ms) and flame intensity 0..1 for each keyframe."""
    rng = random.Random(seed)
    durs = []
    t = 0.0
    while t < seconds:
        d = rng.randint(60, 140)
        durs.append(d)
        t += d / 1000
    n = len(durs)
    dts = [d / 1000 for d in durs]
    ember = smooth_noise(rng, n, dts, 4.0, 0.12)      # slow breathing of the embers
    sway = smooth_noise(rng, n, dts, 0.9, 0.10)       # flames leaning in the draught
    level = []
    flare, flare_left = 0.0, 0.0
    for i in range(n):
        if flare_left <= 0 and rng.random() < 0.004:  # a log catches: ~ every 25 s
            flare, flare_left = rng.uniform(0.15, 0.3), rng.uniform(0.6, 1.8)
        elif flare_left <= 0 and rng.random() < 0.003:  # a gust pushes the flames down
            flare, flare_left = -rng.uniform(0.15, 0.25), rng.uniform(0.3, 0.8)
        flare_left -= dts[i]
        if flare_left <= 0:
            flare *= 0.7
        flicker = rng.gauss(0, 0.09)                  # fast irregular flicker
        level.append(min(1.0, max(0.12, 0.62 + ember[i] + sway[i] + flare + flicker)))
    return durs, level


def make_loop(durs: list[int], level: list[float], fade_s: float) -> tuple[list[int], list[float]]:
    """Cross-fades the last fade_s seconds into the first ones: the loop has no seam."""
    k, t = 0, 0.0
    while t < fade_s:
        t += durs[k] / 1000
        k += 1
    n = len(level) - k
    out = level[:n]
    for i in range(k):
        w = i / k
        out[i] = level[i] * w + level[n + i] * (1 - w)
    return durs[:n], out


def color(x: float) -> tuple[int, int, int, int]:
    """Flame colour for an intensity 0..1, as RGBW 0..255 (before the node's gamma)."""
    r = 255 * x
    g = 255 * x * (0.16 + 0.24 * x * x)               # deep red when low, orange-yellow when high
    w = 255 * max(0.0, x - 0.8) * 0.5                 # a touch of white in the flares only
    return round(r), round(g), 0, round(w)


def build(args) -> Show:
    first = 1 if args.relay_dmx else 0                # strips after the relay channel (PROTOCOL 6.4)
    channels = [rel(first + i) for i in range(4)]
    if args.fixture_rgb:
        channels += [abs_slot(args.fixture_rgb + i) for i in range(3)]
    if args.fixture_dimmer:
        channels.append(abs_slot(args.fixture_dimmer))
    s = Show("feu-cheminee", channels, resume_s=args.resume_s)
    durs, level = make_loop(*flame(args.minutes * 60 + 5, args.seed), 5.0)
    # keyframe 0 is reached from the last one in durs[0]: the rotation keeps the timing
    for d, x in zip(durs, level):
        x *= args.brightness / 100
        r, g, b, w = color(x)
        values = [r, g, b, w]
        if args.fixture_rgb:
            values += [r, g, 0]
        if args.fixture_dimmer:
            values.append(round(255 * x))
        s.step(d, values)
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-o", "--output", default=os.path.join(HERE, "feu-de-cheminee.dxs"))
    ap.add_argument("--minutes", type=float, default=5, help="loop length (default 5)")
    ap.add_argument("--brightness", type=int, default=100, help="0 to 100 %%")
    ap.add_argument("--relay-dmx", type=int, choices=(0, 1), default=1,
                    help="the node's relay_dmx: 1 (default) = strips on start_address + 1 to + 4")
    ap.add_argument("--fixture-rgb", type=int, metavar="SLOT", help="also drive a fixture's R, G, B at SLOT..SLOT+2")
    ap.add_argument("--fixture-dimmer", type=int, metavar="SLOT", help="also drive a fixture's dimmer channel")
    ap.add_argument("--resume-s", type=int, default=5, help="seconds without DMX before the show resumes")
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    s = build(a)
    data = s.encode()
    with open(a.output, "wb") as f:
        f.write(data)
    print(s.describe())
    print("written", os.path.relpath(a.output))


if __name__ == "__main__":
    main()
