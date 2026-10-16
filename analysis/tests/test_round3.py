"""Review round 3 (analysis/round3_supplement.py and the files it reads): the run facts and the
ask ladder hold counts only, E2's turn-end indexes point at texts, and the main round 3 values
recompute from the published files."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NUMBERS = json.loads((ROOT / "results" / "numbers.json").read_text(encoding="utf-8"))

NEW_FACT_COLUMNS = ["own_config_dir", "first_call_context_tokens", "turn_results",
                    "turns_resumed_by_task_notification"]
TEXT_COLUMNS = {"case", "arm", "hooks_registered", "model_reported"}


def _rows(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def test_run_facts_hold_counts_only():
    for exp, n in (("e1", 200), ("e2", 220)):
        rows = _rows(ROOT / exp / "run_facts.csv")
        assert len(rows) == n, exp
        assert list(rows[0])[-4:] == NEW_FACT_COLUMNS, exp
        for r in rows:
            for col, v in r.items():
                if col in TEXT_COLUMNS:
                    assert "/" not in v and len(v) < 60, (exp, col, v)
                else:
                    assert v.isdigit(), (exp, col, v)
            assert r["own_config_dir"] == "1"
            assert int(r["turn_results"]) >= 1
            assert int(r["turns_resumed_by_task_notification"]) < int(r["turn_results"])


def test_e2_turn_end_indexes_point_at_texts():
    facts = {(r["case"], r["arm"], r["run_index"]): r for r in _rows(ROOT / "e2" / "run_facts.csv")}
    n = 0
    for line in open(ROOT / "e2" / "runs.jsonl", encoding="utf-8"):
        run = json.loads(line)
        idx = run["turn_end_text_indexes"]
        assert idx == sorted(set(idx)), run["order"]
        assert all(0 <= i < len(run["texts"]) for i in idx), run["order"]
        f = facts[(run["case"], run["arm"], str(run["run_index"]))]
        assert len(idx) <= int(f["turn_results"]), run["order"]
        n += 1
    assert n == 220


def test_ask_ladder_ends_on_the_published_ask_shares():
    rows = _rows(ROOT / "data" / "ask_reconcile.csv")
    assert list(rows[0]) == ["step", "group", "k", "n", "change"]
    assert len(rows) == 14
    for r in rows:
        assert 0 <= int(r["k"]) <= int(r["n"])
        assert "/" not in r["change"]
    final = {r["group"]: (int(r["k"]), int(r["n"])) for r in rows if r["step"] == "F"}
    for g in ("door", "control"):
        e = NUMBERS["ask.%s.before.answered_q" % g]
        assert final[g] == (e["k"], e["n"]), g
    first = {r["group"]: (int(r["k"]), int(r["n"])) for r in rows if r["step"] == "A"}
    reg = NUMBERS["ask.registration.control.before.answered_q"]
    assert first["control"] == (reg["k"], reg["n"])
    assert first["door"][0] == NUMBERS["ask.registration.door.before.answered_q"]["k"]


def test_round3_values_recompute_from_the_pilot_and_run_files():
    pilot = _rows(ROOT / "e1" / "pilot_runs.csv")
    by_sit = {}
    for r in pilot:
        by_sit.setdefault((r["case"], r["situation"]), []).append(int(r["V_e2_graders"]))
    for (c, s), v in by_sit.items():
        assert NUMBERS["e1.pilot.%s.s%s.V_e2_graders" % (c, s)]["value"] == sum(v)
    for exp, n in (("e1", 200), ("e2", 220)):
        rows = _rows(ROOT / exp / "run_facts.csv")
        resumed = sum(1 for r in rows if int(r["turns_resumed_by_task_notification"]) > 0)
        assert NUMBERS["%s.run_facts.resumed_by_task_notification" % exp]["value"] == resumed
        assert NUMBERS["%s.run_facts.own_config_dir" % exp]["k"] == n
    for key in ("e1.h2.diff.draws_from_zero_cases", "e2.h1.diff.draws_from_zero_cases"):
        e = NUMBERS[key]
        assert 0 < e["value"] < e["n"] == 10000
    assert NUMBERS["e2.explo.informative.h1.verdict"]["value"] == "supported"
    assert NUMBERS["e1.explo.without_C3.h1.verdict"]["value"] == "supported"
    assert NUMBERS["small_sample.wilson.runs_for_upper_5pct"]["value"] == 73
