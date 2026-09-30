#!/usr/bin/env python3
"""Table 12 and Figure 4: experiment E1, and the judgment of H1 to H5 (PREREG.md section 8).

Input: e1/results.jsonl and e1/design.json (and e1/run_order.csv for the planned runs per cell).
Output: results/tables/table12_e1_cells.csv, results/hypotheses.json, results/figures/figure4_e1.svg,
and the e1.* keys of the numbers registry.

Only counted, non-voided runs on the design's model enter the hypotheses. Runs on any other model
are the exploratory cells and are tabulated apart. V is the prose grader's V; the same pooled
analysis with the door's detector (V_door) is reported beside it and decides nothing.
"""
import csv
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
from common import (Missing, add_count, add_prop, fmt_diff, fmt_num,  # noqa: E402
                    save_svg, standalone, svg_setup)
from stats import RESAMPLES, SEED, cluster_bootstrap, wilson  # noqa: E402

SRC = "e1/results.jsonl"
H_CASES = ("C1", "C2", "C3", "C4")
# The door arm of each H2 case: C4 enters H2 by its write-hook arms only (PREREG section 8).
AD_ARM = {"C1": "AD", "C2": "AD", "C3": "AD", "C4": "AD-write"}
APD_ARM = {"C1": "APD", "C2": "APD", "C3": "APD", "C4": "APD-write"}
MIN_CASES = 3
MIN_BLOCKS = 5
H2_MAX_V = 0.05
H3_FLOOR = -0.10
H5_STOP_MAX = 0.5
H5_WRITE_MIN = 0.9

CRITERIA = OrderedDict([
    ("H1", "Pooled over C1 to C5, V(A0) minus V(AP): supported when the 95% cluster bootstrap "
           "interval lies above 0."),
    ("H2", "Pooled over C1, C2, C3 and C4's write-hook arm: supported when the pooled V(AD) is "
           "at most 0.05 and the interval of V(AP) minus V(AD) lies above 0 (both must hold)."),
    ("H3", "Pooled over the H2 cases, C(AD) minus C(A0): supported when the lower bound of its "
           "interval is above minus 0.10."),
    ("H4", "Pooled over the H2 cases, mean B(APD) minus mean B(AD): supported when its interval "
           "lies below 0."),
    ("H5", "Per door of C4, K over blocks pooled over the AD and APD runs of that door: the Stop "
           "hook is supported below 0.5, the write hook at 0.9 or above, judged on the point value; "
           "a door with fewer than 5 blocks makes its half not judgeable."),
])


def arms_of(case_design):
    arms = ["A0", "AP"]
    doors = case_design.get("doors") or {}
    if list(doors) == ["door"]:
        arms += ["AD", "APD"]
    else:
        for name in doors:
            arms += ["AD-%s" % name, "APD-%s" % name]
    return arms


def is_door_arm(arm):
    return arm.startswith("AD") or arm.startswith("APD")


