"""Consistency checks between design.py, the schematic and the PCB.

  python3 check.py netlist <file.net>   compare KiCad-exported netlist with design.py
"""
import sys

import design
from sexp import find, find_all, parse


def netlist_from_kicad(path):
    root = parse(open(path, encoding="utf-8").read())
    res = {}
    for net in find_all(find(root, "nets"), "net"):
        name = str(find(net, "name")[1]).lstrip("/")
        nodes = sorted((str(find(n, "ref")[1]), str(find(n, "pin")[1])) for n in find_all(net, "node"))
        if name.startswith("unconnected-") or name.startswith("Net-("):
            # a single-pin net on a no-connect pin
            if len(nodes) == 1:
                continue
        res[name] = nodes
    return res


def check_netlist(path):
    got = netlist_from_kicad(path)
    want = design.nets()
    errors = []
    for n in sorted(set(want) | set(got)):
        if want.get(n) != got.get(n):
            errors.append("net %s: design=%s schematic=%s" % (n, want.get(n), got.get(n)))
    for e in errors:
        print("ERROR", e)
    print("netlist check: %d nets, %d errors" % (len(want), len(errors)))
    return not errors


if __name__ == "__main__":
    if sys.argv[1] == "netlist":
        sys.exit(0 if check_netlist(sys.argv[2]) else 1)
