#!/usr/bin/env python3
"""Stop hook: a turn does not end on a promise to continue when the operator set a target.

Public copy of the hook pinned for experiment E1 (`stop_promise_gate.py`, sha256 559649dbbca56ea4...).
Code lines are the pinned ones; every edit is marked [REDACTED Hnn] in place and listed in
`e1/REDACTIONS.md`. [REDACTED H21: the original module docstring, which tells the incident
history of the hook, quotes the operator (partly in French) and names private paths.]
"""

from __future__ import annotations

import json
import os
import re
import signal
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# The bounds, the budget and the session key, shared with the other Stop hooks. [REDACTED H22:
# the history of the module.]
import hook_bounds as gate  # noqa: E402

MAX_BLOCKS = 2
TIMEOUT_S = 8
TAIL_CHARS = 700
ARM_SUFFIX = ".promise"
EXCERPT_CHARS = 160

# A target set by the operator: the message that makes stopping wrong. [REDACTED H23: the
# calibration incident; seven of the nine alternatives are French and are replaced below.]
TARGET_RE = re.compile(r"""
    (?!x)x  # [REDACTED H24: one alternative in French]
  | never\s+stop
  | (?:don'?t|do\s+not)\s+stop
  | untill?\s+results
  | (?!x)x  # [REDACTED H24: five alternatives in French]
  | (?!x)x  # [REDACTED H24: one alternative in French]
""", re.I | re.X)

# The promise. [REDACTED H25: the private replay case it was taken from; four alternatives in
# French are replaced below.]
PROMISE_RE = re.compile(r"""
    (?!x)x  # [REDACTED H26: three alternatives in French]
  | next\s+batch
  | I(?:'ll|\s+will)\s+(?:continue|keep\s+going|pick\s+(?:it\s+)?up)
  | to\s+be\s+continued
  | (?!x)x  # [REDACTED H26: one alternative in French]
  | running\s+in\s+(?:the\s+)?background
  | will\s+land
  | not\s+stopping\s+here
  | I(?:'ll|\s+will)\s+(?:report|follow\s+up)\s+(?:back|later)
""", re.I | re.X)


def arm_path(session_id):
    return gate.budget_path(session_id) + ARM_SUFFIX


def armed_excerpt(session_id):
    try:
        with open(arm_path(session_id), encoding="utf-8") as fh:
            return fh.read().strip() or "(target set)"
    except OSError:
        return None


def set_armed(session_id, excerpt):
    path = arm_path(session_id)
    if excerpt is None:
        try:
            os.remove(path)
        except OSError:
            pass
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(excerpt[:EXCERPT_CHARS])


def target_in(prompt):
    return bool(TARGET_RE.search(prompt or ""))


def promise_in(final_text):
    m = PROMISE_RE.search((final_text or "")[-TAIL_CHARS:])
    return m.group(0) if m else None


def last_assistant_text(transcript_path):
    """The text of the last assistant row of a Claude Code transcript, or ''."""
    last = ""
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"type":"assistant"' not in line and '"type": "assistant"' not in line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("type") != "assistant" or row.get("isSidechain"):
                    continue

                # [LAYOUT H45: a blank line added in the public copy, behaviour unchanged]
                content = (row.get("message") or {}).get("content")
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = "\n".join(x.get("text", "") for x in content
                                     if isinstance(x, dict) and x.get("type") == "text")
                else:
                    continue
                if text.strip():
                    last = text
    except OSError:
        return ""
    return last


def reason_text(promise, excerpt):
    # [REDACTED H27: the refusal text names a private rule id and replay case; its gist is kept.]
    return ("The turn ends on a promise to continue (\"{}\") while the operator set a target: \"{}\". "
            "Do the next batch now, in this turn, until the target is reached."
            .format(promise, excerpt))


def on_prompt():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (ValueError, OSError):
        return 0
    prompt = payload.get("prompt") or ""
    if target_in(prompt):
        sid = gate.session_key(payload)
        set_armed(sid, " ".join(prompt.split()))
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    signal.signal(signal.SIGALRM, lambda *_: gate.allow())
    signal.alarm(TIMEOUT_S)

    if "--prompt" in sys.argv:
        return on_prompt()
    if "--arm" in sys.argv:
        i = sys.argv.index("--arm")
        excerpt = sys.argv[i + 1] if i + 1 < len(sys.argv) else "(target set by hand)"
        set_armed(gate.session_key({}), excerpt)
        print("promise guard ARMED for this session: it will refuse a turn ending on a promise.")
        return 0
    if "--disarm" in sys.argv:
        set_armed(gate.session_key({}), None)
        print("promise guard DISARMED for this session.")
        return 0

    show_only = "--print" in sys.argv
    payload = {}
    if not show_only:
        try:
            payload = json.loads(sys.stdin.read() or "{}")
        except (ValueError, OSError):
            gate.allow()
        if payload.get("hook_event_name") != "Stop":
            gate.allow()
        if payload.get("stop_hook_active"):
            gate.allow()

    root = gate.repo_root(payload)
    if os.environ.get(gate.ESCAPE_ENV):
        gate.allow()
    if root and os.path.exists(os.path.join(root, ".claude", gate.ESCAPE_FILE)):
        gate.allow()

    sid = gate.session_key(payload)
    excerpt = armed_excerpt(sid)
    if show_only:
        print("session {}: {}".format(sid or "(unknown)",
                                      "ARMED on \"{}\"".format(excerpt) if excerpt else "not armed, silent"))
        return 0
    if not excerpt:
        gate.allow()

    final = last_assistant_text(payload.get("transcript_path") or "")
    promise = promise_in(final)
    if not promise:
        gate.allow()

    budget = gate.budget_path(sid) + ".promise-blocks"
    used = gate.blocks_so_far(budget)
    if used >= MAX_BLOCKS:
        gate.allow()
    gate.note_block(budget, used + 1)
    print(json.dumps({"decision": "block", "reason": reason_text(promise, excerpt)},
                     ensure_ascii=False))
    return 0


# ---------------------------------------------------------------------------
def self_test():
    # [REDACTED H28: the pinned self-test samples are French, quote the operator or name
    # third-party platforms; the public tests are e1/tests/test_public_hooks.py.]
    print("stop_promise_gate self-test: redacted in the public copy")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# [REDACTED H29: a trailing comment block that dates the incident and quotes the operator.]
