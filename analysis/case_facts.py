#!/usr/bin/env python3
"""Facts of the case measured outside this package's tables (repository size, the rule
inventory's coder agreement, the correction probe of 2026-09-01, the disclosure counts), each
computed by the extraction that owns its source and published as one row of data/case_facts.csv:
key, value, text, source, k, n, ci_low, ci_high (empty cells for what does not apply). This script
copies each row into the registry unchanged, with the row's own source named.
"""
import sys
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
# This folder holds numbers.py, which would shadow the standard library's `numbers` module that
# numpy imports: take the folder off the front of the path, load the real module, append it.
if sys.path and str(Path(sys.path[0] or ".").resolve()) == _HERE:
    sys.path.pop(0)
import numbers  # noqa: E402,F401
if _HERE not in sys.path:
    sys.path.append(_HERE)
from common import num, standalone  # noqa: E402

COLUMNS = ("key", "value", "text", "source", "k", "n", "ci_low", "ci_high")


def run(ctx):
    rows = ctx.read_csv("case_facts.csv", required=COLUMNS)
    reg = ctx.registry
    for r in sorted(rows, key=lambda r: r["key"]):
        v = r["value"]
        try:
            v = num(v, None)
        except ValueError:
            pass
        ci = (float(r["ci_low"]), float(r["ci_high"])) if r["ci_low"] and r["ci_high"] else None
        reg.add(r["key"], v, r["text"], "data/case_facts.csv (%s)" % r["source"],
                k=num(r["k"], None), n=num(r["n"], None), ci=ci)


if __name__ == "__main__":
    sys.exit(standalone(run))
