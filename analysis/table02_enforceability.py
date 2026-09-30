#!/usr/bin/env python3
"""Table 2 (RQ3): the share of in-scope rules in E-full, E-partial and E-none, overall and for
prose-only rules against rules with a door (door only or both). Source: data/rules.csv."""
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
from common import add_prop, standalone  # noqa: E402
from stats import wilson  # noqa: E402
from table01_rules import ENF, load_rules  # noqa: E402

SRC = "data/rules.csv"
SLUG = {"E-full": "efull", "E-partial": "epartial", "E-none": "enone"}


def run(ctx):
    rules = load_rules(ctx)
    reg = ctx.registry
    groups = [("all", rules),
              ("prose_only", [r for r in rules if r["delivery"] == "prose only"]),
              ("with_door", [r for r in rules if r["delivery"] in ("door only", "both")])]
    rows = []
    for g, sub in groups:
        n = len(sub)
        for e in ENF:
            k = sum(1 for r in sub if r["enforceability"] == e)
            key = "rules.share_%s" % SLUG[e] if g == "all" else "rules.%s.share_%s" % (g, SLUG[e])
            add_prop(reg, key, k, n, SRC)
            ci = wilson(k, n) if n else (None, None)
            rows.append([g, e, k, n, k / n if n else None, ci[0], ci[1]])
        # E-partial and E-none together: where a door can see at most a proxy.
        k = sum(1 for r in sub if r["enforceability"] in ("E-partial", "E-none"))
        add_prop(reg, "rules.%s.share_not_efull" % g, k, n, SRC)
    ctx.write_table("table02_enforceability.csv",
                    ["group", "enforceability", "k", "n", "share", "wilson_lo", "wilson_hi"], rows)


if __name__ == "__main__":
    sys.exit(standalone(run))
