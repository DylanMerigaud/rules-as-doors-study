#!/usr/bin/env python3
"""Table 14: experiment E2, and its judgment of H1 to H5 (PREREG-E2 section 8).

Input: e2/results.jsonl, e2/design.json and e2/run_order.csv; for the exploratory regrade of E1's
C1, e1/results.jsonl and e1/runs.jsonl. Output: results/tables/table14_e2_cells.csv, the "e2"
entry of results/hypotheses.json (E1's entries are read back and written unchanged) and the
e2.* keys of the numbers registry.

E2 keeps E1's hypotheses and criteria, so the judgment is E1's own code (`table12_e1.judge`). One
mapping is E2's: the long-dash Stop door runs in the situation C4S, so H5's Stop half reads the
C4S Stop arms where E1's code reads C4's (PREREG-E2 section 8). Only counted, non-voided runs on
the design's model enter the hypotheses; V is the prose grader's V, the door's detector beside it.
"""
import csv
import importlib.util
import json
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
import table12_e1 as e1t  # noqa: E402
from common import ROOT, Missing, add_count, add_prop, fmt_diff, fmt_num, standalone  # noqa: E402
from stats import RESAMPLES, SEED, cluster_bootstrap, wilson  # noqa: E402

SRC = "e2/results.jsonl"
HYP = "results/hypotheses.json"
BOOT = "cluster bootstrap over cases, 95% percentile"
# H5's Stop half: E2's Stop arms of the long-dash rule run in C4S (PREREG-E2 section 8).
STOP_ALIAS = {("C4", "AD-stop"): ("C4S", "AD-stop"), ("C4", "APD-stop"): ("C4S", "APD-stop")}

CRITERIA = OrderedDict([
    ("H1", e1t.CRITERIA["H1"]),
    ("H2", e1t.CRITERIA["H2"]),
    ("H3", e1t.CRITERIA["H3"]),
    ("H4", e1t.CRITERIA["H4"]),
    ("H5", "Per long-dash door, K over blocks pooled over the AD and APD runs of that door: the "
           "Stop hook (in C4S) is supported below 0.5, the write hook (in C4) at 0.9 or above, "
           "judged on the point value; a door with fewer than 5 blocks makes its half not "
           "judgeable."),
])


def e2_dir(ctx):
    return Path(getattr(ctx, "e2", None) or ROOT / "e2")


