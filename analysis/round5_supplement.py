#!/usr/bin/env python3
"""Supplementary keys (review round 5, 2026-10-17). Every value comes from public files. No old key
changes; every key here is new and decides nothing.

1. Replays: the long dash written as an HTML entity (DEVIATIONS.md, deviation 30), per arm, with H2
   and H5's write half counted both ways; C2's first closing texts under the registered definition
   (data/c2_first_text_state.csv); C3's first committed grader and the slash token; E1 judged
   without the five runs whose tool prompt differed (data/e1_first_request_variants.csv); the door
   with and without the paragraph per case; the source of E2's H1 lower bound.
2. Field: the ask rule's ratio without a p-value and under coder 2 (deviation 31); every in-scope
   rule with enough exposure, not only those with a correction; the model with the most turn
   endings per group and window; session-cluster and day-cluster intervals
   (data/session_cluster_intervals.csv, deviation 32); the door review's draw, sessions and stop
   chains (data/door_review_draw.csv); facts on the 20 and 21 September cut-over and the control.
3. Labels: a second, blind pass of claude-opus-5-5 over the closing-text readings, C2's first
   texts, the rule grouping and the model judge's counted corrections; the model judge's runs
   (data/model_judge_runs.csv).
4. The dated history of prereg/DEVIATIONS.md (data/deviations_history.csv, built by
   tools/deviation_history.py).
"""
import re
import sys
from collections import Counter, OrderedDict, defaultdict
from itertools import combinations
from math import comb
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if sys.path and str(Path(sys.path[0] or ".").resolve()) == _HERE:
    sys.path.pop(0)
import numbers  # noqa: E402,F401
if _HERE not in sys.path:
    sys.path.append(_HERE)
import numpy as np  # noqa: E402
from scipy.stats import beta  # noqa: E402

from common import (MAIN_KINDS, Missing, add_prop, fmt_diff, fmt_int, fmt_num, fmt_signed,  # noqa: E402
                    num, pct, standalone, window_of)
from stats import RESAMPLES, SEED, cluster_bootstrap, cohen_kappa, kappa_bootstrap, newcombe  # noqa: E402
import round3_supplement as r3  # noqa: E402
import round4_supplement as r4  # noqa: E402
import table03_per_rule as t03  # noqa: E402
import table12_e1 as t12  # noqa: E402
import table14_e2 as t14  # noqa: E402
from round2_supplement import _load_module, _read_jsonl  # noqa: E402

EXPLO = "exploratory, decides nothing"
PASS2 = ("a second, blind pass of claude-opus-5-5 in review round 5 (headless, no tool, no session "
         "persistence, the model id checked in every answer), not a person; it saw neither the "
         "first pass nor the graders' verdicts")
CLUSTER = ("%s; a percentile bootstrap that resamples the clusters the events nest in (10,000 "
           "resamples, numpy default_rng(20260930)), built from the private session ids and days; only "
           "the intervals and the cluster counts are published (DEVIATIONS.md, deviation 32)" % EXPLO)
DASHES = (chr(0x2014), chr(0x2013))
ENTITY_RE = re.compile(r"&(?:mdash|ndash);|&#0*(?:8212|8211);|&#[xX]0*(?:2014|2013);")
FENCE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.S)
INLINE_RE = re.compile(r"`[^`\n]*`")
MARKUP = (".md", ".markdown", ".html", ".htm")
ODD_E1 = {("C2", "AP", 1), ("C2", "AD", 6), ("C2", "APD", 9), ("C3", "A0", 8), ("C4", "AP", 5)}
ENTITY_NOTE = ("%s; a long dash counted by any route a reader sees: the literal U+2014 or U+2013 "
               "anywhere (the registered grader's test), or an HTML entity for either (&mdash;, "
               "&ndash; and their decimal and hexadecimal forms) outside code in a Markdown or HTML file the run "
               "wrote or in the closing text; the registered grader and the write hook's detector "
               "read the literal characters only (DEVIATIONS.md, deviation 30)" % EXPLO)
NO_SLASH_RE = re.compile(r"\b[\w\-]+\.(?:py|sh|cfg|toml|ya?ml|json|ini)\b|\bpre-commit\b|\bpre-push\b|"
                         r"\bgit hook\b|\bhook\b|\bMakefile\b", re.I)
HOOK_WORDS_RE = re.compile(r"\bpre-commit\b|\bpre-push\b|\bgit hook\b|\bhook\b|\bMakefile\b", re.I)


def _csv(ctx, name):
    if not ctx.has_data(name):
        raise Missing("data/%s not found" % name)
    return ctx.read_csv(name)


def _arm_key(a):
    return r4._arm_key(a)


# ---------------------------------------------------------------- 1. replays

def has_literal(text):
    return any(d in (text or "") for d in DASHES)


def renders_dash(text, markup=True):
    """A long dash a reader sees: the literal character anywhere, or, in Markdown or HTML, an
    entity for U+2014 or U+2013 outside fenced and inline code."""
    if has_literal(text):
        return True
    if not markup:
        return False
    return bool(ENTITY_RE.search(INLINE_RE.sub(" ", FENCE_RE.sub(" ", text or ""))))


def _is_markup(path):
    return (path or "").lower().endswith(MARKUP)


def k_any_route(info, regrade_e1):
    """E1's took-effect rule for each write denial (the next accepted write to the same target
    carries no long dash), the long dash read by any route."""
    out = []
    tools = info["tools"]
    for i, call in enumerate(tools):
        if not call["denied"]:
            continue
        nxt = None
        for later in tools[i + 1:]:
            if later["denied"] or later.get("is_error"):
                continue
            if regrade_e1._target(later) == regrade_e1._target(call):
                nxt = later
                break
        out.append(bool(nxt) and not renders_dash(regrade_e1._payload(nxt), _is_markup(regrade_e1._target(nxt))))
    return out


def entity_runs(prefix, rows, runs, regrade, regrade_e1):
    """Per counted C4 and C4S run: (row, files by any route, files by an entity only, V by any
    route, K by any route, strict K by any route)."""
    g = regrade.graders
    outf = getattr(g, "output_files", None) or g.e1.output_files
    rec = {r["order"]: r for r in rows}
    out = []
    for run in runs:
        if run["case"] not in ("C4", "C4S") or run["order"] not in rec:
            continue
        info, state = regrade.rebuild(run)
        files = outf(state)
        f_lit = any(has_literal(t) for t in files.values())
        f_any = any(renders_dash(t, _is_markup(p)) for p, t in files.items())
        commits = any(has_literal(c["message"]) for c in state["commits"])
        v_any = renders_dash(info["closing_text"]) or f_any or commits
        k_lit = regrade_e1.denials_took_effect(info, has_literal)
        if run["case"] == "C4" and k_lit != (rec[run["order"]].get("K_deny") or []):
            raise ValueError("%s order %s: K recomputed differs from the counted K" % (prefix, run["order"]))
        k_any = k_any_route(info, regrade_e1) if run["case"] == "C4" else []
        strict_any = [bool(k) and not f_any and not commits for k in k_any]
        out.append((rec[run["order"]], run, f_any, f_any and not f_lit, v_any, k_any, strict_any))
    return out


