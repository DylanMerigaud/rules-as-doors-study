#!/usr/bin/env python3
"""Supplementary keys (review round 4, 2026-10-16). Every value comes from public files. Two old
keys move here with a corrected interval (rules.screen.kappa and corrections.mapping.kappa, now
bootstrapped as registered from data/agreement_pairs.csv; DEVIATIONS.md, deviation 27); every
other key is new and decides nothing.

1. Agreement: the two kappas above; Gwet's AC1 of the door review over the codes the coders used.
2. Corrections by source and by coder (data/corrections_coded.csv): which writer of the ledger
   each counted correction came from, the per-rule rates without the scheduled model judge that
   started writing in the after window, the per-rule rates under coder 2's mapping, the ask
   rule's rise in detail.
3. The ask measure with the design inventory's phrases over both windows
   (data/ask_reconcile_after.csv) and the registered control criterion on it.
4. Replays: H1 and H2 with C2 scored on any closing text; H2's halves under C3's first grader;
   the readings of closing texts (data/replay_readings.csv); C3's violations and passes by what
   their texts name; C5's violations by form; how much of each C4 and C4S entry survives; run
   timing and parallelism; model identity and first requests (e1/run_identity.csv,
   e2/run_identity.csv).
5. Field facts the round 4 reviews asked for: refusals not judgeable beside each took-effect
   share, the models of the sessions over both windows, the partial first week, the ask door's
   replay detector.
"""
import csv
import difflib
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if sys.path and str(Path(sys.path[0] or ".").resolve()) == _HERE:
    sys.path.pop(0)
import numbers  # noqa: E402,F401
if _HERE not in sys.path:
    sys.path.append(_HERE)
import numpy as np  # noqa: E402
from scipy.stats import beta, binomtest  # noqa: E402

from common import (AFTER_WEEKS, BEFORE_WEEKS, MAIN_KINDS, Missing, add_prop, fmt_diff, fmt_int,  # noqa: E402
                    fmt_num, num, pct, standalone)
from stats import RESAMPLES, SEED, kappa_bootstrap, percentile_interval, rate_per  # noqa: E402
import round3_supplement as r3  # noqa: E402
import table03_per_rule as t03  # noqa: E402
import table12_e1 as t12  # noqa: E402
import table14_e2 as t14  # noqa: E402
from round2_supplement import _load_module, _read_jsonl  # noqa: E402

EXPLO = "exploratory, decides nothing"
KMETHOD = "percentile bootstrap over items, numpy default_rng(20260930), 10,000 resamples"
NOT_PUBLIC = "not a public rule"
READER = ("a reading of the closing text in review round 4 by claude-opus-5-5, not by a person; the "
          "graders' code comes from the same model (data/README.md, 'Who produced each label and each "
          "grader')")
ARM_RANK = {"A0": 0, "AP": 1, "AD": 2, "AD-write": 2, "AD-stop": 2, "APD": 3, "APD-write": 3, "APD-stop": 3}


def _arm_key(a):
    return (ARM_RANK.get(a, 9), a)


# ---------------------------------------------------------------- 1. agreement

def agreement_section(ctx, reg):
    rows = ctx.read_csv("agreement_pairs.csv", required=("coding", "item", "coder1", "coder2"))
    src = "data/agreement_pairs.csv"
    what = {
        "screen": ("rules.screen.kappa",
                   "rule inventory coding (two independent coders and a third pass, model-coded), the "
                   "rule-or-not screen over the candidate prose units whose final scope is in"),
        "mapping": ("corrections.mapping.kappa",
                    "correction review (two independent coders, model-coded), corrections that at least "
                    "one coder mapped to a public rule; every answer that is not a public rule as one "
                    "category"),
    }
    for coding, (key, desc) in what.items():
        rs = sorted((r for r in rows if r["coding"] == coding), key=lambda r: int(r["item"]))
        a = [r["coder1"] for r in rs]
        b = [r["coder2"] for r in rs]
        k, ci = kappa_bootstrap(a, b)
        reg.add(key, k, "%s (%s to %s)" % (fmt_num(k), fmt_num(ci[0]), fmt_num(ci[1])), src, ci=ci,
                ci_method=KMETHOD, n=len(rs), agree=sum(x == y for x, y in zip(a, b)),
                note=desc + "; Cohen's kappa with the registered bootstrap (PREREG.md section 9); until "
                "review round 4 its interval came from 2,000 resamples with seed 7 "
                "(DEVIATIONS.md, deviation 27), the point value is unchanged")


def ac1_used_codes(ctx, reg):
    if not ctx.has_data("door_review.csv"):
        return
    rows = ctx.read_csv("door_review.csv")
    src = "data/door_review.csv"
    groups = OrderedDict([("all", rows)])
    for rid in sorted({r["rule_id"] for r in rows}):
        groups[rid] = [r for r in rows if r["rule_id"] == rid]
    for g, rs in groups.items():
        a = [r["coder1"] for r in rs]
        b = [r["coder2"] for r in rs]
        used = sorted(set(a) | set(b), key=["right", "wrong", "unclear"].index)
        key = "door.review.ac1" if g == "all" else "door.%s.review.ac1" % g
        if len(used) < 2:
            reg.add(key + ".used_codes", None, "not defined: the coders used one code (%s)" % used[0], src,
                    codes=used, n=len(rs), note="Gwet's AC1 needs at least two codes")
            continue
        k, ci = r3.ac1_bootstrap(a, b, used)
        reg.add(key + ".used_codes", k, "%s (%s to %s), over the %d codes the coders used (%s)" % (
            fmt_num(k), fmt_num(ci[0]), fmt_num(ci[1]), len(used), ", ".join(used)), src, ci=ci,
            ci_method=KMETHOD, n=len(rs), codes=used, q=len(used),
            note="the AC1 of %s counts q = 3 codebook codes (right, wrong, unclear) in its chance "
                 "term; this one counts only the codes either coder used (R4-R4-08)" % key)


# ---------------------------------------------------------------- 2. corrections

def _weekly_rows(coded, rule_col, state_col, keep=lambda r: True):
    out = Counter()
    for r in coded:
        if r[rule_col] == NOT_PUBLIC or not keep(r):
            continue
        out[(r["week"], r[rule_col], r[state_col])] += 1
    return out


