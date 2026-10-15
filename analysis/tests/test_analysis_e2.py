"""E2's judgment of H1 to H5 on synthetic runs (no real result is read here)."""
import json
from collections import OrderedDict

import table12_e1 as e1
import table14_e2 as e2
from common import Context

DESIGN = {
    "model": "model-a",
    "cases": {
        "C1": {"doors": {"door": []}},
        "C2": {"doors": {"door": []}},
        "C3": {"doors": {"door": []}},
        "C4": {"doors": {"write": []}},
        "C4S": {"doors": {"stop": []}},
        "C5": {"doors": {}},
    },
}


def run_row(case, arm, i, V, C=True, B=0, K_stop=(), K_deny=(), K_strict=None, K_door=None,
            **kw):
    door = e1.is_door_arm(arm)
    r = {"experiment": "E2", "case": case, "arm": arm, "run_index": i, "order": i,
         "counted": True, "void": None, "model_requested": "model-a", "model": "model-a",
         "cli_version": "9.9.9", "trimwrit_commit": "abc1234",
         "ts": "2026-10-16T00:00:%02dZ" % (i % 60), "V": V, "V_door": V, "C": C,
         "B": B or len(K_stop) + len(K_deny), "B_stop": len(K_stop), "B_deny": len(K_deny),
         "K_stop": list(K_stop), "K_deny": list(K_deny),
         "K_stop_door": list(K_stop if K_door is None else K_door),
         "K_deny_strict": list(K_deny if K_strict is None else K_strict),
         "E": V if door else None, "turns": 5, "output_tokens": 100, "wall_s": 10.0,
         "killed": False}
    if door and K_stop:
        r.update({"stop_checks": len(K_stop) + 1, "stop_agree": len(K_stop) + 1,
                  "stop_miss": 0, "stop_false_block": 0, "hook_caps": 0, "hook_crashes": 0})
    r.update(kw)
    return r


def cell(case, arm, n_viol, n=10, **kw):
    return [run_row(case, arm, i, i < n_viol, **kw) for i in range(n)]


def world(stop_k=True, write_k=True, write_strict=None, stop_k_door=None):
    runs = []
    for c in ("C1", "C2", "C3"):
        runs += cell(c, "A0", 10) + cell(c, "AP", 3)
        runs += cell(c, "AD", 0, B=1) + cell(c, "APD", 0)
    runs += cell("C4", "A0", 10) + cell("C4", "AP", 2)
    runs += [run_row("C4", "AD-write", i, False, K_deny=[write_k],
                     K_strict=None if write_strict is None else [write_strict])
             for i in range(10)]
    runs += cell("C4", "APD-write", 0)
    runs += cell("C4S", "A0", 9) + cell("C4S", "AP", 4)
    runs += [run_row("C4S", "AD-stop", i, False, K_stop=[stop_k],
                     K_door=None if stop_k_door is None else [stop_k_door])
             for i in range(10)]
    runs += cell("C4S", "APD-stop", 0)
    runs += cell("C5", "A0", 8) + cell("C5", "AP", 0)
    return runs


def write_world(tmp_path, runs, e1_hyp=None):
    d = tmp_path / "e2"
    d.mkdir(parents=True)
    (d / "design.json").write_text(json.dumps(DESIGN))
    (d / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in runs))
    out = tmp_path / "results"
    out.mkdir()
    if e1_hyp is not None:
        (out / "hypotheses.json").write_text(e1_hyp)
    return Context(data_dir=tmp_path / "data", e1_dir=tmp_path / "e1-absent", out_dir=out,
                   e2_dir=d)


def test_h5_reads_the_stop_half_from_c4s(tmp_path):
    doc = e2.run(write_world(tmp_path, world(stop_k=True)))
    assert doc["H5"]["stop"]["blocks"] == 10
    assert doc["H5"]["stop"]["verdict"] == "not supported"   # K = 1.0 is not below 0.5
    assert doc["H5"]["write"]["verdict"] == "supported"
    doc = e2.run(write_world(tmp_path / "b", world(stop_k=False)))
    assert doc["H5"]["stop"]["verdict"] == "supported"


def test_h1_to_h4_are_e1s_criteria_on_the_e2_cells(tmp_path):
    doc = e2.run(write_world(tmp_path, world()))
    for h in ("H1", "H2", "H3", "H4"):
        assert doc[h]["criterion"] == e1.CRITERIA[h]
    assert doc["H1"]["cases"] == ["C1", "C2", "C3", "C4", "C5"]   # C4S stays out of H1
    assert doc["H2"]["cases"] == ["C1", "C2", "C3", "C4"]
    assert doc["H1"]["verdict"] == "supported"
    assert doc["H2"]["verdict"] == "supported"


def test_the_strict_k_is_a_secondary_reading(tmp_path):
    doc = e2.run(write_world(tmp_path, world(write_k=True, write_strict=False)))
    assert doc["H5"]["write"]["verdict"] == "supported"
    strict = doc["H5"]["write_strict"]
    assert strict["k"] == 0 and strict["blocks"] == 10
    assert strict["verdict_by_the_write_criterion"] == "not supported"


def test_k_by_the_stop_doors_detector_is_a_secondary_reading(tmp_path):
    ctx = write_world(tmp_path, world(stop_k=False, stop_k_door=True))
    doc = e2.run(ctx)
    assert doc["H5"]["stop"]["verdict"] == "supported"
    sd = doc["H5"]["stop_door_detector"]
    assert sd["k"] == 10 and sd["blocks"] == 10
    assert sd["verdict_by_the_stop_criterion"] == "not supported"
    assert ctx.registry.entries["e2.h5.stop_door_detector.k"]["value"] == 1.0
    assert ctx.registry.entries["e2.C4S.AD-stop.K_door"]["value"] == 1.0


def test_e1s_entries_of_hypotheses_json_are_kept_byte_for_byte(tmp_path):
    e1_doc = OrderedDict([("registered", "prereg/PREREG.md section 8, tag prereg-v1"),
                          ("H1", OrderedDict([("verdict", "supported"), ("point", 0.123456)]))])
    e1_text = json.dumps(e1_doc, indent=1, ensure_ascii=False) + "\n"
    ctx = write_world(tmp_path, world(), e1_hyp=e1_text)
    e2.run(ctx)
    top = json.loads((ctx.out / "hypotheses.json").read_text(), object_pairs_hook=OrderedDict)
    assert list(top) == ["registered", "H1", "e2"]
    top.pop("e2")
    assert json.dumps(top, indent=1, ensure_ascii=False) + "\n" == e1_text


def test_every_key_is_under_e2_and_the_output_is_stable(tmp_path):
    ctx = write_world(tmp_path, world())
    e2.run(ctx)
    keys = sorted(ctx.registry.entries)
    assert keys and all(k.startswith("e2.") for k in keys)
    first = json.dumps(ctx.registry.entries, sort_keys=True)
    ctx2 = write_world(tmp_path / "again", world())
    e2.run(ctx2)
    assert json.dumps(ctx2.registry.entries, sort_keys=True) == first
    assert ctx.registry.entries["e2.h5.stop.verdict"]["value"] == "not supported"
    assert ctx.registry.entries["e2.C4S.AD-stop.delivery_agree"]["value"] == 1.0
