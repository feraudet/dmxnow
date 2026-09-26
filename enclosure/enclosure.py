"""dmxnow node enclosure - parametric CadQuery model (SPEC 4.12, ADR 0010).

🔴 RELECTURE HUMAINE OBLIGATOIRE : cloison 230 V, accès aux borniers, matériau.

  python3 enclosure.py                 build, check and export both variants
  python3 enclosure.py --variant cut   one variant only
  python3 enclosure.py --check-only    checks, no export

Coordinates: X = PCB x, Y = -PCB y (KiCad Y grows downwards), Z up from the base
bottom face. The board geometry comes from board.json (hardware/gen/export_board.py).
Printed parts: base (floor on the bed), cover_230v and lid_lv (top face on the bed),
clamp_bar x3, sw1_plunger, sw1_collar. Bought parts: see README.md.
"""
import argparse
import json
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = json.load(open(os.path.join(HERE, "board.json")))
OUT = os.path.join(HERE, "out")

# --- Parameters --------------------------------------------------------------------
WALL = 2.5            # side walls, all carrying glands (SPEC: >= 2.0, >= 2.5 with glands)
FLOOR = 2.0
LID = 2.5
CLR = 0.5             # PCB to enclosure clearance (SPEC 8.6)
STANDOFF = 5.0        # floor top to PCB bottom (THT leads <= 3.4 mm below the board)
PCB_T = BOARD["thickness"]
PCB_Z0 = FLOOR + STANDOFF
PCB_Z1 = PCB_Z0 + PCB_T
TOP = 31.0            # inside height (lid underside): tallest part F2 + fuse (21 mm) + 1.4
Z_OUT = TOP + LID

# cable chambers (PCB x): glands' lock nuts must stay clear of the board plane
NUT_T = 6.0           # lock nut + wall-side seal
CLAMP_W = 8.0         # strain-relief saddle and bar (ES-05: clamp independent of the gland)
PE_ZONE = 20.0        # conductor fan-out + WAGO 221-413 (PE junction, A9)
WAGO_FRONT_L = min(p["box"][0] for p in BOARD["parts"] if p["ref"] in ("J1", "J4", "J7"))
WAGO_FRONT_R = max(p["box"][2] for p in BOARD["parts"] if p["ref"] in ("J5", "J6", "J8"))
X_IN_L = WAGO_FRONT_L - CLR - PE_ZONE - CLAMP_W - NUT_T
X_IN_R = {"full": WAGO_FRONT_R + CLR + 8.0 + NUT_T,          # LV side: no clamp, 8 mm to bend
          "cut": BOARD["cut_edge_x"] + 1.0}                    # snapped tab stubs + clearance
Y_IN_TOP = min(r[1] for r in BOARD["rects"]) - CLR               # PCB y (top edge, band)
Y_IN_BOT = max(r[3] for r in BOARD["rects"]) + CLR

PART_X = BOARD["iso_slot_x"]          # 230 V / SELV partition, on the PCB isolation slots
SKIRT = (PART_X + 1.0, PART_X + 2.5)  # cover skirt, LV side of the slot tongues
SHIPLAP = (SKIRT[1], SKIRT[1] + 3.0)  # 230 V cover overlaps the LV lid here

# Glands (V-ENC-01): (name, wall, position along the wall (PCB y or x), axis z, hole d,
# lock-nut across corners). M16x1.5: H05VV-F 3G1.5 (8-9 mm) and LED cables; M12x1.5 for
# the DMX tail (range up to 7 mm: DMX cables are often 6-6.5 mm, too big for PG7).
M16 = (16.3, 22.0)
M12 = (12.3, 17.5)
GLANDS = [("mains_in", "L", 0.0, 15.0) + M16, ("out_fixture", "L", 21.5, 15.0) + M16,
          ("out_ledpsu", "L", 43.0, 15.0) + M16,
          ("dmx", "B", 81.0, 21.2) + M12,
          ("led_strips", "R", 16.0, 15.0) + M16, ("led_supply", "R", 43.0, 15.0) + M16]
CABLE_D = 8.6         # H05VV-F 3G1.5, for the clamp saddle

