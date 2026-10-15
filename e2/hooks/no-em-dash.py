#!/usr/bin/env python3
"""Public copy of the hook pinned for experiment E2 (`no-em-dash.py`, sha256 92e49b601cc6373c...).
Code lines are the pinned ones; every edit is marked in place and listed in
`e2/REDACTIONS.md` (H markers: E1's redactions of the same pinned lines, carried
unchanged; J markers: new in E2).

Stop hook: refuse to end the turn when the final message carries a forbidden dash.

Why this exists as CODE and not as a line in CLAUDE.md: the rule was in CLAUDE.md the whole
time and lost twice in one day, both times to a reading rather than to disagreement. Prose can
be scoped, qualified, and argued with. A string search cannot.

IT DID NOT BLOCK, FROM 2026-08-23 TO 2026-09-30, AND THIS IS WHY. Measured on every main-session
transcript [REDACTED J51: a private path] on 2026-09-30: 293 detections between 2026-08-31 and
2026-09-29, and 0 of them produced a blocking row (`hook_blocking_error` or a "Stop hook
feedback" message); 281 were followed by nothing at all, and of the 12 turns that did go on
(because ANOTHER Stop gate blocked), 8 still carried the dash. Two causes:
  1. The block was written as `{"hookSpecificOutput": {"hookEventName": "Stop", "decision":
     "block", ...}}`. For Stop, Claude Code reads `decision` at the TOP level (or exit code 2);
     inside hookSpecificOutput it is an unrecognized key, dropped without an error. Only the
     `systemMessage` next to it survived, so the user read "Blocked" and the turn ended. The
     old "KNOWN LIMIT" note (claude -p ignores the block) was this same bug, misread.
  2. `stop_hook_active` returned early, so a re-answer forced by another gate was never
     checked, which is where the 8 of 12 come from.
Fixed: a violation exits 2 with the reason on stderr (the documented Stop block, which shows in
the transcript as `hook_blocking_error`), and the re-answers of a stop chain are checked like the
first one, up to hook_trace.CHAIN_CAP blocks in a row. Pinned by [REDACTED J52: the
repository's name and a test file], which replays a final message carrying the dash and asserts exit 2
and a reason.

WHAT IT CHECKS: the closing text of the turn, `last_assistant_message` [REDACTED H44: two words], which the
Stop payload hands over directly. The transcript is deliberately not read: it lags the
in-memory conversation and may not hold the current turn's text yet.

WHAT IT DELIBERATELY DOES NOT CHECK: anything inside a fenced code block or inline backticks.
Quoting a diff, a file, or a tool's own output that already contains the character is not the
failure this gate exists for, and a checker that fires on faithful quoting teaches you to
ignore checkers. To talk ABOUT the character, put it in backticks. That is the rule's own
exemption, not a bypass: the character never reaches prose.

ERRORS ARE LOUD, NEVER SILENT. A crash or a timeout lets the turn end (a hook on the Stop path
that can wedge a session is worse than the typography it polices) and is written to
analytics/hook-health.jsonl, reported to autofix and shown to the user: hook_trace.crashed().
Every block is counted in [REDACTED J53: the repository's name and a task id] door ledger
(hook_trace.witness). No
environment variable and no marker file turns this gate off.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hook_trace  # noqa: E402

HOOK = "no-em-dash.py"
TIMEOUT_S = 8

# em, en, figure, horizontal bar. Written as codepoints so this file stays clean under a grep
# for the characters it refuses.
BAD = {0x2014: "em-dash", 0x2013: "en-dash", 0x2012: "figure dash", 0x2015: "horizontal bar"}

FENCED = re.compile(r"^[ \t]*```.*?^[ \t]*```", re.MULTILINE | re.DOTALL)
INLINE = re.compile(r"`[^`\n]*`")


def offenders(text):
    """[(name, context)] for each forbidden dash in prose. Context so it can be found fast."""
    prose = INLINE.sub("", FENCED.sub("", text))
    found = []
    for i, ch in enumerate(prose):
        name = BAD.get(ord(ch))
        if not name:
            continue
        snippet = prose[max(0, i - 40):i + 40].replace("\n", " ")
        found.append((name, snippet.strip()))
    return found


def reason_text(found):
    lines = ["{} occurrence(s) of a forbidden dash in the message you were about to send. "
             "Rewrite those sentences and answer again.".format(len(found))]
    for name, snippet in found[:6]:
        lines.append("  {}: ...{}...".format(name, snippet))
    if len(found) > 6:
        lines.append("  and {} more.".format(len(found) - 6))
    lines.append("")
    lines.append("Use a comma, a colon, parentheses, or a new sentence. The ASCII hyphen is "
                 "fine. To talk about the character itself, put it in backticks: code spans "
                 "and fenced blocks are not checked.")
    return "\n".join(lines)


def body():
    payload = hook_trace.read_payload()
    message = payload.get("last_assistant_message")
    found = offenders(message) if isinstance(message, str) and message else []
    if not found:
        hook_trace.chain_clear(HOOK, payload)
        return 0
    detail = "{} dash(es): {}".format(len(found), found[0][1])
    if not hook_trace.chain_should_block(HOOK, payload, detail):
        print(hook_trace.cap_message(HOOK, detail))
        return 0
    hook_trace.witness("no-em-dash", "Stop", "forbidden_dash", payload)
    sys.stderr.write(reason_text(found) + "\n")
    return 2


def main():
    hook_trace.configure(sys.argv)
    return hook_trace.run(HOOK, "Stop", body, TIMEOUT_S)


if __name__ == "__main__":
    sys.exit(main())
