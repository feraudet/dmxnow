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

FREEROUTING = os.environ.get("FREEROUTING_JAR", "/opt/freerouting/freerouting.jar")


def prepare_dsn(dsn_path):
    board = P.build(for_routing=True)
    for t in board.GetTracks():
        t.SetLocked(True)
    if not pcbnew.ExportSpecctraDSN(board, dsn_path):
        raise SystemExit("DSN export failed")


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


def main():
    passes = 30
    if "--passes" in sys.argv:
        passes = int(sys.argv[sys.argv.index("--passes") + 1])
    work = os.path.join(P.HW, "build", "route")
    os.makedirs(work, exist_ok=True)
    dsn, ses = os.path.join(work, "dmxnow.dsn"), os.path.join(work, "dmxnow.ses")
    prepare_dsn(dsn)
    run_freerouting(dsn, ses, passes)
    board = pcbnew.LoadBoard(P.PCB)
    w, v = import_ses(board, ses)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(P.PCB)
    print("imported %d track segments, %d vias" % (w, v))


if __name__ == "__main__":
    main()
