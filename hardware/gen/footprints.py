"""Generate the project footprint library hardware/lib/dmxnow.pretty.

Dimensions checked against the manufacturer drawings (hardware/datasheets/):
  - Omron G5RL catalogue, page 5, G5RL-1A-E-HR (omron-g5rl.pdf);
  - WAGO 2604-1102 data sheet, page 2, 18.02.2024 (wago-2604-1102.pdf).
Every dimension lives in DIMS with its source. 🔴 Human review still required before
any order (hardware/REVIEW.md).
"""
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "lib", "dmxnow.pretty")

DIMS = {
    "G5RL": {
        "source": "Omron G5RL-1A-E-HR, catalogue G5RL p. 5 (PCB mounting holes, bottom view): "
                  "six holes 1.3 +-0.1 mm, coil 1/8 7.5 mm apart, COM 3/6 at 20 mm, "
                  "NO 4/5 at 25 mm; body 29.0 x 12.7 x 15.7 mm max, (2.3) behind the coil pins.",
        "coil": [(0.0, 0.0), (7.5, 0.0)],             # A1, A2 (Omron 1, 8; no polarity)
        "com": [(0.0, 20.0), (7.5, 20.0)],            # 13 (Omron 3, 6)
        "no": [(0.0, 25.0), (7.5, 25.0)],             # 14 (Omron 4, 5)
        "drill": 1.3, "pad": 2.6,
        "body": (-2.6, -2.3, 10.1, 26.7),
    },
    "WAGO2604": {
        "source": "WAGO 2604-1102 data sheet p. 2: pin spacing 5 mm, 2 pins per pole 8.2 mm "
                  "apart, hole 1.3 mm, pin 0.8 x 1 mm; body 16.3 mm deep (front pin 5.2 mm "
                  "from the wire-entry face, rear pin 2.9 mm from the back), lever 2.9 mm "
                  "beyond the front face (19.2 mm overall), width L = (n - 1) x 5 + 7.4 mm.",
        "pitch": 5.0, "row": 8.2, "drill": 1.4, "pad": (2.0, 2.8),   # WAGO: hole 1.3 +0.1; JLC PTH tolerance -0.08
        "body_front": 5.2, "body_back": 11.1,   # y extent from the front row: +front (wire entry) / -back
        "lever": 2.9,                           # overhang beyond the front face (upper part only)
        "side": 3.7,                            # (L - (n - 1) x pitch) / 2
    },
}


_NS = uuid.UUID("0b7c7a1e-3f5e-4a53-9d2b-1f4a7f0c9e11")
_count = [0]


def _uid():
    """Deterministic UUIDs: regenerating gives an identical file."""
    _count[0] += 1
    return str(uuid.uuid5(_NS, str(_count[0])))


def _text(kind, txt, x, y, layer, size=1.0, hide=False):
    return ('  (fp_text %s "%s" (at %.3f %.3f) (layer "%s")%s\n'
            '    (effects (font (size %.2f %.2f) (thickness %.2f)))\n'
            '    (tstamp %s)\n  )\n') % (kind, txt, x, y, layer, " hide" if hide else "",
                                          size, size, size * 0.15, _uid())


def _rect(x1, y1, x2, y2, layer, width):
    return ('  (fp_rect (start %.3f %.3f) (end %.3f %.3f) (stroke (width %.2f) (type solid)) '
            '(fill none) (layer "%s") (tstamp %s))\n') % (x1, y1, x2, y2, width, layer, _uid())


def _line(x1, y1, x2, y2, layer, width):
    return ('  (fp_line (start %.3f %.3f) (end %.3f %.3f) (stroke (width %.2f) (type solid)) '
            '(layer "%s") (tstamp %s))\n') % (x1, y1, x2, y2, width, layer, _uid())


def _pad_tht(num, x, y, shape, sx, sy, drill):
    return ('  (pad "%s" thru_hole %s (at %.3f %.3f) (size %.3f %.3f) (drill %.3f) '
            '(layers "*.Cu" "*.Mask") (tstamp %s))\n') % (num, shape, x, y, sx, sy, drill, _uid())