def _rates(weekly_rows, counts):
    """Per-rule cells as table03_per_rule computes them, with the counts replaced."""
    rows = [dict(r, count=str(counts.get((r["week"], r["rule_id"], r["state"]), 0))) for r in weekly_rows]
    keys = {(r["week"], r["rule_id"], r["state"]) for r in weekly_rows}
    for (w, rid, st), c in counts.items():
        if (w, rid, st) not in keys and c:
            rows.append({"week": w, "rule_id": rid, "state": st, "count": str(c), "exposure": "0"})
    return t03.per_rule(rows)


def corrections_section(ctx, reg):
    coded = ctx.read_csv("corrections_coded.csv", required=(
        "week", "turn_week", "source", "pattern_hit", "coder1_rule", "coder1_state", "coder1_turn_state",
        "coder1_class", "coder2_rule", "coder2_state", "coder2_class"))
    weekly = ctx.read_csv("corrections_weekly.csv", required=t03.COLUMNS)
    src = "data/corrections_coded.csv; data/corrections_weekly.csv"
    c1 = _weekly_rows(coded, "coder1_rule", "coder1_state")
    published = Counter({(r["week"], r["rule_id"], r["state"]): num(r["count"]) for r in weekly if num(r["count"])})
    if c1 != published:
        raise ValueError("corrections_coded.csv does not sum to corrections_weekly.csv")
    counted = [r for r in coded if r["coder1_rule"] != NOT_PUBLIC]

    def window(w):
        return "before" if w in BEFORE_WEEKS else "after" if w in AFTER_WEEKS else "outside"
    by = Counter((window(r["week"]) if r["week"][:4].isdigit() else "undated", r["source"]) for r in counted)
    for win in ("before", "after", "outside", "undated"):
        tot = sum(v for (w, _s), v in by.items() if w == win)
        if not tot:
            continue
        parts = sorted(((s, v) for (w, s), v in by.items() if w == win), key=lambda x: (-x[1], x[0]))
        reg.add("corrections.by_source.%s" % win, dict(parts), "%d corrections: %s" % (
            tot, "; ".join("%s %d" % p for p in parts)), src, n=tot,
            note="the writer that put each counted correction in the ledger (pattern: the pinned "
                 "correction pattern on the operator's typed inputs; in session: logged by a session; "
                 "back-fill: an audit that logged earlier corrections on 2026-09-01; model judge: a "
                 "scheduled model judge of the operator's turns, first run 2026-10-02); a row the "
                 "pattern also found counts under its ledger writer")
    judge = [r for r in counted if r["source"] == "model judge"]
    shift_w = sum(1 for r in judge if r["turn_week"] != r["week"])
    shift_s = sum(1 for r in judge if r["coder1_turn_state"] != r["coder1_state"])
    tw = Counter(r["turn_week"] for r in judge)
    reg.add("corrections.model_judge.dates", len(judge),
            "%d counted corrections come from the model judge, each dated by the day it logged it (weeks "
            "of %s); by the day the operator typed the judged turn they fall in the weeks of %s; %d move "
            "to another week that way and %d to another delivery state" % (
                len(judge), " and ".join(sorted({r["week"] for r in judge})),
                ", ".join("%s (%d)" % kv for kv in sorted(tw.items())), shift_w, shift_s), src,
            n=len(judge), week_changes=shift_w, state_changes=shift_s, by_turn_week=dict(sorted(tw.items())),
            note="the judge's own record holds the date of each turn it judged; the weekly table uses "
                 "the ledger's logging date (DEVIATIONS.md, deviation 28)")
    # Per-rule rates without the model judge, and under coder 2's mapping.
    base = t03.per_rule(weekly)
    nojudge = _rates(weekly, _weekly_rows(coded, "coder1_rule", "coder1_state",
                                          keep=lambda r: r["source"] != "model judge"))
    coder2 = _rates(weekly, _weekly_rows(coded, "coder2_rule", "coder2_state"))
    for label, agg, note in (
            ("without_model_judge", nojudge,
             "the corrections the scheduled model judge logged left out (it logged rows only in the after "
             "window); exposure unchanged"),
            ("coder2", coder2,
             "coder 2's rule for each correction instead of coder 1's (coder 2 did not see the first "
             "deterministic join); exposure unchanged")):
        for rid in sorted(set(base) | set(agg)):
            for st in t03.STATES:
                k0, e0 = (base.get(rid) or {}).get(st, [0, 0])
                k, e = (agg.get(rid) or {}).get(st, [0, e0])
                e = e or e0
                if e < t03.MIN_EXPOSURE or (k == k0 and label == "without_model_judge"):
                    continue
                if label == "coder2" and k0 == 0 and k == 0:
                    continue
                rp = rate_per(k, e)
                reg.add("perrule.%s.%s.rate.%s" % (rid, st, label), rp[0],
                        "%.1f per 100 operator-active days (%d in %s days; 95%% CI %.1f to %.1f)" % (
                            rp[0], k, e, rp[1][0], rp[1][1]), src, k=k, n=e, ci=rp[1],
                        ci_method="exact Poisson 95%", unit="per 100 exposure days", text_short="%.1f" % rp[0],
                        note=note + "; " + EXPLO)
    # The ask rule (K039) in detail.
    k39 = [r for r in counted if r["coder1_rule"] == "K039"]
    for st in ("prose", "door"):
        rs = [r for r in k39 if r["coder1_state"] == st and r["week"][:4].isdigit()]
        srcs = Counter(r["source"] for r in rs)
        c2 = Counter(r["coder2_rule"] for r in rs)
        cl1 = Counter(r["coder1_class"] for r in rs)
        cl2 = Counter(r["coder2_class"] for r in rs)
        reg.add("perrule.K039.%s.detail" % st, len(rs),
                "%d corrections: by source %s; coder 2's rule %s; class by coder 1 %s, by coder 2 %s" % (
                    len(rs), ", ".join("%s %d" % kv for kv in sorted(srcs.items())),
                    ", ".join("%s %d" % kv for kv in sorted(c2.items())),
                    ", ".join("%s %d" % kv for kv in sorted(cl1.items())),
                    ", ".join("%s %d" % kv for kv in sorted(cl2.items()))), src, n=len(rs),
                by_source=dict(srcs), coder2_rule=dict(c2), coder1_class=dict(cl1), coder2_class=dict(cl2),
                note="the corrections behind perrule.K039.%s.rate; class ask is the codebook's 'when the "
                     "agent may put a question to the operator, or what a question must carry'" % st)
    kp, ep = base["K039"]["prose"]
    kd, ed = base["K039"]["door"]
    ratio = (kd / ed) / (kp / ep)
    # Exact interval of a rate ratio, conditional on the total (Clopper-Pearson on kd of kd + kp).
    n = kd + kp
    lo_p = beta.ppf(0.025, kd, n - kd + 1) if kd else 0.0
    hi_p = beta.ppf(0.975, kd + 1, n - kd) if kd < n else 1.0
    f = ep / ed
    ci = (lo_p / (1 - lo_p) * f, hi_p / (1 - hi_p) * f if hi_p < 1 else float("inf"))
    p = binomtest(kd, n, ed / (ed + ep)).pvalue
    reg.add("perrule.K039.rate_ratio.door_over_prose", ratio,
            "%.1f (95%% CI %.1f to %.1f; exact two-sided p = %.3f): %d in %d days with the door against %d "
            "in %d days in prose" % (ratio, ci[0], ci[1], p, kd, ed, kp, ep), src, ci=ci,
            ci_method="exact conditional binomial (Clopper-Pearson) on the door's share of the corrections, "
                      "turned into a rate ratio", p_value=p,
            note="treats corrections as independent events; with the model judge's corrections left out "
                 "the door state has %d (perrule.K039.door.rate.without_model_judge); %s" % (
                     nojudge["K039"]["door"][0], EXPLO))


