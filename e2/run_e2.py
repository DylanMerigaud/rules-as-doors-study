#!/usr/bin/env python3
"""Drive E2 (PREREG-E2 sections 4 to 7) through trimwrit's arms runner.

    python3 e2/run_e2.py order                 write e2/run_order.csv (once, before any run)
    python3 e2/run_e2.py prove                 every grader flags its violating sample and passes
                                               its clean one (trimwrit's prove)
    python3 e2/run_e2.py planted DOOR [--n 1]  a planted run per door: can it refuse, does the
                                               refusal take effect (not counted)
    python3 e2/run_e2.py pilot CASE [--n 3]    uncounted A0 runs of one case
    python3 e2/run_e2.py run [--jobs 4]        every counted run left in the order, waiting
                                               while the model-quota door is closed
    python3 e2/run_e2.py status                runs per cell

E2 reuses E1's driver by import where nothing changed (the void rules, the jsonl helpers) and
differs where PREREG-E2 says so: the hooks are the repaired ones and every hook command carries
`--home` (their ledgers and state stay in the run's scratch directory), the Stop-arm situation
of the long-dash rule is C4S, a run that dies on an API error is voided and rerun, and each run
records a delivery check (did every Stop decision equal the door's detector on that text) and
the hooks' own health rows.

Private inputs come from the environment, never from this file: E2_CONTEXT (the pinned
instruction file and the pinned E2 hook copies with their SHA256SUMS), E2_RAW (where raw run files
go, never published), TRIMWRIT (the runner's checkout) and E2_HUB (the harness whose
model-quota door gates every batch and whose credential resolver hands each run a subscription
login; an API key is never used). Results without any text go to e2/results.jsonl.
"""
import argparse
import concurrent.futures
import csv
import glob
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DESIGN = json.load(open(os.path.join(HERE, "design.json")))
ORDER = os.path.join(HERE, "run_order.csv")
RESULTS = os.path.join(HERE, "results.jsonl")
PLANTED = os.path.join(HERE, "planted.json")
PROOF = os.path.join(HERE, "proof.json")
LOCK = threading.Lock()
CRED_LOCK = threading.Lock()
MAX_ATTEMPTS = 4          # a voided order row is run again, up to this many attempts in all
QUOTA_WAIT_S = 600
CRED_WAIT_S = 120


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


graders = _load("e2_graders", os.path.join(HERE, "graders.py"))
run_e1 = _load("e1_driver", os.path.join(ROOT, "e1", "run_e1.py"))
read_jsonl = run_e1.read_jsonl


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


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ---------------------------------------------------------------- the design

def arms_of(case):
    """{arm: (prose_on, registrations)}. Every registration carries `--home`."""
    spec = DESIGN["cases"][case]
    out = {"A0": (False, []), "AP": (True, [])}
    for name, regs in spec["doors"].items():
        regs = [dict(r, args=list(r.get("args", [])) + DESIGN["home_args"]) for r in regs]
        suffix = "" if name == "door" else "-" + name
        out["AD" + suffix] = (False, regs)
        out["APD" + suffix] = (True, regs)
    return out


def cells():
    return [(c, a) for c in sorted(DESIGN["cases"]) for a in arms_of(c)]


def case_paths(case):
    spec = DESIGN["cases"][case]
    d = os.path.join(ROOT, spec["dir"])
    template = os.path.join(ROOT, spec["template"]) if spec.get("template") else \
        os.path.join(d, "template")
    setup = None
    if spec.get("setup_from"):
        setup = os.path.join(ROOT, spec["setup_from"])
    elif spec.get("setup"):
        setup = os.path.join(d, spec["setup"])
    prompt = open(os.path.join(d, "prompt.md"), encoding="utf-8").read().strip()
    return template, setup, prompt


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def check_pins(ctx):
    """Refuse to run on anything but the pinned materials."""
    got = sha256(os.path.join(ctx, "global-CLAUDE-2026-09-30.md"))
    if got != DESIGN["instruction_sha256"]:
        sys.exit("pinned instruction file changed: {}".format(got))
    for name, want in DESIGN["hooks_pin"]["sha256"].items():
        if sha256(os.path.join(ctx, "hooks", name)) != want:
            sys.exit("pinned hook changed: {}".format(name))


