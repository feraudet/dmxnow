"""Generate hardware/dmxnow.kicad_pcb from design.py (KiCad 7+ pcbnew API).

Steps: outline + breakaway slot/tabs + isolation slots, placement, scripted power routing
(230 V and LED power: 🔴 human review mandatory), copper zones, then signal
routing by Freerouting (route.py) and zone fill.

Coordinates below are board-relative millimetres, origin top-left, X right,
Y down. The main (projector) part is X < SPLIT_X, the breakaway strip part X > SPLIT_X.
The 230 V zone has an extra band above Y = 0 (Y from -FUSE_BAND) for the F1 holder.
"""
import os
import sys

import pcbnew

import design
import sch

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, ".."))
PCB = os.path.join(HW, "dmxnow.kicad_pcb")
KICAD_FP = os.environ.get("KICAD_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
LOCAL_LIBS = {"dmxnow": os.path.join(HW, "lib", "dmxnow.pretty"),
              "Espressif": os.path.join(HW, "lib", "Espressif.pretty")}

OX, OY = 50.0, 50.0          # page offset of the board origin
W, H = 146.0, 54.0           # board size (SPEC 4.8.1 updated after placement)
FUSE_BAND = 11.5             # extra height above the 230 V zone only (F1 5x20 holder, 10.8 mm)
BAND_X = 47.5                # right edge of that band
SPLIT_X = 100.0              # breakaway line: routed slot + tabs (ADR 0007, amended)
SPLIT_KEEP = 4.0             # no component within 4 mm of the breakaway line (SPEC 4.8.4)
SLOT_W = 2.0                 # routed slot between the two parts (X 99..101)
TABS = [(6.5, 11.5), (23.0, 29.5), (33.0, 44.0)]   # solid tabs (Y ranges), >= 5 mm (JLCPCB)
BITE_D, BITE_PITCH = 0.5, 0.75   # mouse-bite NPTH holes (JLCPCB: 0.5-0.8 mm, 0.2-0.3 mm apart)
BITE_X = SPLIT_X - SLOT_W / 2 + 0.3   # one row, just inside the main part edge
VIA_D, VIA_DRILL = 0.9, 0.35          # JLCPCB 2 oz: annular ring >= 0.254 mm
PWR_VIA_D, PWR_VIA_DRILL = 1.2, 0.6
# PS1 pin 5 (NC, on the AC pin row), treated as primary: 16-gon keep-out whose sides are
# 7.45 mm from the pin centre = 6 mm + pad radius (1.15) + 0.3 mm margin (DRC rule
# "ps1_nc_pin" in project.py checks the same 6 mm from the pad edge)
NC_KEEPOUT = (68.48, 48.0, 7.6)
MAINS_MAX_X = 46.0           # all 230 V copper at X <= this
LV_MIN_X = 52.0              # all low-voltage copper at X >= this (6 mm)
SLOT_X = 49.0                # 1.2 mm isolation slots centred here
SLOTS = [(12.0, 26.0), (27.5, 52.0)]   # (y start, y end): under K1, under PS1

# ref: (x, y, rotation_deg). Footprint origin = pad 1 for THT parts.
PLACE = {
    # --- 230 V zone 🔴 ---------------------------------------------------
    "J1": (3.8, 5.0, -90),       # L_IN y=5, N y=10 ; wire entry towards -X
    "J4": (3.8, 20.5, -90),      # L_SW y=20.5, N y=25.5
    "J7": (3.8, 36.0, -90),      # L_SW y=36, N y=41
    "K1": (53.0, 15.0, -90),     # coil A1 (53,15) A2 (53,22.5) ; COM x=33 ; NO x=28
    "F1": (13.0, -5.2, 0),       # holder in the top band: pin1 L_IN (13,-5.2), pin2 L_PSU (35.5,-5.2)
    "PS1": (38.0, 48.0, 90),     # AC/L (38,48) AC/N (43.08,48) ; +Vo (63.4,30.22) -Vo (68.48,30.22)
    "RV1": (28.5, 49.5, 90),     # L_PSU (28.5,49.5) ; N (30.13,42) ; 9 mm thick body clear of PS1
    # --- low voltage, main part (X 52..96) -------------------------------
    "U1": (88.0, 8.9, 0),        # ESP32-C3-MINI-1, antenna at the top edge
    "Q1": (59.0, 20.0, 0),
    "R5": (62.5, 17.0, 0),
    "R6": (62.5, 23.5, 0),
    "D2": (58.5, 10.0, 0),
    "U3": (75.5, 21.0, 0),
    "C5": (72.0, 21.0, 90),
    "C6": (79.0, 21.0, 90),
    "C1": (77.5, 17.3, 0),       # 3V3 bulk, as close to U1 pin 3 as the layout allows
    "C10": (67.0, 25.0, 0),      # +5V bulk next to PS1 +Vo / -Vo
    "C2": (79.5, 9.5, 90),
    "R1": (79.5, 13.5, 90),
    "C4": (77.0, 13.5, 90),
    "R4": (77.0, 9.5, 90),
    "R3": (93.5, 20.5, 90),
    "R2": (93.5, 24.0, 90),
    "SW1": (87.5, 24.5, 0),
    "R19": (83.0, 21.0, 90),
    "D4": (83.0, 25.0, 90),
    "J3": (74.0, 30.0, 90),      # 1x6 programming pads, along +X
    "U2": (84.0, 39.0, 0),
    "C3": (84.0, 34.5, 0),
    "D1": (91.5, 40.0, 90),
    "J2": (77.0, 50.5, 0),       # DMX tail wire pads (GND, B, A), >= 6 mm from PS1 pin 5
    "R22": (80.0, 43.5, 90),     # DMX_TX pull-up
    "R23": (95.2, 20.5, 90),     # BOARD_SENSE pull-up (main side)
    "H1": (66.0, 4.5, 0),
    "R15": (94.2, 31.0, 180),    # PWM pull-downs, main side of the breakaway line (SPEC 4.6);
    "R16": (94.2, 33.0, 180),    # GND pad towards the main pour (-X), PWM pad towards the line
    "R17": (94.2, 35.0, 180),
    "R18": (94.2, 37.0, 180),
    "H2": (91.0, 50.0, 0),
    # --- breakaway strip part (X 104..146) -------------------------------
    "J6": (141.5, 30.5, 90),     # VLED y=30.5, CH1..CH4 y=25.5,20.5,15.5,10.5 ; entry towards +X
    "J5": (141.5, 49.0, 90),     # VLED_IN y=49, GND_LED y=44
    "F2": (121.5, 51.5, 180),    # pin1 VLED_IN x 118..121.5, pin2 VLED x 108.7..112.2
    "C7": (116.5, 36.5, 0),      # + (116.5,36.5) - (121.5,36.5)
    "D3": (133.0, 37.0, 180),
    "C8": (140.5, 37.0, 0),
    "Q5": (121.0, 4.5, 0),       # CH4 ; tab (drain) towards +X, gate/source at x=116
    "Q4": (121.0, 12.0, 0),      # CH3
    "Q3": (121.0, 19.5, 0),      # CH2
    "Q2": (121.0, 27.0, 0),      # CH1
    "R10": (111.5, 2.2, 0),      # gate resistors on the gate pad row
    "R14": (111.5, 5.0, 0),      # gate pull-downs
    "R9": (111.5, 9.7, 0),
    "R13": (111.5, 12.5, 0),
    "R8": (111.5, 17.2, 0),
    "R12": (111.5, 20.0, 0),
    "R7": (111.5, 24.7, 0),
    "R11": (111.5, 27.5, 0),
    "U4": (108.5, 37.0, 0),
    "C9": (107.6, 31.0, 0),

    "R20": (111.5, 31.2, 0),     # 0R GND (pad 1) / GND_LED (pad 2 -> via)
    "R21": (105.5, 9.0, 0),      # 0R BOARD_SENSE (pad 1, crossing stub) / GND (pad 2)
    "H3": (139.0, 3.0, 0),
}


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def load_fp(lib_id):
    lib, name = lib_id.split(":", 1)
    vendored = os.path.join(HW, "lib", "vendor", lib + ".pretty")
    default = vendored if os.path.isdir(vendored) else os.path.join(KICAD_FP, lib + ".pretty")
    path = LOCAL_LIBS.get(lib, default)
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit("footprint not found: " + lib_id)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def add_line(board, x1, y1, x2, y2, layer, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pt(x1, y1))
    s.SetEnd(pt(x2, y2))
    s.SetLayer(layer)
    s.SetWidth(mm(width))
    board.Add(s)


def add_arc(board, sx, sy, mx, my, ex, ey, layer, width=0.1):
    a = pcbnew.PCB_SHAPE(board)
    a.SetShape(pcbnew.SHAPE_T_ARC)
    a.SetArcGeometry(pt(sx, sy), pt(mx, my), pt(ex, ey))
    a.SetLayer(layer)
    a.SetWidth(mm(width))
    board.Add(a)


def add_poly_lines(board, pts, layer, width=0.1):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        add_line(board, x1, y1, x2, y2, layer, width)


ANTENNA_KEEPOUT = (79.5, 0.0, SPLIT_X - SLOT_W / 2, 6.5)   # x0, y0, x1, y1


def in_nc_keepout(x, y, r=0.0):
    """True if a circle (x, y, r) reaches a copper keep-out (PS1 NC pin, antenna, board
    edges of the low-voltage area)."""
    cx, cy, rad = NC_KEEPOUT
    if ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 < rad + r + 0.3:
        return True
    edge = 0.5 + r + 0.05       # board setup: copper >= 0.5 mm from Edge.Cuts
    if y < edge or y > H - edge or x > W - edge:
        return True
    x0, y0, x1, y1 = ANTENNA_KEEPOUT
    return x0 - r - 0.3 < x < x1 + r + 0.3 and y < y1 + r + 0.3


def add_rect(board, x1, y1, x2, y2, layer, width=0.1):
    for a, b in (((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))):
        add_line(board, a[0], a[1], b[0], b[1], layer, width)


def add_text(board, txt, x, y, layer, size=1.2, angle=0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt)
    t.SetPosition(pt(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(size * 0.15))
    t.SetTextAngleDegrees(angle)
    board.Add(t)


def add_track(board, net, layer, width, pts):
    n = board.FindNet(net)
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        tr = pcbnew.PCB_TRACK(board)
        tr.SetStart(pt(x1, y1))
        tr.SetEnd(pt(x2, y2))
        tr.SetWidth(mm(width))
        tr.SetLayer(layer)
        tr.SetNet(n)
        board.Add(tr)


def add_via(board, net, x, y, dia=1.2, drill=0.6):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pt(x, y))
    v.SetWidth(mm(dia))
    v.SetDrill(mm(drill))
    v.SetNet(board.FindNet(net))
    board.Add(v)


def add_zone(board, net, layers, poly, clearance=0.3, min_w=0.3, priority=0, solid=False,
             name=""):
    z = pcbnew.ZONE(board)
    ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    if net:
        z.SetNet(board.FindNet(net))
    o = z.Outline()
    o.NewOutline()
    for x, y in poly:
        o.Append(mm(OX + x), mm(OY + y))
    z.SetLocalClearance(mm(clearance))
    z.SetMinThickness(mm(min_w))
    z.SetAssignedPriority(priority)
    # solid="tht_thermal": SMD pads solid, THT pads with wide spokes (2 oz planes are
    # hard to solder otherwise)
    z.SetPadConnection({True: pcbnew.ZONE_CONNECTION_FULL, False: pcbnew.ZONE_CONNECTION_THERMAL,
                        "tht_thermal": pcbnew.ZONE_CONNECTION_THT_THERMAL}[solid])
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetThermalReliefGap(mm(0.5 if solid == "tht_thermal" else 0.4))
    z.SetThermalReliefSpokeWidth(mm(1.2 if solid == "tht_thermal" else 0.5))
    if name:
        z.SetZoneName(name)
    board.Add(z)
    return z


def add_rule_area(board, poly, name, footprints=True, tracks=False, vias=False, pour=False,
                  layers=None):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    ls = pcbnew.LSET()
    for l in layers or [pcbnew.F_Cu, pcbnew.B_Cu]:
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    o = z.Outline()
    o.NewOutline()
    for x, y in poly:
        o.Append(mm(OX + x), mm(OY + y))
    z.SetDoNotAllowFootprints(footprints)
    z.SetDoNotAllowTracks(tracks)
    z.SetDoNotAllowVias(vias)
    z.SetDoNotAllowCopperPour(pour)
    z.SetDoNotAllowPads(False)
    z.SetZoneName(name)
    board.Add(z)


def mouse_bites():
    """NPTH perforation holes along the breakaway line, skipping the crossing tracks."""
    holes = []
    for t0, t1 in TABS:
        y = t0 + 0.45
        while y <= t1 - 0.45:
            if all(abs(y - ty) > tw / 2 + BITE_D / 2 + 0.28 for _, ty, tw in CROSSING_STUBS):   # board hole clearance 0.25
                holes.append((BITE_X, y))
            y += BITE_PITCH
    return holes


def outline(board, for_routing=False):
    E = pcbnew.Edge_Cuts
    x0, x1 = SPLIT_X - SLOT_W / 2, SPLIT_X + SLOT_W / 2
    r = SLOT_W / 2
    (ta0, ta1), (tb0, tb1), (tc0, tc1) = TABS
    # outer contour: 230 V band on top-left, notch from the top edge down to tab A,
    # notch from the bottom edge up to tab C
    add_poly_lines(board, [(0, H), (0, -FUSE_BAND), (BAND_X, -FUSE_BAND), (BAND_X, 0), (x0, 0),
                           (x0, ta0 - r)], E)
    add_arc(board, x0, ta0 - r, SPLIT_X, ta0, x1, ta0 - r, E)
    add_poly_lines(board, [(x1, ta0 - r), (x1, 0), (W, 0), (W, H), (x1, H), (x1, tc1 + r)], E)
    add_arc(board, x1, tc1 + r, SPLIT_X, tc1, x0, tc1 + r, E)
    add_poly_lines(board, [(x0, tc1 + r), (x0, H), (0, H)], E)
    # closed slots between the tabs (stadium shaped)
    for y0, y1 in ((ta1, tb0), (tb1, tc0)):
        add_line(board, x0, y0 + r, x0, y1 - r, E)
        add_arc(board, x0, y1 - r, SPLIT_X, y1, x1, y1 - r, E)
        add_line(board, x1, y1 - r, x1, y0 + r, E)
        add_arc(board, x1, y0 + r, SPLIT_X, y0, x0, y0 + r, E)
    # 1 mm isolation slots (internal cut-outs) 🔴
    for y1, y2 in SLOTS:        # 1.2 mm, round-ended (JLCPCB: no sharp-cornered slots)
        sa, sb, rr = SLOT_X - 0.6, SLOT_X + 0.6, 0.6
        add_line(board, sa, y1 + rr, sa, y2 - rr, E)
        add_arc(board, sa, y2 - rr, SLOT_X, y2, sb, y2 - rr, E)
        add_line(board, sb, y2 - rr, sb, y1 + rr, E)
        add_arc(board, sb, y1 + rr, SLOT_X, y1, sa, y1 + rr, E)
    add_text(board, "CASSER ICI", SPLIT_X - 2.2, 38.5, pcbnew.F_SilkS, 1.0, 90)
    # annotations
    add_text(board, "230V", 8.0, 48.5, pcbnew.F_SilkS, 2.0)
    add_text(board, "F1 T500mA H 250V", 24.25, -10.6, pcbnew.F_SilkS, 1.0)
    # wiring marks (terminals are identical parts)
    add_text(board, "IN L/N", 23.0, 7.3, pcbnew.F_SilkS, 1.0)
    add_text(board, "OUT L/N", 22.5, 23.4, pcbnew.F_SilkS, 1.0)
    add_text(board, "OUT L/N", 22.5, 38.9, pcbnew.F_SilkS, 1.0)
    for x, t in ((77.0, "GND"), (81.2, "B-"), (85.4, "A+")):     # J2 DMX tail
        add_text(board, t, x, 48.3, pcbnew.F_SilkS, 0.9)
    for y, t in ((30.5, "V+"), (25.5, "1"), (20.5, "2"), (15.5, "3"), (10.5, "4")):   # J6
        add_text(board, t, 127.2, y, pcbnew.F_SilkS, 1.0)
    add_line(board, SLOT_X, 1.0, SLOT_X, 11.0, pcbnew.F_SilkS, 0.15)
    add_text(board, "dmxnow v0.3", 88.0, 45.5, pcbnew.F_SilkS, 1.0)
    # J5 polarity (a reversed LED supply short-circuits through D3; only F2 protects)
    add_text(board, "+", 128.8, 49.0, pcbnew.F_SilkS, 1.8)
    add_text(board, "-", 128.8, 44.0, pcbnew.F_SilkS, 1.8)
    add_text(board, "!! 230V - RELECTURE HUMAINE OBLIGATOIRE", 60.0, -4.0, pcbnew.Cmts_User, 1.5)
    # PS1 pin 5 is on the module's AC pin row: treated as primary, no copper around it
    cx, cy, rad = NC_KEEPOUT
    import math
    nc_poly = []
    for k in range(16):
        p = (round(cx + rad * math.cos(k * math.pi / 8), 3), round(min(H, cy + rad * math.sin(k * math.pi / 8)), 3))
        if not nc_poly or p != nc_poly[-1]:
            nc_poly.append(p)
    nc_poly = [p for i, p in enumerate(nc_poly)          # drop collinear points on the edge
               if not (p[1] == H and nc_poly[i - 1][1] == H and nc_poly[(i + 1) % len(nc_poly)][1] == H)]
    add_rule_area(board, nc_poly, "ps1_nc_keepout", footprints=False, tracks=True, vias=True, pour=True)
    if for_routing:
        # Specctra treats any rule area as a routing barrier: for the autorouter
        # the breakaway keep-out is replaced by a routing barrier (only the scripted
        # crossing stubs cross it) and the 230 V zone (+6 mm) is closed.
        add_rule_area(board, [(0, -FUSE_BAND), (LV_MIN_X, -FUSE_BAND), (LV_MIN_X, H), (0, H)],
                      "route_keepout_mains", footprints=False, tracks=True, vias=True, pour=False)
        add_rule_area(board, [(SPLIT_X - 3.0, 0), (SPLIT_X + 3.0, 0), (SPLIT_X + 3.0, H), (SPLIT_X - 3.0, H)],
                      "route_keepout_split", footprints=False, tracks=True, vias=True, pour=False)
        # keep the LED power pours whole: no signal on the bottom layer of the power
        # area (GND_LED pour) nor inside the VLED pour on top
        add_rule_area(board, [(113.4, 0), (W, 0), (W, H), (113.4, H)], "route_keepout_gndled",
                      footprints=False, tracks=True, vias=True, pour=False, layers=[pcbnew.B_Cu])
        add_rule_area(board, VLED_POLY, "route_keepout_vled",
                      footprints=False, tracks=True, vias=True, pour=False, layers=[pcbnew.F_Cu])
    else:
        add_rule_area(board, [(SPLIT_X - SPLIT_KEEP, 0), (SPLIT_X + SPLIT_KEEP, 0), (SPLIT_X + SPLIT_KEEP, H),
                              (SPLIT_X - SPLIT_KEEP, H)], "split_keepout")


def add_npth(board, x, y, d):
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference("MB")
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    fp.SetPosition(pt(x, y))
    fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_BOARD_ONLY)
    pad = pcbnew.PAD(fp)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(pcbnew.VECTOR2I(mm(d), mm(d)))
    pad.SetDrillSize(pcbnew.VECTOR2I(mm(d), mm(d)))
    pad.SetLayerSet(pad.UnplatedHoleMask())
    pad.SetPosition(pt(x, y))
    fp.Add(pad)
    board.Add(fp)


