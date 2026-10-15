"""E2's driver: the design it reads, the order it draws, the runs it voids (no model is called)."""
import csv
import importlib.util
import json
import os
import sys

E2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(E2)


def _load():
    spec = importlib.util.spec_from_file_location("e2_driver_test", os.path.join(E2, "run_e2.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["e2_driver_test"] = mod
    spec.loader.exec_module(mod)
    return mod


drv = _load()


def test_the_design_has_22_cells_and_220_runs():
    cells = drv.cells()
    assert len(cells) == 22
    assert len(cells) * drv.DESIGN["runs_per_cell"] == 220
    by_case = {}
    for c, a in cells:
        by_case.setdefault(c, []).append(a)
    assert by_case["C4"] == ["A0", "AP", "AD-write", "APD-write"]
    assert by_case["C4S"] == ["A0", "AP", "AD-stop", "APD-stop"]
    assert by_case["C5"] == ["A0", "AP"]
    for c in ("C1", "C2", "C3"):
        assert by_case[c] == ["A0", "AP", "AD", "APD"]


def test_every_hook_command_carries_home_and_c1_has_no_question_hook():
    for case in drv.DESIGN["cases"]:
        for arm, (_prose, regs) in drv.arms_of(case).items():
            for reg in regs:
                assert reg["args"][-2:] == drv.DESIGN["home_args"], (case, arm)
                assert reg["script"] in drv.DESIGN["cases"][case]["hook_files"]
                assert "hook_trace.py" in drv.DESIGN["cases"][case]["hook_files"]
    c1 = drv.arms_of("C1")["AD"][1]
    assert [r["event"] for r in c1] == ["Stop"]
    assert drv.arms_of("C2")["AD"][1][0]["args"][0] == "--prompt"


def test_the_prose_arms_and_the_ablated_lines_are_e1s():
    e1 = json.load(open(os.path.join(ROOT, "e1", "design.json")))
    assert drv.DESIGN["instruction_sha256"] == e1["instruction_sha256"]
    for case in ("C1", "C2", "C3", "C4", "C5"):
        assert drv.DESIGN["cases"][case]["ablate"] == e1["cases"][case]["ablate"]
    assert drv.DESIGN["cases"]["C4S"]["ablate"] == e1["cases"]["C4"]["ablate"]
    assert drv.DESIGN["model"] == e1["model"] == "claude-opus-5-5"


def test_each_case_resolves_its_situation():
    for case in drv.DESIGN["cases"]:
        template, setup, prompt = drv.case_paths(case)
        assert os.path.isdir(template) and prompt
        if setup:
            assert os.path.isfile(setup)
    template, setup, _p = drv.case_paths("C4S")
    assert template.endswith(os.path.join("e1", "cases", "C4", "template"))
    assert setup.endswith(os.path.join("e1", "cases", "C4", "setup.sh"))


def test_the_committed_order_is_the_seeded_draw(tmp_path, monkeypatch):
    if not os.path.exists(drv.ORDER):
        return
    monkeypatch.setattr(drv, "ORDER", str(tmp_path / "order.csv"))
    drv.cmd_order(None)
    with open(drv.ORDER) as fh:
        fresh = list(csv.reader(fh))
    with open(os.path.join(E2, "run_order.csv")) as fh:
        committed = list(csv.reader(fh))
    assert fresh == committed and len(fresh) == 221


def test_a_run_that_dies_on_an_api_error_is_void():
    base = {"model": "claude-opus-5-5", "exit_code": 1, "stderr_tail": ""}
    assert drv.void_reason(dict(base, is_error=True, api_error_status=529,
                                result="API Error: overloaded")).startswith("api error")
    assert drv.void_reason(dict(base, is_error=True, api_error_status=429,
                                result="usage limit")).startswith("quota")
    assert drv.void_reason({"model": None, "exit_code": 1}).startswith("no model turn")
    assert drv.void_reason(dict(base, is_error=False, result="done")) is None


def test_a_voided_row_is_run_again_at_the_end_and_at_most_four_times(tmp_path, monkeypatch):
    order = tmp_path / "order.csv"
    order.write_text("order,case,arm,run_index\n0,C1,A0,0\n1,C1,AP,0\n2,C5,A0,0\n")
    res = tmp_path / "results.jsonl"
    rows = [{"order": 0, "counted": True, "void": "api error: 529"},
            {"order": 1, "counted": True, "void": None}]
    rows += [{"order": 2, "counted": True, "void": "api error: 500"}] * 4
    res.write_text("".join(json.dumps(r) + "\n" for r in rows))
    monkeypatch.setattr(drv, "ORDER", str(order))
    monkeypatch.setattr(drv, "RESULTS", str(res))
    assert [r["order"] for r in drv.todo_rows()] == ["0"]
    res.write_text("")
    assert [r["order"] for r in drv.todo_rows()] == ["0", "1", "2"]
