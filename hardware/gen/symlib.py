"""Load KiCad symbol libraries, flatten derived symbols, normalise to KiCad 7 syntax."""
import copy
import os

from sexp import QStr, find, find_all, parse

KICAD_SYMBOL_DIR = os.environ.get("KICAD_SYMBOL_DIR", "/usr/share/kicad/symbols")
HERE = os.path.dirname(os.path.abspath(__file__))
EXTRA_LIBS = {
    "Espressif": os.environ.get(
        "ESPRESSIF_SYMBOLS",
        os.path.join(HERE, "..", "lib", "Espressif.kicad_sym")),
    "dmxnow": os.path.join(HERE, "..", "lib", "dmxnow.kicad_sym"),
}

# Tokens introduced after KiCad 7 that KiCad 7 cannot read.
_DROP = {"exclude_from_sim", "in_pos_files", "duplicate_pin_numbers_are_jumpers",
         "show_name", "do_not_autoplace", "embedded_fonts", "embedded_files"}

_cache = {}


def _lib_path(lib):
    if lib in EXTRA_LIBS:
        return EXTRA_LIBS[lib]
    return os.path.join(KICAD_SYMBOL_DIR, lib + ".kicad_sym")


def load(lib):
    if lib not in _cache:
        root = parse(open(_lib_path(lib), encoding="utf-8").read())
        _cache[lib] = {str(s[1]): s for s in find_all(root, "symbol")}
    return _cache[lib]


def _to_kicad7(node):
    """Recursively rewrite newer syntax into KiCad 7 syntax."""
    if not isinstance(node, list):
        return node
    out = []
    hide = False
    for x in node:
        if isinstance(x, list) and x:
            if x[0] in _DROP:
                continue
            if x[0] == "hide" and len(x) == 2:
                hide = x[1] == "yes"
                continue
        out.append(_to_kicad7(x))
    if hide and out and out[0] == "pin":
        # KiCad 7: hidden pins carry a bare 'hide' atom after (length ...)
        idx = next(i for i, x in enumerate(out) if isinstance(x, list) and x[0] == "length")
        out.insert(idx + 1, "hide")
    elif hide:
        eff = find(out, "effects")
        if eff is None:
            eff = ["effects", ["font", ["size", "1.27", "1.27"]]]
            out.append(eff)
        if "hide" not in eff:
            eff.append("hide")
    return out


def get(lib_id):
    """Return a flattened copy of symbol 'Lib:Name', named 'Lib:Name'."""
    lib, name = lib_id.split(":", 1)
    syms = load(lib)
    sym = copy.deepcopy(syms[name])
    ext = find(sym, "extends")
    if ext is not None:
        parent = get(lib + ":" + str(ext[1]))
        pname = str(ext[1])
        child_props = {str(p[1]): p for p in find_all(sym, "property")}
        flat = [parent[0], QStr(lib_id)]
        for x in parent[2:]:
            if isinstance(x, list) and x[0] == "property" and str(x[1]) in child_props:
                flat.append(child_props.pop(str(x[1])))
            elif isinstance(x, list) and x[0] == "symbol":
                sub = copy.deepcopy(x)
                sub[1] = QStr(str(sub[1]).replace(pname, name, 1))
                flat.append(sub)
            else:
                flat.append(x)
        # properties only present in the child
        idx = max(i for i, x in enumerate(flat) if isinstance(x, list) and x[0] == "property")
        for p in child_props.values():
            idx += 1
            flat.insert(idx, p)
        sym = flat
    else:
        sym[1] = QStr(lib_id)
    return _to_kicad7(sym)


def pins(sym):
    """[(number, name, type, x, y, angle, unit)] for a flattened symbol."""
    res = []
    for sub in find_all(sym, "symbol"):
        unit = int(str(sub[1]).rsplit("_", 2)[-2])
        for p in find_all(sub, "pin"):
            at = find(p, "at")
            res.append((str(find(p, "number")[1]), str(find(p, "name")[1]), str(p[1]),
                        float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0, unit))
    return res
