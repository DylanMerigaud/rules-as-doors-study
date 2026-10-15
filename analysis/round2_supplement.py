#!/usr/bin/env python3
"""Supplementary keys (review round 2, 2026-10-15): exploratory, descriptive or sensitivity
readings; none decides a hypothesis and no earlier key changes. Every value comes from public
files.

1. E1 under its graders as first committed (`e1/graders_first_committed.py`, verbatim from commit
   3bd3559, before the pilot): every counted run graded again from `e1/runs.jsonl`, the cells and
   H1 to H5 judged by the registered code (`table12_e1.judge`).
2. The 30 E1 pilot runs (`e1/pilot_runs.csv`): per situation, V as recorded at run time, under the
   first committed graders and under the counted graders.
3. A strict K for E1's write door: E2's registered strict K (`e2/graders.k_deny_strict`) applied to
   E1's runs, from the files each run left.
4. A two-stage bootstrap (cases, then runs within each cell) beside every pooled E1 and E2 value,
   and the registered criteria read on it; three-decimal twins; t intervals clipped to the range
   of their statistic; H1 over the four door cases.
5. Table 11 (earlier replays), per case with Wilson and Newcombe intervals.
6. RQ3 with and without the door-only rules; the rule labels recomputed from their members.
7. The ask door's control criterion and prediction 2 read word for word; the values known at the
   tag; the ask measures per model.
8. The weekly correction series per repository group, and the ask door's corrections per week.
9. The door refusal ledger without the planted test session; per door, raw agreement and the wrong
   share under each coder; the long-dash Stop blocks over every week and session kind.
10. Per case of E1 and E2, the door's detector against the prose grader; C4 with quoted and code
    text left out of the closing text.
"""
import csv
import importlib.util
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

from common import (KIND_SLUG, MAIN_KINDS, Missing, add_count, add_prop, fmt_diff, fmt_num, fmt_points,  # noqa: E402
                    in_series, num, standalone, window_of)
from stats import (RESAMPLES, SEED, cluster_bootstrap, cohen_kappa, kappa_bootstrap,  # noqa: E402
                   newcombe, percentile_interval)
import table12_e1 as t12  # noqa: E402

E1_SRC = "e1/results.jsonl"
E2_SRC = "e2/results.jsonl"
RUNS = "e1/runs.jsonl"
TWO_STAGE = ("two-stage bootstrap, 95% percentile: cases resampled with replacement, then the runs "
             "of each drawn case's cells resampled with replacement; numpy default_rng(20260930), "
             "10,000 resamples")
BOOT = "cluster bootstrap over cases, 95% percentile"
EXPLO = "exploratory, decides nothing"


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(Path(path).parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


def _read_jsonl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def _counted(rows, model):
    return [r for r in rows if r.get("counted") and not r.get("void")
            and r.get("model_requested", model) == model]


def _cells(rows, cases):
    out = OrderedDict()
    for c, arms in cases.items():
        for a in arms:
            out[(c, a)] = t12.summarise([r for r in rows if r["case"] == c and r["arm"] == a])
    return out


# ---------------------------------------------------------------- 4. the two-stage bootstrap

def two_stage(cases, terms_of, values, resamples=RESAMPLES, seed=SEED):
    """Mean over cases of a per-case statistic, with a two-stage percentile bootstrap.

    `cases`: the case ids; `terms_of(case)`: [(sign, field, arm)]; `values[(case, arm, field)]`:
    the run-level values of that cell. Stage one draws the cases exactly as the cluster bootstrap
    does (the same generator, the same first draw); stage two resamples, for every drawn position
    and term, the runs of that cell with replacement. Returns (point, (lo, hi), per_case)."""
    per_case = OrderedDict()
    arrs = OrderedDict()
    for c in cases:
        v = 0.0
        for sign, field, arm in terms_of(c):
            a = np.asarray(values[(c, arm, field)], dtype=float)
            arrs[(c, arm, field)] = a
            v += sign * float(a.mean())
        per_case[c] = v
    n = len(cases)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(resamples, n))
    total = np.zeros(resamples)
    for j in range(n):
        n_terms = len(terms_of(cases[0]))
        for t in range(n_terms):
            m_max = max(len(arrs[(c, terms_of(c)[t][2], terms_of(c)[t][1])]) for c in cases)
            u = rng.random((resamples, m_max))
            for ci, c in enumerate(cases):
                rows = idx[:, j] == ci
                if not rows.any():
                    continue
                sign, field, arm = terms_of(c)[t]
                a = arrs[(c, arm, field)]
                m = len(a)
                sel = np.floor(u[rows, :m] * m).astype(int)
                total[rows] += sign * a[sel].mean(axis=1)
    boot = total / n
    return float(np.mean(list(per_case.values()))), percentile_interval(boot), per_case


def run_values(rows):
    """{(case, arm, field): [run values]} for V, Vdoor, C and B."""
    out = {}
    for r in rows:
        c, a = r["case"], r["arm"]
        out.setdefault((c, a, "V"), []).append(1.0 if r.get("V") is True else 0.0)
        if r.get("V_door") is not None:
            out.setdefault((c, a, "Vdoor"), []).append(1.0 if r.get("V_door") is True else 0.0)
        out.setdefault((c, a, "C"), []).append(1.0 if r.get("C") is True else 0.0)
        out.setdefault((c, a, "B"), []).append(float(int(r.get("B") or 0)))
    return out


def _spec(kind, field="V", ad_of=None):
    """The per-case terms of a pooled statistic, as table12_e1.judge defines it."""
    ad_of = ad_of or (lambda c: t12.AD_ARM[c])
    if kind == "h1":
        return lambda c: [(1, field, "A0"), (-1, field, "AP")]
    if kind == "h2":
        return lambda c: [(1, field, "AP"), (-1, field, ad_of(c))]
    if kind == "v_ad":
        return lambda c: [(1, field, ad_of(c))]
    if kind == "v_ap":
        return lambda c: [(1, field, "AP")]
    if kind == "h3":
        return lambda c: [(1, "C", ad_of(c)), (-1, "C", "A0")]
    if kind == "h4":
        return lambda c: [(1, "B", t12.APD_ARM[c]), (-1, "B", ad_of(c))]
    raise KeyError(kind)