def place(board):
    root = sch.uid("root")
    for p in design.PARTS:
        fp = load_fp(p.footprint)
        fp.SetReference(p.ref)
        fp.SetValue(p.value)
        x, y, rot = PLACE[p.ref]
        fp.SetPosition(pt(x, y))
        fp.SetOrientationDegrees(rot)
        units = sch.units_of(p) if not p.symbol.startswith("Mechanical:") else [1]
        fp.SetPath(pcbnew.KIID_PATH("/" + str(sch.uid("sym", p.ref, units[0]))))
        attrs = fp.GetAttributes()
        if p.dnp and not p.variant:
            attrs |= pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES
        elif p.dnp:
            attrs |= pcbnew.FP_EXCLUDE_FROM_BOM   # option part: kept in the placement file
        if p.symbol.startswith("Mechanical:"):
            attrs |= pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_BOARD_ONLY
        fp.SetAttributes(attrs)
        for k, v in (("MPN", p.mpn), ("LCSC", p.lcsc), ("Section", p.section)):
            if v:
                fp.SetProperty(k, v)
        for g in fp.GraphicalItems():     # JLCPCB legend: lines >= 0.15 mm
            if g.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS) and hasattr(g, "GetWidth") \
                    and 0 < g.GetWidth() < mm(0.15):
                g.SetWidth(mm(0.15))
        for pad in fp.Pads():
            net = p.pins.get(pad.GetNumber())
            if net:
                pad.SetNet(board.FindNet(net))
        board.Add(fp)


