# dmxnow enclosure (SPEC 4.12). Requires CadQuery (pip install -r requirements.txt);
# renders need an offscreen OpenGL (libosmesa6 or EGL).
PY ?= python3

.PHONY: all check export render board

all: export render

check:
	$(PY) enclosure.py --check-only

export:
	$(PY) enclosure.py

render:
	$(PY) render.py full
	$(PY) render.py cut

# regenerate board.json from the PCB (needs KiCad's pcbnew)
board:
	cd ../hardware/gen && $(PY) export_board.py
