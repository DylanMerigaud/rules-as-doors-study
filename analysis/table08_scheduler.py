#!/usr/bin/env python3
"""Table 8 and Figure 3: the scheduler (in-scope jobs only). Launches, outcomes and door refusals
per week and door class; for jobs a door held, the share done inside their period; the share of
due obligations logged the same day before the cut-over, on the cut-over day and after it, and
the days with no log at all.

Sources: data/scheduler_weekly.csv (week_start, door_class, counts; door_class `all` carries the
launches and outcomes, the other classes the door rows, episodes and held jobs) and
data/scheduler_ontime.csv (row_set, era, due row-days, logged the same day, days with no log).

What these measures cannot say, stated with them: the daily era has no run ledger, only an
engagement log that records a gesture per obligation, not a run; the replay of what was due uses
today's obligation list, so obligations that died before the snapshot are missing; the write door
and the operator-facing floor leave no scheduler row, so their classes are absent, not zero; the
cut-over (09-20) and the ask door (09-21) are a day apart.
"""
import sys
from collections import Counter, OrderedDict
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
from common import add_count, add_prop, in_series, num, save_svg, standalone, svg_setup  # noqa: E402

SRC_W = "data/scheduler_weekly.csv"
SRC_O = "data/scheduler_ontime.csv"
OUTCOMES = ("outcome_done", "outcome_closed_by_ledger", "outcome_error", "outcome_blocked",
            "outcome_to_operator", "outcome_retry", "outcome_superseded")
DOOR_COLS = ("door_rows", "door_episodes", "jobs_held", "jobs_held_done_in_period",
             "jobs_held_no_period")
W_COLUMNS = ("week_start", "door_class", "jobs_created", "launches") + OUTCOMES + DOOR_COLS
O_COLUMNS = ("row_set", "era", "first_day", "last_day", "days", "rows", "due_row_days",
             "logged_same_day", "days_with_no_log_in_set")


def run(ctx):
    reg = ctx.registry
    done_any = False
    if ctx.has_data("scheduler_weekly.csv"):
        weekly(ctx, ctx.read_csv("scheduler_weekly.csv", required=W_COLUMNS))
        done_any = True
    else:
        ctx.note("table 8: data/scheduler_weekly.csv not found, weekly part skipped")
    if ctx.has_data("scheduler_ontime.csv"):
        on_time_part(ctx, ctx.read_csv("scheduler_ontime.csv", required=O_COLUMNS))
        done_any = True
    else:
        ctx.note("table 8: data/scheduler_ontime.csv not found, on-time part skipped")
    if not done_any:
        from common import Missing
        raise Missing("data/scheduler_weekly.csv and data/scheduler_ontime.csv not found")
    return reg


