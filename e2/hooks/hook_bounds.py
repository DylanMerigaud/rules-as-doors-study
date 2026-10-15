"""The bounds every gate hook of the harness shares.

Public copy of the module pinned for experiment E2 (`hook_bounds.py`, sha256 104596746e1565f1...).
Code lines are the pinned ones; every edit is marked in place and listed in
`e2/REDACTIONS.md` (H markers: E1's redactions of the same pinned lines, carried
unchanged; J markers: new in E2).
[REDACTED J41: the history of the module, which names private paths and plans. In gist,
what changed on 2026-09-30: the two escapes (an environment variable and a marker file) are
gone; the per-session budget is gone, a Stop gate counts its consecutive blocks inside one
stop chain and lets go at hook_trace.CHAIN_CAP with a `cap` row and a systemMessage; an error
or a timeout lets the action through and is recorded in a health ledger, an autofix record
and a systemMessage. The mechanics live in `hook_trace.py`. Tests pass `--home DIR` (an
argument, never an environment variable) and every ledger, state file and script the gate
touches resolves under DIR.]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "hooks-global"))
import hook_trace  # noqa: E402

ENV_SESSION = hook_trace.ENV_SESSION
CHAIN_CAP = hook_trace.CHAIN_CAP

configure = hook_trace.configure
run = hook_trace.run
read_payload = hook_trace.read_payload
chain_should_block = hook_trace.chain_should_block
chain_clear = hook_trace.chain_clear
cap_message = hook_trace.cap_message


def allow():
    """End the hook here: the action proceeds. Only ever called on a decision, never on doubt
    (doubt is an error, and an error goes through run())."""
    sys.exit(0)


def session_key(payload):
    return hook_trace.session_key(payload or {})


def budget_path(session_id):
    """The per-session state stem (the promise gate's arm marker hangs off it)."""
    return hook_trace.session_file(session_id, "")


def final_text(payload, transcript_reader):
    """The final assistant text of the turn: `last_assistant_message` from the Stop payload
    first (the transcript is written asynchronously and can lag the current turn, per the
    Claude Code hooks reference), the transcript only when the payload does not carry it."""
    msg = (payload or {}).get("last_assistant_message")
    if isinstance(msg, str) and msg.strip():
        return msg
    return transcript_reader((payload or {}).get("transcript_path") or "")


def witness(door, event, reason_class, payload=None):
    """Count a refusal in [REDACTED J42: a private ledger and its door] through the
    one witness of hook_trace, with THIS checkout's door ledger (a worktree's own copy under
    test, the hub's in production) unless `--home` pointed it at a fixture. Never changes the
    decision the caller already took."""
    script = None if hook_trace.home() else os.path.join(os.path.dirname(HERE), "scripts",
                                                         "door_ledger.py")
    return hook_trace.witness(door, event, reason_class, payload, script=script)


def repo_root(payload):
    """The harness repository root, or None when we are not in it. [REDACTED H42: the repository name.]

    The payload's `cwd` first (it follows a worktree), then CLAUDE_PROJECT_DIR, then this
    file's grandparent. The only test of membership is the write door. [REDACTED H43: its file name.]
    """
    for cand in ((payload or {}).get("cwd"), os.environ.get("CLAUDE_PROJECT_DIR"),
                 os.path.dirname(HERE)):
        if not cand:
            continue
        here = cand
        for _ in range(6):      # a session may run in a subdirectory
            if os.path.isfile(os.path.join(here, "REDACTED_H43.py")) \
                    and os.path.exists(os.path.join(here, "REDACTED_H43.db")):
                return here
            parent = os.path.dirname(here)
            if parent == here:
                break
            here = parent
    return None
