#!/usr/bin/env python3
"""hook_trace: the chain cap, the crash report and the refusal witness every gate hook shares.

Public copy of the module pinned for experiment E2 (`hook_trace.py`, sha256 57409175ba41b9a2...).
Code lines are the pinned ones; every edit is marked in place and listed in
`e2/REDACTIONS.md` (H markers: E1's redactions of the same pinned lines, carried
unchanged; J markers: new in E2).
[REDACTED J61: the original module docstring, which tells the audit that led to it
(2026-09-30) and names private paths, plans and repositories. In gist: refusals go to a
door ledger through witness(); the health of a gate (a `cap`, a `crash`, a `timeout`, a
`recovered`) goes to `hook-health.jsonl`. Each Stop gate counts its own consecutive blocks
inside one stop chain (`stop_hook_active` true means the chain goes on) and at CHAIN_CAP lets
the turn end, writes a `cap` row and says so in a systemMessage; the count restarts with
every chain. A gate that raises or times out lets the action through and records it (ledger
row, autofix record, systemMessage). No environment variable and no marker file turns a gate
off; the only knob is `--home DIR`, an argument, which points the ledger, the state, the
autofix script and the door ledger at DIR.]
"""
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime

HUB = os.path.expanduser("~/Code/redacted-j62")  # [REDACTED J62: the repository's path; read only
# without --home, and every E2 hook command passes --home]
LEDGER_NAME = "hook-health.jsonl"
STATE_NAME = "redacted-j62-stop-gate"  # [REDACTED J62: the repository's name; read only without --home]
CHAIN_CAP = 3
DETAIL_MAX = 600
ENV_SESSION = "CLAUDE_SESSION_ID"

_HOME = None
_PAYLOAD = {}


class HookTimeout(Exception):
    """Raised by the alarm when a hook has not decided in time."""


def configure(argv):
    """Take `--home DIR` out of argv (in place) and remember it. Returns argv."""
    global _HOME
    if "--home" in argv:
        i = argv.index("--home")
        if i + 1 >= len(argv):
            raise SystemExit("--home needs a directory")
        _HOME = argv[i + 1]
        del argv[i:i + 2]
    return argv


def home():
    return _HOME


def ledger_path():
    if _HOME:
        return os.path.join(_HOME, LEDGER_NAME)
    analytics = os.path.join(HUB, "analytics")
    if os.path.isdir(analytics):
        return os.path.join(analytics, LEDGER_NAME)
    return os.path.expanduser(os.path.join("~", ".claude", LEDGER_NAME))


def state_dir():
    d = os.path.join(_HOME, "state") if _HOME else os.path.join(tempfile.gettempdir(), STATE_NAME)
    os.makedirs(d, exist_ok=True)
    return d


def autofix_script():
    return os.path.join(_HOME, "autofix.py") if _HOME else os.path.join(HUB, "scripts", "autofix.py")


def door_ledger_script():
    return (os.path.join(_HOME, "door_ledger.py") if _HOME
            else os.path.join(HUB, "scripts", "door_ledger.py"))


def remember(payload):
    """Keep the payload so a crash row can name the session and the cwd."""
    global _PAYLOAD
    _PAYLOAD = payload if isinstance(payload, dict) else {}
    return _PAYLOAD


def session_key(payload=None):
    p = payload if isinstance(payload, dict) else _PAYLOAD
    return (p or {}).get("session_id") or os.environ.get(ENV_SESSION, "")


def session_file(session_id, suffix):
    key = hashlib.sha256((session_id or "sans-id").encode("utf-8")).hexdigest()[:16]
    return os.path.join(state_dir(), key + suffix)


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def trace(hook, event, outcome, payload=None, **fields):
    """Append one health row. True when written; an unwritable ledger says so on stderr."""
    p = payload if isinstance(payload, dict) else _PAYLOAD
    row = {"at": now_iso(), "hook": hook, "event": event, "outcome": outcome,
           "session": session_key(p), "cwd": (p or {}).get("cwd") or os.getcwd()}
    for k, v in fields.items():
        if isinstance(v, str) and len(v) > DETAIL_MAX:
            v = v[:DETAIL_MAX]
        row[k] = v
    try:
        path = ledger_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="ascii") as fh:
            fh.write(json.dumps(row, ensure_ascii=True) + "\n")
        return True
    except OSError as e:
        sys.stderr.write("hook_trace: ledger unwritable ({}): {}\n".format(e, row))
        return False


