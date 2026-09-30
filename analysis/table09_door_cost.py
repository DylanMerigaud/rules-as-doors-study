#!/usr/bin/env python3
"""Table 9 (RQ2): what a door costs, per door (keyed by the rule id it enforces).

Parts, each read from its own file and skipped with a note when that file is absent:
- refusals and the share that took effect: data/door_refusals_weekly.csv (week, rule_id,
  door_type, refusals, took_effect, did_not, cannot_judge; optional recovery_n, recovery_turns,
  recovery_output_tokens: the number of refusals followed by an accepted action and the sums of
  assistant turns and output tokens spent between each such refusal and that action);
- the share of refusals a second look calls wrong, on the stratified sample (up to 20 refusals per
  door, two coders, model-coded): data/door_review.csv (rule_id, stratum, coder1, coder2, final;
  codes right, wrong, unclear); wrong share = wrong over right plus wrong on the final code;
  kappa on the two original codes, all doors pooled;
- lines of code and tests: data/door_size.csv (rule_id, door_type, code_lines, test_lines,
  n_tests; optional has_bypass, writes_ledger as 0 or 1).
"""
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
# This folder holds numbers.py, which would shadow the standard library's `numbers` module that
# numpy imports: take the folder off the front of the path, load the real module, append it.
if sys.path and str(Path(sys.path[0] or ".").resolve()) == _HERE:
    sys.path.pop(0)
import numbers  # noqa: E402,F401
if _HERE not in sys.path:
    sys.path.append(_HERE)
from common import Missing, add_count, add_prop, in_series, num, standalone  # noqa: E402
from table07_ask_audit import add_kappa  # noqa: E402

REF = "door_refusals_weekly.csv"
REV = "door_review.csv"
SIZE = "door_size.csv"
REF_COLUMNS = ("week", "rule_id", "door_type", "refusals", "took_effect", "did_not", "cannot_judge")
REV_COLUMNS = ("rule_id", "stratum", "coder1", "coder2", "final")
SIZE_COLUMNS = ("rule_id", "door_type", "code_lines", "test_lines", "n_tests")
REVIEW_CODES = ("right", "wrong", "unclear")


def run(ctx):
    parts = 0
    for name, fn in ((REF, refusals), (REV, review), (SIZE, size)):
        if ctx.has_data(name):
            fn(ctx)
            parts += 1
        else:
            ctx.note("table 9: data/%s not found, its part skipped" % name)
    if not parts:
        raise Missing("none of data/%s, data/%s, data/%s found" % (REF, REV, SIZE))


def refusals(ctx):
    rows = [r for r in ctx.read_csv(REF, required=REF_COLUMNS) if in_series(r["week"])]
    reg = ctx.registry
    src = "data/" + REF
    agg = OrderedDict()
    for r in sorted(rows, key=lambda r: (r["rule_id"], r["week"], r["door_type"])):
        a = agg.setdefault(r["rule_id"], Counter())
        for c in ("refusals", "took_effect", "did_not", "cannot_judge", "recovery_n",
                  "recovery_turns", "recovery_output_tokens"):
            a[c] += num(r.get(c))
    table = []
    for rid, a in agg.items():
        add_count(reg, "door.%s.refusals" % rid, a["refusals"], src)
        judged = a["took_effect"] + a["did_not"]
        add_prop(reg, "door.%s.took_effect" % rid, a["took_effect"], judged, src,
                 cannot_judge=a["cannot_judge"])
        if a["recovery_n"]:
            reg.add("door.%s.recovery_turns" % rid, a["recovery_turns"] / a["recovery_n"],
                    "%.1f turns per refusal (%d refusals)" % (a["recovery_turns"] / a["recovery_n"],
                                                              a["recovery_n"]),
                    src, n=a["recovery_n"], stat="mean")
            reg.add("door.%s.recovery_output_tokens" % rid,
                    a["recovery_output_tokens"] / a["recovery_n"],
                    "%.0f output tokens per refusal" % (a["recovery_output_tokens"] / a["recovery_n"]),
                    src, n=a["recovery_n"], stat="mean")
        table.append([rid, a["refusals"], a["took_effect"], a["did_not"], a["cannot_judge"],
                      a["recovery_n"], a["recovery_turns"], a["recovery_output_tokens"]])
    ctx.write_table("table09_door_refusals.csv",
                    ["rule_id", "refusals", "took_effect", "did_not", "cannot_judge",
                     "recovery_n", "recovery_turns", "recovery_output_tokens"], table)


def review(ctx):
    rows = ctx.read_csv(REV, required=REV_COLUMNS)
    bad = sorted({r[c] for r in rows for c in ("coder1", "coder2", "final")} - set(REVIEW_CODES))
    if bad:
        raise ValueError("data/%s carries unknown codes: %s" % (REV, ", ".join(bad)))
    reg = ctx.registry
    src = "data/" + REV
    table = []
    for rid in sorted({r["rule_id"] for r in rows}):
        c = Counter(r["final"] for r in rows if r["rule_id"] == rid)
        n = c["right"] + c["wrong"]
        add_prop(reg, "door.%s.wrong_share" % rid, c["wrong"], n, src, unclear=c["unclear"],
                 label="model-coded")
        table.append([rid, sum(c.values()), c["right"], c["wrong"], c["unclear"]])
    ctx.write_table("table09_door_review.csv", ["rule_id", "sampled", "right", "wrong", "unclear"],
                    table)
    add_kappa(reg, "door.review.kappa", [r["coder1"] for r in rows], [r["coder2"] for r in rows], src)


def size(ctx):
    rows = ctx.read_csv(SIZE, required=SIZE_COLUMNS)
    reg = ctx.registry
    src = "data/" + SIZE
    agg = OrderedDict()
    for r in sorted(rows, key=lambda r: (r["rule_id"], r["door_type"])):
        a = agg.setdefault(r["rule_id"], Counter())
        for c in ("code_lines", "test_lines", "n_tests"):
            a[c] += num(r[c])
    table = []
    for rid, a in agg.items():
        add_count(reg, "door.%s.loc" % rid, a["code_lines"], src)
        add_count(reg, "door.%s.test_loc" % rid, a["test_lines"], src)
        add_count(reg, "door.%s.n_tests" % rid, a["n_tests"], src)
        table.append([rid, a["code_lines"], a["test_lines"], a["n_tests"]])
    ctx.write_table("table09_door_size.csv", ["rule_id", "code_lines", "test_lines", "n_tests"], table)


if __name__ == "__main__":
    sys.exit(standalone(run))
