#!/usr/bin/env python3
"""Checks that every relative link and image of docs/*.md points to an existing file."""
import os
import re
import sys

DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
bad = 0
for name in sorted(os.listdir(DOCS)):
    if not name.endswith(".md"):
        continue
    text = open(os.path.join(DOCS, name), encoding="utf-8").read()
    for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        if not os.path.exists(os.path.normpath(os.path.join(DOCS, target))):
            print(f"{name}: broken link {target}")
            bad += 1
print("links OK" if not bad else f"{bad} broken link(s)")
sys.exit(1 if bad else 0)
