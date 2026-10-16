# Redactions in the published E2 material

E2 ran on E1's pinned instruction file (its published paragraphs are E1's, `e1/treatment/`, with
E1's redactions) and on the hooks as live from 2026-09-30 17:32 +0200 (`prereg/PREREG-E2.md`
section 4). The public copies of those hooks are in `hooks/`. Their code lines are the pinned
ones; every cut is marked in place and listed here. Nothing is cut silently.

Two series of markers:

- **H markers** are E1's redactions (`e1/REDACTIONS.md`), carried unchanged onto the same pinned
  lines: the detectors and their patterns did not change between E1's pins and E2's, so each
  redacted alternative, refusal text, self-test and trailing block is cut the same way.
- **J markers** are new: text that exists only in the E2 pins (the delivery modules and the
  docstrings rewritten by the repair).

| Id | File | What was cut or changed |
|---|---|---|
| J11 | stop_ask_gate.py | the module docstring (incident history, quotes of the operator partly in French, private paths); its part on the delivery bounds is kept in gist |
| J21 | stop_promise_gate.py | the module docstring (same reasons); its part on the bounds and on reading the payload text is kept in gist |
| J22 | stop_promise_gate.py | the history of the shared module, in a comment |
| J29 | stop_promise_gate.py | a trailing comment block that dates the incident and quotes the operator |
| J31 | stop_rule_gate.py | the module docstring (same reasons as J11); its part on the bounds is kept in gist |
| J39 | stop_rule_gate.py | a trailing comment block that dates the incident and quotes the operator |
| J41 | hook_bounds.py | the module docstring (history, private plan and paths); what changed on 2026-09-30 is kept in gist |
| J42 | hook_bounds.py | a private ledger and its door, named in a docstring |
| J51 | no-em-dash.py | a private path in the docstring |
| J52 | no-em-dash.py | the repository's name and a test file, in the docstring |
| J53 | no-em-dash.py | the repository's name and a task id, in the docstring |
| J54 | no-em-dash-write.py | the repository's name and a task id, in the docstring |
| J61 | hook_trace.py | the module docstring (the audit that led to it, private paths, plans, repositories); its mechanics are kept in gist |
| J62 | hook_trace.py | the repository's path and name in two string literals (`HUB`, `STATE_NAME`). Both are read only without `--home`, and every E2 hook command passes `--home`, so the renamed literals behave as the pinned ones did in E2 |
| J63 | hook_trace.py | the repository's name and its door ledger, named in a docstring |
| J64 | hook_trace.py | one docstring sentence on what the client passes on stdin |

`no-em-dash.py` and `no-em-dash-write.py` keep the rest of their docstrings, including the
account of why the long-dash Stop hook did not block before the repair.

The module that E1's question-tool hook imported (`rc_activity.py`) and the question-tool hook
itself are not part of E2 (`prereg/PREREG-E2.md` section 3).

Effect of the cuts on E2: none on the decisions. On every E1 run text and closing text (572), the
six case prompts and the proof samples, each of the six detectors of the public copies gives the
same answer as the pinned E2 hook and as E1's public copy: 0 differences (the first comparison
needs the private pins; the second is `tests/test_hooks_e2.py`). Run as hooks on planted Stop and
PreToolUse payloads (a violating and a clean one per hook, first answer and re-answer), the public
copies and the pins return the same exit code and the same decision in 18 of 18 cases.

## The run records (`runs.jsonl`, R60)

Built with E1's rules (`e1/REDACTIONS.md`, R60): a word of a run's text, file, commit or write
call that matches the private list of third-party names would be replaced by `[REDACTED R60]`.
No word of the 220 E2 records matched, so `runs.jsonl` carries no R60 marker. One substitution
is new for E2: the machine's temporary-directory prefix in front of each run's scratch
directory is written as `/tmp/`, so paths read `/tmp/e2-scratch/...` as E1's read
`/tmp/e1-scratch/...`; the builder refuses to write a string that still holds another absolute
path of the machine, and `e2/tests/test_regrade_e2.py` checks the file for one. It also refuses
a string that shares a passage of eight words with the unpublished part of the instruction file
(none did). The regrade reads the same records and agrees with `results.jsonl` on every field.
