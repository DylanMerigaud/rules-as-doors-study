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

## How the analysis reads it

`analysis/table14_e2.py` (run by `analysis/numbers.py`) writes `results/tables/table14_e2_cells.csv`,
the `e2.*` keys of `results/numbers.json`, and the `e2` entry of `results/hypotheses.json`. H1 to H5
are judged by E1's own code with E1's criteria; H5's Stop half reads C4S's Stop arms.

## What needs the private files

The raw runs (streams, transcripts, the scratch repository after each run, each run's hook health
ledger) and the unredacted pinned hooks stay private, as E1's did. With them, `run_e2.py
planted-report` regrades every planted run from its raw files.

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
