"""Aperçu d'une conduite .dxs : couleur du ruban au fil du temps et valeurs des canaux,
calculées comme le nœud les calcule (Show.render, 40 images par seconde).

    PYTHONPATH=pi python3 shows/preview.py shows/feu-de-cheminee.dxs -o docs/figures/feu-de-cheminee.png

Demande matplotlib (par exemple le venv du boîtier : enclosure/.venv/bin/python).
"""
from __future__ import annotations

import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from dmxnow.show import Show  # noqa: E402

NAMES = ["R", "V", "B", "W"]
COLORS = ["#C0392B", "#27AE60", "#3498DB", "#95A5A6"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--seconds", type=float, default=20)
    ap.add_argument("--seam", action="store_true", help="centre the window on the loop restart")
    a = ap.parse_args()
    s = Show.decode(open(a.file, "rb").read())
    start = s.loop_ms - a.seconds * 500 if a.seam else 0
    ts = [start + i * 25 for i in range(int(a.seconds * 40))]
    vals = [s.render(int(t)) for t in ts]
    xs = [(t - start) / 1000 for t in ts]

    fig, (band, curves) = plt.subplots(2, 1, figsize=(9, 5.5), height_ratios=[1, 3], sharex=True)
    rgb = [[(min(1, (v[0] + v[3]) / 255), min(1, (v[1] + v[3]) / 255), min(1, (v[2] + v[3]) / 255))
            for v in vals]]
    band.imshow(rgb, aspect="auto", extent=(xs[0], xs[-1], 0, 1))
    band.set_yticks([])
    band.set_title(f"{s.name} : couleur du ruban" + (" (reprise de la boucle au milieu)" if a.seam else ""))
    for c in range(min(4, len(s.channels))):
        curves.plot(xs, [v[c] for v in vals], color=COLORS[c], lw=1.2, label=NAMES[c])
    curves.set_ylim(0, 260)
    curves.set_ylabel("valeur DMX (0 à 255)")
    curves.set_xlabel("temps (s)")
    curves.legend(loc="upper right", ncol=4)
    curves.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(a.output, dpi=110)
    print("written", a.output)


if __name__ == "__main__":
    main()
