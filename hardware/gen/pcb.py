"""Generate hardware/dmxnow.kicad_pcb from design.py (KiCad 7+ pcbnew API).

Steps: outline + V-cut + isolation slots, placement, scripted power routing
(230 V and LED power: 🔴 human review mandatory), copper zones, then signal
routing by Freerouting (route.py) and zone fill.

Coordinates below are board-relative millimetres, origin top-left, X right,
Y down. The main (projector) part is X < VCUT, the breakaway strip part X > VCUT.
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
VCUT = 100.0                 # V-cut X position
VCUT_KEEP = 4.0              # no component within 4 mm of the V-cut (SPEC 4.8.4)
MAINS_MAX_X = 46.0           # all 230 V copper at X <= this
LV_MIN_X = 52.0              # all low-voltage copper at X >= this (6 mm)
SLOT_X = 49.0                # 1 mm isolation slots centred here
SLOTS = [(12.0, 26.0), (27.5, 52.0)]   # (y start, y end): under K1, under PS1

# ref: (x, y, rotation_deg). Footprint origin = pad 1 for THT parts.
PLACE = {
    # --- 230 V zone 🔴 ---------------------------------------------------
    "J1": (4.5, 5.0, -90),       # L_IN y=5, N y=10 ; wire entry towards -X
    "J4": (4.5, 20.5, -90),      # L_SW y=20.5, N y=25.5
    "J7": (4.5, 36.0, -90),      # L_SW y=36, N y=41
    "K1": (53.0, 15.0, -90),     # coil A1 (53,15) A2 (53,22.5) ; COM x=33 ; NO x=28
    "F1": (43.5, 3.5, -90),      # pin1 L_IN (43.5,3.5), pin2 L_PSU (43.5,8.58)
    "PS1": (38.0, 48.0, 90),     # AC/L (38,48) AC/N (43.08,48) ; +Vo (63.4,30.22) -Vo (68.48,30.22)
    "RV1": (31.0, 49.5, 90),     # L_PSU (31,49.5) ; N (32.63,42)
    # --- low voltage, main part (X 52..96) -------------------------------
    "U1": (88.0, 8.9, 0),        # ESP32-C3-MINI-1, antenna at the top edge
    "Q1": (59.0, 20.0, 0),
    "R5": (62.5, 17.0, 0),
    "R6": (62.5, 23.5, 0),
    "D2": (58.5, 10.0, 0),
    "U3": (75.5, 21.0, 0),
    "C5": (72.0, 21.0, 90),
    "C6": (79.0, 21.0, 90),
    "C1": (77.0, 25.0, 0),
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
    "J2": (76.0, 50.5, 0),       # DMX tail wire pads (GND, B, A)
    "H1": (66.0, 4.5, 0),
    "R15": (94.2, 31.0, 180),    # PWM pull-downs, main side of the V-cut (SPEC 4.6);
    "R16": (94.2, 33.0, 180),    # GND pad towards the main pour (-X), PWM pad towards the V-cut
    "R17": (94.2, 35.0, 180),
    "R18": (94.2, 37.0, 180),
    "H2": (91.0, 50.0, 0),
    # --- breakaway strip part (X 104..146) -------------------------------
    "J6": (141.5, 30.0, 90),     # VLED y=30, CH1..CH4 y=25,20,15,10 ; entry towards +X
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
    "H3": (139.0, 3.5, 0),
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
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if solid else pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetThermalReliefGap(mm(0.4))
    z.SetThermalReliefSpokeWidth(mm(0.5))
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


def outline(board, for_routing=False):
    add_rect(board, 0, 0, W, H, pcbnew.Edge_Cuts, 0.1)
    # 1 mm isolation slots (internal cut-outs) 🔴
    for y1, y2 in SLOTS:
        add_rect(board, SLOT_X - 0.5, y1, SLOT_X + 0.5, y2, pcbnew.Edge_Cuts, 0.1)
    # V-cut line on User.1 (exported as its own Gerber, see fab.py)
    add_line(board, VCUT, -3, VCUT, H + 3, pcbnew.User_1, 0.2)
    add_text(board, "V-CUT", VCUT, -4.5, pcbnew.User_1, 1.5)
    add_text(board, "V-CUT", VCUT + 1.2, H / 2, pcbnew.F_SilkS, 1.0, 90)
    # annotations
    add_text(board, "230V", 12.0, 48.5, pcbnew.F_SilkS, 2.0)
    add_line(board, SLOT_X, 1.0, SLOT_X, 11.0, pcbnew.F_SilkS, 0.15)
    add_text(board, "dmxnow v0.1", 88.0, 45.5, pcbnew.F_SilkS, 1.0)
    add_text(board, "!! 230V - RELECTURE HUMAINE OBLIGATOIRE", 24.0, -4.0, pcbnew.Cmts_User, 1.5)
    # no component within 4 mm of the V-cut; tracks allowed (crossing nets)
    if for_routing:
        # Specctra treats any rule area as a routing barrier: for the autorouter
        # the V-cut keep-out is replaced by a routing barrier (only the scripted
        # crossing stubs cross it) and the 230 V zone (+6 mm) is closed.
        add_rule_area(board, [(0, 0), (LV_MIN_X, 0), (LV_MIN_X, H), (0, H)],
                      "route_keepout_mains", footprints=False, tracks=True, vias=True, pour=False)
        add_rule_area(board, [(VCUT - 3.0, 0), (VCUT + 3.0, 0), (VCUT + 3.0, H), (VCUT - 3.0, H)],
                      "route_keepout_vcut", footprints=False, tracks=True, vias=True, pour=False)
        # keep the LED power pours whole: no signal on the bottom layer of the power
        # area (GND_LED pour) nor inside the VLED pour on top
        add_rule_area(board, [(113.4, 0), (W, 0), (W, H), (113.4, H)], "route_keepout_gndled",
                      footprints=False, tracks=True, vias=True, pour=False, layers=[pcbnew.B_Cu])
        add_rule_area(board, [(106.3, 32.3), (110.7, 32.3), (110.7, 41.7), (106.3, 41.7)],
                      "route_keepout_u4_bottom", footprints=False, tracks=True, vias=True,
                      pour=False, layers=[pcbnew.B_Cu])
        add_rule_area(board, VLED_POLY, "route_keepout_vled",
                      footprints=False, tracks=True, vias=True, pour=False, layers=[pcbnew.F_Cu])
    else:
        add_rule_area(board, [(VCUT - VCUT_KEEP, 0), (VCUT + VCUT_KEEP, 0), (VCUT + VCUT_KEEP, H),
                              (VCUT - VCUT_KEEP, H)], "vcut_keepout")


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
    # L_IN: J1 pin 1 -> relay COM (x=33) and F1 pin 1. Both layers, above the L_SW bus.
    ("L_IN", F, 1.9, [(4.5, 5.0), (10.5, 5.0)]),
    ("L_IN", B, 1.9, [(4.5, 5.0), (10.5, 5.0)]),
    ("L_IN", F, 4.0, [(10.5, 3.0), (37.15, 3.0)]),
    ("L_IN", B, 4.0, [(10.5, 3.0), (37.15, 3.0)]),
    ("L_IN", F, 1.9, [(10.5, 5.0), (10.5, 3.0)]),
    ("L_IN", B, 1.9, [(10.5, 5.0), (10.5, 3.0)]),
    ("L_IN", F, 4.3, [(37.15, 3.2), (37.15, 22.5)]),
    ("L_IN", B, 4.3, [(37.15, 3.2), (37.15, 22.5)]),
    ("L_IN", F, 2.6, [(34.6, 15.0), (37.15, 15.0)]),
    ("L_IN", B, 2.6, [(34.6, 15.0), (37.15, 15.0)]),
    ("L_IN", F, 2.6, [(34.6, 22.5), (37.15, 22.5)]),
    ("L_IN", B, 2.6, [(34.6, 22.5), (37.15, 22.5)]),
    ("L_IN", F, 2.0, [(37.15, 3.5), (43.5, 3.5)]),
    # L_SW: J4 pin 1 and J7 pin 1 -> relay NO bus (x=26). Fingers on top (cross the N bus).
    ("L_SW", F, 1.9, [(4.5, 20.5), (10.5, 20.5)]),
    ("L_SW", F, 3.5, [(10.5, 19.75), (26.0, 19.75)]),
    ("L_SW", F, 1.9, [(4.5, 36.0), (10.5, 36.0)]),
    ("L_SW", F, 3.5, [(10.5, 35.25), (26.0, 35.25)]),
    ("L_SW", F, 5.0, [(26.0, 15.0), (26.0, 37.0)]),
    ("L_SW", B, 5.0, [(26.0, 15.0), (26.0, 22.5)]),
    ("L_SW", F, 2.6, [(26.0, 15.0), (27.0, 15.0)]),
    ("L_SW", B, 2.6, [(26.0, 15.0), (27.0, 15.0)]),
    ("L_SW", F, 2.6, [(26.0, 22.5), (27.0, 22.5)]),
    ("L_SW", B, 2.6, [(26.0, 22.5), (27.0, 22.5)]),
    # N: J1/J4/J7 pin 2 -> vertical bus on the bottom layer at x=18.5.
    ("N", B, 1.9, [(4.5, 10.0), (10.5, 10.0)]),
    ("N", B, 1.9, [(4.5, 25.5), (10.5, 25.5)]),
    ("N", B, 1.9, [(4.5, 41.0), (10.5, 41.0)]),
    ("N", B, 3.6, [(10.5, 10.75), (18.5, 10.75)]),
    ("N", B, 4.0, [(10.5, 26.5), (18.5, 26.5)]),
    ("N", B, 4.0, [(10.5, 42.0), (18.5, 42.0)]),
    ("N", B, 3.8, [(18.5, 10.75), (18.5, 42.0)]),
    # N branch to RV1 and PS1 AC/N (internal supply only, fused by F1 on the L side)
    ("N", B, 1.0, [(18.5, 43.3), (32.63, 43.3), (43.08, 43.3), (43.08, 48.0)]),
    ("N", B, 1.0, [(32.63, 43.3), (32.63, 42.0)]),
    # L_PSU: F1 pin 2 -> PS1 AC/L, branch to RV1 pin 1
    ("L_PSU", F, 1.0, [(43.5, 8.58), (43.5, 27.0), (38.0, 32.5), (38.0, 48.0)]),
    ("L_PSU", F, 1.0, [(38.0, 46.0), (31.0, 49.5)]),
]

LED_ROUTES = [
    # VLED_IN: J5 pin 1 (front 141.5 / back 135.5, y=49) -> F2 pin 1 (x 118..121.5, y 49..51.5)
    ("VLED_IN", F, 1.9, [(141.5, 49.0), (135.5, 49.0)]),
    ("VLED_IN", B, 1.9, [(141.5, 49.0), (135.5, 49.0)]),
    ("VLED_IN", F, 4.5, [(135.5, 49.75), (121.5, 49.75)]),
    # GND_LED: J5 pin 2 front/back pins (the rest is the bottom-layer pour)
    ("GND_LED", B, 1.9, [(141.5, 44.0), (135.5, 44.0)]),
    # Channels: drain tab -> J6 back pin (6 A per channel -> 2.5 mm)
    ("CH4", F, 2.5, [(122.3, 4.5), (126.5, 4.5), (132.0, 10.0), (141.5, 10.0)]),
    ("CH3", F, 2.5, [(122.3, 12.0), (126.5, 12.0), (129.5, 15.0), (141.5, 15.0)]),
    ("CH2", F, 2.5, [(122.3, 19.5), (126.5, 19.5), (127.0, 20.0), (141.5, 20.0)]),
    ("CH1", F, 2.5, [(122.3, 27.0), (126.5, 27.0), (128.5, 25.0), (141.5, 25.0)]),
]

R21_PAD1_X = 105.5 - 0.825   # R_0603: pads at +-0.825 mm
R20_PAD2_X = 111.5 + 0.95    # R_0805: pads at +-0.95 mm

# The only copper crossing the V-cut (SPEC 4.8.4): short fixed stubs, the
# autorouter connects to their ends. (net, y, width)
CROSSING_STUBS = [("BOARD_SENSE", 9.0, 0.25), ("+5V", 24.0, 0.6), ("PWM4", 26.0, 0.25),
                  ("GND", 28.5, 0.6), ("PWM1", 34.46, 0.25), ("PWM2", 38.27, 0.25),
                  ("PWM3", 42.6, 0.25)]
STUB_X0, STUB_X1 = VCUT - 3.8, VCUT + 3.8   # stub ends just outside the router barrier
LED_ROUTES += [(n, F, w, [(STUB_X0, y), (STUB_X1, y)]) for n, y, w in CROSSING_STUBS]
# BOARD_SENSE stub straight onto NT2 pad 1; NT1 GND_LED pad to a via into the GND_LED pour
LED_ROUTES += [("BOARD_SENSE", F, 0.25, [(STUB_X1, 9.0), (R21_PAD1_X, 9.0)]),
               ("GND_LED", F, 0.4, [(R20_PAD2_X, 31.2), (114.0, 31.5)])]
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
U4_OE_VIAS = [(x + 1.5, y) if x < U4_X else (x - 1.5, y) for x, y in U4_OE]
LED_ROUTES += [("GND", F, 0.3, [a, b]) for a, b in zip(U4_OE, U4_OE_VIAS)]
# D4 (LED option) cathode to its own via
LED_ROUTES += [("GND", F, 0.3, [(83.0, 25.79), (83.0, 27.2)])]
# GND crossing stub: vias at both ends so the main and strip pours are joined on both layers
GND_VIAS = [(STUB_X0, 28.5), (STUB_X1, 28.5),
            (111.5 - 0.9125, 31.2),                      # R20 pad 1 (star point): via in pad
            (83.0, 27.2)] + U4_OE_VIAS                   # D4 cathode, U4 OE pins
# U3 (AP2112K) GND pin is boxed in by pins 1 and 3: tie it to C5 pin 2 directly
LED_ROUTES += [("GND", F, 0.3, [(74.36, 21.0), (73.2, 21.0), (72.0, 20.225)])]
# D3 anode and C8 pin 2 to the GND_LED pour (bottom)
LED_ROUTES += [("GND_LED", F, 1.0, [(130.85, 37.0), (130.85, 39.6)]),
               ("GND_LED", F, 1.0, [(141.9, 37.0), (141.9, 39.6)])]
# VLED: F2 pin 2 -> C7 + (keeps the VLED pour in one piece whatever the autorouter does)
LED_ROUTES += [("VLED", F, 3.0, [(108.7, 49.0), (112.2, 49.0)]),
               ("VLED", F, 3.0, [(110.45, 49.0), (110.45, 45.5), (114.5, 41.5), (116.5, 38.5), (116.5, 36.5)])]

# MOSFET sources and other GND_LED pads to the bottom pour: via arrays
Q_Y = (4.5, 12.0, 19.5, 27.0)
GND_LED_VIAS = [(114.0, y + 2.28 + dy) for y in Q_Y for dy in (-0.7, 0.7)] + \
    [(114.0, 31.5), (130.85, 39.6), (141.9, 39.6)]
LED_ROUTES += [("GND_LED", F, 1.4, [(115.96, y + 2.28), (114.0, y + 2.28)]) for y in Q_Y]



def route_power(board):
    for net, layer, w, pts in MAINS_ROUTES + LED_ROUTES:
        add_track(board, net, layer, w, pts)
    for x, y in GND_LED_VIAS:
        add_via(board, "GND_LED", x, y, 1.0, 0.5)
    for x, y in GND_VIAS:
        add_via(board, "GND", x, y, 0.6, 0.3)


VLED_POLY = [(104.5, 53.5), (115.0, 53.5), (115.0, 45.8), (127.0, 45.8), (127.0, 41.9),
             (145.5, 41.9), (145.5, 28.6), (129.0, 28.6), (129.0, 32.5), (114.0, 32.5),
             (114.0, 44.8), (104.5, 44.8)]


def zones(board):
    # Low-voltage ground, both layers, main part only (no ground plane in the 230 V zone)
    lv = [(LV_MIN_X, 0.5), (VCUT - 0.5, 0.5), (VCUT - 0.5, H - 0.5), (LV_MIN_X, H - 0.5)]
    add_zone(board, "GND", [F, B], lv, clearance=0.3, name="GND_LV")
    # ESP32-C3 antenna: no copper at all around it, up to the V-cut (Espressif HW guidelines)
    add_rule_area(board, [(79.5, 0), (VCUT - 0.5, 0), (VCUT - 0.5, 6.5), (79.5, 6.5)],
                  "antenna_keepout", footprints=False, tracks=True, vias=True, pour=True)
    # LED return on the strip part, bottom layer
    strip = [(113.4, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (113.4, H - 0.3)]
    add_zone(board, "GND_LED", [B], strip, clearance=0.4, name="GND_LED", solid=True)
    # VLED on the top layer: F2 pin 2 -> C7 / D3 / C8 -> J6 pin 1 (17 A path)
    add_zone(board, "VLED", [F], VLED_POLY, clearance=0.4, name="VLED", solid=True, priority=1)
    # Logic ground of the strip part (U4, pull-downs, net ties), top layer only
    logic = [(VCUT + 0.5, 0.5), (113.2, 0.5), (113.2, 44.3), (VCUT + 0.5, 44.3)]
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
    enabled = board.GetEnabledLayers()
    enabled.AddLayer(pcbnew.User_1)
    board.SetEnabledLayers(enabled)
    board.SetLayerName(pcbnew.User_1, "V-CUT")
    for n in design.nets():
        board.Add(pcbnew.NETINFO_ITEM(board, n))
    outline(board, for_routing)
    place(board)
    route_power(board)
    zones(board)
    tb = board.GetTitleBlock()
    tb.SetTitle("dmxnow - noeud DMX / relais / rubans LED")
    tb.SetRevision("0.1")
    tb.SetComment(0, "Généré par hardware/gen/pcb.py - ne pas éditer à la main")
    tb.SetComment(1, "Zone 230 V : RELECTURE HUMAINE OBLIGATOIRE")
    tb.SetComment(2, "K1, J1, J4, J7, J5, J6 : empreintes PROVISOIRES")
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
