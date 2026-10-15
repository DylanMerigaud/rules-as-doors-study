#!/usr/bin/env python3
"""Stop hook: a final message does not announce a new behavioural rule with no door.

Public copy of the hook pinned for experiment E2 (`stop_rule_gate.py`, sha256 f89ac2f297375f69...).
Code lines are the pinned ones; every edit is marked in place and listed in
`e2/REDACTIONS.md` (H markers: E1's redactions of the same pinned lines, carried
unchanged; J markers: new in E2).
[REDACTED J31: the original module docstring, which tells the incident history of
the hook, quotes the operator (partly in French) and names private paths. Its part on the delivery bounds since 2026-09-30, in gist: the re-answer of a stop chain is
checked like the first answer; the gate lets go after CHAIN_CAP blocks in a row in one
chain, with a recorded `cap` row and a systemMessage; no environment variable and no marker
file turns it off; `hook_event_name` must be "Stop"; an error or a timeout lets the turn
end and is recorded.]
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hook_bounds as gate  # noqa: E402

HOOK = "stop_rule_gate.py"
TIMEOUT_S = 8
TAIL_CHARS = 1600

# A quoted verbatim of the operator's words is not an announcement of ours: a markdown blockquote
# line, or a span wrapped in *"..."*.
QUOTE_LINE_RE = re.compile(r"^>.*$", re.M)
QUOTE_SPAN_RE = re.compile(r'\*"[^"]*"\*')


def strip_quotes(text):
    text = QUOTE_SPAN_RE.sub(" ", text)
    text = QUOTE_LINE_RE.sub(" ", text)
    return text


def sentences(text):
    """Rough sentence split: good enough to scope a marker to its own subject."""
    return [s for s in re.split(r"(?<=[.!?])\s+|\n{2,}", text) if s.strip()]


# A behavioural-rule announcement. [REDACTED H32: the calibration incident; four of the seven
# alternatives are French and are replaced below.]
PHRASE_RE = re.compile(r"""
    \bfrom\s+now\s+on\b
  | (?!x)x  # [REDACTED H33: two alternatives in French]
  | \bnever\s+again\b
  | (?!x)x  # [REDACTED H33: one alternative in French]
  | \bevery\b[^.!?\n]{0,60}?\bmust\b
  | (?!x)x  # [REDACTED H33: one alternative in French]