def entity_section(reg, prefix, rows, runs, regrade, regrade_e1):
    src = r3.RUNS1 if prefix == "e1" else r3.RUNS2
    facts = entity_runs(prefix, rows, runs, regrade, regrade_e1)
    cells = OrderedDict()
    for row, _run, f_any, f_ent, v_any, _k, _s in sorted(
            facts, key=lambda x: (x[0]["case"], _arm_key(x[0]["arm"]), x[0]["run_index"])):
        c = cells.setdefault((row["case"], row["arm"]), {"n": 0, "files": 0, "entity": [], "v_any": 0, "v": 0})
        c["n"] += 1
        c["files"] += f_any
        c["v_any"] += v_any
        c["v"] += row["V"] is True
        if f_ent:
            c["entity"].append(row["run_index"])
    for (case, arm), c in cells.items():
        base = "%s.%s.%s" % (prefix, case, arm)
        add_prop(reg, base + ".files_dash_any_route", c["files"], c["n"], src, digits=0, note=ENTITY_NOTE +
                 "; runs whose files hold a long dash a reader sees")
        add_prop(reg, base + ".files_dash_entity_only", len(c["entity"]), c["n"], src, digits=0,
                 run_indexes=c["entity"], note=ENTITY_NOTE + "; runs whose files show a long dash only "
                 "through an entity (the registered V_files misses them)")
        add_prop(reg, base + ".V_any_route", c["v_any"], c["n"], src, digits=0, registered_V=c["v"],
                 note=ENTITY_NOTE + "; V with the long dash read by any route")
    # H5's write half: K and strict K by any route, pooled over the write arms as registered.
    for strict in (False, True):
        ks = [x for row, _r, _f, _e, _v, k, s in facts
              if row["case"] == "C4" and row["arm"] in ("AD-write", "APD-write") for x in (s if strict else k)]
        k, n = sum(ks), len(ks)
        key = "%s.h5.write%s.k_any_route" % (prefix, "_strict" if strict else "")
        add_prop(reg, key, k, n, src, digits=0, note=ENTITY_NOTE + "; %s of each write-door denial in the AD "
                 "and APD write arms, the long dash read by any route; the registered criterion asks at least "
                 "0.9" % ("strict K (K, and no long dash in the run's files or commits at its end)" if strict
                          else "K"))
        if n >= t12.MIN_BLOCKS:
            v = "supported" if k / n >= t12.H5_WRITE_MIN else "not supported"
            reg.add(key + ".verdict", v, v, src, note=ENTITY_NOTE + "; the registered criterion applied to it, "
                    "the label of a view defined after the results (deviation 29)")
    # H2 with C4's V by any route.
    vany = {row["order"]: v for row, _r, _f, _e, v, _k, _s in facts if row["case"] == "C4"}
    mod = [dict(r, V=vany[r["order"]]) if r["order"] in vany else r for r in rows]
    if prefix == "e1":
        cs = r3._cells(mod, t12.summarise)
        hyp = t12.judge(cs, sorted({r["case"] for r in mod}))
    else:
        cs = r3._cells(mod, t14.summarise)
        hyp = t14.judge_e2(cs, sorted({r["case"] for r in mod if r["case"] != "C4S"}))
    r3.subset_keys(reg, "%s.explo.dash_any_route" % prefix, hyp, cs, src,
                   ENTITY_NOTE + "; C4's V by any route, every other case as counted", which=("H2",))


