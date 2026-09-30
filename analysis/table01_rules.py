#!/usr/bin/env python3
"""Table 1: in-scope rules by class, delivery (prose only, door only, both) and enforceability.
Source: data/rules.csv."""
import sys
from collections import Counter
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
# This folder holds numbers.py, which would shadow the standard library's `numbers` module that
# numpy imports: take the folder off the front of the path, load the real module, append it.
if sys.path and str(Path(sys.path[0] or ".").resolve()) == _HERE:
    sys.path.pop(0)
import numbers  # noqa: E402,F401
if _HERE not in sys.path:
    sys.path.append(_HERE)
from common import add_count, add_prop, standalone  # noqa: E402

SRC = "data/rules.csv"
DELIVERY_KEY = {"prose only": "n_prose_only", "door only": "n_door_only", "both": "n_both"}
ENF = ("E-full", "E-partial", "E-none")


def load_rules(ctx):
    return ctx.read_csv("rules.csv", required=("id", "class", "delivery", "enforceability"))


def run(ctx):
    rules = load_rules(ctx)
    reg = ctx.registry
    n = len(rules)
    add_count(reg, "rules.n_in_scope", n, SRC)
    by_delivery = Counter(r["delivery"] for r in rules)
    for d, key in DELIVERY_KEY.items():
        add_prop(reg, "rules." + key, by_delivery.get(d, 0), n, SRC)
    classes = sorted({r["class"] for r in rules})
    rows = []
    for c in classes:
        sub = [r for r in rules if r["class"] == c]
        dc = Counter(r["delivery"] for r in sub)
        ec = Counter(r["enforceability"] for r in sub)
        rows.append([c, len(sub)] + [dc.get(d, 0) for d in DELIVERY_KEY] + [ec.get(e, 0) for e in ENF])
        add_count(reg, "rules.class.%s" % c, len(sub), SRC)
    dc = Counter(r["delivery"] for r in rules)
    ec = Counter(r["enforceability"] for r in rules)
    rows.append(["all", n] + [dc.get(d, 0) for d in DELIVERY_KEY] + [ec.get(e, 0) for e in ENF])
    ctx.write_table("table01_rules.csv", ["class", "rules"] + list(DELIVERY_KEY) + list(ENF), rows)


if __name__ == "__main__":
    sys.exit(standalone(run))
