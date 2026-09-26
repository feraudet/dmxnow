"""Fabrication outputs for JLCPCB (SPEC §8.2).

  hardware/fab/gerbers/*          Gerber X2 (Protel extensions) + Excellon PTH/NPTH
  hardware/fab/dmxnow-gerbers.zip archive to upload
  hardware/fab/dmxnow-vcut.gbr    V-cut line (User.1 layer), see README_FAB.md
  hardware/fab/bom_jlcpcb_base.csv, bom_jlcpcb_led.csv   SMT assembly BOMs (option A7)
  hardware/fab/cpl_jlcpcb_base.csv, cpl_jlcpcb_led.csv   placement files
  hardware/fab/bom_full.csv       every part, including hand-soldered and off-board items

LCSC part numbers are indicative and must be checked (SPEC §10 V-HW-13).
"""
import csv
import glob
import os
import shutil
import subprocess
import zipfile

import design

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, ".."))
PCB = os.path.join(HW, "dmxnow.kicad_pcb")
OUT = os.path.join(HW, "fab")
GERBER_LAYERS = ["F.Cu", "B.Cu", "F.Paste", "B.Paste", "F.SilkS", "B.SilkS", "F.Mask", "B.Mask", "Edge.Cuts"]

# Items that are not on the PCB but belong to a node (bom_full only)
OFF_BOARD = [
    ("WAGO 221-413", "PE junction, 230 V compartment (arbitrage A9)", 1, "221-413", "full+cut"),
    ("ATO blade fuse 20 A", "F2 fuse", 1, "Littelfuse 0257020", "full"),
    ("Fuse TR5 T500 mA", "F1 (if the holder-less TR5 is socketed)", 0, "", "full+cut"),
    ("Neutrik NC3FXX", "DMX tail connector", 1, "NC3FXX", "full+cut"),
    ("DMX cable 120 ohm, 1 m", "DMX tail", 1, "", "full+cut"),
    ("Cable gland M16 (or PG9)", "mains in, projector out, LED PSU out", 3, "", "full+cut"),
    ("Cable gland PG7", "DMX tail; LED in/out on full board", 3, "", "full+cut"),
    ("M3 heat-set insert + M3 nylon screw", "PCB and lid fixing", 6, "", "full+cut"),
]


def run(cmd):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)


def gerbers():
    gdir = os.path.join(OUT, "gerbers")
    shutil.rmtree(gdir, ignore_errors=True)
    os.makedirs(gdir)
    run(["kicad-cli", "pcb", "export", "gerbers", "--layers", ",".join(GERBER_LAYERS),
         "--subtract-soldermask", "--use-drill-file-origin", "-o", gdir + "/", PCB])
    run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th",
         "--drill-origin", "plot", "-u", "mm", "-o", gdir + "/", PCB])
    vdir = os.path.join(OUT, "vcut")
    os.makedirs(vdir, exist_ok=True)
    run(["kicad-cli", "pcb", "export", "gerbers", "--layers", "User.1,Edge.Cuts", "--use-drill-file-origin",
         "--no-protel-ext", "-o", vdir + "/", PCB])
    for f in glob.glob(os.path.join(vdir, "*User_1*")) + glob.glob(os.path.join(vdir, "*V-CUT*")):
        shutil.move(f, os.path.join(OUT, "dmxnow-vcut.gbr"))
    shutil.rmtree(vdir, ignore_errors=True)
    zpath = os.path.join(OUT, "dmxnow-gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(gdir)):
            z.write(os.path.join(gdir, f), f)
    print("gerbers:", zpath)


def _smt(p):
    return not any(k in p.footprint for k in ("THT", "TerminalBlock", "Relay", "Fuse", "Varistor",
                                                "PinHeader", "MountingHole", "Converter_ACDC",
                                                "SolderWire", "NetTie", "CP_Radial"))


def boms():
    variants = {"base": lambda p: not p.dnp, "led": lambda p: not p.dnp or p.variant == "led"}
    for vname, keep in variants.items():
        rows = {}
        for p in design.PARTS:
            if not keep(p) or not _smt(p):
                continue
            key = (p.value, p.footprint.split(":")[1], p.lcsc)
            rows.setdefault(key, []).append(p.ref)
        with open(os.path.join(OUT, "bom_jlcpcb_%s.csv" % vname), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
            for (val, fp, lcsc), refs in sorted(rows.items(), key=lambda r: r[1][0]):
                w.writerow([val, ",".join(sorted(refs)), fp, lcsc])
    with open(os.path.join(OUT, "bom_full.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Ref", "Value", "Footprint", "MPN", "LCSC", "Section", "Fitted", "Assembly", "Note"])
        for p in design.PARTS:
            if p.symbol.startswith("Mechanical:"):
                continue
            fitted = "DNP (option A7)" if p.variant == "led" else ("no" if p.dnp else "yes")
            w.writerow([p.ref, p.value, p.footprint, p.mpn, p.lcsc, p.section, fitted,
                        "SMT" if _smt(p) else "hand/THT", p.note])
        for name, note, qty, mpn, var in OFF_BOARD:
            w.writerow(["-", name, "-", mpn, "", var, "x%d" % qty, "off-board", note])


def cpl():
    tmp = os.path.join(OUT, "pos_all.csv")
    run(["kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
         "--use-drill-file-origin", "-o", tmp, PCB])
    rows = list(csv.DictReader(open(tmp)))
    os.remove(tmp)
    parts = {p.ref: p for p in design.PARTS}
    for vname in ("base", "led"):
        with open(os.path.join(OUT, "cpl_jlcpcb_%s.csv" % vname), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
            for r in rows:
                p = parts.get(r["Ref"])
                if p is None or not _smt(p):
                    continue
                if p.dnp and not (vname == "led" and p.variant == "led"):
                    continue
                w.writerow([r["Ref"], r["PosX"] + "mm", r["PosY"] + "mm",
                            "Top" if r["Side"] == "top" else "Bottom", r["Rot"]])


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    gerbers()
    boms()
    cpl()
