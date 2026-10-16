# Experiment E1: the replay

The design is `prereg/PREREG.md` (sections 4 to 8); deviations are in `prereg/DEVIATIONS.md`, the
pilot in `PILOT.md`. This page lists what the folder holds and what a reader can check with it.

## What is here

- `cases/C1` to `cases/C5`: each case's prompt, its scratch repository (`template/`) and, where
  there is one, the setup script that gives the repository its history.
- `design.json`: models, arms, the pinned line range each arm removes, hook registration per arm.
- `treatment/`: the five ablated paragraphs of the pinned instruction file, one per case, redacted
  with visible markers (`REDACTIONS.md`), with their line range, arms, sha256 and word count.
- `hooks/`: public copies of the hooks pinned for E1 (the ask, promise and rule-announcement Stop
  gates, their shared `hook_bounds.py`, the two long-dash hooks, and the detector of the
  question-tool hook), redacted with visible markers (`REDACTIONS.md`).
- `graders.py`, `proof.json`, `tests/`: the graders of `PREREG.md` section 7 and their proofs.
  `tests/test_completion_can_fail.py` shows that each completion grader can fail.
- `run_order.csv`, `run_e1.py`: the drawn run order and the driver.
- `results.jsonl`: one row per run with the measures of `PREREG.md` section 7, no text.
- `runs.jsonl`: per counted run, what the run left (review round 1): every closing text the run
  produced (`texts`, with `closing_text` and its index), each stop attempt with the Stop hooks'
  decisions (`stops`), the PreToolUse denials (`n_denials`), the files it wrote (`output_files`,
  full content), the paths it created and deleted, its commits (text, paths, whether it touched
  the situation files), its branches, and for C4 every write call (tool, target, the text the
  write hook inspects, denied or not).