E1_POOLED = (
    ("e1.h1.diff", "h1", "V"), ("e1.h1.diff.door_detector", "h1", "Vdoor"),
    ("e1.h2.diff", "h2", "V"), ("e1.h2.diff.door_detector", "h2", "Vdoor"),
    ("e1.h2.diff.without_C1", "h2", "V"),
    ("e1.h2.v_ad", "v_ad", "V"), ("e1.h2.v_ad.C1_to_C3", "v_ad", "V"),
    ("e1.h2.v_ad.door_detector", "v_ad", "Vdoor"), ("e1.h2.v_ad.without_C1", "v_ad", "V"),
    ("e1.h2.v_ap", "v_ap", "V"), ("e1.h2.v_ap.door_detector", "v_ap", "Vdoor"),
    ("e1.h3.diff", "h3", "C"), ("e1.h3.diff.without_C1", "h3", "C"),
    ("e1.h4.diff", "h4", "B"), ("e1.h4.diff.without_C1", "h4", "B"),
)
E2_POOLED = (
    ("e2.h1.diff", "h1", "V"), ("e2.h1.diff_door_detector", "h1", "Vdoor"),
    ("e2.h2.diff", "h2", "V"), ("e2.h2.diff_door_detector", "h2", "Vdoor"),
    ("e2.h2.v_ad", "v_ad", "V"), ("e2.h2.v_ap", "v_ap", "V"),
    ("e2.h3.diff", "h3", "C"), ("e2.h4.diff", "h4", "B"),
    ("e2.explo.without_c1.h1.diff", "h1", "V"), ("e2.explo.without_c1.h2.diff", "h2", "V"),
    ("e2.explo.h2_with_c4s_stop.diff", "h2s", "V"), ("e2.explo.h2_with_c4s_stop.v_ad", "v_ads", "V"),
)
WITH_C4S_STOP = {"C1": "AD", "C2": "AD", "C3": "AD", "C4": "AD-write", "C4S": "AD-stop"}


def _terms(kind, field):
    if kind == "h2s":
        return _spec("h2", field, lambda c: WITH_C4S_STOP[c])
    if kind == "v_ads":
        return _spec("v_ad", field, lambda c: WITH_C4S_STOP[c])
    return _spec(kind, field)


def _range(kind):
    return (0.0, 1.0) if kind in ("v_ad", "v_ap", "v_ads") else (-1.0, 1.0)


def add_two_stage(reg, key, kind, field, values, source, per_case_expected):
    cases = list(per_case_expected)
    pt, ci, per = two_stage(cases, _terms(kind, field), values)
    for c in cases:
        if abs(per[c] - per_case_expected[c]) > 1e-9:
            raise ValueError("%s: per-case value of %s differs from the registered one" % (key, c))
    reg.add(key + ".two_stage", pt, fmt_diff(pt, ci), source, ci=ci, ci_method=TWO_STAGE,
            per_case=dict(per), cases=cases, text_short=fmt_num(pt),
            note="sensitivity beside %s (whose interval resamples cases only); decides nothing" % key)
    return pt, ci


def verdicts_two_stage(reg, prefix, ivs, source):
    """The registered criteria of H1 to H4 read on the two-stage intervals."""
    out = OrderedDict()
    if "h1" in ivs:
        out["h1"] = ivs["h1"][1][0] > 0
    if "h2" in ivs and "v_ad" in ivs:
        out["h2"] = ivs["v_ad"][0] <= t12.H2_MAX_V and ivs["h2"][1][0] > 0
    if "h3" in ivs:
        out["h3"] = ivs["h3"][1][0] > t12.H3_FLOOR
    if "h4" in ivs:
        out["h4"] = ivs["h4"][1][1] < 0
    for h, ok in out.items():
        v = "supported" if ok else "not supported"
        reg.add("%s.%s.verdict.two_stage" % (prefix, h), v, v, source,
                note="the registered criterion applied to the two-stage interval; decides nothing")


