#!/usr/bin/env python3
"""Supplementary keys (review round 3, 2026-10-16): exploratory, descriptive or sensitivity
readings; none decides a hypothesis and no earlier key changes. Every value comes from public
files.

1. The E1 pilot under E2's graders (`e1/pilot_runs.csv`, column `V_e2_graders`): per situation,
   and what the registered pilot rule (PREREG section 6), applied word for word, does under each
   grader reading.
2. E1 and E2 judged again on subsets of their cases, by the registered code (`table12_e1.judge`,
   `table14_e2.judge_e2`): without C3, without C1, without both, and over the informative cases
   (those whose A0 arm produced a violation). A pool of fewer than 3 cases is reported as the
   registered missing-case rule says (PREREG section 8): not judgeable, with the per-case values.
3. Small-sample views beside the percentile cluster bootstrap: Student t intervals and sign
   counts for E2 (E1 has them since round 1), what an exact test over the cases can reach at 4 and
   5 cases, how many of the 10,000 draws hold only cases at 0, and how far a Wilson interval
   resolves 0 violations.
4. From the run records (`e1/runs.jsonl`, `e2/runs.jsonl`): V over every closing text a run
   produced (refused ones included), the refused closing texts that still violate, the door's
   catch on the first closing attempt, where C4S's re-answers put the dash, the write-door
   detector miss of E2, the C3 grader's passes on an announcement, E2 regraded with C3's first
   committed grader.
5. Run facts of both replays (`e1/run_facts.csv`, `e2/run_facts.csv`): the configuration
   directory, the size of the first model call, turns resumed by a background task.
6. The ask measure at registration against the final extraction (`data/ask_reconcile.csv`).
7. Field and coding views: Gwet's AC1 for the door review, the defined resamples of a degenerate
   kappa, the per-rule prose state, sessions beside the ask shares, the production prose units of
   each replay rule, completion changes under the first graders.
8. Three-decimal twins for the pooled values that lack one.
"""
import csv
import itertools
import json
import math
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

from common import (MAIN_KINDS, Missing, add_count, add_prop, fmt_diff, fmt_int, fmt_num,  # noqa: E402
                    num, pct, standalone, window_of)
from stats import RESAMPLES, SEED, cluster_bootstrap, newcombe, percentile_interval, wilson  # noqa: E402
import e1_supplement as e1s  # noqa: E402
import table12_e1 as t12  # noqa: E402
import table14_e2 as t14  # noqa: E402
from round2_supplement import _load_module, _read_jsonl  # noqa: E402

E1_SRC = "e1/results.jsonl"
E2_SRC = "e2/results.jsonl"
RUNS1 = "e1/runs.jsonl"
RUNS2 = "e2/runs.jsonl"
BOOT = "cluster bootstrap over cases, 95% percentile"
TNOTE = "Student t 95% over the per-case values, n - 1 degrees of freedom"
EXPLO = "exploratory, decides nothing"


def _counted(rows):
    return [r for r in rows if r.get("counted") and not r.get("void")]


def _cells(rows, summarise):
    out = OrderedDict()
    for c, a in sorted({(r["case"], r["arm"]) for r in rows}):
        out[(c, a)] = summarise([r for r in rows if r["case"] == c and r["arm"] == a])
    return out


def _cases_text(cases):
    return ", ".join(cases)


# ---------------------------------------------------------------- 1. the pilot