- `run_facts.csv`: per run, the hook events of its raw stream: hooks registered, Stop and
  PreToolUse hook runs, empty Stop outputs, blocks and denials, prompt hook runs, operator skills
  listed (0 everywhere: isolation held), the model reported, and since review round 3 whether
  the run had its own empty configuration directory (`own_config_dir`, 200 of 200), the context
  size of its first model call (`first_call_context_tokens`), its turn results (`turn_results`, 1
  in every run, so each run's closing text is its one turn end) and how many turns a background
  job's notification resumed (`turns_resumed_by_task_notification`, 0 in every run).
- `graders_first_committed.py`: the graders as first committed (3bd3559, 2026-09-30 18:24 +0200),
  byte for byte, before the refinements of deviation 6 (`prereg/DEVIATIONS.md`).
  `analysis/round2_supplement.py` grades the 200 counted runs with it (`e1.first_graders.*`) and
  `analysis/tests/test_round2.py` checks it against the commit.
- `pilot_runs.csv`: the 30 pilot runs, one row each: case, situation, run index, batch start
  (UTC), trimwrit commit, and V as recorded at the end of the run, under the first committed
  graders, under the counted graders and (review round 3) under E2's graders, which differ only
  in C1 (`V_e2_graders`). No text (`PILOT.md`, keys `e1.pilot.*`).
- `regrade.py`: rebuilds each run's final state from `runs.jsonl` and the case's setup, grades it
  with `graders.py` and the public hooks, and compares V, V_door, C, B, K_stop and K_deny with
  `results.jsonl`. `python3 e1/regrade.py` prints `200 runs regraded, 0 field disagreements`.
  `stop_blocks_took_effect` and `denials_took_effect` are copied from trimwrit (MIT) at the commit
  the runs used (a098f95).
- `run_identity.csv` (review round 4): per counted run, what the records hold about the model and
  the first request. Columns: case, arm, run index; the tool version; the model the session start
  reports; the run's responses and how many of them report the alias `claude-opus-5-5`, carry a
  response id, carry a request id and ran on the standard service tier; the model, the
  canonical model and the provider and cost basis the run's result lists; the model and knowledge
  cutoff the tool's model attachment names; the instruction files the tool reported loading; the
  first 16 hex digits of a sha256 of the first request as the transcript reports it (the user's
  first input and the sandbox, environment, instruction-file, session, prompt snapshot and date
  attachments before the first answer: this tool version recorded no request), once the scratch
  path (and its dashed form), uuids, timestamps and commit hashes are replaced by fixed markers,
  and its length in characters; whether the run had its own scratch directory. No text.

## What the run records show (keys in `results/numbers.json`, from `analysis/e1_supplement.py`)

- **The pinned Stop gates of C1 to C3 judged the text before the closing one.** They read the
  session transcript, which at Stop time does not yet hold the closing text. In C2's door arms the
  gate's decision equals its detector on the previous text at 22 of 22 stop attempts, and on the
  closing text at 18 of 22 (`e1.C2.door_arms.stop_decisions_match_detector_on_*`). So C2 AD's
  blocked runs (0 and 7, blocked because the text before held a promise by the gate's detector) are not the runs
  whose closing text the detector flags (6 and 8). The harness's live gates read the closing text
  from the Stop payload since 2026-09-30 17:27 +0200 (`prereg/ANALYSIS.md` section 9;
  `DEVIATIONS.md`, deviation 18). The long-dash Stop hook always read the payload.
- **C4's Stop door had nothing to refuse.** No closing text of the two Stop arms held a long dash
  (`e1.C4.stop_arms.closing_text_flagged_by_stop_hook`, 0 of 20), and every Stop hook run printed
  nothing (20 of 20). The runner reads a block in both of its forms, so these zeros are not a
  reading failure. AD-stop's 10 violations are all in files the run wrote, which a Stop hook does
  not read (`e1.C4.AD-stop.violations.in_files`, 10 of 10).
- **C4's write door: escapes in closing texts.** 6 of the 20 write-arm runs violate
  (`e1.C4.write_arms.E`); all 6 hold the dash in their closing text, which the write hook does not
  see, and the one that also reached a file did so through write calls whose inspected text was
  clean (`e1.C4.write_arms.file_escapes_through_calls_the_hook_saw_clean`, 1 of 1).
- **C3 depends on the refined grader.** The C3 grader as first committed (3bd3559, committed
  at 18:24 +0200, after the first pilot batches started at 18:19 and before the redesigned
  situations ran from 18:26; the V the driver recorded equals it in 30 of 30 pilot runs) flags
  0 of 10 runs in every arm (`e1.C3.<arm>.V_first_committed_grader`); the counted grader,
  refined after the pilot (`DEVIATIONS.md`, deviation 6), flags 10 of 10 in A0 and AD.
- Every door arm registered and ran its hooks (100 of 100), no arm without a door had a hook event
  (0 of 100), and the question-tool hook never ran (0 of 20, deviation 1).
- Doors refused in 12 of the 100 door-arm runs, all in C2 AD (2) and C4 AD-write (10); each such
  run, with its turns and output tokens, is listed under `e1.refused_runs`.
- For each case, one counted run the grader flags and one it passes, to read in `runs.jsonl`:
  `e1.<case>.example_flagged` and `e1.<case>.example_passed` (run orders). C1's flagged example is
  not a real violation: no counted C1 run holds one (`e1.C1.reading`, review round 4).

## The model behind the alias (review round 4)

Every run requested `claude-opus-5-5`, an alias. The records hold the alias and nothing more
specific: every response of every counted run reports `claude-opus-5-5` with a response id and a
request id, on the standard service tier; each run's result lists one model, canonical model
`claude-opus-5-5`, provider and cost basis `firstParty/list`; the tool's model attachment names
`claude-opus-5-5` with a knowledge cutoff of June 2026 (`e1.identity.model`). No record names a
dated snapshot and none carries a response header, so the model behind the alias is not verified
within this replay or across E1 and E2; a difference between the replays can come from the tool
version (2.1.285 here, 2.1.300 in E2) or from the model.

## What each run was given (review round 4)

Each run had its own scratch directory and loaded one instruction file, the scratch repository's
`CLAUDE.md` that its arm built (`e1.identity.instruction_files_and_scratch`). Once the scratch
path, ids, timestamps and commit hashes are replaced, the first request as the transcript reports
it is the same for every run of a cell in 15 of the 20 cells; in each of the other five, one run
got a shorter variant of the tool's own instructions (680 characters less, 629 in C2 AD). Each
door arm's request equals its twin's without the door, and AP's is A0's with the case's paragraph
inserted (`e1.first_request.within_cell`). This tool version did not record the system prompt, so
what varies in `first_call_context_tokens` (`run_facts.csv`) within a cell beyond the replaced
parts cannot be read from the records.

## What is not published

The raw run streams (`E1_RAW`, never published by design; `runs.jsonl` and `run_facts.csv` are
what is derived from them), the pinned
instruction file beyond the five paragraphs, the module `rc_activity.py`, and the pilot runs'
texts and outputs. The pilot runs were made on situations later redesigned, before the counted
runs; their texts would need the same redaction. `pilot_runs.csv` gives each pilot run's flags
and times, and `PILOT.md` each pilot's outcome.

## The rest of the instruction file

The arms remove only the paragraph of their case; the rest of the pinned file (219 lines) stays
in every arm and is not published. What it still says near each case's rule, in that case's A0:

- C1 (lines 207 to 219 removed): lines 48 to 58 (the shape of an answer, ask with context), 99 to
  100 (ask only when unsure whether a step is mechanical), 175 to 179 (a decision already taken is
  not proposed again) and 181 to 185 (never ask for an input the machine can produce).
- C2 (lines 166 to 173 removed): lines 160 to 164, the heading and introduction of the section the
  paragraph belongs to (rules promoted from the correction ledger, each with a replay case). No
  other line is about ending a turn on a promise.
- C3 (lines 146 to 159 removed): no other line states the rule, but three passages show it by
  example: lines 140 to 143 (a hook named as the mechanism of a terminal rule), 171 to 172 (C2's
  paragraph names its Stop hook as its mechanism) and 218 to 219 (C1's paragraph says its rule is
  checked by a gate and a door rather than read).
- C4 (lines 9 to 16 removed): lines 17 to 31, the rest of the writing-style section (other style
  rules and the kinds of text they cover).
- C5 (lines 40 to 47 removed): no other line is about internal identifiers.

Each case's own door is mentioned only inside that case's removed paragraph (C5 has no door).

## Running it again

The numbers need none of this: `python3 analysis/numbers.py` reads the published files, and
`python3 e1/regrade.py` regrades the 200 counted runs from `runs.jsonl`.

A new run of the replay needs, besides this folder: Claude Code 2.1.285, access to
`claude-opus-5-5`, trimwrit at a098f95 (`TRIMWRIT`, public, MIT), a subscription credential
(`E1_TOKEN_FILE`), a directory for raw runs (`E1_RAW`) and a context directory (`E1_CONTEXT`) that
holds the instruction file and the hooks, with their sha256 in `SHA256SUMS`. The driver refuses
any instruction file or hook whose sha256 differs from the pins (`design.json`, `SHA256SUMS`).

What is public and what is not, exactly:

- Public: the five ablated paragraphs (`treatment/`, redacted with visible markers), the hooks
  (`hooks/`, redacted with visible markers), the cases, the graders, the driver and the drawn run
  order.
- Not public: the pinned instruction file beyond the five paragraphs (219 lines, summarised in
  "The rest of the instruction file" above), the hooks' unredacted bytes, the module
  `rc_activity.py` that one hook imports (deviation 2), the raw run streams and the credential.

So the pins cannot be met from the public files, and the published runs cannot be repeated byte
for byte. An outside replication builds its own context (an instruction file holding the five
published paragraphs at their line ranges, with or without text of its own around them, and the
public hooks with the redacted parts filled), records its sha256 in `design.json` and
`SHA256SUMS`, and is a new experiment on the same design rather than a re-run. `E1_HUB` is
optional: it pointed at the harness whose model-quota check gated each batch; unset, the check is
skipped with a note.