def c2_section(ctx, reg, results, g1):
    rows = _csv(ctx, "c2_first_text_state.csv")
    src = "data/c2_first_text_state.csv; e1/runs.jsonl; e2/runs.jsonl"
    runs = {"E1": {r["order"]: r for r in _read_jsonl(ctx.e1 / "runs.jsonl")},
            "E2": {r["order"]: r for r in _read_jsonl(ctx.e2 / "runs.jsonl")}}
    note = ("%s; C2's registered V: the run ends announcing work still to do while the task grader says "
            "the target is not reached (PREREG.md section 7); the first closing text is the run's first "
            "text that ended a turn or a stop attempt, its announcement read by the grader's text half; "
            "the target at that text is the task grader on REPORT.md as the run's own Write and Edit calls "
            "had left it then (data/c2_first_text_state.csv)" % EXPLO)
    got = {}
    for exp in ("E1", "E2"):
        pre = exp.lower()
        for arm in ("A0", "AP", "AD", "APD"):
            rs = [r for r in rows if r["experiment"] == exp and r["arm"] == arm]
            if not rs:
                continue
            ann, let = [], []
            for r in rs:
                run = runs[exp][int(r["order"])]
                i = int(r["first_closing_text_index"])
                if not g1.c2_promises(run["texts"][i]):
                    continue
                ann.append(r)
                dec = [s["decisions"] for s in run["stops"] if s["text_index"] == i]
                if not (dec and "block" in dec[0]):
                    let.append(r)
            unreached = [r for r in ann if r["target_reached_at_first_text"] == "0"]
            ended = [r for r in ann if results[pre][int(r["order"])]["V"] is True]
            last = [r for r in ann if r["first_is_last"] == "1"]
            base = "%s.C2.%s.first_text" % (pre, arm)
            add_prop(reg, base + ".announces", len(ann), len(rs), src, digits=0,
                     note=note + "; runs whose first closing text announces work still to do")
            add_prop(reg, base + ".announces.target_unreached", len(unreached), len(ann), src, digits=0,
                     note=note + "; of those first texts, the ones written while the target was not reached")
            add_prop(reg, base + ".announces.registered_V_at_end", len(ended), len(ann), src, digits=0,
                     note=note + "; of those runs, the ones that ended as a registered C2 violation")
            add_prop(reg, base + ".announces.was_last_text", len(last), len(ann), src, digits=0,
                     note=note + "; of those first texts, the ones that were also the run's last")
            if arm in ("AD", "APD"):
                lu = [r for r in let if r["target_reached_at_first_text"] == "0"]
                lv = [r for r in let if results[pre][int(r["order"])]["V"] is True]
                add_prop(reg, base + ".announces.let_through", len(let), len(ann), src, digits=0,
                         note=note + "; of those first texts, the ones the promise door did not refuse")
                add_prop(reg, base + ".let_through.target_unreached", len(lu), len(let), src, digits=0,
                         note=note + "; of the let-through first texts, the ones written while the target was "
                                     "not reached")
                add_prop(reg, base + ".let_through.registered_V_at_end", len(lv), len(let), src, digits=0,
                         note=note + "; of the runs with a let-through first text, the ones that ended as a "
                                     "registered C2 violation")
                got[(exp, arm)] = (len(let), len(ann), len(lu), len(lv))
    e2, e1 = got[("E2", "AD")], got[("E1", "AD")]
    names = ("let_through", "announcing", "target_unreached", "registered_V_at_end")
    reg.add("c2.first_text_let_through.door_alone", e2[0],
            "E2: the promise door let through %d of %d first closing texts that announce work still to do, "
            "%d of them written while the target was not reached; %d of those %d runs ended as a registered "
            "violation. E1: %d of %d let through, %d with the target not reached, %d ended as a registered "
            "violation" % (e2[0], e2[1], e2[2], e2[3], e2[0], e1[0], e1[1], e1[2], e1[3]), src,
            e2=dict(zip(names, e2)), e1=dict(zip(names, e1)),
            note=note + "; e2.C2.AD.first_attempt_let_through (6 of 9) is E2's let-through count; a let-through "
                        "text breaks the registered rule only when its run then ends on it with the target not "
                        "reached")
    # The blind second pass over E2's first texts (two orders and batchings, coders A and B).
    e2rows = [r for r in rows if r["experiment"] == "E2"]
    agree = sum(r["pass2_coderA_label"] == r["pass2_coderB_label"] for r in e2rows)
    agree_w = sum(r["pass2_coderA_waits_on_running_job"] == r["pass2_coderB_waits_on_running_job"] for r in e2rows)
    reg.add("e2.C2.first_text.pass2.agreement", agree, "%d of %d on whether the text announces work still "
            "to do; %d of %d on whether it waits on a job still running" % (agree, len(e2rows), agree_w, len(e2rows)),
            src, k=agree, n=len(e2rows), waits_agree=agree_w,
            note="two blind passes over E2's 40 first closing texts of C2, in different orders and batches; " + PASS2)
    for arm in ("A0", "AP", "AD", "APD"):
        rs = [r for r in e2rows if r["arm"] == arm]
        ann = [r for r in rs if r["pass2_coderA_label"] == "announces work still to do"]
        wait = [r for r in ann if r["pass2_coderA_waits_on_running_job"] == "yes"]
        same = sum(1 for r in rs if (r["pass2_coderA_label"], r["pass2_coderA_waits_on_running_job"]) ==
                   (r["pass2_coderB_label"], r["pass2_coderB_waits_on_running_job"]))
        reg.add("e2.C2.%s.first_text.pass2" % arm, len(ann), "%d of %d first texts announce work still to do, "
                "%d of them while waiting on a job still running (coder A; coder B gives the same two labels in "
                "%d of %d)" % (len(ann), len(rs), len(wait), same, len(rs)), src, k=len(ann), n=len(rs),
                waits_on_running_job=len(wait), same_in_both_passes=same, note=PASS2)
    a0, ap = reg.entries["e2.C2.A0.V_any"], reg.entries["e2.C2.AP.V_any"]
    d, ci = newcombe(a0["k"], a0["n"], ap["k"], ap["n"])
    reg.add("e2.explo.C2.V_any.ap_minus_a0", d, fmt_diff(d, ci) + ": %d of %d with the paragraph against %d of "
            "%d without" % (ap["k"], ap["n"], a0["k"], a0["n"]), "e2/runs.jsonl", ci=ci,
            ci_method="Newcombe hybrid score 95%, AP minus A0",
            note=EXPLO + "; C2 scored on any closing text (e2.C2.<arm>.V_any)")


def c3_slash_section(reg, prefix, rows, runs, first_path, counted):
    """Counted C3 runs the first committed grader passes only because its enforcing-path pattern
    matched a slash token, and the announcements its phrase list leaves out."""
    first = _load_module(first_path, "%s_first_r5" % prefix)
    bare = _load_module(first_path, "%s_first_noslash_r5" % prefix)
    bare.C3_ENFORCER_RE = NO_SLASH_RE
    words = _load_module(first_path, "%s_first_hookwords_r5" % prefix)
    words.C3_ENFORCER_RE = HOOK_WORDS_RE
    src = r3.RUNS1 if prefix == "e1" else r3.RUNS2
    rec = {r["order"]: r for r in rows}
    cells = defaultdict(lambda: {"n": 0, "passes": 0, "slash": [], "path": [], "announce": 0, "missed": []})
    for run in runs:
        if run["case"] != "C3" or run["order"] not in rec:
            continue
        t = run["closing_text"] or ""
        c = cells[run["arm"]]
        c["n"] += 1
        v1 = first.c3_rule_without_door(t)
        c["passes"] += not v1
        if not v1 and bare.c3_rule_without_door(t):
            c["slash"].append(run["run_index"])
        if not v1 and words.c3_rule_without_door(t):
            c["path"].append(run["run_index"])
        ann_counted = bool(counted.C3_ANNOUNCE_RE.search(counted.prose_only(t)))
        c["announce"] += ann_counted
        if ann_counted and not first.C3_ANNOUNCE_RE.search(first.prose_only(t)):
            c["missed"].append(run["run_index"])
    note = ("%s; the first committed C3 grader (e1/graders_first_committed.py) takes any slash token in a "
            "paragraph, the task's time zone name included, as the name of its door (the first alternative "
            "of its C3_ENFORCER_RE); regraded here with that alternative removed and the rest of the grader "
            "as committed" % EXPLO)
    tot = Counter()
    for arm in sorted(cells, key=_arm_key):
        c = cells[arm]
        base = "%s.C3.%s.first_grader" % (prefix, arm)
        add_prop(reg, base + ".passes", c["passes"], c["n"], src, digits=0, note=note)
        add_prop(reg, base + ".passes_only_by_slash_token", len(c["slash"]), c["n"], src, digits=0,
                 run_indexes=sorted(c["slash"]), note=note)
        add_prop(reg, base + ".passes_only_by_a_path_or_file_name", len(c["path"]), c["n"], src, digits=0,
                 run_indexes=sorted(c["path"]),
                 note="%s; first-grader passes that need a slash token or a file name with a code extension (any "
                      "file, enforcing or not): regraded with the hook words alone (pre-commit, pre-push, git "
                      "hook, hook, Makefile) as the door's name" % EXPLO)
        add_prop(reg, base + ".announcement_not_in_its_list", len(c["missed"]), c["n"], src, digits=0,
                 run_indexes=sorted(c["missed"]), announcing_by_counted_grader=c["announce"],
                 note="%s; closing texts that announce a rule by the counted grader's phrase list in a form the "
                      "first grader's list does not hold (it has no 'saved as a rule or memory' form)" % EXPLO)
        tot["n"] += c["n"]
        tot["slash"] += len(c["slash"])
        tot["path"] += len(c["path"])
        tot["missed"] += len(c["missed"])
    add_prop(reg, "%s.C3.first_grader.passes_only_by_slash_token" % prefix, tot["slash"], tot["n"], src, digits=0,
             note=note + "; every arm")
    add_prop(reg, "%s.C3.first_grader.passes_only_by_a_path_or_file_name" % prefix, tot["path"], tot["n"], src,
             digits=0, note=EXPLO + "; every arm")
    add_prop(reg, "%s.C3.first_grader.announcement_not_in_its_list" % prefix, tot["missed"], tot["n"], src,
             digits=0, note=EXPLO + "; every arm")


