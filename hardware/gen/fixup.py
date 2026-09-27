"""Finish what the autorouter left: read the DRC report and close the remaining
"missing connection" items with the simplest clean fix.

  * two items of the same net close to each other -> straight segment (top, then
    bottom layer) if it clears every other-net object;
  * a GND pad isolated from its pour -> via in the pad (tented) to the other layer.

Every fix is checked again by the next DRC run.
Usage: python3 fixup.py
"""
import math
import os
import re

import pcbnew

import drc
import maze
import pcb as P
import route as R

REPORT = os.path.join(P.HW, "build", "drc.rpt")
ITEM = re.compile(r"@\(([-\d.]+) mm, ([-\d.]+) mm\): (.*)")


def missing_pairs(txt):
    pairs = []
    blocks = txt.split("[unconnected_items]")[1:]
    for b in blocks:
        items = ITEM.findall(b)[:2]
        if len(items) == 2:
            pairs.append([(float(x) - P.OX, float(y) - P.OY, d) for x, y, d in items])
    return pairs


def net_of(desc):
    m = re.search(r"\[([^\]]+)\]", desc)
    return m.group(1) if m else None


def seg_clear(a, b, width, net, layer, segs, circles, boxes, margin=0.25):
    for s in segs:
        if s[5] == net or s[6] != layer:
            continue
        if R._seg_seg(a, b, s[0:2], s[2:4]) <= s[4] + width / 2 + margin:
            return False
    for c in circles:
        if c[3] != net and R._seg_dist(c[0], c[1], a[0], a[1], b[0], b[1]) <= c[2] + width / 2 + margin:
            return False
    for bx in boxes:
        if bx[4] == net or not (bx[6] & (1 << layer) or True):
            continue
        cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        half = max(bx[2] - bx[0], bx[3] - bx[1]) / 2
        if R._seg_dist(cx, cy, a[0], a[1], b[0], b[1]) <= half + width / 2 + margin:
            return False
    return True


def pad_via(board, net, px, py, segs, circles, boxes):
    """Via in (or next to) an isolated pad, only where it clears every other net."""
    pad = next((b[5] for b in boxes if b[0] <= px <= b[2] and b[1] <= py <= b[3] and b[4] == net), None)
    boxes6 = [b[:6] for b in boxes]
    segs6 = [s[:6] for s in segs]
    for dist in (1.0, 1.4, 1.9, 2.4, 2.9, 3.5):   # never in the pad itself (solder wicking)
        dirs = [(0, 0)] if dist == 0 else [(0, 1), (0, -1), (1, 0), (-1, 0), (0.7, 0.7), (-0.7, 0.7),
                                            (0.7, -0.7), (-0.7, -0.7)]
        for dx, dy in dirs:
            x, y = px + dx * dist, py + dy * dist
            if P.in_nc_keepout(x, y, P.VIA_D / 2) or \
                    not R._free(x, y, P.VIA_D / 2, segs6, circles, boxes6, net):   # own pad included
                continue
            if dist and not seg_clear((px, py), (x, y), 0.3, net, pcbnew.F_Cu, segs, circles,
                                      [b for b in boxes if b[5] is not pad]):
                continue
            if dist:
                P.add_track(board, net, pcbnew.F_Cu, 0.3, [(px, py), (x, y)])
                segs.append((px, py, x, y, 0.15, net, pcbnew.F_Cu))
            P.add_via(board, net, x, y, P.VIA_D, P.VIA_DRILL)
            circles.append((x, y, P.VIA_D / 2, net))
            return True
    return False


