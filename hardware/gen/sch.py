"""Generate hardware/dmxnow.kicad_sch from design.py.

Label-based schematic: every connected pin gets a short wire stub ending on a net
label; unconnected pins get a no-connect flag. Written in KiCad 7 syntax
(readable by KiCad 7, 8 and 9).
"""
import os
import sys
import uuid

import design
import symlib
from sexp import QStr, dump, find, find_all

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "dmxnow.kicad_sch")
PROJECT = "dmxnow"
GRID = 2.54
STUB = 2.54

GROUPS = [
    ("230 V : entrée, protection, alimentation isolée  -  RELECTURE HUMAINE OBLIGATOIRE",
     ["J1", "F1", "RV1", "PS1"]),
    ("230 V : relais et sorties commutées  -  RELECTURE HUMAINE OBLIGATOIRE",
     ["K1", "J4", "J7", "Q1", "R5", "R6", "D2"]),
    ("Alimentation 3,3 V", ["U3", "C5", "C10", "C6", "C1", "C2"]),
    ("ESP32-C3, démarrage, programmation, bouton, LED option (A7)",
     ["U1", "R1", "C4", "R2", "R3", "R4", "R23", "SW1", "J3", "R19", "D4"]),
    ("Sortie DMX", ["U2", "C3", "R22", "D1", "J2"]),
    ("Partie sécable rubans LED : entrée 12/24 V et commande",
     ["J5", "F2", "D3", "C7", "C8", "U4", "C9", "R20", "R21",
      "R15", "R16", "R17", "R18"]),
    ("Partie sécable rubans LED : étages de puissance",
     ["R7", "R11", "Q2", "R8", "R12", "Q3", "R9", "R13", "Q4", "R10", "R14", "Q5", "J6"]),
    ("Fixations", ["H1", "H2", "H3"]),
]
_missing = {p.ref for p in __import__("design").PARTS} - {r for _, refs in GROUPS for r in refs}
if _missing:
    raise SystemExit("sch.py: parts missing from GROUPS: %s" % sorted(_missing))
POWER_FLAG_NETS = ["L_PSU", "N"]

_uuid_ns = uuid.UUID("5f0c7a52-9d1b-4c7e-8a51-6a0d3c1e2b7f")


def uid(*key):
    """Deterministic UUIDs so that regenerating gives a stable diff."""
    return QStr(str(uuid.uuid5(_uuid_ns, "/".join(str(k) for k in key))))


def snap(v):
    return round(round(v / GRID) * GRID, 4)


def fmt(v):
    return "%g" % round(v, 4)


def at(x, y, a=0):
    return ["at", fmt(x), fmt(y), fmt(a)]


def label_width(net):
    return 1.0 * len(net) + 2.0