INSERT_D, INSERT_L = 4.0, 5.7     # M3 heat-set insert hole
SCREW_D = 3.4
BOSS_D = 8.0
ANTENNA_METAL_CLEAR = 15.0        # SPEC 4.12: no metal within 15 mm of the antenna

# lid screw bosses: (PCB x, wall 'T'/'B' or 'R' with PCB y), which lid
COVER_BOSSES = [(-35.0, "T"), (-35.0, "B"), (44.0, "T"), (44.0, "B")]
LID_BOSSES = {"full": [(58.0, "T"), (58.0, "B"), (158.0, "T"), (158.0, "B")],
              # cut: the top-right corner is 16 mm from the antenna: no screw there
              "cut": [(58.0, "T"), (58.0, "B"), (94.0, "B"), ("R", 45.0)]}

SW1 = next(p for p in BOARD["parts"] if p["ref"] == "SW1")
D4 = next(p for p in BOARD["parts"] if p["ref"] == "D4")
HOLES = {h["ref"]: h for h in BOARD["holes"]}


# --- Helpers ---------------------------------------------------------------------
def Y(y):
    return -y


def box(x1, y1, x2, y2, z1, z2):
    """Axis-aligned box from PCB coordinates (any corner order)."""
    xa, xb = sorted((x1, x2))
    ya, yb = sorted((Y(y1), Y(y2)))
    return cq.Workplane("XY").box(xb - xa, yb - ya, z2 - z1, centered=False).translate((xa, ya, z1))


def cyl(x, y, d, z1, z2):
    return cq.Workplane("XY").circle(d / 2).extrude(z2 - z1).translate((x, Y(y), z1))


def _drop(r):
    """Teardrop outline (local 2D, point up), truncated 0.6 mm above the circle: the
    flat top bridges easily and the opening stays under the gland seal and lock nut."""
    h = r + 0.6
    w = r * math.sqrt(2) - h          # half-width of the 45 deg point at height h
    return [(-r / math.sqrt(2), r / math.sqrt(2)), (-w, h), (w, h), (r / math.sqrt(2), r / math.sqrt(2)), (0, 0)]


def teardrop_x(y, z, d, x1, x2):
    """Horizontal hole along X, pointed upwards (printable without support)."""
    r = d / 2
    wp = lambda: cq.Workplane("YZ").workplane(offset=min(x1, x2)).center(Y(y), z)
    return wp().circle(r).extrude(abs(x2 - x1)).union(wp().polyline(_drop(r)).close().extrude(abs(x2 - x1)))


def teardrop_y(x, z, d, y1, y2):
    """Horizontal hole along Y (PCB y range y1..y2), pointed upwards."""
    r = d / 2
    ya, yb = sorted((Y(y1), Y(y2)))
    wp = lambda: cq.Workplane("XZ").workplane(offset=-yb).center(x, z)
    return wp().circle(r).extrude(yb - ya).union(wp().polyline(_drop(r)).close().extrude(yb - ya))


def boss_xy(spec, variant):
    """Lid screw boss centre (PCB coords): outside the cavity, tangent to it."""
    off = BOSS_D / 2
    if spec[0] == "R":
        return X_IN_R[variant] + off, spec[1]
    x, wall = spec
    return x, (Y_IN_TOP - off) if wall == "T" else (Y_IN_BOT + off)


def board_solid(variant):
    """The PCB as a slab (for clearance checks and renders): outline, slots, holes."""
    s = None
    x_max = BOARD["cut_edge_x"] if variant == "cut" else None
    for x1, y1, x2, y2 in BOARD["rects"]:
        b = box(x1, y1, min(x2, x_max) if x_max else x2, y2, PCB_Z0, PCB_Z1)
        s = b if s is None else s.union(b)
    sx, sw = BOARD["iso_slot_x"], BOARD["iso_slot_w"]
    for y1, y2 in BOARD["iso_slots"]:
        s = s.cut(box(sx - sw / 2, y1, sx + sw / 2, y2, PCB_Z0 - 1, PCB_Z1 + 1))
    if variant == "full":   # routed slot between the tabs
        xs, w = BOARD["split_x"], BOARD["slot_w"]
        edges = [0.0] + [v for t in BOARD["tabs"] for v in t] + [max(r[3] for r in BOARD["rects"])]
        for i in range(0, len(edges), 2):
            if edges[i + 1] > edges[i]:
                s = s.cut(box(xs - w / 2, edges[i], xs + w / 2, edges[i + 1], PCB_Z0 - 1, PCB_Z1 + 1))
    for h in BOARD["holes"]:
        if variant == "cut" and h["x"] > BOARD["cut_edge_x"]:
            continue
        s = s.cut(cyl(h["x"], h["y"], h["d"], PCB_Z0 - 1, PCB_Z1 + 1))
    return s


