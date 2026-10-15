"""The round 2 supplement (analysis/round2_supplement.py), its inputs and the figure fix: the first
committed graders are the committed bytes, the two-stage bootstrap is seeded and reduces to the
cluster bootstrap when runs do not vary, SVG clip ids are stable, the new public tables carry no
text, and the main values hold on the published files."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NUMBERS = ROOT / "analysis" / "numbers.py"
FIRST_SHA256 = "3cf60890e34fbbf0f3d75e49968ab0ddafed122ff234d9b7982351876c169b5b"


def test_first_committed_graders_are_the_committed_bytes():
    body = (ROOT / "e1" / "graders_first_committed.py").read_bytes()
    assert hashlib.sha256(body).hexdigest() == FIRST_SHA256
    p = subprocess.run(["git", "-C", str(ROOT), "show", "3bd3559:e1/graders.py"], capture_output=True)
    if p.returncode != 0:
        pytest.skip("no git history here (an archive copy): the sha256 pin above holds")
    assert p.stdout == body


def test_two_stage_is_seeded_and_reduces_to_the_cluster_bootstrap():
    from round2_supplement import two_stage
    from stats import cluster_bootstrap

    cases = ["a", "b", "c", "d"]
    flat = {}
    for i, c in enumerate(cases):
        flat[(c, "A0", "V")] = [1.0 * (i % 2)] * 10
        flat[(c, "AP", "V")] = [0.0] * 10

    def terms(c):
        return [(1, "V", "A0"), (-1, "V", "AP")]

    pt, ci, per = two_stage(cases, terms, flat)
    cpt, cci = cluster_bootstrap(list(per.values()))
    assert pt == pytest.approx(cpt) and ci == pytest.approx(cci)
    mixed = dict(flat)
    mixed[("a", "A0", "V")] = [1.0] * 5 + [0.0] * 5
    one = two_stage(cases, terms, mixed)
    two = two_stage(cases, terms, mixed)
    assert one == two
    assert one[1][0] <= cluster_bootstrap(list(one[2].values()))[1][0]


def test_svg_clip_ids_are_renamed_in_order():
    from common import stable_clip_ids

    svg = ('<clipPath id="p7f9c619296"/><clipPath id="p21f25496fd"/>'
           '<g clip-path="url(#p21f25496fd)"/><g clip-path="url(#p7f9c619296)"/>')
    out = stable_clip_ids(svg)
    assert out == ('<clipPath id="clip1"/><clipPath id="clip2"/>'
                   '<g clip-path="url(#clip2)"/><g clip-path="url(#clip1)"/>')
    assert stable_clip_ids(out) == out


def test_pilot_table_holds_flags_and_times_only():
    rows = list(csv.DictReader(open(ROOT / "e1" / "pilot_runs.csv", encoding="utf-8")))
    assert len(rows) == 30
    assert list(rows[0]) == ["case", "situation", "run_index", "batch_started_utc", "trimwrit_commit",
                             "V_recorded_at_run_time", "V_first_committed_graders", "V_counted_graders"]
    for r in rows:
        assert {r["V_recorded_at_run_time"], r["V_first_committed_graders"], r["V_counted_graders"]} <= {"0", "1"}


def test_rule_members_cover_every_public_rule():
    rules = {r["id"]: r for r in csv.DictReader(open(ROOT / "data" / "rules.csv", encoding="utf-8"))}
    units = {r["unit"]: r["rule_id"] for r in csv.DictReader(open(ROOT / "data" / "rules_coding.csv", encoding="utf-8"))}
    mem = list(csv.DictReader(open(ROOT / "data" / "rule_members.csv", encoding="utf-8")))
    assert {m["rule_id"] for m in mem} == set(rules)
    for rid, r in rules.items():
        text = [m for m in mem if m["rule_id"] == rid and m["kind"] == "text unit"]
        assert len(text) == int(r["n_prose_units"] or 0), rid
        assert all(units[m["member"]] == rid for m in text)
    assert {m["member"] for m in mem if m["kind"] == "text unit"} == set(units)


def test_round2_values_on_the_published_files(tmp_path):
    out = tmp_path / "out"
    p = subprocess.run([sys.executable, str(NUMBERS), "--out", str(out)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    manifest = json.loads((out / "manifest.json").read_text())
    assert "round 2 supplement (review round 2)" in manifest["ran"]
    n = json.loads((out / "numbers.json").read_text())
    assert n == json.loads((ROOT / "results" / "numbers.json").read_text())
    assert (n["e1.h5.write_strict.k"]["k"], n["e1.h5.write_strict.k"]["n"]) == (9, 10)
    assert n["e1.first_graders.runs_with_another_V"]["per_case"] == {"C3": 20}
    for arm in ("A0", "AP", "AD", "APD"):
        assert n["e1.first_graders.C3.%s.V" % arm]["k"] == n["e1.C3.%s.V_first_committed_grader" % arm]["k"]
    assert n["e1.pilot.recorded_equals_first_graders"]["value"] == 30
    assert n["rules.labels.recomputed_agree.class"]["value"] == 134
    assert n["rules.labels.recomputed_agree.enforceability"]["value"] == 134
    assert n["door.K001.refusals.without_test_session"]["value"] == n["door.K001.refusals"]["value"] - 1
    assert n["door.K001.recovery_turns.without_test_session"]["n"] == n["door.K001.recovery_turns"]["n"] - 1
    assert n["door.K001.review.frame.stop_hook.without_test_session"]["refusals"] == \
        n["door.K001.review.frame.stop_hook"]["refusals"] - 1
    assert n["dashstop.blocks.all_weeks_all_kinds"]["value"] >= n["dashstop.blocks"]["value"]
    for key in ("e1.h1.diff", "e1.h2.v_ap", "e2.h1.diff", "e2.h2.diff"):
        assert n[key + ".two_stage"]["value"] == n[key]["value"]
