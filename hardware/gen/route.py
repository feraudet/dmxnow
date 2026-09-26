"""Route the low-voltage signal nets with Freerouting and import the result.

1. copy the board, lock every existing track (230 V and LED power are scripted
   in pcb.py and must not be touched), replace the V-cut keep-out (footprints
   only, but Specctra would treat it as a routing barrier) by a routing keep-out
   covering the 230 V zone + 6 mm;
2. export Specctra DSN, run Freerouting headless;
3. parse the SES file and add wires / vias to the real board, fill zones.

Usage: python3 route.py [--passes N]
"""
import os
import re
import subprocess
import sys

import pcbnew

import pcb as P
from sexp import find, find_all, parse

import design

# Nets routed by pcb.py (230 V, LED power): never take router output for them
SCRIPTED_NETS = set(design.MAINS_NETS) | set(design.NETCLASSES["LED_PWR"]["nets"])

FREEROUTING = os.environ.get("FREEROUTING_JAR", "/opt/freerouting/freerouting.jar")


def prepare_dsn(dsn_path):
    # separate process: pcbnew does not cope with a NewBoard() and a LoadBoard()
    # of the same file in one interpreter (the second board comes back empty)
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pcb.py"),
                    "--dsn", dsn_path], check=True)


def run_freerouting(dsn, ses, passes):
    cmd = ["java", "-jar", FREEROUTING, "-de", dsn, "-do", ses, "-mp", str(passes),
           "--gui.enabled=false", "-dct", "0"]
    print(" ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    tail = "\n".join((r.stdout + r.stderr).splitlines()[-15:])
    print(tail)
    if not os.path.exists(ses):
        raise SystemExit("Freerouting produced no session file")


def import_ses(board, ses_path):
    root = parse(open(ses_path).read())
    routes = find(root, "routes")
    res = find(routes, "resolution")
    scale = {"um": 1e-3, "mm": 1.0, "mil": 0.0254, "inch": 25.4}[str(res[1])] / float(res[2])
    layer_ids = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}
    vias = {}
    lib = find(routes, "library_out")
    for ps in find_all(lib, "padstack") if lib else []:
        name = str(ps[1])
        m = re.search(r"_(\d+):(\d+)_um", name)
        if m:
            vias[name] = (int(m.group(1)) / 1000.0, int(m.group(2)) / 1000.0)
    n_wires = n_vias = 0
    for net in find_all(find(routes, "network_out"), "net"):
        netname = str(net[1])
        if netname in SCRIPTED_NETS:
            continue   # fully routed by pcb.py (tracks + pours): ignore router additions
        ni = board.FindNet(netname)
        for w in find_all(net, "wire"):
            if find(w, "type") is not None and str(find(w, "type")[1]) in ("fix", "protect"):
                continue
            path = find(w, "path")
            layer, width = layer_ids[str(path[1])], float(path[2]) * scale
            coords = [float(v) * scale for v in path[3:]]
            pts = list(zip(coords[0::2], coords[1::2]))
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                tr = pcbnew.PCB_TRACK(board)
                tr.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(-y1)))
                tr.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(-y2)))
                tr.SetWidth(pcbnew.FromMM(width))
                tr.SetLayer(layer)
                tr.SetNet(ni)
                board.Add(tr)
                n_wires += 1
        for v in find_all(net, "via"):
            if find(v, "type") is not None and str(find(v, "type")[1]) in ("fix", "protect"):
                continue
            dia, drill = vias.get(str(v[1]), (0.6, 0.3))
            x, y = float(v[2]) * scale, float(v[3]) * scale
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(-y)))
            via.SetWidth(pcbnew.FromMM(dia))
            via.SetDrill(pcbnew.FromMM(drill))
            via.SetNet(ni)
            board.Add(via)
            n_vias += 1
    return n_wires, n_vias


def _seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L))
    return ((px - x1 - t * dx) ** 2 + (py - y1 - t * dy) ** 2) ** 0.5


def _obstacles(board):
    mm = pcbnew.ToMM
    ox, oy = P.OX, P.OY
    segs, circles, boxes = [], [], []
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            circles.append((mm(t.GetPosition().x) - ox, mm(t.GetPosition().y) - oy,
                            mm(t.GetWidth()) / 2, t.GetNetname()))
        else:
            segs.append((mm(t.GetStart().x) - ox, mm(t.GetStart().y) - oy, mm(t.GetEnd().x) - ox,
                         mm(t.GetEnd().y) - oy, mm(t.GetWidth()) / 2, t.GetNetname()))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            boxes.append((mm(bb.GetLeft()) - ox, mm(bb.GetTop()) - oy, mm(bb.GetRight()) - ox,
                          mm(bb.GetBottom()) - oy, pad.GetNetname(), pad))
    return segs, circles, boxes


def _free(x, y, r, segs, circles, boxes, net, margin=0.35, ignore_pad=None):
    for s in segs:
        if s[5] != net and _seg_dist(x, y, *s[:4]) <= s[4] + r + margin:
            return False
    for c in circles:
        if ((x - c[0]) ** 2 + (y - c[1]) ** 2) ** 0.5 <= c[2] + r + max(margin, 0.45):
            return False
    for b in boxes:
        if b[5] is ignore_pad:
            continue
        g = margin if b[4] != net else 0.2
        if b[0] - r - g < x < b[2] + r + g and b[1] - r - g < y < b[3] + r + g:
            return False
    return True