def weekly(ctx, rows):
    reg = ctx.registry
    rows = [r for r in rows if in_series(r["week_start"])]
    alls = sorted((r for r in rows if r["door_class"] == "all"), key=lambda r: r["week_start"])
    tot = Counter()
    table = []
    for r in alls:
        for c in ("jobs_created", "launches") + OUTCOMES:
            tot[c] += num(r[c])
        table.append([r["week_start"], "all", num(r["jobs_created"]), num(r["launches"])] +
                     [num(r[c]) for c in OUTCOMES] + [None] * len(DOOR_COLS))
        add_count(reg, "sched.launches.%s" % r["week_start"], num(r["launches"]), SRC_W)
    add_count(reg, "sched.launches", tot["launches"], SRC_W)
    add_count(reg, "sched.jobs_created", tot["jobs_created"], SRC_W)
    for c in OUTCOMES:
        add_prop(reg, "sched.%s" % c, tot[c], tot["launches"], SRC_W,
                 note="share of launches over the weeks shown")
    classes = sorted({r["door_class"] for r in rows} - {"all"})
    by_class = OrderedDict((c, Counter()) for c in classes)
    per_week = {}
    for r in sorted(rows, key=lambda r: (r["week_start"], r["door_class"])):
        if r["door_class"] == "all":
            continue
        for c in DOOR_COLS:
            by_class[r["door_class"]][c] += num(r[c])
        per_week[(r["week_start"], r["door_class"])] = num(r["door_episodes"])
        table.append([r["week_start"], r["door_class"], None, None] + [None] * len(OUTCOMES) +
                     [num(r[c]) for c in DOOR_COLS])
    for c, t in by_class.items():
        reg.add("sched.refusals.%s" % c, t["door_episodes"],
                "%s episodes (%s deferral rows)" % ("{:,}".format(t["door_episodes"]),
                                                    "{:,}".format(t["door_rows"])),
                SRC_W, rows=t["door_rows"],
                note="an episode is consecutive deferrals of one job by one door class")
        held = t["jobs_held"] - t["jobs_held_no_period"]
        add_prop(reg, "sched.held_done_in_period.%s" % c, t["jobs_held_done_in_period"], held,
                 SRC_W, note="held jobs with a period, done inside it; held jobs, not violations")
    ctx.write_table("table08_scheduler_weekly.csv",
                    ["week_start", "door_class", "jobs_created", "launches"] + list(OUTCOMES) +
                    list(DOOR_COLS), table)
    figure(ctx, alls, classes, per_week)


# The extraction names its eras pre, cutover_day and post; the keys use the words of ANALYSIS.md.
ERA = {"pre": "before", "post": "after"}


def on_time_part(ctx, rows):
    reg = ctx.registry
    table = []
    for r in rows:
        n, k = num(r["due_row_days"]), num(r["logged_same_day"])
        era = ERA.get(r["era"], r["era"])
        key = "sched.on_time.%s.%s" % (r["row_set"], era)
        add_prop(reg, key, k, n, SRC_O, days=num(r["days"]), rows=num(r["rows"]),
                 first_day=r["first_day"], last_day=r["last_day"])
        reg.add("sched.days_no_log.%s.%s" % (r["row_set"], era),
                num(r["days_with_no_log_in_set"]),
                "%s of %s days" % (num(r["days_with_no_log_in_set"]), num(r["days"])), SRC_O,
                k=num(r["days_with_no_log_in_set"]), n=num(r["days"]))
        table.append([r["row_set"], era, r["first_day"], r["last_day"], num(r["days"]),
                      num(r["rows"]), n, k, k / n if n else None,
                      num(r["days_with_no_log_in_set"])])
        if r["row_set"] == "all_open_rows" and r["era"] == "post":
            add_prop(reg, "sched.on_time_share", k, n, SRC_O,
                     note="due obligations logged the same day after the cut-over")
    ctx.write_table("table08_scheduler_ontime.csv",
                    ["row_set", "era", "first_day", "last_day", "days", "rows", "due_row_days",
                     "logged_same_day", "share", "days_with_no_log"], table)


def figure(ctx, alls, classes, per_week):
    plt = svg_setup()
    weeks = [r["week_start"] for r in alls]
    xs = [date.fromisoformat(w) for w in weeks]
    fig, ax = plt.subplots(figsize=(7, 3.5))
    bottom = [0] * len(weeks)
    for c in classes:
        ys = [per_week.get((w, c), 0) for w in weeks]
        ax.bar(xs, ys, bottom=bottom, width=5, label=c)
        bottom = [b + y for b, y in zip(bottom, ys)]
    ax2 = ax.twinx()
    ax2.plot(xs, [num(r["launches"]) for r in alls], color="black", marker="o", label="launches")
    ax.set_ylabel("door episodes")
    ax2.set_ylabel("launches")
    ax.legend(fontsize=7, loc="upper left")
    ax2.legend(fontsize=7, loc="upper right")
    ax.set_xticks(xs)
    ax.set_xticklabels([w[5:] for w in weeks], fontsize=7)
    save_svg(plt, fig, ctx.figure_path("figure3_scheduler.svg"))


if __name__ == "__main__":
    sys.exit(standalone(run))
