#!/usr/bin/env python3
"""Drive E1 (PREREG sections 4 to 7) through trimwrit's arms runner.

    python3 e1/run_e1.py order                      write e1/run_order.csv (once, before any run)
    python3 e1/run_e1.py pilot C1 [--n 3]           uncounted A0 runs of one case
    python3 e1/run_e1.py batch [--n 20] [--jobs 4]  the next counted runs of the order
    python3 e1/run_e1.py status                     runs per cell

Private inputs come from the environment, never from this file: E1_CONTEXT (the pinned
instruction file and hook copies), E1_RAW (where raw run files go, never published), E1_HUB (the
harness whose model-quota door gates every batch), TRIMWRIT (the runner's checkout), E1_TOKEN_FILE
(a subscription credential; an API key is never used). Results without any text go to
e1/results.jsonl.
"""
import argparse
import concurrent.futures
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import graders  # noqa: E402

DESIGN = json.load(open(os.path.join(HERE, "design.json")))
ORDER = os.path.join(HERE, "run_order.csv")
RESULTS = os.path.join(HERE, "results.jsonl")
PILOT_NAME = "pilot.jsonl"
LOCK = threading.Lock()


def env(name):
    val = os.environ.get(name)
    if not val:
        sys.exit("set {}".format(name))
    return val


def trimwrit():
    tw = env("TRIMWRIT")
    if tw not in sys.path:
        sys.path.insert(0, tw)
    from trimwrit import arms
    commit = subprocess.run(["git", "-C", tw, "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    return arms, commit


def arms_of(case):
    doors = DESIGN["cases"][case]["doors"]
    out = {"A0": (False, []), "AP": (True, [])}
    for name, regs in doors.items():
        suffix = "" if name == "door" else "-" + name
        out["AD" + suffix] = (False, regs)
        out["APD" + suffix] = (True, regs)
    return out


def cells():
    return [(c, a) for c in sorted(DESIGN["cases"]) for a in arms_of(c)]


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def check_pins(ctx):
    """Refuse to run on anything but the pinned materials."""
    got = sha256(os.path.join(ctx, "global-CLAUDE-2026-09-30.md"))
    if got != DESIGN["instruction_sha256"]:
        sys.exit("pinned instruction file changed: {}".format(got))
    with open(os.path.join(ctx, "SHA256SUMS")) as fh:
        for line in fh:
            want, rel = line.split()
            if rel.startswith("hooks/") and sha256(os.path.join(ctx, rel)) != want:
                sys.exit("pinned hook changed: {}".format(rel))


def quota_open():
    """The harness's own model-quota door (its scheduler status). Closed means stop."""
    done = subprocess.run([sys.executable, "-m", "sched", "status"], cwd=env("E1_HUB"),
                          capture_output=True, text=True, timeout=180)
    m = re.search(r"claude_quota=(None|\{.*?\}|\S+?),", done.stdout)
    return bool(m) and m.group(1) == "None"


def void_reason(info):
    if not info.get("model"):
        return "no model turn (exit {}): {}".format(info.get("exit_code"),
                                                   (info.get("stderr_tail") or "")[-160:])
    status = info.get("api_error_status")
    result = str(info.get("result") or "")
    if status in (429, "429") or (info.get("is_error") and re.search(
            r"rate.?limit|usage limit|quota", result, re.I)):
        return "quota: {}".format(status or result[:120])
    return None


def grade(arms_mod, case, arm, info, state, prompt):
    """Every outcome of PREREG section 7 for one run, from what the run left."""
    ctx = env("E1_CONTEXT")
    _prose, regs = arms_of(case)[arm]
    v = graders.violation(case, info, state)
    k_stop = arms_mod.stop_blocks_took_effect(
        info, lambda t: graders.text_violates(case, t, state))
    k_deny = arms_mod.denials_took_effect(info, graders.has_dash) if case == "C4" else []
    return {
        "V": v,
        "V_door": graders.door_violation(case, info, state, os.path.join(ctx, "hooks"), prompt),
        "B": arms_mod.blocks(info),
        "B_stop": sum(1 for s in info["stops"] for h in s["hooks"] if h["decision"] == "block"),
        "B_deny": len(info["denials"]),
        "K_stop": k_stop,
        "K_deny": k_deny,
        "E": (v if regs else None),
        "C": graders.complete(case, info, state),
        "stop_attempts": len(info["stops"]),
        "tool_calls": len(info["tools"]),
    }


def one_run(case, arm, run_index, out_dir, counted, order=None):
    arms_mod, tw_commit = trimwrit()
    ctx = env("E1_CONTEXT")
    spec = DESIGN["cases"][case]
    prose, regs = arms_of(case)[arm]
    full = open(os.path.join(ctx, "global-CLAUDE-2026-09-30.md"), encoding="utf-8").read()
    text = full if prose else arms_mod.ablate_lines(full, spec["ablate"])
    hook_files = {n: os.path.join(ctx, "hooks", n) for n in spec["hook_files"]} if regs else {}
    case_dir = os.path.join(HERE, "cases", case)
    prompt = open(os.path.join(case_dir, "prompt.md"), encoding="utf-8").read().strip()
    token = open(os.path.expanduser(env("E1_TOKEN_FILE"))).read().strip()
    setup = os.path.join(case_dir, spec["setup"]) if spec.get("setup") else None
    scratch = os.path.join("/tmp", "e1-scratch")
    os.makedirs(scratch, exist_ok=True)
    info, state = arms_mod.run_arm(
        prompt, os.path.join(case_dir, "template"), text, regs, hook_files, DESIGN["model"],
        out_dir, token=token, timeout_s=DESIGN["wall_seconds"], scratch_root=scratch,
        setup=setup, env_extra={"RC_ACTIVITY_DIR": os.path.join(out_dir, "rc")})
    void = void_reason(info)
    rec = {"order": order, "case": case, "arm": arm, "run_index": run_index,
           "counted": counted, "ts": info["ts"], "model_requested": DESIGN["model"],
           "model": info.get("model"), "cli_version": info.get("cli_version"),
           "trimwrit_commit": tw_commit, "void": void, "wall_s": info.get("wall_s"),
           "killed": info.get("killed"), "turns": info.get("num_turns"),
           "output_tokens": info.get("output_tokens")}
    if not void:
        rec.update(grade(arms_mod, case, arm, info, state, prompt))
    return rec


def append(path, rec):
    with LOCK:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=True) + "\n")


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


