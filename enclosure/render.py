"""Assembly renders (PNG) of the enclosure with the PCB envelope, offscreen VTK.

  python3 render.py [full|cut]      -> out/<variant>/assembly_closed.png, assembly_open.png
"""
import os
import sys
import tempfile

import cadquery as cq
import vtk

import enclosure as E

COLORS = {"base": (0.85, 0.85, 0.82), "cover_230v": (0.95, 0.55, 0.15), "lid_lv": (0.55, 0.62, 0.72),
          "pcb": (0.1, 0.45, 0.2), "parts": (0.25, 0.25, 0.28), "clamp": (0.95, 0.55, 0.15)}


def _actor(shape, color, opacity=1.0):
    fd, path = tempfile.mkstemp(suffix=".stl")
    os.close(fd)
    cq.exporters.export(shape, path, tolerance=0.1, angularTolerance=0.3)
    r = vtk.vtkSTLReader()
    r.SetFileName(path)
    r.Update()
    os.remove(path)
    m = vtk.vtkPolyDataMapper()
    m.SetInputConnection(r.GetOutputPort())
    a = vtk.vtkActor()
    a.SetMapper(m)
    a.GetProperty().SetColor(*color)
    a.GetProperty().SetOpacity(opacity)
    return a


def render(actors, path, az, el):
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    for a in actors:
        ren.AddActor(a)
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetSize(1600, 1000)
    win.AddRenderer(ren)
    cam = ren.GetActiveCamera()
    ren.ResetCamera()
    cam.Azimuth(az)
    cam.Elevation(el)
    ren.ResetCamera()
    cam.Zoom(1.3)
    win.Render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(win)
    w2i.Update()
    wr = vtk.vtkPNGWriter()
    wr.SetFileName(path)
    wr.SetInputConnection(w2i.GetOutputPort())
    wr.Write()
    print("written", path)


def main():
    variant = sys.argv[1] if len(sys.argv) > 1 else "full"
    d = os.path.join(E.OUT, variant)
    os.makedirs(d, exist_ok=True)
    base = E.base(variant)
    cover = E.cover_230v(variant)
    lid = E.lid_lv(variant)
    pcb = E.board_solid(variant)
    parts = None
    for _, b in E.part_boxes(variant):
        parts = b if parts is None else parts.union(b)
    common = [_actor(base, COLORS["base"]), _actor(pcb, COLORS["pcb"]), _actor(parts, COLORS["parts"])]
    for i, (name, wall, pos, z, dia, _) in enumerate(E.GLANDS[:3]):
        bar = E.clamp_bar().translate((E.X_IN_L + E.NUT_T, E.Y(pos), 15.0 + E.CABLE_D / 2 - 1.2))
        common.append(_actor(bar, COLORS["clamp"]))
    render(common + [_actor(cover, COLORS["cover_230v"]), _actor(lid, COLORS["lid_lv"])],
           os.path.join(d, "assembly_closed.png"), -35, 35)
    render(common, os.path.join(d, "assembly_open.png"), -35, 50)


if __name__ == "__main__":
    main()
