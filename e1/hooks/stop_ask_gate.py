#!/usr/bin/env python3
"""Stop hook: a turn does not end on an unclassed question to the operator.

Public copy of the hook pinned for experiment E1 (`stop_ask_gate.py`, sha256 f5e2410acd045920...).
Code lines are the pinned ones; every edit is marked [REDACTED Hnn] in place and listed in
`e1/REDACTIONS.md`. [REDACTED H11: the original module docstring, which tells the incident
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
import hook_bounds as gate  # noqa: E402

MAX_BLOCKS = 2
TIMEOUT_S = 8
TAIL_CHARS = 800

# [REDACTED H12: CONTRACT_TEXT, a verbatim copy of the rule paragraph (published, redacted,
# in e1/treatment/C1-K039.md); no function of this hook reads it.]
CONTRACT_TEXT = "[REDACTED H12]"

# A genuine decision-request aimed at the operator, in the closing block. [REDACTED H13: the
# incident it was calibrated on.]
ASK_RE = re.compile(r"""
    (?!x)x  # [REDACTED H14: one alternative in French]
  | \boption\s+a\b.{0,150}\boption\s+b\b
  | which\s+(?:one|option)\s+(?:do\s+you|would\s+you)
  | do\s+you\s+want\s+me\s+to\b
  | should\s+I\b
  | go\s+on\s+(?:option|which)\b
  | (?!x)x  # [REDACTED H14: two alternatives in French]
""", re.I | re.X | re.S)

# The class an ask must name, in the same window: three literal words. [REDACTED H15: the
# private file that shares them.]
CLASS_RE = re.compile(r"\b(knowledge|irreversible|absent)\b", re.I)


def ask_without_class(final_text):
    """The matched ask phrase when the tail asks a decision of Dylan with no class named nearby,
    else None. Both regexes run on the SAME window: a class named earlier in a long message, far
    from the actual ask, is not what makes the closing block legible."""
    tail = (final_text or "")[-TAIL_CHARS:]
    m = ASK_RE.search(tail)
    if not m:
        return None
    if CLASS_RE.search(tail):
        return None
    return m.group(0)


def last_assistant_text(transcript_path):
    """The text of the last assistant row of a Claude Code transcript, or ''. Duplicated from
    `stop_promise_gate.py` on purpose: a Stop hook that imports another Stop hook's internals
    couples two files that are edited by different incidents, one for a mismatch neither owns."""
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


def reason_text(asked):
    # [REDACTED H16: the refusal text names the operator's instruction file path and a
    # private replay case; its gist is kept.]
    return ('The closing block asks a question ("{}") without naming which class it is. '
            'Name the class (knowledge, irreversible, absent) inline, or resolve it '
            'yourself and report it as done.'.format(asked))


def main():
    if "--self-test" in sys.argv:
        return self_test()
    signal.signal(signal.SIGALRM, lambda *_: gate.allow())
    signal.alarm(TIMEOUT_S)

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

    if show_only:
        print("stop_ask_gate: would check the final message's closing block for an unclassed ask.")
        return 0

    final = last_assistant_text(payload.get("transcript_path") or "")
    asked = ask_without_class(final)
    if not asked:
        gate.allow()

    sid = gate.session_key(payload)
    budget = gate.budget_path(sid) + ".ask-blocks"
    used = gate.blocks_so_far(budget)
    if used >= MAX_BLOCKS:
        gate.allow()
    gate.note_block(budget, used + 1)
    print(json.dumps({"decision": "block", "reason": reason_text(asked)}, ensure_ascii=False))
    return 0


# ---------------------------------------------------------------------------
def self_test():
    # [REDACTED H17: the pinned self-test samples are French, quote the operator or name
    # third-party platforms; the public tests are e1/tests/test_public_hooks.py.]
    print("stop_ask_gate self-test: redacted in the public copy")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# [REDACTED H18: a trailing comment block that dates the incident and quotes the operator.]
