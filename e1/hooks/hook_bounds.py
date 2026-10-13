"""The bounds every Stop hook of the harness shares.

Public copy of the module pinned for E1 (sha256 6f3978259b6c7744...). [REDACTED H41: the history of
the module, which names private paths.]

What a bound is for, and none of it is loosened from the original:

- A SESSION KEY, from the hook payload or the environment. Both carry the same value (verified
  2026-08-17 by comparing a live session's budget file to the hash of the variable), which is
  what lets `--arm` from a shell leave a marker the Stop hook then reads.
- A BUDGET, one file per session under the system temp dir, never in the repo: a versioned
  counter would dirty the tree at every session end, and one session's state has no business
  in the history. A hook may block MAX_BLOCKS times and then lets go, because a gate that
  never lets go is a gate someone disables for good.
- TWO ESCAPES, an env var and a file, both checked before anything else.
- `allow()`, the one exit on doubt: every unknown ends the hook by letting the session end.
"""
import hashlib
import os
import sys
import tempfile

ENV_SESSION = "CLAUDE_SESSION_ID"
ESCAPE_ENV = "REDACTED_H43_NO_STOP_GATE"  # [REDACTED H43: the repository name]
ESCAPE_FILE = "no-stop-gate"
MAX_BLOCKS = 3          # per session, and it is a hard ceiling
BUDGET_DIR = "redacted-h43-stop-gate"  # [REDACTED H43: the repository name]


def allow():
    """Let the session end. The only exit on doubt."""
    sys.exit(0)


def session_key(payload):
    return (payload or {}).get("session_id") or os.environ.get(ENV_SESSION, "")


def budget_path(session_id):
    key = hashlib.sha256((session_id or "sans-id").encode("utf-8")).hexdigest()[:16]
    d = os.path.join(tempfile.gettempdir(), BUDGET_DIR)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, key)


def blocks_so_far(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return int(fh.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def note_block(path, n):
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(str(n))
    except OSError:
        pass            # a budget we cannot write is not a reason to break the session


def repo_root(payload):
    """The harness repository root, or None when we are not in it. [REDACTED H42: the repository name.]

    The payload's `cwd` first (it follows a worktree), then CLAUDE_PROJECT_DIR, then this
    file's grandparent. The only test of membership is the write door. [REDACTED H43: its file name.]
    """
    for cand in ((payload or {}).get("cwd"), os.environ.get("CLAUDE_PROJECT_DIR"),
                 os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
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
