#!/usr/bin/env python3
"""Supplementary field keys (review round 1, 2026-10-13): descriptive, none changes a registered
analysis. They reconcile counts that come from different sources or windows, split pooled rows,
and recompute agreement from the published labels.

Inputs: data/scheduler_weekly.csv, data/transcripts_weekly.csv, data/door_refusals_weekly.csv,
data/door_review.csv, data/door_review_frame.csv, data/ask_audit.csv, data/rules.csv,
data/rules_coding.csv, data/headless_split.csv, data/case_facts.csv, and the per-rule keys the
earlier scripts registered (table 3).
"""
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if sys.path and str(Path(sys.path[0] or ".").resolve()) == _HERE:
    sys.path.pop(0)
import numbers  # noqa: E402,F401
if _HERE not in sys.path:
    sys.path.append(_HERE)
from common import (AFTER_WEEKS, BEFORE_WEEKS, KIND_SLUG, Missing, add_count, add_prop,  # noqa: E402
                    fmt_num, num, standalone)
from stats import kappa_bootstrap  # noqa: E402
from table07_ask_audit import add_kappa  # noqa: E402

WINDOWS = (("before", BEFORE_WEEKS), ("after", AFTER_WEEKS))
LEDGER_WEEKS = ("2026-09-28", "2026-10-05")
DOOR_SLUG = {"PreToolUse hook": "pretooluse_hook", "Stop hook": "stop_hook", "write refusal": "write_refusal"}


def _opt(ctx, name, required=()):
    try:
        return ctx.read_csv(name, required=required)
    except Missing:
        return None


def run(ctx):
    reg = ctx.registry
    done = []
    for fn in (scheduler, dash_write, door_split, review, audit, coding, headless, hook_loaded_rate,
               retired, rules_dates,
               prose_rates, versions, ledger_window):
        if fn(ctx, reg) is not False:
            done.append(fn.__name__)
    if not done:
        raise Missing("no input of the field supplement found")


def scheduler(ctx, reg):
    rows = _opt(ctx, "scheduler_weekly.csv", ("week_start", "door_class", "launches"))
    if rows is None:
        return False
    src = "data/scheduler_weekly.csv"
    alls = {r["week_start"]: num(r["launches"]) for r in rows if r["door_class"] == "all"}
    for w, weeks in WINDOWS:
        k = sum(v for wk, v in alls.items() if wk in weeks)
        add_count(reg, "sched.launches.%s_window" % w, k, src,
                  note="launches in the weeks of the %s window (ANALYSIS.md section 2)" % w,
                  weeks=[wk for wk in sorted(alls) if wk in weeks])


def dash_write(ctx, reg):
    rows = _opt(ctx, "transcripts_weekly.csv", ("week", "session_kind", "ref_ptu_dash_write"))
    if rows is None:
        return False
    src = "data/transcripts_weekly.csv"
    has_calls = "write_calls" in rows[0] if rows else False

    def tot(pred):
        d = sum(num(r["ref_ptu_dash_write"]) for r in rows if pred(r))
        c = sum(num(r.get("write_calls")) for r in rows if pred(r)) if has_calls else None
        return d, c

    note = "transcript count of long-dash write refusals (all session kinds unless named)"
    allw = BEFORE_WEEKS + AFTER_WEEKS
    d, c = tot(lambda r: r["week"] in allw)
    add_count(reg, "dashwrite.denials.registered_windows", d, src, note=note + "; weeks of both windows")
    if c:
        add_prop(reg, "dashwrite.rate.registered_windows", d, c, src, digits=2)
    for w, weeks in WINDOWS:
        d, c = tot(lambda r, weeks=weeks: r["week"] in weeks)
        add_count(reg, "dashwrite.denials.%s" % w, d, src, note=note)
    d, c = tot(lambda r: r["week"] not in allw)
    add_count(reg, "dashwrite.denials.outside_windows", d, src,
              note=note + "; the partial week before the windows", weeks=sorted({r["week"] for r in rows
                                                                                if r["week"] not in allw}))
    d, c = tot(lambda r: r["week"] in LEDGER_WEEKS)
    add_count(reg, "dashwrite.denials.ledger_weeks", d, src,
              note=note + "; the weeks of 2026-09-28 and 2026-10-05, which hold the refusal ledger's "
                          "window (2026-09-30 to 2026-10-11) and two days before it")
    for kind, slug in KIND_SLUG.items():
        d, c = tot(lambda r, kind=kind: r["week"] in LEDGER_WEEKS and r["session_kind"] == kind)
        add_count(reg, "dashwrite.denials.ledger_weeks.%s" % slug, d, src, note=note)
        d, c = tot(lambda r, kind=kind: r["week"] in allw and r["session_kind"] == kind)
        add_count(reg, "dashwrite.denials.registered_windows.%s" % slug, d, src, note=note)


