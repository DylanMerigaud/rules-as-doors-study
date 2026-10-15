"""E2's public hook copies (`e2/hooks/`): the detectors are E1's, the delivery is the repaired one.

E2 manipulates how a door refuses, never what it detects. These tests pin both halves on the
public copies: the detectors give E1's public detectors' answer on every E1 run text and every
case prompt, and the delivery behaves as PREREG-E2 section 4 says (a Stop block that Claude Code
honours, the re-answer of a stop chain checked, a cap after CHAIN_CAP blocks in a row, a crash
recorded rather than silent, every write under `--home`)."""
import ast
import importlib.util
import json
import os
import re
import subprocess
import sys

import pytest

E2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(E2)
HOOKS = os.path.join(E2, "hooks")
E1_HOOKS = os.path.join(ROOT, "e1", "hooks")
NAMES = ("stop_ask_gate.py", "stop_promise_gate.py", "stop_rule_gate.py", "hook_bounds.py",
         "hook_trace.py", "no-em-dash.py", "no-em-dash-write.py")
EM = chr(0x2014)


def load(d, name, tag):
    sys.path.insert(0, d)
    saved = {m: sys.modules.pop(m) for m in ("hook_bounds", "hook_trace") if m in sys.modules}
    try:
        spec = importlib.util.spec_from_file_location(tag + re.sub(r"\W", "_", name),
                                                      os.path.join(d, name))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.pop(0)
        for m in ("hook_bounds", "hook_trace"):
            sys.modules.pop(m, None)
        sys.modules.update(saved)


@pytest.mark.parametrize("name", NAMES)
def test_every_public_copy_imports(name):
    load(HOOKS, name, "e2pub_")


@pytest.mark.parametrize("name", NAMES)
def test_every_redaction_is_marked(name):
    lines = open(os.path.join(HOOKS, name), encoding="utf-8").read().split("\n")
    for i, line in enumerate(lines):
        if "(?!x)x" in line:
            assert any("REDACTED H" in x or "REDACTED J" in x
                       for x in lines[max(0, i - 4):i + 1]), line


# ---------------------------------------------------------------- the detectors are E1's

