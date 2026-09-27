# dmxnow enclosure (SPEC 4.12) and dongle case (SPEC 4.10). Requires CadQuery
# (pip install -r requirements.txt); renders need an offscreen OpenGL (libosmesa6 or EGL).
PY ?= python3

.PHONY: all check export render board

all: export render

check:
	$(PY) enclosure.py --check-only
	$(PY) dongle_case.py --check-only

export:
	$(PY) enclosure.py
	$(PY) dongle_case.py

render:
	$(PY) render.py full
	$(PY) render.py cut
	$(PY) render_dongle.py

# regenerate board.json from the PCB (needs KiCad's pcbnew)
board:
	cd ../hardware/gen && $(PY) export_board.py
