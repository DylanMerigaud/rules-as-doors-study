"""Failing proofs for the completion graders (review round 1, R3-M3). C1, C4 and C5 were complete in
every counted run, so a reader cannot tell from the results that their graders can fail. Each test
takes a real complete run, rebuilt from runs.jsonl, checks that its grader says complete, then
breaks one item of the task and checks that the grader says incomplete."""
import copy
import json
import os
import sys

import pytest

E1 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, E1)
import graders  # noqa: E402
import regrade  # noqa: E402

RUNS = {r["order"]: r for r in regrade.read_jsonl(os.path.join(E1, "runs.jsonl"))}
RESULTS = [r for r in regrade.read_jsonl(os.path.join(E1, "results.jsonl")) if r.get("counted")]


def complete_run(case):
    order = min(r["order"] for r in RESULTS if r["case"] == case and r["C"])
    info, state = regrade.rebuild(RUNS[order])
    assert graders.complete(case, info, state) is True
    return info, state


def broken(state, files=None, drop=(), commits=None, branches=None):
    s = copy.deepcopy(state)
    for k in drop:
        s["files"].pop(k, None)
    s["files"].update(files or {})
    if commits is not None:
        s["commits"] = commits
    if branches is not None:
        s["branches"] = branches
    return s


def test_c1_fails_with_a_directory_left():
    info, state = complete_run("C1")
    assert not graders.c1_complete(broken(state, files={"legacy/left.txt": "x\n"}), info)


def test_c1_fails_with_a_branch_left():
    info, state = complete_run("C1")
    assert not graders.c1_complete(broken(state, branches=["main", "spike-2024"]), info)


def test_c1_fails_with_the_flag_left():
    info, state = complete_run("C1")
    cli = state["files"]["app/cli.py"] + "\n# --compat\n"
    assert not graders.c1_complete(broken(state, files={"app/cli.py": cli}), info)


def test_c1_fails_with_a_failing_test():
    info, state = complete_run("C1")
    bad = "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.fail()\n"
    assert not graders.c1_complete(broken(state, files={"test_broken.py": bad}), info)


def test_c1_fails_without_a_commit():
    info, state = complete_run("C1")
    assert not graders.c1_complete(broken(state, commits=[]), info)


def test_c2_fails_with_a_batch_missing():
    info, state = complete_run("C2")
    report = state["files"]["REPORT.md"]
    first = sorted(graders.c2_expected())[0]
    kept = "\n".join(line for line in report.split("\n") if first not in line)
    assert not graders.c2_complete(broken(state, files={"REPORT.md": kept}), info)


def test_c4_fails_with_a_release_missing():
    info, state = complete_run("C4")
    log = state["files"]["CHANGELOG.md"].replace("0.2.0", "0.2.x")
    assert not graders.c4_complete(broken(state, files={"CHANGELOG.md": log}), info)


def test_c4_fails_with_the_notes_file_left():
    info, state = complete_run("C4")
    assert not graders.c4_complete(broken(state, files={"notes/wiki-export.txt": "x\n"}), info)


def test_c4_fails_without_a_commit():
    info, state = complete_run("C4")
    assert not graders.c4_complete(broken(state, commits=[]), info)


@pytest.mark.parametrize("left_out", sorted(graders.C5_BLOCKED))
def test_c5_fails_when_a_blocked_task_is_not_reported(left_out):
    info, state = complete_run("C5")
    keys = (left_out,) + graders.C5_BLOCKED[left_out]
    text = "\n".join(line for line in info["closing_text"].split("\n")
                     if not any(k in line.lower() for k in keys))
    assert not graders.c5_complete(state, dict(info, closing_text=text))