def bootstrap_section(ctx, reg, e1_rows, e2_rows, first_rows):
    ent = reg.entries
    v1 = run_values(e1_rows)
    ivs = {}
    for key, kind, field in E1_POOLED:
        if key not in ent or "per_case" not in ent[key]:
            continue
        pt, ci = add_two_stage(reg, key, kind, field, v1, E1_SRC, ent[key]["per_case"])
        if key in ("e1.h1.diff", "e1.h2.diff", "e1.h2.v_ad", "e1.h3.diff", "e1.h4.diff"):
            ivs[kind] = (pt, ci)
    verdicts_two_stage(reg, "e1", ivs, E1_SRC)
    if e2_rows is not None:
        v2 = run_values(e2_rows)
        ivs = {}
        for key, kind, field in E2_POOLED:
            if key not in ent or "per_case" not in ent[key]:
                continue
            pt, ci = add_two_stage(reg, key, kind, field, v2, E2_SRC, ent[key]["per_case"])
            if key in ("e2.h1.diff", "e2.h2.diff", "e2.h2.v_ad", "e2.h3.diff", "e2.h4.diff"):
                ivs[kind] = (pt, ci)
        verdicts_two_stage(reg, "e2", ivs, E2_SRC)
    # The E1 C1 regrade with E2's corrected grader (an E2 exploratory key), at the run level.
    c1r = ctx.e2 / "graders.py"
    if "e2.explo.e1_c1_regraded.h1.diff" in ent and c1r.exists():
        g2 = _load_module(c1r, "e2_graders_r2")
        closing = {r["order"]: r.get("closing_text") or "" for r in _read_jsonl(ctx.e1 / "runs.jsonl")}
        rows = []
        for r in e1_rows:
            r2 = dict(r)
            if r["case"] == "C1":
                r2["V"] = bool(g2.c1_asks(closing[r["order"]]))
            rows.append(r2)
        vr = run_values(rows)
        for h, kind in (("h1", "h1"), ("h2", "h2")):
            key = "e2.explo.e1_c1_regraded.%s.diff" % h
            add_two_stage(reg, key, kind, "V", vr, RUNS, ent[key]["per_case"])
    if first_rows is not None:
        vf = run_values(first_rows)
        for key, kind, field in (("e1.first_graders.h1.diff", "h1", "V"),
                                 ("e1.first_graders.h2.diff", "h2", "V"),
                                 ("e1.first_graders.h2.v_ad", "v_ad", "V"),
                                 ("e1.first_graders.h3.diff", "h3", "C")):
            if key in ent:
                add_two_stage(reg, key, kind, field, vf, RUNS, ent[key]["per_case"])
    # Three decimals for every pooled value (R4-m2) and t intervals clipped to the range (R4-m1).
    for key, kind, _field in E1_POOLED + E2_POOLED:
        e = ent.get(key)
        if not e or e.get("value") is None or "interval" not in e:
            continue
        reg.add(key + ".three_decimals", e["value"], fmt_diff(e["value"], e["interval"], 3),
                e["source"], ci=e["interval"], ci_method=e.get("ci_method"),
                note="the same value and interval printed to three decimals")
    for key, kind in (("e1.h1.diff.t95", "h1"), ("e1.h2.diff.t95", "h2"), ("e1.h2.v_ad.t95", "v_ad"),
                      ("e1.h2.v_ap.t95", "v_ap"), ("e1.h3.diff.t95", "h3")):
        e = ent.get(key)
        if not e:
            continue
        lo_b, hi_b = _range(kind)
        ci = (max(lo_b, e["interval"][0]), min(hi_b, e["interval"][1]))
        reg.add(key + ".clipped", e["value"], fmt_diff(e["value"], ci), e["source"], ci=ci,
                ci_method="Student t 95%% over the per-case values, cut at the range of the "
                          "statistic (%g to %g)" % (lo_b, hi_b),
                clipped=[ci[0] != e["interval"][0], ci[1] != e["interval"][1]])
    # H1 over C1 to C4, the case set of the detector's H1 (R4-m3, R1-R16).
    for prefix, rows, src in (("e1", e1_rows, E1_SRC), ("e2", e2_rows, E2_SRC)):
        if rows is None:
            continue
        vals = run_values(rows)
        if not all((c, a, "V") in vals for c in t12.H_CASES for a in ("A0", "AP")):
            continue
        per = OrderedDict((c, float(np.mean(vals[(c, "A0", "V")])) - float(np.mean(vals[(c, "AP", "V")])))
                          for c in t12.H_CASES)
        pt, ci = cluster_bootstrap(list(per.values()), RESAMPLES, SEED)
        reg.add("%s.h1.diff.C1_to_C4" % prefix, pt, fmt_diff(pt, ci), src, ci=ci, ci_method=BOOT,
                per_case=dict(per), cases=list(per), text_short=fmt_num(pt),
                note="the prose grader's H1 over the four cases the door's detector covers; decides nothing")


# ---------------------------------------------------------------- 1. graders as first committed

def first_graders_section(ctx, reg, design, e1_rows):
    gpath = ctx.e1 / "graders_first_committed.py"
    rpath = ctx.e1 / "regrade.py"
    if not gpath.exists() or not rpath.exists() or not (ctx.e1 / "runs.jsonl").exists():
        return None
    first = _load_module(gpath, "e1_graders_first_committed")
    regrade = _load_module(rpath, "e1_regrade_r2")
    runs = {r["order"]: r for r in _read_jsonl(ctx.e1 / "runs.jsonl")}
    rows, changed = [], Counter()
    for r in e1_rows:
        info, state = regrade.rebuild(runs[r["order"]])
        case = r["case"]
        r2 = dict(r)
        r2["V"] = bool(first.violation(case, info, state))
        r2["C"] = bool(first.complete(case, info, state))
        r2["K_stop"] = regrade.stop_blocks_took_effect(
            info, lambda t, case=case, state=state: first.text_violates(case, t, state))
        if r.get("E") is not None:
            r2["E"] = r2["V"]
        if r2["V"] != (r.get("V") is True):
            changed[case] += 1
        rows.append(r2)
    cases = OrderedDict((c, t12.arms_of(d)) for c, d in sorted(design["cases"].items()))
    cells = _cells(rows, cases)
    ok = list(cases)
    hyp = t12.judge(cells, ok)
    note = ("exploratory: E1's counted runs graded with the graders as first committed (3bd3559, "
            "before the pilot; e1/graders_first_committed.py); the counted graders decide")
    for (c, a), s in cells.items():
        if not s["n"]:
            continue
        add_prop(reg, "e1.first_graders.%s.%s.V" % (c, a), s["V_k"], s["n"], RUNS, digits=0, note=note)
        add_prop(reg, "e1.first_graders.%s.%s.C" % (c, a), s["C_k"], s["n"], RUNS, digits=0,
                 note=note + "; C1's and C4's first completion graders check files of their first "
                             "situations, which the counted situations do not have")
    reg.add("e1.first_graders.runs_with_another_V", sum(changed.values()),
            "%d of %d runs (%s)" % (sum(changed.values()), len(rows),
                                    ", ".join("%s %d" % (c, changed[c]) for c in sorted(changed)) or "none"),
            RUNS, k=sum(changed.values()), n=len(rows), per_case=dict(sorted(changed.items())), note=note)
    for h in ("H1", "H2", "H3", "H4"):
        d = hyp[h]
        if "point" in d:
            reg.add("e1.first_graders.%s.diff" % h.lower(), d["point"], fmt_diff(d["point"], d["interval"]),
                    RUNS, ci=d["interval"], ci_method=BOOT, per_case=d["per_case"],
                    text_short=fmt_num(d["point"]), note=note)
            pc = d["per_case"]
            reg.add("e1.first_graders.%s.diff.n_cases_positive" % h.lower(),
                    sum(1 for v in pc.values() if v > 0),
                    "%d of %d cases above 0, %d at 0, %d below" % (
                        sum(1 for v in pc.values() if v > 0), len(pc),
                        sum(1 for v in pc.values() if v == 0), sum(1 for v in pc.values() if v < 0)),
                    RUNS, n=len(pc))
        reg.add("e1.first_graders.%s.verdict" % h.lower(), d["verdict"], d["verdict"], RUNS,
                note=note + "; the registered criterion applied")
    for part in ("v_ad", "v_ap"):
        pv = hyp["H2"].get(part, {})
        if "point" in pv:
            reg.add("e1.first_graders.h2.%s" % part, pv["point"], fmt_diff(pv["point"], pv["interval"]),
                    RUNS, ci=pv["interval"], ci_method=BOOT, per_case=pv["per_case"],
                    text_short=fmt_num(pv["point"]), note=note)
    for door in ("stop", "write"):
        p = hyp["H5"][door]
        txt = "%d of %d blocks" % (p["k"], p["blocks"]) if p["blocks"] else "no block"
        reg.add("e1.first_graders.h5.%s" % door, p.get("point"), "%s: %s" % (txt, p["verdict"]), RUNS,
                k=p["k"], n=p["blocks"], note=note)
    # C3 alone under its first grader, the other cases as counted (the reviewers' reading).
    c3_only = [dict(r, V=f["V"]) if r["case"] == "C3" else r for r, f in zip(e1_rows, rows)]
    hyp3 = t12.judge(_cells(c3_only, cases), ok)
    for h in ("H1", "H2"):
        d = hyp3[h]
        if "point" in d:
            reg.add("e1.first_graders.c3_only.%s.diff" % h.lower(), d["point"],
                    fmt_diff(d["point"], d["interval"]), RUNS, ci=d["interval"], ci_method=BOOT,
                    per_case=d["per_case"], text_short=fmt_num(d["point"]),
                    note="exploratory: only C3 graded with its first committed grader")
        reg.add("e1.first_graders.c3_only.%s.verdict" % h.lower(), d["verdict"], d["verdict"], RUNS,
                note="exploratory, the registered criterion applied")
    return rows


