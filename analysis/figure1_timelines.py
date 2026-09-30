#!/usr/bin/env python3
"""Figure 1: per-rule timelines for the rules of Table 3: the prose date, the door date and the
weekly corrections on one time axis. Sources: data/corrections_weekly.csv, data/rules.csv."""
import sys
from datetime import date
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
# This folder holds numbers.py, which would shadow the standard library's `numbers` module that
# numpy imports: take the folder off the front of the path, load the real module, append it.
if sys.path and str(Path(sys.path[0] or ".").resolve()) == _HERE:
    sys.path.pop(0)
import numbers  # noqa: E402,F401
if _HERE not in sys.path:
    sys.path.append(_HERE)
from common import in_series, num, save_svg, standalone, svg_setup  # noqa: E402
from table03_per_rule import COLUMNS, per_rule, rules_with_corrections  # noqa: E402


def run(ctx):
    rows = ctx.read_csv("corrections_weekly.csv", required=COLUMNS)
    rules = {r["id"]: r for r in ctx.read_csv("rules.csv", required=("id",))}
    ids = rules_with_corrections(per_rule(rows))
    weekly = {}
    for r in rows:
        if in_series(r["week"]) and num(r["count"]):
            weekly[(r["rule_id"], r["week"])] = weekly.get((r["rule_id"], r["week"]), 0) + num(r["count"])
    plt = svg_setup()
    fig, ax = plt.subplots(figsize=(7, 0.35 * max(3, len(ids)) + 1))
    seen = set()

    def once(label):
        if label in seen:
            return None
        seen.add(label)
        return label

    for y, rid in enumerate(ids):
        meta = rules.get(rid, {})
        for field, marker, label in (("prose_first_seen", "|", "prose"), ("door_landed", "s", "door")):
            d = meta.get(field)
            if d:
                ax.plot([date.fromisoformat(d)], [y], marker=marker, color="black",
                        markersize=8 if marker == "|" else 5, linestyle="none",
                        label=once(label))
        pts = sorted((w, c) for (r, w), c in weekly.items() if r == rid)
        if pts:
            ax.scatter([date.fromisoformat(w) for w, _ in pts], [y] * len(pts),
                       s=[20 * c for _, c in pts], color="grey", alpha=0.7,
                       label=once("corrections per week"))
    ax.set_yticks(range(len(ids)))
    ax.set_yticklabels(ids, fontsize=7)
    ax.axvline(date(2026, 9, 21), color="grey", linewidth=0.5, linestyle="--")
    ax.set_xlabel("week")
    if ids:
        ax.legend(fontsize=7, loc="upper left")
    fig.autofmt_xdate()
    save_svg(plt, fig, ctx.figure_path("figure1_timelines.svg"))


if __name__ == "__main__":
    sys.exit(standalone(run))