def clean_template(src):
    """A copy of the template without byte-code caches, so no run starts from a stale one."""
    dst = tempfile.mkdtemp(prefix="e2-template-")
    shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dst


# ---------------------------------------------------------------- the harness's doors

def quota_open():
    """The harness's own model-quota door (its scheduler status). Closed means wait."""
    hub = env("E2_HUB")
    done = subprocess.run([sys.executable, "-m", "sched", "status"], cwd=hub,
                          capture_output=True, text=True, timeout=180)
    m = re.search(r"claude_quota=(None|\{.*?\}|\S+?),", done.stdout)
    return bool(m) and m.group(1) == "None"


def wait_for_quota(stop=None):
    while not quota_open():
        log("model-quota door closed: waiting {} s".format(QUOTA_WAIT_S))
        if stop is not None and stop.is_set():
            return False
        time.sleep(QUOTA_WAIT_S)
    return True


_HEADLESS = []


def credential(timeout_s):
    """A subscription login from the harness's resolver, waiting while none can answer for a
    run of `timeout_s`. The token never leaves this process except into the run's env."""
    with CRED_LOCK:
        if not _HEADLESS:
            path = os.path.join(env("E2_HUB"), "career", "evals-core")
            if path not in sys.path:
                sys.path.append(path)
            import headless
            _HEADLESS.append(headless)
        headless = _HEADLESS[0]
        while True:
            try:
                cred = headless._credential(timeout=timeout_s)
            except Exception as e:  # noqa: BLE001  no credential can answer yet: wait
                log("no credential for a {} s run ({}): waiting {} s".format(
                    timeout_s, getattr(e, "code", type(e).__name__), CRED_WAIT_S))
                time.sleep(CRED_WAIT_S)
                continue
            if cred and cred.get("token"):
                src = str(cred.get("source") or "file")
                return cred["token"], src.split(":")[0]
            time.sleep(CRED_WAIT_S)


# ---------------------------------------------------------------- one run

API_ERROR_RE = re.compile(r"API Error|overloaded|internal server error|api_error|"
                          r"authentication_error|invalid.{0,20}token|OAuth", re.I)


def void_reason(info):
    """E1's void rules (no model turn, a quota limit), plus a run that died on an API error."""
    reason = run_e1.void_reason(info)
    if reason:
        return reason
    result = str(info.get("result") or "")
    if info.get("is_error") and (info.get("api_error_status") or API_ERROR_RE.search(result)):
        return "api error: {} {}".format(info.get("api_error_status"), result[:120])
    return None


def hook_health(home):
    rows = []
    path = os.path.join(home, "hook-health.jsonl")
    if os.path.exists(path):
        with open(path, encoding="ascii", errors="replace") as fh:
            rows = [json.loads(x) for x in fh if x.strip()]
    count = {}
    for r in rows:
        count[r.get("outcome")] = count.get(r.get("outcome"), 0) + 1
    return {"hook_caps": count.get("cap", 0), "hook_crashes": count.get("crash", 0),
            "hook_timeouts": count.get("timeout", 0)}


def delivery_check(case, info, ctx, prompt):
    """Per Stop hook answer: the door's detector on that stop's text, and whether the hook
    blocked. A miss is a text the detector flags with no block; a false block the reverse. A
    stop let through by the chain cap is counted apart (the cap is part of the door)."""
    det = graders.stop_detector(case, os.path.join(ctx, "hooks"), prompt)
    if det is None:
        return {}
    checks = []
    for stop in info["stops"]:
        for h in stop["hooks"]:
            checks.append((bool(det(stop["text"])), h["decision"] == "block"))
    return {"stop_checks": len(checks),
            "stop_agree": sum(1 for d, b in checks if d == b),
            "stop_miss": sum(1 for d, b in checks if d and not b),
            "stop_false_block": sum(1 for d, b in checks if b and not d)}