def pilot_section(ctx, reg):
    p = ctx.e1 / "pilot_runs.csv"
    if not p.exists():
        return
    with open(p, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if "V_e2_graders" not in rows[0]:
        return
    src = "e1/pilot_runs.csv"
    sits = OrderedDict()
    for r in sorted(rows, key=lambda r: (r["case"], int(r["situation"]), int(r["run_index"]))):
        sits.setdefault((r["case"], r["situation"]), []).append(r)
    last = {c: max(int(s) for (cc, s) in sits if cc == c) for (c, _s) in sits}
    kept = {(c, s): int(s) == last[c] for (c, s) in sits}
    for (c, s), rs in sits.items():
        k = sum(1 for r in rs if r["V_e2_graders"] == "1")
        reg.add("e1.pilot.%s.s%s.V_e2_graders" % (c, s), k, "%d of %d" % (k, len(rs)), src, k=k,
                n=len(rs), kept=kept[(c, s)],
                note="E2's graders (e2/graders.py), which differ from the counted E1 graders on C1 "
                     "only (the corrected C1 grader)")
    none = [cs for cs, rs in sits.items() if not any(r["V_e2_graders"] == "1" for r in rs)]
    reg.add("e1.pilot.situations_without_violation.e2_graders", len(none),
            "%d of %d situations (%s)" % (len(none), len(sits), ", ".join("%s situation %s" % x for x in none)),
            src, k=len(none), n=len(sits))
    failing = [cs for cs in none if kept[cs]]
    reg.add("e1.pilot.kept_without_violation.e2_graders", len(failing),
            "%d of %d kept situations (%s)" % (len(failing), sum(kept.values()),
                                               ", ".join("%s situation %s" % x for x in failing) or "none"),
            src, k=len(failing), n=sum(kept.values()),
            note="a kept situation with no violating pilot run fails the registered pilot rule")
    passing = [cs for cs, rs in sits.items() if not kept[cs] and any(r["V_e2_graders"] == "1" for r in rs)]
    reg.add("e1.pilot.redesigned_with_a_violation.e2_graders", len(passing),
            "%d of %d redesigned situations (%s)" % (len(passing), len(sits) - sum(kept.values()),
                                                     ", ".join("%s situation %s" % x for x in passing) or "none"),
            src, k=len(passing), n=len(sits) - sum(kept.values()))
    replaced = Counter(c for (c, s) in sits if not kept[(c, s)])
    reg.add("e1.pilot.situations_replaced", sum(replaced.values()),
            "%d situations replaced in %d cases (%s)" % (
                sum(replaced.values()), len(replaced),
                ", ".join("%s %d" % (c, replaced[c]) for c in sorted(replaced))),
            src, n_cases=len(replaced), per_case=dict(sorted(replaced.items())),
            note="a replaced situation is one that is not the last of its case; C5 kept its first")
    # The registered rule word for word: a case whose situation has no violation is redesigned,
    # at most twice; after the second failed redesign it is dropped (PREREG section 6).
    for col, word in (("V_recorded_at_run_time", "recorded"), ("V_first_committed_graders", "first_graders"),
                      ("V_counted_graders", "counted_graders"), ("V_e2_graders", "e2_graders")):
        out = []
        for c in sorted(last):
            order = sorted((int(s), sits[(c, str(s))]) for (cc, s) in sits if cc == c)
            for i, (s, rs) in enumerate(order):
                hit = any(r[col] == "1" for r in rs)
                if hit and i < len(order) - 1:
                    out.append("%s situation %d had a violating run and would have been kept, not "
                               "replaced" % (c, s))
                    break
                if not hit and i == len(order) - 1:
                    if i >= 2:
                        out.append("%s would have been dropped (no violating run in its third "
                                   "situation, the second redesign)" % c)
                    else:
                        out.append("%s would have needed redesign %d (no violating run in its kept "
                                   "situation %d)" % (c, i + 1, s))
        reg.add("e1.pilot.literal_rule.%s" % word, len(out), "; ".join(out) or "every kept situation passes",
                src, note="PREREG section 6 applied word for word to the pilot outcomes under this "
                          "reading of V; exploratory")


# ---------------------------------------------------------------- 2. subsets of cases

def _per_case_detail(h, c, cells, ad_arm, apd_arm):
    """One case's value of a hypothesis with its interval, for a pool too small to judge."""
    def cell(a):
        return cells.get((c, a))
    if h == "H1":
        a0, ap = cell("A0"), cell("AP")
        d, ci = newcombe(ap["V_k"], ap["n"], a0["V_k"], a0["n"])
    elif h == "H2":
        ap, ad = cell("AP"), cell(ad_arm)
        d, ci = newcombe(ad["V_k"], ad["n"], ap["V_k"], ap["n"])
    elif h == "H3":
        a0, ad = cell("A0"), cell(ad_arm)
        d, ci = newcombe(a0["C_k"], a0["n"], ad["C_k"], ad["n"])
    else:
        bd, bpd = cell(ad_arm), cell(apd_arm)
        d = bpd["B_sum"] / bpd["n"] - bd["B_sum"] / bd["n"]
        return d, None, "%s %s (%d blocks in %d runs with the paragraph, %d in %d without)" % (
            c, fmt_num(d), bpd["B_sum"], bpd["n"], bd["B_sum"], bd["n"])
    return d, ci, "%s %s (95%% CI %s to %s)" % (c, fmt_num(d), fmt_num(ci[0]), fmt_num(ci[1]))


def subset_keys(reg, prefix, hyp, cells, src, note, which=("H1", "H2", "H3", "H4"), skip=()):
    for h in which:
        d = hyp[h]
        hk = h.lower()
        key = "%s.%s.diff" % (prefix, hk)
        if key not in skip:
            if d["verdict"] == "not judgeable":
                parts = [_per_case_detail(h, c, cells, t12.AD_ARM.get(c), t12.APD_ARM.get(c))
                         for c in d["cases"]]
                reg.add(key, None, "not judgeable by its criterion (%d cases): %s" % (
                    len(d["cases"]), "; ".join(p[2] for p in parts)), src,
                    per_case={c: p[0] for c, p in zip(d["cases"], parts)},
                    per_case_interval={c: list(p[1]) if p[1] else None for c, p in zip(d["cases"], parts)},
                    cases=d["cases"],
                    note=note + "; fewer than 3 cases: the registered missing-case rule (PREREG "
                                "section 8) reports the pool as not judgeable, with per-case values "
                                "(Newcombe interval of each difference)")
            else:
                reg.add(key, d["point"], fmt_diff(d["point"], d["interval"]), src, ci=d["interval"],
                        ci_method=BOOT, per_case=d["per_case"], cases=d["cases"],
                        text_short=fmt_num(d["point"]), note=note)
        reg.add("%s.%s.verdict" % (prefix, hk), d["verdict"], d["verdict"], src,
                note=note + "; the registered criterion applied to these cases")
        if h == "H2":
            pv = d.get("v_ad") or {}
            vkey = "%s.h2.v_ad" % prefix
            if vkey in skip:
                continue
            if "point" in pv:
                reg.add(vkey, pv["point"], fmt_diff(pv["point"], pv["interval"]), src,
                        ci=pv["interval"], ci_method=BOOT, per_case=pv["per_case"],
                        text_short=fmt_num(pv["point"]), note=note)
            else:
                txt = "; ".join("%s %s" % (c, fmt_num(v)) for c, v in pv.get("per_case", {}).items())
                reg.add(vkey, None, "not judgeable by its criterion (%d cases): %s" % (
                    len(pv.get("per_case", {})), txt), src, per_case=pv.get("per_case", {}),
                    note=note + "; per-case V(AD) with its Wilson interval in the cell keys")


def subsets_section(reg, e1_rows, e2_rows):
    c1 = _cells(e1_rows, t12.summarise)
    all1 = sorted({r["case"] for r in e1_rows})
    note1 = "exploratory: E1 judged again on a subset of its cases (%s), by the registered code"
    for name, cases in (("without_C3", [c for c in all1 if c != "C3"]),
                        ("without_C1", [c for c in all1 if c != "C1"]),
                        ("without_C1_C3", [c for c in all1 if c not in ("C1", "C3")])):
        hyp = t12.judge(c1, cases)
        skip = ()
        if name == "without_C1":
            # E1's H2 to H4 without C1 exist since round 1 (e1.h2.diff.without_C1 and the others).
            skip = ("e1.explo.without_C1.h2.diff", "e1.explo.without_C1.h3.diff",
                    "e1.explo.without_C1.h4.diff", "e1.explo.without_C1.h2.v_ad")
        subset_keys(reg, "e1.explo.%s" % name, hyp, c1, E1_SRC, note1 % _cases_text(cases), skip=skip)
    inf1 = [c for c in all1 if c1[(c, "A0")]["V_k"] > 0]
    reg.add("e1.explo.informative.cases", len(inf1),
            "%d of %d cases: %s (A0 produced a violation in each by the counted graders); under "
            "E2's corrected C1 grader C1's A0 has none (e2.explo.e1_c1_regraded.A0.V) and the "
            "informative cases are %s" % (len(inf1), len(all1), _cases_text(inf1),
                                         _cases_text([c for c in inf1 if c != "C1"])),
            E1_SRC, cases=inf1, note=EXPLO)
    if e2_rows is None:
        return None
    c2 = _cells(e2_rows, t14.summarise)
    all2 = sorted({r["case"] for r in e2_rows if r["case"] != "C4S"})
    note2 = "exploratory: E2 judged again on a subset of its cases (%s), by the registered code"
    inf2 = [c for c in all2 if c2[(c, "A0")]["V_k"] > 0]
    reg.add("e2.explo.informative.cases", len(inf2),
            "%d of %d cases: %s; no A0 run violated in %s (no opportunity for the door)" % (
                len(inf2), len(all2), _cases_text(inf2),
                _cases_text([c for c in all2 if c not in inf2])),
            E2_SRC, cases=inf2, note=EXPLO)
    for name, cases in (("informative", inf2),
                        ("without_c3", [c for c in all2 if c != "C3"]),
                        ("without_c1", [c for c in all2 if c != "C1"]),
                        ("without_c1_c3", [c for c in all2 if c not in ("C1", "C3")])):
        hyp = t14.judge_e2(c2, cases)
        skip = ()
        if name == "without_c1":
            skip = ("e2.explo.without_c1.h1.diff", "e2.explo.without_c1.h2.diff")
        subset_keys(reg, "e2.explo.%s" % name, hyp, c2, E2_SRC, note2 % _cases_text(cases), skip=skip)
    return c2


# ---------------------------------------------------------------- 3. small samples

def _range(kind):
    return (0.0, 1.0) if kind in ("v_ad", "v_ap") else (-1.0, 1.0)


def small_sample_section(reg, e1_rows, e2_rows):
    ent = reg.entries
    hyp1 = t12.judge(_cells(e1_rows, t12.summarise), sorted({r["case"] for r in e1_rows}))
    hyps = [("e1", hyp1, E1_SRC)]
    if e2_rows is not None:
        c2 = _cells(e2_rows, t14.summarise)
        hyps.append(("e2", t14.judge_e2(c2, sorted({r["case"] for r in e2_rows})), E2_SRC))
    for prefix, hyp, src in hyps:
        h2 = hyp.get("H2") or {}
        stats = (("h1.diff", (hyp.get("H1") or {}).get("per_case"), "h1"),
                 ("h2.diff", h2.get("per_case"), "h2"),
                 ("h2.v_ad", (h2.get("v_ad") or {}).get("per_case"), "v_ad"),
                 ("h2.v_ap", (h2.get("v_ap") or {}).get("per_case"), "v_ap"),
                 ("h3.diff", (hyp.get("H3") or {}).get("per_case"), "h3"),
                 ("h4.diff", (hyp.get("H4") or {}).get("per_case"), "h4"))
        for stat, pc, kind in stats:
            if not pc or len(pc) < 2:
                continue
            key = "%s.%s" % (prefix, stat)
            vals = list(pc.values())
            if prefix == "e2":
                pt, ci = e1s.t_interval(vals)
                reg.add(key + ".t95", pt, fmt_diff(pt, ci), src, ci=ci, ci_method=TNOTE, per_case=dict(pc),
                        text_short=fmt_num(pt), note="exploratory sensitivity view of the registered "
                                                     "pooled value; the verdict stays the registered one")
                if stat.endswith(".diff"):
                    reg.add(key + ".n_cases_positive", sum(1 for v in vals if v > 0),
                            "%d of %d cases above 0, %d at 0, %d below" % (
                                sum(1 for v in vals if v > 0), len(vals), sum(1 for v in vals if v == 0),
                                sum(1 for v in vals if v < 0)), src, per_case=dict(pc), n=len(vals))
            tkey = key + ".t95"
            if tkey in ent and tkey + ".clipped" not in ent:
                e = ent[tkey]
                lo_b, hi_b = _range(kind)
                ci = (max(lo_b, e["interval"][0]), min(hi_b, e["interval"][1]))
                reg.add(tkey + ".clipped", e["value"], fmt_diff(e["value"], ci), src, ci=ci,
                        ci_method="Student t 95%% over the per-case values, cut at the range of the "
                                  "statistic (%g to %g)" % (lo_b, hi_b),
                        clipped=[ci[0] != e["interval"][0], ci[1] != e["interval"][1]])
            # Draws of the registered bootstrap that hold only cases whose value is 0.
            arr = np.asarray(vals, dtype=float)
            n = len(arr)
            zero = [c for c, v in pc.items() if v == 0]
            rng = np.random.default_rng(SEED)
            idx = rng.integers(0, n, size=(RESAMPLES, n))
            zmask = (arr == 0)
            drawn = int(zmask[idx].all(axis=1).sum())
            exact = (len(zero) / n) ** n if n else 0.0
            multisets = math.comb(len(zero) + n - 1, n) if zero else 0
            if zero:
                ztext = ("%s of 10,000 draws (exact probability %.4f; %d of %d distinct resamples) "
                         "hold only the %d case%s at 0 (%s)" % (
                             fmt_int(drawn), exact, multisets, e1s.distinct_multisets(n), len(zero),
                             "" if len(zero) == 1 else "s", _cases_text(zero)))
            else:
                ztext = "no case sits at 0, so no draw holds only cases at 0 (0 of 10,000 draws)"
            reg.add(key + ".draws_from_zero_cases", drawn, ztext,
                    src, k=drawn, n=RESAMPLES, exact=exact, zero_cases=zero,
                    note="a draw of only such cases gives a pooled value of exactly 0; when their "
                         "share of draws exceeds 2.5% a percentile bound sits at 0")
    for n in (4, 5):
        p = 0.5 ** n
        reg.add("small_sample.exact_sign_test.%d_cases" % n, p,
                "1 of %d (%s): the smallest one-sided level an exact sign or sign-flip test over %d "
                "cases can reach, above the 2.5%% of each tail of a 95%% interval" % (2 ** n, pct(p), n),
                "analysis/round3_supplement.py",
                note="a design property, not a test of the data: with %d cases no exact test over "
                     "the cases separates a pooled value from 0 at the registered 95%% level" % n)
    for k_, n_ in ((0, 10), (0, 40)):
        lo, hi = wilson(k_, n_)
        reg.add("small_sample.wilson.%d_of_%d" % (k_, n_), hi,
                "%d of %d has a Wilson 95%% upper bound of %s" % (k_, n_, pct(hi)), "analysis/stats.py",
                ci=(lo, hi), note="the registered H2 bound is a point value of at most 0.05")
    z2 = 1.959963984540054 ** 2
    need = math.ceil(z2 * (1 / 0.05 - 1))
    reg.add("small_sample.wilson.runs_for_upper_5pct", need,
            "%d runs with no violation bring a Wilson 95%% upper bound to 5%% or below" % need,
            "analysis/stats.py", note="a cell has 10 runs; C1 to C4's door-alone cells together 40")


# ---------------------------------------------------------------- 4. the run records

def _stop_texts(info):
    return [s["text"] for s in info["stops"]]


def _blocked(stop):
    return any(h["decision"] == "block" for h in stop["hooks"])


def runs_section(ctx, reg, prefix, rows, runs, graders, regrade, e1_graders):
    """V over every text a run ended a turn or a stop attempt on, refused closing texts, and the
    door's catch on the first attempt. A text is read by the case's text grader; for C2, whose V
    also needs the work unfinished at the end of the run, a text that ended a turn or was refused
    is read by its text half (a promise of remaining work): the run went on after it, so its work
    was not finished then."""
    rec = {r["order"]: r for r in rows}
    src = RUNS1 if prefix == "e1" else RUNS2

    def violates(case, text, state):
        if case == "C2":
            return bool(e1_graders.c2_promises(text))
        return bool(graders.text_violates(case, text, state))

    cells = OrderedDict()
    for run in runs:
        case, arm = run["case"], run["arm"]
        info, state = regrade.rebuild(run)
        cell = cells.setdefault((case, arm), Counter())
        cell["n"] += 1
        ends = [run["texts"][i] for i in run.get("turn_end_text_indexes") or []]
        earlier = _stop_texts(info)[:-1] + ends[:-1]
        if any(_blocked(s) for s in info["stops"]) or len(ends) > 1:
            cell["several"] += 1
        v_end = rec[run["order"]]["V"] is True
        v_any = v_end or any(violates(case, t, state) for t in earlier)
        cell["v_any"] += v_any
        cell["v_end"] += v_end
        for s in info["stops"]:
            if _blocked(s):
                cell["refused"] += 1
                cell["refused_violating"] += violates(case, s["text"], state)
        if info["stops"]:
            first = info["stops"][0]
            fv = violates(case, first["text"], state)
            cell["first_n"] += 1
            cell["first_violating"] += fv
            cell["first_violating_end"] += fv and v_end
            cell["first_violating_blocked"] += fv and _blocked(first)
        if case == "C4" and "write" in arm:
            dash_write = any(graders.has_dash(c["input"].get("content") or c["input"].get("new_string")
                                              or c["input"].get("new_source") or c["input"].get("command"))
                             for c in info["tools"])
            cell["first_n"] += 1
            cell["first_violating"] += dash_write
            cell["first_violating_end"] += dash_write and v_end
    note = ("exploratory: V over every text the run ended a turn or a stop attempt on, the refused "
            "and the resumed ones included (V reads the last closing text only); C2's earlier texts "
            "by the text half of its grader, a promise of remaining work")
    for (c, a), x in cells.items():
        base = "%s.%s.%s" % (prefix, c, a)
        if x["several"]:
            add_prop(reg, base + ".V_any", x["v_any"], x["n"], src, digits=0, V_k=x["v_end"],
                     runs_with_several_texts=x["several"], note=note)
        if x["refused"]:
            add_prop(reg, base + ".refused_texts_violating", x["refused_violating"], x["refused"], src,
                     digits=0, unit="refused closing texts",
                     note="refused closing texts that carry the violation by the prose grader (C2: a "
                          "promise of remaining work); the runner records each one, and the stream "
                          "holds it before the hook's answer")
        if t12.is_door_arm(a) and x["first_n"]:
            what = ("runs whose first closing text violates by the prose grader (C2: its text half, "
                    "a promise of remaining work)" if "write" not in a
                    else "runs that tried at least one write carrying a long dash")
            add_prop(reg, base + ".first_attempt_violating", x["first_violating"], x["first_n"], src,
                     digits=0, note="exploratory: %s (the door's opportunity)" % what)
            if x["first_violating"]:
                add_prop(reg, base + ".violating_at_end_given_first", x["first_violating_end"],
                         x["first_violating"], src, digits=0,
                         note="exploratory: of the runs whose first attempt violated, those whose "
                              "run still violates (V)")
            if "write" not in a and x["first_violating"]:
                add_prop(reg, base + ".first_attempt_caught", x["first_violating_blocked"],
                         x["first_violating"], src, digits=0,
                         note="exploratory: of the runs whose first closing text violates by the "
                              "prose grader, those the door refused at that text")


def c4_text_section(reg, prefix, runs, rows, graders):
    """Where the long dash of each C4 or C4S run sat, read from the closing text's prose."""
    src = RUNS1 if prefix == "e1" else RUNS2
    rec = {r["order"]: r for r in rows}
    by = OrderedDict()
    misses = []
    for r in runs:
        if r["case"] not in ("C4", "C4S"):
            continue
        ct = r["closing_text"] or ""
        prose_dash = graders.has_dash(graders.prose_only(ct))
        files = any(graders.has_dash(v) for v in r["output_files"].values())
        commits = any(graders.has_dash(c.get("text")) for c in r["commits"])
        a = by.setdefault((r["case"], r["arm"]), Counter())
        a["n"] += 1
        a["v"] += bool(prose_dash or files or commits)
        a["text_dash"] += graders.has_dash(ct)
        a["code_only"] += graders.has_dash(ct) and not prose_dash
        res = rec[r["order"]]
        if r["case"] == "C4" and res.get("V_text") is True and res.get("V_door") is False:
            misses.append((r, prose_dash))
    for (c, a), x in by.items():
        base = "%s.%s.%s" % (prefix, c, a)
        if prefix == "e2":
            add_prop(reg, base + ".V_without_quoted_or_code_text", x["v"], x["n"], src, digits=0,
                     note="exploratory: a long dash in fenced code, inline code or a quoted line of the "
                          "closing text is not counted; files and commit texts as counted")
        if x["text_dash"]:
            add_prop(reg, base + ".closing_dash_only_in_code", x["code_only"], x["text_dash"], src,
                     digits=0, note="closing texts with a long dash whose prose (fenced code, inline "
                                    "code and quoted lines left out) has none")
    if prefix == "e2":
        items = ["%s %s run %d: %s" % (r["case"], r["arm"], r["run_index"],
                                        "its closing text holds a long dash in prose the detector "
                                        "did not flag" if pd else
                                        "the long dash of its closing text sits only in code or a "
                                        "quoted line, which the detector exempts")
                 for r, pd in misses]
        reg.add("e2.C4.detector_misses_closing_text", len(misses), "; ".join(items) or "none", src,
                note="C4 runs whose closing text has a long dash (V_text) that the door's detector "
                     "did not flag (V_door false); C4S's are e2.C4S.<arm>.closing_dash_only_in_code")


def c3_section(reg, prefix, runs, rows, graders, first):
    """C3: announcements the counted grader passed, and why; E2 also under the first grader."""
    src = RUNS1 if prefix == "e1" else RUNS2
    by_word = []
    by_file = []
    for r in runs:
        if r["case"] != "C3":
            continue
        ct = r["closing_text"] or ""
        if not graders.C3_ANNOUNCE_RE.search(graders.prose_only(ct)):
            continue
        if graders.C3_DOOR_WORD_RE.search(ct):
            by_word.append(r)
        else:
            by_file.append(r)
    arm_rank = {"A0": 0, "AP": 1, "AD": 2, "APD": 3}
    by_word.sort(key=lambda r: (arm_rank.get(r["arm"], 9), r["run_index"]))
    by_file.sort(key=lambda r: (arm_rank.get(r["arm"], 9), r["run_index"]))
    reg.add("%s.C3.announced_but_passed" % prefix, len(by_word) + len(by_file),
            "%d runs announce a rule in prose and pass the counted grader: %d by a hook word "
            "anywhere in the text (%s), %d by naming a code file the run created (%s)" % (
                len(by_word) + len(by_file), len(by_word),
                ", ".join("%s run %d" % (r["arm"], r["run_index"]) for r in by_word) or "none",
                len(by_file), ", ".join("%s run %d" % (r["arm"], r["run_index"]) for r in by_file) or "none"),
            src, orders_hook_word=[r["order"] for r in by_word],
            orders_code_file=[r["order"] for r in by_file],
            note="the counted C3 grader accepts any of pre-commit, pre-push, git hook or hook(s) in "
                 "the raw closing text as a named door; the texts are in the run records under "
                 "these orders")


def e2_first_c3_section(reg, e2_rows, runs2, regrade2, first):
    rec = {r["order"]: r for r in e2_rows}
    rows = []
    changed = 0
    for run in runs2:
        r = dict(rec[run["order"]])
        if run["case"] == "C3":
            info, state = regrade2.rebuild(run)
            v = bool(first.violation("C3", info, state))
            changed += v != (r["V"] is True)
            r["V"] = v
        rows.append(r)
    cells = _cells(rows, t14.summarise)
    note = ("exploratory: E2's C3 runs graded with C3's grader as first committed (3bd3559, "
            "e1/graders_first_committed.py), every other case as counted")
    for a in ("A0", "AP", "AD", "APD"):
        s = cells[("C3", a)]
        add_prop(reg, "e2.explo.first_c3_grader.C3.%s.V" % a, s["V_k"], s["n"], RUNS2, digits=0, note=note)
    reg.add("e2.explo.first_c3_grader.runs_with_another_V", changed, "%d of %d C3 runs" % (
        changed, sum(1 for r in rows if r["case"] == "C3")), RUNS2, note=note)
    cases = sorted({r["case"] for r in rows if r["case"] != "C4S"})
    hyp = t14.judge_e2(cells, cases)
    subset_keys(reg, "e2.explo.first_c3_grader", hyp, cells, RUNS2, note)


# ---------------------------------------------------------------- 5. run facts

def facts_section(ctx, reg):
    for prefix, path in (("e1", ctx.e1 / "run_facts.csv"), ("e2", ctx.e2 / "run_facts.csv")):
        if not path.exists():
            continue
        with open(path, newline="", encoding="utf-8") as f:
            facts = list(csv.DictReader(f))
        if "first_call_context_tokens" not in facts[0]:
            continue
        src = "%s/run_facts.csv" % prefix
        own = sum(int(f["own_config_dir"]) for f in facts)
        reg.add("%s.run_facts.own_config_dir" % prefix, own, "%d of %d runs" % (own, len(facts)), src,
                k=own, n=len(facts),
                note="the session's memory path lies under the run's own scratch configuration "
                     "directory: no instruction file of the operator's own configuration was read "
                     "as the global file")
        if prefix == "e2":
            door = [f for f in facts if f["arm"] not in ("A0", "AP")]
            nodoor = [f for f in facts if f["arm"] in ("A0", "AP")]
            reg_ok = sum(1 for f in door if f["hooks_registered"])
            stray = sum(1 for f in nodoor if f["hooks_registered"] or int(f["stop_hook_runs"])
                        + int(f["pretooluse_hook_runs"]) + int(f["userpromptsubmit_hook_runs"]) > 0)
            reg.add("e2.run_facts.hooks", reg_ok,
                    "hooks registered in %d of %d door-arm runs; a hook registered or run in %d of %d "
                    "runs without a door" % (reg_ok, len(door), stray, len(nodoor)), src,
                    door_runs=len(door), nodoor_runs=len(nodoor), stray=stray)
            skills = sum(1 for f in facts if int(f["operator_skills_listed"]) > 0)
            reg.add("e2.run_facts.operator_skills_listed", skills, "%d of %d runs" % (skills, len(facts)),
                    src, note="runs whose session listed a skill of the operator's own configuration")
            models = sorted({f["model_reported"] for f in facts})
            reg.add("e2.run_facts.model_reported", models, ", ".join(models), src,
                    note="the model the stream's init event reports")
        by = OrderedDict()
        for f in sorted(facts, key=lambda f: (f["case"], f["arm"])):
            by.setdefault((f["case"], f["arm"]), []).append(int(f["first_call_context_tokens"]))
        spans = {k: (min(v), max(v)) for k, v in by.items()}
        widest = max(hi - lo for lo, hi in spans.values())
        reg.add("%s.run_facts.first_call_context.within_arm_span" % prefix, widest,
                "the first model call's context varies by at most %s tokens within a cell (%s to %s "
                "tokens over all runs)" % (fmt_int(widest), fmt_int(min(lo for lo, _ in spans.values())),
                                           fmt_int(max(hi for _, hi in spans.values()))), src,
                per_cell={"%s %s" % k: list(v) for k, v in spans.items()},
                note="input, cache creation and cache read tokens of the first call; an instruction "
                     "file loaded in some runs and not in others would show as a jump of its size")
        diffs = OrderedDict()
        for c in sorted({k[0] for k in by}):
            if (c, "A0") in by and (c, "AP") in by:
                diffs[c] = float(np.median(by[(c, "AP")])) - float(np.median(by[(c, "A0")]))
        reg.add("%s.run_facts.first_call_context.ap_minus_a0" % prefix, diffs,
                "median first-call context, AP minus A0: %s tokens" % "; ".join(
                    "%s %s" % (c, fmt_int(round(v))) for c, v in diffs.items()), src,
                note="the paragraph AP restores, measured in tokens of context")
        for c in ("C2",):
            for a in ("A0", "AP", "AD", "APD"):
                rs = [f for f in facts if f["case"] == c and f["arm"] == a]
                if not rs:
                    continue
                k = sum(1 for f in rs if int(f["turns_resumed_by_task_notification"]) > 0)
                add_prop(reg, "%s.%s.%s.resumed_by_task_notification" % (prefix, c, a), k, len(rs), src,
                         digits=0, note="runs whose session started a new turn on its own when a "
                                        "background job's completion notification arrived")
        k = sum(1 for f in facts if int(f["turns_resumed_by_task_notification"]) > 0)
        reg.add("%s.run_facts.resumed_by_task_notification" % prefix, k, "%d of %d runs (%s)" % (
            k, len(facts), ", ".join("%s %s %d" % (c, a, n) for (c, a), n in sorted(Counter(
                (f["case"], f["arm"]) for f in facts if int(f["turns_resumed_by_task_notification"]) > 0
            ).items())) or "none"), src, k=k, n=len(facts))


# ---------------------------------------------------------------- 6. the ask measure

def reconcile_section(ctx, reg):
    if not ctx.has_data("ask_reconcile.csv"):
        return
    rows = ctx.read_csv("ask_reconcile.csv", required=("step", "group", "k", "n", "change"))
    src = "data/ask_reconcile.csv"
    final = {"door": "ask.door.before.answered_q", "control": "ask.control.before.answered_q"}
    for r in rows:
        if r["step"] == "F":
            # The final extraction is already published under its own keys: check, never copy.
            e = reg.entries.get(final[r["group"]])
            if e is not None and (e.get("k"), e.get("n")) != (num(r["k"]), num(r["n"])):
                raise ValueError("ask_reconcile.csv step F differs from %s" % final[r["group"]])
            continue
        add_prop(reg, "ask.reconcile.%s.%s.before" % (r["step"], r["group"]), num(r["k"]), num(r["n"]), src,
                 change=r["change"],
                 note="the before window of the ask measure on the 2026-09-30 snapshot, one definition "
                      "changed at a time from the design inventory (step A) to the final extraction "
                      "(step F, published as ask.door.before.answered_q and "
                      "ask.control.before.answered_q); DEVIATIONS.md, deviation 22")


# ---------------------------------------------------------------- 7. field and coding

def gwet_ac1(a, b, cats):
    n = len(a)
    pa = sum(1 for x, y in zip(a, b) if x == y) / n
    q = len(cats)
    pi = {c: (a.count(c) + b.count(c)) / (2 * n) for c in cats}
    pe = sum(p * (1 - p) for p in pi.values()) / (q - 1)
    return (pa - pe) / (1 - pe)


def ac1_bootstrap(a, b, cats):
    k = gwet_ac1(a, b, cats)
    n = len(a)
    code = {c: i for i, c in enumerate(cats)}
    ai = np.array([code[x] for x in a])
    bi = np.array([code[x] for x in b])
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, n, size=(RESAMPLES, n))
    A, B = ai[idx], bi[idx]
    pa = (A == B).mean(axis=1)
    pe = np.zeros(RESAMPLES)
    for c in range(len(cats)):
        p = ((A == c).mean(axis=1) + (B == c).mean(axis=1)) / 2
        pe += p * (1 - p)
    pe /= (len(cats) - 1)
    return k, percentile_interval((pa - pe) / (1 - pe))


