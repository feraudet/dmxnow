"""Run KiCad DRC through the pcbnew API (KiCad 7+) and summarise the report.

  python3 drc.py [--fill] [report.rpt]
CI runs the authoritative check with `kicad-cli pcb drc` (KiCad 9).
"""
import collections
import os
import re
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.normpath(os.path.join(HERE, "..", "dmxnow.kicad_pcb"))


def run(report, fill=False):
    board = pcbnew.LoadBoard(PCB)
    if fill:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.WriteDRCReport(board, report, pcbnew.EDA_UNITS_MILLIMETRES, True)
    txt = open(report).read()
    items = re.findall(r"^\[(\w+)\]: (.*)$", txt, re.M)
    counts = collections.Counter(k for k, _ in items)
    return txt, items, counts


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    rpt = args[0] if args else os.path.join(HERE, "..", "drc.rpt")
    txt, items, counts = run(rpt, "--fill" in sys.argv)
    for k, v in counts.most_common():
        print("%5d %s" % (v, k))
    print("unconnected:", re.search(r"\*\* Found (\d+) unconnected pads", txt).group(1)
          if re.search(r"\*\* Found (\d+) unconnected pads", txt) else "?")