def part_boxes(variant):
    """Component envelopes above the board (courtyard x height)."""
    out = []
    for p in BOARD["parts"]:
        if variant == "cut" and p["strip"]:
            continue
        if p["height"] <= 0:
            continue
        x1, y1, x2, y2 = p["box"]
        out.append((p["ref"], box(x1, y1, x2, y2, PCB_Z1, PCB_Z1 + p["height"])))
    return out


def supports(variant):
    return [s for s in BOARD["supports"] if not (variant == "cut" and s["zone"] == "strip")]


# --- Base ------------------------------------------------------------------------
def base(variant):
    xr = X_IN_R[variant]
    xo1, xo2 = X_IN_L - WALL, xr + WALL
    yo1, yo2 = Y_IN_TOP - WALL, Y_IN_BOT + WALL
    b = box(xo1, yo1, xo2, yo2, 0, TOP).cut(box(X_IN_L, Y_IN_TOP, xr, Y_IN_BOT, FLOOR, TOP + 1))

    # lid screw bosses (outside the cavity, full height, M3 insert at the top)
    for spec in COVER_BOSSES + LID_BOSSES[variant]:
        x, y = boss_xy(spec, variant)
        b = b.union(cyl(x, y, BOSS_D, 0, TOP)).cut(cyl(x, y, INSERT_D, TOP - INSERT_L - 0.5, TOP + 1))

    # 230 V / SELV partition 🔴: full height where there is no board (band side), under
    # the board elsewhere, plus thin tongues filling the PCB isolation slots (flush with
    # the top face: K1 and PS1 sit over the slots).
    px1, px2 = PART_X - 1.0, PART_X + 1.0
    b = b.union(box(px1, Y_IN_TOP, px2, -CLR, FLOOR - 0.1, TOP))
    b = b.union(box(px1, -CLR, px2, Y_IN_BOT, FLOOR - 0.1, PCB_Z0 - 0.3))
    t = (BOARD["iso_slot_w"] - 0.4) / 2
    for y1, y2 in BOARD["iso_slots"]:
        b = b.union(box(PART_X - t, y1 + 0.8, PART_X + t, y2 - 0.8, PCB_Z0 - 0.4, PCB_Z1 - 0.2))

    # PCB mounting: H2 (and H3 on the full board) on M3 inserts; H1 is 13.5 mm from the
    # antenna, so a printed locating pin instead of metal (clamped by the lid).
    for ref in ("H2", "H3"):
        h = HOLES[ref]
        if variant == "cut" and h["x"] > BOARD["cut_edge_x"]:
            continue
        b = b.union(cyl(h["x"], h["y"], BOSS_D, FLOOR - 0.1, PCB_Z0)).cut(
            cyl(h["x"], h["y"], INSERT_D, PCB_Z0 - INSERT_L, PCB_Z0 + 1))
    h1 = HOLES["H1"]
    b = b.union(cyl(h1["x"], h1["y"], 7.0, FLOOR - 0.1, PCB_Z0)).union(
        cyl(h1["x"], h1["y"], h1["d"] - 0.3, PCB_Z0 - 0.1, PCB_Z1 + 1.4))
    for s in supports(variant):
        b = b.union(cyl(s["x"], s["y"], 6.0, FLOOR - 0.1, PCB_Z0))

    # cable glands (teardrop holes, point up)
    for name, wall, pos, z, d, _ in GLANDS:
        if variant == "cut" and wall == "R":
            continue
        if wall == "L":
            b = b.cut(teardrop_x(pos, z, d, xo1 - 1, X_IN_L + 1))
        elif wall == "R":
            b = b.cut(teardrop_x(pos, z, d, xr - 1, xo2 + 1))
        else:
            b = b.cut(teardrop_y(pos, z, d, Y_IN_BOT - 1, yo2 + 1))

    # strain relief saddle for the three mains cables (ES-05), inserts for the bars
    sx1 = X_IN_L + NUT_T
    sz = 15.0 - CABLE_D / 2 - 0.3
    b = b.union(box(sx1, Y_IN_TOP, sx1 + CLAMP_W, Y_IN_BOT, FLOOR - 0.1, sz))
    for name, wall, pos, z, d, _ in GLANDS[:3]:
        b = b.cut(teardrop_x(pos, z, CABLE_D + 0.6, sx1 - 1, sx1 + CLAMP_W + 1))
        for dy in (-8.0, 8.0):
            b = b.cut(cyl(sx1 + CLAMP_W / 2, pos + dy, INSERT_D, sz - INSERT_L - 0.3, sz + 1))

    # WAGO 221-413 (PE junction, 18.7 x 18.6 x 8.3) clip in the fan-out zone
    wx1, wx2 = sx1 + CLAMP_W + 0.8, sx1 + CLAMP_W + 0.8 + 18.6
    wy = GLANDS[1][2]
    for sgn in (-1, 1):
        ye = wy + sgn * (18.7 / 2 + 0.3)
        b = b.union(box(wx1 + 3, ye, wx2 - 3, ye + sgn * 1.6, FLOOR - 0.1, FLOOR + 6.0))
        b = b.union(box(wx1 + 3, ye, wx2 - 3, ye - sgn * 0.5, FLOOR + 5.0, FLOOR + 6.0))   # snap lip

    # ventilation inlets low on the top wall, under the strip part (MOSFETs), full only
    if variant == "full":
        for i in range(6):
            x = 108.0 + i * 5.0
            b = b.cut(box(x, Y_IN_TOP + 1, x + 2.0, yo1 - 1, FLOOR + 1.0, FLOOR + 4.0))

    # cable-tie passages on the floor (SPEC: 5-8 mm wide): ears on both long walls
    for x in ((0.0, 80.0) if variant == "cut" else (0.0, 120.0)):
        for y_in, sgn in ((yo1, -1), (yo2, 1)):
            ear = box(x - 7, y_in, x + 7, y_in + sgn * 8.0, 0, 4.0)
            b = b.union(ear).cut(box(x - 3.5, y_in + sgn * 2.5, x + 3.5, y_in + sgn * 5.5, -1, 5))
    return b