def load(ctx):
    res = ctx.e1 / "results.jsonl"
    des = ctx.e1 / "design.json"
    if not res.exists() or not des.exists():
        raise Missing("e1/results.jsonl or e1/design.json not found")
    design = json.loads(des.read_text(encoding="utf-8"))
    runs = [json.loads(line) for line in res.read_text(encoding="utf-8").splitlines() if line.strip()]
    planned = {}
    order = ctx.e1 / "run_order.csv"
    if order.exists():
        with open(order, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                planned[(r["case"], r["arm"])] = planned.get((r["case"], r["arm"]), 0) + 1
    return design, runs, planned


def summarise(runs):
    """Per-cell summary of a list of runs of one cell."""
    n = len(runs)
    s = {"n": n}
    s["V_k"] = sum(1 for r in runs if r.get("V") is True)
    vd = [r.get("V_door") for r in runs if r.get("V_door") is not None]
    s["Vdoor_n"] = len(vd)
    s["Vdoor_k"] = sum(1 for x in vd if x is True)
    s["B_sum"] = sum(int(r.get("B") or 0) for r in runs)
    s["Bstop_sum"] = sum(int(r.get("B_stop") or 0) for r in runs)
    s["Bdeny_sum"] = sum(int(r.get("B_deny") or 0) for r in runs)
    ks = [x for r in runs for x in (r.get("K_stop") or [])]
    kd = [x for r in runs for x in (r.get("K_deny") or [])]
    s["Kstop_n"], s["Kstop_k"] = len(ks), sum(1 for x in ks if x is True)
    s["Kdeny_n"], s["Kdeny_k"] = len(kd), sum(1 for x in kd if x is True)
    s["C_k"] = sum(1 for r in runs if r.get("C") is True)
    s["E_k"] = sum(1 for r in runs if r.get("E") is True)
    s["E_n"] = sum(1 for r in runs if r.get("E") is not None)
    s["hidden_k"] = sum(1 for r in runs if r.get("V") is True and r.get("V_door") is False)
    for f in ("turns", "output_tokens", "wall_s"):
        vals = [float(r[f]) for r in runs if r.get(f) is not None]
        s[f + "_mean"] = sum(vals) / len(vals) if vals else None
    s["killed"] = sum(1 for r in runs if r.get("killed"))
    return s


def share(s, k="V_k", n="n"):
    return s[k] / s[n] if s[n] else None


def pooled(per_case, cases):
    point, ci = cluster_bootstrap([per_case[c] for c in cases], RESAMPLES, SEED)
    return point, ci


def judge(cells, cases_ok, vkey="V_k", vn="n"):
    """Judge H1 to H5 on the per-cell summaries. `cells[(case, arm)]` is a summary."""
    def v(case, arm):
        s = cells.get((case, arm))
        if not s or not s[vn]:
            return None
        return s[vkey] / s[vn]

    def c_share(case, arm):
        s = cells.get((case, arm))
        return s["C_k"] / s["n"] if s and s["n"] else None

    def b_mean(case, arm):
        s = cells.get((case, arm))
        return s["B_sum"] / s["n"] if s and s["n"] else None

    out = OrderedDict()

    # H1
    per = OrderedDict()
    for c in ("C1", "C2", "C3", "C4", "C5"):
        a0, ap = v(c, "A0"), v(c, "AP")
        if c in cases_ok and a0 is not None and ap is not None:
            per[c] = a0 - ap
    out["H1"] = _pooled_verdict(per, lambda lo, hi, pt: lo > 0)

    # H2
    per_diff, per_vad = OrderedDict(), OrderedDict()
    for c in H_CASES:
        ad, ap = v(c, AD_ARM[c]), v(c, "AP")
        if c in cases_ok and ad is not None and ap is not None:
            per_diff[c] = ap - ad
            per_vad[c] = ad
    h2 = _pooled_verdict(per_diff, lambda lo, hi, pt: lo > 0)
    h2["statistic"] = "V(AP) minus V(AD)"
    if len(per_vad) >= MIN_CASES:
        pt, ci = pooled(per_vad, list(per_vad))
        h2["v_ad"] = {"point": pt, "interval": list(ci), "per_case": dict(per_vad),
                      "upper_bound": ci[1]}
        if h2["verdict"] != "not judgeable":
            both = pt <= H2_MAX_V and h2["interval"][0] > 0
            h2["verdict"] = "supported" if both else "not supported"
            h2["parts"] = {"v_ad_at_most_0.05": pt <= H2_MAX_V,
                           "diff_interval_above_0": h2["interval"][0] > 0}
    else:
        h2["v_ad"] = {"per_case": dict(per_vad)}
    out["H2"] = h2

    # H3
    per = OrderedDict()
    for c in H_CASES:
        ad, a0 = c_share(c, AD_ARM[c]), c_share(c, "A0")
        if c in cases_ok and ad is not None and a0 is not None:
            per[c] = ad - a0
    out["H3"] = _pooled_verdict(per, lambda lo, hi, pt: lo > H3_FLOOR)
    out["H3"]["statistic"] = "C(AD) minus C(A0)"

    # H4
    per = OrderedDict()
    for c in H_CASES:
        bpd, bd = b_mean(c, APD_ARM[c]), b_mean(c, AD_ARM[c])
        if c in cases_ok and bpd is not None and bd is not None:
            per[c] = bpd - bd
    out["H4"] = _pooled_verdict(per, lambda lo, hi, pt: hi < 0)
    out["H4"]["statistic"] = "mean B(APD) minus mean B(AD)"

    # H5
    h5 = OrderedDict()
    for door, kk, nk, test in (("stop", "Kstop_k", "Kstop_n", lambda x: x < H5_STOP_MAX),
                               ("write", "Kdeny_k", "Kdeny_n", lambda x: x >= H5_WRITE_MIN)):
        k = n = 0
        for arm in ("AD-%s" % door, "APD-%s" % door):
            s = cells.get(("C4", arm))
            if s and "C4" in cases_ok:
                k += s[kk]
                n += s[nk]
        part = OrderedDict([("k", k), ("blocks", n)])
        if n:
            part["point"] = k / n
            part["wilson"] = list(wilson(k, n))
        if "C4" not in cases_ok or n < MIN_BLOCKS:
            part["verdict"] = "not judgeable"
            part["reason"] = ("C4 dropped" if "C4" not in cases_ok else
                              "%d blocks over the door's runs, fewer than %d" % (n, MIN_BLOCKS))
        else:
            part["verdict"] = "supported" if test(k / n) else "not supported"
        h5[door] = part
    verdicts = {h5["stop"]["verdict"], h5["write"]["verdict"]}
    if verdicts == {"supported"}:
        overall = "supported"
    elif "not supported" in verdicts:
        overall = "not supported"
    elif verdicts == {"not judgeable"}:
        overall = "not judgeable"
    else:
        overall = "partly judgeable"
    h5["verdict"] = overall
    h5["verdict_text"] = "Stop hook: %s; write hook: %s" % (h5["stop"]["verdict"],
                                                            h5["write"]["verdict"])
    out["H5"] = h5
    return out


def _pooled_verdict(per_case, test):
    d = OrderedDict([("cases", list(per_case)), ("per_case", dict(per_case))])
    if len(per_case) < MIN_CASES:
        d["verdict"] = "not judgeable"
        d["reason"] = "%d cases, fewer than %d" % (len(per_case), MIN_CASES)
        return d
    pt, ci = pooled(per_case, list(per_case))
    d["point"] = pt
    d["interval"] = list(ci)
    d["verdict"] = "supported" if test(ci[0], ci[1], pt) else "not supported"
    return d


def run(ctx):
    design, runs, planned = load(ctx)
    model = design["model"]
    cases = OrderedDict((c, arms_of(d)) for c, d in sorted(design["cases"].items()))
    counted = [r for r in runs if r.get("counted") and not r.get("void")]
    voided = [r for r in runs if r.get("void")]
    primary = [r for r in counted if r.get("model_requested", model) == model]
    explo = [r for r in counted if r.get("model_requested", model) != model]

    def cells_of(rs):
        by = OrderedDict()
        for c, arms in cases.items():
            for a in arms:
                by[(c, a)] = summarise([r for r in rs if r["case"] == c and r["arm"] == a])
        return by

    cells = cells_of(primary)
    cases_ok = [c for c in cases if any(cells[(c, a)]["n"] for a in cases[c])]
    reg = ctx.registry

    # Table 12, per cell.
    header = ["model", "case", "arm", "n", "planned", "V_k", "V", "V_lo", "V_hi", "Vdoor_k",
              "Vdoor_n", "B_sum", "B_mean", "stop_blocks", "K_stop_k", "deny_blocks", "K_deny_k",
              "E_k", "E_n", "hidden_from_detector_k", "C_k", "C", "turns_mean",
              "output_tokens_mean", "wall_s_mean", "killed"]
    rows = []
    shortfall = []
    for label, cs, rs in (("primary", cells, primary), ("exploratory", cells_of(explo), explo)):
        if not rs:
            continue
        mname = sorted({r.get("model_requested", model) for r in rs})
        for (c, a), s in cs.items():
            if label == "exploratory" and not s["n"]:
                continue
            ci = wilson(s["V_k"], s["n"]) if s["n"] else (None, None)
            rows.append([",".join(mname), c, a, s["n"], planned.get((c, a)) if label == "primary" else None,
                         s["V_k"], share(s), ci[0], ci[1], s["Vdoor_k"], s["Vdoor_n"], s["B_sum"],
                         s["B_sum"] / s["n"] if s["n"] else None, s["Bstop_sum"], s["Kstop_k"],
                         s["Bdeny_sum"], s["Kdeny_k"], s["E_k"], s["E_n"], s["hidden_k"], s["C_k"],
                         share(s, "C_k"), s["turns_mean"], s["output_tokens_mean"],
                         s["wall_s_mean"], s["killed"]])
            if label == "primary" and planned.get((c, a), 0) > s["n"]:
                shortfall.append("%s %s: %d of %d" % (c, a, s["n"], planned[(c, a)]))
    ctx.write_table("table12_e1_cells.csv", header, rows)

    for (c, a), s in cells.items():
        if not s["n"]:
            continue
        base = "e1.%s.%s" % (c, a)
        add_prop(reg, base + ".V", s["V_k"], s["n"], SRC, digits=0)
        if s["Vdoor_n"]:
            add_prop(reg, base + ".V_door", s["Vdoor_k"], s["Vdoor_n"], SRC, digits=0)
        add_prop(reg, base + ".C", s["C_k"], s["n"], SRC, digits=0)
        reg.add(base + ".B", s["B_sum"] / s["n"], "%s blocks in %s runs" % (s["B_sum"], s["n"]),
                SRC, k=s["B_sum"], n=s["n"], stat="mean blocks per run")
        if is_door_arm(a):
            add_prop(reg, base + ".E", s["E_k"], s["n"], SRC, digits=0)
            kn = s["Kstop_n"] + s["Kdeny_n"]
            kk = s["Kstop_k"] + s["Kdeny_k"]
            if kn:
                add_prop(reg, base + ".K", kk, kn, SRC, digits=0, unit="blocks")
            else:
                reg.add(base + ".K", None, "no block", SRC, k=0, n=0, unit="blocks")
        for f, d in (("turns", 1), ("output_tokens", 0), ("wall_s", 1)):
            if s[f + "_mean"] is not None:
                reg.add(base + "." + f, s[f + "_mean"], fmt_num(s[f + "_mean"], d), SRC,
                        stat="mean per run", n=s["n"])

    # Meta.
    add_count(reg, "e1.n_runs", len(primary), SRC, note="counted, non-voided runs on %s" % model)
    add_count(reg, "e1.n_void", len(voided), SRC)
    add_count(reg, "e1.n_cells", sum(1 for s in cells.values() if s["n"]), SRC)
    add_count(reg, "e1.n_exploratory_runs", len(explo), SRC)
    reported = sorted({r.get("model") for r in primary if r.get("model")})
    reg.add("e1.model_id", reported, (reported[0] if len(reported) == 1 else
            "more than one model id reported: " + ", ".join(reported)), SRC)
    clis = sorted({r.get("cli_version") for r in primary if r.get("cli_version")})
    reg.add("e1.cli_version", clis, clis[0] if len(clis) == 1 else ", ".join(clis), SRC)
    tws = sorted({r.get("trimwrit_commit") for r in primary if r.get("trimwrit_commit")})
    reg.add("e1.trimwrit_commit", tws, ", ".join(tws), SRC)
    ts = sorted(r["ts"] for r in primary if r.get("ts"))
    if ts:
        reg.add("e1.first_run_ts", ts[0], ts[0], SRC)
        reg.add("e1.last_run_ts", ts[-1], ts[-1], SRC)
    reg.add("e1.shortfall", shortfall, "none" if not shortfall else "; ".join(shortfall), SRC)
    add_count(reg, "e1.n_killed", sum(s["killed"] for s in cells.values()), SRC,
              note="runs stopped by the 30-minute wall cap")

    # Hypotheses: primary V, and the door detector's V beside it.
    hyp = judge(cells, cases_ok)
    sec = judge(cells, cases_ok, vkey="Vdoor_k", vn="Vdoor_n")
    doc = OrderedDict()
    doc["registered"] = "prereg/PREREG.md section 8, tag prereg-v1"
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
        doc[h] = entry
    doc["exploratory"] = exploratory(cells)
    (ctx.out).mkdir(parents=True, exist_ok=True)
    (ctx.out / "hypotheses.json").write_text(
        json.dumps(_round(doc), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    for h in ("H1", "H2", "H3", "H4"):
        d = hyp[h]
        key = {"H1": "e1.h1.diff", "H2": "e1.h2.diff", "H3": "e1.h3.diff", "H4": "e1.h4.diff"}[h]
        if "point" in d:
            reg.add(key, d["point"], fmt_diff(d["point"], d["interval"]), "results/hypotheses.json",
                    ci=d["interval"], ci_method="cluster bootstrap over cases, 95% percentile",
                    per_case=d["per_case"], text_short=fmt_num(d["point"]))
        reg.add("e1.%s.verdict" % h.lower(), d["verdict"], d["verdict"], "results/hypotheses.json")
    vad = hyp["H2"].get("v_ad", {})
    if "point" in vad:
        reg.add("e1.h2.v_ad", vad["point"], fmt_diff(vad["point"], vad["interval"]),
                "results/hypotheses.json", ci=vad["interval"],
                ci_method="cluster bootstrap over cases, 95% percentile",
                per_case=vad["per_case"], text_short=fmt_num(vad["point"]))
    for door in ("stop", "write"):
        p = hyp["H5"][door]
        if p["blocks"]:
            add_prop(reg, "e1.h5.%s.k" % door, p["k"], p["blocks"], "results/hypotheses.json",
                     digits=0, unit="blocks")
        else:
            reg.add("e1.h5.%s.k" % door, None, "no block", "results/hypotheses.json", k=0, n=0)
        reg.add("e1.h5.%s.verdict" % door, p["verdict"], p["verdict"], "results/hypotheses.json")
    reg.add("e1.h5.verdict", hyp["H5"]["verdict"], hyp["H5"]["verdict_text"],
            "results/hypotheses.json")

    figure(ctx, cases, cells)
    return doc


def exploratory(cells):
    """No criterion: escapes, detector-hidden violations, turns and tokens by arm."""
    out = OrderedDict()
    for (c, a), s in cells.items():
        if not s["n"] or not is_door_arm(a):
            continue
        out["%s %s" % (c, a)] = OrderedDict([
            ("escapes", "%d of %d" % (s["E_k"], s["n"])),
            ("escape_wilson", list(wilson(s["E_k"], s["n"]))),
            ("violations_the_door_detector_did_not_see", s["hidden_k"]),
            ("blocks", s["B_sum"]),
            ("turns_mean", s["turns_mean"]),
            ("output_tokens_mean", s["output_tokens_mean"]),
        ])
    return out


def _round(x):
    if isinstance(x, float):
        return round(x, 6)
    if isinstance(x, dict):
        return OrderedDict((k, _round(v)) for k, v in x.items())
    if isinstance(x, (list, tuple)):
        return [_round(v) for v in x]
    return x


def figure(ctx, cases, cells):
    plt = svg_setup()
    fig, axes = plt.subplots(1, len(cases), figsize=(2.4 * len(cases), 3.2), sharey=True)
    if len(cases) == 1:
        axes = [axes]
    for ax, (c, arms) in zip(axes, cases.items()):
        xs, ys, lo, hi = [], [], [], []
        for i, a in enumerate(arms):
            s = cells[(c, a)]
            if not s["n"]:
                continue
            p = s["V_k"] / s["n"]
            w = wilson(s["V_k"], s["n"])
            xs.append(i)
            ys.append(p)
            lo.append(max(0.0, p - w[0]))
            hi.append(max(0.0, w[1] - p))
        ax.errorbar(xs, ys, yerr=[lo, hi], fmt="o", color="black", capsize=3)
        ax.set_xticks(range(len(arms)))
        ax.set_xticklabels(arms, rotation=60, fontsize=7)
        ax.set_title(c, fontsize=9)
        ax.set_ylim(-0.05, 1.05)
        ax.grid(axis="y", linewidth=0.3)
    axes[0].set_ylabel("V, share of runs (Wilson 95%)")
    save_svg(plt, fig, ctx.figure_path("figure4_e1.svg"))


if __name__ == "__main__":
    sys.exit(standalone(run))