def _header(name, descr, tags):
    return ('(footprint "%s" (version 20221018) (generator dmxnow_footprints)\n'
            '  (layer "F.Cu")\n  (descr "%s")\n  (tags "%s")\n  (attr through_hole)\n'
            % (name, descr, tags))


def _write(name, body):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name + ".kicad_mod"), "w") as f:
        f.write(body + ")\n")


def relay_g5rl():
    d = DIMS["G5RL"]
    name = "Relay_SPST_Omron_G5RL-1A-E-HR"
    x1, y1, x2, y2 = d["body"]
    s = _header(name, "Omron G5RL-1A-E-HR 16A high inrush SPST-NO, reinforced coil-contact insulation. " + d["source"],
                "relay omron G5RL 16A inrush")
    s += _text("reference", "REF**", 3.75, -3.8, "F.SilkS")
    s += _text("value", name, 3.75, 28.0, "F.Fab")
    s += _rect(x1, y1, x2, y2, "F.Fab", 0.1)
    s += _rect(x1 - 0.12, y1 - 0.12, x2 + 0.12, y2 + 0.12, "F.SilkS", 0.12)
    s += _rect(x1 - 0.5, y1 - 0.5, x2 + 0.5, y2 + 0.5, "F.CrtYd", 0.05)
    # coil / contacts separation marker (slot is cut in the board, see pcb.py)
    s += _line(x1, 12.0, x2, 12.0, "F.Fab", 0.1)
    for (x, y), n in zip(d["coil"], ("A1", "A2")):
        s += _pad_tht(n, x, y, "rect" if n == "A1" else "circle", 2.0, 2.0, d["drill"])
    for x, y in d["com"]:
        s += _pad_tht("13", x, y, "circle", d["pad"], d["pad"], d["drill"])
    for x, y in d["no"]:
        s += _pad_tht("14", x, y, "circle", d["pad"], d["pad"], d["drill"])
    s += ('  (model "${KICAD7_3DMODEL_DIR}/Relay_THT.3dshapes/Relay_SPST_Omron_G2RL-1A-E.wrl"\n'
          '    (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n')
    _write(name, s)


def wago_2604(poles):
    d = DIMS["WAGO2604"]
    name = "TerminalBlock_WAGO_2604-110%d_1x%02d_P5.00mm_Horizontal" % (poles, poles)
    p = d["pitch"]
    w = (poles - 1) * p
    x1, x2 = -d["side"], w + d["side"]
    y1, y2 = -d["body_back"], d["body_front"]
    y3 = y2 + d["lever"]
    s = _header(name, "WAGO 2604-110%d lever PCB terminal block, %d poles, pitch 5.0 mm, "
                      "4 mm2, side wire entry towards +Y. %s" % (poles, poles, d["source"]),
                "WAGO 2604 lever terminal block")
    s += _text("reference", "REF**", w / 2, y1 - 1.5, "F.SilkS")
    s += _text("value", name, w / 2, y2 + 1.5, "F.Fab", 0.8)
    s += _rect(x1, y1, x2, y2, "F.Fab", 0.1)
    s += _rect(x1 - 0.12, y1 - 0.12, x2 + 0.12, y2 + 0.12, "F.SilkS", 0.12)
    s += _rect(x1, y2, x2, y3, "F.Fab", 0.1)     # lever overhang (above the board)
    s += _rect(x1 - 0.25, y1 - 0.25, x2 + 0.25, y3 + 0.25, "F.CrtYd", 0.05)
    # wire entry arrows
    for i in range(poles):
        x = i * p
        s += _line(x, y2 + 0.3, x, y2 - 1.5, "F.Fab", 0.1)
        s += _line(x - 0.6, y2 - 0.9, x, y2 - 1.5, "F.Fab", 0.1)
        s += _line(x + 0.6, y2 - 0.9, x, y2 - 1.5, "F.Fab", 0.1)
    for i in range(poles):
        for row in (0.0, -d["row"]):
            shape = "roundrect" if (i == 0 and row == 0.0) else "oval"
            pad = _pad_tht(str(i + 1), i * p, row, shape, d["pad"][0], d["pad"][1], d["drill"])
            if shape == "roundrect":
                pad = pad.replace('(layers "*.Cu" "*.Mask")', '(layers "*.Cu" "*.Mask") (roundrect_rratio 0.25)')
            s += pad
    _write(name, s)


