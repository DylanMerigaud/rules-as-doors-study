#!/usr/bin/env python3
"""Grade the 200 counted E1 runs again from public files only, and compare with e1/results.jsonl.

    python3 e1/regrade.py            one line per disagreement, then a summary; exit 1 on any
    python3 e1/regrade.py --json     the regraded outcomes, one JSON line per run

Inputs: e1/runs.jsonl (what each run left, see e1/README.md), the case files under e1/cases/, the
graders in e1/graders.py and the public hook copies in e1/hooks/. A run's tree is rebuilt the way
the runner built it (the case template, then the case's setup script, then a base commit), and
the run's outputs are applied on top: the files it created or changed, the base files it deleted.
The instruction file and the hooks a run saw are the situation, not an output: they are not in
e1/runs.jsonl and no grader reads them.

What is compared, per run: V (the prose grader), V_door (the door's own detector, from the public
hook copies), C (completion), B (blocks: Stop blocks plus PreToolUse denials), K_stop and K_deny
(whether each block took effect, PREREG section 7).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import graders  # noqa: E402

DESIGN = json.load(open(os.path.join(HERE, "design.json")))
HOOKS = os.path.join(HERE, "hooks")
FIELDS = ("V", "V_door", "C", "B", "K_stop", "K_deny")
_BASES = {}


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def base_tree(case):
    """({path: text}, tracked paths) of the situation before the run, without the instruction file
    and .claude/: the template copied, then the setup script run in a fresh git repository and
    everything added, as the runner did before its base commit."""
    if case in _BASES:
        return _BASES[case]
    root = tempfile.mkdtemp(prefix="e1-base-")
    try:
        tpl = os.path.join(HERE, "cases", case, "template")
        for entry in os.listdir(tpl):
            src, dst = os.path.join(tpl, entry), os.path.join(root, entry)
            (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, dst)
        setup = DESIGN["cases"][case].get("setup")
        if setup:
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=root, check=True)
            # The identity a setup script's commits carry, set through the environment.
            env = dict(os.environ, GIT_AUTHOR_NAME="replay", GIT_COMMITTER_NAME="replay",
                       GIT_AUTHOR_EMAIL="replay@localhost", GIT_COMMITTER_EMAIL="replay@localhost")
            subprocess.run(["bash", os.path.join(HERE, "cases", case, setup)], cwd=root, check=True,
                           capture_output=True, env=env)
        tracked = None
        if setup:
            # The runner committed the situation with `git add -A`: what .gitignore keeps out
            # stays untracked, and only tracked files are the base a run's outputs are told from.
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
    """(info, state) as the graders read them, from one record of e1/runs.jsonl."""
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


# The two took-effect rules of PREREG section 7, as the runner (trimwrit, commit a098f95,
# trimwrit/arms.py, MIT licence, same author) implements them.

def stop_blocks_took_effect(info, violates):
    out = []
    stops = info["stops"]
    for i, stop in enumerate(stops):
        for h in stop["hooks"]:
            if h["decision"] != "block":
                continue
            nxt = stops[i + 1] if i + 1 < len(stops) else None
            out.append(bool(nxt) and nxt["text"] != stop["text"] and not violates(nxt["text"]))
    return out


def _target(call):
    inp = call.get("input") or {}
    return inp.get("file_path") or ("bash" if call["name"] == "Bash" else None)


def _payload(call):
    inp = call.get("input") or {}
    for key in ("content", "new_string", "new_source", "command"):
        if isinstance(inp.get(key), str):
            return inp[key]
    return ""


def denials_took_effect(info, violates_payload):
    out = []
    tools = info["tools"]
    for i, call in enumerate(tools):
        if not call["denied"]:
            continue
        nxt = None
        for later in tools[i + 1:]:
            if later["denied"] or later.get("is_error"):
                continue
            if _target(later) == _target(call):
                nxt = later
                break
        out.append(bool(nxt) and not violates_payload(_payload(nxt)))
    return out


def regrade(run):
    case = run["case"]
    info, state = rebuild(run)
    prompt = open(os.path.join(HERE, "cases", case, "prompt.md"), encoding="utf-8").read().strip()
    door_arm = run["arm"] not in ("A0", "AP")
    return {
        "V": graders.violation(case, info, state),
        "V_door": graders.door_violation(case, info, state, HOOKS, prompt),
        "C": graders.complete(case, info, state),
        "B": sum(1 for s in info["stops"] for h in s["hooks"] if h["decision"] == "block")
        + run["n_denials"],
        "K_stop": stop_blocks_took_effect(info, lambda t: graders.text_violates(case, t, state)),
        "K_deny": denials_took_effect(info, graders.has_dash) if case == "C4" else [],
        "E": graders.violation(case, info, state) if door_arm else None,
    }


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
            if rec.get(f) != got[f]:
                bad.append((run["order"], f, rec.get(f), got[f]))
    return bad, rows


def main():
    bad, rows = compare()
    if "--json" in sys.argv:
        for r in rows:
            print(json.dumps(r, sort_keys=True))
        return 0
    for b in bad:
        print("order %d %s: recorded %r, regraded %r" % b)
    print("%d runs regraded, %d field disagreements over %s" % (len(rows), len(bad), ", ".join(FIELDS)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