# ---------------------------------------------------------------- 2. the pilot runs

def pilot_section(ctx, reg):
    p = ctx.e1 / "pilot_runs.csv"
    if not p.exists():
        return
    with open(p, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    src = "e1/pilot_runs.csv"
    sits = OrderedDict()
    for r in sorted(rows, key=lambda r: (r["case"], int(r["situation"]), int(r["run_index"]))):
        sits.setdefault((r["case"], r["situation"]), []).append(r)
    add_count(reg, "e1.pilot.n_runs", len(rows), src)
    add_count(reg, "e1.pilot.n_situations", len(sits), src)
    kept = {}
    for (c, s), rs in sits.items():
        last = max(int(x) for (cc, x) in sits if cc == c)
        kept[(c, s)] = int(s) == last
        for col, word in (("V_recorded_at_run_time", "recorded"), ("V_first_committed_graders", "first_graders"),
                          ("V_counted_graders", "counted_graders")):
            k = sum(1 for r in rs if r[col] == "1")
            reg.add("e1.pilot.%s.s%s.V_%s" % (c, s, word), k, "%d of %d" % (k, len(rs)), src, k=k, n=len(rs),
                    kept=kept[(c, s)])
    for col, word in (("V_first_committed_graders", "first_graders"), ("V_counted_graders", "counted_graders"),
                      ("V_recorded_at_run_time", "recorded")):
        none = [cs for cs, rs in sits.items() if not any(r[col] == "1" for r in rs)]
        reg.add("e1.pilot.situations_without_violation.%s" % word, len(none),
                "%d of %d situations (%s)" % (len(none), len(sits), ", ".join("%s situation %s" % x for x in none)),
                src, k=len(none), n=len(sits))
        failing = [cs for cs in none if kept[cs]]
        reg.add("e1.pilot.kept_without_violation.%s" % word, len(failing),
                "%d of %d kept situations (%s)" % (len(failing), sum(kept.values()),
                                                   ", ".join("%s situation %s" % x for x in failing) or "none"),
                src, k=len(failing), n=sum(kept.values()),
                note="a kept situation with no violating pilot run fails the registered pilot rule")
        passing = [cs for cs, rs in sits.items() if not kept[cs] and any(r[col] == "1" for r in rs)]
        reg.add("e1.pilot.redesigned_with_a_violation.%s" % word, len(passing),
                "%d of %d redesigned situations (%s)" % (len(passing), len(sits) - sum(kept.values()),
                                                         ", ".join("%s situation %s" % x for x in passing) or "none"),
                src, k=len(passing), n=len(sits) - sum(kept.values()))
    same = sum(1 for r in rows if r["V_recorded_at_run_time"] == r["V_first_committed_graders"])
    reg.add("e1.pilot.recorded_equals_first_graders", same, "%d of %d pilot runs" % (same, len(rows)), src,
            k=same, n=len(rows), note="V as the driver recorded it when the run ended equals V under "
                                      "the graders as first committed")
    ts = sorted(r["batch_started_utc"] for r in rows)
    reg.add("e1.pilot.first_batch_utc", ts[0], ts[0], src)
    reg.add("e1.pilot.last_batch_utc", ts[-1], ts[-1], src)


# ---------------------------------------------------------------- 3. strict K for E1's write door

def strict_k_section(ctx, reg, e1_rows):
    gp = ctx.e2 / "graders.py"
    if not gp.exists() or not (ctx.e1 / "runs.jsonl").exists():
        return
    g2 = _load_module(gp, "e2_graders_strict")
    regrade = _load_module(ctx.e1 / "regrade.py", "e1_regrade_strict")
    runs = {r["order"]: r for r in _read_jsonl(ctx.e1 / "runs.jsonl")}
    tot_k = tot_n = 0
    failed = []
    for arm in ("AD-write", "APD-write"):
        k = n = 0
        for r in e1_rows:
            if r["case"] != "C4" or r["arm"] != arm or not r.get("K_deny"):
                continue
            _info, state = regrade.rebuild(runs[r["order"]])
            ks = g2.k_deny_strict(r["K_deny"], state)
            k += sum(1 for x in ks if x)
            n += len(ks)
            if not all(ks):
                failed.append("run order %d (%s, run %d)" % (r["order"], arm, r["run_index"]))
        tot_k += k
        tot_n += n
        if n:
            add_prop(reg, "e1.C4.%s.K_strict" % arm, k, n, RUNS, digits=0, unit="blocks",
                     note="E2's registered strict K applied to E1's runs; exploratory")
    if tot_n:
        add_prop(reg, "e1.h5.write_strict.k", tot_k, tot_n, RUNS, digits=1, unit="blocks",
                 note="exploratory: a denial took effect when the next accepted write to the same "
                      "target carried no long dash AND no file the run wrote nor commit text it "
                      "made carried one at the end of the run (E2's registered strict K).")
        reg.add("e1.h5.write_strict.not_taking_effect", len(failed), "; ".join(failed) or "none", RUNS)


# ---------------------------------------------------------------- 5. Table 11 per case

def replays_section(ctx, reg):
    if not ctx.has_data("replays_past.csv"):
        return
    rows = ctx.read_csv("replays_past.csv")
    src = "data/replays_past.csv"
    tw = tn = ww = wn = 0
    for r in sorted(rows, key=lambda r: r["case_id"]):
        nw, kw = num(r["runs_without"]), num(r["violations_without"])
        n1, k1 = num(r["runs_with"]), num(r["violations_with"])
        base = "replays.%s" % r["case_id"]
        add_prop(reg, base + ".v_without", kw, nw, src, digits=0, note="the whole instruction file left out")
        add_prop(reg, base + ".v_with", k1, n1, src, digits=0, note="the whole instruction file given")
        d, ci = newcombe(k1, n1, kw, nw)
        reg.add(base + ".diff", d, fmt_diff(d, ci), src, ci=ci,
                ci_method="Newcombe hybrid score 95%, share without minus share with",
                text_short=fmt_num(d))
        tw, tn, ww, wn = tw + kw, tn + nw, ww + k1, wn + n1
    add_prop(reg, "replays.pooled_runs.v_without", tw, tn, src, digits=0,
             note="runs of the in-scope earlier replays pooled, unclustered, descriptive")
    add_prop(reg, "replays.pooled_runs.v_with", ww, wn, src, digits=0)
    d, ci = newcombe(ww, wn, tw, tn)
    reg.add("replays.pooled_runs.diff", d, fmt_diff(d, ci), src, ci=ci,
            ci_method="Newcombe hybrid score 95%, share without minus share with", text_short=fmt_num(d))


# ---------------------------------------------------------------- 6. RQ3 and the rule labels

def rules_section(ctx, reg):
    if not ctx.has_data("rules.csv"):
        return
    rules = ctx.read_csv("rules.csv")
    src = "data/rules.csv"

    def share_not_efull(rs):
        return sum(1 for r in rs if r["enforceability"] != "E-full"), len(rs)

    groups = OrderedDict([("prose only", [r for r in rules if r["delivery"] == "prose only"]),
                          ("both", [r for r in rules if r["delivery"] == "both"]),
                          ("door only", [r for r in rules if r["delivery"] == "door only"])])
    kp, np_ = share_not_efull(groups["prose only"])
    kb, nb = share_not_efull(groups["both"])
    kd, nd = share_not_efull(groups["door only"])
    add_prop(reg, "rules.both.share_not_efull", kb, nb, src,
             note="rules stated in prose AND enforced by a door, the door-only rules left out")
    add_prop(reg, "rules.door_only.share_not_efull", kd, nd, src,
             note="rules that exist only as a door; labelled by the two door coders from the door entry")
    for name, k, n in (("with_door", kb + kd, nb + nd), ("both", kb, nb)):
        d, ci = newcombe(k, n, kp, np_)
        reg.add("rules.rq3.diff.prose_only_minus_%s" % name, d, fmt_points(d, ci), src, ci=ci,
                ci_method="Newcombe hybrid score 95%: share not E-full, prose only minus " + name,
                text_short="%.1f points" % (100 * d),
                note="RQ3's contrast %s the 12 door-only rules" % ("with" if name == "with_door" else "without"))
    reg.add("rules.both.not_efull_ids", kb, ", ".join("%s (%s)" % (r["id"], r["enforceability"])
                                                     for r in groups["both"] if r["enforceability"] != "E-full")
            or "none",
            src, k=kb, n=nb)
    if not ctx.has_data("rule_members.csv"):
        return
    mem = ctx.read_csv("rule_members.csv")
    msrc = "data/rule_members.csv"
    add_count(reg, "rules.members.n", len(mem), msrc, note="text units and door entries of the public rules")
    add_count(reg, "rules.members.n_door_entries", sum(1 for m in mem if m["kind"] == "door entry"), msrc)
    by = OrderedDict()
    for m in sorted(mem, key=lambda m: (m["rule_id"], int(m["member_order"]))):
        by.setdefault(m["rule_id"], []).append(m)
    agree = Counter()
    ties = {"class": [], "enforceability": []}
    unlike = []
    for rid, ms in by.items():
        r = next(x for x in rules if x["id"] == rid)
        for f, default in (("class", "other"), ("enforceability", "E-none")):
            labs = [m["final_" + f] for m in ms if m["final_" + f]]
            cnt = Counter(labs)
            lab = cnt.most_common(1)[0][0] if labs else default
            agree[f] += lab == r[f]
            top = sorted(cnt.values(), reverse=True)
            if len(top) > 1 and top[0] == top[1]:
                ties[f].append(rid)
        if any(m["coder1_enforceability"] and m["coder1_enforceability"] == m["coder2_enforceability"]
               and m["coder1_enforceability"] != r["enforceability"] for m in ms):
            unlike.append(rid)
    for f in ("class", "enforceability"):
        reg.add("rules.labels.recomputed_agree.%s" % f, agree[f], "%d of %d rules" % (agree[f], len(by)),
                msrc, k=agree[f], n=len(by),
                note="the rule label recomputed as the mode of its members' final labels, a tie going "
                     "to the earliest member, equals data/rules.csv")
        reg.add("rules.labels.ties.%s" % f, len(ties[f]), "%d rules (%s)" % (len(ties[f]), ", ".join(ties[f]) or "none"),
                msrc, n=len(by), note="rules whose two most frequent member labels tie; the earliest member decides")
    reg.add("rules.labels.agreed_unit_unlike_rule", len(unlike),
            "%d rules (%s)" % (len(unlike), ", ".join(unlike)), msrc, n=len(by),
            note="rules with at least one member both coders labelled alike with an enforceability "
                 "other than the rule's: the rule takes the mode of all its members")
    doors_only = [ms[0] for rid, ms in by.items() if all(m["kind"] == "door entry" for m in ms)]
    for f in ("class", "enforceability"):
        k = sum(1 for m in doors_only if m["coder1_" + f] == m["coder2_" + f])
        add_prop(reg, "rules.door_only.coders_agree.%s" % f, k, len(doors_only), msrc, digits=0,
                 note="the two door coders (the same model, run separately, the inventory codebook) on "
                      "the door entry of each door-only rule")
        de = [m for m in mem if m["kind"] == "door entry"]
        k = sum(1 for m in de if m["coder1_" + f] == m["coder2_" + f])
        add_prop(reg, "rules.door_entries.coders_agree.%s" % f, k, len(de), msrc, digits=0)
    split = [m for m in doors_only if m["coder1_class"] != m["coder2_class"]]
    reg.add("rules.door_only.class_disagreements", len(split),
            "; ".join("%s: %s against %s, resolved to %s" % (m["rule_id"], m["coder1_class"], m["coder2_class"],
                                                            m["final_class"]) for m in split) or "none", msrc)
    if ctx.has_data("rules_coding.csv"):
        units = ctx.read_csv("rules_coding.csv")
        csrc = "data/rules_coding.csv"
        not_both = [u for u in units if not (u["coder1_is_rule"] == "1" and u["coder2_is_rule"] == "1")]
        reg.add("rules.coding.units_not_both_rule", len(not_both),
                "%d units (%s)" % (len(not_both), ", ".join("%s of %s: %s and %s" % (
                    u["unit"], u["rule_id"], u["coder1_is_rule"] or "none", u["coder2_is_rule"] or "none")
                    for u in not_both)), csrc, n=len(units),
                note="units the two coders did not both call a rule; the resolver decided them")
        rids = sorted({u["rule_id"] for u in units})
        coded = {u["rule_id"] for u in units if u["coder1_is_rule"] == "1" and u["coder2_is_rule"] == "1"}
        reg.add("rules.coding.rules_outside_the_kappa", len(rules) - len(coded),
                "%d of %d rules: the %d door-only rules and %s" % (
                    len(rules) - len(coded), len(rules), nd, ", ".join(sorted(set(rids) - coded))),
                csrc, n=len(rules))
        both = [u for u in units if u["coder1_is_rule"] == "1" and u["coder2_is_rule"] == "1"]
        for f in ("class", "enforceability"):
            k, ci = rule_cluster_kappa(both, f)
            reg.add("rules.kappa_%s.rule_cluster" % f, k, "%.2f (%.2f to %.2f)" % (k, ci[0], ci[1]), csrc,
                    n=len(both), ci=ci, n_rules=len({u["rule_id"] for u in both}),
                    ci_method="bootstrap over rules (all units of a drawn rule), 95% percentile; "
                              "resamples with an undefined kappa left out",
                    label="model-coded", text_short="%.2f" % k)


def rule_cluster_kappa(units, f, resamples=RESAMPLES, seed=SEED):
    a = [u["coder1_" + f] or "null" for u in units]
    b = [u["coder2_" + f] or "null" for u in units]
    k = cohen_kappa(a, b)
    by = OrderedDict()
    for i, u in enumerate(units):
        by.setdefault(u["rule_id"], []).append(i)
    groups = list(by.values())
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(groups), size=(resamples, len(groups)))
    ks = []
    for row in idx:
        items = [i for g in row for i in groups[g]]
        kk = cohen_kappa([a[i] for i in items], [b[i] for i in items])
        if kk is not None:
            ks.append(kk)
    return k, percentile_interval(ks)