def endpoint(board, net, x, y, desc, toward):
    """Connection point (board mm) and allowed layer indexes (0=F, 1=B) for a DRC item."""
    pos = pcbnew.VECTOR2I(pcbnew.FromMM(x + P.OX), pcbnew.FromMM(y + P.OY))
    if "Pad" in desc:
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetname() == net and pad.HitTest(pos):
                    c = pad.GetPosition()
                    layers = (0, 1) if pad.GetDrillSize().x > 0 else (0,)
                    return (pcbnew.ToMM(c.x) - P.OX, pcbnew.ToMM(c.y) - P.OY), layers
        return (x, y), (0,)
    if "Via" in desc:
        return (x, y), (0, 1)
    if "Track" in desc:
        best = None
        for t in board.GetTracks():
            if isinstance(t, pcbnew.PCB_VIA) or t.GetNetname() != net:
                continue
            for e in (t.GetStart(), t.GetEnd()):
                ex, ey = pcbnew.ToMM(e.x) - P.OX, pcbnew.ToMM(e.y) - P.OY
                if t.HitTest(pos):
                    dd = (ex - toward[0]) ** 2 + (ey - toward[1]) ** 2
                    if best is None or dd < best[0]:
                        best = (dd, (ex, ey), 0 if t.GetLayer() == pcbnew.F_Cu else 1)
        if best:
            return best[1], (best[2],)
    return None, None


def obstacles(board):
    mm = pcbnew.ToMM
    segs, circles, boxes = [], [], []
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            circles.append((mm(t.GetPosition().x) - P.OX, mm(t.GetPosition().y) - P.OY,
                            mm(t.GetWidth()) / 2, t.GetNetname()))
        else:
            segs.append((mm(t.GetStart().x) - P.OX, mm(t.GetStart().y) - P.OY, mm(t.GetEnd().x) - P.OX,
                         mm(t.GetEnd().y) - P.OY, mm(t.GetWidth()) / 2, t.GetNetname(), t.GetLayer()))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            boxes.append((mm(bb.GetLeft()) - P.OX, mm(bb.GetTop()) - P.OY, mm(bb.GetRight()) - P.OX,
                          mm(bb.GetBottom()) - P.OY, pad.GetNetname(), pad, 0))
    return segs, circles, boxes


# Hand-checked closures for connections the autorouter tends to leave open
# (net, layer, width, [(x, y), ...]); validated by the DRC run that follows.
MANUAL = []
MANUAL_HOP_VIAS = []
# GND pads that the pours cannot reach: via in pad (tented) to the bottom pour
MANUAL_VIAS = []


def _ring(x, y, r, n=12):
    """Points on a circle: a via is inside a pour only if its whole ring is."""
    return [pcbnew.VECTOR2I(pcbnew.FromMM(x + r * math.cos(2 * math.pi * k / n)),
                            pcbnew.FromMM(y + r * math.sin(2 * math.pi * k / n))) for k in range(n)]


def island_vias(board, segs, circles, boxes):
    """Join every stray GND pour island to the other layer with a via."""
    n = 0
    zones = [z for z in board.Zones() if z.GetNetname() == "GND" and not z.GetIsRuleArea()]
    fills = {}
    for z in zones:
        for l in z.GetLayerSet().Seq():
            fills.setdefault(l, []).append(z.GetFilledPolysList(l))
    for layer, polys in fills.items():
        other = [p for l, ps in fills.items() if l != layer for p in ps]
        for poly in polys:
            areas = [(poly.Outline(i).Area(), i) for i in range(poly.OutlineCount())]
            if not areas:
                continue
            biggest = max(areas)[1]
            for _, i in areas:
                if i == biggest:
                    continue
                ol = poly.Outline(i)
                bb = ol.BBox()
                placed = False
                x = pcbnew.ToMM(bb.GetLeft()) + 0.4
                while x < pcbnew.ToMM(bb.GetRight()) - 0.3 and not placed:
                    y = pcbnew.ToMM(bb.GetTop()) + 0.4
                    while y < pcbnew.ToMM(bb.GetBottom()) - 0.3 and not placed:
                        v = pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
                        ring = _ring(x, y, P.VIA_D / 2 + 0.2)
                        if all(ol.PointInside(q) for q in ring) and \
                                any(all(o.Contains(q) for q in ring) for o in other) and \
                                not P.in_nc_keepout(x - P.OX, y - P.OY, P.VIA_D / 2) and \
                                R._free(x - P.OX, y - P.OY, P.VIA_D / 2, [s[:6] for s in segs], circles,
                                        [b[:6] for b in boxes], "GND"):
                            P.add_via(board, "GND", x - P.OX, y - P.OY, P.VIA_D, P.VIA_DRILL)
                            circles.append((x - P.OX, y - P.OY, P.VIA_D / 2, "GND"))
                            placed = True
                            n += 1
                        y += 0.3
                    x += 0.3
                if not placed:
                    # sliver too thin for a via: via next to a GND SMD pad it feeds
                    for b in boxes:
                        pad = b[5]
                        if b[4] != "GND" or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                            continue
                        # the pad is cut out of the pour and joined by spokes: test proximity
                        if ol.SquaredDistance(pad.GetPosition()) > pcbnew.FromMM(1.5) ** 2:
                            continue
                        c = pad.GetPosition()
                        if pad_via(board, "GND", pcbnew.ToMM(c.x) - P.OX, pcbnew.ToMM(c.y) - P.OY,
                                   segs, circles, boxes):
                            n += 1
                            break
    return n