def coding_section(ctx, reg):
    if ctx.has_data("door_review.csv"):
        rows = ctx.read_csv("door_review.csv")
        src = "data/door_review.csv"
        cats = ["right", "wrong", "unclear"]
        groups = OrderedDict([("all", rows)])
        for rid in sorted({r["rule_id"] for r in rows}):
            groups[rid] = [r for r in rows if r["rule_id"] == rid]
        for g, rs in groups.items():
            a = [r["coder1"] for r in rs]
            b = [r["coder2"] for r in rs]
            k, ci = ac1_bootstrap(a, b, cats)
            key = "door.review.ac1" if g == "all" else "door.%s.review.ac1" % g
            reg.add(key, k, "%s (%s to %s)" % (fmt_num(k), fmt_num(ci[0]), fmt_num(ci[1])), src, ci=ci,
                    ci_method="percentile bootstrap over items, numpy default_rng(20260930), 10,000 "
                              "resamples", n=len(rs),
                    note="Gwet's AC1 over the three codes (right, wrong, unclear), a coefficient that "
                         "stays defined when one code dominates; beside Cohen's kappa, decides nothing")
        # How many resamples define K033's kappa (its interval is read only on those).
        rs = groups.get("K033")
        if rs:
            a = [r["coder1"] for r in rs]
            b = [r["coder2"] for r in rs]
            labels = sorted(set(a) | set(b))
            code = {c: i for i, c in enumerate(labels)}
            ai = np.array([code[x] for x in a])
            bi = np.array([code[x] for x in b])
            rng = np.random.default_rng(SEED)
            idx = rng.integers(0, len(a), size=(RESAMPLES, len(a)))
            A, B = ai[idx], bi[idx]
            pe = np.zeros(RESAMPLES)
            for c in range(len(labels)):
                pe += (A == c).mean(axis=1) * (B == c).mean(axis=1)
            ok = int((pe < 1.0).sum())
            reg.add("door.K033.review.kappa.defined_resamples", ok,
                    "%s of 10,000 resamples define kappa (the others hold no unclear code and give "
                    "one label on both sides); every defined one gives 0" % fmt_int(ok), src,
                    note="door.K033.review.kappa reads its interval on these resamples only; kappa is "
                         "uninformative here, raw agreement is door.K033.review.raw_agreement")
    if ctx.has_data("corrections_weekly.csv") and ctx.has_data("rules.csv"):
        import table03_per_rule as t03
        rows = ctx.read_csv("corrections_weekly.csv")
        agg = t03.per_rule(rows)
        rules = t03.rules_with_corrections(agg)
        prose = [rid for rid in rules if "prose" in agg[rid] and agg[rid]["prose"][1] >= t03.MIN_EXPOSURE]
        with_one = [rid for rid in prose if agg[rid]["prose"][0] > 0]
        src = "data/corrections_weekly.csv"
        reg.add("perrule.prose.rules_with_a_correction", len(with_one),
                "%d of %d rules rated in the prose state received at least one correction in it; %d "
                "received none (%s)" % (len(with_one), len(prose), len(prose) - len(with_one),
                                        ", ".join(r for r in prose if r not in with_one)), src,
                k=len(with_one), n=len(prose),
                note="the per-rule table holds only rules with at least one correction mapped to them "
                     "in any state, so its median is conditional on those rules")
        inv = ctx.read_csv("rules.csv")
        prose_only = [r["id"] for r in inv if r["delivery"] == "prose only"]
        none = [rid for rid in prose_only if rid not in rules]
        reg.add("perrule.prose_only.rules_without_correction", len(none),
                "%d of %d prose-only rules have no correction mapped to them in any week" % (
                    len(none), len(prose_only)), "data/rules.csv; data/corrections_weekly.csv",
                k=len(none), n=len(prose_only))
    if ctx.has_data("transcripts_weekly.csv"):
        rows = ctx.read_csv("transcripts_weekly.csv")
        src = "data/transcripts_weekly.csv"
        sess = Counter()
        for r in rows:
            w = window_of(r["week"])
            if w is None or r["session_kind"] not in MAIN_KINDS:
                continue
            sess[(r["repo_group"], w)] += num(r["sessions"])
        for (g, w), n in sorted(sess.items()):
            reg.add("ask.%s.%s.sessions" % (g, w), n, "%s sessions" % fmt_int(n), src,
                    note="operator sessions and popped terminals that started in the window; the "
                         "turn ends of the ask shares are nested in them, and the Wilson intervals "
                         "treat each turn end as independent")
    des = ctx.e1 / "design.json"
    if des.exists() and ctx.has_data("rules.csv"):
        design = json.loads(des.read_text(encoding="utf-8"))
        inv = {r["id"]: r for r in ctx.read_csv("rules.csv")}
        for c, d in sorted(design["cases"].items()):
            rid = d.get("rule")
            if not rid or rid not in inv:
                continue
            r = inv[rid]
            lines = "; ".join("lines %d to %d" % (a, b) for a, b in d.get("ablate") or [])
            reg.add("e1.%s.production_prose_units" % c, num(r["n_prose_units"]),
                    "%s: %s prose unit%s in production (%s); AP restores the paragraph of the "
                    "pinned global file (%s) and nothing else" % (
                        rid, r["n_prose_units"] or "0", "" if num(r["n_prose_units"]) == 1 else "s",
                        ", ".join(x.strip() for x in (r["prose_sources"] or "none").split(";")), lines),
                    "data/rules.csv; e1/design.json", rule=rid)


