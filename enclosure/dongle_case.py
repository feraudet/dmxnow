"""Printed case of the USB dongle: Seeed XIAO ESP32-C3 + its 2.4 GHz FPC antenna
(SPEC 4.10, ADR 0002). Low voltage only (5 V USB): PETG or PLA are fine, no V-0 needed.

  python3 dongle_case.py              build, check, export out/dongle/
  python3 dongle_case.py --check-only

Layout along X: USB-C in the end wall at X = 0, the XIAO lying on the floor, then the
FPC antenna stuck (its own adhesive) on the floor, away from the board ground plane.
Two parts: tray (floor down on the bed) and lid (top face down), held by a snap lip.
A slotted tab at the far end takes a cable tie or a strap to hang the dongle high
(SPEC 4.10: dongle up on a USB extension, not behind the Pi).
"""
import argparse
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "dongle")

# --- Parts to house ---------------------------------------------------------------
XIAO_L, XIAO_W = 21.0, 17.8        # Seeed datasheet 113991054
XIAO_PCB = 1.2                     # PCB thickness, to measure (V-ENC-04): 1.0 expected
XIAO_TOP = 3.4                     # tallest part above the PCB: USB-C receptacle (3.2)
USBC_W, USBC_H = 8.94, 3.26        # USB-C receptacle shell (USB-IF)
USBC_OVERHANG = 1.0                # receptacle beyond the PCB edge, to measure (V-ENC-04)
ANT_L, ANT_W, ANT_T = 40.0, 20.0, 0.3   # FPC antenna A-01 (Seeed drawing M01-0601770R0A)
ANT_GAP = 7.0                      # board end to antenna: coax bend, keep the antenna off the ground plane

# --- Case -------------------------------------------------------------------------
WALL, FLOOR, LID = 1.6, 1.4, 1.4
CLR = 0.3                          # parts to walls
IN_L = XIAO_L + ANT_GAP + ANT_L + 1.0
IN_W = max(XIAO_W, ANT_W) + 2 * CLR + 1.0
IN_H = XIAO_PCB + XIAO_TOP + 1.8   # room for the U.FL plug and the coax above the board
LIP = 1.8                          # lid lip depth into the tray
TAB_L, SLOT_W, SLOT_L = 8.0, 3.2, 10.0


def box(x1, y1, z1, x2, y2, z2):
    return cq.Workplane("XY").box(x2 - x1, y2 - y1, z2 - z1, centered=False).translate((x1, y1, z1))


def usbc_z():
    return FLOOR + XIAO_PCB + USBC_H / 2   # receptacle centre, board resting on the floor


def tray():
    ox1, oy1 = -WALL, -IN_W / 2 - WALL
    ox2, oy2 = IN_L + WALL, IN_W / 2 + WALL
    t = box(ox1, oy1, 0, ox2, oy2, FLOOR + IN_H).cut(box(0, -IN_W / 2, FLOOR, IN_L, IN_W / 2, FLOOR + IN_H + 1))
    # USB-C opening in the end wall, receptacle shell + 0.35 mm, taller for the PCB tolerance
    zc = usbc_z()
    t = t.cut(box(-WALL - 1, -USBC_W / 2 - 0.35, zc - USBC_H / 2 - 0.5, 1, USBC_W / 2 + 0.35, zc + USBC_H / 2 + 0.5))
    # counterbore outside so that the plug overmold (12 x 7 mm) seats 0.8 mm deeper
    t = t.cut(box(-WALL - 1, -6.4, zc - 3.6, -WALL + 0.8, 6.4, zc + 3.6))
    # board pocket: side ribs and an end stop, the PCB edge against the end wall
    for s in (-1, 1):
        y = s * (XIAO_W / 2 + CLR)
        t = t.union(box(1.0, min(y, y + s * 0.9), FLOOR - 0.1, XIAO_L - 1.0, max(y, y + s * 0.9), FLOOR + XIAO_PCB + 0.8))
    t = t.union(box(XIAO_L + CLR, -5.0, FLOOR - 0.1, XIAO_L + CLR + 1.2, 5.0, FLOOR + XIAO_PCB))
    # antenna outline: a low border so the FPC is stuck in place
    ax1 = XIAO_L + ANT_GAP
    for s in (-1, 1):
        y = s * (ANT_W / 2 + 0.3)
        t = t.union(box(ax1 + 2, min(y, y + s * 0.8), FLOOR - 0.1, ax1 + ANT_L - 2, max(y, y + s * 0.8), FLOOR + 0.8))
    # snap bead inside the walls, under the lid lip
    zb = FLOOR + IN_H - LIP + 0.5
    for s in (-1, 1):
        y = s * IN_W / 2
        t = t.union(box(8, min(y, y - s * 0.35), zb, IN_L - 8, max(y, y - s * 0.35), zb + 0.6))
    # hanging tab with a cable-tie / strap slot
    t = t.union(box(ox2 - 0.1, -IN_W / 2, 0, ox2 + TAB_L, IN_W / 2, FLOOR + 0.6))
    t = t.cut(box(ox2 + (TAB_L - SLOT_W) / 2, -SLOT_L / 2, -1, ox2 + (TAB_L + SLOT_W) / 2, SLOT_L / 2, 5))
    return t