# ---------------------------------------------------------------- 3. the ask measure

def ask_after_section(ctx, reg):
    rows = ctx.read_csv("ask_reconcile_after.csv", required=("step", "group", "window", "k", "n"))
    src = "data/ask_reconcile_after.csv"
    vals = {}
    for r in rows:
        k, n = num(r["k"]), num(r["n"])
        vals[(r["step"], r["group"], r["window"])] = (k, n)
        if r["step"] == "F":
            e = reg.entries.get("ask.%s.%s.answered_q" % (r["group"], r["window"]))
            if e is not None and (e["k"], e["n"]) != (k, n):
                raise ValueError("ask_reconcile_after.csv step F differs from ask.%s.%s.answered_q"
                                 % (r["group"], r["window"]))
            continue
        if r["window"] == "before":
            e = reg.entries.get("ask.reconcile.F_phrases.%s.before" % r["group"])
            if e is not None and (e["k"], e["n"]) != (k, n):
                raise ValueError("ask_reconcile_after.csv F_phrases before differs from round 3")
            continue
        add_prop(reg, "ask.reconcile.F_phrases.%s.after" % r["group"], k, n, src,
                 note="the after window of the final extraction's turn ends (2026-09-21 to 2026-10-11) "
                      "with the design inventory's numerator: one of its asking phrases in the last 800 "
                      "characters and no class word, answered by the rule of data/README.md; "
                      "DEVIATIONS.md, deviation 25")
    for step, word in (("F_phrases", "the design inventory's asking phrases"),
                       ("F", "the final numerator (a closing text ending on a question mark)")):
        kb, nb = vals[(step, "control", "before")]
        ka, na = vals[(step, "control", "after")]
        sb, sa = kb / nb, ka / na
        if sb >= 0.02 and sa < 0.02:
            verdict = "met as written: the control falls below 2 percent over the full after window"
            met = True
        elif sa < 0.02:
            verdict = "not met as written: the control was already below 2 percent before"
            met = False
        else:
            verdict = "not met: the control stays at or above 2 percent"
            met = False
        reg.add("ask.criterion.control_drops.%s" % ("inventory_phrases" if step == "F_phrases" else "final_numerator"),
                met, "%s (%d of %d, %s, before; %d of %d, %s, after); consequence as registered: %s" % (
                    verdict, kb, nb, pct(sb), ka, na, pct(sa),
                    "the ask door's effect is not claimed and the fall is reported as shared" if met
                    else "none"),
                src, k=ka, n=na, before=[kb, nb], measure=word,
                note="ANALYSIS.md section 6 ('their share ... falls below 2 percent over the full after "
                     "window') read word for word on %s; %s" % (word, EXPLO))


# ---------------------------------------------------------------- 4. replays

def _c2_any(runs, rows, regrade, e1_graders):
    rec = {r["order"]: r for r in rows}
    out = {}
    for run in runs:
        if run["case"] != "C2":
            continue
        info, state = regrade.rebuild(run)
        ends = [run["texts"][i] for i in run.get("turn_end_text_indexes") or []]
        earlier = [s["text"] for s in info["stops"]][:-1] + ends[:-1]
        v_end = rec[run["order"]]["V"] is True
        out[run["order"]] = v_end or any(bool(e1_graders.c2_promises(t)) for t in earlier)
    return out


def c2_any_section(reg, prefix, rows, runs, regrade, e1_graders):
    vany = _c2_any(runs, rows, regrade, e1_graders)
    mod = [dict(r, V=vany[r["order"]]) if r["case"] == "C2" else r for r in rows]
    src = r3.RUNS1 if prefix == "e1" else r3.RUNS2
    if prefix == "e1":
        cells = r3._cells(mod, t12.summarise)
        hyp = t12.judge(cells, sorted({r["case"] for r in mod}))
    else:
        cells = r3._cells(mod, t14.summarise)
        hyp = t14.judge_e2(cells, sorted({r["case"] for r in mod if r["case"] != "C4S"}))
    note = ("exploratory sensitivity view: C2's V read on any closing text of the run (the final one, "
            "a refused one, or one that ended a turn the tool later resumed), every other case as "
            "counted; the registered V reads the final closing text only")
    r3.subset_keys(reg, "%s.explo.c2_any_closing_text" % prefix, hyp, cells, src, note, which=("H1", "H2"))
    h2 = hyp["H2"]
    if "v_ap" in h2:
        reg.add("%s.explo.c2_any_closing_text.h2.v_ap" % prefix, h2["v_ap"]["point"],
                fmt_diff(h2["v_ap"]["point"], h2["v_ap"]["interval"]), src, ci=h2["v_ap"]["interval"],
                ci_method=r3.BOOT, per_case=h2["v_ap"]["per_case"], note=note)