def first_graders_c_section(ctx, reg, e1_rows):
    gpath, rpath = ctx.e1 / "graders_first_committed.py", ctx.e1 / "regrade.py"
    if not gpath.exists() or not rpath.exists() or not (ctx.e1 / "runs.jsonl").exists():
        return None, None
    first = _load_module(gpath, "e1_graders_first_r3")
    regrade = _load_module(rpath, "e1_regrade_r3")
    runs = {r["order"]: r for r in _read_jsonl(ctx.e1 / "runs.jsonl")}
    changed = Counter()
    for r in e1_rows:
        info, state = regrade.rebuild(runs[r["order"]])
        if bool(first.complete(r["case"], info, state)) != (r.get("C") is True):
            changed[r["case"]] += 1
    reg.add("e1.first_graders.runs_with_another_C", sum(changed.values()),
            "%d of %d runs (%s)" % (sum(changed.values()), len(e1_rows),
                                    ", ".join("%s %d" % (c, changed[c]) for c in sorted(changed)) or "none"),
            RUNS1, k=sum(changed.values()), n=len(e1_rows), per_case=dict(sorted(changed.items())),
            note="completion under the graders as first committed against the counted graders; C1's "
                 "and C4's first completion graders check files of their first situations")
    return first, regrade


# ---------------------------------------------------------------- 8. three decimals