# --------------------------------------------------------------------------
# Scripted power routing 🔴 (230 V) and LED power
# Each entry: (net, layer, width, [(x, y), ...])
# --------------------------------------------------------------------------
F, B = pcbnew.F_Cu, pcbnew.B_Cu

MAINS_ROUTES = [
    # L_IN: J1 pin 1 -> relay COM (x=33) and, up into the top band, F1 pin 1. Both layers.
    ("L_IN", F, 1.9, [(3.8, 5.0), (12.0, 5.0)]),
    ("L_IN", B, 1.9, [(3.8, 5.0), (12.0, 5.0)]),
    ("L_IN", F, 4.0, [(12.0, 3.0), (37.15, 3.0)]),
    ("L_IN", B, 4.0, [(12.0, 3.0), (37.15, 3.0)]),
    ("L_IN", F, 1.9, [(12.0, 5.0), (12.0, 3.0)]),
    ("L_IN", B, 1.9, [(12.0, 5.0), (12.0, 3.0)]),
    ("L_IN", F, 4.3, [(37.15, 3.2), (37.15, 22.5)]),
    ("L_IN", B, 4.3, [(37.15, 3.2), (37.15, 22.5)]),
    ("L_IN", F, 2.6, [(34.6, 15.0), (37.15, 15.0)]),
    ("L_IN", B, 2.6, [(34.6, 15.0), (37.15, 15.0)]),
    ("L_IN", F, 2.6, [(34.6, 22.5), (37.15, 22.5)]),
    ("L_IN", B, 2.6, [(34.6, 22.5), (37.15, 22.5)]),
    ("L_IN", F, 2.5, [(13.0, -5.2), (13.0, 3.0)]),
    ("L_IN", B, 2.5, [(13.0, -5.2), (13.0, 3.0)]),
    # L_SW: J4 pin 1 and J7 pin 1 -> relay NO bus (x=25). 7.4 mm fingers on top (they
    # cross the N bus, which is on the bottom), 3.1 mm from the N pads of the terminals.
    ("L_SW", F, 1.9, [(3.8, 20.5), (12.0, 20.5)]),
    ("L_SW", F, 7.4, [(7.5, 17.75), (25.0, 17.75)]),
    ("L_SW", F, 1.9, [(3.8, 36.0), (12.0, 36.0)]),
    ("L_SW", F, 7.4, [(7.5, 33.25), (25.0, 33.25)]),
    ("L_SW", F, 7.0, [(25.0, 15.0), (25.0, 34.0)]),      # the J7 finger continues it down
    ("L_SW", F, 2.6, [(25.0, 15.0), (27.0, 15.0)]),     # ends at the NO pads (3 mm from COM)
    ("L_SW", F, 2.6, [(25.0, 22.5), (27.0, 22.5)]),
    # N: J1/J4/J7 pin 2 -> 7.1 mm vertical bus on the bottom layer (x 16.5..23.6).
    ("N", B, 1.9, [(3.8, 10.0), (12.0, 10.0)]),
    ("N", B, 1.9, [(3.8, 25.5), (12.0, 25.5)]),
    ("N", B, 1.9, [(3.8, 41.0), (12.0, 41.0)]),
    ("N", B, 3.4, [(12.0, 10.75), (20.05, 10.75)]),
    ("N", B, 4.0, [(12.0, 26.5), (20.05, 26.5)]),
    ("N", B, 4.0, [(12.0, 42.0), (20.05, 42.0)]),
    ("N", B, 7.1, [(20.05, 12.3), (20.05, 42.0)]),
    # N branch to RV1 and PS1 AC/N (internal supply only, fused by F1 on the L side)
    ("N", B, 1.0, [(18.5, 43.3), (30.13, 43.3), (43.08, 43.3), (43.08, 48.0)]),
    ("N", B, 1.0, [(30.13, 43.3), (30.13, 42.0)]),
    # L_PSU: F1 pin 2 (top band) -> PS1 AC/L, branch to RV1 pin 1
    ("L_PSU", F, 1.0, [(35.5, -5.2), (43.5, -5.2), (43.5, 27.0), (38.0, 32.5), (38.0, 48.0)]),
    ("L_PSU", F, 1.0, [(38.0, 46.0), (28.5, 49.5)]),
]