def grade(arms_mod, case, arm, info, state, prompt, ctx):
    """Every outcome of PREREG-E2 section 7 for one run, from what the run left."""
    _prose, regs = arms_of(case)[arm]
    v = graders.violation(case, info, state)
    k_stop = arms_mod.stop_blocks_took_effect(
        info, lambda t: graders.text_violates(case, t, state))
    k_deny = arms_mod.denials_took_effect(info, graders.has_dash) if case == "C4" else []
    rec = {
        "V": v,
        "V_door": graders.door_violation(case, info, state, os.path.join(ctx, "hooks"), prompt),
        "B": arms_mod.blocks(info),
        "B_stop": sum(1 for s in info["stops"] for h in s["hooks"] if h["decision"] == "block"),
        "B_deny": len(info["denials"]),
        "K_stop": k_stop,
        "K_deny": k_deny,
        "K_deny_strict": graders.k_deny_strict(k_deny, state) if case == "C4" else [],
        "E": (v if regs else None),
        "C": graders.complete(case, info, state),
        "stop_attempts": len(info["stops"]),
        "tool_calls": len(info["tools"]),
    }
    rec.update(graders.violation_parts(case, info, state))
    if regs:
        rec.update(delivery_check(case, info, ctx, prompt))
        det = graders.stop_detector(case, os.path.join(ctx, "hooks"), prompt)
        # K by the door's own detector (secondary): the re-answer after each Stop block no
        # longer flagged by the detector the hook runs, code-span exemption included.
        rec["K_stop_door"] = arms_mod.stop_blocks_took_effect(info, det) if det else []
    return rec


def one_run(case, arm, out_dir, prompt_override=None, wall=None):
    """One run in its own scratch root; returns (record, info, state). The hooks' --home
    directory is copied next to the raw run before the scratch root goes."""
    arms_mod, tw_commit = trimwrit()
    ctx = env("E2_CONTEXT")
    spec = DESIGN["cases"][case]
    prose, regs = arms_of(case)[arm]
    full = open(os.path.join(ctx, "global-CLAUDE-2026-09-30.md"), encoding="utf-8").read()
    text = full if prose else arms_mod.ablate_lines(full, spec["ablate"])
    hook_files = {n: os.path.join(ctx, "hooks", n) for n in spec["hook_files"]} if regs else {}
    template, setup, prompt = case_paths(case)
    if prompt_override is not None:
        prompt = prompt_override
    wall = wall or DESIGN["wall_seconds"]
    token, source_kind = credential(wall)
    scratch = os.path.join(tempfile.gettempdir(), "e2-scratch", uuid.uuid4().hex[:12])
    os.makedirs(scratch, exist_ok=True)
    tpl = clean_template(template)
    try:
        info, state = arms_mod.run_arm(
            prompt, tpl, text, regs, hook_files, DESIGN["model"], out_dir, token=token,
            timeout_s=wall, scratch_root=scratch, setup=setup,
            keep_workdir=True)
        homes = glob.glob(os.path.join(scratch, "arms-*", "hook-home"))
        health = {}
        if homes:
            shutil.copytree(homes[0], os.path.join(out_dir, "hook-home"), dirs_exist_ok=True)
            health = hook_health(homes[0])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        shutil.rmtree(tpl, ignore_errors=True)
    void = void_reason(info)
    rec = {"experiment": "E2", "case": case, "arm": arm, "ts": info["ts"],
           "model_requested": DESIGN["model"], "model": info.get("model"),
           "cli_version": info.get("cli_version"), "trimwrit_commit": tw_commit,
           "credential": source_kind, "void": void, "wall_s": info.get("wall_s"),
           "killed": info.get("killed"), "turns": info.get("num_turns"),
           "output_tokens": info.get("output_tokens")}
    if not void:
        rec.update(grade(arms_mod, case, arm, info, state, prompt, ctx))
        if regs:
            rec.update(health)
    return rec, info, state


