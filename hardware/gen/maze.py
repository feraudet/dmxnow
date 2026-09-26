"""Tiny local maze router (A* on a 0.1 mm grid, two layers + vias) used by fixup.py
to close the last connections the autorouter leaves open. Clearances are checked
against every other-net pad, track, via and pour fill in a window around the pair."""
import heapq
import math

import pcbnew

import pcb as P

STEP = 0.1          # grid pitch, mm
TRACK_W = 0.25
VIA_D, VIA_DRILL = P.VIA_D, P.VIA_DRILL
CLEAR = 0.25        # clearance used by the maze router (board rule is 0.2)


def _mm(v):
    return pcbnew.ToMM(v)


def _seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(px - x1 - t * dx, py - y1 - t * dy)


class Grid:
    def __init__(self, board, net, x0, y0, x1, y1):
        self.x0, self.y0 = x0, y0
        self.nx = int((x1 - x0) / STEP) + 1
        self.ny = int((y1 - y0) / STEP) + 1
        self.layers = (pcbnew.F_Cu, pcbnew.B_Cu)
        # distance to nearest foreign copper per layer (mm), computed lazily per cell
        self.board, self.net = board, net
        self.items = {l: [] for l in self.layers}
        box = (x0 - 3, y0 - 3, x1 + 3, y1 + 3)

        def inside(x, y):
            return box[0] <= x <= box[2] and box[1] <= y <= box[3]
        for t in board.GetTracks():
            if t.GetNetname() == net:
                continue
            if isinstance(t, pcbnew.PCB_VIA):
                x, y = _mm(t.GetPosition().x) - P.OX, _mm(t.GetPosition().y) - P.OY
                if inside(x, y):
                    for l in self.layers:
                        self.items[l].append(("c", x, y, _mm(t.GetWidth()) / 2))
            else:
                a = (_mm(t.GetStart().x) - P.OX, _mm(t.GetStart().y) - P.OY)
                b = (_mm(t.GetEnd().x) - P.OX, _mm(t.GetEnd().y) - P.OY)
                if inside(*a) or inside(*b) or inside((a[0] + b[0]) / 2, (a[1] + b[1]) / 2):
                    if t.GetLayer() in self.items:
                        self.items[t.GetLayer()].append(("s", a[0], a[1], b[0], b[1], _mm(t.GetWidth()) / 2))
        self.smd = []   # every SMD pad, own net included: no via may land on one
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                bb = pad.GetBoundingBox()
                if pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
                    self.smd.append((_mm(bb.GetLeft()) - P.OX, _mm(bb.GetTop()) - P.OY,
                                     _mm(bb.GetRight()) - P.OX, _mm(bb.GetBottom()) - P.OY))
                r = (_mm(bb.GetLeft()) - P.OX, _mm(bb.GetTop()) - P.OY, _mm(bb.GetRight()) - P.OX,
                     _mm(bb.GetBottom()) - P.OY)
                if not (inside(r[0], r[1]) or inside(r[2], r[3])):
                    continue
                same = pad.GetNetname() == net and net != ""
                for l in self.layers:
                    if pad.IsOnLayer(l) and not same:
                        self.items[l].append(("r",) + r)
                    if pad.GetDrillSize().x > 0 and not same:
                        self.items[l].append(("r",) + r)
        self.fills = {l: [] for l in self.layers}
        for z in board.Zones():
            # logic GND pours re-flow around new copper: only the LED power pours block
            if z.GetIsRuleArea() or z.GetNetname() == net or z.GetNetname() == "GND":
                continue
            for l in z.GetLayerSet().Seq():
                if l in self.fills:
                    self.fills[l].append(z.GetFilledPolysList(l))
        self.cache = {}

    def free(self, ix, iy, li, radius):
        key = (ix, iy, li, radius)
        if key in self.cache:
            return self.cache[key]
        x, y = self.x0 + ix * STEP, self.y0 + iy * STEP
        need = radius + CLEAR
        ok = True
        for it in self.items[self.layers[li]]:
            if it[0] == "c":
                d = math.hypot(x - it[1], y - it[2]) - it[3]
            elif it[0] == "s":
                d = _seg_dist(x, y, it[1], it[2], it[3], it[4]) - it[5]
            else:
                dx = max(it[1] - x, 0, x - it[3])
                dy = max(it[2] - y, 0, y - it[4])
                d = math.hypot(dx, dy)
            if d < need:
                ok = False
                break
        if ok:
            v = pcbnew.VECTOR2I(pcbnew.FromMM(x + P.OX), pcbnew.FromMM(y + P.OY))
            for f in self.fills[self.layers[li]]:
                # a point is blocked if foreign pour copper is within `need`
                if f.Contains(v, -1, pcbnew.FromMM(need)):
                    ok = False
                    break
        self.cache[key] = ok
        return ok

    def via_ok(self, ix, iy):
        x, y = self.x0 + ix * STEP, self.y0 + iy * STEP
        if P.in_nc_keepout(x, y, VIA_D / 2):
            return False
        for r in self.smd:
            dx = max(r[0] - x, 0, x - r[2])
            dy = max(r[1] - y, 0, y - r[3])
            if math.hypot(dx, dy) < VIA_D / 2 + 0.15:
                return False
        return True

    def cell(self, x, y):
        return int(round((x - self.x0) / STEP)), int(round((y - self.y0) / STEP))

    def xy(self, ix, iy):
        return self.x0 + ix * STEP, self.y0 + iy * STEP