class Sheet:
    def __init__(self):
        self.root = uid("root")
        self.items = []
        self.lib = {}

    def add_lib(self, lib_id):
        if lib_id not in self.lib:
            self.lib[lib_id] = symlib.get(lib_id)
        return self.lib[lib_id]

    def text(self, s, x, y, size=2.0):
        self.items.append(["text", QStr(s), at(x, y),
                           ["effects", ["font", ["size", fmt(size), fmt(size)], "bold"], ["justify", "left", "bottom"]],
                           ["uuid", uid("text", s)]])

    def wire(self, x1, y1, x2, y2, key):
        self.items.append(["wire", ["pts", ["xy", fmt(x1), fmt(y1)], ["xy", fmt(x2), fmt(y2)]],
                           ["stroke", ["width", "0"], ["type", "default"]], ["uuid", uid("wire", *key)]])

    def label(self, net, x, y, dx, dy, key):
        # angle: text reads away from the pin
        if dx > 0:
            ang, just = 0, ["justify", "left", "bottom"]
        elif dx < 0:
            ang, just = 180, ["justify", "right", "bottom"]
        elif dy < 0:
            ang, just = 90, ["justify", "left", "bottom"]
        else:
            ang, just = 270, ["justify", "right", "bottom"]
        self.items.append(["label", QStr(net), at(x, y, ang), ["fields_autoplaced"],
                           ["effects", ["font", ["size", "1.27", "1.27"]], just],
                           ["uuid", uid("label", *key)]])

    def no_connect(self, x, y, key):
        self.items.append(["no_connect", ["at", fmt(x), fmt(y)], ["uuid", uid("nc", *key)]])

    def symbol(self, lib_id, ref, value, x, y, unit=1, footprint="", fields=None,
               dnp=False, in_bom=True, on_board=True):
        sym = self.add_lib(lib_id)
        node = ["symbol", ["lib_id", QStr(lib_id)], at(x, y), ["unit", str(unit)],
                ["in_bom", "yes" if in_bom else "no"], ["on_board", "yes" if on_board else "no"],
                ["dnp", "yes" if dnp else "no"], ["uuid", uid("sym", ref, unit)]]
        props = {"Reference": ref, "Value": value, "Footprint": footprint, "Datasheet": ""}
        lib_props = {str(p[1]): p for p in find_all(sym, "property")}
        pid = 0
        for name, val in props.items():
            lp = lib_props.get(name)
            if lp is not None:
                lat = find(lp, "at")
                px, py, pa = float(lat[1]), float(lat[2]), float(lat[3]) if len(lat) > 3 else 0
                eff = find(lp, "effects") or ["effects", ["font", ["size", "1.27", "1.27"]]]
            else:
                px, py, pa, eff = 0, 0, 0, ["effects", ["font", ["size", "1.27", "1.27"]], "hide"]
            node.append(["property", QStr(name), QStr(val), at(x + px, y - py, pa), ["id", str(pid)], eff])
            pid += 1
        for name, val in (fields or {}).items():
            node.append(["property", QStr(name), QStr(val), at(x, y, 0), ["id", str(pid)],
                         ["effects", ["font", ["size", "1.27", "1.27"]], "hide"]])
            pid += 1
        seen = set()
        for p in symlib.pins(sym):
            if p[6] in (0, unit) and p[0] not in seen:
                seen.add(p[0])
                node.append(["pin", QStr(p[0]), ["uuid", uid("pin", ref, unit, p[0])]])
        node.append(["instances", ["project", QStr(PROJECT),
                                   ["path", QStr("/" + self.root), ["reference", QStr(ref)], ["unit", str(unit)]]]])
        self.items.append(node)
        return sym


def symbol_extent(sym, unit):
    """(xmin, ymin, xmax, ymax) in schematic orientation, pins + labels included."""
    xs, ys = [0.0], [0.0]
    for p in symlib.pins(sym):
        if p[6] in (0, unit):
            xs.append(p[3]); ys.append(-p[4])
    for sub in find_all(sym, "symbol"):
        for r in find_all(sub, "rectangle"):
            s, e = find(r, "start"), find(r, "end")
            xs += [float(s[1]), float(e[1])]; ys += [-float(s[2]), -float(e[2])]
    return min(xs), min(ys), max(xs), max(ys)


def place_part(sh, part, x, y, unit=1):
    sym = sh.add_lib(part.symbol)
    fields = {"MPN": part.mpn, "LCSC": part.lcsc, "Section": part.section}
    if part.variant:
        fields["Variant"] = part.variant
    is_mech = part.symbol.startswith("Mechanical:")
    sh.symbol(part.symbol, part.ref, part.value, x, y, unit, part.footprint, fields,
              dnp=part.dnp, in_bom=not is_mech)
    done = set()
    for num, name, ptype, px, py, pa, pu in symlib.pins(sym):
        if pu not in (0, unit):
            continue
        ex, ey = x + px, y - py
        key = (round(ex, 3), round(ey, 3))
        if key in done:
            continue  # stacked pins (ESP32 GND) share one stub
        done.add(key)
        # direction from the pin end away from the body
        dirs = {0: (-1, 0), 90: (0, 1), 180: (1, 0), 270: (0, -1)}
        dx, dy = dirs[int(pa) % 360]
        net = part.pins.get(num)
        if num not in part.pins:
            raise SystemExit("%s pin %s (%s) missing in design.py" % (part.ref, num, name))
        if net is None:
            sh.no_connect(ex, ey, (part.ref, num))
            continue
        lx, ly = ex + dx * STUB, ey + dy * STUB
        sh.wire(ex, ey, lx, ly, (part.ref, unit, num))
        sh.label(net, lx, ly, dx, dy, (part.ref, unit, num))