def append(path, rec):
    with LOCK:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=True, sort_keys=True) + "\n")


def short(rec, keys=("order", "case", "arm", "V", "V_door", "B", "K_stop", "K_deny", "C",
                     "stop_miss", "void", "wall_s")):
    return json.dumps({k: rec.get(k) for k in keys if k in rec})


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


def cmd_prove(_a):
    """trimwrit's prove on every case's proof samples: the grader flags the violating one and
    passes the clean one. Exit 1 on any failure."""
    arms_mod, _c = trimwrit()
    proof = json.load(open(PROOF))
    e1_proof = json.load(open(os.path.join(ROOT, "e1", "proof.json")))
    failed = 0
    for case in sorted(DESIGN["cases"]):
        p = proof.get(case) or e1_proof.get(case)
        empty = {"files": {}, "commits": [], "base": {}}
        clean_state = p.get("clean_state", empty)

        def grader(t, _case=case):
            # the clean sample is graded with the state it names (a door file the run created)
            return bool(graders.text_violates(_case, t, clean_state if t in clean_texts
                                              else empty))

        clean_texts = [p["clean"]] + list(p.get("also_clean", []))
        fails = arms_mod.prove(grader, p["violating"], p["clean"])
        for s in p.get("also_violating", []):
            fails += arms_mod.prove(grader, s, p["clean"])
        for s in p.get("also_clean", []):
            fails += arms_mod.prove(grader, p["violating"], s)
        print("{} {}".format(case, "proved" if not fails else "FAILED: " + "; ".join(fails)))
        failed += bool(fails)
    sys.exit(1 if failed else 0)


def planted_verdict(door, rec, info, state, ctx):
    """The proof of one planted run (see cmd_planted). Adds K by the detector, the effect and the
    verdict to `rec`, from what the run left."""
    arms_mod, _c = trimwrit()
    planted = json.load(open(PLANTED))[door]
    case = planted["case"]
    det = graders.stop_detector(case, os.path.join(ctx, "hooks"), planted["prompt"])
    k_door = arms_mod.stop_blocks_took_effect(info, det) if det else []
    if det:
        effect = bool(rec.get("B_stop")) and not det(info.get("closing_text") or "") \
            and not rec.get("hook_caps")
    else:
        strict = rec.get("K_deny_strict") or []
        effect = bool(rec.get("B_deny")) and bool(strict) and bool(strict[-1])
    rec.update({"planted": door, "K_stop_door": k_door, "effect": effect,
                "proven": bool(rec.get("B")) and effect and not rec.get("stop_miss")
                and not rec.get("stop_false_block") and not rec.get("hook_crashes")})
    return rec


PLANTED_KEYS = ("planted", "case", "arm", "B", "K_stop", "K_stop_door", "K_deny",
                "K_deny_strict", "stop_checks", "stop_agree", "stop_miss", "hook_caps",
                "hook_crashes", "effect", "proven", "void", "model", "cli_version")


def cmd_planted(a):
    """A planted run per door (PREREG-E2 section 6): a prompt that makes the violation, in the
    door-only arm. Proven when the door refused at least once, every Stop decision equalled the
    door's detector on that text, no hook crashed, and the refusal took effect: a Stop door's
    chain ended, before its cap, on a closing text the detector no longer flags; for the write
    door, the last denial was followed by an accepted write to the same target with no long
    dash, and no file the run wrote holds one. Per-block K (by the prose grader and by the
    detector) is recorded beside."""
    check_pins(env("E2_CONTEXT"))
    raw = env("E2_RAW")
    ctx = env("E2_CONTEXT")
    planted = json.load(open(PLANTED))[a.door]
    if not wait_for_quota():
        return
    case, arm = planted["case"], planted["arm"]
    for k in range(a.n):
        out = os.path.join(raw, "planted", "{}-{}".format(a.door, a.tag or "v1"), str(k))
        rec, info, state = one_run(case, arm, out, prompt_override=planted["prompt"],
                                   wall=a.wall)
        rec["wall_cap_s"] = a.wall
        planted_verdict(a.door, rec, info, state, ctx)
        append(os.path.join(raw, "planted.jsonl"), rec)
        print(short(rec, PLANTED_KEYS), flush=True)


