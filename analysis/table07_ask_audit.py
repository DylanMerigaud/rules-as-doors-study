#!/usr/bin/env python3
"""Table 7: the 2026-09-21 ask audit replicated with the codebook of ANALYSIS.md section 7, by two
independent coders (model-coded), on the before and the after window: asks per class, the
avoidable share (avoidable over only-him plus avoidable, on the resolved code) with its Wilson
interval, and Cohen's kappa of the two original codes with a bootstrap interval over items.

Source: data/ask_audit.csv, one row per ask: window (before, after), week, coder1, coder2, final
(codes: only-him, avoidable, not-an-ask; final is the third pass where the two disagree).
"""
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
from stats import kappa_bootstrap, wilson  # noqa: E402

SRC = "data/ask_audit.csv"
COLUMNS = ("window", "week", "coder1", "coder2", "final")
CODES = ("only-him", "avoidable", "not-an-ask")
KAPPA_FLOOR = 0.6


def add_kappa(reg, key, a, b, source):
    kb = kappa_bootstrap(a, b)
    if kb is None:
        reg.add(key, None, "undefined (one label only)", source, n=len(a))
        return None
    k, ci = kb
    reg.add(key, k, "%.2f (%.2f to %.2f)" % (k, ci[0], ci[1]), source, n=len(a), ci=ci,
            ci_method="bootstrap over items, 95% percentile", label="model-coded",
            below_0_6=k < KAPPA_FLOOR, text_short="%.2f" % k)
    return k


def run(ctx):
    rows = ctx.read_csv("ask_audit.csv", required=COLUMNS)
    bad = sorted({r[c] for r in rows for c in ("coder1", "coder2", "final")} - set(CODES))
    if bad:
        raise ValueError("data/ask_audit.csv carries unknown codes: %s" % ", ".join(bad))
    reg = ctx.registry
    table = []
    for w in ("before", "after"):
        sub = [r for r in rows if r["window"] == w]
        c = Counter(r["final"] for r in sub)
        add_count(reg, "audit.%s.n_asks" % w, len(sub), SRC)
        for code in CODES:
            add_count(reg, "audit.%s.n_%s" % (w, code.replace("-", "_")), c[code], SRC)
        n = c["only-him"] + c["avoidable"]
        add_prop(reg, "audit.%s.avoidable" % w, c["avoidable"], n, SRC, label="model-coded")
        ci = wilson(c["avoidable"], n) if n else (None, None)
        table.append([w, len(sub)] + [c[x] for x in CODES] +
                     [c["avoidable"] / n if n else None, ci[0], ci[1]])
    ctx.write_table("table07_ask_audit.csv",
                    ["window", "asks"] + list(CODES) + ["avoidable_share", "lo", "hi"], table)
    add_kappa(reg, "audit.kappa", [r["coder1"] for r in rows], [r["coder2"] for r in rows], SRC)


if __name__ == "__main__":
    sys.exit(standalone(run))
