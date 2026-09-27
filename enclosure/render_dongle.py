"""Renders of the dongle case (PNG), offscreen VTK: open (XIAO and antenna shown) and closed.

  python3 render_dongle.py      -> out/dongle/assembly_open.png, assembly_closed.png
"""
import os

import dongle_case as D
import render as R


def main():
    os.makedirs(D.OUT, exist_ok=True)
    tray, lid, env = D.tray(), D.lid(), D.parts_envelope()
    R.render([R._actor(tray, R.COLORS["base"]), R._actor(env, R.COLORS["pcb"])],
             os.path.join(D.OUT, "assembly_open.png"), -30, 45)
    R.render([R._actor(tray, R.COLORS["base"]), R._actor(lid, R.COLORS["lid_lv"])],
             os.path.join(D.OUT, "assembly_closed.png"), -30, 35)


if __name__ == "__main__":
    main()
