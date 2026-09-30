#!/usr/bin/env python3
"""Table 4 and Figure 2: the weekly series. Per week and session kind (both repository groups
together, and each group in the table): operator turns, corrections per 100 operator turns, turn
ends on a question per 100 turn ends, and refusals per hook, with the model id and tool version in
force. The week starting 2026-09-21 carries two changes (the scheduler cut-over on 09-20 and the ask
door on 09-21) and is marked as such; no change of that week is attributed to one of them.

Source: data/transcripts_weekly.csv. Operator turns are `human_msgs_operator_likely` and
corrections `corr_hits_operator_likely` (the fixed detector on those turns).
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
from common import (BEFORE_WEEKS, KIND_SLUG, TWO_CHANGES_WEEK, add_prop, in_series, num,  # noqa: E402
                    save_svg, standalone, svg_setup, window_of)

SRC = "data/transcripts_weekly.csv"
KEYS = ("week", "session_kind", "repo_group", "model", "cli_version")
COUNTS = ("sessions", "asst_msgs", "human_msgs", "human_msgs_operator_likely",
          "corr_hits_operator_likely", "turn_ends", "ends_q_trailing", "ends_q_last400",
          "ends_q_trailing_replied")
HOOKS = ("ref_stop_promise", "ref_stop_ask", "ref_stop_rule", "dash_stop_detected",
         "ref_ptu_askuserquestion", "ref_ptu_dash_write")


def load(ctx):
    return ctx.read_csv("transcripts_weekly.csv", required=KEYS + COUNTS + HOOKS)


def aggregate(rows, keyf, cols):
    out = OrderedDict()
    for r in sorted(rows, key=lambda r: tuple(r[k] for k in KEYS)):
        k = keyf(r)
        if k is None:
            continue
        a = out.setdefault(k, Counter())
        for c in cols:
            a[c] += num(r.get(c))
    return out


def in_force(rows):
    """Per week: the model with the most assistant turns and the tool version with the most
    sessions (ties broken by name)."""
    models, clis = {}, {}
    for r in rows:
        w = r["week"]
        if r["model"] not in ("", "none"):
            models.setdefault(w, Counter())[r["model"]] += num(r["asst_msgs"])
        if r["cli_version"] not in ("", "none"):
            clis.setdefault(w, Counter())[r["cli_version"]] += num(r["sessions"])
    top = lambda c: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if c else ""  # noqa: E731
    return {w: top(c) for w, c in models.items()}, {w: top(c) for w, c in clis.items()}


def run(ctx):
    rows = [r for r in load(ctx) if in_series(r["week"])]
    reg = ctx.registry
    cols = COUNTS + HOOKS
    by_kind = aggregate(rows, lambda r: (r["week"], r["session_kind"], "all"), cols)
    by_group = aggregate(rows, lambda r: (r["week"], r["session_kind"], r["repo_group"]), cols)
    model, cli = in_force(rows)
    table = []
    for (w, kind, g), a in list(by_kind.items()) + list(by_group.items()):
        ht, te = a["human_msgs_operator_likely"], a["turn_ends"]
        label = window_of(w) or ("partial" if w < BEFORE_WEEKS[0] else "")
        if w == TWO_CHANGES_WEEK:
            label += "; two changes"
        table.append([w, label, kind, g, model.get(w, ""), cli.get(w, ""), a["sessions"], ht,
                      a["corr_hits_operator_likely"],
                      100 * a["corr_hits_operator_likely"] / ht if ht else None, te,
                      a["ends_q_trailing"], 100 * a["ends_q_trailing"] / te if te else None,
                      a["ends_q_trailing_replied"]] + [a[h] for h in HOOKS])
        if g != "all":
            continue
        slug = KIND_SLUG.get(kind, kind.replace(" ", "_"))
        if ht:
            add_prop(reg, "weekly.%s.%s.corr_per100" % (w, slug), a["corr_hits_operator_likely"],
                     ht, SRC, unit="per 100 operator turns")
        if te:
            add_prop(reg, "weekly.%s.%s.q_end_per100" % (w, slug), a["ends_q_trailing"], te, SRC,
                     unit="per 100 turn ends")
    ctx.write_table("table04_weekly.csv",
                    ["week", "label", "session_kind", "repo_group", "model_in_force",
                     "cli_in_force", "sessions", "operator_turns", "corrections",
                     "corrections_per_100_turns", "turn_ends", "ends_on_question",
                     "ends_on_question_per_100", "ends_on_question_answered"] + list(HOOKS), table)
    for w in sorted(model):
        reg.add("weekly.%s.model" % w, model[w], model[w], SRC)
    for w in sorted(cli):
        reg.add("weekly.%s.cli_version" % w, cli[w], cli[w], SRC)
    figure(ctx, by_kind, model)


def figure(ctx, by_kind, model):
    plt = svg_setup()
    fig, axes = plt.subplots(2, 1, figsize=(7, 5), sharex=True)
    kinds = sorted({k for (_, k, _) in by_kind})
    for kind in kinds:
        pts = sorted((w, a) for (w, k, _), a in by_kind.items() if k == kind)
        xs = [date.fromisoformat(w) for w, _ in pts]
        c = [100 * a["corr_hits_operator_likely"] / a["human_msgs_operator_likely"]
             if a["human_msgs_operator_likely"] else float("nan") for _, a in pts]
        q = [100 * a["ends_q_trailing"] / a["turn_ends"] if a["turn_ends"] else float("nan")
             for _, a in pts]
        axes[0].plot(xs, c, marker="o", label=kind)
        axes[1].plot(xs, q, marker="o", label=kind)
    axes[0].set_ylabel("corrections per 100\noperator turns")
    axes[1].set_ylabel("turn ends on a question\nper 100 turn ends")
    for ax in axes:
        ax.axvline(date.fromisoformat(TWO_CHANGES_WEEK), color="grey", linestyle="--", linewidth=0.8)
        ax.grid(linewidth=0.3)
    axes[0].legend(fontsize=7)
    axes[1].set_xticks([date.fromisoformat(w) for w in sorted(model)])
    axes[1].set_xticklabels(["%s\n%s" % (w[5:], model[w]) for w in sorted(model)], fontsize=6)
    axes[0].set_title("dashed line: week of two changes (cut-over and ask door)", fontsize=8)
    save_svg(plt, fig, ctx.figure_path("figure2_weekly.svg"))


if __name__ == "__main__":
    sys.exit(standalone(run))
