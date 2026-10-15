"""C1's corrected prose grader on the E1 runs the registered grader misread (review round 2, R3-R1
and R1-R02). E1's registered numbers are never regraded in place; this only shows what the
correction changes, before E2 is registered."""
import importlib.util
import json
import os
import sys

E2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(E2)


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
RUNS = [json.loads(line) for line in open(os.path.join(ROOT, "e1", "runs.jsonl"), encoding="utf-8")
        if line.strip()]
C1_RUNS = {r["order"]: r for r in RUNS if r["case"] == "C1"}


def test_the_nine_misread_runs_are_flagged_by_e1_and_not_by_the_correction():
    orders = PROOF["C1"]["e1_orders_misread"]
    assert len(orders) == 9
    for o in orders:
        text = C1_RUNS[o]["closing_text"]
        assert graders.e1.c1_asks(text) is True, o
        assert graders.c1_asks(text) is False, o


def test_e1_flagged_exactly_those_nine():
    flagged = sorted(o for o, r in C1_RUNS.items() if graders.e1.c1_asks(r["closing_text"]))
    assert flagged == sorted(PROOF["C1"]["e1_orders_misread"])


def test_the_correction_flags_no_e1_closing_text_of_c1():
    assert len(C1_RUNS) == 40
    assert not [o for o, r in C1_RUNS.items() if graders.c1_asks(r["closing_text"])]


def test_the_correction_still_fires_on_real_run_texts():
    # it is not a grader that can never fire: across every text of every E1 run (not only
    # closing texts, and not only C1's), it flags the ones that ask for the operator's go
    hits = [r["order"] for r in RUNS for t in r["texts"] if graders.c1_asks(t)]
    assert hits
