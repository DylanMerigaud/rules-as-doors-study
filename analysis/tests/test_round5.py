"""Review round 5 (analysis/round5_supplement.py, tools/deviation_history.py and the files they
read). Each test would have caught one error a round 5 review found in the package: long dashes
written as HTML entities that no grader counted, a p-value in a field plan that forbids them, a
model named in a table cell that was not the one with the most turn endings, intervals that
treated nested events as independent with no way to check the draw, deviations dated by a heading
written before their later parts, labels from a single model pass, the model judge left unnamed,
rule descriptions beyond the domain sentence, a citation title that was not the paper's, a first C3
grader that took any slash token for a door, and a per-rule claim read only on rules selected by their
outcome."""
import csv
import importlib.util
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
from common import MAIN_KINDS, window_of  # noqa: E402

NUMBERS = json.loads((ROOT / "results" / "numbers.json").read_text(encoding="utf-8"))
ENTITY = re.compile(r"&(?:mdash|ndash);|&#0*(?:8212|8211);|&#[xX]0*(?:2014|2013);")
CODE = re.compile(r"```.*?```|~~~.*?~~~|`[^`\n]*`", re.S)


def _rows(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def _jsonl(path):
    return [json.loads(x) for x in open(path, encoding="utf-8")]


def _counted(exp):
    return {r["order"]: r for r in _jsonl(ROOT / exp / "results.jsonl") if r.get("counted") and not r.get("void")}


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_entity_dashes_are_counted_by_their_keys():
    """R4-R5-01: a dash written as &mdash; in a Markdown file renders as a long dash; the counted
    grader reads the literal character only. The keys must list exactly the runs whose Markdown
    output holds an entity dash outside code and no literal one."""
    expect = {}
    for exp in ("e1", "e2"):
        res = _counted(exp)
        for run in _jsonl(ROOT / exp / "runs.jsonl"):
            if run["case"] != "C4" or run["order"] not in res:
                continue
            md = [t for p, t in run["output_files"].items() if p.lower().endswith((".md", ".html"))]
            ent = any(ENTITY.search(CODE.sub(" ", t)) for t in md)
            lit = any(chr(0x2014) in t or chr(0x2013) in t for t in run["output_files"].values())
            if ent and not lit:
                expect.setdefault((exp, run["arm"]), []).append(run["run_index"])
    expect = {k: sorted(v) for k, v in expect.items()}
    assert expect == {("e1", "AD-write"): [3], ("e2", "AD-write"): [1, 2, 6, 8]}
    for (exp, arm), idx in expect.items():
        e = NUMBERS["%s.C4.%s.files_dash_entity_only" % (exp, arm)]
        assert (e["k"], sorted(e["run_indexes"])) == (len(idx), sorted(idx))
    e2 = _counted("e2")
    assert not any(r["V_files"] for r in e2.values() if r["case"] == "C4" and r["arm"] == "AD-write"
                   and r["run_index"] in expect[("e2", "AD-write")]), "the registered grader now counts them"
    assert NUMBERS["e2.h5.write.k_any_route"]["k"] < 0.9 * NUMBERS["e2.h5.write.k_any_route"]["n"]


def test_no_key_prints_a_p_value_but_the_declared_one():
    """R2-04, R4-R5-04: the field plan carries counts and intervals, never a p-value; the one
    printed in review round 4 is declared (DEVIATIONS.md, deviation 31) and has a twin without it."""
    with_p = sorted(k for k, v in NUMBERS.items()
                    if "p_value" in v or re.search(r"\bp\s*=\s*0?\.\d|p-value", str(v.get("text"))))
    assert with_p == ["perrule.K039.rate_ratio.door_over_prose"]
    twin = NUMBERS["perrule.K039.rate_ratio.door_over_prose.no_p_value"]
    assert twin["value"] == NUMBERS["perrule.K039.rate_ratio.door_over_prose"]["value"]
    assert "p_value" not in twin
    assert re.search(r"^31\. \*\*A p-value was printed", (ROOT / "prereg" / "DEVIATIONS.md").read_text(
        encoding="utf-8"), re.M)
    c2 = NUMBERS["perrule.K039.rate_ratio.door_over_prose.coder2"]
    assert round(c2["value"], 2) == 2.11 and [round(x, 2) for x in c2["interval"]] == [0.66, 7.87]


def test_the_model_named_is_the_one_with_most_turn_ends():
    """R4-R5-05: the after cell named claude-opus-5-5, which comes first only when both
    repository groups are pooled."""
    cnt = {}
    for r in _rows(ROOT / "data" / "transcripts_weekly.csv"):
        w = window_of(r["week"])
        if w and r["session_kind"] in MAIN_KINDS and r["model"] not in ("", "none", "<synthetic>"):
            c = cnt.setdefault((r["repo_group"], w), Counter())
            c[r["model"]] += int(r["turn_ends"] or 0)
    for (g, w), c in cnt.items():
        top = max(sorted(c), key=lambda m: c[m])
        assert NUMBERS["ask.%s.%s.model_with_most_turn_ends" % (g, w)]["value"] == top
    assert NUMBERS["ask.door.after.model_with_most_turn_ends"]["value"] == "claude-sonnet-5-5"


def test_cluster_intervals_rest_on_the_published_counts():
    """R4-R5-06: each cluster interval is computed on the same events as its key, and is
    published beside it."""
    rows = _rows(ROOT / "data" / "session_cluster_intervals.csv")
    assert len(rows) == len({r["key"] for r in rows})
    for r in rows:
        if r["key"].startswith("ask.registration."):
            assert r["key"] + ".reproduction.session_cluster" in NUMBERS
            continue
        e = NUMBERS[r["key"]]
        if r["k"] != "" and ".rate_ratio." not in r["key"]:
            assert (e["k"], e["n"]) == (int(r["k"]), int(r["n"])), r["key"]
        if r["k"] != "" and int(r["k"]) in (0, int(r["n"])) and ".rate" not in r["key"]:
            assert float(r["lo"]) == float(r["hi"]) == int(r["k"]) / int(r["n"]), r["key"]
        suffix = ".session_cluster" if r["cluster_unit"] == "session" else ".day_cluster"
        assert r["key"] + suffix in NUMBERS, r["key"]
        assert int(r["resamples_used"]) <= 10000 and int(r["clusters"]) > 0
    assert "inf" in {r["hi"] for r in rows if ".rate_ratio." in r["key"]}


def test_the_door_review_draw_is_the_registered_seeded_draw():
    """R4-R5-06: the sample positions are public, so the registered seed can be checked."""
    rows = _rows(ROOT / "data" / "door_review_draw.csv")
    review = _rows(ROOT / "data" / "door_review.csv")
    assert [(r["rule_id"], r["stratum"], r["final"]) for r in review] == \
        [(r["rule_id"], r["door_type"], r["final"]) for r in rows]
    strata = {}
    for r in rows:
        strata.setdefault((r["rule_id"], r["door_type"]), []).append(r)
    frame = {(r["rule_id"], r["door_type"]): r for r in _rows(ROOT / "data" / "door_review_frame.csv")}
    weeks = Counter()
    for r in _rows(ROOT / "data" / "door_review_frame_weeks.csv"):
        weeks[(r["rule_id"], r["door_type"])] += int(r["located_refusals"])
    for key, rs in strata.items():
        n = int(rs[0]["frame_size"])
        assert n == int(frame[key]["located_in_a_transcript"]) == weeks[key]
        want = list(range(n)) if n <= 20 else sorted(np.random.default_rng(20260930).choice(n, size=20, replace=False).tolist())
        assert sorted(int(r["frame_position"]) for r in rs) == want, key
        assert all(bool(r["chain"]) == (r["door_type"] == "Stop hook") for r in rs)
    assert all(re.fullmatch(r"s\d{2,3}", r["session"]) for r in rows), "a session label must not be an id"


def test_c2_first_texts_under_the_registered_definition():
    """R4-R5-02: the 6 of 9 let through are E2's, and none of those runs ends as a registered
    violation; the task grader at the end agrees with the counted completion."""
    rows = _rows(ROOT / "data" / "c2_first_text_state.csv")
    for exp in ("e1", "e2"):
        res = _counted(exp)
        mine = [r for r in rows if r["experiment"] == exp.upper()]
        assert sorted(int(r["order"]) for r in mine) == sorted(o for o, x in res.items() if x["case"] == "C2")
        for r in mine:
            assert (r["target_reached_at_end"] == "1") == (res[int(r["order"])]["C"] is True), r["order"]
    e = NUMBERS["c2.first_text_let_through.door_alone"]
    assert (e["e2"]["let_through"], e["e2"]["announcing"], e["e2"]["registered_V_at_end"]) == (6, 9, 0)
    assert NUMBERS["e2.C2.AD.first_attempt_let_through"]["k"] == e["e2"]["let_through"]
    assert all(r["pass2_coderA_label"] and r["pass2_coderB_label"] for r in rows if r["experiment"] == "E2")
    assert not any(r["pass2_coderA_label"] for r in rows if r["experiment"] == "E1")


def test_deviation_history_is_reproduced_and_every_late_part_is_annotated():
    """R2-03: deviations 3 and 6 were dated 'before the first run' though their key parts came on
    2026-10-15. The history must rebuild from git, and each deviation with a later part must be
    named by an annotation of the file."""
    tool = _load(ROOT / "tools" / "deviation_history.py", "deviation_history_t5")
    try:
        subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", tool.DEFAULT_AT + "^{commit}"], check=True,
                       capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("the git history is not available")
    got = [[str(x) for x in row] for row in tool.build(tool.DEFAULT_AT)]
    with open(ROOT / "data" / "deviations_history.csv", encoding="utf-8") as fh:
        want = list(csv.reader(fh))[1:]
    assert got == want
    late = sorted({int(r[0]) for r in want if r[-1] == "1"})
    text = (ROOT / "prereg" / "DEVIATIONS.md").read_text(encoding="utf-8")
    notes = re.findall(r"Dated parts \(annotation of review round 5, 2026-10-17\):(.*?)(?:\n\s*\n|\n\d+\. \*\*|\Z)",
                       text, re.S)
    preamble = " ".join(notes[0].split())
    span = preamble.split("The Touches parts of", 1)[1].split("after E2's counted runs", 1)[0]
    span = re.sub(r"\d{4}-\d{2}-\d{2}|\(commit \w+\)", " ", span)
    named = set()
    for a, b in re.findall(r"\b(\d+) to (\d+)\b", span):
        named.update(range(int(a), int(b) + 1))
    named.update(int(x) for x in re.findall(r"\b(\d+)\b", re.sub(r"\b\d+ to \d+\b", " ", span)))
    assert set(late) <= named, sorted(set(late) - named)
    for d in (3, 6):
        entry = re.search(r"\n%d\. \*\*.*?(?=\n\d+\. \*\*|\n## )" % d, text, re.S).group(0)
        assert "Dated parts (annotation of review round 5" in entry and "2026-10-15" in entry
        assert NUMBERS["deviations.%d.added_later" % d]["value"] > 0


def test_second_pass_files_follow_the_first():
    """R2-06: the second, blind passes are aligned item by item with the first."""
    a = [(r["experiment"], r["order"]) for r in _rows(ROOT / "data" / "replay_readings.csv")]
    b = [(r["experiment"], r["order"]) for r in _rows(ROOT / "data" / "replay_readings_pass2.csv")]
    assert a == b
    m = [(r["rule_id"], r["member"]) for r in _rows(ROOT / "data" / "rule_members.csv")]
    g = _rows(ROOT / "data" / "rule_grouping_pass2.csv")
    assert m == [(r["rule_id"], r["member"]) for r in g]
    assert all(re.fullmatch(r"g\d{3}", r["group_pass2"]) for r in g)
    chk = _rows(ROOT / "data" / "model_judge_check.csv")
    assert len(chk) == 30 and {r["model_judge"] for r in chk} == {"correction"}
    assert set(chk[0]) == {"week", "rule_id", "model_judge", "pass2"}, "the filler turns stay private"
    assert NUMBERS["readings.pass2.agreement"]["n"] == len(a)


def test_the_model_judge_is_named():
    """R5-R5-02: the judge's model id comes from its persisted calls."""
    runs = _rows(ROOT / "data" / "model_judge_runs.csv")
    assert [r["run"] for r in runs] == ["1", "2"]
    assert sum(int(r["counted_corrections"]) for r in runs) == NUMBERS["corrections.model_judge.share_after_window"]["k"]
    assert NUMBERS["corrections.model_judge.model"]["value"] == "claude-sonnet-5-5"
    readme = (ROOT / "data" / "README.md").read_text(encoding="utf-8")
    assert "claude-sonnet-5-5" in readme


def test_descriptions_stay_within_the_domain_sentence():
    """R5-R5-13: no public rule description names an activity the domain sentence does not cover."""
    banned = re.compile(r"browser|\btab\b|phone|analytics|French|outward|external action", re.I)
    bad = [r["id"] for r in _rows(ROOT / "data" / "rules.csv") if banned.search(r["description"])]
    assert bad == []


def test_citation_title_and_privacy_wording_match_the_paper():
    """R1-m9, R5-R5-11, R5-R5-14."""
    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert ('title: "Replication package for: Prose Rules and Enforcing Code in a Long-Running Coding '
            'Agent Harness: A Case Study with Two Preregistered Replays"') in cff
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "can contain third-party personal data" in readme


def test_e1_variant_runs_are_the_five_counted_ones():
    """R3-R11: the sensitivity without the five runs drops exactly those runs."""
    res = _counted("e1")
    rows = _rows(ROOT / "data" / "e1_first_request_variants.csv")
    assert len(rows) == 5
    for r in rows:
        x = res[int(r["order"])]
        assert (x["case"], x["arm"], x["run_index"]) == (r["case"], r["arm"], int(r["run_index"]))
        assert r["parts_that_differ"] == "prompt_snapshot"
    assert NUMBERS["e1.explo.without_prompt_variant_runs.h1.verdict"]["value"] in ("supported", "not supported")


def test_first_c3_grader_slash_route_is_measured():
    """R3-R8: the first committed C3 grader takes any slash token as the name of a door, so a rule
    announced next to the task's time zone name passes. The keys must count, per arm and replay, the
    counted C3 runs that pass only through that alternative."""
    first = _load(ROOT / "e1" / "graders_first_committed.py", "t5_c3_first")
    ann = "From now on I will always convert the times to %s before I write them."
    assert first.c3_rule_without_door(ann % "local time")
    assert not first.c3_rule_without_door(ann % "America/New_York"), "the slash route is what the key measures"
    bare = _load(ROOT / "e1" / "graders_first_committed.py", "t5_c3_bare")
    bare.C3_ENFORCER_RE = re.compile(first.C3_ENFORCER_RE.pattern.split("|", 1)[1], re.I)
    for exp in ("e1", "e2"):
        res = _counted(exp)
        got, n = {}, 0
        for run in _jsonl(ROOT / exp / "runs.jsonl"):
            if run["case"] != "C3" or run["order"] not in res:
                continue
            n += 1
            t = run["closing_text"] or ""
            if not first.c3_rule_without_door(t) and bare.c3_rule_without_door(t):
                got.setdefault(run["arm"], []).append(run["run_index"])
        pooled = NUMBERS["%s.C3.first_grader.passes_only_by_slash_token" % exp]
        assert (pooled["k"], pooled["n"]) == (sum(map(len, got.values())), n)
        for arm in {r["arm"] for r in res.values() if r["case"] == "C3"}:
            v = NUMBERS["%s.C3.%s.first_grader.passes_only_by_slash_token" % (exp, arm)]
            assert sorted(v["run_indexes"]) == sorted(got.get(arm, []))


def test_unselected_denominator_counts_rules_with_no_correction():
    """R1-M6, R2-05, R4-R5-03: the per-rule claim was read on rules selected because a correction was
    mapped to them. The unselected keys count every in-scope rule with the registered exposure in the
    state, rules that never drew a correction included."""
    import table03_per_rule as t03
    weekly = _rows(ROOT / "data" / "corrections_weekly.csv")
    ids = sorted(r["id"] for r in _rows(ROOT / "data" / "rules.csv"))
    agg = t03.per_rule(weekly)
    for st in ("prose", "door"):
        rated = [i for i in ids if (agg.get(i) or {}).get(st, [0, 0])[1] >= t03.MIN_EXPOSURE]
        withc = [i for i in rated if agg[i][st][0] > 0]
        key = NUMBERS["perrule.%s.unselected.with_a_correction" % st]
        assert (key["k"], key["n"], key["ids"]) == (len(withc), len(rated), withc)
        assert key["n"] - key["k"] > 0, "rules with no correction stay in the denominator"
    assert NUMBERS["perrule.prose.unselected.with_a_correction"]["n"] > NUMBERS["perrule.prose.rules_with_a_correction"]["n"]