LED_ROUTES = [
    # VLED_IN: J5 pin 1 (front 141.5 / back 133.3, y=49) -> F2 pin 1 (x 118..121.5, y 49..51.5)
    ("VLED_IN", F, 1.9, [(141.5, 49.0), (133.3, 49.0)]),
    ("VLED_IN", B, 1.9, [(141.5, 49.0), (133.3, 49.0)]),
    ("VLED_IN", F, 4.5, [(133.3, 49.75), (121.5, 49.75)]),
    # GND_LED: J5 pin 2 front/back pins (the rest is the bottom-layer pour)
    ("GND_LED", B, 1.9, [(141.5, 44.0), (133.3, 44.0)]),
    # Channels: drain tab -> J6 back pin (6 A per channel -> 2.5 mm)
    ("CH4", F, 2.5, [(122.3, 4.5), (126.5, 4.5), (132.5, 10.5), (141.5, 10.5)]),
    ("CH3", F, 2.5, [(122.3, 12.0), (126.5, 12.0), (130.0, 15.5), (141.5, 15.5)]),
    ("CH2", F, 2.5, [(122.3, 19.5), (126.5, 19.5), (127.5, 20.5), (141.5, 20.5)]),
    ("CH1", F, 2.5, [(122.3, 27.0), (126.5, 27.0), (128.0, 25.5), (141.5, 25.5)]),
]

