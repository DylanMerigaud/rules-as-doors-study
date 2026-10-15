#!/usr/bin/env python3
"""Public copy of the hook pinned for experiment E2 (`no-em-dash-write.py`, sha256 70e1d9844c06351c...).
Code lines are the pinned ones; every edit is marked in place and listed in
`e2/REDACTIONS.md` (H markers: E1's redactions of the same pinned lines, carried
unchanged; J markers: new in E2).

PreToolUse hook: refuse to WRITE a forbidden dash into a file.

The Stop hook next to this one guards what Claude SAYS. This one guards what Claude STORES,
and it exists because the Stop hook does not run in headless `--bare` runs, so every such worker
would write ungated.

IT HAS TO COVER BASH, and that is not a guess. Counted over the session that produced it:
0 Write tool calls, 0 Edit tool calls, 175 Bash calls carrying a heredoc or a redirect. A gate
on Write and Edit alone would have inspected exactly nothing.

WHAT IS CHECKED
  Write         tool_input.content
  Edit          tool_input.new_string
  NotebookEdit  tool_input.new_source
  Bash          heredoc bodies in full, plus each command SEGMENT that redirects, tees, or
                edits in place. Segments are split on the shell separators, not on pipes, so
                `printf <dash> | tee f` is still caught while `grep <dash> f` stays allowed.
                Per segment, not per command: the first live run of this hook denied a compound
                command whose redirect and whose dash were in different halves, the dash half
                being a grep. Auditing files for these dashes is a thing you legitimately do,
                and a gate that blocks the audit gets switched off the same day.

NO CODE-FENCE EXEMPTION, unlike the Stop hook. A dash in a file is a dash in a file; there is
no "quoting someone else" once it is on disk under your name.

THE RULE'S OWN ESCAPE, and it is the only one: write the codepoint instead of the character.
`\\u2014` in JSON, YAML and JavaScript, `chr(0x2014)` in Python, `&mdash;` in HTML. That keeps the
file greppable for the literal character, which is the property that makes the rule checkable at
all. The session-wide switch this file used to honour (an environment variable) is gone since
2026-09-30: the rule names no such exemption ("A rule is a door, not a sentence").

EVERY DENY IS COUNTED, EVERY ERROR IS LOUD. A deny is counted in [REDACTED J54: the repository's name and a task
id] door ledger (hook_trace.witness). A crash or a timeout lets the write through (a PreToolUse
hook that can wedge every write in a session is worse than the typography it polices) and is
written to analytics/hook-health.jsonl, reported to autofix and shown to the user. Never a
silent pass.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hook_trace  # noqa: E402

HOOK = "no-em-dash-write.py"
TIMEOUT_S = 8

BAD = {0x2014: "em-dash", 0x2013: "en-dash", 0x2012: "figure dash", 0x2015: "horizontal bar"}

# Does this shell command put bytes into a file? Deliberately loose on the write side and
# deliberately silent on everything else: a false deny costs a blocked command, a false allow
# costs one dash on disk, and only the first one trains you to switch the hook off.
WRITES = re.compile(r">>?\s*\S|\btee\b|\bsed\b[^|]*-i|\bdd\b")

# Heredoc bodies are pulled out and judged whole, because a body is content by definition and
# because it can contain the separators the segment splitter uses.
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1\n(.*?)^\s*\2\s*$",
                     re.DOTALL | re.MULTILINE)

# Everything else is judged PER SEGMENT. The first live use of this hook denied
#   echo clean > a.txt ; grep <dash> b.txt
# because the command as a whole held both a redirect and a dash, while the redirect was in one
# segment and the dash in another that only READS. Pipes are NOT separators here:
# `printf <dash> | tee f` really does write the character.
SEGMENTS = re.compile(r"&&|\|\||;|\n")

FIELD = {
    "Write": "content",
    "Edit": "new_string",
    "NotebookEdit": "new_source",
}


def scan(text):
    found = []
    for i, ch in enumerate(text):
        name = BAD.get(ord(ch))
        if name:
            snippet = text[max(0, i - 40):i + 40].replace("\n", " ")
            found.append((name, snippet.strip()))
    return found


def payload_text(tool, tool_input):
    """The string this call would persist, or None when there is nothing to check."""
    if tool in FIELD:
        value = tool_input.get(FIELD[tool])
        return value if isinstance(value, str) else None
    if tool == "Bash":
        cmd = tool_input.get("command")
        if not isinstance(cmd, str):
            return None
        parts = []
        rest = cmd
        for match in HEREDOC.finditer(cmd):
            parts.append(match.group(3))          # a heredoc body is content, always checked
            rest = rest.replace(match.group(0), " ")
        for segment in SEGMENTS.split(rest):
            if WRITES.search(segment):
                parts.append(segment)
        return "\n".join(parts) or None
    return None


def body():
    payload = hook_trace.read_payload()
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    text = payload_text(tool, tool_input)
    found = scan(text) if text else []
    if not found:
        return 0

    where = "the command" if tool == "Bash" else "the content"
    lines = ["{} forbidden dash(es) in {} of this {} call. The write is refused.".format(
        len(found), where, tool)]
    for name, snippet in found[:5]:
        lines.append("  {}: ...{}...".format(name, snippet))
    if len(found) > 5:
        lines.append("  and {} more.".format(len(found) - 5))
    lines.append("Rewrite with a comma, a colon, parentheses, or a new sentence. If the "
                 "character is genuinely required, write it as an escape so the file stays "
                 "greppable: \\u2014 in JSON, YAML or JS, chr(0x2014) in Python, &mdash; in "
                 "HTML.")
    reason = "\n".join(lines)
    hook_trace.witness("no-em-dash-write", "PreToolUse", "forbidden_dash_write", payload)
    json.dump({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }, sys.stdout)
    return 0


def main():
    hook_trace.configure(sys.argv)
    return hook_trace.run(HOOK, "PreToolUse", body, TIMEOUT_S)


if __name__ == "__main__":
    sys.exit(main())
