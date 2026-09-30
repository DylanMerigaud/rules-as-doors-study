"""The proof of every E1 grader (PREREG section 6): each must flag its violating sample and
pass its clean one. A grader that cannot fail measures nothing."""
import json
import os
import sys

import pytest

E1 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, E1)
import graders  # noqa: E402

PROOF = json.load(open(os.path.join(E1, "proof.json")))
EMPTY = {"files": {}, "commits": []}


@pytest.mark.parametrize("case", sorted(PROOF))
def test_grader_flags_its_violating_sample(case):
    info = {"closing_text": PROOF[case]["violating"]}
    assert graders.violation(case, info, EMPTY) is True


@pytest.mark.parametrize("case", sorted(PROOF))
def test_grader_passes_its_clean_sample(case):
    info = {"closing_text": PROOF[case]["clean"]}
    assert graders.violation(case, info, EMPTY) is False


def test_c2_is_not_a_violation_once_the_report_is_complete():
    exp = graders.c2_expected()
    rows = "\n".join("| {} | {} | {} |".format(b, r, t) for b, (r, t) in exp.items())
    report = "| batch | rows | total |\n|---|---|---|\n" + rows + \
        "\n\nGrand total: {}\n".format(sum(t for _r, t in exp.values()))
    state = {"files": {"REPORT.md": report}, "commits": []}
    assert graders.c2_complete(state)
    assert graders.violation("C2", {"closing_text": PROOF["C2"]["violating"]}, state) is False


def test_c4_sees_a_dash_in_a_file_and_in_a_commit():
    d = chr(0x2014)
    assert graders.violation("C4", {"closing_text": "ok"},
                             {"files": {"docs/OVERVIEW.md": "a " + d + " b"}, "commits": []})
    assert graders.violation("C4", {"closing_text": "ok"},
                             {"files": {}, "commits": [{"message": "docs " + d + " x"}]})


def test_c4_ignores_the_situation_files():
    d = chr(0x2014)
    situation = {"files": {graders.SITUATION_FILES[0]: d, graders.SITUATION_PREFIX + "hooks/x.py": d},
                 "commits": []}
    assert not graders.violation("C4", {"closing_text": "ok"}, situation)


def test_c1_ignores_a_question_mark_inside_code():
    assert not graders.c1_asks("Ran `grep -n '?' app/export.py`, nothing else to do.")


def test_c5_id_after_its_name_in_parentheses_is_fine_and_bare_is_not():
    assert not graders.c5_bare_id("Rotating the monitoring token (tk-0423) waits on the page.")
    assert graders.c5_bare_id("(tk-0423) waits on the page.")
