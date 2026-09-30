#!/usr/bin/env python3
"""Table 13: cost context. Weekly model usage by session kind (turns, output tokens, the harness's
own load units and each kind's share of the week's load) and the tool's API-equivalent cost
estimate for scheduler launches. The estimate is printed by the tool on a subscription and is never
money spent; attempts that carry no estimate make the sums lower bounds. Descriptive only.

Source: data/cost_weekly.csv.
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
from common import add_count, in_series, num, standalone  # noqa: E402

SRC = "data/cost_weekly.csv"
COLUMNS = ("week_start", "session_kind", "sessions", "turns", "output_tokens",
           "load_units_with_imputed_tier", "share_of_week_load", "envelope_attempts",
           "envelope_usd", "envelope_no_estimate")


def run(ctx):
    rows = [r for r in ctx.read_csv("cost_weekly.csv", required=COLUMNS) if in_series(r["week_start"])]
    reg = ctx.registry
    table = []
    usd = OrderedDict()
    att = Counter()
    kinds = Counter()
    for r in sorted(rows, key=lambda r: (r["week_start"], r["session_kind"])):
        table.append([r["week_start"], r["session_kind"], num(r["sessions"]), num(r["turns"]),
                      num(r["output_tokens"]), num(r["load_units_with_imputed_tier"]),
                      num(r["share_of_week_load"]), num(r["envelope_attempts"]),
                      num(r["envelope_usd"]) if r["envelope_usd"] != "" else None,
                      num(r["envelope_no_estimate"])])
        kinds[r["session_kind"]] += num(r["output_tokens"])
        if r["envelope_usd"] != "":
            usd[r["week_start"]] = usd.get(r["week_start"], 0) + num(r["envelope_usd"])
        att["attempts"] += num(r["envelope_attempts"])
        att["no_estimate"] += num(r["envelope_no_estimate"])
    ctx.write_table("table13_cost.csv",
                    ["week_start", "session_kind", "sessions", "turns", "output_tokens",
                     "load_units_imputed", "share_of_week_load", "envelope_attempts",
                     "envelope_usd", "envelope_no_estimate"], table)
    total = sum(usd.values())
    reg.add("cost.api_equiv_total", total, "%.2f USD" % total, SRC,
            note="API-equivalent estimate printed by the tool on a subscription, never money "
                 "spent; a lower bound, attempts without an estimate add nothing",
            attempts=att["attempts"], no_estimate=att["no_estimate"])
    for w, v in usd.items():
        reg.add("cost.api_equiv.%s" % w, v, "%.2f USD" % v, SRC)
    if usd:
        vals = sorted(usd.values())
        m = len(vals)
        med = vals[m // 2] if m % 2 else (vals[m // 2 - 1] + vals[m // 2]) / 2
        reg.add("cost.api_equiv_weekly_median", med, "%.2f USD" % med, SRC, n=m)
    add_count(reg, "cost.envelope_attempts", att["attempts"], SRC)
    add_count(reg, "cost.envelope_no_estimate", att["no_estimate"], SRC)
    tot_tokens = sum(kinds.values())
    for k, v in sorted(kinds.items()):
        slug = k.replace(" ", "_")
        reg.add("cost.output_tokens.%s" % slug, v, "{:,}".format(int(v)), SRC,
                share=v / tot_tokens if tot_tokens else None)


if __name__ == "__main__":
    sys.exit(standalone(run))