R21_PAD1_X = 105.5 - 0.825   # R_0603: pads at +-0.825 mm
R20_PAD2_X = 111.5 + 0.95    # R_0805: pads at +-0.95 mm

# The only copper crossing the breakaway line (SPEC 4.8.4): short fixed stubs over the
# tabs, the autorouter connects to their ends. (net, y, width)
CROSSING_STUBS = [("BOARD_SENSE", 9.0, 0.25), ("+5V", 24.0, 0.6), ("PWM4", 26.0, 0.25),
                  ("GND", 28.5, 0.6), ("PWM1", 34.46, 0.25), ("PWM2", 38.27, 0.25),
                  ("PWM3", 42.6, 0.25)]
STUB_X0, STUB_X1 = SPLIT_X - 3.8, SPLIT_X + 3.8   # stub ends just outside the router barrier
LED_ROUTES += [(n, F, w, [(STUB_X0, y), (STUB_X1, y)]) for n, y, w in CROSSING_STUBS]
# BOARD_SENSE stub straight onto NT2 pad 1; NT1 GND_LED pad to a via into the GND_LED pour
LED_ROUTES += [("BOARD_SENSE", F, 0.25, [(STUB_X1, 9.0), (R21_PAD1_X, 9.0)]),
               ("GND_LED", F, 0.4, [(R20_PAD2_X, 31.2), (114.0, 27.0 + 2.28 + 1.4)])]   # Q2 source via