# --- Lids ------------------------------------------------------------------------
def _plate(x1, x2, variant):
    yo1, yo2 = Y_IN_TOP - WALL, Y_IN_BOT + WALL
    p = box(x1, yo1, x2, yo2, TOP, Z_OUT)
    # locating rim inside the walls
    rim_x1 = max(x1, X_IN_L + 0.3)
    rim_x2 = min(x2, X_IN_R[variant] - 0.3)
    rim = box(rim_x1, Y_IN_TOP + 0.3, rim_x2, Y_IN_BOT - 0.3, TOP - 1.0, TOP)
    rim = rim.cut(box(rim_x1 + 1.2 if x1 <= X_IN_L else rim_x1 - 1, Y_IN_TOP + 1.5,
                      rim_x2 - 1.2 if x2 >= X_IN_R[variant] else rim_x2 + 1, Y_IN_BOT - 1.5, TOP - 3, TOP + 1))
    return p.union(rim)


def _screws(p, specs, variant):
    for spec in specs:
        x, y = boss_xy(spec, variant)
        p = p.union(cyl(x, y, BOSS_D, TOP, Z_OUT))
        p = p.cut(cyl(x, y, SCREW_D, TOP - 1, Z_OUT + 1)).cut(cyl(x, y, 6.2, Z_OUT - 1.2, Z_OUT + 1))
    return p


def _engrave(p, txt, x, y, size, depth=0.6):
    t = (cq.Workplane("XY").workplane(offset=Z_OUT - depth)
         .text(txt, size, depth + 0.5, halign="center", valign="center").translate((x, Y(y), 0)))
    return p.cut(t)


