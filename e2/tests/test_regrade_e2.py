"""E2's published run records reproduce every recorded measure (review round 3, R1-R14, R2-M11,
R3-R3-04, R4-R4-M3), and the regrade can disagree when a record is changed."""
import copy
import importlib.util
import json
import os

E2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("e2_regrade_test", os.path.join(E2, "regrade.py"))
regrade = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(regrade)


def test_runs_jsonl_regrades_to_results_jsonl():
    bad, rows = regrade.compare()
    assert len(rows) == 220
    assert bad == []


def test_the_regrade_can_disagree(tmp_path):
    runs = regrade.read_jsonl(os.path.join(E2, "runs.jsonl"))
    changed = copy.deepcopy(runs)
    # A door-alone C4S run whose re-answer moved the dash into code: drop the dash from its
    # closing text and the prose grader's V must flip; a C4 write run that lost its denials must
    # change B and K.
    c4s = next(r for r in changed if r["case"] == "C4S" and r["arm"] == "AD-stop")
    c4s["closing_text"] = c4s["closing_text"].replace(chr(0x2014), ",").replace(chr(0x2013), " to ")
    c4w = next(r for r in changed if r["case"] == "C4" and r["arm"] == "AD-write" and r["n_denials"])
    c4w["n_denials"] = 0
    p = tmp_path / "runs.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in changed), encoding="utf-8")
    bad, _rows = regrade.compare(runs_path=str(p))
    fields = {(o, f) for o, f, _a, _b in bad}
    assert (c4s["order"], "V") in fields
    assert (c4w["order"], "B") in fields


def test_runs_jsonl_holds_no_machine_path():
    raw = open(os.path.join(E2, "runs.jsonl"), "rb").read()
    raw.decode("ascii")
    for needle in (b"/Users/", b"/var/folders/", b"/home/"):
        assert needle not in raw
