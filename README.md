# rules-as-doors-study

The harness runs recurring operations of the author's one-person software business, such as job
scheduling, data pipelines, monitoring and alerting, cost and quota control, and the maintenance
of the author's code repositories and documentation, on one laptop under the author's
supervision. The study counts events (instructions, refusals, corrections, scheduled runs) and
never reports their content; rules and jobs that concern other people or their data are left
out, because they cannot be published.

`prereg/PREREG.md` (frozen at its tag, 2026-09-30) opens with "runs a coding agent unattended, for
months". That wording predates the paragraph above, which supersedes it: the harness runs under
the author's supervision, and the two field windows cover 2026-08-31 to 2026-10-11
(`prereg/ANALYSIS.md` section 2).

Replication package: prose rules versus enforced rules in a long-running coding agent harness. The package accompanies a manuscript under submission; this page will cite it once it is public.

Archive: DOI 10.5281/zenodo.23347509 (Zenodo, reserved; the record becomes public with the paper). See `CITATION.cff`.

## Reproduce

Python 3.12; `pip install -r env/requirements.txt`. From the repository root:

```
python3 -m pytest -q                                   # 243 tests, all green
python3 analysis/numbers.py                            # rebuilds every table, figure and results/numbers.json
git diff --exit-code results/numbers.json              # exit 0: the committed numbers are what the code produces
python3 e1/run_e1.py status                            # the E1 replay: runs present per case and arm (10 of 10 each)
python3 e1/regrade.py                                  # regrades the 200 runs from e1/runs.jsonl: 0 disagreements
python3 e2/run_e2.py status                            # the E2 replay: runs present per case and arm
```

`analysis/numbers.py` is byte-deterministic: two runs give identical `results/numbers.json`,
tables and SVG figures (the figures' clip-path ids, which matplotlib draws from object addresses,
are renamed in order of appearance). It reads only `data/`, `e1/` and `e2/` (the results, the run
records, the graders and the public hook copies). Re-running the replay itself needs a
Claude Code installation, model access and a context built from the published paragraphs and hooks
(`e1/README.md` and `e2/README.md`, "Running it again", say exactly which parts are private); it
is not needed to reproduce the numbers.

## Folders

- `prereg/`: the preregistrations of experiments E1 (`PREREG.md`, tag `prereg-v1`) and E2
  (`PREREG-E2.md`, tag `prereg-e2`), the field analysis plan and the deviations.
- `data/`: derived tables only (one row per in-scope rule, weekly counts); `data/README.md` is the
  data dictionary.
- `e1/`: the E1 cases, the five ablated paragraphs (`e1/treatment/`), the pinned hooks
  (`e1/hooks/`, redacted with visible markers, `e1/REDACTIONS.md`), the graders, the runner, the
  per-run results (`e1/results.jsonl`) and run records (`e1/runs.jsonl`); see `e1/README.md`.
- `e2/`: the second replay, with the doors as repaired: its one new situation, the public copies
  of the repaired hooks (`e2/REDACTIONS.md`), the graders it changes, the planted runs, the
  driver and the per-run results (`e2/results.jsonl`); see `e2/README.md`.
- `analysis/`: analysis code that produces the numbers.
- `results/`: `numbers.json`, `hypotheses.json`, `manifest.json` (what ran), the tables and figures.
- `tools/`: manuscript checks (render, check_numbers, wordcount, check_refs) and their tests.
- `env/`: the environment needed to rerun.

Raw logs cannot be shared because they contain third-party personal data. The derived tables and
the replay experiment are public.

## Licences

Code: MIT (`LICENSE`). Data: CC BY 4.0 (`LICENSE-DATA.md`).
