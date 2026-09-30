#!/usr/bin/env python3
"""Table 3 (RQ1, RQ2): for each in-scope rule with at least one correction mapped to it,
corrections per 100 exposure days (operator-active days) in each delivery state, with exact Poisson
intervals. A state with fewer than 5 exposure days is listed, not rated.

Source: data/corrections_weekly.csv (week, rule_id, state, count, exposure). States: none, prose,
door, and unknown (before a censored first sighting of the prose, listed only). A week label that
is not a date (corrections back-filled from transcripts that no longer exist, with no exposure)
is counted as undated and never enters a rate. Weeks after the after window are left out.
"""
import sys
from collections import OrderedDict
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
# This folder holds numbers.py, which would shadow the standard library's `numbers` module that
# numpy imports: take the folder off the front of the path, load the real module, append it.
if sys.path and str(Path(sys.path[0] or ".").resolve()) == _HERE:
    sys.path.pop(0)
import numbers  # noqa: E402,F401
if _HERE not in sys.path:
    sys.path.append(_HERE)
from common import add_count, in_series, num, standalone  # noqa: E402
from stats import rate_per  # noqa: E402

SRC = "data/corrections_weekly.csv"
STATES = ("none", "prose", "door")
LISTED_STATES = ("unknown",)
MIN_EXPOSURE = 5
COLUMNS = ("week", "rule_id", "state", "count", "exposure")


def per_rule(rows):
    """{rule: {state: [count, exposure]}, plus 'undated': count}."""
    agg = OrderedDict()
    for r in sorted(rows, key=lambda r: (r["rule_id"], r["week"], r["state"])):
        a = agg.setdefault(r["rule_id"], {"undated": 0})
        c = num(r["count"])
        if not in_series(r["week"]):
            if not (len(r["week"]) == 10 and r["week"][4] == "-"):
                a["undated"] += c
            continue
        s = a.setdefault(r["state"], [0, 0])
        s[0] += c
        s[1] += num(r["exposure"])
    return agg


def rules_with_corrections(agg):
    return [rid for rid, a in agg.items()
            if a["undated"] + sum(v[0] for k, v in a.items() if k != "undated") > 0]


def run(ctx):
    rows = ctx.read_csv("corrections_weekly.csv", required=COLUMNS)
    reg = ctx.registry
    agg = per_rule(rows)
    rules = rules_with_corrections(agg)
    table = []
    n_rated = n_listed = 0
    for rid in rules:
        a = agg[rid]
        for st in STATES + LISTED_STATES:
            if st not in a:
                continue
            k, expo = a[st]
            rated = st in STATES and expo >= MIN_EXPOSURE
            rp = rate_per(k, expo) if rated else None
            table.append([rid, st, k, expo, "rated" if rated else "listed",
                          rp[0] if rp else None, rp[1][0] if rp else None, rp[1][1] if rp else None])
            key = "perrule.%s.%s" % (rid, st)
            if rated:
                n_rated += 1
                reg.add(key + ".rate", rp[0],
                        "%.1f per 100 operator-active days (%d in %s days; 95%% CI %.1f to %.1f)"
                        % (rp[0], k, expo, rp[1][0], rp[1][1]), SRC, k=k, n=expo, ci=rp[1],
                        ci_method="exact Poisson 95%", unit="per 100 exposure days",
                        text_short="%.1f" % rp[0])
            else:
                n_listed += 1
                reg.add(key + ".listed", k, "%d in %s days (not rated)" % (k, expo), SRC,
                        k=k, n=expo)
        if a["undated"]:
            table.append([rid, "undated", a["undated"], None, "listed", None, None, None])
    ctx.write_table("table03_per_rule.csv",
                    ["rule_id", "state", "corrections", "exposure_days", "status",
                     "rate_per_100", "poisson_lo", "poisson_hi"], table)
    add_count(reg, "perrule.n_rules", len(rules), SRC, note="rules with at least one correction")
    add_count(reg, "perrule.n_rated", n_rated, SRC, note="rule and state cells rated")
    add_count(reg, "perrule.n_listed_not_rated", n_listed, SRC,
              note="rule and state cells listed, fewer than %d exposure days or state unknown"
              % MIN_EXPOSURE)
    add_count(reg, "perrule.n_undated_corrections", sum(agg[r]["undated"] for r in rules), SRC)
    total = sum(v[0] for r in rules for s, v in agg[r].items() if s != "undated")
    add_count(reg, "perrule.n_corrections_dated", total, SRC)


if __name__ == "__main__":
    sys.exit(standalone(run))