# ---------------------------------------------------------------- 7. the ask door's criteria

def ask_section(ctx, reg):
    ent = reg.entries
    b, a = ent.get("ask.control.before.answered_q"), ent.get("ask.control.after.answered_q")
    if b and a:
        fell = b["value"] >= 0.02 and a["value"] < 0.02
        reg.add("ask.criterion.control_drops.literal", fell,
                "not met as written: the control's share did not fall below 2 percent, it was already "
                "below (%s before, %s after)" % (b["text"], a["text"]) if not fell else
                "met as written: the control's share fell below 2 percent",
                "data/transcripts_weekly.csv", k=a["k"], n=a["n"],
                note="ANALYSIS.md section 6 read word for word ('falls below 2 percent'), which needs a "
                     "share at or above 2 percent before; ask.criterion.control_drops reads it as "
                     "'is below 2 percent'. With the control at 0 percent before, neither reading can "
                     "show a fall the door did not cause.")
    p = ent.get("prosp.control.answered_q")
    if p and b:
        reg.add("prosp.control.prediction2.literal", p["value"] >= 0.02,
                "the control's prospective share is %s, below the registered 2 percent, and its share "
                "before the door was %s; with %d turn ends the prediction is insufficient by the "
                "registered rule (fewer than 100)" % (p["text"], b["text"], p["n"]),
                "data/transcripts_prospective.csv", k=p["k"], n=p["n"],
                note="prediction 2 ('stay where they were ... at or above 2 percent') read word for word")
    if ctx.has_data("transcripts_prospective.csv"):
        rows = ctx.read_csv("transcripts_prospective.csv")
        for g in ("door", "control"):
            sel = [r for r in rows if r["part"] == "retrospective" and r["repo_group"] == g
                   and r["session_kind"] in MAIN_KINDS]
            add_prop(reg, "prosp.retrospective.%s.answered_q" % g,
                     sum(num(r["ends_q_trailing_replied"]) for r in sel),
                     sum(num(r["turn_ends"]) for r in sel), "data/transcripts_prospective.csv",
                     note="the after window up to the tag, final extraction: the part already "
                          "elapsed when the prospective thresholds were registered")
    if ctx.has_data("transcripts_weekly.csv"):
        rows = ctx.read_csv("transcripts_weekly.csv")
        cells = OrderedDict()
        for r in rows:
            w = window_of(r["week"])
            if w is None or r["session_kind"] not in MAIN_KINDS or r["model"] in ("", "none"):
                continue
            c = cells.setdefault((r["repo_group"], w, r["model"]), Counter())
            c["n"] += num(r["turn_ends"])
            c["k"] += num(r["ends_q_trailing_replied"])
            c["q"] += num(r["ends_q_last400"])
        for (g, w, m), c in sorted(cells.items()):
            if c["n"] < 100:
                continue
            add_prop(reg, "ask.%s.%s.by_model.%s.answered_q" % (g, w, m), c["k"], c["n"],
                     "data/transcripts_weekly.csv", note="cells of 100 turn ends or more")
            add_prop(reg, "ask.%s.%s.by_model.%s.qmark400" % (g, w, m), c["q"], c["n"],
                     "data/transcripts_weekly.csv")


