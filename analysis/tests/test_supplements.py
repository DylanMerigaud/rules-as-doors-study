"""The review-round supplements (analysis/e1_supplement.py, analysis/field_supplement.py) on the
published files: they run, they leave every earlier key as it was, and their main values hold."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NUMBERS = ROOT / "analysis" / "numbers.py"


def test_supplements_on_the_published_files(tmp_path):
    out = tmp_path / "out"
    p = subprocess.run([sys.executable, str(NUMBERS), "--out", str(out)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    manifest = json.loads((out / "manifest.json").read_text())
    assert "E1 supplement (review round 1)" in manifest["ran"]
    assert "field supplement (review round 1)" in manifest["ran"]
    n = json.loads((out / "numbers.json").read_text())
    published = json.loads((ROOT / "results" / "numbers.json").read_text())
    assert n == published
    assert n["sched.launches.after_window"]["value"] == 516
    assert n["sched.launches.before_window"]["value"] + 516 == n["sched.launches"]["value"]
    assert n["dashwrite.denials.registered_windows"]["value"] + \
        n["dashwrite.denials.outside_windows"]["value"] == n["dashwrite.denials"]["value"]
    k001 = sum(n["door.K001.refusals.%s" % t]["value"]
               for t in ("pretooluse_hook", "stop_hook", "write_refusal"))
    assert k001 == n["door.K001.refusals"]["value"]
    assert n["e1.regrade.disagreements"]["value"] == 0
    assert n["e1.C2.door_arms.stop_decisions_match_detector_on_previous_text"]["value"] == 22
    assert round(n["rules.kappa_class.recomputed"]["value"], 6) == round(n["rules.kappa_class"]["value"], 6)
    assert round(n["rules.kappa_enforceability.recomputed"]["value"], 6) == \
        round(n["rules.kappa_enforceability"]["value"], 6)


def test_headless_split_agrees_with_the_weekly_table_over_all_weeks():
    import csv
    weekly = list(csv.DictReader(open(ROOT / "data" / "transcripts_weekly.csv")))
    split = list(csv.DictReader(open(ROOT / "data" / "headless_split.csv")))
    for col in ("stop_firings", "ref_stop_promise", "ref_stop_ask", "ref_stop_rule", "ref_stop_retired",
                "dash_stop_detected", "ref_ptu_dash_write", "write_calls"):
        a = sum(int(r[col] or 0) for r in weekly if r["session_kind"] == "scheduler worker")
        b = sum(int(r[col] or 0) for r in split)
        assert a == b, col
    bare = [r for r in split if r["headless_kind"] == "scheduler worker prompt"]
    assert all(int(r[c]) == 0 for r in bare for c in split[0] if c.startswith(("ref_", "stop_", "dash_")))