def cmd_planted_report(_a):
    """Every planted run under E2_RAW/planted, graded again from its raw files."""
    arms_mod, _c = trimwrit()
    ctx = env("E2_CONTEXT")
    raw = env("E2_RAW")
    proven = {}
    for path in sorted(glob.glob(os.path.join(raw, "planted", "*", "*", "run.json"))):
        door, tag = os.path.basename(os.path.dirname(os.path.dirname(path))).rsplit("-", 1)
        planted = json.load(open(PLANTED))[door]
        case, arm = planted["case"], planted["arm"]
        prompt = planted.get("versions", {}).get(tag, planted["prompt"])
        run = json.load(open(path))
        info, state = run["info"], run["state"]
        rec = {"case": case, "arm": arm, "void": void_reason(info), "model": info.get("model"),
               "cli_version": info.get("cli_version")}
        home = os.path.join(os.path.dirname(path), "hook-home")
        if not rec["void"]:
            rec.update(grade(arms_mod, case, arm, info, state, prompt, ctx))
            rec.update(hook_health(home))
            planted_verdict(door, rec, info, state, ctx)
        proven[door] = proven.get(door, False) or bool(rec.get("proven"))
        print(tag, short(rec, PLANTED_KEYS), flush=True)
    for door in json.load(open(PLANTED)):
        if door.startswith("_"):
            continue
        print("{}: {}".format(door, "proven" if proven.get(door) else "NOT PROVEN"))
    sys.exit(0 if all(proven.get(d) for d in json.load(open(PLANTED))
                      if not d.startswith("_")) else 1)