# ---------------------------------------------------------------- 8. weekly corrections

def weekly_section(ctx, reg):
    if ctx.has_data("transcripts_weekly.csv"):
        rows = ctx.read_csv("transcripts_weekly.csv")
        agg = OrderedDict()
        for r in sorted(rows, key=lambda r: (r["week"], r["session_kind"], r["repo_group"])):
            if r["session_kind"] not in MAIN_KINDS or not in_series(r["week"]):
                continue
            c = agg.setdefault((r["week"], KIND_SLUG[r["session_kind"]], r["repo_group"]), Counter())
            c["k"] += num(r["corr_hits_operator_likely"])
            c["n"] += num(r["human_msgs_operator_likely"])
        for (w, kind, g), c in agg.items():
            if c["n"]:
                add_prop(reg, "weekly.%s.%s.%s.corr_per100" % (w, kind, g), c["k"], c["n"],
                         "data/transcripts_weekly.csv", unit="per 100 operator turns",
                         note="one session kind, one repository group (weekly.<week>.<kind>.corr_per100 "
                              "pools both groups)")
    if ctx.has_data("corrections_weekly.csv"):
        rows = ctx.read_csv("corrections_weekly.csv")
        k39 = [r for r in rows if r["rule_id"] == "K039" and r["week"][:4] == "2026"]
        if not k39:
            return
        reg.add("corrections.K039.weekly", sum(num(r["count"]) for r in k39),
                "; ".join("%s %s: %s in %s days" % (r["week"], r["state"], r["count"], r["exposure"])
                          for r in sorted(k39, key=lambda r: r["week"])),
                "data/corrections_weekly.csv",
                note="the ask rule's corrections per week, with its delivery state and exposure")
        for w in ("2026-09-21", "2026-09-28", "2026-10-05"):
            r = next((x for x in k39 if x["week"] == w), None)
            if r:
                reg.add("corrections.K039.%s" % w, num(r["count"]), "%s corrections in %s operator-active days"
                        % (r["count"], r["exposure"]), "data/corrections_weekly.csv", state=r["state"])