def _skirt_bottom(y):
    """Lowest skirt z at PCB y: above the board, or above K1/PS1 which cross the line."""
    z = PCB_Z1 + 0.5
    for p in BOARD["parts"]:
        x1, y1, x2, y2 = p["box"]
        if x1 < SKIRT[1] and x2 > SKIRT[0] and y1 - 0.5 < y < y2 + 0.5:
            z = max(z, PCB_Z1 + p["height"] + 0.5)
    return z


def cover_230v(variant):
    """🔴 Access cover of the mains terminals (J1, J4, J7, PE junction): screwed, tool
    needed; lies over the LV lid edge (shiplap) so it comes off on its own."""
    xo1 = X_IN_L - WALL
    p = _plate(xo1, SHIPLAP[0], variant)
    p = p.union(box(SHIPLAP[0], Y_IN_TOP - WALL, SHIPLAP[1], Y_IN_BOT + WALL, TOP + LID / 2, Z_OUT))
    p = _screws(p, COVER_BOSSES, variant)
    # skirt above the board on the partition line, stepped over K1 and PS1
    ys = sorted({Y_IN_TOP, Y_IN_BOT} | {v for q in BOARD["parts"] if q["box"][0] < SKIRT[1] and q["box"][2] > SKIRT[0]
                                        for v in (q["box"][1] - 0.5, q["box"][3] + 0.5)})
    ys = [v for v in ys if Y_IN_TOP <= v <= Y_IN_BOT]
    for y1, y2 in zip(ys, ys[1:]):
        zb = _skirt_bottom((y1 + y2) / 2)
        if y2 < -CLR:            # no board: meet the full-height partition of the base
            zb = TOP - 3.0
        p = p.union(box(SKIRT[0], y1, SKIRT[1], y2, zb, TOP))
    # pressers on the PCB support points of the mains zone
    for s in supports(variant):
        if s["zone"] == "mains" and s["presser"]:
            p = p.union(cyl(s["x"], s["y"], 4.0, PCB_Z1 + 0.2, TOP))
    p = _engrave(p, "230V~  16A MAX", (xo1 + PART_X) / 2, 38.0, 5.0)
    p = _engrave(p, "! 230V", (xo1 + PART_X) / 2, 12.0, 7.0)
    return p


def lid_lv(variant, light_pipe=False):
    xr = X_IN_R[variant] + WALL
    p = _plate(SHIPLAP[0], xr, variant)
    p = p.cut(box(SHIPLAP[0] - 1, Y_IN_TOP - WALL - 1, SHIPLAP[1], Y_IN_BOT + WALL + 1, TOP + LID / 2, Z_OUT + 1))
    p = _screws(p, LID_BOSSES[variant], variant)
    # H1: presser tube around the printed locating pin
    h1 = HOLES["H1"]
    p = p.union(cyl(h1["x"], h1["y"], 6.5, PCB_Z1 + 0.2, TOP)).cut(cyl(h1["x"], h1["y"], 3.6, PCB_Z1, TOP - 0.5))
    for s in supports(variant):
        if s["zone"] != "mains" and s["presser"]:
            p = p.union(cyl(s["x"], s["y"], 4.0, PCB_Z1 + 0.2, TOP))
    # SW1 push-button (A6): guide tube under the lid, 2 mm hole, plunger 2 mm below the surface
    sx, sy = (SW1["box"][0] + SW1["box"][2]) / 2, (SW1["box"][1] + SW1["box"][3]) / 2
    p = p.union(cyl(sx, sy, 6.4, 22.0, TOP)).cut(cyl(sx, sy, 4.3, 21.0, TOP)).cut(cyl(sx, sy, 2.0, TOP - 1, Z_OUT + 1))
    if light_pipe:   # option A7: 3 mm light guide above D4
        lx, ly = (D4["box"][0] + D4["box"][2]) / 2, (D4["box"][1] + D4["box"][3]) / 2
        p = p.union(cyl(lx, ly, 4.4, PCB_Z1 + 3.0, TOP)).cut(cyl(lx, ly, 3.1, PCB_Z1 + 2.0, Z_OUT + 1))
    if variant == "full":   # vents above the MOSFETs Q2..Q5 (R-08)
        for i in range(4):
            x = 114.5 + i * 3.4
            p = p.cut(box(x, 1.0, x + 1.8, 29.0, TOP - 3, Z_OUT + 1))
    p = _engrave(p, "dmxnow", (SHIPLAP[1] + X_IN_R[variant]) / 2 if variant == "cut" else 75.0, 44.0, 6.0)
    p = _engrave(p, "MAINT", sx, sy + 5.5, 3.0)
    if variant == "full":
        p = _engrave(p, "LED 12-24V  16A MAX", 128.0, 44.0, 3.5)
    return p