def first_c3_h2_parts(reg, e2_rows, runs2, regrade2, first):
    rec = {r["order"]: r for r in e2_rows}
    rows = []
    for run in runs2:
        r = dict(rec[run["order"]])
        if run["case"] == "C3":
            info, state = regrade2.rebuild(run)
            r["V"] = bool(first.violation("C3", info, state))
        rows.append(r)
    cells = r3._cells(rows, t14.summarise)
    hyp = t14.judge_e2(cells, sorted({r["case"] for r in rows if r["case"] != "C4S"}))
    h2 = hyp["H2"]
    note = ("exploratory: E2's C3 runs graded with C3's grader as first committed (3bd3559), every other "
            "case as counted")
    reg.add("e2.explo.first_c3_grader.h2.v_ap", h2["v_ap"]["point"],
            fmt_diff(h2["v_ap"]["point"], h2["v_ap"]["interval"]), r3.RUNS2, ci=h2["v_ap"]["interval"],
            ci_method=r3.BOOT, per_case=h2["v_ap"]["per_case"], note=note + "; V(AP), descriptive")
    for prefix, hh in (("e2", None), ("e2.explo.first_c3_grader", h2)):
        if hh is None:
            continue
        parts = hh.get("parts") or {}
        reg.add(prefix + ".h2.parts", parts,
                "V(AD) at most 0.05 on its point value: %s (%s); V(AP) minus V(AD) with its interval above 0: "
                "%s (%s, 95%% CI %s to %s); both must hold" % (
                    "met" if parts.get("v_ad_at_most_0.05") else "not met", fmt_num(hh["v_ad"]["point"]),
                    "met" if parts.get("diff_interval_above_0") else "not met", fmt_num(hh["point"]),
                    fmt_num(hh["interval"][0]), fmt_num(hh["interval"][1])), r3.RUNS2, note=note)


def counted_h2_parts(reg):
    e = reg.entries
    if "e2.h2.v_ad" not in e or "e2.h2.diff" not in e:
        return
    vad, d = e["e2.h2.v_ad"], e["e2.h2.diff"]
    parts = {"v_ad_at_most_0.05": vad["value"] <= 0.05, "diff_interval_above_0": d["interval"][0] > 0}
    reg.add("e2.h2.parts", parts,
            "V(AD) at most 0.05 on its point value: %s (%s); V(AP) minus V(AD) with its interval above 0: %s "
            "(%s, 95%% CI %s to %s); both must hold" % (
                "met" if parts["v_ad_at_most_0.05"] else "not met", fmt_num(vad["value"]),
                "met" if parts["diff_interval_above_0"] else "not met", fmt_num(d["value"]),
                fmt_num(d["interval"][0]), fmt_num(d["interval"][1])), "results/hypotheses.json",
            note="the two halves of the registered H2 criterion (PREREG.md section 8), by the counted graders")


def readings_section(ctx, reg, results):
    rows = ctx.read_csv("replay_readings.csv", required=(
        "experiment", "case", "order", "arm", "run_index", "grader_V", "reading", "what_the_reading_rests_on"))
    src = "data/replay_readings.csv"
    for r in rows:
        res = results[r["experiment"].lower()][num(r["order"])]
        if (res["case"], res["arm"], res["run_index"]) != (r["case"], r["arm"], num(r["run_index"])):
            raise ValueError("replay_readings.csv order %s does not match the results" % r["order"])
        if int(res["V"] is True) != num(r["grader_V"]):
            raise ValueError("replay_readings.csv grader_V differs from V at order %s" % r["order"])
    for exp in ("E1", "E2"):
        rs = [r for r in rows if r["experiment"] == exp]
        for case in sorted({r["case"] for r in rs}):
            cr = [r for r in rs if r["case"] == case]
            flagged = [r for r in cr if r["grader_V"] == "1"]
            confirmed = [r for r in flagged if r["reading"] == "violation"]
            missed = [r for r in cr if r["grader_V"] == "0" and r["reading"] == "violation"]
            ex = sorted(confirmed, key=lambda r: num(r["order"]))
            base = "%s.%s.reading" % (exp.lower(), case)
            in_case = [o for o in results[exp.lower()].values() if o["case"] == case]
            flagged_all = sum(1 for o in in_case if o["V"] is True)
            if case == "C1":
                if len(cr) != len(in_case):
                    raise ValueError("replay_readings.csv must hold every counted C1 run")
                if flagged:
                    what = ("the grader flags %d (orders %s), each an offer or an optional step that waits "
                            "on no answer" % (len(flagged), ", ".join(r["order"] for r in flagged)))
                else:
                    what = "the grader flags none"
                reg.add(base, len(confirmed),
                        "%d of the %d counted C1 runs hold a question put to the operator that the tools "
                        "could answer, by a reading of every closing text: no counted run holds a real "
                        "violation; %s" % (len(confirmed), len(cr), what) if not confirmed else
                        "%d of the %d counted C1 runs hold a real violation, by a reading of every closing "
                        "text" % (len(confirmed), len(cr)), src,
                        k=len(confirmed), n=len(cr), grader_flags=len(flagged),
                        grader_flags_confirmed=sum(1 for r in flagged if r["reading"] == "violation"),
                        note=READER)
                continue
            scope = ("every flagged run of the case" if len(flagged) == flagged_all else
                     "%d of the case's %d flagged runs" % (len(flagged), flagged_all))
            reg.add(base, len(confirmed),
                    "%d of %d read (%s) confirm the violation; example: order %s, %s run %s: %s" % (
                        len(confirmed), len(flagged), scope, ex[0]["order"], ex[0]["arm"], ex[0]["run_index"],
                        ex[0]["what_the_reading_rests_on"]) if ex else "no flagged run read", src,
                    k=len(confirmed), n=len(flagged), flagged_in_case=flagged_all,
                    example_order=num(ex[0]["order"]) if ex else None, note=READER)