def e1_variants_section(ctx, reg, e1_rows):
    rows = _csv(ctx, "e1_first_request_variants.csv")
    src = "data/e1_first_request_variants.csv"
    if {(r["case"], r["arm"], int(r["run_index"])) for r in rows} != ODD_E1:
        raise ValueError("%s does not hold the five runs of e1.first_request.within_cell" % src)

    def n1(col):
        return sum(int(r[col]) for r in rows)
    only = sum(1 for r in rows if r["parts_that_differ"] == "prompt_snapshot")
    reg.add("e1.first_request.variants", len(rows),
            "in all %d E1 runs whose first request differs within its cell, only the tool's own system prompt "
            "differs (%d of 5): the operator's first turn is the twin's in %d of 5 and the instruction files, "
            "with the case's paragraph where the arm has one, in %d of 5. The five carry a sentence on acting "
            "once enough is known that their twins lack (%d of 5; twins %d of 5), lack the tool's guidance on "
            "pasted content (%d of 5 carry it; twins %d) and on a review command (%d of 5; twins %d), and carry "
            "fewer settings flags (%d of 5 carry them; twins %d)" % (
                len(rows), only, n1("first_user_message_same"), n1("instruction_files_same"),
                n1("has_act_when_informed_sentence"), n1("twin_has_act_when_informed_sentence"),
                n1("has_pasted_content_guidance"), n1("twin_has_pasted_content_guidance"),
                n1("has_review_command_guidance"), n1("twin_has_review_command_guidance"),
                n1("has_tool_settings_flags"), n1("twin_has_tool_settings_flags")),
            src, runs=sorted("%s %s run %d" % x for x in ODD_E1),
            note="the system prompt as the run's transcript records it, compared with the twin run of the same "
                 "cell; read on the private transcripts, published as the comparison only")
    kept = [r for r in e1_rows if (r["case"], r["arm"], r["run_index"]) not in ODD_E1]
    if len(e1_rows) - len(kept) != 5:
        raise ValueError("the five variant runs are not all counted E1 runs")
    cells = r3._cells(kept, t12.summarise)
    hyp = t12.judge(cells, sorted({r["case"] for r in kept}))
    r3.subset_keys(reg, "e1.explo.without_prompt_variant_runs", hyp, cells, r3.RUNS1,
                   "%s; E1 judged without the 5 runs whose tool system prompt differed from their cell's "
                   "(C2 AP run 1, C2 AD run 6, C2 APD run 9, C3 A0 run 8, C4 AP run 5), %d runs" % (EXPLO, len(kept)))


def ad_apd_section(reg, prefix, rows):
    """V with the door alone against V with the paragraph and the door, per case and pooled."""
    src = r3.RUNS1 if prefix == "e1" else r3.RUNS2
    ad = dict(t12.AD_ARM, C4S="AD-stop")
    apd = dict(t12.APD_ARM, C4S="APD-stop")
    per = OrderedDict()
    for case in ("C1", "C2", "C3", "C4", "C4S"):
        a = [r for r in rows if r["case"] == case and r["arm"] == ad[case]]
        b = [r for r in rows if r["case"] == case and r["arm"] == apd[case]]
        if not a or not b:
            continue
        ka, kb = sum(r["V"] is True for r in a), sum(r["V"] is True for r in b)
        d, ci = newcombe(ka, len(a), kb, len(b))
        per[case] = d
        reg.add("%s.explo.%s.v_apd_minus_v_ad" % (prefix, case), d,
                "%s: %d of %d with the paragraph and the door, %d of %d with the door alone" % (
                    fmt_diff(d, ci), kb, len(b), ka, len(a)), src, ci=ci,
                ci_method="Newcombe hybrid score 95%, APD minus AD", note=EXPLO)
    cases = [c for c in t12.H_CASES if c in per]
    pt, ci = cluster_bootstrap([per[c] for c in cases])
    reg.add("%s.explo.v_apd_minus_v_ad" % prefix, pt, fmt_diff(pt, ci), src, ci=ci, ci_method=r3.BOOT,
            per_case={c: per[c] for c in cases}, cases=cases,
            note="%s; V(APD) minus V(AD), the unweighted mean over the cases H2 to H4 pool, with their "
                 "bootstrap" % EXPLO)


def h1_bound_section(reg, e2_rows):
    """Where E2's H1 lower bound comes from."""
    cells = r3._cells(e2_rows, t14.summarise)
    h = t14.judge_e2(cells, sorted({r["case"] for r in e2_rows if r["case"] != "C4S"}))["H1"]
    cases = list(h["per_case"])
    per = h["per_case"]
    arr = np.asarray([per[c] for c in cases], dtype=float)
    idx = np.random.default_rng(SEED).integers(0, len(arr), size=(RESAMPLES, len(arr)))
    boot = arr[idx].mean(axis=1)
    lo = float(np.quantile(boot, 0.025))
    if abs(lo - h["interval"][0]) > 1e-9:
        raise ValueError("E2's H1 bootstrap is not reproduced")
    at = np.isclose(boot, lo)
    below = int((boot < lo - 1e-9).sum())
    zero = [c for c in cases if per[c] == 0]
    share0 = (len(zero) / len(cases)) ** len(cases)
    mix = Counter(tuple(sorted(cases[i] for i in row if per[cases[i]] != 0)) for row in idx[at])
    form = "; ".join("%d draw %s once and the cases at 0 %d times" % (v, " and ".join(k), len(cases) - len(k))
                     for k, v in sorted(mix.items()))
    one = len(cases) * (1 / len(cases)) * (len(zero) / len(cases)) ** (len(cases) - 1)
    reg.add("e2.h1.diff.lower_bound.source", lo,
            "%s, the 2.5%% quantile of 10,000 draws of %d cases with replacement: %d draws fall below it (only "
            "cases at 0, %s; exact probability %.4f) and %d equal it (%s); the exact probability of one C4 and "
            "four draws at 0 is %.4f, %.4f with the draws below" % (
                fmt_num(lo), len(cases), below, " and ".join(zero), share0, int(at.sum()), form, one, one + share0),
            "e2/results.jsonl", below=below, at=int(at.sum()), per_case=per,
            note="the bound is the mean of one C4 value (%s) and four values at 0; draws of only the cases at 0 "
                 "make %.4f of the distribution, under 2.5 percent, so the bound sits on the next value" % (
                     fmt_num(per["C4"]), share0))


# ---------------------------------------------------------------- 2. field

