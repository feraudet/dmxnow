"""Fabrication outputs for JLCPCB (SPEC §8.2).

  hardware/fab/gerbers/*          Gerber X2 (Protel extensions) + Excellon PTH/NPTH
  hardware/fab/dmxnow-gerbers.zip archive to upload (breakaway slot and mouse bites are
                                  in Edge.Cuts / NPTH: no V-cut)
  hardware/fab/bom_jlcpcb_<v>.csv, cpl_jlcpcb_<v>.csv   JLCPCB assembly files, variants:
      smt, smt_led      SMT only (Economic PCBA), THT parts soldered by hand
      full, full_led    SMT + THT (Standard PCBA)             (_led: option A7)
  hardware/fab/bom_full.csv       every part, including hand-soldered and off-board items

CPL: KiCad footprint origins/orientations are converted to the JLCPCB library
conventions (JLC_FIX below, from the EasyEDA footprints of the LCSC parts). The
placement preview must still be checked at order time (REVIEW.md 5.4).

LCSC part numbers checked against the JLCPCB parts API on 2026-09-26 (SPEC §10 V-HW-13).
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
    ("ATO blade fuse 20 A", "F2 fuse (<= 80 % continuous load, see REVIEW.md)", 1, "Littelfuse 0257020", "full"),
    ("Fuse 5x20 T500mA H 250V ceramic", "F1 cartridge, into the F1 holder (LCSC C142839)", 1,
     "Littelfuse 0215.500MXP", "full+cut"),
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
    for old in glob.glob(os.path.join(OUT, "*vcut*")):
        os.remove(old)
    zpath = os.path.join(OUT, "dmxnow-gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(gdir)):
            z.write(os.path.join(gdir, f), f)
    print("gerbers:", zpath)


def _smt(p):
    return not any(k in p.footprint for k in ("THT", "TerminalBlock", "Relay", "Fuse", "Varistor",
                                                "PinHeader", "MountingHole", "Converter_ACDC",
                                                "SolderWire", "NetTie", "CP_Radial"))


# footprint name -> (rotation offset deg, dx, dy): JLC centroid = KiCad origin + (dx, dy)
# in footprint coordinates (mm, KiCad axes); JLC rotation = KiCad rotation + offset.
JLC_FIX = {
    "SOT-23": (180, 0.0, 0.0),
    "SOT-23-5": (270, 0.0, 0.0),
    "SOIC-8_3.9x4.9mm_P1.27mm": (270, 0.0, 0.0),
    "SOIC-14_3.9x8.7mm_P1.27mm": (270, 0.0, 0.0),
    "TO-252-2": (0, -1.8, 0.0),          # JLC origin 1.8 mm towards the leads
    "ESP32-C3-MINI-1": (0, 0.0, 2.7),    # JLC origin at the centre of the pad array
    # THT (JLC centroid = body centre, computed from the courtyard)
    "Relay_SPST_Omron_G5RL-1A-E-HR": (-90, None, None),
    "Converter_ACDC_MeanWell_IRM-03-xx_THT": (-90, None, None),
    "FuseHolder_Blade_ATO_Littelfuse_FLR_178.6165": (180, None, None),
}
THT_DEFAULT = (0, None, None)

VARIANTS = {
    "smt": lambda p: not p.dnp and _smt(p),
    "smt_led": lambda p: (not p.dnp or p.variant == "led") and _smt(p),
    "full": lambda p: not p.dnp,
    "full_led": lambda p: not p.dnp or p.variant == "led",
}


def _assembled(p):
    return not p.symbol.startswith("Mechanical:") and p.footprint.split(":")[0] != "Connector_Wire"


def boms():
    for old in glob.glob(os.path.join(OUT, "bom_jlcpcb_*.csv")) + glob.glob(os.path.join(OUT, "cpl_jlcpcb_*.csv")):
        os.remove(old)
    for vname, keep in VARIANTS.items():
        rows = {}
        for p in design.PARTS:
            if not keep(p) or not _assembled(p):
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
                        "SMT" if _smt(p) else "THT", p.note])
        for name, note, qty, mpn, var in OFF_BOARD:
            w.writerow(["-", name, "-", mpn, "", var, "x%d" % qty, "off-board", note])


def cpl():
    import pcbnew
    board = pcbnew.LoadBoard(PCB)
    origin = board.GetDesignSettings().GetAuxOrigin()
    parts = {p.ref: p for p in design.PARTS}
    placed = []
    for fp in board.GetFootprints():
        p = parts.get(fp.GetReference())
        if p is None or not _assembled(p):
            continue
        name = fp.GetFPID().GetLibItemName().wx_str()
        rot0 = fp.GetOrientationDegrees()
        dr, dx, dy = JLC_FIX.get(name, (0, 0.0, 0.0) if _smt(p) else THT_DEFAULT)
        if dx is None:   # THT: body centre from the courtyard
            c = fp.GetCourtyard(pcbnew.F_CrtYd).BBox().Centre()
            x, y = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
        else:
            import math
            a = math.radians(rot0)
            # KiCad: y down, positive rotation counter-clockwise on screen
            ox = dx * math.cos(a) + dy * math.sin(a)
            oy = -dx * math.sin(a) + dy * math.cos(a)
            x, y = pcbnew.ToMM(fp.GetPosition().x) + ox, pcbnew.ToMM(fp.GetPosition().y) + oy
        placed.append((p, x - pcbnew.ToMM(origin.x), pcbnew.ToMM(origin.y) - y, (rot0 + dr) % 360))
    for vname, keep in VARIANTS.items():
        with open(os.path.join(OUT, "cpl_jlcpcb_%s.csv" % vname), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
            for p, x, y, r in sorted(placed, key=lambda t: t[0].ref):
                if keep(p):
                    w.writerow([p.ref, "%.3fmm" % x, "%.3fmm" % y, "Top", "%g" % r])


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    gerbers()
    boms()
    cpl()
