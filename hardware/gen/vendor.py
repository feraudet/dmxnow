"""Snapshot every KiCad library symbol and footprint used by design.py into
hardware/lib/vendor/, so that generation does not depend on the KiCad version
installed (KiCad 9 renamed or removed some symbols, e.g. Device:Q_NMOS_GDS).

Run once with a KiCad install; the snapshot is committed.
"""
import os
import shutil

import design
from sexp import QStr, dump, find, find_all, parse

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, "..", "lib", "vendor")
SYM_DIR = os.environ.get("KICAD_SYMBOL_DIR", "/usr/share/kicad/symbols")
FP_DIR = os.environ.get("KICAD_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
PROJECT_LIBS = {"Espressif", "dmxnow"}


def vendor_symbols():
    wanted = {}
    for p in design.PARTS:
        lib, name = p.symbol.split(":", 1)
        if lib not in PROJECT_LIBS:
            wanted.setdefault(lib, set()).add(name)
    wanted.setdefault("power", set()).update({"PWR_FLAG"})
    for lib, names in wanted.items():
        root = parse(open(os.path.join(SYM_DIR, lib + ".kicad_sym"), encoding="utf-8").read())
        syms = {str(s[1]): s for s in find_all(root, "symbol")}
        todo, keep = list(names), {}
        while todo:
            n = todo.pop()
            if n in keep:
                continue
            keep[n] = syms[n]
            ext = find(syms[n], "extends")
            if ext is not None:
                todo.append(str(ext[1]))
        out = [x for x in root if not (isinstance(x, list) and x and x[0] == "symbol")]
        out += [keep[n] for n in sorted(keep)]
        with open(os.path.join(VENDOR, lib + ".kicad_sym"), "w", encoding="utf-8") as f:
            f.write(dump(out) + "\n")


def vendor_footprints():
    for p in design.PARTS:
        lib, name = p.footprint.split(":", 1)
        if lib in PROJECT_LIBS:
            continue
        d = os.path.join(VENDOR, lib + ".pretty")
        os.makedirs(d, exist_ok=True)
        shutil.copy(os.path.join(FP_DIR, lib + ".pretty", name + ".kicad_mod"), d)


if __name__ == "__main__":
    shutil.rmtree(VENDOR, ignore_errors=True)
    os.makedirs(VENDOR)
    vendor_symbols()
    vendor_footprints()
    print("vendored into", os.path.normpath(VENDOR))