# ---------------------------------------------------------------- 9. the door ledger and review

def doors_section(ctx, reg):
    ent = reg.entries
    if ctx.has_data("door_refusals_test_rows.csv") and ctx.has_data("door_refusals_weekly.csv"):
        test = ctx.read_csv("door_refusals_test_rows.csv")
        weekly = ctx.read_csv("door_refusals_weekly.csv")
        tsrc = "data/door_refusals_test_rows.csv"
        add_count(reg, "door.test_rows.n", len(test), tsrc,
                  note="counted ledger refusals that came from a planted test session of the study")
        for rid in sorted({t["rule_id"] for t in test}):
            mine = [t for t in test if t["rule_id"] == rid]
            rs = [r for r in weekly if r["rule_id"] == rid]
            tot = sum(num(r["refusals"]) for r in rs) - len(mine)
            add_count(reg, "door.%s.refusals.without_test_session" % rid, tot, "data/door_refusals_weekly.csv")
            te = sum(num(r["took_effect"]) for r in rs) - sum(1 for t in mine if t["took_effect"] == "1")
            judged = sum(num(r["took_effect"]) + num(r["did_not"]) for r in rs) - \
                sum(1 for t in mine if t["took_effect"] in ("0", "1"))
            add_prop(reg, "door.%s.took_effect.without_test_session" % rid, te, judged,
                     "data/door_refusals_weekly.csv")
            for dt in sorted({t["door_type"] for t in mine}):
                slug = dt.lower().replace(" ", "_")
                sub = [r for r in rs if r["door_type"] == dt]
                drop = [t for t in mine if t["door_type"] == dt]
                n = sum(num(r["refusals"]) for r in sub) - len(drop)
                add_count(reg, "door.%s.refusals.%s.without_test_session" % (rid, slug), n,
                          "data/door_refusals_weekly.csv")
                k = sum(num(r["took_effect"]) for r in sub) - sum(1 for t in drop if t["took_effect"] == "1")
                j = sum(num(r["took_effect"]) + num(r["did_not"]) for r in sub) - \
                    sum(1 for t in drop if t["took_effect"] in ("0", "1"))
                add_prop(reg, "door.%s.refusals.%s.took_effect.without_test_session" % (rid, slug), k, j,
                         "data/door_refusals_weekly.csv")
            if ctx.has_data("door_review.csv"):
                rev = [r for r in ctx.read_csv("door_review.csv") if r["rule_id"] == rid]
                drop = [t for t in mine if t["in_review_sample"] == "1"]
                keep = list(rev)
                for t in drop:
                    for i, r in enumerate(keep):
                        if (r["stratum"], r["coder1"], r["coder2"], r["final"]) == \
                                (t["door_type"], t["coder1"], t["coder2"], t["final"]):
                            del keep[i]
                            break
                coded = [r for r in keep if r["final"] in ("right", "wrong")]
                add_count(reg, "door.%s.review.n_items.without_test_session" % rid, len(keep), "data/door_review.csv")
                add_prop(reg, "door.%s.wrong_share.without_test_session" % rid,
                         sum(1 for r in coded if r["final"] == "wrong"), len(coded), "data/door_review.csv")
        if ctx.has_data("door_review.csv"):
            rev = ctx.read_csv("door_review.csv")
            keep = list(rev)
            for t in test:
                if t["in_review_sample"] != "1":
                    continue
                for i, r in enumerate(keep):
                    if (r["rule_id"], r["stratum"], r["coder1"], r["coder2"], r["final"]) == \
                            (t["rule_id"], t["door_type"], t["coder1"], t["coder2"], t["final"]):
                        del keep[i]
                        break
            kb = kappa_bootstrap([r["coder1"] for r in keep], [r["coder2"] for r in keep])
            reg.add("door.review.kappa.without_test_session", kb[0], "%.2f (%.2f to %.2f)" % (kb[0], kb[1][0], kb[1][1]),
                    "data/door_review.csv", n=len(keep), ci=kb[1], ci_method="bootstrap over items, 95% percentile",
                    label="model-coded", text_short="%.2f" % kb[0])
    if ctx.has_data("door_review_frame.csv"):
        frame = ctx.read_csv("door_review_frame.csv")
        unloc = sum(num(r["refusals_in_ledger"]) - num(r["located_in_a_transcript"]) for r in frame)
        tot = sum(num(r["refusals_in_ledger"]) for r in frame)
        reg.add("door.refusals.not_located", unloc, "%d of %d refusals (%s)" % (unloc, tot, ", ".join(
            "%s %s %d" % (r["rule_id"], r["door_type"], num(r["refusals_in_ledger"]) - num(r["located_in_a_transcript"]))
            for r in frame if num(r["refusals_in_ledger"]) != num(r["located_in_a_transcript"]))),
            "data/door_review_frame.csv", k=unloc, n=tot,
            note="ledger rows whose session transcript holds no matching refusal: took effect cannot be judged")
    if ctx.has_data("door_review.csv"):
        rev = ctx.read_csv("door_review.csv")
        by = OrderedDict()
        for r in rev:
            by.setdefault(r["rule_id"], []).append(r)
        for rid, rs in by.items():
            agree = sum(1 for r in rs if r["coder1"] == r["coder2"])
            add_prop(reg, "door.%s.review.raw_agreement" % rid, agree, len(rs), "data/door_review.csv", digits=0)
            for c in ("coder1", "coder2"):
                coded = [r for r in rs if r[c] in ("right", "wrong")]
                add_prop(reg, "door.%s.wrong_share.%s" % (rid, c), sum(1 for r in coded if r[c] == "wrong"),
                         len(coded), "data/door_review.csv", digits=0,
                         note="the wrong share under one coder's codes alone, unclear left out")
    if ctx.has_data("transcripts_weekly.csv"):
        rows = ctx.read_csv("transcripts_weekly.csv")
        tot = sum(num(r["dash_stop_detected"]) for r in rows)
        add_count(reg, "dashstop.blocks.all_weeks_all_kinds", tot, "data/transcripts_weekly.csv",
                  note="every week on disk and every session kind; dashstop.blocks counts operator "
                       "sessions and popped terminals in the weeks before 2026-09-28")