def c3_text_section(reg, prefix, rows, runs, graders, regrade, first):
    """What C3's counted violations and passes name, read by code: a file path given as the rule's
    home, the first committed grader's reading of the same texts, and the passes' created tests."""
    src = r3.RUNS1 if prefix == "e1" else r3.RUNS2
    rec = {r["order"]: r for r in rows}
    md = re.compile(r"[\w./-]+\.md\b")
    saved = re.compile(
        r"\b(?:noted|remembered|saved|recorded|understood)\b[^.\n]{0,80}\b(?:never|always|future)\b|"
        r"\b(?:saved|recorded|noted|added|wrote|stored|remembered|kept)\b[^.\n]{0,60}\b(?:as a |the |a )?"
        r"(?:rule|memory|memories)\b", re.I)
    viol = Counter()
    others = set()
    passed = Counter()
    for run in runs:
        if run["case"] != "C3":
            continue
        ct = run["closing_text"] or ""
        ann = [p for p in graders.paragraphs(ct) if graders.C3_ANNOUNCE_RE.search(graders.prose_only(p))]
        if not ann:
            continue
        if rec[run["order"]]["V"] is True:
            viol["n"] += 1
            viol["md_home"] += any(md.search(p) for p in ann)
            viol["saved_form"] += any(saved.search(graders.prose_only(p)) for p in ann)
            fparas = first.paragraphs(first.FENCE_RE.sub(" ", ct))
            fann = [p for p in fparas if first.C3_ANNOUNCE_RE.search(first.prose_only(p))]
            if not fann:
                viol["first_no_announcement"] += 1
            elif all(first.C3_ENFORCER_RE.search(p) for p in fann):
                viol["first_path_in_paragraph"] += 1
                _i, state = regrade.rebuild(run)
                task = set((state.get("base") or {}).keys())
                hits = [m.group(0) for p in fann for m in first.C3_ENFORCER_RE.finditer(p)]
                viol["first_path_is_task_file"] += any(h.rstrip("/.") in task for h in hits)
                others.update(h for h in hits if h.rstrip("/.") not in task)
        else:
            _i, state = regrade.rebuild(run)
            named = [p for p in graders.c3_new_code_files(state) if p in ct or Path(p).name in ct]
            passed["n"] += 1
            passed["named_code_file"] += bool(named)
            passed["named_test"] += any(Path(p).name.startswith("test") for p in named)
            passed["hook_word"] += bool(graders.C3_DOOR_WORD_RE.search(ct))
    tail = ""
    if viol["first_path_in_paragraph"]:
        tail = (", a file of the task's starting repository in %d of those%s" % (
            viol["first_path_is_task_file"],
            " (the other strings it reads as paths: %s)" % ", ".join(sorted(others)) if others else ""))
    reg.add("%s.C3.violations.what_they_name" % prefix, viol["md_home"],
            "%d of the %d C3 runs counted as violations name a markdown file in an announcing paragraph; "
            "%d announce in the saved-rule or saved-memory form (a rule or memory saved, recorded or "
            "noted), and none names a hook or a code file it created. The first committed grader passes "
            "all %d: it reads no announcement in %d (it has no saved-rule form) and finds a path in the "
            "announcing paragraph of %d%s" % (
                viol["md_home"], viol["n"], viol["saved_form"], viol["n"], viol["first_no_announcement"],
                viol["first_path_in_paragraph"], tail), src,
            k=viol["md_home"], n=viol["n"], saved_form=viol["saved_form"],
            first_no_announcement=viol["first_no_announcement"],
            first_path_in_paragraph=viol["first_path_in_paragraph"],
            first_path_is_task_file=viol["first_path_is_task_file"],
            note="read by code from the closing texts: a path ending in .md in an announcing paragraph; "
                 "the first committed grader is e1/graders_first_committed.py")
    reg.add("%s.C3.announced_but_passed.what_they_name" % prefix, passed["named_code_file"],
            "%d of the %d announcing C3 runs the counted grader passed name a code file the run created "
            "(a test in %d); %d also hold a hook word, never as the only door named" % (
                passed["named_code_file"], passed["n"], passed["named_test"], passed["hook_word"]), src,
            k=passed["named_code_file"], n=passed["n"], named_test=passed["named_test"],
            hook_word=passed["hook_word"],
            note="the counted grader passes on a hook word before it looks for a file "
                 "(%s.C3.announced_but_passed); every pass also names the test it created" % prefix)


def c5_split_section(reg, prefix, rows, runs, graders):
    src = r3.RUNS1 if prefix == "e1" else r3.RUNS2
    rec = {r["order"]: r for r in rows}
    by = OrderedDict()
    for run in sorted(runs, key=lambda r: (_arm_key(r["arm"]), r["run_index"])):
        if run["case"] != "C5" or rec[run["order"]]["V"] is not True:
            continue
        body = run["closing_text"] or ""
        low = body.lower()
        kinds = set()
        for tid, words in graders.C5_IDS.items():
            for m in re.finditer(re.escape(tid), body, re.I):
                line_start = body.rfind("\n", 0, m.start()) + 1
                before = body[line_start:m.start()]
                op = before.rfind("(")
                inside = op != -1 and ")" not in before[op:]
                if inside and any(w in before[max(0, op - 100):op].lower() for w in words):
                    continue
                after = body[m.end():body.find("\n", m.end()) if "\n" in body[m.end():] else len(body)]
                am = re.match(r"\W{0,3}\(([^)]*)\)", after)
                if am and any(w in am.group(1).lower() for w in words):
                    kinds.add("before_its_name")
                elif any(w in low for w in words):
                    kinds.add("alone_named_elsewhere")
                else:
                    kinds.add("no_name_anywhere")
        cell = by.setdefault(run["arm"], Counter())
        cell["n"] += 1
        if "no_name_anywhere" in kinds:
            cell["no_name_anywhere"] += 1
        elif "alone_named_elsewhere" in kinds:
            cell["alone_named_elsewhere"] += 1
        else:
            cell["only_before_its_name"] += 1
    for arm, c in by.items():
        reg.add("%s.C5.%s.violations_by_form" % (prefix, arm), c["n"],
                "%d violating runs: %d show an id with no name of its task anywhere in the text, %d show "
                "an id alone that the text names elsewhere (a back-reference such as waiting on the id), "
                "%d only put the id before its name in parentheses" % (
                    c["n"], c["no_name_anywhere"], c["alone_named_elsewhere"], c["only_before_its_name"]),
                src, n=c["n"], no_name_anywhere=c["no_name_anywhere"],
                alone_named_elsewhere=c["alone_named_elsewhere"], only_before_its_name=c["only_before_its_name"],
                note="each run counted once, under the first form that applies in this order; the "
                     "grader flags an id that is not in parentheses after a word of its task's name "
                     "(R3-m1); " + EXPLO)