def prune_vias(board):
    """Remove GND vias that reach a GND pour on one layer only and carry no track
    (stitching/island vias that ended up in a void)."""
    fills = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}
    for z in board.Zones():
        if z.GetNetname() == "GND" and not z.GetIsRuleArea():
            for l in z.GetLayerSet().Seq():
                if l in fills:
                    fills[l].append(z.GetFilledPolysList(l))
    ends = set()
    for t in board.GetTracks():
        if not isinstance(t, pcbnew.PCB_VIA) and t.GetNetname() == "GND":
            ends.add((t.GetStart().x, t.GetStart().y))
            ends.add((t.GetEnd().x, t.GetEnd().y))
    gnd_pads = [p for fp in board.GetFootprints() for p in fp.Pads() if p.GetNetname() == "GND"]
    removed = 0
    for v in [t for t in board.GetTracks() if isinstance(t, pcbnew.PCB_VIA) and t.GetNetname() == "GND"]:
        pos = v.GetPosition()
        if (pos.x, pos.y) in ends or any(p.HitTest(pos) for p in gnd_pads):
            continue
        on = [any(f.Contains(pos) for f in fills[l]) for l in (pcbnew.F_Cu, pcbnew.B_Cu)]
        if not all(on):
            board.Remove(v)
            removed += 1
    # GND track stubs whose far end touches nothing (left over by a pruned via)
    pads_all = [p for fp in board.GetFootprints() for p in fp.Pads()]
    tracks = [t for t in board.GetTracks() if not isinstance(t, pcbnew.PCB_VIA)]
    vias_pos = {(t.GetPosition().x, t.GetPosition().y) for t in board.GetTracks() if isinstance(t, pcbnew.PCB_VIA)}
    for t in [t for t in tracks if t.GetNetname() == "GND" and not t.IsLocked()]:
        for end in (t.GetStart(), t.GetEnd()):
            key = (end.x, end.y)
            touched = key in vias_pos or any(p.HitTest(end) for p in pads_all) or \
                sum(1 for o in tracks if o is not t and key in ((o.GetStart().x, o.GetStart().y),
                                                                (o.GetEnd().x, o.GetEnd().y)))
            if not touched:
                board.Remove(t)
                break
    return removed


