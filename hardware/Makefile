# dmxnow hardware pipeline. Requires KiCad >= 7 (pcbnew Python module + kicad-cli),
# Java 17+ and Freerouting (FREEROUTING_JAR) for the `route` step.
PY ?= python3
BUILD := build

.PHONY: all lib sch project pcb route reimport check drc fab clean vendor

all: lib sch project pcb route check fab

lib:
	$(PY) gen/footprints.py

# Snapshot the KiCad library symbols/footprints used (needs a KiCad install).
vendor:
	$(PY) gen/vendor.py

sch:
	$(PY) gen/sch.py

project:
	$(PY) gen/project.py

# Placement, 230 V / LED power routing and zones. Overwrites any previous routing.
pcb: project
	$(PY) gen/pcb.py

# Low-voltage signals with Freerouting (slow: ~15 min), then the finishing pass
# that closes what the autorouter left (straight links, vias to the pours).
route:
	$(PY) gen/route.py --passes 20
	$(PY) gen/fixup.py

# Re-import the last Freerouting session without routing again (after pcb changes
# that do not move footprints).
reimport:
	$(PY) gen/route.py --ses route/dmxnow.ses
	$(PY) gen/fixup.py

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
