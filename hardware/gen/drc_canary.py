"""DRC canary: prove that the custom 230 V rules (dmxnow.kicad_dru) are loaded and
active in the running KiCad version. A malformed rule or an unknown function is
silently ignored by KiCad, so a clean DRC alone does not prove the rules work.

Copies the board and project to build/canary/, injects copper that each rule must
reject, runs DRC and requires every expected violation.

  python3 drc_canary.py        (exit 1 if a rule did not fire)
"""
import os
import re
import shutil
import sys

import pcbnew

import pcb as P

HW = P.HW
OUT = os.path.join(HW, "build", "canary")

# (net, layer, (x1, y1), (x2, y2), width, rule expected to fire)
CANARIES = [
    # GND 3 mm from the L_PSU track at x=43.5: mains <-> low voltage (6 mm)
    ("GND", pcbnew.F_Cu, (47.0, 5.0), (47.0, 9.0), 0.3, "mains_to_low_voltage"),
    # L_PSU 1.4 mm from the N finger of J1 (bottom layer): between mains nets (3 mm)
    ("L_PSU", pcbnew.B_Cu, (13.0, 14.0), (15.0, 14.0), 0.3, "mains_between_nets"),
    # GND 3 mm from PS1 pin 5 (NC, primary row) at (68.48, 48)
    ("GND", pcbnew.F_Cu, (72.8, 46.0), (72.8, 50.0), 0.3, "ps1_nc_pin"),
]


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    for ext in ("kicad_pro", "kicad_dru"):
        shutil.copy(os.path.join(HW, "dmxnow." + ext), os.path.join(OUT, "dmxnow." + ext))
    # the canaries touch no other copper (KiCad would rename them on reload); the DRC
    # runs on the in-memory board, with the project's rules
    board = pcbnew.LoadBoard(os.path.join(HW, "dmxnow.kicad_pcb"))
    for net, layer, a, b, w, _ in CANARIES:
        P.add_track(board, net, layer, w, [a, b])
    board.Save(os.path.join(OUT, "dmxnow.kicad_pcb"))   # for inspection only
    rpt = os.path.join(OUT, "drc.rpt")
    pcbnew.WriteDRCReport(board, rpt, pcbnew.EDA_UNITS_MILLIMETRES, False)
    txt = open(rpt).read()
    fired = set(re.findall(r"Rule: (\w+); Severity: error", txt))
    missing = [r for *_, r in CANARIES if r not in fired]
    for *_, r in CANARIES:
        print("%-24s %s" % (r, "fired" if r in fired else "NOT FIRED"))
    if missing:
        print("DRC canary FAILED: custom rules not active:", ", ".join(missing))
        return 1
    print("DRC canary: all custom 230 V rules active")
    return 0


if __name__ == "__main__":
    sys.exit(main())