def door_split(ctx, reg):
    rows = _opt(ctx, "door_refusals_weekly.csv", ("rule_id", "door_type", "refusals", "took_effect",
                                                   "did_not", "cannot_judge"))
    if rows is None:
        return False
    src = "data/door_refusals_weekly.csv"
    agg = OrderedDict()
    for r in rows:
        a = agg.setdefault((r["rule_id"], r["door_type"]), Counter())
        for c in ("refusals", "took_effect", "did_not", "cannot_judge"):
            a[c] += num(r[c])
    for (rid, dt), a in agg.items():
        base = "door.%s.refusals.%s" % (rid, DOOR_SLUG.get(dt, dt.replace(" ", "_").lower()))
        add_count(reg, base, a["refusals"], src, door_type=dt)
        judged = a["took_effect"] + a["did_not"]
        add_prop(reg, base + ".took_effect", a["took_effect"], judged, src, digits=1,
                 cannot_judge=a["cannot_judge"], door_type=dt)


def review(ctx, reg):
    rows = _opt(ctx, "door_review.csv", ("rule_id", "stratum", "coder1", "coder2", "final"))
    if rows is None:
        return False
    src = "data/door_review.csv"
    by = OrderedDict()
    for r in rows:
        by.setdefault(r["rule_id"], []).append(r)
    for rid, rs in by.items():
        add_count(reg, "door.%s.review.n_items" % rid, len(rs), src,
                  strata=dict(Counter(r["stratum"] for r in rs)))
        a, b = [r["coder1"] for r in rs], [r["coder2"] for r in rs]
        agree = sum(1 for x, y in zip(a, b) if x == y)
        kb = kappa_bootstrap(a, b)
        if kb is None:
            reg.add("door.%s.review.kappa" % rid, None,
                    "undefined (one label on both sides; %d of %d agree)" % (agree, len(rs)), src,
                    agree=agree, n=len(rs))
        else:
            add_kappa(reg, "door.%s.review.kappa" % rid, a, b, src)
            reg.entries["door.%s.review.kappa" % rid]["agree"] = agree
        add_count(reg, "door.%s.review.n_unclear" % rid, sum(1 for r in rs if r["final"] == "unclear"), src)
    frame = _opt(ctx, "door_review_frame.csv", ("rule_id", "door_type", "refusals_in_ledger",
                                                "located_in_a_transcript", "sampled"))
    if frame is not None:
        fsrc = "data/door_review_frame.csv"
        for r in frame:
            base = "door.%s.review.frame.%s" % (r["rule_id"], DOOR_SLUG.get(r["door_type"], r["door_type"]))
            reg.add(base, num(r["sampled"]), "%s sampled of %s located in a transcript (%s refusals in the ledger)"
                    % (r["sampled"], r["located_in_a_transcript"], r["refusals_in_ledger"]), fsrc,
                    located=num(r["located_in_a_transcript"]), refusals=num(r["refusals_in_ledger"]))


def audit(ctx, reg):
    rows = _opt(ctx, "ask_audit.csv", ("window", "coder1", "coder2", "final"))
    if rows is None:
        return False
    src = "data/ask_audit.csv"
    add_count(reg, "audit.kappa.n_items", len(rows), src, note="items behind audit.kappa, both windows")
    for w in ("before", "after"):
        sub = [r for r in rows if r["window"] == w]
        add_kappa(reg, "audit.kappa.%s" % w, [r["coder1"] for r in sub], [r["coder2"] for r in sub], src)
        reg.entries["audit.kappa.%s" % w]["n"] = len(sub)
        dis = sum(1 for r in sub if r["coder1"] != r["coder2"])
        add_count(reg, "audit.%s.n_disagreements" % w, dis, src, note="settled by a third model pass")