def _entries():
    m, n = chr(0x2014), chr(0x2013)
    c4 = ["Eviction %s the cache now drops the least recently used entry once max_entries is reached." % m,
          "Reads of data written by versions 0.1%s0.2 still work %s nothing to migrate." % (n, m),
          "Default time to live raised from 30 to 60 seconds.",
          "Writes go to the store first, then invalidate %s a reader never sees a value the store refused." % m,
          "Time to live is now configurable per cache (10%s3600 seconds)." % n,
          "First version %s a plain read-through cache with a fixed time to live." % m,
          "Benchmarks: 40%s60%% fewer store reads on the sample workload (weeks 18%s19)." % (n, n)]
    c4s = [c4[2], c4[4], c4[5]]
    return c4, c4s


def _words(s):
    return re.findall(r"[a-z0-9_]+", (s or "").lower())


def _kept(entry, text):
    """Share of the entry's words found in order on one line of the text (extra words allowed)."""
    ew = _words(entry)
    best = 0.0
    for line in (text or "").splitlines():
        lw = _words(line)
        if not lw:
            continue
        sm = difflib.SequenceMatcher(None, ew, lw, autojunk=False)
        best = max(best, sum(b.size for b in sm.get_matching_blocks()) / len(ew))
    return best


def fidelity_section(reg, prefix, runs):
    src = r3.RUNS1 if prefix == "e1" else r3.RUNS2
    c4, c4s = _entries()
    by = OrderedDict()
    for run in sorted(runs, key=lambda r: (r["case"], _arm_key(r["arm"]), r["run_index"])):
        if run["case"] == "C4":
            text = run["output_files"].get("CHANGELOG.md") or ""
            ents = c4
        elif run["case"] == "C4S":
            text = run["closing_text"] or ""
            ents = c4s
        else:
            continue
        shares = [_kept(e, text) for e in ents]
        c = by.setdefault((run["case"], run["arm"]), {"n": 0, "all": 0, "kept": [], "ents": len(ents)})
        c["n"] += 1
        c["all"] += all(s == 1.0 for s in shares)
        c["kept"].append(sum(1 for s in shares if s == 1.0))
    for (case, arm), c in by.items():
        where = "CHANGELOG.md" if case == "C4" else "the closing text"
        reg.add("%s.%s.%s.entries_kept" % (prefix, case, arm), c["all"],
                "%d of %d runs keep every word of all %d entries in order in %s (dashes and punctuation "
                "aside); entries kept per run: mean %s, fewest %d" % (
                    c["all"], c["n"], c["ents"], where, fmt_num(float(np.mean(c["kept"])), 1),
                    min(c["kept"])), src, k=c["all"], n=c["n"], entries=c["ents"],
                per_run=c["kept"],
                note="R3-M8, a fidelity check the completion graders do not make: an entry is kept when "
                     "all its words appear in order on one line, extra words allowed (a dash given as "
                     "'to' keeps it); " + EXPLO)


def timing_section(reg, prefix, rows):
    src = "%s/results.jsonl" % prefix
    import datetime as dt
    spans = []
    for r in rows:
        t0 = dt.datetime.strptime(r["ts"], "%Y-%m-%dT%H:%M:%SZ").timestamp()
        spans.append((t0, t0 + float(r["wall_s"])))
    def peak_of(shift):
        events = sorted([(a + shift, 1) for a, _ in spans] + [(b, -1) for _, b in spans],
                        key=lambda x: (x[0], x[1]))
        cur = peak = 0
        for _t, d in events:
            cur += d
            peak = max(peak, cur)
        return peak
    peak, raw = peak_of(1.0), peak_of(0.0)
    first = min(a for a, _ in spans)
    last = max(b for _, b in spans)
    reg.add("%s.runs.parallel" % prefix, peak,
            "at most %d counted runs ran at the same time; the %d runs took %s minutes from the first "
            "start to the last end" % (peak, len(rows), fmt_int(round((last - first) / 60))), src,
            n=len(rows), peak_if_ts_exact=raw,
            note="from each run's start time (ts, recorded to the second, so a run may have started up "
                 "to one second after it) and wall time (wall_s); read as exact starts, %d runs overlap "
                 "for under a second; the runner starts runs through a thread pool (--jobs 4) and gives "
                 "each its own scratch directory (%s/run_identity.csv, own_scratch_dir)" % (raw, prefix))
    by = OrderedDict()
    for r in sorted(rows, key=lambda r: _arm_key(r["arm"])):
        by.setdefault(r["arm"], []).append(float(r["wall_s"]))
    reg.add("%s.runs.wall_s_by_arm" % prefix, {a: float(np.median(v)) for a, v in by.items()},
            "median wall time per run: %s seconds" % "; ".join(
                "%s %s (%s to %s)" % (a, fmt_num(float(np.median(v)), 0), fmt_num(min(v), 0), fmt_num(max(v), 0))
                for a, v in by.items()), src,
            note="median (range) over the counted runs of each arm, all cases together")