# --- Small parts -----------------------------------------------------------------
def clamp_bar():
    """Strain relief bar, one per mains cable; two M3 x 16 screws into the saddle."""
    b = box(0, -10.0, CLAMP_W, 10.0, 0, 5.0)
    b = b.cut(teardrop_x(0.0, -CABLE_D / 2 + 1.2, CABLE_D + 0.6, -1, CLAMP_W + 1))
    for dy in (-8.0, 8.0):
        b = b.cut(cyl(CLAMP_W / 2, dy, SCREW_D, -1, 6))
    return b


def sw1_plunger():
    """Captive plunger: pin 1.8 mm in the 2 mm hole, body in the 4.3 mm tube."""
    top = TOP - 0.3
    sw_top = PCB_Z1 + 2.5
    p = cyl(0, 0, 1.8, top - 0.5, top + 0.5)            # pin, stops 2 mm under the surface
    p = p.union(cyl(0, 0, 3.9, sw_top + 0.2, top - 0.5))
    return p.translate((0, 0, -(sw_top + 0.2)))


def sw1_collar():
    """Press-fit collar under the guide tube: keeps the plunger in the lid."""
    return cyl(0, 0, 6.0, 0, 1.6).cut(cyl(0, 0, 3.7, -1, 3))


# --- Checks (SPEC 8.6) -----------------------------------------------------------
def _vol(a, b):
    try:
        return a.intersect(b).val().Volume()
    except Exception:   # empty result
        return 0.0


def check(variant, parts):
    errs = []
    for name, s in parts.items():
        v = s.val()
        if not v.isValid():
            errs.append("%s: invalid solid" % name)
        if any(not sh.Closed() for sh in v.Shells()):
            errs.append("%s: open shell" % name)
    pcb = board_solid(variant)
    comps = part_boxes(variant)
    for name in ("base", "cover_230v", "lid_lv"):
        v = _vol(parts[name], pcb)
        if v > 0.05:
            errs.append("%s intersects the PCB (%.2f mm3)" % (name, v))
        for ref, cb in comps:
            v = _vol(parts[name], cb)
            if v > 0.05:
                errs.append("%s intersects %s (%.2f mm3)" % (name, ref, v))
    # PCB + 0.5 mm inside the cavity
    for x1, y1, x2, y2 in BOARD["rects"]:
        x2 = min(x2, BOARD["cut_edge_x"]) if variant == "cut" else x2
        if not (X_IN_L <= x1 - CLR and x2 + CLR <= X_IN_R[variant] + 1e-6
                and Y_IN_TOP <= y1 - CLR + 1e-6 and y2 + CLR <= Y_IN_BOT + 1e-6):
            errs.append("board rect %s not within cavity - %.1f mm" % ((x1, y1, x2, y2), CLR))
    # wall thickness (by construction, re-measured on the solid's bounding boxes)
    bb = parts["base"].val().BoundingBox()
    if min(X_IN_L - bb.xmin, bb.xmax - X_IN_R[variant]) < 2.5 - 1e-6 or FLOOR < 2.0 or LID < 2.0:
        errs.append("wall/floor/lid thinner than required")
    # glands: lock nuts inside must clear the board, the parts, each other
    nuts = []
    for name, wall, pos, z, d, ac in GLANDS:
        if variant == "cut" and wall == "R":
            continue
        if wall == "L":
            n = cq.Workplane("YZ").workplane(offset=X_IN_L).center(Y(pos), z).polygon(6, ac).extrude(NUT_T - 0.5)
        elif wall == "R":
            n = cq.Workplane("YZ").workplane(offset=X_IN_R[variant] - NUT_T + 0.5).center(Y(pos), z).polygon(6, ac).extrude(NUT_T - 0.5)
        else:
            n = cq.Workplane("XZ").workplane(offset=-(-Y_IN_BOT)).center(pos, z).polygon(6, ac).extrude(-(NUT_T - 0.5))
            n = cq.Workplane("XY").add(n.val())
        nuts.append((name, n))
    for name, n in nuts:
        if _vol(n, pcb) > 0.05:
            errs.append("gland %s nut hits the PCB" % name)
        for ref, cb in comps:
            if _vol(n, cb) > 0.05:
                errs.append("gland %s nut hits %s" % (name, ref))
        zb, zt = n.val().BoundingBox().zmin, n.val().BoundingBox().zmax
        if zb < FLOOR - 1e-6 or zt > TOP + 1e-6:
            errs.append("gland %s nut outside the cavity height (%.1f..%.1f)" % (name, zb, zt))
    # gland openings (truncated teardrop) covered by the lock nut (radius at the flats)
    for name, wall, pos, z, d, ac in GLANDS:
        r = d / 2
        w = r * math.sqrt(2) - (r + 0.6)
        if math.hypot(w, r + 0.6) > ac / 2 * math.cos(math.pi / 6) - 0.3:
            errs.append("gland %s: opening not covered by its lock nut" % name)
    # no metal within 15 mm of the antenna (inserts, screws), edge distance
    ax1, ay1, ax2, ay2 = BOARD["antenna"]
    metal = [boss_xy(s, variant) + (INSERT_D / 2 + 0.6,) for s in COVER_BOSSES + LID_BOSSES[variant]]
    metal += [(h["x"], h["y"], 2.8) for r, h in HOLES.items() if r != "H1"
              and not (variant == "cut" and h["x"] > BOARD["cut_edge_x"])]
    for x, y, r in metal:
        dx = max(ax1 - x, 0, x - ax2)
        dy = max(ay1 - y, 0, y - ay2)
        if math.hypot(dx, dy) - r < ANTENNA_METAL_CLEAR:
            errs.append("metal at (%.1f, %.1f) %.1f mm from the antenna" % (x, y, math.hypot(dx, dy) - r))
    # partition continuity: base wall + tongues + cover skirt overlap (labyrinth)
    if _skirt_bottom(40.0) > PCB_Z1 + 2.0 + 30:
        errs.append("skirt too high")
    return errs