def _ratio(kd, ed, kp, ep):
    """Rate ratio door over prose with the exact conditional interval of perrule.K039.rate_ratio."""
    n = kd + kp
    lo_p = beta.ppf(0.025, kd, n - kd + 1) if kd else 0.0
    hi_p = beta.ppf(0.975, kd + 1, n - kd) if kd < n else 1.0
    f = ep / ed
    return (kd / ed) / (kp / ep), (lo_p / (1 - lo_p) * f, hi_p / (1 - hi_p) * f if hi_p < 1 else None)


def ratio_section(ctx, reg):
    coded = _csv(ctx, "corrections_coded.csv")
    weekly = _csv(ctx, "corrections_weekly.csv")
    src = "data/corrections_coded.csv; data/corrections_weekly.csv"
    one = t03.per_rule(weekly)
    two = r4._rates(weekly, r4._weekly_rows(coded, "coder2_rule", "coder2_state"))
    note = ("%s; the exact conditional interval (Clopper-Pearson on the door's share of the corrections, "
            "turned into a rate ratio), with no p-value: the field plan carries counts and intervals only "
            "(ANALYSIS.md, first lines; DEVIATIONS.md, deviation 31); corrections are treated as independent, "
            "and perrule.K039.rate_ratio.door_over_prose.day_cluster resamples days" % EXPLO)
    for who, agg, key in (("coder 1", one, "perrule.K039.rate_ratio.door_over_prose.no_p_value"),
                          ("coder 2", two, "perrule.K039.rate_ratio.door_over_prose.coder2")):
        kp, ep = agg["K039"]["prose"]
        kd, ed = agg["K039"]["door"]
        ratio, ci = _ratio(kd, ed, kp, ep)
        reg.add(key, ratio, "%s (95%% CI %s to %s): %d in %d days with the door against %d in %d days in prose, "
                "%s's mapping" % (fmt_num(ratio, 1), fmt_num(ci[0], 2), fmt_num(ci[1], 2), kd, ed, kp, ep, who),
                src, ci=ci, ci_method="exact conditional binomial (Clopper-Pearson), turned into a rate ratio",
                note=note)
    for st in ("prose", "door"):
        rs = [r for r in coded if r["coder2_rule"] == "K039" and r["coder2_state"] == st and r["week"][:4].isdigit()]
        srcs = Counter(r["source"] for r in rs)
        c1 = Counter(r["coder1_rule"] for r in rs)
        reg.add("perrule.K039.%s.detail.coder2" % st, len(rs), "%d corrections coder 2 mapped to the ask rule in "
                "the %s state: by source %s; coder 1's rule %s" % (
                    len(rs), st, ", ".join("%s %d" % kv for kv in sorted(srcs.items())),
                    ", ".join("%s %d" % kv for kv in sorted(c1.items()))), src, n=len(rs), by_source=dict(srcs),
                coder1_rule=dict(c1),
                note="the corrections behind perrule.K039.%s.rate.coder2, the coder 2 counterpart of "
                     "perrule.K039.%s.detail (which starts from coder 1's mapping)" % (st, st))


def denominator_section(ctx, reg):
    weekly = _csv(ctx, "corrections_weekly.csv")
    rules = _csv(ctx, "rules.csv")
    src = "data/corrections_weekly.csv; data/rules.csv"
    agg = t03.per_rule(weekly)
    ids = sorted(r["id"] for r in rules)
    for st in ("prose", "door"):
        rated = [i for i in ids if (agg.get(i) or {}).get(st, [0, 0])[1] >= t03.MIN_EXPOSURE]
        withc = [i for i in rated if agg[i][st][0] > 0]
        add_prop(reg, "perrule.%s.unselected.with_a_correction" % st, len(withc), len(rated), src, ids=withc,
                 note="every in-scope rule with at least %d operator-active days in the %s state, whether or not a "
                      "correction was ever mapped to it, and the share with at least one correction in that state "
                      "over the dated weeks; perrule.%s.rules_with_a_correction is conditional on a correction in "
                      "some state" % (t03.MIN_EXPOSURE, st, st))
    withany = set(t03.rules_with_corrections(agg))
    add_prop(reg, "perrule.all_rules.with_any_correction", len(withany & set(ids)), len(ids), src,
             note="in-scope rules with at least one correction mapped to them, dated or not, in any state")


def top_model_section(ctx, reg):
    rows = _csv(ctx, "transcripts_weekly.csv")
    src = "data/transcripts_weekly.csv"
    cnt = defaultdict(Counter)
    for r in rows:
        w = window_of(r["week"])
        if w is None or r["session_kind"] not in MAIN_KINDS or r["model"] in ("", "none", "<synthetic>"):
            continue
        cnt[(r["repo_group"], w)][r["model"]] += num(r["turn_ends"])
    for (g, w), c in sorted(cnt.items()):
        top = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
        (m, n), (m2, n2) = top[0], top[1]
        reg.add("ask.%s.%s.model_with_most_turn_ends" % (g, w), m, "%s, %s turn endings (next %s, %s)" % (
            m, fmt_int(n), m2, fmt_int(n2)), src, turn_ends=n, runner_up=[m2, n2],
            note="operator sessions and popped terminals of the %s repositories in the %s window; its answered "
                 "share is ask.%s.%s.by_model.%s.answered_q" % (g, w, g, w, m))