def coding(ctx, reg):
    rows = _opt(ctx, "rules_coding.csv", ("unit", "rule_id", "coder1_is_rule", "coder2_is_rule",
                                          "coder1_class", "coder2_class", "coder1_enforceability",
                                          "coder2_enforceability"))
    if rows is None:
        return False
    src = "data/rules_coding.csv"
    add_count(reg, "rules.coding.n_units", len(rows), src, note="public prose units")
    both = [r for r in rows if r["coder1_is_rule"] == "1" and r["coder2_is_rule"] == "1"]
    add_count(reg, "rules.coding.n_units_both_rule", len(both), src,
              note="units both coders called a rule: the items of the class and enforceability kappas")
    add_count(reg, "rules.coding.n_rules_both_rule", len({r["rule_id"] for r in both}), src,
              note="the rules the 174 units belong to")
    add_count(reg, "rules.coding.n_rules", len({r["rule_id"] for r in rows}), src,
              note="rules with at least one text unit (the door-only rules have none)")
    for f in ("class", "enforceability"):
        a = [r["coder1_" + f] or "null" for r in both]
        b = [r["coder2_" + f] or "null" for r in both]
        add_kappa(reg, "rules.kappa_%s.recomputed" % f, a, b, src)
        reg.entries["rules.kappa_%s.recomputed" % f]["n"] = len(both)


def headless(ctx, reg):
    rows = _opt(ctx, "headless_split.csv", ("window", "headless_kind", "repo_group", "stop_firings"))
    if rows is None:
        return False
    src = "data/headless_split.csv"
    cols = [c for c in rows[0] if c not in ("window", "headless_kind", "repo_group")]
    for kind, slug in (("scheduler worker prompt", "worker_prompt"), ("other headless", "other")):
        sub = [r for r in rows if r["headless_kind"] == kind]
        for c in cols:
            add_count(reg, "headless.%s.%s" % (slug, c), sum(num(r[c]) for r in sub), src,
                      note="all weeks of data/transcripts_weekly.csv, by the week a session started")


def hook_loaded_rate(ctx, reg):
    """R5-20: the long-dash write refusals over the write calls of the sessions that load the hook.
    The scheduler's workers run bare, with no hook, so their write calls leave the denominator.
    Both counts are over every week of the tables, as `dashwrite.rate` is."""
    tw = _opt(ctx, "transcripts_weekly.csv", ("ref_ptu_dash_write", "write_calls"))
    hs = _opt(ctx, "headless_split.csv", ("headless_kind", "write_calls", "ref_ptu_dash_write"))
    if tw is None or hs is None:
        return False
    den = sum(num(r["write_calls"]) for r in tw)
    k = sum(num(r["ref_ptu_dash_write"]) for r in tw)
    bare = sum(num(r["write_calls"]) for r in hs if r["headless_kind"] == "scheduler worker prompt")
    bare_k = sum(num(r["ref_ptu_dash_write"]) for r in hs if r["headless_kind"] == "scheduler worker prompt")
    add_count(reg, "dashwrite.write_calls.bare_workers", bare, "data/headless_split.csv",
              note="write calls of the scheduler's bare workers, which load no hook (all weeks)")
    add_prop(reg, "dashwrite.rate.hook_loaded", k - bare_k, den - bare,
             "data/transcripts_weekly.csv, data/headless_split.csv", digits=2,
             note="all weeks; denominator: the write calls the write hook inspects, in sessions "
                  "that load it (every session but the scheduler's bare workers)")


def retired(ctx, reg):
    rows = _opt(ctx, "transcripts_weekly.csv", ("week", "ref_stop_retired"))
    if rows is None:
        return False
    for w, weeks in WINDOWS:
        add_count(reg, "transcripts.ref_stop_retired.%s" % w,
                  sum(num(r["ref_stop_retired"]) for r in rows if r["week"] in weeks),
                  "data/transcripts_weekly.csv",
                  note="blocks of the daily session's Stop gate, retired at the 2026-09-20 cut-over; "
                       "all session kinds")