def lid():
    ox1, oy1 = -WALL, -IN_W / 2 - WALL
    ox2, oy2 = IN_L + WALL, IN_W / 2 + WALL
    z0 = FLOOR + IN_H
    l = box(ox1, oy1, z0, ox2, oy2, z0 + LID)
    # lip inside the walls (0.2 mm clearance), with a groove for the tray bead
    lip = box(0.2, -IN_W / 2 + 0.2, z0 - LIP, IN_L - 0.2, IN_W / 2 - 0.2, z0)
    lip = lip.cut(box(1.4, -IN_W / 2 + 1.4, z0 - LIP - 1, IN_L - 1.4, IN_W / 2 - 1.4, z0 + 1))
    zb = FLOOR + IN_H - LIP + 0.5
    for s in (-1, 1):
        y = s * (IN_W / 2 - 0.2)
        lip = lip.cut(box(7.5, min(y, y - s * 0.5), zb - 0.1, IN_L - 7.5, max(y, y - s * 0.5), zb + 0.7))
    l = l.union(lip)
    # two pressers on the PCB long edges (castellated border, no parts there)
    for s in (-1, 1):
        y = s * (XIAO_W / 2 - 0.4)
        l = l.union(box(4.0, y - 0.4, FLOOR + XIAO_PCB + 0.15, XIAO_L - 4.0, y + 0.4, z0))
    # engraving on the outer face
    txt = (cq.Workplane("XY").workplane(offset=z0 + LID - 0.5)
           .text("dmxnow", 6.0, 1.0, halign="center", valign="center").translate((IN_L / 2 + 6, 0, 0)))
    return l.cut(txt)


def parts_envelope():
    """XIAO (PCB + tallest part over the whole board) and antenna, for the checks."""
    x = box(0, -XIAO_W / 2, FLOOR, XIAO_L, XIAO_W / 2, FLOOR + XIAO_PCB)
    x = x.union(box(3.0, -XIAO_W / 2 + 1.0, FLOOR + XIAO_PCB, XIAO_L - 1.0, XIAO_W / 2 - 1.0,
                    FLOOR + XIAO_PCB + XIAO_TOP))
    zc = usbc_z()
    x = x.union(box(-USBC_OVERHANG, -USBC_W / 2, zc - USBC_H / 2, 3.0, USBC_W / 2, zc + USBC_H / 2))
    a = box(XIAO_L + ANT_GAP, -ANT_W / 2, FLOOR, XIAO_L + ANT_GAP + ANT_L, ANT_W / 2, FLOOR + ANT_T)
    return x.union(a)


def _vol(a, b):
    try:
        return a.intersect(b).val().Volume()
    except Exception:
        return 0.0


def check(parts):
    errs = []
    for name, s in parts.items():
        if not s.val().isValid():
            errs.append(name + ": invalid solid")
        if any(not sh.Closed() for sh in s.val().Shells()):
            errs.append(name + ": open shell")
    env = parts_envelope()
    for name in ("tray", "lid"):
        v = _vol(parts[name], env)
        if v > 0.01:
            errs.append("%s intersects the XIAO or the antenna (%.3f mm3)" % (name, v))
    if _vol(parts["tray"], parts["lid"]) > 0.01:
        errs.append("tray and lid overlap")
    if min(WALL, FLOOR, LID) < 1.2:
        errs.append("wall thinner than 1.2 mm")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args()
    parts = {"tray": tray(), "lid": lid()}
    errs = check(parts)
    bb = parts["tray"].val().BoundingBox()
    print("[dongle] outside %.1f x %.1f x %.1f mm (tab included), %d check error(s)"
          % (bb.xlen, bb.ylen, FLOOR + IN_H + LID, len(errs)))
    for e in errs:
        print("   -", e)
    if not a.check_only:
        os.makedirs(OUT, exist_ok=True)
        for name, s in parts.items():
            cq.exporters.export(s, os.path.join(OUT, name + ".step"))
            pose = s.rotate((0, 0, 0), (1, 0, 0), 180) if name == "lid" else s   # lid: top face on the bed
            b = pose.val().BoundingBox()
            cq.exporters.export(pose.translate((-b.xmin, -b.ymin, -b.zmin)), os.path.join(OUT, name + ".stl"),
                                tolerance=0.02, angularTolerance=0.2)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