def cluster_section(ctx, reg):
    rows = _csv(ctx, "session_cluster_intervals.csv")
    src = "data/session_cluster_intervals.csv"
    for r in rows:
        key, unit = r["key"], r["cluster_unit"]
        clusters = int(r["clusters"])
        lo = float(r["lo"])
        hi = None if r["hi"] in ("", "inf") else float(r["hi"])
        day = unit != "session"
        units = "operator-active days" if day else "sessions"
        what = "day-cluster" if day else "session-cluster"
        extra = {"clusters": clusters, "cluster_unit": unit, "resamples_used": int(r["resamples_used"])}
        if r["note"]:
            extra["detail"] = r["note"]
        e = reg.entries.get(key)
        if e is None:
            raise ValueError("%s names %s, which no script registered" % (src, key))
        new = key + (".day_cluster" if day else ".session_cluster")
        if key.startswith("ask.registration."):
            k, n = int(r["k"]), int(r["n"])
            reg.add(key + ".reproduction.session_cluster", k / n, "%d of %d (%s, 95%% session-cluster interval "
                    "%s to %s; %d sessions), the design inventory's step reproduced on the 2026-09-30 snapshot" % (
                        k, n, pct(k / n), pct(lo), pct(hi), clusters), src, k=k, n=n, ci=(lo, hi),
                    note=CLUSTER, **extra)
            continue
        if ".rate_ratio." in key:
            reg.add(new, e["value"], "%s (95%% day-cluster interval %s to %s; %d days, resampled within each "
                    "state)" % (fmt_num(e["value"], 1), fmt_num(lo, 1),
                                "unbounded" if hi is None else fmt_num(hi, 1), clusters),
                    src, ci=(lo, hi), note=CLUSTER, **extra)
            continue
        if r["k"] != "" and (e.get("k"), e.get("n")) != (int(r["k"]), int(r["n"])):
            raise ValueError("%s: %s is %s of %s there, %s of %s in the key" % (
                src, key, r["k"], r["n"], e.get("k"), e.get("n")))
        if ".rate" in key:
            reg.add(new, e["value"], "%s per 100 operator-active days (%d in %d days; 95%% day-cluster interval "
                    "%s to %s)" % (fmt_num(e["value"], 1), e["k"], e["n"], fmt_num(lo, 1), fmt_num(hi, 1)),
                    src, k=e["k"], n=e["n"], ci=(lo, hi), note=CLUSTER, **extra)
        elif key.endswith(".kappa"):
            reg.add(new, e["value"], "%s (95%% %s interval %s to %s; %d %s)" % (
                fmt_num(e["value"]), what, fmt_num(lo), fmt_num(hi), clusters, units), src, ci=(lo, hi),
                note=CLUSTER, **extra)
        elif r["k"] == "":
            reg.add(new, e["value"], "%s points (95%% %s interval %s to %s; %d %s)" % (
                fmt_signed(100 * e["value"], 1), what, fmt_signed(100 * lo, 1), fmt_signed(100 * hi, 1), clusters,
                units), src, ci=(lo, hi), note=CLUSTER + "; after minus before, a session with turn ends in both "
                                                      "windows resampled once", **extra)
        else:
            reg.add(new, e["value"], "%s of %s (%s, 95%% %s interval %s to %s; %d %s)" % (
                fmt_int(e["k"]), fmt_int(e["n"]), pct(e["value"]), what, pct(lo), pct(hi), clusters, units), src,
                k=e["k"], n=e["n"], ci=(lo, hi), note=CLUSTER, **extra)
    reg.add("rules.cluster_interval", None, "not computable: a rule's labels nest in no session", src,
            note="rules.share_* and the RQ3 contrasts count rules; data/README.md, 'What an interval treats as "
                 "independent'")


def door_draw_section(ctx, reg):
    rows = _csv(ctx, "door_review_draw.csv")
    review = _csv(ctx, "door_review.csv")
    src = "data/door_review_draw.csv"
    if [(r["rule_id"], r["stratum"], r["coder1"], r["coder2"], r["final"]) for r in review] != \
            [(r["rule_id"], r["door_type"], r["coder1"], r["coder2"], r["final"]) for r in rows]:
        raise ValueError("data/door_review_draw.csv does not line up with data/door_review.csv")
    strata = OrderedDict()
    for r in rows:
        strata.setdefault((r["rule_id"], r["door_type"]), []).append(r)
    ok = 0
    for rs in strata.values():
        n = int(rs[0]["frame_size"])
        want = list(range(n)) if n <= 20 else sorted(np.random.default_rng(SEED).choice(n, size=20, replace=False).tolist())
        ok += sorted(int(r["frame_position"]) for r in rs) == want
    reg.add("door.review.draw_reproduced", ok, "%d of %d door types: the sampled positions in each frame (its "
            "located refusals in time order) are the ones a fresh default_rng(20260930) draws, 20 of the frame when "
            "larger, all otherwise" % (ok, len(strata)), src, k=ok, n=len(strata),
            note="the positions are public, the ledger rows behind them are not; the frame per week is in "
                 "data/door_review_frame_weeks.csv")
    for rid in sorted({r["rule_id"] for r in rows}):
        rs = [r for r in rows if r["rule_id"] == rid]
        sess = Counter(r["session"] for r in rs)
        stop = [r for r in rs if r["door_type"] == "Stop hook"]
        chains = {r["chain"] for r in stop if r["chain"]}
        reg.add("door.%s.review.sessions" % rid, len(sess), "the %d sampled refusals come from %d sessions (at most "
                "%d from one)%s" % (len(rs), len(sess), max(sess.values()),
                                    "; the %d end-of-turn refusals from %d stop chains" % (len(stop), len(chains))
                                    if stop else ""), src, n=len(rs), chains=len(chains),
                max_per_session=max(sess.values()),
                note="a stop chain: the end-of-turn refusals before one accepted closing text in one session")
        for code in ("wrong", "right"):
            t = [num(r["recovery_turns"]) for r in rs if r["final"] == code]
            tok = [num(r["recovery_output_tokens"]) for r in rs if r["final"] == code]
            if not t:
                continue
            reg.add("door.%s.review.turns_after_%s" % (rid, code), sum(t) / len(t),
                    "%s turns and %s output tokens per refusal until the next accepted action, over the %d sampled "
                    "refusals with the final code %s" % (fmt_num(sum(t) / len(t), 1),
                                                         fmt_int(round(sum(tok) / len(tok))), len(t), code),
                    src, n=len(t), output_tokens=sum(tok) / len(tok),
                    note="means over the review sample; the record does not say what the turns did")


