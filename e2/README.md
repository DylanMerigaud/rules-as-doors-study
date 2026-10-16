# Experiment E2: the replay with the doors as repaired

The design is `prereg/PREREG-E2.md` (tag `prereg-e2`); deviations go in `prereg/DEVIATIONS.md`
under their E2 heading; the pilot and the planted runs are in `PILOT.md`. E1 (`e1/`) is unchanged:
E2 reuses its case files, its graders and its driver by import, and copies nothing it does not
change.

## What is here

- `design.json`: the model, the arms, the pinned line range each prose-less arm removes (E1's),
  the hook registration of each door arm, and the sha256 of each pinned hook (commit `7af9779e` of
  the harness repository, live from 2026-09-30 17:32 +0200).
- `cases/C4S/prompt.md`: the one new situation, which uses C4's repository and setup
  (`e1/cases/C4/`). C1 to C5 are E1's case files.
- `hooks/`: public copies of the pinned hooks (the ask, promise and rule-announcement Stop gates,
  their shared `hook_bounds.py` and `hook_trace.py`, the two long-dash hooks), redacted with
  visible markers (`REDACTIONS.md`). Their detectors are E1's; their delivery is the repaired one.
- `graders.py`, `proof.json`, `tests/`: E2's graders (E1's, imported, except the corrected C1
  grader, C4S's completion and the strict K), committed before any E2 pilot or planted run, and
  their tests: the proofs, the corrected C1 grader on the nine E1 runs the old one misread, the
  strict K, the public hooks against E1's detectors and the repaired delivery.
- `planted.json`: one planted situation per door.
- `run_order.csv`, `run_e2.py`: the drawn run order (numpy `default_rng(20261015)`) and the driver
  (`order`, `prove`, `planted`, `planted-report`, `pilot`, `run`, `status`).
- `results.jsonl`: one row per run attempt with the measures of `PREREG-E2.md` section 7, no
  text. A voided attempt keeps its reason and its order row is run again.
- `runs.jsonl` (review round 3): per counted run, what the run left, built from the raw runs the
  way `e1/runs.jsonl` was: every assistant text in order (`texts`, with `closing_text` and its
  index), each stop attempt with the index of the text the Stop hooks judged and their decisions
  (`stops`), the index in `texts` of the text that ended each turn (`turn_end_text_indexes`: a run
  whose session resumed when a background job reported back has more than one turn), the
  PreToolUse denials (`n_denials`) and tool calls (`n_tool_calls`), the files it wrote
  (`output_files`, full content), the paths it created and deleted, its commits (text, paths,
  whether they touched the situation files), its branches, in a door arm the counts of the
  hooks' own health rows (`hook_health`: caps, crashes, timeouts), and for C4 every write call
  (tool, target, the text the write hook inspects, denied or not, error or not). A closing text
  a Stop door refused is in `texts`: the stream records it before the hook answers, so the texts
  before each refusal and the re-answers after it can be read. Redactions: `REDACTIONS.md`, R60.
- `regrade.py`, `tests/test_regrade_e2.py`: rebuilds each run's final state from `runs.jsonl` and
  the case's setup (E1's case files, C4S's prompt), grades it with `graders.py` and the public
  hook copies, and compares 23 fields with `results.jsonl` (V, V_door, V_text, V_files,
  V_commits, C, B, B_stop, B_deny, K_stop, K_deny, K_deny_strict, K_stop_door, E, the delivery
  check, the hooks' health rows, stop attempts and tool calls). `python3 e2/regrade.py` prints
  `220 runs regraded, 0 field disagreements`; the test pins it and shows that a changed record
  makes it disagree.
- `run_facts.csv`: per run, from its raw stream: hooks registered, Stop and PreToolUse hook runs,
  empty Stop outputs, blocks and denials, prompt hook runs, operator skills listed (0
  everywhere), the model reported, whether the run had its own empty configuration directory
  (`own_config_dir`), the context size of its first model call (`first_call_context_tokens`), its
  turn results (`turn_results`) and how many of its turns a background job's notification
  resumed (`turns_resumed_by_task_notification`). No text.

## How the analysis reads it

`analysis/table14_e2.py` (run by `analysis/numbers.py`) writes `results/tables/table14_e2_cells.csv`,
the `e2.*` keys of `results/numbers.json`, and the `e2` entry of `results/hypotheses.json`. H1 to H5
are judged by E1's own code with E1's criteria; H5's Stop half reads C4S's Stop arms.

## What needs the private files

The raw runs (streams, session records, the scratch repository after each run, each run's hook
health ledger) and the unredacted pinned hooks stay private, as E1's did; `runs.jsonl` and
`run_facts.csv` are what is derived from them, and they are enough to regrade every counted run.
Not published: the pilot and planted runs' texts (`PILOT.md` gives their outcomes), the
instruction file beyond the five paragraphs, the hooks' unredacted bytes (`REDACTIONS.md`), and
the hook trace each run wrote (its decisions are in `stops`, its health counts in
`hook_health`). With the raw files, `run_e2.py planted-report` regrades every planted run.

## Running it again

The numbers need none of this: `python3 analysis/numbers.py` reads the published files.

A new run needs, besides this folder and `e1/` (whose case files, graders and driver E2 imports):
Claude Code 2.1.300 (recorded on every run; E1 ran on 2.1.285), access to `claude-opus-5-5`,
trimwrit at 0ab0b33 (`TRIMWRIT`, public, MIT), a directory for raw runs (`E2_RAW`), a context
directory (`E2_CONTEXT`) that holds the instruction file and the pinned E2 hook copies with their
`SHA256SUMS`, and `E2_HUB`, the harness whose model-quota check gates every batch and whose
credential resolver gives each run a subscription login. The driver refuses an instruction file
or a hook whose sha256 differs from `design.json`.

What is public and what is not, exactly:

- Public: the treatment, which is E1's: the five ablated paragraphs in `e1/treatment/` (the same
  pinned instruction file, sha256 `a71019d6...`, and the same line ranges), redacted with visible
  markers; the hooks as repaired (`hooks/`, redacted with visible markers, `REDACTIONS.md`); C4S;
  the graders, the planted situations, the driver and the drawn run order.
- Not public: the pinned instruction file beyond the five paragraphs (the same 219 lines as E1's,
  summarised in `e1/README.md`), the hooks' unredacted bytes, the raw runs and the harness that
  `E2_HUB` points to (its quota check and its credential resolver).

So, as for E1, the pins cannot be met from the public files: an outside replication builds its
own context from the published paragraphs and hooks, records its sha256, supplies its own
credential in place of `E2_HUB`'s resolver, and is a new experiment on the same design rather
than a re-run.
