#!/usr/bin/env python3
"""Table 5 (RQ2): the ask door against its control. For the door repository and the control
repositories, in the before and the after window, over operator sessions and popped terminals:
turn ends that put a question to the operator and got his answer, over all turn ends (the gated
measure, `ends_q_trailing_replied`), and turn ends with a question mark in their last 400
characters (`ends_q_last400`, a measure that does not depend on the gate). Wilson intervals per
cell; the change in each group with Newcombe's interval. A group with fewer than 100 turn ends in
a window is labelled insufficient for that window. Also the field criterion of ANALYSIS.md
section 6 on the control group (below 2 percent over the full after window).

Source: data/transcripts_weekly.csv.
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
from common import MAIN_KINDS, add_prop, fmt_points, num, standalone, window_of  # noqa: E402
from stats import newcombe, wilson  # noqa: E402
from table04_weekly import load  # noqa: E402

SRC = "data/transcripts_weekly.csv"
MIN_ENDS = 100
MEASURES = (("answered_q", "ends_q_trailing_replied"), ("qmark400", "ends_q_last400"))
CONTROL_FLOOR = 0.02


def cells(rows):
    out = {}
    for r in rows:
        w = window_of(r["week"])
        if w is None or r["session_kind"] not in MAIN_KINDS:
            continue
        c = out.setdefault((r["repo_group"], w), Counter())
        c["turn_ends"] += num(r["turn_ends"])
        for _, col in MEASURES:
            c[col] += num(r[col])
    return out


def run(ctx):
    rows = load(ctx)
    reg = ctx.registry
    cs = cells(rows)
    table = []
    for g in ("door", "control"):
        for m, col in MEASURES:
            for w in ("before", "after"):
                c = cs.get((g, w), Counter())
                n, k = c["turn_ends"], c[col]
                insufficient = n < MIN_ENDS
                ci = wilson(k, n) if n else (None, None)
                table.append([g, m, w, k, n, k / n if n else None, ci[0], ci[1],
                              "insufficient" if insufficient else ""])
                add_prop(reg, "ask.%s.%s.%s" % (g, w, m), k, n, SRC, insufficient=insufficient)
            b, a = cs.get((g, "before"), Counter()), cs.get((g, "after"), Counter())
            nd = newcombe(b[col], b["turn_ends"], a[col], a["turn_ends"])
            if nd:
                d, ci = nd
                key = "ask.%s.diff" % g if m == "answered_q" else "ask.%s.diff.%s" % (g, m)
                reg.add(key, d, fmt_points(d, ci), SRC, ci=ci,
                        ci_method="Newcombe hybrid score 95%, after minus before",
                        text_short="%.1f points" % (100 * d))
                table.append([g, m, "after minus before", None, None, d, ci[0], ci[1], ""])
    ctx.write_table("table05_ask_door.csv",
                    ["group", "measure", "window", "k", "turn_ends", "share", "lo", "hi", "label"],
                    table)
    a = cs.get(("control", "after"), Counter())
    n, k = a["turn_ends"], a["ends_q_trailing_replied"]
    if n:
        dropped = (k / n) < CONTROL_FLOOR
        text = ("the control group's share over the after window is below 2 percent: the ask "
                "door's effect is not claimed" if dropped else
                "the control group's share over the after window is at or above 2 percent")
        if n < MIN_ENDS:
            text += " (insufficient: fewer than %d turn ends)" % MIN_ENDS
        reg.add("ask.criterion.control_drops", dropped, text, SRC, k=k, n=n,
                insufficient=n < MIN_ENDS)


if __name__ == "__main__":
    sys.exit(standalone(run))
