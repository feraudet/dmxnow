"""Minimal S-expression reader/writer for KiCad files.

Atoms are kept as Python str; quoted strings are wrapped in QStr so that the
writer can quote them back. Lists are Python lists.
"""
import re

class QStr(str):
    """A quoted string atom."""

_TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


def parse(text):
    stack = [[]]
    pos = 0
    n = len(text)
    while pos < n:
        m = _TOKEN.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ValueError("parse error at %d: %r" % (pos, text[pos:pos + 40]))
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            done = stack.pop()
            stack[-1].append(done)
        elif m.group(3) is not None:
            stack[-1].append(QStr(m.group(3).replace('\\"', '"').replace("\\\\", "\\")))
        else:
            stack[-1].append(m.group(4))
    if len(stack) != 1:
        raise ValueError("unbalanced parentheses")
    return stack[0][0] if len(stack[0]) == 1 else stack[0]


def _atom(a):
    if isinstance(a, QStr):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(a, bool):
        return "yes" if a else "no"
    if isinstance(a, float):
        s = ("%.6f" % a).rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(a)


def dump(node, indent=0):
    if not isinstance(node, list):
        return _atom(node)
    if all(not isinstance(x, list) for x in node):
        return "(" + " ".join(_atom(x) for x in node) + ")"
    pad = "  " * (indent + 1)
    parts = []
    line = "(" + " ".join(_atom(x) for x in node if not isinstance(x, list))
    # keep leading atoms on the first line, sub-lists below
    head = []
    rest = []
    for x in node:
        (rest if (isinstance(x, list) or rest) else head).append(x)
    line = "(" + " ".join(_atom(x) for x in head)
    for x in rest:
        parts.append(pad + dump(x, indent + 1))
    return line + "\n" + "\n".join(parts) + "\n" + "  " * indent + ")"


def find(node, key):
    """First direct child list whose head is key."""
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def find_all(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]