# ---------------------------------------------------------------- 10. detector against grader

def detector_section(reg, e1_rows, e2_rows, runs, graders):
    for prefix, rows, src in (("e1", e1_rows, E1_SRC), ("e2", e2_rows, E2_SRC)):
        if rows is None:
            continue
        for c in sorted({r["case"] for r in rows if r.get("V_door") is not None}):
            rs = [r for r in rows if r["case"] == c and r.get("V_door") is not None]
            both = sum(1 for r in rs if r["V"] is True and r["V_door"] is True)
            g_only = sum(1 for r in rs if r["V"] is True and r["V_door"] is not True)
            d_only = sum(1 for r in rs if r["V"] is not True and r["V_door"] is True)
            neither = len(rs) - both - g_only - d_only
            reg.add("%s.%s.detector_vs_grader" % (prefix, c), both,
                    "%d runs: both flag %d, the grader only %d, the detector only %d, neither %d" % (
                        len(rs), both, g_only, d_only, neither), src,
                    n=len(rs), both=both, grader_only=g_only, detector_only=d_only, neither=neither,
                    note="over every arm; the door's detector read as a classifier of the prose "
                         "grader's V (no human label): recall both of grader-flagged, precision both "
                         "of detector-flagged")
            if both + g_only:
                add_prop(reg, "%s.%s.detector_recall_vs_grader" % (prefix, c), both, both + g_only, src, digits=0)
            if both + d_only:
                add_prop(reg, "%s.%s.detector_precision_vs_grader" % (prefix, c), both, both + d_only, src,
                         digits=0)
    if runs is None or graders is None:
        return
    # C4 with fenced code, inline code and quoted lines left out of the closing text (R3-R5).
    rec = {r["order"]: r for r in e1_rows}
    by = OrderedDict()
    for r in runs:
        if r["case"] != "C4":
            continue
        text_dash = graders.has_dash(graders.prose_only(r["closing_text"] or ""))
        files = any(graders.has_dash(v) for v in r["output_files"].values())
        commits = any(graders.has_dash(c.get("text")) for c in r["commits"])
        a = by.setdefault(r["arm"], {"n": 0, "v": 0, "counted": 0, "text_only": 0})
        a["n"] += 1
        a["v"] += bool(text_dash or files or commits)
        a["counted"] += rec[r["order"]]["V"] is True
        a["text_only"] += bool(graders.has_dash(r["closing_text"] or "") and not files and not commits)
    for arm, a in by.items():
        add_prop(reg, "e1.C4.%s.V_without_quoted_or_code_text" % arm, a["v"], a["n"], RUNS, digits=0,
                 counted_k=a["counted"],
                 note="exploratory: a long dash in fenced code, inline code or a quoted line of the "
                      "closing text is not counted (the C1 to C3 graders read prose only); files and "
                      "commit texts as counted.")


# ---------------------------------------------------------------- run

def run(ctx):
    res, des = ctx.e1 / "results.jsonl", ctx.e1 / "design.json"
    if not res.exists() or not des.exists():
        raise Missing("e1/results.jsonl or e1/design.json not found")
    reg = ctx.registry
    design = json.loads(des.read_text(encoding="utf-8"))
    e1_rows = _counted(_read_jsonl(res), design["model"])
    e2_rows = None
    if (ctx.e2 / "results.jsonl").exists() and (ctx.e2 / "design.json").exists():
        d2 = json.loads((ctx.e2 / "design.json").read_text(encoding="utf-8"))
        e2_rows = _counted(_read_jsonl(ctx.e2 / "results.jsonl"), d2["model"])
    first_rows = first_graders_section(ctx, reg, design, e1_rows)
    pilot_section(ctx, reg)
    strict_k_section(ctx, reg, e1_rows)
    bootstrap_section(ctx, reg, e1_rows, e2_rows, first_rows)
    replays_section(ctx, reg)
    rules_section(ctx, reg)
    ask_section(ctx, reg)
    weekly_section(ctx, reg)
    doors_section(ctx, reg)
    runs = _read_jsonl(ctx.e1 / "runs.jsonl") if (ctx.e1 / "runs.jsonl").exists() else None
    graders = _load_module(ctx.e1 / "graders.py", "e1_graders_r2") if (ctx.e1 / "graders.py").exists() else None
    detector_section(reg, e1_rows, e2_rows, runs, graders)


if __name__ == "__main__":
    sys.exit(standalone(run))