def witness(door, event, reason_class, payload=None, script=None):
    """Count one refusal in [REDACTED J63: the repository's name and its door ledger]. The door
    already decided: a ledger that cannot be reached changes nothing here, and door_ledger.py
    owns its own failure policy. `script` lets a repo gate name its own checkout's copy."""
    script = script or door_ledger_script()
    if not os.path.isfile(script):
        return False
    try:
        spec = importlib.util.spec_from_file_location("door_ledger", script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return bool(mod.log(door, event, reason_class, session_key(payload) or None))
    except Exception as e:  # noqa: BLE001  said on stderr, never a change of decision
        sys.stderr.write("hook_trace: door ledger unreachable: {}\n".format(e))
        return False


def _read_int(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return int(fh.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def _write_int(path, n):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(str(n))


def chain_path(hook, payload):
    return session_file(session_key(payload), "." + hook + ".chain")


def chain_should_block(hook, payload, detail):
    """For a Stop gate that found a violation. True: block now (the chain count goes up). False:
    this gate already blocked CHAIN_CAP times in a row in this stop chain, so the turn ends, a
    `cap` row is written and the caller prints cap_message()."""
    path = chain_path(hook, payload)
    used = _read_int(path) if (payload or {}).get("stop_hook_active") else 0
    if used >= CHAIN_CAP:
        _write_int(path, 0)
        trace(hook, "Stop", "cap", payload, blocks=used, detail=detail)
        return False
    _write_int(path, used + 1)
    return True


def chain_clear(hook, payload):
    try:
        os.remove(chain_path(hook, payload))
    except OSError:
        pass


def cap_message(hook, detail):
    return json.dumps({"systemMessage": (
        "{}: {} blocks in a row did not clear it, the turn ends anyway and the miss is recorded "
        "(analytics/hook-health.jsonl, outcome cap): {}".format(hook, CHAIN_CAP, detail[:200]))},
        ensure_ascii=False)


def _crash_marker(hook):
    return os.path.join(state_dir(), hook + ".crashed")


def autofix(hook, ok, detail=""):
    """Spawn `autofix.py record hook:<name>`, detached: the session never waits on it. Returns
    a short status for the ledger row."""
    script = autofix_script()
    if not os.path.isfile(script):
        return "autofix absent: " + script
    args = [sys.executable, script, "record", "hook:" + hook]
    if ok:
        args.append("--ok")
    else:
        args += ["--detail", detail[-400:],
                 "--reproduce", "replay the last {} row of {} into the hook on stdin".format(
                     hook, ledger_path())]
    try:
        subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)
        return "spawned"
    except OSError as e:
        return "spawn failed: {}".format(e)


def crashed(hook, event, kind, detail):
    """The one exit of a broken gate: ledger row, autofix, a visible systemMessage, exit 0."""
    status = autofix(hook, ok=False, detail="{} {}: {}".format(hook, kind, detail))
    trace(hook, event, kind, None, detail=detail, autofix=status)
    try:
        with open(_crash_marker(hook), "w", encoding="utf-8") as fh:
            fh.write(now_iso())
    except OSError:
        pass
    print(json.dumps({"systemMessage": (
        "{} {} ({}): this {} goes on UNGUARDED. Recorded in analytics/hook-health.jsonl and "
        "autofix (instrument hook:{}).".format(
            hook, "crashed" if kind == "crash" else "timed out", detail[-200:],
            "turn" if event == "Stop" else "call", hook))}, ensure_ascii=False))
    sys.stdout.flush()
    return 0


def recovered(hook):
    """After a clean run: if the last run crashed, say it recovered to autofix and the ledger."""
    marker = _crash_marker(hook)
    if not os.path.exists(marker):
        return
    try:
        os.remove(marker)
    except OSError:
        return
    trace(hook, "", "recovered", None, autofix=autofix(hook, ok=True))


def run(hook, event, body, timeout_s):
    """Run `body()` (returns an exit code) under an alarm; a crash or a timeout goes through
    crashed(), a clean run through recovered(). Returns the exit code for sys.exit."""
    def on_alarm(*_):
        raise HookTimeout()

    signal.signal(signal.SIGALRM, on_alarm)
    signal.alarm(timeout_s)
    try:
        try:
            code = body()
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 0
        signal.alarm(0)
    except HookTimeout:
        return crashed(hook, event, "timeout", "no decision after {}s".format(timeout_s))
    except Exception as e:  # noqa: BLE001  every error is reported, none is swallowed
        signal.alarm(0)
        tail = "".join(traceback.format_exception(type(e), e, e.__traceback__))[-DETAIL_MAX:]
        return crashed(hook, event, "crash", tail)
    recovered(hook)
    return code or 0


def read_payload():
    """stdin as a JSON object. Anything else raises, and run() reports it as a crash.
    [REDACTED J64: one sentence on what the client always passes on stdin.]"""
    raw = sys.stdin.read()
    payload = json.loads(raw or "{}")
    if not isinstance(payload, dict):
        raise ValueError("hook payload is not a JSON object: {!r}".format(raw[:120]))
    return remember(payload)
