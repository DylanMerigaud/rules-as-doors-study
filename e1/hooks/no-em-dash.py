#!/usr/bin/env python3
"""Public copy of the hook pinned for E1 (sha256 e3de9287bc209340...), unredacted.

Stop hook: refuse to end the turn when the final message carries a forbidden dash.

Why this exists as CODE and not as a line in CLAUDE.md: the rule was in CLAUDE.md the whole
time and lost twice in one day, both times to a reading rather than to disagreement. Prose can
be scoped, qualified, and argued with. A string search cannot.

WHAT IT CHECKS: the closing text of the turn, `last_assistant_message` [REDACTED H44: two words], which the
Stop payload hands over directly. The transcript is deliberately not read: it lags the
in-memory conversation and may not hold the current turn's text yet.

WHAT IT DELIBERATELY DOES NOT CHECK: anything inside a fenced code block or inline backticks.
Quoting a diff, a file, or a tool's own output that already contains the character is not the
failure this gate exists for, and a checker that fires on faithful quoting teaches you to
ignore checkers. It also leaves the escape hatch that makes the gate liveable: to talk ABOUT
the character, put it in backticks.

KNOWN LIMIT, measured on 2026-08-23 with Claude Code 2.1.241: `claude -p` runs this hook and
receives its block decision, then ends the turn anyway. Verified by logging both sides, the
payload arriving correct and the block being emitted, with the offending output still returned.
So this gate covers interactive sessions only. Headless and subagent output is NOT gated.

FAIL OPEN, ALWAYS. Any unexpected input, any exception, exit 0 and let the turn end. A hook on
the Stop path that can wedge a session is worse than the typography it polices.
"""
import json
import re
import sys

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


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    # Claude Code already ignores a block on the second pass, but returning early keeps the
    # turn from paying for this check twice and makes the intent obvious to anyone reading it.
    if payload.get("stop_hook_active"):
        return 0

    message = payload.get("last_assistant_message")
    if not isinstance(message, str) or not message:
        return 0

    try:
        found = offenders(message)
    except Exception:
        return 0
    if not found:
        return 0

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
    reason = "\n".join(lines)

    json.dump({
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "decision": "block",
            "reason": reason,
        },
        "systemMessage": "Blocked: {} forbidden dash(es) in the reply.".format(len(found)),
    }, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
