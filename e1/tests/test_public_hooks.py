"""The public copies of the pinned hooks (review round 1, R3 B1). A redacted alternative is the
pattern (?!x)x, which never matches; the detectors still work on English text; and the copies
reproduce what the pinned hooks did in E1."""
import importlib.util
import json
import os
import re
import sys

import pytest

E1 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(E1, "hooks")
NAMES = ("stop_ask_gate.py", "stop_promise_gate.py", "stop_rule_gate.py", "hook_bounds.py",
         "no-em-dash.py", "no-em-dash-write.py", "ask_question_gate.py")


def load(name):
    sys.path.insert(0, HOOKS)
    try:
        spec = importlib.util.spec_from_file_location("pub_" + re.sub(r"\W", "_", name), os.path.join(HOOKS, name))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.pop(0)


@pytest.mark.parametrize("name", NAMES)
def test_every_public_copy_imports(name):
    load(name)


def test_the_placeholder_never_matches():
    never = re.compile(r"(?!x)x")
    for s in ("", "x", "xx", "(?!x)x", "never stop " * 50):
        assert never.search(s) is None


@pytest.mark.parametrize("name", NAMES)
def test_every_redaction_is_marked(name):
    text = open(os.path.join(HOOKS, name), encoding="utf-8").read()
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "(?!x)x" in line:
            # the marker sits on the line or on the comment block just above it
            assert any("REDACTED H" in x for x in lines[max(0, i - 4):i + 1]), line


def test_ask_detector_on_english():
    ask = load("stop_ask_gate.py")
    assert ask.ask_without_class("Done. Should I also delete the old branch?")
    assert not ask.ask_without_class("Done. Should I also delete the old branch? (irreversible)")
    assert not ask.ask_without_class("Done. Both branches are deleted and the tests pass.")


def test_promise_detector_on_english():
    p = load("stop_promise_gate.py")
    assert p.target_in("Process every batch and never stop before the report is complete.")
    assert p.promise_in("Batches 1 to 3 are done. I'll continue with the next batch.")
    assert not p.promise_in("All six batches are in REPORT.md.")


def test_rule_detector_on_english():
    r = load("stop_rule_gate.py")
    assert r.rule_without_door("Fixed. From now on, never edit vendor/ by hand.", None)
    assert not r.rule_without_door("Fixed the generator and regenerated the table.", None)


def test_dash_detectors():
    d = chr(0x2014)
    stop, write = load("no-em-dash.py"), load("no-em-dash-write.py")
    assert stop.offenders("a " + d + " b")
    assert not stop.offenders("a - b")
    assert write.scan("a " + d + " b")
    assert write.payload_text("Write", {"content": "x", "file_path": "y"}) == "x"


def test_c2_stop_hook_judged_the_text_before_the_closing_text():
    """The pinned promise gate read the transcript, which did not yet hold the closing text: its
    decision at every stop attempt equals its detector on the PREVIOUS text of the run."""
    p = load("stop_promise_gate.py")
    prompt = open(os.path.join(E1, "cases", "C2", "prompt.md"), encoding="utf-8").read().strip()
    armed = bool(p.target_in(prompt))
    n = ok = 0
    with open(os.path.join(E1, "runs.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["case"] != "C2" or r["arm"] not in ("AD", "APD"):
                continue
            for s in r["stops"]:
                i = s["text_index"]
                prev = r["texts"][i - 1] if i else ""
                block = any(d == "block" for d in s["decisions"])
                n += 1
                ok += int(block == (armed and bool(p.promise_in(prev))))
    assert n == 22 and ok == 22