# ---------------------------------------------------------------- commands


def cmd_order(_a):
    if os.path.exists(ORDER):
        sys.exit("run_order.csv exists; the order is drawn once")
    rows = [(c, a, i) for c, a in cells() for i in range(DESIGN["runs_per_cell"])]
    perm = np.random.default_rng(DESIGN["seed"]).permutation(len(rows))
    with open(ORDER, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["order", "case", "arm", "run_index"])
        for k, idx in enumerate(perm):
            w.writerow([k] + list(rows[idx]))
    print("{} runs over {} cells".format(len(rows), len(cells())))


def cmd_pilot(a):
    ctx = env("E1_CONTEXT")
    check_pins(ctx)
    raw = env("E1_RAW")
    tag = a.tag or "v1"
    if not a.skip_quota and not quota_open():
        sys.exit("model-quota door closed")

    def work(k):
        out = os.path.join(raw, "pilot", "{}-{}".format(a.case, tag), str(k))
        rec = one_run(a.case, a.arm, k, out, counted=False)
        rec["pilot"] = tag
        append(os.path.join(raw, PILOT_NAME), rec)
        print(json.dumps({x: rec.get(x) for x in ("case", "arm", "run_index", "V", "V_door",
                                                  "B", "C", "void", "wall_s", "turns")}),
              flush=True)
        return rec

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:
        list(pool.map(work, range(a.n)))


def done_orders():
    return {r["order"] for r in read_jsonl(RESULTS) if r.get("counted") and not r.get("void")}