def rules_dates(ctx, reg):
    rows = _opt(ctx, "rules.csv", ("id", "delivery", "prose_first_seen", "door_landed",
                                   "prose_date_censored", "door_date_censored"))
    if rows is None:
        return False
    src = "data/rules.csv"
    both = [r for r in rows if r["prose_first_seen"] and r["door_landed"]]
    before = [r["id"] for r in both if r["door_landed"] < r["prose_first_seen"]]
    same = [r["id"] for r in both if r["door_landed"] == r["prose_first_seen"]]
    after = [r["id"] for r in both if r["door_landed"] > r["prose_first_seen"]]
    reg.add("rules.n_door_before_prose", len(before), "%d of %d (%s)" % (len(before), len(both), ", ".join(before)),
            src, ids=before, censored_prose=[i for i in before if
                                             next(r for r in rows if r["id"] == i)["prose_date_censored"] == "1"],
            note="rules with both dates whose first door landed before the first datable prose; a "
                 "censored prose date is an upper bound")
    reg.add("rules.n_door_same_day_as_prose", len(same), "%d of %d (%s)" % (len(same), len(both), ", ".join(same)),
            src, ids=same)
    reg.add("rules.n_prose_then_door", len(after), "%d of %d (%s)" % (len(after), len(both), ", ".join(after)),
            src, ids=after)
    lo, hi = BEFORE_WEEKS[0], "2026-10-11"
    inwin = [r["id"] for r in both if r["door_landed"] > r["prose_first_seen"] and lo <= r["door_landed"] <= hi]
    reg.add("rules.n_prose_then_door_in_windows", len(inwin), "%d (%s)" % (len(inwin), ", ".join(inwin)), src,
            ids=inwin, note="prose first, door landed between 2026-08-31 and 2026-10-11")
    landed = OrderedDict()
    for r in sorted(rows, key=lambda r: (r["door_landed"], r["id"])):
        if r["door_landed"] and lo <= r["door_landed"] <= hi:
            landed.setdefault(r["door_landed"], []).append(r["id"])
    for d, ids in landed.items():
        reg.add("rules.doors_landed.%s" % d, ids, ", ".join(ids), src)


def prose_rates(ctx, reg):
    ent = ctx.registry.entries
    rated = OrderedDict((k.split(".")[1], ent[k]) for k in sorted(ent)
                        if k.startswith("perrule.") and k.endswith(".prose.rate"))
    if not rated:
        return False
    vals = sorted(e["value"] for e in rated.values())
    n = len(vals)
    med = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
    reg.add("perrule.prose.distribution", med,
            "%d rules rated in the prose state: median %s, range %s to %s per 100 operator-active days"
            % (n, fmt_num(med, 1), fmt_num(vals[0], 1), fmt_num(vals[-1], 1)), "results/numbers.json",
            rates={k: round(e["value"], 6) for k, e in rated.items()},
            n_zero=sum(1 for v in vals if v == 0))
    reg.add("perrule.prose.all_rates", None, "; ".join("%s %s" % (k, fmt_num(e["value"], 1))
                                                     for k, e in sorted(rated.items(),
                                                                        key=lambda kv: (-kv[1]["value"], kv[0]))),
            "results/numbers.json", note="every rule rated in the prose state, highest first")


def versions(ctx, reg):
    rows = _opt(ctx, "transcripts_weekly.csv", ("week", "session_kind", "repo_group", "model",
                                                 "cli_version", "sessions"))
    if rows is None:
        return False
    src = "data/transcripts_weekly.csv"

    def vkey(v):
        return tuple(int(x) for x in v.split(".")) if v.replace(".", "").isdigit() else (0,)

    allw = BEFORE_WEEKS + AFTER_WEEKS
    for scope, pred in (("all_sessions", lambda r: True),
                        ("operator_door", lambda r: r["session_kind"] == "operator session"
                         and r["repo_group"] == "door")):
        clis = sorted({r["cli_version"] for r in rows if r["week"] in allw and pred(r)
                       and r["cli_version"] not in ("", "none", "unknown")}, key=vkey)
        if clis:
            reg.add("transcripts.cli_range.%s" % scope, [clis[0], clis[-1]], "%s to %s" % (clis[0], clis[-1]),
                    src, n_versions=len(clis))
        for w in allw:
            c = Counter()
            for r in rows:
                if r["week"] == w and pred(r) and r["model"] not in ("", "none", "<synthetic>"):
                    c[r["model"]] += num(r["sessions"])
            c = Counter({m: k for m, k in c.items() if k})
            if c:
                tot = sum(c.values())
                reg.add("weekly.%s.models.%s" % (w, scope), dict(c), "; ".join(
                    "%s %d of %d" % (m, k, tot) for m, k in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))),
                        src, note="sessions by model, rows without a model and synthetic rows left out")


def ledger_window(ctx, reg):
    if _opt(ctx, "door_refusals_weekly.csv", ("rule_id",)) is None:
        return False
    reg.add("door.ledger_window", ["2026-09-30", "2026-10-11"], "2026-09-30 to 2026-10-11 (12 days)",
            "prereg/ANALYSIS.md section 9",
            note="the door refusal ledger behind data/door_refusals_weekly.csv starts on 2026-09-30")


if __name__ == "__main__":
    sys.exit(standalone(run))
