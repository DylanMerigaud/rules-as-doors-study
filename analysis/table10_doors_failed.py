#!/usr/bin/env python3
"""Table 10: doors that failed. The long-dash Stop hook's detections against the ones followed by
a new closing text (operator sessions and popped terminals, both repository groups), split at the
week of its repair (2026-09-30, ANALYSIS.md section 9: weeks before the one starting 09-28 are the
inert door, that week mixes both); the long-dash write door's denials; the bypasses each door
carries and the doors that write no ledger.

Sources: data/transcripts_weekly.csv (dash_stop_detected, dash_stop_continued, ref_ptu_dash_write;
optional dash_stop_still_violating and write_calls), data/door_size.csv (optional columns
has_bypass and writes_ledger).
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
from common import MAIN_KINDS, Missing, add_count, add_prop, in_series, num, standalone  # noqa: E402
from table04_weekly import load  # noqa: E402

REPAIR_WEEK = "2026-09-28"


def run(ctx):
    parts = 0
    if ctx.has_data("transcripts_weekly.csv"):
        dash(ctx)
        parts += 1
    else:
        ctx.note("table 10: data/transcripts_weekly.csv not found, long-dash part skipped")
    if ctx.has_data("door_size.csv"):
        parts += bypass(ctx)
    else:
        ctx.note("table 10: data/door_size.csv not found, bypass and ledger part skipped")
    if not parts:
        raise Missing("data/transcripts_weekly.csv and data/door_size.csv not found")


def dash(ctx):
    rows = [r for r in load(ctx) if in_series(r["week"])]
    reg = ctx.registry
    src = "data/transcripts_weekly.csv"
    eras = {"inert": Counter(), "repair_week_and_after": Counter()}
    write = Counter()
    for r in rows:
        if r["session_kind"] in MAIN_KINDS:
            era = "inert" if r["week"] < REPAIR_WEEK else "repair_week_and_after"
            for c in ("dash_stop_detected", "dash_stop_continued", "dash_stop_still_violating"):
                eras[era][c] += num(r.get(c))
            eras[era]["has_still"] += 1 if "dash_stop_still_violating" in r else 0
        write["denials"] += num(r["ref_ptu_dash_write"])
        write["write_calls"] += num(r.get("write_calls"))
        write["has_calls"] += 1 if "write_calls" in r else 0
    table = []
    for era, c in eras.items():
        base = "dashstop" if era == "inert" else "dashstop.%s" % era
        add_count(reg, base + ".blocks", c["dash_stop_detected"], src,
                  note="detections the hook reported as a block, main sessions")
        add_prop(reg, base + ".followed", c["dash_stop_continued"], c["dash_stop_detected"], src,
                 note="followed by a new closing text before the next operator turn")
        if c["has_still"]:
            add_prop(reg, base + ".still_violating", c["dash_stop_still_violating"],
                     c["dash_stop_continued"], src)
        table.append([era, c["dash_stop_detected"], c["dash_stop_continued"],
                      c["dash_stop_still_violating"] if c["has_still"] else None])
    add_count(reg, "dashwrite.denials", write["denials"], src, note="all session kinds")
    if write["has_calls"] and write["write_calls"]:
        add_prop(reg, "dashwrite.rate", write["denials"], write["write_calls"], src, digits=2)
        add_count(reg, "dashwrite.write_calls", write["write_calls"], src)
    else:
        ctx.note("table 10: no write_calls column, dashwrite.write_calls not produced")
    ctx.write_table("table10_dash_stop.csv", ["era", "blocks", "followed", "still_violating"], table)


def bypass(ctx):
    rows = ctx.read_csv("door_size.csv", required=("rule_id", "door_type"))
    reg = ctx.registry
    src = "data/door_size.csv"
    n = 0
    if rows and "has_bypass" in rows[0]:
        add_prop(reg, "doors.n_with_bypass", sum(1 for r in rows if num(r["has_bypass"])), len(rows),
                 src, unit="doors")
        n = 1
    if rows and "writes_ledger" in rows[0]:
        add_prop(reg, "doors.n_no_ledger", sum(1 for r in rows if not num(r["writes_ledger"])),
                 len(rows), src, unit="doors")
        n = 1
    if not n:
        ctx.note("table 10: data/door_size.csv has no has_bypass or writes_ledger column")
    return n


if __name__ == "__main__":
    sys.exit(standalone(run))