def cmd_batch(a):
    ctx = env("E1_CONTEXT")
    check_pins(ctx)
    raw = env("E1_RAW")
    with open(ORDER) as fh:
        order = [dict(r) for r in csv.DictReader(fh)]
    skip = set(a.skip_case or [])
    done = done_orders()
    voided = {}
    for r in read_jsonl(RESULTS):
        if r.get("counted") and r.get("void"):
            voided[r["order"]] = voided.get(r["order"], 0) + 1
    todo = [r for r in order if int(r["order"]) not in done and r["case"] not in skip
            and voided.get(int(r["order"]), 0) == 0]
    # A voided run is rerun once, at the end of the order (PREREG section 5).
    todo += [r for r in order if int(r["order"]) not in done and r["case"] not in skip
             and voided.get(int(r["order"]), 0) == 1]
    todo = todo[:a.n]
    if not todo:
        print("nothing left to run")
        return
    if not quota_open():
        print("model-quota door closed: no batch")
        return
    stop = threading.Event()

    def work(r):
        if stop.is_set():
            return None
        k = int(r["order"])
        out = os.path.join(raw, "runs", "{:03d}-{}-{}-{}".format(k, r["case"], r["arm"],
                                                                 r["run_index"]))
        if os.path.exists(out):
            out += "-rerun"
        rec = one_run(r["case"], r["arm"], int(r["run_index"]), out, counted=True, order=k)
        append(RESULTS, rec)
        print(json.dumps({x: rec.get(x) for x in ("order", "case", "arm", "V", "B", "K", "C",
                                                  "void", "wall_s")}), flush=True)
        if rec.get("void", "") and rec["void"].startswith("quota"):
            stop.set()
        return rec

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:
        futures = []
        for i, r in enumerate(todo):
            if stop.is_set():
                break
            if i and i % (a.jobs * 2) == 0 and not quota_open():
                print("model-quota door closed mid-batch: stopping", flush=True)
                stop.set()
                break
            futures.append(pool.submit(work, r))
            while sum(1 for f in futures if not f.done()) >= a.jobs:
                time.sleep(2)
        for f in futures:
            f.result()


def cmd_regrade(a):
    """Grade again, with the current graders, every run.json under a directory of raw runs."""
    arms_mod, _c = trimwrit()
    root = a.root
    for dirpath, _d, files in sorted(os.walk(root)):
        if "run.json" not in files:
            continue
        rel = os.path.relpath(dirpath, root)
        case = a.case or rel.split("-")[0].split(os.sep)[0]
        with open(os.path.join(dirpath, "run.json"), encoding="utf-8") as fh:
            run = json.load(fh)
        prompt = open(os.path.join(HERE, "cases", case, "prompt.md")).read().strip()
        out = {"run": rel, "case": case, "void": void_reason(run["info"])}
        if not out["void"]:
            out.update(grade(arms_mod, case, a.arm, run["info"], run["state"], prompt))
        print(json.dumps(out), flush=True)


def cmd_status(_a):
    got = {}
    for r in read_jsonl(RESULTS):
        if r.get("counted") and not r.get("void"):
            got[(r["case"], r["arm"])] = got.get((r["case"], r["arm"]), 0) + 1
    for c, a in cells():
        print("{} {:10s} {:2d}/{}".format(c, a, got.get((c, a), 0), DESIGN["runs_per_cell"]))
    print("total", sum(got.values()))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("order")
    pl = sub.add_parser("pilot")
    pl.add_argument("case")
    pl.add_argument("--arm", default="A0")
    pl.add_argument("--n", type=int, default=3)
    pl.add_argument("--jobs", type=int, default=3)
    pl.add_argument("--tag")
    pl.add_argument("--skip-quota", action="store_true")
    bt = sub.add_parser("batch")
    bt.add_argument("--n", type=int, default=20)
    bt.add_argument("--jobs", type=int, default=4)
    bt.add_argument("--skip-case", action="append")
    sub.add_parser("status")
    rg = sub.add_parser("regrade")
    rg.add_argument("root")
    rg.add_argument("--case")
    rg.add_argument("--arm", default="A0")
    a = p.parse_args()
    {"order": cmd_order, "pilot": cmd_pilot, "batch": cmd_batch, "status": cmd_status,
     "regrade": cmd_regrade}[a.cmd](a)


if __name__ == "__main__":
    main()
