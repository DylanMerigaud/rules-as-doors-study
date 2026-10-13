# Redactions in the published E1 material

E1 ran on a private instruction file and private hooks, pinned on 2026-09-30 at 16:27 +0200
(`prereg/PREREG.md` section 4). What the arms changed is published here, with every cut marked in
place by `[REDACTED <id>: what was cut]` and listed below. Nothing is cut silently. Three reasons
recur: the text quotes the operator (often in French), it names a private path, replay case or
repository, or it names an activity outside the domain sentence of the top-level `README.md`.

## The five ablated paragraphs (`treatment/`, series R01 to R17)

Each file gives the pinned line range, the arms that carry the paragraph, the sha256 of the
unredacted lines and their word count, so a holder of the pinned file can check the copy.

| Id | File | What was cut |
|---|---|---|
| R01 | C4-K001.md | an HTML marker naming a private replay case |
| R02 | C4-K001.md | one word (twice) |
| R03 | C4-K001.md | the path of a private replay case |
| R04 | none | not used |
| R05 | C1-K039.md | a verbatim quote of the operator in French, two sentences (its gist is given) |
| R06 | C1-K039.md | two examples outside the study's domain sentence |
| R07 | C2-K033.md | an HTML marker naming a private replay case |
| R08 | C2-K033.md | one example in French |
| R09 | C2-K033.md | one example that names an activity outside the domain sentence |
| R10 | C3-K029.md | two examples that name an activity outside the domain sentence |
| R11 | C3-K029.md | the name of a private memory note |
| R12 | C3-K029.md | the repository's name and the hook's directory |
| R13 | C3-K029.md | a private replay case |
| R14 | C5-K004.md | an HTML marker naming a private replay case |
| R15 | C5-K004.md | a verbatim quote of the operator in French, one sentence (its gist is given) |
| R16 | C5-K004.md | three examples: two private identifiers and one that names an activity outside the domain sentence |
| R17 | C5-K004.md | one sentence on how to name a person and a company (third-party data) |

The rest of the pinned instruction file, present in every arm, is not published. The lines of it
that touch the five doors are named in `e1/README.md`.

## The pinned hooks (`hooks/`, series H11 to H51)

Code lines are the pinned ones. A regular-expression alternative that is French, names a
third-party platform or a private path is replaced by `(?!x)x`, a pattern that never matches,
with a marker on the line or in the comment just above it. Docstrings, comments, refusal texts
and self-tests that quote the operator, are French, tell the incident history or name private
paths are replaced by a marker; a refusal text keeps its gist.

| Id | File | What was cut or changed |
|---|---|---|
| H11 | stop_ask_gate.py | the module docstring |
| H12 | stop_ask_gate.py | `CONTRACT_TEXT`, a verbatim copy of the C1 paragraph (published, redacted, in `treatment/C1-K039.md`); no function reads it |
| H13 | stop_ask_gate.py | the calibration incident in a comment |
| H14 | stop_ask_gate.py | three French alternatives of the ask pattern |
| H15 | stop_ask_gate.py | the private file that shares the class words, in a comment |
| H16 | stop_ask_gate.py | the refusal text (the instruction file's path, a private replay case); gist kept |
| H17 | stop_ask_gate.py | the self-test samples |
| H18 | stop_ask_gate.py | a trailing comment block |
| H21 | stop_promise_gate.py | the module docstring |
| H22 | stop_promise_gate.py | the history of the shared module, in a comment |
| H23 | stop_promise_gate.py | the calibration incident in a comment |
| H24 | stop_promise_gate.py | seven French alternatives of the target pattern |
| H25 | stop_promise_gate.py | the private replay case the promise pattern came from |
| H26 | stop_promise_gate.py | four French alternatives of the promise pattern |
| H27 | stop_promise_gate.py | the refusal text (a private rule id and replay case); gist kept |
| H28 | stop_promise_gate.py | the self-test samples |
| H29 | stop_promise_gate.py | a trailing comment block |
| H31 | stop_rule_gate.py | the module docstring |
| H32 | stop_rule_gate.py | the calibration incident in a comment |
| H33 | stop_rule_gate.py | four French alternatives of the announcement pattern |
| H34 | stop_rule_gate.py | the French noun and adverb in three patterns |
| H35 | stop_rule_gate.py | the list of 28 vendor and platform names (now empty) |
| H36 | stop_rule_gate.py | three private path prefixes of seven |
| H37 | stop_rule_gate.py | the refusal text (private paths, a private replay case); gist kept |
| H38 | stop_rule_gate.py | the self-test samples |
| H39 | stop_rule_gate.py | a trailing comment block |
| H41 | hook_bounds.py | the history of the module |
| H42 | hook_bounds.py | the repository's name in a docstring |
| H43 | hook_bounds.py | the repository's name in four string literals and a docstring line (escape variable, budget directory, two marker files). In E1 the variable was unset and no replay directory held the marker files, so the renamed literals behave as the pinned ones did |
| H44 | no-em-dash.py | two words of the docstring |
| H45 | the three Stop gates | layout only: one blank line in the transcript reader, behaviour unchanged |
| H51 | ask_question_gate.py | everything but its detector (docstring, refusal text, main function, self-test) |

`no-em-dash.py` and `no-em-dash-write.py` are otherwise unredacted. Not published at all: the
module `rc_activity.py` that the question-tool hook imports (`prereg/DEVIATIONS.md`, deviation 2),
inert outside remote-control sessions; the question-tool hook never ran in E1
(`e1.C1.question_hook_ran`, 0 of 20).

Effect of the cuts on E1: none on the runs. The replay prompts and the run texts are English, so a
French alternative could not match them. On 2026-10-13 every detector of the public copies was run
against the pinned one on all 372 run texts of `runs.jsonl` and the five prompts: 0 differences
for each of the five detectors (ask, promise and target, rule announcement, long dash at Stop,
long dash at write). That check needs the private pinned files; the public one is
`python3 e1/regrade.py`, which recomputes V_door from these copies with 0 disagreements, and
`e1/tests/test_public_hooks.py`.

## The run records (`runs.jsonl`, R60)

One word of one run text (order 60, its first text) matched the private list of third-party
names and is replaced by `[REDACTED R60]`; it is in no closing text, and the regrade is unchanged.
Absolute paths of the scratch directories are stripped from tool call targets.