# Gate pull-downs R11..R14 (pad 2) to the GND_LED via next to each MOSFET source
LED_ROUTES += [("GND_LED", F, 0.4, [(112.275, y + 0.5), (114.0, y + 2.28 - 0.7)])
               for y in (4.5, 12.0, 19.5, 27.0)]
# F2 pin 1 is four pads (two per blade): tie them together
LED_ROUTES += [("VLED_IN", F, 2.0, [(118.0, 49.0), (121.5, 49.0)]),
               ("VLED_IN", F, 2.0, [(118.0, 51.5), (121.5, 51.5)]),
               ("VLED_IN", F, 1.5, [(118.0, 49.0), (118.0, 51.5)])]
# U4 output-enable pins (1, 4, 10, 13) to GND through their own vias (bottom pour)
U4_X, U4_Y = 108.5, 37.0
U4_OE = [(U4_X - 2.475, U4_Y - 3.81), (U4_X - 2.475, U4_Y - 3.81 + 3 * 1.27),
         (U4_X + 2.475, U4_Y + 3.81 - 2 * 1.27), (U4_X + 2.475, U4_Y + 3.81 - 5 * 1.27)]
# OE pins: vias under the package body to the bottom GND pour (the autorouter is
# kept off the bottom layer under U4 so that this pour stays whole).
U4_OE_VIAS = [(x + 1.7, y) if x < U4_X else (x - 1.7, y) for x, y in U4_OE]   # >= 0.25 mm from pads
LED_ROUTES += [("GND", F, 0.3, [a, b]) for a, b in zip(U4_OE, U4_OE_VIAS)]
# D4 (LED option) cathode to its own via
LED_ROUTES += [("GND", F, 0.3, [(83.0, 25.79), (83.0, 27.2)])]
# GND crossing stub: vias at both ends so the main and strip pours are joined on both layers
# R20 pad 1 (star point) to its own via, next to the pad (no via in pad: solder wicking)
LED_ROUTES += [("GND", F, 0.4, [(111.5 - 0.9125, 31.2), (110.55, 29.75)])]
GND_VIAS = [(STUB_X0, 28.5), (STUB_X1, 28.5),
            (110.55, 29.75),                             # R20 pad 1 (star point)
            (83.0, 27.2)] + U4_OE_VIAS                   # D4 cathode, U4 OE pins
