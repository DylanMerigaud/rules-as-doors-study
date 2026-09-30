#!/usr/bin/env python3
"""Table 6: the three preregistered predictions for the prospective part (ANALYSIS.md section 5),
and the field criterion on the door repository drifting back (section 6).

Source: data/transcripts_prospective.csv, one row per part (retrospective, prospective), session
kind and repository group, with the counts of data/transcripts_weekly.csv split at the tagger date
of prereg-v1. Columns read: part, session_kind, repo_group, turn_ends, ends_q_trailing_replied,
ref_stop_promise, ref_stop_promise_continued.

1. Door repository, operator sessions and popped terminals: answered questions ending a turn at or
   below 1 percent of turn ends.
2. Control repositories, same sessions: at or above 2 percent; insufficient below 100 turn ends.
3. Promise Stop hook, every session kind: at least 80 percent of its refusals followed by
   continued work.
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
from common import MAIN_KINDS, add_prop, num, standalone  # noqa: E402
from stats import wilson  # noqa: E402

SRC = "data/transcripts_prospective.csv"
COLUMNS = ("part", "session_kind", "repo_group", "turn_ends", "ends_q_trailing_replied",
           "ref_stop_promise", "ref_stop_promise_continued")
MIN_ENDS = 100


def verdicts(cs):
    """Return a list of (name, k, n, verdict, extra) for the three predictions."""
    door, ctrl, prom = cs["door"], cs["control"], cs["promise"]
    out = []
    n, k = door["turn_ends"], door["ends_q_trailing_replied"]
    if not n:
        v = "no data"
    else:
        v = "met" if k / n <= 0.01 else "failed"
    drift = bool(n) and k / n > 0.02
    out.append(("door", k, n, v, {"drifts_back": drift}))
    n, k = ctrl["turn_ends"], ctrl["ends_q_trailing_replied"]
    if n < MIN_ENDS:
        v = "insufficient"
    else:
        v = "met" if k / n >= 0.02 else "failed"
    out.append(("control", k, n, v, {}))
    n, k = prom["ref_stop_promise"], prom["ref_stop_promise_continued"]
    v = "no refusals" if not n else ("met" if k / n >= 0.8 else "failed")
    out.append(("promise", k, n, v, {}))
    return out


def run(ctx):
    rows = ctx.read_csv("transcripts_prospective.csv", required=COLUMNS)
    reg = ctx.registry
    cs = {"door": Counter(), "control": Counter(), "promise": Counter()}
    for r in rows:
        if r["part"] != "prospective":
            continue
        if r["session_kind"] in MAIN_KINDS and r["repo_group"] in ("door", "control"):
            c = cs[r["repo_group"]]
            c["turn_ends"] += num(r["turn_ends"])
            c["ends_q_trailing_replied"] += num(r["ends_q_trailing_replied"])
        cs["promise"]["ref_stop_promise"] += num(r["ref_stop_promise"])
        cs["promise"]["ref_stop_promise_continued"] += num(r["ref_stop_promise_continued"])
    table = []
    names = {"door": "answered_q", "control": "answered_q", "promise": "continued"}
    for name, k, n, v, extra in verdicts(cs):
        key = "prosp.%s.%s" % (name, names[name])
        add_prop(reg, key, k, n, SRC)
        reg.add("prosp.%s.verdict" % name, v, v, SRC)
        ci = wilson(k, n) if n else (None, None)
        table.append([name, k, n, k / n if n else None, ci[0], ci[1], v])
        if name == "door" and n:
            reg.add("prosp.criterion.door_drifts_back", extra["drifts_back"],
                    "the door repository's share rose above 2 percent in the prospective part"
                    if extra["drifts_back"] else
                    "the door repository's share stayed at or below 2 percent in the prospective part",
                    SRC, k=k, n=n)
    ctx.write_table("table06_prospective.csv",
                    ["prediction", "k", "n", "share", "wilson_lo", "wilson_hi", "verdict"], table)


if __name__ == "__main__":
    sys.exit(standalone(run))