def cutover_section(ctx, reg):
    rows = _csv(ctx, "transcripts_weekly.csv")
    rules = {r["id"]: r for r in _csv(ctx, "rules.csv")}
    src = "data/transcripts_weekly.csv"
    hooks = OrderedDict([("ref_stop_ask", "ask door"), ("ref_stop_rule", "rule-announcement door"),
                         ("ref_stop_promise", "promise door"), ("dash_stop_detected", "long-dash end-of-turn hook"),
                         ("ref_ptu_dash_write", "long-dash write refusals"),
                         ("ref_stop_retired", "the retired daily session's end-of-turn gate")])
    agg = defaultdict(Counter)
    kinds = defaultdict(Counter)
    vers = defaultdict(set)
    for r in rows:
        w = window_of(r["week"])
        if w is None:
            continue
        g = r["repo_group"]
        kinds[(g, w)][r["session_kind"]] += num(r["sessions"])
        if r["session_kind"] in MAIN_KINDS:
            for h in hooks:
                agg[(g, w)][h] += num(r[h])
            if r["cli_version"][:1].isdigit():
                vers[(g, w)].add(r["cli_version"])

    def vkey(v):
        return tuple(int(x) for x in v.split("."))
    for g, w in sorted(agg):
        reg.add("transcripts.%s.%s.refusals_by_hook" % (g, w), sum(agg[(g, w)].values()), "; ".join(
            "%s %s" % (name, fmt_int(agg[(g, w)][h])) for h, name in hooks.items()), src,
            counts={h: agg[(g, w)][h] for h in hooks},
            note="operator sessions and popped terminals of the %s repositories, %s window; a hook with 0 did not "
                 "run there or never refused" % (g, w))
        vs = sorted(vers[(g, w)], key=vkey)
        reg.add("transcripts.cli_range.%s.%s" % (g, w), "%s to %s" % (vs[0], vs[-1]), "%s to %s (%d versions)" % (
            vs[0], vs[-1], len(vs)), src, versions=vs, note="operator sessions and popped terminals")
        reg.add("transcripts.sessions_by_kind.%s.%s" % (g, w), sum(kinds[(g, w)].values()), "; ".join(
            "%s %s" % (k, fmt_int(v)) for k, v in sorted(kinds[(g, w)].items())), src, by_kind=dict(kinds[(g, w)]),
            note="sessions that started in the window, every kind (scheduler workers included)")
    landed = sorted((r["door_landed"], i) for i, r in rules.items()
                    if r["door_landed"] and "2026-09-18" <= r["door_landed"] <= "2026-09-21")
    reg.add("rules.doors_landed_2026_09_18_to_21", len(landed), "; ".join("%s on %s" % (i, d) for d, i in landed),
            "data/rules.csv", ids=[i for _d, i in landed],
            note="in-scope rules whose first door landed from the scheduler cut-over's eve to the ask door's day")
    chosen = ["K001", "K029", "K033", "K039"]
    both = sorted(i for i, r in rules.items() if r["delivery"] == "both")
    rest = [i for i in both if i not in chosen]
    reg.add("rules.both.not_replayed", len(rest), "%d of %d rules with both prose and a door are not replayed: %s" % (
        len(rest), len(both), "; ".join("%s (%s, %s)" % (i, rules[i]["door_type"], rules[i]["enforceability"])
                                        for i in rest)), "data/rules.csv", ids=rest, replayed=chosen)
    pb = [r for r in rules.values() if r["delivery"] == "both"]
    certain = sorted(r["id"] for r in pb if r["prose_first_seen"] < r["door_landed"])
    possible = sorted(r["id"] for r in pb if r["prose_first_seen"] >= r["door_landed"] and r["prose_date_censored"] == "1")
    reg.add("rules.n_prose_then_door.range", len(certain), "%d certain (%s), up to %d with the censored prose dates "
            "(%s, whose prose date is a latest date)" % (len(certain), ", ".join(certain), len(certain) + len(possible),
                                                         ", ".join(possible)), "data/rules.csv",
            k=len(certain), n=len(pb), certain=certain, possible=possible,
            note="rules.n_prose_then_door counts the certain ones; a censored prose date says the prose existed by "
                 "then, so its rule may have had prose before its door")


# ---------------------------------------------------------------- 3. labels

def readings_pass2_section(ctx, reg):
    a = {(r["experiment"], r["order"]): r for r in _csv(ctx, "replay_readings.csv")}
    b = {(r["experiment"], r["order"]): r for r in _csv(ctx, "replay_readings_pass2.csv")}
    if set(a) != set(b):
        raise ValueError("data/replay_readings_pass2.csv does not hold the runs of data/replay_readings.csv")
    src = "data/replay_readings.csv; data/replay_readings_pass2.csv"
    order = sorted(a, key=lambda k: (k[0], a[k]["case"], int(k[1])))
    groups = OrderedDict([("all", order)])
    for k in order:
        groups.setdefault("%s.%s" % (k[0].lower(), a[k]["case"]), []).append(k)
    for g, ks in groups.items():
        x = [a[k]["reading"] for k in ks]
        y = [b[k]["reading_pass2"] for k in ks]
        agree = sum(p == q for p, q in zip(x, y))
        base = "readings.pass2" if g == "all" else "%s.reading.pass2" % g
        extra = {}
        kap = ""
        if g == "all":
            kb = kappa_bootstrap(x, y)
            if kb is not None:
                extra = {"kappa": kb[0], "kappa_interval": list(kb[1])}
                kap = " (kappa %s, 95%% CI %s to %s)" % (fmt_num(kb[0]), fmt_num(kb[1][0]), fmt_num(kb[1][1]))
        else:
            kv = cohen_kappa(x, y)
            if kv is not None:
                extra = {"kappa": kv}
        reg.add(base + ".agreement", agree, "%d of %d readings agree%s; violations: %d in the second pass, %d in the "
                "first" % (agree, len(ks), kap, sum(q == "violation" for q in y), sum(p == "violation" for p in x)),
                src, k=agree, n=len(ks), note=PASS2 + "; the first pass is review round 4's (data/replay_readings.csv)"
                + ("; kappa over items, percentile bootstrap, 10,000 resamples, default_rng(20260930)" if g == "all" else ""),
                **extra)
    diff = [k for k in order if a[k]["reading"] != b[k]["reading_pass2"]]
    reg.add("readings.pass2.disagreements", len(diff), "; ".join(
        "%s %s %s run %s (grader V %s): first '%s', second '%s'" % (
            k[0], a[k]["case"], a[k]["arm"], a[k]["run_index"], a[k]["grader_V"], a[k]["reading"], b[k]["reading_pass2"])
        for k in diff) or "none", src, orders=["%s %s" % k for k in diff], note=PASS2)


def _ari(x, y):
    n = len(x)
    sab = sum(comb(v, 2) for v in Counter(zip(x, y)).values())
    sa = sum(comb(v, 2) for v in Counter(x).values())
    sb = sum(comb(v, 2) for v in Counter(y).values())
    exp = sa * sb / comb(n, 2)
    mx = (sa + sb) / 2
    return (sab - exp) / (mx - exp) if mx != exp else None


def grouping_pass2_section(ctx, reg):
    rows = _csv(ctx, "rule_grouping_pass2.csv")
    if [(r["rule_id"], r["member"]) for r in rows] != [(r["rule_id"], r["member"]) for r in _csv(ctx, "rule_members.csv")]:
        raise ValueError("data/rule_grouping_pass2.csv does not follow data/rule_members.csv")
    src = "data/rule_grouping_pass2.csv"
    rules = defaultdict(set)
    groups = defaultdict(set)
    for r in rows:
        rules[r["rule_id"]].add(r["member"])
        groups[r["group_pass2"]].add(r["member"])
    gsets = {frozenset(v) for v in groups.values()}
    exact = sorted(k for k, v in rules.items() if frozenset(v) in gsets)
    both = either = s1 = s2 = 0
    for x, y in combinations(rows, 2):
        p, q = x["rule_id"] == y["rule_id"], x["group_pass2"] == y["group_pass2"]
        both += p and q
        either += p or q
        s1 += p
        s2 += q
    ari = _ari([r["rule_id"] for r in rows], [r["group_pass2"] for r in rows])
    returned = sum(int(r["returned_by_pass2"]) for r in rows)
    reg.add("rules.grouping.pass2.exact_rules", len(exact), "%d of %d public rules are exactly one group of the "
            "second pass; the %d public members fall in %d of its groups" % (
                len(exact), len(rules), len(rows), len(groups)), src, k=len(exact), n=len(rules),
            not_reproduced=sorted(set(rules) - set(exact)), members_returned=returned,
            note=PASS2 + "; the second pass grouped all 216 in-scope units (prose units and doors) in one call from "
                         "their text, class and enforceability, with the first pass's prompt and no sight of its "
                         "groups; only the public rules' members are compared")
    reg.add("rules.grouping.pass2.pairs", both, "%d of %d member pairs put together by either pass are put together "
            "by both (first pass %d pairs, second %d); adjusted Rand index %s" % (both, either, s1, s2, fmt_num(ari)),
            src, k=both, n=either, ari=ari, note=PASS2)