# U1 GND pads 52 (corner) and 11 (left column) tied on top, next to the module edge
LED_ROUTES += [("GND", F, 0.3, [(82.05, 16.55), (82.1, 15.6)])]
# PWM pull-downs R15-R18: their GND pads (x=93.375) tied by a spine, so that routed PWM
# tracks cannot strand one of them
LED_ROUTES += [("GND", F, 0.4, [(93.375, 31.0), (93.375, 37.0)])]
# U3 (AP2112K) GND pin is boxed in by pins 1 and 3: tie it to C5 pin 2 directly
LED_ROUTES += [("GND", F, 0.3, [(74.36, 21.0), (73.2, 21.0), (72.0, 20.225)])]
# D3 anode and C8 pin 2 to the GND_LED pour (bottom)
LED_ROUTES += [("GND_LED", F, 1.0, [(130.85, 37.0), (130.85, 39.6)]),
               ("GND_LED", F, 1.0, [(141.9, 37.0), (141.9, 39.6)])]
# VLED: F2 pin 2 -> C7 + (keeps the VLED pour in one piece whatever the autorouter does)
LED_ROUTES += [("VLED", F, 3.0, [(108.7, 49.0), (112.2, 49.0)]),
               ("VLED", F, 3.0, [(110.45, 49.0), (110.45, 45.5), (114.5, 41.5), (116.5, 38.5), (116.5, 36.5)])]

# MOSFET sources and other GND_LED pads to the bottom pour: 3 x 0.6 mm vias per source
Q_Y = (4.5, 12.0, 19.5, 27.0)
GND_LED_VIAS = [(114.0, y + 2.28 + dy) for y in Q_Y for dy in (-1.4, 0.0, 1.4)] + \
    [(130.85, 39.6), (141.9, 39.6)]
LED_ROUTES += [("GND_LED", F, 1.4, [(115.96, y + 2.28), (114.0, y + 2.28)]) for y in Q_Y]
LED_ROUTES += [("GND_LED", F, 1.2, [(114.0, y + 0.88), (114.0, y + 3.68)]) for y in Q_Y]



def route_power(board):
    for net, layer, w, pts in MAINS_ROUTES + LED_ROUTES:
        add_track(board, net, layer, w, pts)
    for x, y in GND_LED_VIAS:
        add_via(board, "GND_LED", x, y, PWR_VIA_D, PWR_VIA_DRILL)
    for x, y in GND_VIAS:
        add_via(board, "GND", x, y, VIA_D, VIA_DRILL)


def _box_dist(x, y, b):
    return (max(b[0] - x, 0, x - b[2]) ** 2 + max(b[1] - y, 0, y - b[3]) ** 2) ** 0.5


def _seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L))
    return ((px - x1 - t * dx) ** 2 + (py - y1 - t * dy) ** 2) ** 0.5


# Every logic-GND SMD pad gets its own via before routing (the autorouter is not
# deterministic and strands a different pad on each run); for U1 only these:
GND_PAD_VIAS = {("C2", "2"), ("C5", "2"), ("U3", "2"), ("SW1", "2"), ("C3", "2"), ("U2", "5"),
                ("U1", "51"), ("C4", "2"), ("C6", "2"), ("R15", "2"), ("R18", "2"), ("C9", "2"),
                ("U1", "11"), ("U1", "14")}


def gnd_pad_vias(board):
    """Before routing, give the GND SMD pads listed in GND_PAD_VIAS their own via to the bottom pour
    (short 0.4 mm track, never in the pad): the pad no longer depends on a sliver of
    top-layer pour between the routed tracks."""
    tm = pcbnew.ToMM
    pads = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            pads.append(((tm(bb.GetLeft()) - OX, tm(bb.GetTop()) - OY, tm(bb.GetRight()) - OX,
                          tm(bb.GetBottom()) - OY), pad.GetNetname(), pad))
    segs = [(tm(t.GetStart().x) - OX, tm(t.GetStart().y) - OY, tm(t.GetEnd().x) - OX,
             tm(t.GetEnd().y) - OY, tm(t.GetWidth()) / 2, t.GetNetname())
            for t in board.GetTracks() if not isinstance(t, pcbnew.PCB_VIA)]
    vias = [(tm(t.GetPosition().x) - OX, tm(t.GetPosition().y) - OY, tm(t.GetWidth()) / 2)
            for t in board.GetTracks() if isinstance(t, pcbnew.PCB_VIA)]
    r = VIA_D / 2
    n = 0
    for box, net, pad in pads:
        if net != "GND" or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
            continue
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        if pad.GetParent().GetReference() == "U1" and (pad.GetParent().GetReference(), pad.GetNumber()) \
                not in GND_PAD_VIAS:
            continue      # module GND pads: the listed ones only (the others are under the module)
        half = max(box[2] - box[0], box[3] - box[1]) / 2
        done = False
        for dist in (half + 0.75, half + 1.1, half + 1.5, half + 2.0, half + 2.5):
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0), (0.707, 0.707), (-0.707, 0.707),
                           (0.707, -0.707), (-0.707, -0.707)):
                x, y = cx + dx * dist, cy + dy * dist
                in_lv = LV_MIN_X + 0.8 < x < SPLIT_X - SPLIT_KEEP - 0.2 and 0.9 < y < H - 0.9
                in_strip = SPLIT_X + SPLIT_KEEP + 0.2 < x < 112.6 and 0.9 < y < 43.6
                if not (in_lv or in_strip) or in_nc_keepout(x, y, r):
                    continue
                ok = all(_box_dist(x, y, b) > r + (0.15 if (nn == net and p is not pad) else 0.35)
                         for b, nn, p in pads if p is not pad)
                ok = ok and _box_dist(x, y, box) > r + 0.1
                ok = ok and all(_seg_dist(x, y, *sg[:4]) > r + sg[4] + 0.3 for sg in segs if sg[5] != net)
                ok = ok and all(((x - vx) ** 2 + (y - vy) ** 2) ** 0.5 > r + vr + 0.3 for vx, vy, vr in vias)
                # the 0.4 mm link from the pad centre to the via must clear foreign pads
                ok = ok and all(min(_box_dist(cx + (x - cx) * k / 10, cy + (y - cy) * k / 10, b)
                                    for k in range(11)) > 0.2 + 0.2
                                for b, nn, p in pads if nn != net)
                if ok:
                    add_track(board, net, F, 0.4, [(cx, cy), (x, y)])
                    add_via(board, net, x, y, VIA_D, VIA_DRILL)
                    vias.append((x, y, r))
                    segs.append((cx, cy, x, y, 0.2, net))
                    n += 1
                    done = True
                    break
            if done:
                break
    return n