def route(board, net, a, b, a_layers=(0, 1), b_layers=(0, 1), margin=6.0):
    """Return list of ('track', layer, [(x, y)...]) / ('via', x, y) or None."""
    x0, y0 = min(a[0], b[0]) - margin, min(a[1], b[1]) - margin
    x1, y1 = max(a[0], b[0]) + margin, max(a[1], b[1]) + margin
    g = Grid(board, net, x0, y0, x1, y1)
    rt, rv = TRACK_W / 2, VIA_D / 2
    start = [(g.cell(*a), l) for l in a_layers]
    goal = {(g.cell(*b), l) for l in b_layers}
    gx, gy = g.cell(*b)

    def h(c):
        return math.hypot(c[0][0] - gx, c[0][1] - gy)
    openq = []
    best = {}
    for s in start:
        best[s] = 0.0
        heapq.heappush(openq, (h(s), 0.0, s, None))
    parent = {}
    moves = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
             (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    found = None
    expanded = 0
    while openq and expanded < 400000:
        f, cost, cur, par = heapq.heappop(openq)
        if cur in parent:
            continue
        parent[cur] = par
        expanded += 1
        if cur in goal:
            found = cur
            break
        (ix, iy), li = cur
        near_end = math.hypot(ix - gx, iy - gy) < 8 or (cur in [s for s in start])
        for dx, dy, c in moves:
            nx, ny = ix + dx, iy + dy
            if not (0 <= nx < g.nx and 0 <= ny < g.ny):
                continue
            nxt = ((nx, ny), li)
            endzone = math.hypot(nx - gx, ny - gy) < 4 or math.hypot(nx - start[0][0][0], ny - start[0][0][1]) < 4
            if not endzone and not g.free(nx, ny, li, rt):
                continue
            nc = cost + c
            if nc < best.get(nxt, 1e18):
                best[nxt] = nc
                heapq.heappush(openq, (nc + h(nxt), nc, nxt, cur))
        # via
        other = 1 - li
        if g.free(ix, iy, 0, rv) and g.free(ix, iy, 1, rv) and g.via_ok(ix, iy):
            nxt = ((ix, iy), other)
            nc = cost + 25.0
            if nc < best.get(nxt, 1e18):
                best[nxt] = nc
                heapq.heappush(openq, (nc + h(nxt), nc, nxt, cur))
    if not found:
        return None
    path = []
    c = found
    while c is not None:
        path.append(c)
        c = parent[c]
    path.reverse()
    out, seg, layer = [], [], path[0][1]
    for (ix, iy), l in path:
        if l != layer:
            out.append(("track", g.layers[layer], seg))
            out.append(("via",) + g.xy(ix, iy))
            seg, layer = [], l
        seg.append(g.xy(ix, iy))
    out.append(("track", g.layers[layer], seg))
    # simplify collinear points
    res = []
    for item in out:
        if item[0] != "track":
            res.append(item)
            continue
        pts = item[2]
        simp = [pts[0]]
        for i in range(1, len(pts) - 1):
            (ax, ay), (bx, by), (cx, cy) = simp[-1], pts[i], pts[i + 1]
            if abs((bx - ax) * (cy - by) - (by - ay) * (cx - bx)) > 1e-9:
                simp.append(pts[i])
        simp.append(pts[-1])
        if len(simp) >= 2:
            res.append(("track", item[1], simp))
    # snap endpoints exactly on the requested points
    for item in res:
        if item[0] == "track":
            break
    if res and res[0][0] == "track":
        res[0][2][0] = a
    if res and res[-1][0] == "track":
        res[-1][2][-1] = b
    return res


def apply(board, net, plan):
    for item in plan:
        if item[0] == "track":
            P.add_track(board, net, item[1], TRACK_W, item[2])
        else:
            P.add_via(board, net, item[1], item[2], VIA_D, VIA_DRILL)