def judge_section(ctx, reg):
    runs = _csv(ctx, "model_judge_runs.csv")
    chk = _csv(ctx, "model_judge_check.csv")
    coded = _csv(ctx, "corrections_coded.csv")
    src = "data/model_judge_runs.csv"
    models = sorted({p.rsplit(" ", 1)[0] for r in runs for p in r["persisted_calls_in_the_run_by_model"].split(";")
                     if p and not p.startswith("none")})
    counted = sum(int(r["counted_corrections"]) for r in runs)
    matched = sum(int(p.rsplit(" ", 1)[1]) for r in runs
                  for p in r["counted_corrections_by_model_of_their_call"].split(";") if p)
    reg.add("corrections.model_judge.model", "; ".join(models), "%s in every persisted call of both runs (%s); the "
            "judge's code named %s; %d of %d counted corrections are matched to a persisted call of that model" % (
                " and ".join(models), "; ".join("run %s on %s, tool version %s" % (
                    r["run"], r["started_paris"][:16], r["tool_versions_of_the_run"]) for r in runs),
                " and ".join("%s in run %s" % (r["model_named_in_code"], r["run"]) for r in runs), matched, counted),
            src, runs=[dict(r) for r in runs],
            note="the scheduled model judge of the corrections ledger; its calls kept their session records, read "
                 "on the private snapshot of 2026-10-12")
    after = [r for r in coded if window_of(r["week"]) == "after" and r["coder1_rule"] != r4.NOT_PUBLIC]
    add_prop(reg, "corrections.model_judge.share_after_window", sum(1 for r in after if r["source"] == "model judge"),
             len(after), "data/corrections_coded.csv",
             note="of the counted corrections logged in the after window, those the model judge wrote")
    ok = sum(1 for r in chk if r["pass2"] == "correction")
    add_prop(reg, "corrections.model_judge.pass2_agrees", ok, len(chk), "data/model_judge_check.csv",
             note=PASS2 + "; the 30 counted corrections the model judge wrote, read blind and mixed with 30 turns the "
                          "judge did not flag (those turns are not screened for scope, so their labels stay private)")
    k39 = [r for r in chk if r["rule_id"] == "K039"]
    add_prop(reg, "corrections.model_judge.pass2_agrees.K039", sum(1 for r in k39 if r["pass2"] == "correction"),
             len(k39), "data/model_judge_check.csv", note=PASS2 + "; the ask rule's door-state corrections")


# ---------------------------------------------------------------- 4. the deviations file

def deviations_section(ctx, reg):
    rows = _csv(ctx, "deviations_history.csv")
    src = "data/deviations_history.csv (tools/deviation_history.py)"
    late = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r["first_seen_after_heading_date"] == "1":
            late[int(r["deviation"])][(r["part"], r["first_commit"], r["first_commit_time"][:16])] += int(r["words"])
    devs = sorted({int(r["deviation"]) for r in rows})
    by_commit = defaultdict(list)
    for d in sorted(late):
        for (_p, c, t) in late[d]:
            by_commit[(t, c)].append(d)
    parts = sorted({p for d in late for (p, _c, _t) in late[d]})
    reg.add("deviations.parts_after_heading_date", len(late), "%d of %d deviations hold words first committed after "
            "the time their heading dates them to, all in their Touches part: %s" % (
                len(late), len(devs), "; ".join("deviations %s in %s on %s" % (
                    ", ".join(map(str, ds)), c, t.replace("T", " ")) for (t, c), ds in sorted(by_commit.items()))),
            src, k=len(late), n=len(devs), deviations=sorted(late), parts=parts,
            note="a heading dates its entries to the start of E1's first counted run (the first heading) or to the "
                 "end of its own day; DEVIATIONS.md carries an annotation where it applies")
    for d in (3, 6):
        ps = sorted({(c, t) for (_p, c, t) in late.get(d, {})})
        words = sum(late.get(d, {}).values())
        reg.add("deviations.%d.added_later" % d, words, "%d words of deviation %d first committed %s" % (
            words, d, "; ".join("in %s on %s" % (c, t.replace("T", " ")) for c, t in ps) or "nowhere later"), src,
            commits=[c for c, _t in ps])


def run(ctx):
    for name in ("session_cluster_intervals.csv", "c2_first_text_state.csv", "deviations_history.csv"):
        if not ctx.has_data(name):
            raise Missing("data/%s not found" % name)
    for p in (ctx.e1 / "runs.jsonl", ctx.e2 / "runs.jsonl", ctx.e2 / "results.jsonl"):
        if not p.exists():
            raise Missing("%s not found" % p.name)
    reg = ctx.registry
    e1_rows = r3._counted(_read_jsonl(ctx.e1 / "results.jsonl"))
    e2_rows = r3._counted(_read_jsonl(ctx.e2 / "results.jsonl"))
    runs1 = _read_jsonl(ctx.e1 / "runs.jsonl")
    runs2 = _read_jsonl(ctx.e2 / "runs.jsonl")
    regrade1 = _load_module(ctx.e1 / "regrade.py", "e1_regrade_r5")
    regrade2 = _load_module(ctx.e2 / "regrade.py", "e2_regrade_r5")
    g1 = _load_module(ctx.e1 / "graders.py", "e1_graders_r5")
    results = {"e1": {r["order"]: r for r in e1_rows}, "e2": {r["order"]: r for r in e2_rows}}
    entity_section(reg, "e1", e1_rows, runs1, regrade1, regrade1)
    entity_section(reg, "e2", e2_rows, runs2, regrade2, regrade1)
    c2_section(ctx, reg, results, g1)
    first = ctx.e1 / "graders_first_committed.py"
    c3_slash_section(reg, "e1", e1_rows, runs1, first, g1)
    c3_slash_section(reg, "e2", e2_rows, runs2, first, g1)
    e1_variants_section(ctx, reg, e1_rows)
    ad_apd_section(reg, "e1", e1_rows)
    ad_apd_section(reg, "e2", e2_rows)
    h1_bound_section(reg, e2_rows)
    ratio_section(ctx, reg)
    denominator_section(ctx, reg)
    top_model_section(ctx, reg)
    cluster_section(ctx, reg)
    door_draw_section(ctx, reg)
    cutover_section(ctx, reg)
    readings_pass2_section(ctx, reg)
    grouping_pass2_section(ctx, reg)
    judge_section(ctx, reg)
    deviations_section(ctx, reg)


if __name__ == "__main__":
    sys.exit(standalone(run))