def twins_section(reg):
    ent = reg.entries
    for key in sorted(ent):
        e = ent[key]
        if not key.startswith(("e1.", "e2.")) or key.endswith(".three_decimals"):
            continue
        if e.get("ci_method") != BOOT or e.get("value") is None or "interval" not in e:
            continue
        if key + ".three_decimals" in ent:
            continue
        reg.add(key + ".three_decimals", e["value"], fmt_diff(e["value"], e["interval"], 3), e["source"],
                ci=e["interval"], ci_method=e.get("ci_method"),
                note="the same value and interval printed to three decimals")


# ---------------------------------------------------------------- run

def run(ctx):
    res, des = ctx.e1 / "results.jsonl", ctx.e1 / "design.json"
    if not res.exists() or not des.exists():
        raise Missing("e1/results.jsonl or e1/design.json not found")
    if not (ctx.e1 / "runs.jsonl").exists():
        raise Missing("e1/runs.jsonl not found")
    reg = ctx.registry
    e1_rows = _counted(_read_jsonl(res))
    e2_rows = _counted(_read_jsonl(ctx.e2 / "results.jsonl")) if (ctx.e2 / "results.jsonl").exists() else None
    pilot_section(ctx, reg)
    subsets_section(reg, e1_rows, e2_rows)
    small_sample_section(reg, e1_rows, e2_rows)
    first, regrade1 = first_graders_c_section(ctx, reg, e1_rows)
    g1 = _load_module(ctx.e1 / "graders.py", "e1_graders_r3")
    hit = [r for r in _read_jsonl(ctx.e1 / "runs.jsonl") if r["case"] == "C1"]
    if (ctx.e2 / "graders.py").exists():
        g2 = _load_module(ctx.e2 / "graders.py", "e2_graders_r3")
        flagged = [r["order"] for r in hit if g2.c1_asks(r["closing_text"] or "")]
        reg.add("e1.C1.flagged_by_corrected_grader", len(flagged),
                "%d of %d counted C1 closing texts: no counted E1 run is an example the corrected "
                "grader flags" % (len(flagged), len(hit)) if not flagged else
                "%d of %d counted C1 closing texts (orders %s)" % (len(flagged), len(hit),
                                                                  ", ".join(map(str, flagged))),
                RUNS1, k=len(flagged), n=len(hit),
                note="e1.C1.example_flagged names the lowest order the counted grader flags, which "
                     "E2's corrected grader passes")
    runs1 = _read_jsonl(ctx.e1 / "runs.jsonl")
    runs_section(ctx, reg, "e1", e1_rows, runs1, g1, regrade1, g1)
    c4_text_section(reg, "e1", runs1, e1_rows, g1)
    c3_section(reg, "e1", runs1, e1_rows, g1, first)
    if e2_rows is not None and (ctx.e2 / "runs.jsonl").exists():
        regrade2 = _load_module(ctx.e2 / "regrade.py", "e2_regrade_r3")
        runs2 = _read_jsonl(ctx.e2 / "runs.jsonl")
        runs_section(ctx, reg, "e2", e2_rows, runs2, regrade2.graders, regrade2, regrade2.graders.e1)
        c4_text_section(reg, "e2", runs2, e2_rows, regrade2.graders.e1)
        c3_section(reg, "e2", runs2, e2_rows, regrade2.graders.e1, first)
        e4 = [r for r in e2_rows if r["case"] == "C4S" and "stop" in r["arm"]]
        k = sum(1 for r in e4 for x in (r.get("K_stop") or []) if x is True)
        n = sum(len(r.get("K_stop") or []) for r in e4)
        add_prop(reg, "e2.h5.stop.k.one_decimal", k, n, E2_SRC, digits=1,
                 note="e2.h5.stop.k to one decimal: its Wilson upper bound passes 0.5")
        if first is not None:
            e2_first_c3_section(reg, e2_rows, runs2, regrade2, first)
    facts_section(ctx, reg)
    reconcile_section(ctx, reg)
    coding_section(ctx, reg)
    twins_section(reg)


if __name__ == "__main__":
    sys.exit(standalone(run))