def gnd_groups(board):
    """GND copper split into connected groups: pour fragments joined by GND vias, THT
    pads and tracks. Returns (main group anchors, [anchors of each other group]) where an
    anchor is a GND via or THT pad position (board mm, both layers)."""
    frag = []
    for z in board.Zones():
        if z.GetNetname() != "GND" or z.GetIsRuleArea():
            continue
        for l in z.GetLayerSet().Seq():
            f = z.GetFilledPolysList(l)
            for i in range(f.OutlineCount()):
                frag.append((l, f.Outline(i)))
    parent = list(range(len(frag)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    anchors = [t.GetPosition() for t in board.GetTracks()
               if isinstance(t, pcbnew.PCB_VIA) and t.GetNetname() == "GND"]
    anchors += [p.GetPosition() for fp in board.GetFootprints() for p in fp.Pads()
                if p.GetNetname() == "GND" and p.GetDrillSize().x > 0]
    where = {}
    for k, pos in enumerate(anchors):
        hit = [i for i, (l, ol) in enumerate(frag) if ol.PointInside(pos, pcbnew.FromMM(0.3))]
        where[k] = hit
        for h in hit[1:]:
            parent[find(h)] = find(hit[0])
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA) or t.GetNetname() != "GND":
            continue
        hit = [i for i, (l, ol) in enumerate(frag) if l == t.GetLayer() and
               (ol.PointInside(t.GetStart(), pcbnew.FromMM(0.1)) or ol.PointInside(t.GetEnd(), pcbnew.FromMM(0.1)))]
        for h in hit[1:]:
            parent[find(h)] = find(hit[0])
    groups = {}
    for i in range(len(frag)):
        groups.setdefault(find(i), []).append(i)
    if not groups:
        return [], []
    main_root = max(groups, key=lambda r: sum(frag[i][1].Area() for i in groups[r]))
    by_group = {}
    for k, hit in where.items():
        if hit:
            pos = anchors[k]
            by_group.setdefault(find(hit[0]), []).append((pcbnew.ToMM(pos.x) - P.OX, pcbnew.ToMM(pos.y) - P.OY))
    others = [by_group.get(r, []) for r in groups if r != main_root]
    return by_group.get(main_root, []), [o for o in others if o]


def join_gnd_groups(board, rounds=6):
    """Route a GND link (maze router) from each stray GND group to the main one."""
    joined = 0
    for _ in range(rounds):
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        main_pts, others = gnd_groups(board)
        if not others or not main_pts:
            break
        progress = False
        for grp in others:
            pairs = sorted(((a, b) for a in grp for b in main_pts),
                           key=lambda ab: (ab[0][0] - ab[1][0]) ** 2 + (ab[0][1] - ab[1][1]) ** 2)
            for a, b in pairs[:12]:
                if ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 > 12:
                    break
                plan = maze.route(board, "GND", a, b, (0, 1), (0, 1))
                if plan:
                    maze.apply(board, "GND", plan)
                    joined += 1
                    progress = True
                    break
        if not progress:
            break
    return joined


def trim_stubs(board):
    """Shorten the fixed crossing stubs (pcb.CROSSING_STUBS) to the span actually used:
    the autorouter may join a stub short of its end, leaving a dangling tip."""
    tol = pcbnew.FromMM(0.05)
    nets = {n for n, _, _ in P.CROSSING_STUBS}
    tracks = [t for t in board.GetTracks() if not isinstance(t, pcbnew.PCB_VIA)]
    n = 0
    for s in tracks:
        a, b = s.GetStart(), s.GetEnd()
        if s.GetNetname() not in nets or a.y != b.y or abs(abs(a.x - b.x) - pcbnew.FromMM(P.STUB_X1 - P.STUB_X0)) > tol:
            continue
        lo, hi = sorted((a.x, b.x))
        y = a.y
        xs = []
        for t in tracks:      # other copper of the net touching the stub line
            if t is s or t.GetNetname() != s.GetNetname() or t.GetLayer() != s.GetLayer():
                continue
            for q in (t.GetStart(), t.GetEnd()):
                if abs(q.y - y) <= tol and lo - tol <= q.x <= hi + tol:
                    xs.append(q.x)
            for q in (a, b):  # stub end lying on another segment (T joint)
                qq = (pcbnew.ToMM(q.x), pcbnew.ToMM(q.y))
                if R._seg_seg(qq, qq, (pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y)),
                              (pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y))) < 0.05:
                    xs.append(q.x)
        for it in list(board.GetPads()) + [v for v in board.GetTracks() if isinstance(v, pcbnew.PCB_VIA)]:
            if it.GetNetname() == s.GetNetname() and it.HitTest(pcbnew.VECTOR2I(it.GetPosition().x, y)) \
                    and lo - tol <= it.GetPosition().x <= hi + tol:
                xs.append(it.GetPosition().x)
        if not xs:
            continue
        nlo, nhi = max(lo, min(xs)), min(hi, max(xs))
        if nhi - nlo > pcbnew.FromMM(1.0) and (nlo > lo + tol or nhi < hi - tol):
            s.SetStart(pcbnew.VECTOR2I(nlo, y))
            s.SetEnd(pcbnew.VECTOR2I(nhi, y))
            n += 1
    return n


