"""E1's judgment of H1 to H5 on synthetic runs (no real result is read here)."""
import json

import pytest

import table12_e1 as e1
from common import Context

DESIGN = {
    "model": "model-a",
    "cases": {
        "C1": {"doors": {"door": []}},
        "C2": {"doors": {"door": []}},
        "C3": {"doors": {"door": []}},
        "C4": {"doors": {"stop": [], "write": []}},
        "C5": {"doors": {}},
    },
}


def run_row(case, arm, i, V, C=True, B=0, K_stop=(), K_deny=(), V_door=None, **kw):
    door = e1.is_door_arm(arm)
    r = {"case": case, "arm": arm, "run_index": i, "counted": True, "void": None,
         "model_requested": "model-a", "model": "model-a", "cli_version": "9.9.9",
         "trimwrit_commit": "abc1234", "ts": "2026-10-01T00:00:%02dZ" % (i % 60),
         "V": V, "V_door": V if V_door is None else V_door, "C": C, "B": B,
         "B_stop": len(K_stop), "B_deny": len(K_deny), "K_stop": list(K_stop),
         "K_deny": list(K_deny), "E": V if door else None, "turns": 5, "output_tokens": 100,
         "wall_s": 10.0, "killed": False}
    r.update(kw)
    return r


def cell(case, arm, n_viol, n=10, **kw):
    return [run_row(case, arm, i, i < n_viol, **kw) for i in range(n)]


def world(ad_viol=0, write_k=True, stop_blocks=0, drop=()):
    runs = []
    for c in ("C1", "C2", "C3"):
        if c in drop:
            continue
        runs += cell(c, "A0", 10) + cell(c, "AP", 3)
        runs += cell(c, "AD", ad_viol, B=1) + cell(c, "APD", 0)
    if "C4" not in drop:
        runs += cell("C4", "A0", 10) + cell("C4", "AP", 2)
        runs += [run_row("C4", "AD-stop", i, False, K_stop=[False] if i < stop_blocks else [])
                 for i in range(10)]
        runs += cell("C4", "APD-stop", 0)
        runs += [run_row("C4", "AD-write", i, False, K_deny=[write_k]) for i in range(10)]
        runs += cell("C4", "APD-write", 0)
    runs += cell("C5", "A0", 8) + cell("C5", "AP", 0)
    return runs


def write_world(tmp_path, runs):
    d = tmp_path / "e1"
    d.mkdir()
    (d / "design.json").write_text(json.dumps(DESIGN))
    (d / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in runs))
    return Context(data_dir=tmp_path / "data", e1_dir=d, out_dir=tmp_path / "results")


def test_arms_follow_the_design():
    assert e1.arms_of(DESIGN["cases"]["C1"]) == ["A0", "AP", "AD", "APD"]
    assert e1.arms_of(DESIGN["cases"]["C4"]) == ["A0", "AP", "AD-stop", "APD-stop",
                                                 "AD-write", "APD-write"]
    assert e1.arms_of(DESIGN["cases"]["C5"]) == ["A0", "AP"]


def test_a_world_where_prose_and_door_both_work(tmp_path):
    ctx = write_world(tmp_path, world(stop_blocks=6))
    doc = e1.run(ctx)
    assert doc["H1"]["verdict"] == "supported"
    assert doc["H2"]["verdict"] == "supported"
    assert doc["H2"]["v_ad"]["point"] == 0.0
    assert doc["H3"]["verdict"] == "supported"
    assert doc["H4"]["verdict"] == "supported"
    assert doc["H5"]["stop"]["verdict"] == "supported"
    assert doc["H5"]["write"]["verdict"] == "supported"
    assert doc["H5"]["verdict"] == "supported"
    reg = ctx.registry.entries
    assert reg["e1.n_runs"]["value"] == 200
    assert reg["e1.C1.A0.V"]["k"] == 10
    assert reg["e1.model_id"]["text"] == "model-a"
    assert (ctx.out / "hypotheses.json").exists()
    assert (ctx.out / "tables" / "table12_e1_cells.csv").exists()


def test_a_leaky_door_fails_h2_and_a_door_that_does_not_hold_fails_h5(tmp_path):
    ctx = write_world(tmp_path, world(ad_viol=5, write_k=False, stop_blocks=6))
    doc = e1.run(ctx)
    assert doc["H2"]["verdict"] == "not supported"
    assert doc["H2"]["parts"]["v_ad_at_most_0.05"] is False
    assert doc["H5"]["write"]["verdict"] == "not supported"
    assert doc["H5"]["verdict"] == "not supported"


def test_fewer_than_five_blocks_is_not_judgeable(tmp_path):
    ctx = write_world(tmp_path, world(stop_blocks=4))
    doc = e1.run(ctx)
    assert doc["H5"]["stop"]["verdict"] == "not judgeable"
    assert doc["H5"]["write"]["verdict"] == "supported"
    assert doc["H5"]["verdict"] == "partly judgeable"


def test_pooled_hypotheses_need_three_cases(tmp_path):
    ctx = write_world(tmp_path, world(drop=("C2", "C3")))
    doc = e1.run(ctx)
    assert doc["H1"]["verdict"] == "supported"  # C1, C4, C5 remain
    for h in ("H2", "H3", "H4"):
        assert doc[h]["verdict"] == "not judgeable"


def test_voided_uncounted_and_other_model_runs_stay_out(tmp_path):
    runs = world(stop_blocks=6)
    runs.append(run_row("C1", "AP", 99, True, void="tool crash"))
    runs.append(run_row("C1", "AP", 98, True, counted=False))
    runs += cell("C1", "AP", 10, model_requested="model-b")
    ctx = write_world(tmp_path, runs)
    doc = e1.run(ctx)
    reg = ctx.registry.entries
    assert reg["e1.C1.AP.V"]["k"] == 3 and reg["e1.C1.AP.V"]["n"] == 10
    assert reg["e1.n_void"]["value"] == 1
    assert reg["e1.n_exploratory_runs"]["value"] == 10
    assert doc["n_runs"] == 200


def test_door_detector_analysis_is_beside_and_decides_nothing(tmp_path):
    runs = world(stop_blocks=6)
    for r in runs:
        r["V_door"] = False
    ctx = write_world(tmp_path, runs)
    doc = e1.run(ctx)
    assert doc["H1"]["verdict"] == "supported"
    assert doc["H1"]["secondary_door_detector"]["verdict"] == "not judgeable" or \
        doc["H1"]["secondary_door_detector"]["point"] == pytest.approx(0.0)


def test_verdicts_do_not_depend_on_run_order(tmp_path):
    runs = world(ad_viol=2, stop_blocks=6)
    a = e1.run(write_world(tmp_path / "a", runs) if (tmp_path / "a").mkdir() is None else None)
    b = e1.run(write_world(tmp_path / "b", list(reversed(runs))) if (tmp_path / "b").mkdir() is None
               else None)
    assert json.dumps(a) == json.dumps(b)
