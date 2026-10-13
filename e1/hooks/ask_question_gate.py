"""PreToolUse hook on the question tool: a question names its class or is refused.

Public EXCERPT of the hook pinned for E1 (sha256 4b17a4d7980961c9...): its detector only. [REDACTED H51:
the docstring, the refusal text, the main function and the self-test, which quote the
operator in French and name private paths and the remote-control module it imports.] In E1 the
hook was registered in C1's door arms but never ran: the coding agent offers no question tool
in non-interactive runs (prereg/DEVIATIONS.md, deviation 1).
"""
import re

CLASS_RE = re.compile(r"\b(knowledge|irreversible|absent)\b", re.I)


def question_text(q: dict) -> str:
    parts = [str(q.get("question") or ""), str(q.get("header") or "")]
    for opt in q.get("options") or []:
        if isinstance(opt, dict):
            parts.append(str(opt.get("label") or ""))
            parts.append(str(opt.get("description") or ""))
    return "\n".join(parts)


def unclassed(tool_input: dict) -> list[str]:
    """The questions naming no class. Empty means the call passes. Pure."""
    bad = []
    for q in (tool_input or {}).get("questions") or []:
        if not isinstance(q, dict):
            continue
        if not CLASS_RE.search(question_text(q)):
            bad.append(str(q.get("question") or "")[:120])
    return bad