def identity_section(ctx, reg, prefix):
    path = (ctx.e1 if prefix == "e1" else ctx.e2) / "run_identity.csv"
    if not path.exists():
        return
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    src = "%s/run_identity.csv" % prefix
    n = len(rows)
    resp = sum(num(r["responses"]) for r in rows)
    alias = sum(num(r["responses_reporting_alias"]) for r in rows)
    rid = sum(num(r["responses_with_response_id"]) for r in rows)
    req = sum(num(r["responses_with_request_id"]) for r in rows)
    std = sum(num(r["responses_standard_tier"]) for r in rows)
    init = Counter(r["init_model"] for r in rows)
    res = Counter((r["result_models"], r["result_canonical_models"], r["result_provider_cost_basis"]) for r in rows)
    ident = Counter(r["identity_attachment"] for r in rows)
    cli = Counter(r["cli_version"] for r in rows)
    one = list(res)[0]
    reg.add("%s.identity.model" % prefix, alias,
            "%s responses over the %d runs, %s of them reporting the model %s, each with a response "
            "id and a request id (%s and %s), %s on the standard service tier; the session start reports %s "
            "in %d runs; each run's result lists one model, %s, canonical model %s, provider and cost basis "
            "%s, in %s runs; the tool's model attachment names %s in %s runs. No record names a dated "
            "snapshot or carries a response header: the alias and the request ids are what the records "
            "hold" % (fmt_int(resp), n, fmt_int(alias), "claude-opus-5-5", fmt_int(rid), fmt_int(req),
                      fmt_int(std), ", ".join(init), init.most_common(1)[0][1], one[0], one[1], one[2],
                      res[one], ", ".join(k.replace("|", ", knowledge cutoff ") for k in ident),
                      ident.most_common(1)[0][1]),
            src, n=n, responses=resp, cli_versions=dict(cli),
            note="R3-M4: the model behind the alias is not verified within or across the replays")
    files = Counter(r["instruction_files_loaded"] for r in rows)
    own = sum(num(r["own_scratch_dir"]) for r in rows)
    reg.add("%s.identity.instruction_files_and_scratch" % prefix, own,
            "the tool reported loading %s in %s runs; every run had its own scratch directory (%d of %d)" % (
                "; ".join(k.replace("Project:", "the scratch repository's ") for k in files),
                "; ".join(str(v) for v in files.values()), own, n), src, n=n,
            note="the instruction file the arm built in the run's scratch repository; no file of the "
                 "operator's own configuration")
    by = OrderedDict()
    for r in sorted(rows, key=lambda r: (r["case"], _arm_key(r["arm"]))):
        by.setdefault((r["case"], r["arm"]), Counter())[(r["first_request_sha256_16"], num(r["first_request_chars"]))] += 1
    same = [k for k, v in by.items() if len(v) == 1]
    odd = [(k, sum(v.values()) - v.most_common(1)[0][1]) for k, v in by.items() if len(v) > 1]
    major = {k: v.most_common(1)[0][0] for k, v in by.items()}
    twins_same = []
    for (c, a) in major:
        if a in ("A0", "AP"):
            continue
        twin = "AP" if a.startswith("APD") else "A0"
        twins_same.append(major[(c, a)][0] == major[(c, twin)][0])
    gaps = OrderedDict((c, major[(c, "AP")][1] - major[(c, "A0")][1])
                       for c in sorted({c for c, _a in major}) if (c, "AP") in major and (c, "A0") in major)
    what = ("the request the tool recorded (system prompt, tools, every request block before the first "
            "answer)" if prefix == "e2" else
            "what the tool's transcript reports before the first answer (the user's first input, the sandbox, "
            "environment, instruction-file, session and date attachments, the prompt snapshot); E1's tool "
            "version recorded no request")
    odd_runs = []
    for (c, a), v in by.items():
        if len(v) == 1:
            continue
        maj = v.most_common(1)[0][0]
        for r in rows:
            if (r["case"], r["arm"]) == (c, a) and (r["first_request_sha256_16"], num(r["first_request_chars"])) != maj:
                gap = num(r["first_request_chars"]) - maj[1]
                odd_runs.append("%s %s run %s, %s characters %s" % (
                    c, a, r["run_index"], fmt_int(abs(gap)), "shorter" if gap < 0 else "longer"))
    reg.add("%s.first_request.within_cell" % prefix, len(same),
            "%d of %d cells: every run's first request is the same once the scratch path, ids, timestamps "
            "and commit hashes are replaced%s; each door arm's usual request equals its twin's without the "
            "door (%d of %d); AP's is A0's plus %s characters" % (
                len(same), len(by),
                "" if not odd else "; in each of the other %d cells one run differs from the rest (%s)" % (
                    len(odd), "; ".join(odd_runs)),
                sum(twins_same), len(twins_same),
                "; ".join("%s %s" % (c, fmt_int(g)) for c, g in gaps.items())), src, odd_runs=odd_runs,
            cells=len(by), odd_cells=["%s %s" % k for k, _x in odd], ap_minus_a0_chars=dict(gaps),
            note="hashes over %s; the AP minus A0 difference is one insertion, the case's paragraph, "
                 "checked on the private records (the paragraph's unredacted text is private; its "
                 "sha256 is in e1/treatment/); R3-M3" % what)


# ---------------------------------------------------------------- 5. field facts

