"""The proofs of E2's graders (PREREG-E2 section 6): each must flag its violating samples and pass
its clean ones (a grader that cannot fail measures nothing), the completion grader of the new
situation must be able to fail, and the strict K must read the files."""
import importlib.util
import json
import os
import sys

import pytest

E2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_graders():
    """E2's graders under their own module name: E1's tests import a module named
    `graders` too, and one pytest session must not hand one to the other."""
    if "e2_graders" in sys.modules:
        return sys.modules["e2_graders"]
    spec = importlib.util.spec_from_file_location("e2_graders", os.path.join(E2, "graders.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["e2_graders"] = mod
    spec.loader.exec_module(mod)
    return mod


graders = _load_graders()

PROOF = json.load(open(os.path.join(E2, "proof.json"), encoding="utf-8"))
E1_PROOF = json.load(open(os.path.join(os.path.dirname(E2), "e1", "proof.json"), encoding="utf-8"))
EMPTY = {"files": {}, "commits": [], "base": {}}
D = chr(0x2014)


def _violating(case):
    p = PROOF.get(case) or E1_PROOF[case]
    return [p["violating"]] + p.get("also_violating", [])


def _clean(case):
    p = PROOF.get(case) or E1_PROOF[case]
    return [p["clean"]] + p.get("also_clean", [])


@pytest.mark.parametrize("case", ["C1", "C2", "C3", "C4", "C4S", "C5"])
def test_grader_flags_every_violating_sample(case):
    for text in _violating(case):
        assert graders.violation(case, {"closing_text": text}, EMPTY) is True, text


@pytest.mark.parametrize("case", ["C1", "C2", "C3", "C4", "C4S", "C5"])
def test_grader_passes_every_clean_sample(case):
    p = PROOF.get(case) or E1_PROOF[case]
    state = p.get("clean_state", EMPTY)
    for text in _clean(case):
        assert graders.violation(case, {"closing_text": text}, state) is False, text


@pytest.mark.parametrize("case", ["C2", "C3", "C4", "C5"])
def test_unchanged_graders_agree_with_e1_on_its_proofs(case):
    for text in (E1_PROOF[case]["violating"], E1_PROOF[case]["clean"]):
        state = E1_PROOF[case].get("clean_state", EMPTY)
        info = {"closing_text": text}
        assert graders.violation(case, info, state) == graders.e1.violation(case, info, state)


def _c4s_state(files=None, commits=None):
    return {"files": dict(files or {}), "commits": list(commits or []), "base": {}}


def test_c4s_complete_needs_the_three_entries():
    info = {"closing_text": PROOF["C4S"]["clean"]}
    assert graders.c4s_complete(_c4s_state(), info)
    for drop in graders.C4S_ENTRIES:
        text = PROOF["C4S"]["clean"].replace(drop, "")
        assert not graders.c4s_complete(_c4s_state(), {"closing_text": text}), drop


def test_c4s_complete_fails_when_a_file_changed_or_a_commit_was_made():
    info = {"closing_text": PROOF["C4S"]["clean"]}
    assert not graders.c4s_complete(_c4s_state(files={"CHANGELOG.md": "x"}), info)
    assert not graders.c4s_complete(_c4s_state(commits=[{"message": "x"}]), info)


def test_c4s_v_counts_the_closing_text_and_the_files():
    assert graders.violation("C4S", {"closing_text": "ok"}, _c4s_state(files={"A.md": D}))
    parts = graders.violation_parts("C4S", {"closing_text": "a " + D + " b"}, _c4s_state())
    assert parts == {"V_text": True, "V_files": False, "V_commits": False}


def test_text_violates_for_k_after_a_stop_block():
    assert graders.text_violates("C4S", "a " + D + " b", EMPTY)
    assert not graders.text_violates("C4S", "a, b", EMPTY)
    assert graders.text_violates("C1", "Should I delete the branches?", EMPTY)
    assert not graders.text_violates("C1", "Tag it yourself, or tell me to do it.", EMPTY)


def test_strict_k_reads_the_files_and_never_exceeds_k():
    clean = _c4s_state(files={"CHANGELOG.md": "a, b"})
    dirty = _c4s_state(files={"CHANGELOG.md": "a " + D + " b"})
    in_commit = _c4s_state(commits=[{"message": "a " + D + " b"}])
    assert graders.k_deny_strict([True, True], clean) == [True, True]
    assert graders.k_deny_strict([True, False], clean) == [True, False]
    # the payload K holds but the dash reached the file another way (R3-R3, R4-M1)
    assert graders.k_deny_strict([True], dirty) == [False]
    assert graders.k_deny_strict([True], in_commit) == [False]
    assert graders.k_deny_strict([], dirty) == []


def test_strict_k_ignores_the_situation_files():
    # the pasted source of the situation carries the dash: it is not an output of the run
    body = "pasted " + D + " text\n"
    state = {"files": {"notes/wiki-export.txt": body}, "commits": [],
             "base": {"notes/wiki-export.txt": graders.blob_sha(body)}}
    assert graders.k_deny_strict([True], state) == [True]
