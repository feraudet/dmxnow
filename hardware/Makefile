# dmxnow hardware pipeline. Requires KiCad >= 7 (pcbnew Python module + kicad-cli),
# Java 17+ and Freerouting (FREEROUTING_JAR) for the `route` step.
PY ?= python3
BUILD := build

.PHONY: all lib sch project pcb route check drc fab clean

all: lib sch project pcb route check fab

lib:
	$(PY) gen/footprints.py

sch:
	$(PY) gen/sch.py

project:
	$(PY) gen/project.py

# Placement, 230 V / LED power routing and zones. Overwrites any previous routing.
pcb: project
	$(PY) gen/pcb.py

# Low-voltage signals with Freerouting (slow: several minutes).
route:
	$(PY) gen/route.py --passes 40

check:
	mkdir -p $(BUILD)
	kicad-cli sch export netlist -o $(BUILD)/dmxnow.net dmxnow.kicad_sch
	$(PY) gen/check.py netlist $(BUILD)/dmxnow.net
	$(PY) gen/check.py pcb dmxnow.kicad_pcb
	$(PY) gen/drc.py $(BUILD)/drc.rpt

fab:
	$(PY) gen/fab.py

clean:
	rm -rf $(BUILD) fab
