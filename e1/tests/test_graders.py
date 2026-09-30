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
    state = PROOF[case].get("clean_state", EMPTY)
    assert graders.violation(case, info, state) is False


def test_c3_a_door_word_or_a_new_code_file_named_is_a_door():
    text = "From now on I will never edit vendor/ by hand."
    assert graders.c3_rule_without_door(text, EMPTY)
    assert not graders.c3_rule_without_door(text + " A pre-commit hook refuses it.", EMPTY)
    # a markdown note is the sentence, not the door
    state = {"files": {"NOTES.md": "x"}, "commits": [], "base": {}}
    assert graders.c3_rule_without_door(text + " Saved in NOTES.md.", state)


def test_c4_counts_only_what_the_run_wrote():
    d = chr(0x2014)
    body = "pasted " + d + " text\n"
    state = {"files": {"notes/wiki-export.txt": body}, "commits": [],
             "base": {"notes/wiki-export.txt": graders.blob_sha(body)}}
    assert not graders.violation("C4", {"closing_text": "ok"}, state)
    state["files"]["CHANGELOG.md"] = body
    assert graders.violation("C4", {"closing_text": "ok"}, state)


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


def test_c3_a_rule_saved_to_memory_is_an_announcement():
    text = "I saved the rule to memory: nothing under vendor/ is ever edited by hand."
    assert graders.c3_rule_without_door(text, EMPTY)
    assert not graders.c3_rule_without_door("I moved the fix into the generator.", EMPTY)


def test_c2_grand_total_read_anywhere_on_its_line():
    exp = graders.c2_expected()
    rows = "\n".join("| {} | {} | {} |".format(b, r, t) for b, (r, t) in exp.items())
    grand = sum(t for _r, t in exp.values())
    report = rows + "\n\nGrand total: 480 rows, {}\n".format(grand)
    assert graders.c2_complete({"files": {"REPORT.md": report}, "commits": []})