def corpus():
    texts = []
    with open(os.path.join(ROOT, "e1", "runs.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            texts += [t for t in (r.get("texts") or []) if t]
            if r.get("closing_text"):
                texts.append(r["closing_text"])
    for c in ("C1", "C2", "C3", "C4", "C5"):
        texts.append(open(os.path.join(ROOT, "e1", "cases", c, "prompt.md")).read())
    texts.append(open(os.path.join(E2, "cases", "C4S", "prompt.md")).read())
    return texts


DETECTORS = [("stop_ask_gate.py", "ask_without_class"), ("stop_promise_gate.py", "promise_in"),
             ("stop_promise_gate.py", "target_in"), ("stop_rule_gate.py", "rule_without_door"),
             ("no-em-dash.py", "offenders"), ("no-em-dash-write.py", "scan")]


@pytest.mark.parametrize("name,fn", DETECTORS)
def test_each_detector_answers_as_e1s_on_every_e1_text(name, fn):
    e2 = getattr(load(HOOKS, name, "e2pub_"), fn)
    e1 = getattr(load(E1_HOOKS, name, "e1pub_"), fn)
    args = (lambda t: (t, None)) if fn == "rule_without_door" else (lambda t: (t,))
    texts = corpus()
    assert len(texts) > 500
    assert [e2(*args(t)) for t in texts] == [e1(*args(t)) for t in texts]


# ---------------------------------------------------------------- the delivery is the repaired one

def run_hook(name, payload, home, *extra):
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "CLAUDE_PROJECT_DIR": str(home)}
    return subprocess.run([sys.executable, os.path.join(HOOKS, name), *extra, "--home", str(home)],
                          input=payload if isinstance(payload, str) else json.dumps(payload),
                          capture_output=True, text=True, env=env, cwd=str(home), timeout=60)


def stop(msg, active=False, sid="s1"):
    return {"hook_event_name": "Stop", "session_id": sid, "stop_hook_active": active,
            "last_assistant_message": msg, "transcript_path": ""}


def decision(r):
    out = r.stdout.strip()
    return json.loads(out).get("decision") if out.startswith("{") else None


GATES = {"stop_ask_gate.py": ("Done. Should I also delete the old branch?",
                              "Done, the old branch is deleted."),
         "stop_rule_gate.py": ("From now on, every release must carry a changelog entry.",
                               "The release is tagged and its changelog entry written."),
         "stop_promise_gate.py": ("Batches 1 to 3 are done. I'll continue with the next batch.",
                                  "All twelve batches are done and REPORT.md is filled in.")}


def arm(home, sid="s1"):
    r = run_hook("stop_promise_gate.py", {"hook_event_name": "UserPromptSubmit", "session_id": sid,
                                          "prompt": "Process every batch and never stop before "
                                                    "the report is complete."}, home, "--prompt")
    assert r.returncode == 0


@pytest.mark.parametrize("name", sorted(GATES))
def test_a_stop_gate_blocks_with_a_top_level_decision_and_checks_the_re_answer(name, tmp_path):
    bad, good = GATES[name]
    if name == "stop_promise_gate.py":
        arm(tmp_path)
    first = run_hook(name, stop(bad), tmp_path)
    assert first.returncode == 0 and decision(first) == "block"
    # the re-answer of the same stop chain is checked like the first answer
    again = run_hook(name, stop(bad, active=True), tmp_path)
    assert decision(again) == "block"
    fixed = run_hook(name, stop(good, active=True), tmp_path)
    assert fixed.returncode == 0 and fixed.stdout.strip() == ""


def test_the_long_dash_stop_hook_blocks_by_exit_code_2(tmp_path):
    r = run_hook("no-em-dash.py", stop("All done " + EM + " nothing left."), tmp_path)
    assert r.returncode == 2 and "forbidden dash" in r.stderr and r.stdout.strip() == ""
    again = run_hook("no-em-dash.py", stop("Still " + EM + " here.", active=True), tmp_path)
    assert again.returncode == 2
    ok = run_hook("no-em-dash.py", stop("All done, nothing left.", active=True), tmp_path)
    assert ok.returncode == 0 and ok.stderr.strip() == ""


def test_the_stop_hook_reads_the_payload_text_not_the_transcript(tmp_path):
    tr = tmp_path / "t.jsonl"
    earlier = {"content": [{"type": "text", "text": "Should I also delete the old branch?"}]}
    record = {"type": "assistant"}
    # The earlier answer goes under its usual key.
    record["message"] = earlier
    tr.write_text(json.dumps(record) + "\n")
    p = stop("Done, the old branch is deleted.")
    p["transcript_path"] = str(tr)
    r = run_hook("stop_ask_gate.py", p, tmp_path)
    assert decision(r) is None


@pytest.mark.parametrize("name", sorted(GATES) + ["no-em-dash.py"])
def test_a_gate_lets_go_after_chain_cap_blocks_in_a_row_and_records_it(name, tmp_path):
    bad = GATES[name][0] if name in GATES else "Done " + EM + " really."
    if name == "stop_promise_gate.py":
        arm(tmp_path)
    cap = load(HOOKS, "hook_trace.py", "e2pub_").CHAIN_CAP
    assert cap == 3

    def blocked(r):
        return decision(r) == "block" or r.returncode == 2

    results = [run_hook(name, stop(bad, active=(i > 0)), tmp_path) for i in range(cap + 1)]
    assert [blocked(r) for r in results] == [True] * cap + [False]
    assert "systemMessage" in results[-1].stdout
    rows = [json.loads(x) for x in (tmp_path / "hook-health.jsonl").read_text().splitlines()]
    assert [r["outcome"] for r in rows] == ["cap"]
    # a new stop chain starts from zero
    assert blocked(run_hook(name, stop(bad, active=False), tmp_path))


def test_a_crash_lets_the_turn_end_and_is_recorded(tmp_path):
    r = run_hook("stop_ask_gate.py", "[1, 2]", tmp_path)
    assert r.returncode == 0 and "systemMessage" in r.stdout
    rows = [json.loads(x) for x in (tmp_path / "hook-health.jsonl").read_text().splitlines()]
    assert rows[-1]["outcome"] == "crash"
    assert rows[-1]["autofix"].startswith("autofix absent")


def test_the_write_door_denies_a_dash_in_content(tmp_path):
    p = {"hook_event_name": "PreToolUse", "session_id": "s", "tool_name": "Write",
         "tool_input": {"file_path": str(tmp_path / "x.md"), "content": "a " + EM + " b"}}
    r = run_hook("no-em-dash-write.py", p, tmp_path)
    spec = json.loads(r.stdout)["hookSpecificOutput"]
    assert r.returncode == 0 and spec["permissionDecision"] == "deny"
    p["tool_input"]["content"] = "a, b"
    assert run_hook("no-em-dash-write.py", p, tmp_path).stdout.strip() == ""


def test_home_is_read_only_where_a_path_is_chosen():
    """`--home` (every E2 hook command passes it) changes where state and ledgers are written,
    never a decision: the module global it sets is read only by the path functions."""
    tree = ast.parse(open(os.path.join(HOOKS, "hook_trace.py"), encoding="utf-8").read())
    readers = set()
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef):
            for node in ast.walk(fn):
                if isinstance(node, ast.Name) and node.id == "_HOME":
                    readers.add(fn.name)
    assert readers == {"configure", "home", "ledger_path", "state_dir", "autofix_script",
                       "door_ledger_script"}
    bounds = open(os.path.join(HOOKS, "hook_bounds.py"), encoding="utf-8").read()
    # hook_bounds reads home() once, to pick which door ledger script witnesses a refusal
    assert bounds.count("hook_trace.home()") == 1
    for name in ("stop_ask_gate.py", "stop_promise_gate.py", "stop_rule_gate.py",
                 "no-em-dash.py", "no-em-dash-write.py"):
        src = open(os.path.join(HOOKS, name), encoding="utf-8").read()
        assert "home()" not in src and "_HOME" not in src, name