""", re.I | re.X)

RULE_LABEL_RE = re.compile(r"\b(?:rule)\s*:", re.I)  # [REDACTED H34: the French noun removed]

# "always" is only a rule marker when it is applied to a process of ours: paired,
# in the same short span, with a first-person subject or a verb that names a process action.
ALWAYS_RE = re.compile(r"""
    \b(?:i(?:'ll|\s+will)?|we|claude|this\s+session|this\s+gate|this\s+hook|this\s+door)\b
    [^.!?\n]{0,60}?\b(?:always)\b  # [REDACTED H34: the French adverb removed]
  | \b(?:always)\b[^.!?\n]{0,60}?  # [REDACTED H34: the French adverb removed]
    \b(?:run|runs|check|checks|refuse|refuses|block|blocks|verify|verifies|enforce|enforces|
        ensure|ensures|commit|commits|gate|gates|route|routes|name|names|ask|asks|do|does)\b
""", re.I | re.X)

HEADING_RE = re.compile(r"^#{1,6}\s*(?:rule)\b", re.I | re.M)  # [REDACTED H34: the French noun removed]

# A sentence whose subject is a third party's rule, not ours, is excluded. [REDACTED H35: the
# pinned list names 28 vendors and platforms; it is replaced by an empty list, and the
# expression below then matches only a sentence opening on "the".]
VENDOR_NAMES = ()
VENDOR_SUBJECT_RE = re.compile(
    r"^\s*(?:the\s+)?(?:" + ("|".join(re.escape(n) for n in VENDOR_NAMES) or '(?!x)x') + r")\b"  # [REDACTED H35]
    r"[^.!?\n]{0,80}?\b(?:rule|rules|policy|policies|limit|limits|cap|caps|requires?|allows?|"
    r"rejects?|bans?|restricts?|throttles?)\b",
    re.I,
)

# A path under one of the prefixes the harness enforces rules from. [REDACTED H36: three of the
# seven prefixes are private paths of the harness repository and are replaced by a pattern
# that never matches.]
PATH_RE = re.compile(
    r"(?<!\w)(?:scripts|sched|\.claude|tests|(?!x)x)/"
    r"[\w./-]*\w"
)


def load_hook_basenames(root):
    """Bare filenames of every hook command in `.claude/settings.json`, read live so a hook
    added or renamed there is picked up without editing this file."""
    names = set()
    if not root:
        return names
    path = os.path.join(root, ".claude", "settings.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return names
    for entries in (data.get("hooks") or {}).values():
        for entry in entries:
            for h in entry.get("hooks", []):
                cmd = h.get("command") or ""
                names.update(re.findall(r"[\w][\w.\-]*\.(?:py|sh)\b", cmd))
    return names


def path_named(text, root):
    if PATH_RE.search(text):
        return True
    for name in load_hook_basenames(root):
        if re.search(r"(?<![\w.\-])" + re.escape(name) + r"(?![\w.\-])", text):
            return True
    return False


def find_marker(window):
    """The matched marker text in `window`, honouring the vendor-subject exclusion, or None.
    A heading is always ours (no vendor filter: a heading is not a description of a third
    party's rule); every other marker is scoped to the sentence it appears in."""
    m = HEADING_RE.search(window)
    if m:
        return m.group(0).strip()
    for s in sentences(window):
        if VENDOR_SUBJECT_RE.match(s.strip()):
            continue
        for rx in (PHRASE_RE, RULE_LABEL_RE, ALWAYS_RE):
            m = rx.search(s)
            if m:
                return m.group(0)
    return None


def rule_without_door(final_text, root):
    """The matched rule-announcement marker when the closing block announces a new behavioural
    rule with no enforcing path named anywhere in the message, else None."""
    stripped = strip_quotes(final_text or "")
    if not stripped.strip():
        return None
    window = stripped[-TAIL_CHARS:]
    marker = find_marker(window)
    if not marker:
        return None
    if path_named(stripped, root):
        return None
    return marker


def last_assistant_text(transcript_path):
    """The text of the last assistant row of a Claude Code transcript, or ''. Duplicated from
    the other Stop gates on purpose: a hook that imports another hook's internals couples two
    files that are edited by different incidents, one for a mismatch neither owns."""
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


def reason_text(marker):
    # [REDACTED H37: the refusal text lists private paths and a private replay case; its gist is kept.]
    return ('The closing block announces a new behavioural rule ("{}") with no enforcing path '
            'named anywhere in the message. Name the file that refuses when the rule is broken, '
            'or build it before ending.'.format(marker))


def on_stop():
    payload = gate.read_payload()
    if payload.get("hook_event_name") != "Stop":
        return 0
    marker = rule_without_door(gate.final_text(payload, last_assistant_text),
                               gate.repo_root(payload))
    if not marker:
        gate.chain_clear(HOOK, payload)
        return 0
    if not gate.chain_should_block(HOOK, payload, "rule marker: " + marker):
        print(gate.cap_message(HOOK, "rule marker: " + marker))
        return 0
    gate.witness("stop_rule_gate", "Stop", "rule_no_door", payload)
    print(json.dumps({"decision": "block", "reason": reason_text(marker)}, ensure_ascii=False))
    return 0


def main():
    gate.configure(sys.argv)
    if "--self-test" in sys.argv:
        return self_test()
    if "--print" in sys.argv:
        print("stop_rule_gate: would check the final message for a rule announced with no door.")
        return 0
    return gate.run(HOOK, "Stop", on_stop, TIMEOUT_S)


# ---------------------------------------------------------------------------
def self_test():
    # [REDACTED H38: the pinned self-test samples are French, quote the operator or name
    # third-party platforms; the public tests are e1/tests/test_public_hooks.py.]
    print("stop_rule_gate self-test: redacted in the public copy")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# [REDACTED J39: a trailing comment block that dates the incident and quotes the operator.]