def units_of(part):
    sym = symlib.get(part.symbol)
    return sorted({p[6] for p in symlib.pins(sym) if p[6] != 0}) or [1]


def build():
    sh = Sheet()
    x0, y0 = 20.32, 30.48
    col_x, row_y, row_h = x0, y0, 0.0
    sheet_w = 570.0
    for title, refs in GROUPS:
        # measure the block
        cells = []
        for ref in refs:
            part = design.part(ref)
            for unit in units_of(part):
                sym = sh.add_lib(part.symbol)
                xmin, ymin, xmax, ymax = symbol_extent(sym, unit)
                netw = max([label_width(n) for n in part.pins.values() if n] + [4.0])
                half = max(xmax + STUB + netw, 0.5 * len(part.value) + 2)
                cells.append((part, unit, min(xmin - STUB - netw, -half), ymin - STUB - 6, half, ymax + STUB + 6))
        block_w = min(sheet_w - 40, sum(c[4] - c[2] + 5 for c in cells))
        if col_x + block_w > sheet_w and col_x > x0:
            col_x, row_y, row_h = x0, row_y + row_h + 20, 0.0
        sh.text(title, col_x, row_y - 5)
        cx, cy, line_h, used_w = col_x, row_y, 0.0, 0.0
        for part, unit, xmin, ymin, xmax, ymax in cells:
            w, h = xmax - xmin, ymax - ymin
            if cx - col_x + w > block_w and cx > col_x:
                cx, cy, line_h = col_x, cy + line_h + 5, 0.0
            sx, sy = snap(cx - xmin), snap(cy - ymin)
            place_part(sh, part, sx, sy, unit)
            cx += w + 5
            used_w = max(used_w, cx - col_x)
            line_h = max(line_h, h)
        row_h = max(row_h, cy + line_h - row_y)
        col_x += used_w + 25
    # power flags
    fx, fy = snap(x0), snap(row_y + row_h + 25)
    sh.text("Drapeaux d'alimentation (ERC)", fx, fy - 8)
    for i, net in enumerate(POWER_FLAG_NETS):
        x = snap(fx + i * 25.4)
        sh.symbol("power:PWR_FLAG", "#FLG%02d" % (i + 1), "PWR_FLAG", x, fy, in_bom=False, on_board=False)
        sh.wire(x, fy, x, fy + STUB, ("flag", net))
        sh.label(net, x, fy + STUB, 0, 1, ("flag", net))
    return sh


def write(sh):
    doc = ["kicad_sch", ["version", "20230121"], ["generator", "eeschema"], ["uuid", sh.root],
           ["paper", "A2"],
           ["title_block", ["title", QStr("dmxnow - noeud DMX / relais / rubans LED")],
            ["rev", QStr("0.1")], ["company", QStr("dmxnow")],
            ["comment", "1", QStr("Généré par hardware/gen/sch.py depuis design.py - ne pas éditer à la main")],
            ["comment", "2", QStr("Parties 230 V : RELECTURE HUMAINE OBLIGATOIRE")],
            ["comment", "3", QStr("K1, J1, J4, J7, J5, J6 : empreintes PROVISOIRES (fiches non vérifiées)")]],
           ["lib_symbols"] + list(sh.lib.values())]
    doc += sh.items
    doc.append(["sheet_instances", ["path", QStr("/"), ["page", QStr("1")]]])
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(dump(doc) + "\n")


if __name__ == "__main__":
    s = build()
    write(s)
    print("written", os.path.normpath(OUT), "-", sum(1 for i in s.items if i[0] == "symbol"), "symbols")