def main():
    txt, _, _ = drc.run(REPORT, fill=True)
    board = pcbnew.LoadBoard(P.PCB)
    segs, circles, boxes = obstacles(board)
    fixed = 0
    for (x1, y1, d1), (x2, y2, d2) in missing_pairs(txt):
        net = net_of(d1) or net_of(d2)
        if not net or net in R.SCRIPTED_NETS:
            continue
        zone1, zone2 = d1.startswith("Zone"), d2.startswith("Zone")
        if zone1 and zone2:
            continue
        if zone1 or zone2:
            # isolated pad of a pour net: via in the pad
            x, y, d = (x2, y2, d2) if zone1 else (x1, y1, d1)
            if "Pad" in d and net == "GND" and pad_via(board, net, x, y, segs, circles, boxes):
                fixed += 1
            continue
        ea, la = endpoint(board, net, x1, y1, d1, (x2, y2))
        eb, lb = endpoint(board, net, x2, y2, d2, (x1, y1))
        plan = maze.route(board, net, ea, eb, la, lb) if ea and eb else None
        if plan:
            maze.apply(board, net, plan)
            fixed += 1
            continue
        if ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5 > 6.0:
            continue
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            if layer == pcbnew.B_Cu and ("Pad" in d1 and "PTH" not in d1 or "Pad" in d2 and "PTH" not in d2):
                continue   # SMD pads are top-side only
            if seg_clear((x1, y1), (x2, y2), 0.25, net, layer, segs, circles, boxes):
                P.add_track(board, net, layer, 0.25, [(x1, y1), (x2, y2)])
                segs.append((x1, y1, x2, y2, 0.125, net, layer))
                fixed += 1
                break
    for net, layer, w, pts in MANUAL:
        P.add_track(board, net, layer, w, pts)
    for net, x, y in MANUAL_HOP_VIAS + MANUAL_VIAS:
        P.add_via(board, net, x, y, P.VIA_D, P.VIA_DRILL)
        circles.append((x, y, P.VIA_D / 2, net))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    segs, circles, boxes = obstacles(board)     # include the maze router's tracks and vias
    boxes5 = [b[:6] for b in boxes]
    iv = island_vias(board, segs, circles, boxes)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    rm = prune_vias(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    rm += prune_vias(board)
    jg = join_gnd_groups(board)
    print("GND groups joined: %d" % jg)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    print("pruned %d dangling GND vias" % rm)
    # zero-length debris left by the autorouter
    for t in [t for t in board.GetTracks() if not isinstance(t, pcbnew.PCB_VIA)]:
        if (t.GetStart() - t.GetEnd()).EuclideanNorm() < pcbnew.FromMM(0.02):
            board.Remove(t)
    print("trimmed %d crossing stubs" % trim_stubs(board))
    board.Save(P.PCB)
    print("fixup: %d fixes, %d manual, %d island vias" % (fixed, len(MANUAL) + len(MANUAL_VIAS), iv))


if __name__ == "__main__":
    main()