def varistor_10d():
    """10D561K disc varistor (LCSC C113236, HEL 10D series): leads d = 0.8 +-0.1 mm,
    pitch 7.5 mm, disc 12 mm, thickness T up to 9.0 mm (430-560 V row of the datasheet).
    KiCad's RV_Disc_D12mm_W4.2mm_P7.5mm drills 0.8 mm (too tight with JLC's -0.08 mm
    tolerance) and assumes a 4.2 mm body."""
    name = "RV_Disc_D12mm_T9mm_P7.5mm_Drill1.1"
    s = _header(name, "Disc varistor 10D series (12 mm), pitch 7.5 mm, lead offset 1.63 mm, "
                      "body up to 9 mm thick, 1.1 mm holes (lead 0.8 +-0.1 mm)", "varistor MOV 10D")
    s += _text("reference", "REF**", 3.75, -5.0, "F.SilkS")
    s += _text("value", name, 3.75, 7.0, "F.Fab", 0.8)
    yc = 1.633 / 2
    s += _rect(-2.25, yc - 4.5, 9.75, yc + 4.5, "F.Fab", 0.1)
    s += _rect(-2.37, yc - 4.62, 9.87, yc + 4.62, "F.SilkS", 0.12)
    s += _rect(-2.5, yc - 4.75, 10.0, yc + 4.75, "F.CrtYd", 0.05)
    s += _pad_tht("1", 0.0, 0.0, "circle", 2.2, 2.2, 1.1)
    s += _pad_tht("2", 7.5, 1.633, "circle", 2.2, 2.2, 1.1)
    s += ('  (model "${KICAD7_3DMODEL_DIR}/Varistor.3dshapes/RV_Disc_D12mm_W4.2mm_P7.5mm.wrl"\n'
          '    (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n')
    _write(name, s)


def irm03():
    """Mean Well IRM-03-xx (PCB mounting style), from the IRM-03 datasheet p. 4 (2025-08-08):
    pins 0.6 +-0.1 mm, AC/L (1) - AC/N (3) 5.08 mm, NC (5) 30.48 mm from AC/L, -Vo (14) and
    +Vo (16) on the second row 17.78 mm away, body 37 x 24 mm. Same pad layout as KiCad's
    Converter_ACDC_MeanWell_IRM-03-xx_THT, but 1.0 mm holes (0.76-0.8 mm is too tight for a
    0.7 mm pin with JLCPCB's -0.08 mm tolerance)."""
    name = "Converter_ACDC_MeanWell_IRM-03-xx_THT_Drill1.0"
    s = _header(name, "Mean Well IRM-03 AC-DC module, THT, 1.0 mm holes", "Mean Well IRM-03 AC-DC")
    s += _text("reference", "REF**", 8.89, -4.5, "F.SilkS")
    s += _text("value", name, 8.89, 35.0, "F.Fab", 0.8)
    s += _rect(-3.11, -3.26, 20.89, 33.74, "F.Fab", 0.1)
    s += _rect(-3.23, -3.38, 21.01, 33.86, "F.SilkS", 0.15)
    s += _rect(-3.36, -3.51, 21.14, 33.99, "F.CrtYd", 0.05)
    s += _pad_tht("1", 0.0, 0.0, "rect", 2.3, 2.0, 1.0)     # as KiCad: 2.93 mm to pin 3
    for num, x, y in (("3", 0.0, 5.08), ("5", 0.0, 30.48), ("14", 17.78, 30.48), ("16", 17.78, 25.4)):
        s += _pad_tht(num, x, y, "circle", 2.3, 2.3, 1.0)
    s += ('  (model "${KICAD7_3DMODEL_DIR}/Converter_ACDC.3dshapes/Converter_ACDC_MeanWell_IRM-03-xx_THT.wrl"\n'
          '    (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n')
    _write(name, s)


if __name__ == "__main__":
    relay_g5rl()
    varistor_10d()
    irm03()
    for n in (2, 5):
        wago_2604(n)
    print("footprints written to", os.path.normpath(OUT))
