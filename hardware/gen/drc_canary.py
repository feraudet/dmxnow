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
import subprocess
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
    path = os.path.join(OUT, "dmxnow.kicad_pcb")
    board.Save(path)
    rpt = os.path.join(OUT, "drc.rpt")
    # prefer the same engine as the CI DRC step (kicad-cli, KiCad 8+); KiCad 7 has no
    # `pcb drc` in kicad-cli, so fall back to the pcbnew API on the in-memory board
    r = subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "-o", rpt, path],
                       capture_output=True, text=True) if shutil.which("kicad-cli") else None
    if r is None or r.returncode != 0 or not os.path.exists(rpt):
        name = next(n for n in ("EDA_UNITS_MILLIMETRES", "EDA_UNITS_MM") + tuple(
            n for n in dir(pcbnew) if n.startswith("EDA_UNITS_") and ("MILLI" in n or n.endswith("_MM")))
            if hasattr(pcbnew, n))
        pcbnew.WriteDRCReport(board, rpt, getattr(pcbnew, name), False)
        engine = "pcbnew API"
    else:
        engine = "kicad-cli"
    txt = open(rpt).read()
    # "Rule: <name>; Severity: error" (KiCad 7) or "Rule: <name>; error" (KiCad 8+)
    fired = set(re.findall(r"Rule: (\w+);", txt))
    print("DRC engine:", engine)
    missing = [r for *_, r in CANARIES if r not in fired]
    for *_, r in CANARIES:
        print("%-24s %s" % (r, "fired" if r in fired else "NOT FIRED"))
    if missing:
        print("DRC canary FAILED: custom rules not active:", ", ".join(missing))
        print("---- report (rules seen: %s) ----" % ", ".join(sorted(fired)))
        print("\n".join(l for l in txt.splitlines() if "Rule:" in l or l.startswith("[")) [:4000])
        return 1
    print("DRC canary: all custom 230 V rules active")
    return 0


if __name__ == "__main__":
    sys.exit(main())