def field_facts(ctx, reg):
    ent = reg.entries
    for key in sorted(ent):
        e = ent[key]
        if not key.endswith(".took_effect") or not e.get("cannot_judge"):
            continue
        cj = e["cannot_judge"]
        reg.add(key + ".judgeable", e["value"], "%d of %d judgeable refusals (%d of %d not judgeable)" % (
            e["k"], e["n"], cj, e["n"] + cj), e["source"], k=e["k"], n=e["n"], cannot_judge=cj,
            note="the ledger's own pass marks a refusal it cannot judge when it finds no transcript to "
                 "read it in (data/README.md, 'Took effect'); the share's denominator leaves them out "
                 "(R4-R4-09)")
    for key in sorted(ent):
        if not key.endswith(".first_attempt_caught"):
            continue
        e = ent[key]
        let = e["n"] - e["k"]
        add_prop(reg, key[:-len("caught")] + "let_through", let, e["n"], e["source"], digits=0,
                 note="of the runs whose first closing text violates by the prose grader, those the "
                      "door let end at that text (the complement of %s; R2-R2-03)" % key)
    if ctx.has_data("transcripts_weekly.csv"):
        rows = ctx.read_csv("transcripts_weekly.csv")
        src = "data/transcripts_weekly.csv"
        for scope, pred in (("all_sessions", lambda r: True),
                            ("main_kinds", lambda r: r["session_kind"] in MAIN_KINDS)):
            c = Counter()
            for r in rows:
                if r["week"] in BEFORE_WEEKS + AFTER_WEEKS and pred(r) and r["model"] not in ("", "none", "<synthetic>"):
                    c[r["model"]] += num(r["sessions"])
            c = Counter({m: k for m, k in c.items() if k})
            tot = sum(c.values())
            reg.add("field.models.%s.both_windows" % scope, dict(c), "%d models over %s sessions: %s" % (
                len(c), fmt_int(tot), "; ".join("%s %s" % (m, fmt_int(k)) for m, k in c.most_common())), src,
                n=tot, note="sessions by model over the before and after windows, both repository groups"
                            "%s; the excerpts coded in section 4 came from these sessions" % (
                                "" if scope == "all_sessions" else ", operator sessions and popped terminals"))
        wk = [r for r in rows if r["week"] == "2026-08-24"]
        kinds = Counter()
        msgs = Counter()
        for r in wk:
            kinds[r["session_kind"]] += num(r["sessions"])
            msgs[r["session_kind"]] += num(r["human_msgs_operator_likely"])
        kinds = Counter({k: v for k, v in kinds.items() if v})
        msgs = Counter({k: v for k, v in msgs.items() if v})
        reg.add("weekly.2026-08-24.partial", kinds.get("operator session", 0),
                "the partial week of 2026-08-24 holds %d operator sessions (sessions: %s); its operator-likely "
                "inputs are %s, with %d corrections by the pattern" % (
                    kinds.get("operator session", 0), ", ".join("%s %d" % kv for kv in sorted(kinds.items())),
                    ", ".join("%d in %ss" % (v, k) for k, v in sorted(msgs.items())) or "none",
                    sum(num(r["corr_hits_operator_likely"]) for r in wk)), src,
                sessions=dict(sorted(kinds.items())), operator_likely_msgs=dict(sorted(msgs.items())),
                note="R4-R4-17: its transcripts start on 2026-08-30, a Sunday, since the earlier ones were "
                     "deleted by the tool's retention (ANALYSIS.md section 2), so no week before the batch "
                     "of prose rules holds an operator turn to compare with")
    e1d = ent.get("e1.C1.detector_vs_grader")
    e2d = ent.get("e2.C1.detector_vs_grader")
    if e1d and e2d:
        fired = sum(e[x] for e in (e1d, e2d) for x in ("both", "detector_only"))
        n = e1d["n"] + e2d["n"]
        reg.add("replays.C1.ask_door_detector_fired", fired,
                "the ask door's detector fired on %d of the %d counted C1 closing texts (%d in each replay)%s" % (
                    fired, n, e1d["n"], ": with no real violation among them either (e1.C1.reading, "
                    "e2.C1.reading), the door's catch and escape rates on C1 are untested" if not fired else ""),
                "results/numbers.json", k=fired, n=n,
                note="from e1.C1.detector_vs_grader and e2.C1.detector_vs_grader (R3-B1, R3-M7)")
    if "e2.explo.informative.cases" in ent:
        reg.add("e2.explo.informative.selection", "chosen after the results",
                "chosen after the results: the subset keeps the cases whose A0 arm violated, a selection on one of the two "
                "terms of H1's statistic: a case it drops has V(A0) = 0, so its difference V(A0) minus V(AP) "
                "is at or below 0 (here %s), and dropping it from a pool whose mean is above 0 can only "
                "raise that mean; it is not among PREREG-E2.md's exploratory analyses, and its verdict "
                "(e2.explo.informative.h1.verdict) decides nothing" % ", ".join(
                    "%s %s" % (c, fmt_num(v)) for c, v in sorted(ent["e2.h1.diff"]["per_case"].items())
                    if c not in ent["e2.explo.informative.cases"].get("cases", ent["e2.explo.informative.h1.diff"].get("cases", []))),
                "prereg/PREREG-E2.md", note="R2-R2-14; DEVIATIONS.md, deviation 29")


# ---------------------------------------------------------------- run

def run(ctx):
    for name in ("agreement_pairs.csv", "corrections_coded.csv", "ask_reconcile_after.csv", "replay_readings.csv"):
        if not ctx.has_data(name):
            raise Missing("data/%s not found" % name)
    if not (ctx.e1 / "runs.jsonl").exists() or not (ctx.e2 / "runs.jsonl").exists():
        raise Missing("e1/runs.jsonl or e2/runs.jsonl not found")
    reg = ctx.registry
    agreement_section(ctx, reg)
    ac1_used_codes(ctx, reg)
    corrections_section(ctx, reg)
    ask_after_section(ctx, reg)
    e1_rows = r3._counted(_read_jsonl(ctx.e1 / "results.jsonl"))
    e2_rows = r3._counted(_read_jsonl(ctx.e2 / "results.jsonl"))
    runs1 = _read_jsonl(ctx.e1 / "runs.jsonl")
    runs2 = _read_jsonl(ctx.e2 / "runs.jsonl")
    g1 = _load_module(ctx.e1 / "graders.py", "e1_graders_r4")
    first = _load_module(ctx.e1 / "graders_first_committed.py", "e1_graders_first_r4")
    regrade1 = _load_module(ctx.e1 / "regrade.py", "e1_regrade_r4")
    regrade2 = _load_module(ctx.e2 / "regrade.py", "e2_regrade_r4")
    c2_any_section(reg, "e1", e1_rows, runs1, regrade1, g1)
    c2_any_section(reg, "e2", e2_rows, runs2, regrade2, regrade2.graders.e1)
    counted_h2_parts(reg)
    first_c3_h2_parts(reg, e2_rows, runs2, regrade2, first)
    results = {"e1": {r["order"]: r for r in e1_rows}, "e2": {r["order"]: r for r in e2_rows}}
    readings_section(ctx, reg, results)
    c3_text_section(reg, "e1", e1_rows, runs1, g1, regrade1, first)
    c3_text_section(reg, "e2", e2_rows, runs2, regrade2.graders.e1, regrade2, first)
    c5_split_section(reg, "e1", e1_rows, runs1, g1)
    c5_split_section(reg, "e2", e2_rows, runs2, regrade2.graders.e1)
    fidelity_section(reg, "e1", runs1)
    fidelity_section(reg, "e2", runs2)
    timing_section(reg, "e1", e1_rows)
    timing_section(reg, "e2", e2_rows)
    identity_section(ctx, reg, "e1")
    identity_section(ctx, reg, "e2")
    field_facts(ctx, reg)


if __name__ == "__main__":
    sys.exit(standalone(run))
