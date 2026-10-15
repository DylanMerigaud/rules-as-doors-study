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