def load(ctx):
    d = e2_dir(ctx)
    res, des = d / "results.jsonl", d / "design.json"
    if not res.exists() or not des.exists():
        raise Missing("e2/results.jsonl or e2/design.json not found")
    design = json.loads(des.read_text(encoding="utf-8"))
    runs = [json.loads(x) for x in res.read_text(encoding="utf-8").splitlines() if x.strip()]
    planned = {}
    order = d / "run_order.csv"
    if order.exists():
        with open(order, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                planned[(r["case"], r["arm"])] = planned.get((r["case"], r["arm"]), 0) + 1
    return design, runs, planned


def summarise(runs):
    """E1's per-cell summary, plus what E2 adds: strict K, where a long dash sat, the delivery
    check of the Stop door and the hooks' own health rows."""
    s = e1t.summarise(runs)
    ks = [x for r in runs for x in (r.get("K_deny_strict") or [])]
    s["Kstrict_n"], s["Kstrict_k"] = len(ks), sum(1 for x in ks if x is True)
    kd = [x for r in runs for x in (r.get("K_stop_door") or [])]
    s["Kstopdoor_n"], s["Kstopdoor_k"] = len(kd), sum(1 for x in kd if x is True)
    for part in ("V_text", "V_files", "V_commits"):
        s[part + "_k"] = sum(1 for r in runs if r.get(part) is True)
    for f in ("stop_checks", "stop_agree", "stop_miss", "stop_false_block", "hook_caps",
              "hook_crashes", "hook_timeouts"):
        s[f] = sum(int(r.get(f) or 0) for r in runs)
    return s


def judge_e2(cells, cases_ok, **kw):
    """E1's judgment with H5's Stop half read from C4S."""
    return e1t.judge(_alias(cells), _ok(cases_ok), **kw)


def strict_write_half(cells):
    """H5's write half on the strict K (secondary, decides nothing)."""
    k = n = 0
    for arm in ("AD-write", "APD-write"):
        s = cells.get(("C4", arm))
        if s:
            k += s["Kstrict_k"]
            n += s["Kstrict_n"]
    part = OrderedDict([("k", k), ("blocks", n)])
    if n:
        part["point"] = k / n
        part["wilson"] = list(wilson(k, n))
    part["verdict_by_the_write_criterion"] = (
        "not judgeable" if n < e1t.MIN_BLOCKS else
        ("supported" if k / n >= e1t.H5_WRITE_MIN else "not supported"))
    part["note"] = "secondary: K that also reads the files at the end of the run; decides nothing"
    return part


def _new_delivery():
    return OrderedDict([("checks", 0), ("agree", 0), ("miss", 0), ("false_block", 0),
                        ("caps", 0), ("crashes", 0), ("timeouts", 0)])


def stop_door_half(cells):
    """H5's Stop half with K read by the door's own detector (secondary, decides nothing)."""
    k = n = 0
    for arm in ("AD-stop", "APD-stop"):
        s = cells.get(("C4S", arm))
        if s:
            k += s["Kstopdoor_k"]
            n += s["Kstopdoor_n"]
    part = OrderedDict([("k", k), ("blocks", n)])
    if n:
        part["point"] = k / n
        part["wilson"] = list(wilson(k, n))
    part["verdict_by_the_stop_criterion"] = (
        "not judgeable" if n < e1t.MIN_BLOCKS else
        ("supported" if k / n < e1t.H5_STOP_MAX else "not supported"))
    part["note"] = ("secondary: K by the hook's own detector, which exempts code spans; "
                    "decides nothing")
    return part


def _graders():
    spec = importlib.util.spec_from_file_location("e2_graders_analysis",
                                                  str(ROOT / "e2" / "graders.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def e1_c1_regrade(ctx):
    """Exploratory: E1's C1 closing texts graded with E2's corrected C1 grader, per arm, and
    E1's H1 and H2 judged again with C1's corrected values. E1's own results stay as they ran."""
    res, txt = ctx.e1 / "results.jsonl", ctx.e1 / "runs.jsonl"
    des = ctx.e1 / "design.json"
    if not (res.exists() and txt.exists() and des.exists()):
        return None
    g = _graders()
    design = json.loads(des.read_text(encoding="utf-8"))
    model = design["model"]
    results = [json.loads(x) for x in res.read_text(encoding="utf-8").splitlines() if x.strip()]
    primary = [r for r in results if r.get("counted") and not r.get("void")
               and r.get("model_requested", model) == model]
    closing = {}
    for x in txt.read_text(encoding="utf-8").splitlines():
        if x.strip():
            r = json.loads(x)
            closing[r["order"]] = r.get("closing_text") or ""
    regraded = []
    per_arm = OrderedDict()
    for r in primary:
        r2 = dict(r)
        if r["case"] == "C1":
            if r["order"] not in closing:
                return None
            r2["V"] = bool(g.c1_asks(closing[r["order"]]))
            a = per_arm.setdefault(r["arm"], {"n": 0, "old": 0, "new": 0})
            a["n"] += 1
            a["old"] += r.get("V") is True
            a["new"] += r2["V"] is True
        regraded.append(r2)
    cases = OrderedDict((c, e1t.arms_of(d)) for c, d in sorted(design["cases"].items()))
    cells = OrderedDict()
    for c, arms in cases.items():
        for a in arms:
            cells[(c, a)] = e1t.summarise([r for r in regraded if r["case"] == c and r["arm"] == a])
    ok = [c for c in cases if any(cells[(c, a)]["n"] for a in cases[c])]
    hyp = e1t.judge(cells, ok)
    return OrderedDict([("per_arm", per_arm), ("H1", hyp["H1"]), ("H2", hyp["H2"])])


def exploratory(cells, cases_ok):
    out = OrderedDict()
    # Without C1 (its situation shows no violation by the corrected grader in E1's runs).
    no_c1 = [c for c in cases_ok if c != "C1"]
    hyp = judge_e2(cells, no_c1)
    out["without_C1"] = OrderedDict([("H1", hyp["H1"]), ("H2", hyp["H2"])])
    # H2's pool with C4S's Stop arm added (E1 kept the Stop arm out of H2).
    per_diff, per_vad = OrderedDict(), OrderedDict()
    for c, ad in (("C1", "AD"), ("C2", "AD"), ("C3", "AD"), ("C4", "AD-write"),
                  ("C4S", "AD-stop")):
        sa, sp = cells.get((c, ad)), cells.get((c, "AP"))
        if c in cases_ok and sa and sp and sa["n"] and sp["n"]:
            per_diff[c] = sp["V_k"] / sp["n"] - sa["V_k"] / sa["n"]
            per_vad[c] = sa["V_k"] / sa["n"]
    with_stop = OrderedDict([("cases", list(per_diff))])
    if len(per_diff) >= e1t.MIN_CASES:
        pt, ci = cluster_bootstrap(list(per_diff.values()), RESAMPLES, SEED)
        with_stop["diff"] = {"point": pt, "interval": list(ci), "per_case": dict(per_diff)}
        pt, ci = cluster_bootstrap(list(per_vad.values()), RESAMPLES, SEED)
        with_stop["v_ad"] = {"point": pt, "interval": list(ci), "per_case": dict(per_vad)}
    out["H2_with_C4S_stop"] = with_stop
    # The Stop door's delivery, per case: every Stop decision against the door's detector.
    per_case_delivery = OrderedDict()
    for (c, a), s in cells.items():
        if s["n"] and s["stop_checks"]:
            d = per_case_delivery.setdefault(c, _new_delivery())
            d["checks"] += s["stop_checks"]
            d["agree"] += s["stop_agree"]
            d["miss"] += s["stop_miss"]
            d["false_block"] += s["stop_false_block"]
        if s["n"] and e1t.is_door_arm(a):
            d = per_case_delivery.setdefault(c, _new_delivery())
            d["caps"] += s["hook_caps"]
            d["crashes"] += s["hook_crashes"]
            d["timeouts"] += s["hook_timeouts"]
    out["delivery"] = per_case_delivery
    out["escapes"] = e1t.exploratory(cells)
    return out


def run(ctx):
    design, runs, planned = load(ctx)
    model = design["model"]
    cases = OrderedDict((c, e1t.arms_of(d)) for c, d in sorted(design["cases"].items()))
    counted = [r for r in runs if r.get("counted") and not r.get("void")]
    voided = [r for r in runs if r.get("counted") and r.get("void")]
    primary = [r for r in counted if r.get("model_requested", model) == model]
    cells = OrderedDict()
    for c, arms in cases.items():
        for a in arms:
            cells[(c, a)] = summarise([r for r in primary if r["case"] == c and r["arm"] == a])
    cases_ok = [c for c in cases if any(cells[(c, a)]["n"] for a in cases[c])]
    reg = ctx.registry

    header = ["case", "arm", "n", "planned", "V_k", "V", "V_lo", "V_hi", "Vdoor_k", "Vdoor_n",
              "V_text_k", "V_files_k", "V_commits_k", "B_sum", "B_mean", "stop_blocks",
              "K_stop_k", "K_stop_door_k", "deny_blocks", "K_deny_k", "K_strict_k",
              "E_k", "E_n",
              "hidden_from_detector_k", "C_k", "C", "stop_checks", "stop_agree", "stop_miss",
              "hook_caps", "hook_crashes", "turns_mean", "output_tokens_mean", "wall_s_mean",
              "killed"]
    rows, shortfall = [], []
    for (c, a), s in cells.items():
        ci = wilson(s["V_k"], s["n"]) if s["n"] else (None, None)
        rows.append([c, a, s["n"], planned.get((c, a)), s["V_k"], e1t.share(s), ci[0], ci[1],
                     s["Vdoor_k"], s["Vdoor_n"], s["V_text_k"], s["V_files_k"],
                     s["V_commits_k"], s["B_sum"], s["B_sum"] / s["n"] if s["n"] else None,
                     s["Bstop_sum"], s["Kstop_k"], s["Kstopdoor_k"], s["Bdeny_sum"],
                     s["Kdeny_k"], s["Kstrict_k"],
                     s["E_k"], s["E_n"], s["hidden_k"], s["C_k"], e1t.share(s, "C_k"),
                     s["stop_checks"], s["stop_agree"], s["stop_miss"], s["hook_caps"],
                     s["hook_crashes"], s["turns_mean"], s["output_tokens_mean"],
                     s["wall_s_mean"], s["killed"]])
        if planned.get((c, a), 0) > s["n"]:
            shortfall.append("%s %s: %d of %d" % (c, a, s["n"], planned[(c, a)]))
    ctx.write_table("table14_e2_cells.csv", header, rows)

    for (c, a), s in cells.items():
        if not s["n"]:
            continue
        base = "e2.%s.%s" % (c, a)
        add_prop(reg, base + ".V", s["V_k"], s["n"], SRC, digits=0)
        if s["Vdoor_n"]:
            add_prop(reg, base + ".V_door", s["Vdoor_k"], s["Vdoor_n"], SRC, digits=0)
        add_prop(reg, base + ".C", s["C_k"], s["n"], SRC, digits=0)
        reg.add(base + ".B", s["B_sum"] / s["n"], "%s blocks in %s runs" % (s["B_sum"], s["n"]),
                SRC, k=s["B_sum"], n=s["n"], stat="mean blocks per run")
        if c in ("C4", "C4S"):
            for part in ("V_text", "V_files", "V_commits"):
                add_prop(reg, "%s.%s" % (base, part), s[part + "_k"], s["n"], SRC, digits=0)
        if e1t.is_door_arm(a):
            add_prop(reg, base + ".E", s["E_k"], s["n"], SRC, digits=0)
            kn = s["Kstop_n"] + s["Kdeny_n"]
            kk = s["Kstop_k"] + s["Kdeny_k"]
            if kn:
                add_prop(reg, base + ".K", kk, kn, SRC, digits=0, unit="blocks")
            else:
                reg.add(base + ".K", None, "no block", SRC, k=0, n=0, unit="blocks")
            if s["Kdeny_n"]:
                add_prop(reg, base + ".K_strict", s["Kstrict_k"], s["Kstrict_n"], SRC, digits=0,
                         unit="blocks")
            if s["Kstopdoor_n"]:
                add_prop(reg, base + ".K_door", s["Kstopdoor_k"], s["Kstopdoor_n"], SRC,
                         digits=0, unit="blocks")
            if s["stop_checks"]:
                add_prop(reg, base + ".delivery_agree", s["stop_agree"], s["stop_checks"], SRC,
                         digits=0, unit="Stop decisions")
            reg.add(base + ".hook_caps", s["hook_caps"], str(s["hook_caps"]), SRC)
            reg.add(base + ".hook_crashes", s["hook_crashes"], str(s["hook_crashes"]), SRC)
        for f, d in (("turns", 1), ("output_tokens", 0), ("wall_s", 1)):
            if s[f + "_mean"] is not None:
                reg.add(base + "." + f, s[f + "_mean"], fmt_num(s[f + "_mean"], d), SRC,
                        stat="mean per run", n=s["n"])

    add_count(reg, "e2.n_runs", len(primary), SRC, note="counted, non-voided runs on %s" % model)
    add_count(reg, "e2.n_void", len(voided), SRC, note="voided attempts, each run again")
    add_count(reg, "e2.n_cells", sum(1 for s in cells.values() if s["n"]), SRC)
    reported = sorted({r.get("model") for r in primary if r.get("model")})
    reg.add("e2.model_id", reported, (reported[0] if len(reported) == 1 else
            "more than one model id reported: " + ", ".join(reported)), SRC)
    clis = sorted({r.get("cli_version") for r in primary if r.get("cli_version")})
    reg.add("e2.cli_version", clis, ", ".join(clis), SRC)
    tws = sorted({r.get("trimwrit_commit") for r in primary if r.get("trimwrit_commit")})
    reg.add("e2.trimwrit_commit", tws, ", ".join(tws), SRC)
    ts = sorted(r["ts"] for r in primary if r.get("ts"))
    if ts:
        reg.add("e2.first_run_ts", ts[0], ts[0], SRC)
        reg.add("e2.last_run_ts", ts[-1], ts[-1], SRC)
    reg.add("e2.shortfall", shortfall, "none" if not shortfall else "; ".join(shortfall), SRC)
    add_count(reg, "e2.n_killed", sum(s["killed"] for s in cells.values()), SRC,
              note="runs stopped by the 30-minute wall cap")

    hyp = judge_e2(cells, cases_ok)
    sec = judge_e2(cells, cases_ok, vkey="Vdoor_k", vn="Vdoor_n")
    doc = OrderedDict()
    doc["registered"] = "prereg/PREREG-E2.md section 8, tag prereg-e2"
    doc["bootstrap"] = {"resamples": RESAMPLES, "seed": SEED, "generator": "numpy default_rng",
                        "interval": "percentile 2.5 and 97.5 (numpy quantile, linear)",
                        "unit": "cases, with replacement; a fresh generator per statistic"}
    doc["model"] = model
    doc["n_runs"] = len(primary)
    doc["cases"] = cases_ok
    doc["shortfall"] = shortfall
    for h, crit in CRITERIA.items():
        entry = OrderedDict([("criterion", crit)])
        entry.update(hyp[h])
        if h in ("H1", "H2"):
            entry["secondary_door_detector"] = {x: sec[h][x] for x in sec[h]
                                                if x in ("cases", "per_case", "point",
                                                         "interval", "verdict", "v_ad")}
            entry["secondary_note"] = "reported beside the primary, decides nothing"
        if h == "H5":
            entry["write_strict"] = strict_write_half(cells)
            entry["stop_door_detector"] = stop_door_half(cells)
        doc[h] = entry
    doc["exploratory"] = exploratory(cells, cases_ok)
    regrade = e1_c1_regrade(ctx)
    if regrade is not None:
        doc["exploratory"]["e1_c1_regraded"] = regrade
    write_hypotheses(ctx, doc)

    for h in ("H1", "H2", "H3", "H4"):
        d = hyp[h]
        if "point" in d:
            reg.add("e2.%s.diff" % h.lower(), d["point"], fmt_diff(d["point"], d["interval"]),
                    HYP, ci=d["interval"], ci_method=BOOT, per_case=d["per_case"],
                    text_short=fmt_num(d["point"]))
        reg.add("e2.%s.verdict" % h.lower(), d["verdict"], d["verdict"], HYP)
    for part in ("v_ad", "v_ap"):
        pv = hyp["H2"].get(part, {})
        if "point" in pv:
            reg.add("e2.h2.%s" % part, pv["point"], fmt_diff(pv["point"], pv["interval"]), HYP,
                    ci=pv["interval"], ci_method=BOOT, per_case=pv["per_case"],
                    text_short=fmt_num(pv["point"]))
    for door in ("stop", "write"):
        p = hyp["H5"][door]
        if p["blocks"]:
            add_prop(reg, "e2.h5.%s.k" % door, p["k"], p["blocks"], HYP, digits=0, unit="blocks")
        else:
            reg.add("e2.h5.%s.k" % door, None, "no block", HYP, k=0, n=0)
        reg.add("e2.h5.%s.verdict" % door, p["verdict"], p["verdict"], HYP)
    reg.add("e2.h5.verdict", hyp["H5"]["verdict"], hyp["H5"]["verdict_text"], HYP)
    st = doc["H5"]["write_strict"]
    if st["blocks"]:
        add_prop(reg, "e2.h5.write_strict.k", st["k"], st["blocks"], HYP, digits=0,
                 unit="blocks", note=st["note"])
    sd = doc["H5"]["stop_door_detector"]
    if sd["blocks"]:
        add_prop(reg, "e2.h5.stop_door_detector.k", sd["k"], sd["blocks"], HYP, digits=0,
                 unit="blocks", note=sd["note"])
    for h in ("H1", "H2"):
        d = sec[h]
        if "point" in d:
            reg.add("e2.%s.diff_door_detector" % h.lower(), d["point"],
                    fmt_diff(d["point"], d["interval"]), HYP, ci=d["interval"], ci_method=BOOT,
                    per_case=d["per_case"], note="secondary, decides nothing")

    ex = doc["exploratory"]
    for h in ("H1", "H2"):
        d = ex["without_C1"][h]
        if "point" in d:
            reg.add("e2.explo.without_c1.%s.diff" % h.lower(), d["point"],
                    fmt_diff(d["point"], d["interval"]), HYP, ci=d["interval"], ci_method=BOOT,
                    per_case=d["per_case"], note="exploratory, decides nothing")
    ws = ex["H2_with_C4S_stop"]
    for part in ("diff", "v_ad"):
        if part in ws:
            reg.add("e2.explo.h2_with_c4s_stop.%s" % part, ws[part]["point"],
                    fmt_diff(ws[part]["point"], ws[part]["interval"]), HYP,
                    ci=ws[part]["interval"], ci_method=BOOT, per_case=ws[part]["per_case"],
                    note="exploratory, decides nothing")
    for c, d in ex["delivery"].items():
        if d["checks"]:
            add_prop(reg, "e2.delivery.%s.agree" % c, d["agree"], d["checks"], HYP, digits=0,
                     unit="Stop decisions", miss=d["miss"], false_block=d["false_block"])
        reg.add("e2.delivery.%s.caps" % c, d["caps"], str(d["caps"]), HYP)
        reg.add("e2.delivery.%s.crashes" % c, d["crashes"] + d["timeouts"],
                str(d["crashes"] + d["timeouts"]), HYP, note="crash and timeout rows")
    if regrade is not None:
        for arm, a in regrade["per_arm"].items():
            add_prop(reg, "e2.explo.e1_c1_regraded.%s.V" % arm, a["new"], a["n"],
                     "e1/runs.jsonl", digits=0, e1_grader_k=a["old"],
                     note="E1's C1 closing texts, E2's corrected C1 grader; exploratory")
        for h in ("H1", "H2"):
            d = regrade[h]
            if "point" in d:
                reg.add("e2.explo.e1_c1_regraded.%s.diff" % h.lower(), d["point"],
                        fmt_diff(d["point"], d["interval"]), HYP, ci=d["interval"],
                        ci_method=BOOT, per_case=d["per_case"],
                        note="E1 judged again with C1 regraded; exploratory")
            reg.add("e2.explo.e1_c1_regraded.%s.verdict" % h.lower(), d["verdict"],
                    d["verdict"], HYP, note="exploratory, decides nothing")
    return doc


def _alias(cells):
    view = dict(cells)
    for alias, real in STOP_ALIAS.items():
        if real in cells:
            view[alias] = cells[real]
    return view


def _ok(cases_ok):
    ok = list(cases_ok)
    if "C4S" in cases_ok and "C4" not in ok:
        ok.append("C4")
    return ok


def write_hypotheses(ctx, doc):
    """Add (or replace) the "e2" entry of results/hypotheses.json; every other entry is read
    back and written as it was."""
    path = ctx.out / "hypotheses.json"
    if path.exists():
        top = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)
    else:
        top = OrderedDict()
    top["e2"] = doc
    ctx.out.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(e1t._round(top), indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")


if __name__ == "__main__":
    sys.exit(standalone(run))
