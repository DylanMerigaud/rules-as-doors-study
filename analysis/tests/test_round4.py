"""Review round 4 (analysis/round4_supplement.py and the files it reads). Each test would have
caught one error a round 4 review found in the package: C3 keys that listed violating runs as
passes, agreement intervals bootstrapped off their registration, an answer rule worded three ways,
and the new files' content (codes and counts only)."""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
from stats import kappa_bootstrap  # noqa: E402

NUMBERS = json.loads((ROOT / "results" / "numbers.json").read_text(encoding="utf-8"))
REGISTERED_CI = "percentile bootstrap over items, numpy default_rng(20260930), 10,000 resamples"


def _rows(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def _results(exp):
    return {r["order"]: r for r in (json.loads(x) for x in open(ROOT / exp / "results.jsonl", encoding="utf-8"))
            if r.get("counted") and not r.get("void")}


def test_c3_keys_agree_with_the_counted_v():
    """R1-R1-M11: a run listed as passing the counted grader must have V false, and every
    announcing run counted as a violation must be listed as one."""
    for exp in ("e1", "e2"):
        res = _results(exp)
        passed = NUMBERS["%s.C3.announced_but_passed" % exp]
        violated = NUMBERS["%s.C3.announced_and_violated" % exp]
        orders = passed["orders_hook_word"] + passed["orders_code_file"]
        assert passed["value"] == len(orders), exp
        for o in orders:
            assert res[o]["case"] == "C3" and res[o]["V"] is not True, (exp, o)
        for o in violated["orders"]:
            assert res[o]["case"] == "C3" and res[o]["V"] is True, (exp, o)
        all_v = sorted(o for o, r in res.items() if r["case"] == "C3" and r["V"] is True)
        assert sorted(violated["orders"]) == all_v, exp
        assert not set(orders) & set(violated["orders"]), exp
    assert NUMBERS["e1.C3.announced_but_passed"]["value"] == 10
    assert NUMBERS["e2.C3.announced_but_passed"]["value"] == 15


def test_kappas_use_the_registered_bootstrap():
    """R4-R4-06: PREREG.md section 9 registers 10,000 resamples and the study seed."""
    rows = _rows(ROOT / "data" / "agreement_pairs.csv")
    assert list(rows[0]) == ["coding", "item", "coder1", "coder2"]
    for coding, key, n in (("screen", "rules.screen.kappa", 256), ("mapping", "corrections.mapping.kappa", 84)):
        rs = sorted((r for r in rows if r["coding"] == coding), key=lambda r: int(r["item"]))
        assert len(rs) == n and [int(r["item"]) for r in rs] == list(range(1, n + 1))
        k, ci = kappa_bootstrap([r["coder1"] for r in rs], [r["coder2"] for r in rs])
        e = NUMBERS[key]
        assert e["ci_method"] == REGISTERED_CI
        assert abs(e["value"] - k) < 1e-6 and abs(e["interval"][0] - ci[0]) < 1e-6
        assert abs(e["interval"][1] - ci[1]) < 1e-6
    screen = Counter((r["coder1"], r["coder2"]) for r in rows if r["coding"] == "screen")
    assert screen == Counter({("rule", "rule"): 174, ("not a rule", "not a rule"): 68,
                              ("rule", "not a rule"): 9, ("not a rule", "rule"): 5})
    mapping = [r for r in rows if r["coding"] == "mapping"]
    assert sum(r["coder1"] == r["coder2"] for r in mapping) == NUMBERS["corrections.mapping.agreement"]["k"]
    # Every kappa interval in the registry follows the registration (the note may name the old one).
    for key, e in NUMBERS.items():
        if "kappa" in key and e.get("interval"):
            how = e.get("ci_method", "") + e["source"]
            assert "2000 resamples" not in how and "seed 7" not in how, key


def test_case_facts_no_longer_hold_the_two_kappas():
    keys = {r["key"] for r in _rows(ROOT / "data" / "case_facts.csv")}
    assert "rules.screen.kappa" not in keys and "corrections.mapping.kappa" not in keys


def test_corrections_coded_sum_to_the_weekly_table():
    coded = _rows(ROOT / "data" / "corrections_coded.csv")
    weekly = Counter()
    for r in _rows(ROOT / "data" / "corrections_weekly.csv"):
        if int(r["count"]):
            weekly[(r["week"], r["rule_id"], r["state"])] += int(r["count"])
    mine = Counter((r["week"], r["coder1_rule"], r["coder1_state"]) for r in coded
                   if r["coder1_rule"] != "not a public rule")
    assert mine == weekly
    assert {r["source"] for r in coded} <= {"model judge", "pattern", "back-fill", "in session"}
    for r in coded:
        assert r["pattern_hit"] in ("0", "1")
        assert (r["source"] == "model judge") == bool(r["turn_week"])
        assert r["coder1_rule"] != "not a public rule" or r["coder2_rule"] != "not a public rule"
        for col in ("coder1_rule", "coder2_rule"):
            assert r[col] == "not a public rule" or re.fullmatch(r"K\d{3}", r[col]), r[col]
    k39 = [r for r in coded if r["coder1_rule"] == "K039" and r["coder1_state"] == "door"]
    assert len(k39) == 12 and {r["source"] for r in k39} == {"model judge"}
    assert NUMBERS["perrule.K039.door.rate.without_model_judge"]["k"] == 0


def test_ask_after_rows_match_the_published_shares():
    rows = _rows(ROOT / "data" / "ask_reconcile_after.csv")
    assert len(rows) == 8
    for r in rows:
        k, n = int(r["k"]), int(r["n"])
        if r["step"] == "F":
            e = NUMBERS["ask.%s.%s.answered_q" % (r["group"], r["window"])]
        else:
            e = NUMBERS["ask.reconcile.F_phrases.%s.%s" % (r["group"], r["window"])]
        assert (e["k"], e["n"]) == (k, n), r
    assert NUMBERS["ask.criterion.control_drops.inventory_phrases"]["value"] is True
    assert NUMBERS["ask.criterion.control_drops.final_numerator"]["value"] is False


def test_the_answer_rule_is_worded_one_way():
    """R4-R4-11: the reconciliation table names the rule data/README.md defines (a user-role
    entry with text, prompt source not checked, a Stop hook's feedback not an answer)."""
    rows = {(r["step"], r["group"]): r["change"] for r in _rows(ROOT / "data" / "ask_reconcile.csv")}
    d = rows[("D", "door")]
    assert "user-role" in d and "prompt source is not checked" in d
    assert "Stop hook's feedback is not an answer" in d
    for key in rows.values():
        assert "operator prompt" not in key and "typed in the command line" not in key
    readme = (ROOT / "data" / "README.md").read_text(encoding="utf-8")
    assert "Its prompt source is not checked" in readme


def test_run_identity_holds_codes_and_counts_only():
    """R3-M3, R3-M4: per run, what the tool reports of the model, the first request's hash, the
    loaded instruction files; no path, no text."""
    for exp, n in (("e1", 200), ("e2", 220)):
        rows = _rows(ROOT / exp / "run_identity.csv")
        assert len(rows) == n, exp
        for r in rows:
            for col, v in r.items():
                assert "/Users" not in v and "/private" not in v and "tmp" not in v, (exp, col)
                assert len(v) < 60, (exp, col, v)
            assert re.fullmatch(r"[0-9a-f]{16}", r["first_request_sha256_16"])
            assert r["own_scratch_dir"] == "1"
            assert r["responses_reporting_alias"] == r["responses"]
            assert r["instruction_files_loaded"] == "Project:CLAUDE.md"
        keys = {(r["case"], r["arm"], r["run_index"]) for r in rows}
        res = {(r["case"], r["arm"], str(r["run_index"])) for r in _results(exp).values()}
        assert keys == res, exp


def test_readings_cover_c1_and_c2_and_match_v():
    rows = _rows(ROOT / "data" / "replay_readings.csv")
    res = {"E1": _results("e1"), "E2": _results("e2")}
    for r in rows:
        o = res[r["experiment"]][int(r["order"])]
        assert (o["case"], o["arm"], o["run_index"]) == (r["case"], r["arm"], int(r["run_index"]))
        assert int(o["V"] is True) == int(r["grader_V"])
        assert r["reading"] in ("violation", "no violation")
    c1 = [r for r in rows if r["case"] == "C1"]
    assert len(c1) == 80 and all(r["reading"] == "no violation" for r in c1)
    c2 = [r for r in rows if r["experiment"] == "E1" and r["case"] == "C2"]
    assert len(c2) == 20 and all(r["reading"] == "violation" and r["grader_V"] == "1" for r in c2)
    assert NUMBERS["e1.C1.reading"]["k"] == 0 and NUMBERS["e2.C1.reading"]["k"] == 0


def test_codebooks_withhold_what_they_say():
    folder = ROOT / "data" / "codebooks"
    names = {p.name for p in folder.iterdir()}
    assert {"README.md", "rule_inventory.md", "correction_mapping.md", "refusal_review.md",
            "ask_audit.md", "correction_pattern.py"} <= names
    inv = (folder / "rule_inventory.md").read_text(encoding="utf-8")
    assert "[Withheld for publication." in inv and "Dylan" not in inv
    sys.path.insert(0, str(folder))
    import correction_pattern as cp  # noqa: E402
    assert cp.is_candidate("you did it again")
    assert not cp.is_candidate("thanks, looks good")
