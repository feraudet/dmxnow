"""Consistency checks between design.py, the schematic and the PCB.

  python3 check.py netlist <file.net>   compare KiCad-exported netlist with design.py
"""
import sys

import design
from sexp import find, find_all, parse


def netlist_from_kicad(path):
    root = parse(open(path, encoding="utf-8").read())
    res = {}
    for net in find_all(find(root, "nets"), "net"):
        name = str(find(net, "name")[1]).lstrip("/")
        nodes = sorted((str(find(n, "ref")[1]), str(find(n, "pin")[1])) for n in find_all(net, "node"))
        if name.startswith("unconnected-") or name.startswith("Net-("):
            # a single-pin net on a no-connect pin
            if len(nodes) == 1:
                continue
        res[name] = nodes
    return res


def check_netlist(path):
    got = netlist_from_kicad(path)
    want = design.nets()
    errors = []
    for n in sorted(set(want) | set(got)):
        if want.get(n) != got.get(n):
            errors.append("net %s: design=%s schematic=%s" % (n, want.get(n), got.get(n)))
    for e in errors:
        print("ERROR", e)
    print("netlist check: %d nets, %d errors" % (len(want), len(errors)))
    return not errors


def check_pcb(path):
    """Pad nets match design.py; only CROSSING_NETS cross the V-cut; no 230 V copper
    beyond MAINS_MAX_X."""
    import pcbnew
    import pcb as P
    board = pcbnew.LoadBoard(path)
    errors = []
    want = {(r, pin): n for n, conns in design.nets().items() for r, pin in conns}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNumber():
                continue
            key = (fp.GetReference(), pad.GetNumber())
            got = pad.GetNetname() or None
            if want.get(key) != got:
                errors.append("pad %s.%s: design=%s pcb=%s" % (key[0], key[1], want.get(key), got))
    vx = pcbnew.FromMM(P.OX + P.VCUT)
    lim = pcbnew.FromMM(P.OX + P.MAINS_MAX_X)
    for t in board.GetTracks():
        xs = (t.GetStart().x, t.GetEnd().x)
        if min(xs) < vx < max(xs) and t.GetNetname() not in design.CROSSING_NETS:
            errors.append("net %s crosses the V-cut" % t.GetNetname())
        if t.GetNetname() in design.MAINS_NETS and max(xs) + t.GetWidth() // 2 > lim:
            errors.append("230 V track %s beyond X=%.1f mm" % (t.GetNetname(), P.MAINS_MAX_X))
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        bb = z.GetBoundingBox()
        if bb.GetLeft() < vx < bb.GetRight():
            errors.append("zone %s crosses the V-cut" % z.GetNetname())
    for e in errors:
        print("ERROR", e)
    print("pcb check: %d errors" % len(errors))
    return not errors


if __name__ == "__main__":
    if sys.argv[1] == "netlist":
        sys.exit(0 if check_netlist(sys.argv[2]) else 1)
    if sys.argv[1] == "pcb":
        sys.exit(0 if check_pcb(sys.argv[2]) else 1)
