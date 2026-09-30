#!/usr/bin/env python3
"""Table 11: earlier replays of in-scope cases with and without the whole instruction file, per
case, with Wilson intervals. The model of those runs was not recorded.

Source: data/replays_past.csv (case_id, runs_without, violations_without, runs_with,
violations_with). The difference is the violation share without the file minus with it: positive
means the file moved the replay toward the rule.
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
from common import add_count, num, standalone  # noqa: E402
from stats import wilson  # noqa: E402

SRC = "data/replays_past.csv"
COLUMNS = ("case_id", "runs_without", "violations_without", "runs_with", "violations_with")


def run(ctx):
    rows = ctx.read_csv("replays_past.csv", required=COLUMNS)
    reg = ctx.registry
    table = []
    pos = zero = neg = 0
    for r in sorted(rows, key=lambda r: r["case_id"]):
        nw, kw = num(r["runs_without"]), num(r["violations_without"])
        n1, k1 = num(r["runs_with"]), num(r["violations_with"])
        if not nw or not n1:
            continue
        d = kw / nw - k1 / n1
        pos += d > 0
        zero += d == 0
        neg += d < 0
        cw, c1 = wilson(kw, nw), wilson(k1, n1)
        table.append([r["case_id"], kw, nw, kw / nw, cw[0], cw[1], k1, n1, k1 / n1, c1[0], c1[1], d])
    ctx.write_table("table11_replays.csv",
                    ["case_id", "violations_without", "runs_without", "share_without", "lo_without",
                     "hi_without", "violations_with", "runs_with", "share_with", "lo_with",
                     "hi_with", "difference"], table)
    add_count(reg, "replays.n_cases", len(table), SRC, note="model of the runs not recorded")
    add_count(reg, "replays.n_positive", pos, SRC)
    add_count(reg, "replays.n_zero", zero, SRC)
    add_count(reg, "replays.n_negative", neg, SRC)


if __name__ == "__main__":
    sys.exit(standalone(run))
