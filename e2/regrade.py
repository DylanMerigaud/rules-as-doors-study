#!/usr/bin/env python3
"""Grade the 220 counted E2 runs again from public files only, and compare with e2/results.jsonl.

    python3 e2/regrade.py            one line per disagreement, then a summary; exit 1 on any
    python3 e2/regrade.py --json     the regraded outcomes, one JSON line per run

Inputs: e2/runs.jsonl (what each run left, see e2/README.md), the case files (E1's under
e1/cases/, C4S's prompt under e2/cases/), the graders in e2/graders.py (E1's, imported, except
where PREREG-E2 section 7 changes them) and the public hook copies in e2/hooks/. A run's tree is
rebuilt the way the runner built it (the case template, then the case's setup script, then a
base commit), and the run's outputs are applied on top: the files it created or changed, the base
files it deleted. The instruction file and the hooks a run saw are the situation, not an output:
they are not in e2/runs.jsonl and no grader reads them.

What is compared, per run (PREREG-E2 section 7): V (the prose grader), V_door (the door's own
detector, from the public hook copies), V_text, V_files and V_commits (C4 and C4S), C
(completion), B, B_stop and B_deny (refusals), K_stop and K_deny (whether each refusal took
effect, E1's rule), K_deny_strict (the write door's strict K), K_stop_door (K of a Stop door by its
own detector), E, the delivery check (stop_checks, stop_agree, stop_miss, stop_false_block), the
hooks' own health rows (hook_caps, hook_crashes, hook_timeouts), stop_attempts and tool_calls.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DESIGN = json.load(open(os.path.join(HERE, "design.json")))
HOOKS = os.path.join(HERE, "hooks")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


graders = _load("e2_graders_regrade", os.path.join(HERE, "graders.py"))
# E1's copies of the runner's two took-effect rules (trimwrit, MIT, same author); trimwrit's
# arms.py did not change them between E1's commit (a098f95) and E2's (0ab0b33).
e1_regrade = _load("e1_regrade_for_e2", os.path.join(ROOT, "e1", "regrade.py"))
stop_blocks_took_effect = e1_regrade.stop_blocks_took_effect
denials_took_effect = e1_regrade.denials_took_effect

FIELDS = ("V", "V_door", "V_text", "V_files", "V_commits", "C", "B", "B_stop", "B_deny",
          "K_stop", "K_deny", "K_deny_strict", "K_stop_door", "E", "stop_checks", "stop_agree",
          "stop_miss", "stop_false_block", "hook_caps", "hook_crashes", "hook_timeouts",
          "stop_attempts", "tool_calls")
_BASES = {}


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def case_paths(case):
    """(template dir, setup script or None, prompt) of a case, as e2/run_e2.py reads them."""
    spec = DESIGN["cases"][case]
    d = os.path.join(ROOT, spec["dir"])
    template = os.path.join(ROOT, spec["template"]) if spec.get("template") else \
        os.path.join(d, "template")
    setup = None
    if spec.get("setup_from"):
        setup = os.path.join(ROOT, spec["setup_from"])
    elif spec.get("setup"):
        setup = os.path.join(d, spec["setup"])
    with open(os.path.join(d, "prompt.md"), encoding="utf-8") as fh:
        prompt = fh.read().strip()
    return template, setup, prompt


def base_tree(case):
    """({path: text}, tracked paths) of the situation before the run, without the instruction file
    and .claude/: the template copied, then the setup script run in a fresh git repository and
    everything added, as the runner did before its base commit (e1/regrade.py, same steps)."""
    if case in _BASES:
        return _BASES[case]
    template, setup, _prompt = case_paths(case)
    root = tempfile.mkdtemp(prefix="e2-base-")
    try:
        for entry in os.listdir(template):
            if entry in ("__pycache__",) or entry.endswith(".pyc"):
                continue
            src, dst = os.path.join(template, entry), os.path.join(root, entry)
            if os.path.isdir(src):
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            else:
                shutil.copy2(src, dst)
        tracked = None
        if setup:
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=root, check=True)
            env = dict(os.environ, GIT_AUTHOR_NAME="replay", GIT_COMMITTER_NAME="replay",
                       GIT_AUTHOR_EMAIL="replay@localhost", GIT_COMMITTER_EMAIL="replay@localhost")
            subprocess.run(["bash", setup], cwd=root, check=True, capture_output=True, env=env)
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)
            ls = subprocess.run(["git", "ls-files", "-z"], cwd=root, check=True,
                                capture_output=True, text=True).stdout
            tracked = set(p for p in ls.split("\0") if p)
        files = {}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != ".git"]
            for f in filenames:
                p = os.path.join(dirpath, f)
                with open(p, encoding="utf-8", errors="replace") as fh:
                    files[os.path.relpath(p, root)] = fh.read()
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if tracked is None:
        tracked = set(files)
    _BASES[case] = (files, tracked)
    return _BASES[case]


def rebuild(run):
    """(info, state) as the graders read them, from one record of e2/runs.jsonl."""
    base, tracked = base_tree(run["case"])
    files = {p: t for p, t in base.items() if p not in run["deleted"]}
    files.update(run["output_files"])
    state = {"files": files,
             "base": {p: graders.blob_sha(t) for p, t in base.items() if p in tracked},
             "commits": [{"message": c["text"]} for c in run["commits"]],
             "branches": run["branches"]}
    texts = run["texts"]
    stops = [{"text": texts[s["text_index"]] if s["text_index"] is not None else "",
              "hooks": [{"decision": d} for d in s["decisions"]]} for s in run["stops"]]
    tools = []
    for c in run.get("write_calls") or []:
        key = {"Write": "content", "Edit": "new_string", "NotebookEdit": "new_source",
               "Bash": "command"}[c["tool"]]
        inp = {key: c["payload"]}
        if c["tool"] != "Bash":
            inp["file_path"] = c["target"]
        tools.append({"name": c["tool"], "input": inp, "denied": c["denied"],
                      "is_error": c["is_error"]})
    info = {"closing_text": run["closing_text"], "stops": stops, "tools": tools,
            "denials": [{}] * run["n_denials"]}
    return info, state


def is_door_arm(arm):
    return arm.startswith("AD") or arm.startswith("APD")


def regrade(run):
    """Every measure e2/run_e2.py `grade` records, from one public run record."""
    case, arm = run["case"], run["arm"]
    info, state = rebuild(run)
    _t, _s, prompt = case_paths(case)
    door = is_door_arm(arm)
    v = graders.violation(case, info, state)
    k_deny = denials_took_effect(info, graders.has_dash) if case == "C4" else []
    b_stop = sum(1 for s in info["stops"] for h in s["hooks"] if h["decision"] == "block")
    out = {
        "V": v,
        "V_door": graders.door_violation(case, info, state, HOOKS, prompt),
        "B": b_stop + run["n_denials"],
        "B_stop": b_stop,
        "B_deny": run["n_denials"],
        "K_stop": stop_blocks_took_effect(info, lambda t: graders.text_violates(case, t, state)),
        "K_deny": k_deny,
        "K_deny_strict": graders.k_deny_strict(k_deny, state) if case == "C4" else [],
        "E": v if door else None,
        "C": graders.complete(case, info, state),
        "stop_attempts": len(info["stops"]),
        "tool_calls": run["n_tool_calls"],
    }
    out.update(graders.violation_parts(case, info, state))
    if door:
        det = graders.stop_detector(case, HOOKS, prompt)
        if det is not None:
            checks = [(bool(det(s["text"])), h["decision"] == "block")
                      for s in info["stops"] for h in s["hooks"]]
            out.update({"stop_checks": len(checks),
                        "stop_agree": sum(1 for d, b in checks if d == b),
                        "stop_miss": sum(1 for d, b in checks if d and not b),
                        "stop_false_block": sum(1 for d, b in checks if b and not d)})
        out["K_stop_door"] = stop_blocks_took_effect(info, det) if det else []
        health = run.get("hook_health") or {}
        out.update({"hook_caps": health.get("cap", 0), "hook_crashes": health.get("crash", 0),
                    "hook_timeouts": health.get("timeout", 0)})
    return out


def compare(runs_path=None, results_path=None):
    """[(order, field, recorded, regraded)] for every disagreement, and the regraded rows."""
    runs = read_jsonl(runs_path or os.path.join(HERE, "runs.jsonl"))
    results = {r["order"]: r for r in read_jsonl(results_path or os.path.join(HERE, "results.jsonl"))
               if r.get("counted") and not r.get("void")}
    bad, rows = [], []
    for run in runs:
        got = regrade(run)
        rows.append(dict(order=run["order"], case=run["case"], arm=run["arm"],
                         run_index=run["run_index"], **got))
        rec = results[run["order"]]
        for f in FIELDS:
            if (f in rec or f in got) and rec.get(f) != got.get(f):
                bad.append((run["order"], f, rec.get(f), got.get(f)))
    missing = sorted(set(results) - {r["order"] for r in runs})
    for o in missing:
        bad.append((o, "record", "counted", "absent from runs.jsonl"))
    return bad, rows


def main():
    bad, rows = compare()
    if "--json" in sys.argv:
        for r in rows:
            print(json.dumps(r, sort_keys=True))
        return 0
    for b in bad:
        print("order %s %s: recorded %r, regraded %r" % b)
    print("%d runs regraded, %d field disagreements over %s" % (len(rows), len(bad), ", ".join(FIELDS)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