def escape_vias(board, net="GND"):
    """Give every SMD pad of `net` its own via to the other layer's pour."""
    segs, circles, boxes = _obstacles(board)
    n = 0
    for b in boxes:
        pad = b[5]
        if b[4] != net or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
            continue
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if not (P.LV_MIN_X < cx < P.VCUT - P.VCUT_KEEP or P.VCUT + P.VCUT_KEEP < cx < 112.8):
            continue
        if cx > 79.0 and cy < 7.5:
            continue
        half = max(b[2] - b[0], b[3] - b[1]) / 2
        done = False
        for dist in (half + 0.7, half + 1.1, half + 1.6):
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0), (0.7, 0.7), (-0.7, 0.7), (0.7, -0.7), (-0.7, -0.7)):
                x, y = cx + dx * dist, cy + dy * dist
                if _free(x, y, 0.3, segs, circles, boxes, net, ignore_pad=pad) and \
                        all(_seg_dist(px, py, cx, cy, x, y) > 0.2 + 0.35 + (bb[2] - bb[0]) / 2
                            for bb in boxes if bb[4] != net
                            for px, py in [((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)]) and \
                        all(s[5] == net or _seg_dist((cx + x) / 2, (cy + y) / 2, *s[:4]) > s[4] + 0.2 + 0.35
                            for s in segs):
                    P.add_track(board, net, pcbnew.F_Cu, 0.3, [(cx, cy), (x, y)])
                    P.add_via(board, net, x, y, 0.6, 0.3)
                    circles.append((x, y, 0.3, net))
                    segs.append((cx, cy, x, y, 0.15, net))
                    n += 1
                    done = True
                    break
            if done:
                break
    return n


def stitch_gnd(board, pitch=1.8, dia=0.6, drill=0.3, margin=0.35):
    """Add GND vias on a grid in the low-voltage area wherever they clear everything,
    so that the top and bottom GND pours form one piece."""
    mm = pcbnew.ToMM
    ox, oy = P.OX, P.OY
    obstacles = []   # (kind, geometry..., net)
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            obstacles.append(("c", mm(t.GetPosition().x) - ox, mm(t.GetPosition().y) - oy,
                              mm(t.GetWidth()) / 2, t.GetNetname()))
        else:
            obstacles.append(("s", mm(t.GetStart().x) - ox, mm(t.GetStart().y) - oy,
                              mm(t.GetEnd().x) - ox, mm(t.GetEnd().y) - oy, mm(t.GetWidth()) / 2,
                              t.GetNetname()))
    boxes = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            boxes.append((mm(bb.GetLeft()) - ox, mm(bb.GetTop()) - oy, mm(bb.GetRight()) - ox,
                          mm(bb.GetBottom()) - oy, pad.GetNetname(), pad.GetDrillSize().x > 0))
    r = dia / 2
    added = []
    y = 1.5
    while y < P.H - 1.0:
        x = P.LV_MIN_X + 1.5
        while x < 112.6:
            if P.VCUT - P.VCUT_KEEP - 0.5 <= x <= P.VCUT + P.VCUT_KEEP + 0.5:
                x += pitch        # no stitching in the V-cut band
                continue
            ok = not (x > 79.0 and y < 7.5)            # antenna keep-out
            ok = ok and not (x > P.VCUT and y > 43.8)  # strip: logic GND pour ends at y=44.3
            for b in boxes:
                if not ok:
                    break
                gap = 0.5 if (b[4] == "GND" and not b[5]) else margin
                if b[0] - r - gap < x < b[2] + r + gap and b[1] - r - gap < y < b[3] + r + gap:
                    ok = False
            for o in obstacles:
                if not ok:
                    break
                if o[0] == "c":
                    ok = ((x - o[1]) ** 2 + (y - o[2]) ** 2) ** 0.5 > o[3] + r + max(margin, 0.5)
                else:
                    ok = o[6] == "GND" or _seg_dist(x, y, *o[1:5]) > o[5] + r + margin
            for ax, ay in added:
                if not ok:
                    break
                ok = ((x - ax) ** 2 + (y - ay) ** 2) ** 0.5 > 1.5
            if ok:
                P.add_via(board, "GND", x, y, dia, drill)
                added.append((x, y))
            x += pitch
        y += pitch
    return len(added)


def main():
    passes = 30
    if "--passes" in sys.argv:
        passes = int(sys.argv[sys.argv.index("--passes") + 1])
    work = os.path.join(P.HW, "build", "route")
    os.makedirs(work, exist_ok=True)
    dsn, ses = os.path.join(work, "dmxnow.dsn"), os.path.join(work, "dmxnow.ses")
    if "--ses" in sys.argv:
        ses = sys.argv[sys.argv.index("--ses") + 1]   # re-import an existing session
    else:
        prepare_dsn(dsn)
        run_freerouting(dsn, ses, passes)
        # keep the session in the repository: `make reimport` rebuilds the board from it
        import shutil
        os.makedirs(os.path.join(P.HW, "route"), exist_ok=True)
        shutil.copy(ses, os.path.join(P.HW, "route", "dmxnow.ses"))
    board = pcbnew.LoadBoard(P.PCB)
    w, v = import_ses(board, ses)
    e = escape_vias(board)
    print("GND escape vias:", e)
    n = stitch_gnd(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    print("GND stitching vias:", n)
    board.Save(P.PCB)
    print("imported %d track segments, %d vias" % (w, v))


if __name__ == "__main__":
    main()