VLED_POLY = [(104.5, 53.5), (116.3, 53.5), (116.3, 47.1), (127.0, 47.1), (127.0, 41.9),
             (145.5, 41.9), (145.5, 28.6), (128.0, 28.6), (125.0, 31.0), (125.0, 32.5), (114.0, 32.5),
             (114.0, 44.8), (104.5, 44.8)]


def zones(board):
    # Low-voltage ground, both layers, main part only (no ground plane in the 230 V zone)
    lv = [(LV_MIN_X, 0.5), (SPLIT_X - SLOT_W / 2 - 0.7, 0.5), (SPLIT_X - SLOT_W / 2 - 0.7, H - 0.5),
          (LV_MIN_X, H - 0.5)]
    add_zone(board, "GND", [F, B], lv, clearance=0.3, name="GND_LV")
    # ESP32-C3 antenna: no copper at all around it, up to the breakaway slot (Espressif HW guidelines)
    x0, y0, x1, y1 = ANTENNA_KEEPOUT
    add_rule_area(board, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                  "antenna_keepout", footprints=False, tracks=True, vias=True, pour=True)
    # LED return on the strip part, bottom layer
    strip = [(113.4, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (113.4, H - 0.3)]
    add_zone(board, "GND_LED", [B], strip, clearance=0.4, name="GND_LED", solid="tht_thermal")
    # VLED on the top layer: F2 pin 2 -> C7 / D3 / C8 -> J6 pin 1 (17 A path)
    add_zone(board, "VLED", [F], VLED_POLY, clearance=0.4, name="VLED", solid="tht_thermal", priority=1)
    # Logic ground of the strip part (U4, pull-downs, net ties), top layer only
    logic = [(SPLIT_X + SLOT_W / 2 + 0.7, 0.5), (113.2, 0.5), (113.2, 44.3), (SPLIT_X + SLOT_W / 2 + 0.7, 44.3)]
    add_zone(board, "GND", [F, B], logic, clearance=0.3, name="GND_STRIP", priority=2)


def build(for_routing=False):
    # NewBoard() writes an empty board at the given path: never point it at the real
    # board file when building the routing variant.
    path = os.path.join(HW, "build", "route", "routing_variant.kicad_pcb") if for_routing else PCB
    os.makedirs(os.path.dirname(path), exist_ok=True)
    board = pcbnew.NewBoard(path)
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.SetBoardThickness(mm(1.6))
    ds.SetAuxOrigin(pt(0, H))      # fab outputs use the bottom-left board corner as origin
    nc = ds.m_NetSettings.m_DefaultNetClass   # autorouter vias (JLCPCB 2 oz annular ring)
    nc.SetViaDiameter(mm(VIA_D))
    nc.SetViaDrill(mm(VIA_DRILL))
    for n in design.nets():
        board.Add(pcbnew.NETINFO_ITEM(board, n))
    outline(board, for_routing)
    place(board)
    route_power(board)
    gnd_pad_vias(board)
    if not for_routing:   # the Specctra exporter rejects these board-only NPTH holes
        for x, y in mouse_bites():
            add_npth(board, x, y, BITE_D)
    zones(board)
    tb = board.GetTitleBlock()
    tb.SetTitle("dmxnow - noeud DMX / relais / rubans LED")
    tb.SetRevision("0.3")
    tb.SetComment(0, "Généré par hardware/gen/pcb.py - ne pas éditer à la main")
    tb.SetComment(1, "Zone 230 V : RELECTURE HUMAINE OBLIGATOIRE")
    tb.SetComment(2, "K1, PS1, WAGO 2604 : cotes vérifiées sur fiches (relecture humaine)")
    return board


if __name__ == "__main__":
    if "--dsn" in sys.argv:
        # routing variant, exported to Specctra DSN for route.py (board file untouched)
        b = build(for_routing=True)
        for t in b.GetTracks():
            t.SetLocked(True)
        dsn = sys.argv[sys.argv.index("--dsn") + 1]
        if not pcbnew.ExportSpecctraDSN(b, dsn):
            raise SystemExit("DSN export failed")
        print("exported", dsn)
    else:
        b = build()
        b.Save(PCB)
        print("written", PCB)