# --- Build / export ----------------------------------------------------------------
def build(variant):
    return {"base": base(variant), "cover_230v": cover_230v(variant), "lid_lv": lid_lv(variant),
            "lid_lv_light_pipe": lid_lv(variant, light_pipe=True),
            "clamp_bar": clamp_bar(), "sw1_plunger": sw1_plunger(), "sw1_collar": sw1_collar()}


def print_pose(name, s):
    """STL in printing position (SPEC 4.12): lids and cover top face down on the bed,
    everything else as modelled; always resting on z = 0."""
    if name.startswith(("lid", "cover")):
        s = s.rotate((0, 0, 0), (1, 0, 0), 180)
    bb = s.val().BoundingBox()
    return s.translate((-bb.xmin, -bb.ymin, -bb.zmin))


def export(variant, parts):
    """STEP in assembly position (CAD), STL in printing position (slicer)."""
    d = os.path.join(OUT, variant)
    os.makedirs(d, exist_ok=True)
    for name, s in parts.items():
        if variant == "cut" and name in ("clamp_bar", "sw1_plunger", "sw1_collar"):
            continue   # identical to the full variant
        cq.exporters.export(s, os.path.join(d, name + ".step"))
        cq.exporters.export(print_pose(name, s), os.path.join(d, name + ".stl"),
                            tolerance=0.05, angularTolerance=0.2)


def size(variant):
    bb = base(variant).val().BoundingBox()
    return bb.xlen, bb.ylen, Z_OUT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=("full", "cut"))
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args()
    fail = False
    for variant in ([a.variant] if a.variant else ["full", "cut"]):
        parts = build(variant)
        errs = check(variant, parts)
        L, Wd, Hh = size(variant)
        print("[%s] outside %.1f x %.1f x %.1f mm (walls + bosses/ears), %d check error(s)"
              % (variant, L, Wd, Hh, len(errs)))
        for e in errs:
            print("   -", e)
        fail |= bool(errs)
        if not a.check_only:
            export(variant, parts)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