def cmd_pilot(a):
    check_pins(env("E2_CONTEXT"))
    raw = env("E2_RAW")
    if not wait_for_quota():
        return

    def work(k):
        out = os.path.join(raw, "pilot", "{}-{}-{}".format(a.case, a.arm, a.tag or "v1"),
                           str(k))
        rec, _i, _s = one_run(a.case, a.arm, out)
        rec.update({"pilot": a.tag or "v1", "run_index": k})
        append(os.path.join(raw, "pilot.jsonl"), rec)
        print(short(rec, ("case", "arm", "run_index", "V", "V_text", "V_files", "V_door", "B",
                          "C", "void", "wall_s", "turns", "model", "cli_version")), flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:
        list(pool.map(work, range(a.n)))


def attempts():
    """{order: (counted, voided)} from the results file."""
    out = {}
    for r in read_jsonl(RESULTS):
        if r.get("counted"):
            got = out.setdefault(r["order"], [0, 0])
            got[1 if r.get("void") else 0] += 1
    return out


def todo_rows():
    with open(ORDER) as fh:
        order = [dict(r) for r in csv.DictReader(fh)]
    seen = attempts()
    fresh, again = [], []
    for r in order:
        counted, voided = seen.get(int(r["order"]), (0, 0))
        if counted:
            continue
        if voided == 0:
            fresh.append(r)
        elif voided < MAX_ATTEMPTS:
            again.append(r)
    # A voided run goes to the end of the order and is run again (PREREG-E2 section 5).
    return fresh + again


def tag_guard():
    """No counted run before the registration: the tag prereg-e2 exists here and on the
    remote, and its commit time is in the past."""
    here = subprocess.run(["git", "-C", ROOT, "log", "-1", "--format=%ct", "prereg-e2"],
                          capture_output=True, text=True)
    if here.returncode != 0 or not here.stdout.strip():
        sys.exit("no tag prereg-e2: no counted run")
    remote = subprocess.run(["git", "-C", ROOT, "ls-remote", "--tags", "origin",
                             "refs/tags/prereg-e2"], capture_output=True, text=True)
    if "refs/tags/prereg-e2" not in remote.stdout:
        sys.exit("prereg-e2 is not on the remote: no counted run")
    if int(here.stdout.strip()) >= time.time():
        sys.exit("prereg-e2 is not older than now")


def cmd_run(a):
    """Every counted run left, in the registered order, `jobs` at a time. The quota door is read
    before the first run and before every `2 * jobs` runs; while it is closed nothing new starts."""
    check_pins(env("E2_CONTEXT"))
    raw = env("E2_RAW")
    tag_guard()
    while True:
        todo = todo_rows()
        if a.limit:
            todo = todo[:a.limit]
        if not todo:
            log("nothing left to run")
            return
        log("{} runs to go".format(len(todo)))
        wait_for_quota()
        stop = threading.Event()

        def work(r):
            k = int(r["order"])
            n_prev = sum(attempts().get(k, (0, 0)))
            out = os.path.join(raw, "runs", "{:03d}-{}-{}-{}".format(
                k, r["case"], r["arm"], r["run_index"]))
            if n_prev:
                out += "-attempt{}".format(n_prev + 1)
            rec, _i, _s = one_run(r["case"], r["arm"], out)
            rec.update({"order": k, "run_index": int(r["run_index"]), "counted": True,
                        "attempt": n_prev + 1})
            append(RESULTS, rec)
            log(short(rec))
            if (rec.get("void") or "").startswith("quota"):
                stop.set()
            return rec

        with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:
            futures = []
            for i, r in enumerate(todo):
                if stop.is_set():
                    break
                if i and i % (a.jobs * 2) == 0 and not quota_open():
                    log("model-quota door closed mid-batch: no new run until it opens")
                    break
                futures.append(pool.submit(work, r))
                while sum(1 for f in futures if not f.done()) >= a.jobs:
                    time.sleep(2)
            for f in futures:
                f.result()
        if a.limit:
            return


def cmd_status(_a):
    got = {}
    voids = 0
    for r in read_jsonl(RESULTS):
        if r.get("counted") and not r.get("void"):
            got[(r["case"], r["arm"])] = got.get((r["case"], r["arm"]), 0) + 1
        elif r.get("counted"):
            voids += 1
    complete = True
    for c, a in cells():
        n = got.get((c, a), 0)
        complete &= n >= DESIGN["runs_per_cell"]
        print("{:4s} {:10s} {:2d}/{}".format(c, a, n, DESIGN["runs_per_cell"]))
    print("total", sum(got.values()), "voided", voids)
    sys.exit(0 if complete else 1)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("order")
    sub.add_parser("prove")
    pt = sub.add_parser("planted")
    pt.add_argument("door")
    pt.add_argument("--n", type=int, default=1)
    pt.add_argument("--tag")
    pt.add_argument("--wall", type=int, default=600)
    pl = sub.add_parser("pilot")
    pl.add_argument("case")
    pl.add_argument("--arm", default="A0")
    pl.add_argument("--n", type=int, default=3)
    pl.add_argument("--jobs", type=int, default=3)
    pl.add_argument("--tag")
    rn = sub.add_parser("run")
    rn.add_argument("--jobs", type=int, default=4)
    rn.add_argument("--limit", type=int)
    sub.add_parser("status")
    sub.add_parser("planted-report")
    a = p.parse_args()
    {"order": cmd_order, "prove": cmd_prove, "planted": cmd_planted, "pilot": cmd_pilot,
     "run": cmd_run, "status": cmd_status, "planted-report": cmd_planted_report}[a.cmd](a)


if __name__ == "__main__":
    main()
