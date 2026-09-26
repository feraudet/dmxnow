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
    """Pad nets match design.py; only CROSSING_NETS cross the breakaway line; no 230 V copper
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
    vx = pcbnew.FromMM(P.OX + P.SPLIT_X)
    lim = pcbnew.FromMM(P.OX + P.MAINS_MAX_X)
    for t in board.GetTracks():
        xs = (t.GetStart().x, t.GetEnd().x)
        if min(xs) < vx < max(xs) and t.GetNetname() not in design.CROSSING_NETS:
            errors.append("net %s crosses the breakaway line" % t.GetNetname())
        if t.GetNetname() in design.MAINS_NETS and max(xs) + t.GetWidth() // 2 > lim:
            errors.append("230 V track %s beyond X=%.1f mm" % (t.GetNetname(), P.MAINS_MAX_X))
    # every crossing stub must still carry its own net (a stub touching a foreign pad
    # would be silently renamed by KiCad when the board is reloaded)
    for net, y, w in P.CROSSING_STUBS:
        ok = any(not isinstance(t, pcbnew.PCB_VIA) and t.GetNetname() == net
                 and abs(pcbnew.ToMM(t.GetStart().y) - P.OY - y) < 0.01
                 and min(t.GetStart().x, t.GetEnd().x) < vx < max(t.GetStart().x, t.GetEnd().x)
                 for t in board.GetTracks())
        if not ok:
            errors.append("crossing stub %s at y=%.2f missing or renamed" % (net, y))
        elif not any(t0 + w / 2 + 0.5 <= y <= t1 - w / 2 - 0.5 for t0, t1 in P.TABS):
            errors.append("crossing stub %s at y=%.2f is not on a solid tab" % (net, y))
    # no via inside an SMD pad (open via in a pad wicks the solder away)
    smd = [pad for fp in board.GetFootprints() for pad in fp.Pads()
           if pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD]
    for v in board.GetTracks():
        if isinstance(v, pcbnew.PCB_VIA):
            for pad in smd:
                if pad.HitTest(v.GetPosition(), v.GetWidth() // 2):
                    errors.append("via %s at (%.2f, %.2f) inside SMD pad %s.%s" % (
                        v.GetNetname(), pcbnew.ToMM(v.GetPosition().x) - P.OX,
                        pcbnew.ToMM(v.GetPosition().y) - P.OY,
                        pad.GetParent().GetReference(), pad.GetNumber()))
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        bb = z.GetBoundingBox()
        if bb.GetLeft() < vx < bb.GetRight():
            errors.append("zone %s crosses the breakaway line" % z.GetNetname())
    for e in errors:
        print("ERROR", e)
    print("pcb check: %d errors" % len(errors))
    return not errors


if __name__ == "__main__":
    if sys.argv[1] == "netlist":
        sys.exit(0 if check_netlist(sys.argv[2]) else 1)
    if sys.argv[1] == "pcb":
        sys.exit(0 if check_pcb(sys.argv[2]) else 1)
