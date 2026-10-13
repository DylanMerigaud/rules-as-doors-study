# rules-as-doors-study

The harness runs recurring operations of the author's one-person software business, such as job
scheduling, data pipelines, monitoring and alerting, cost and quota control, and the maintenance
of the author's code repositories and documentation, on one laptop under the author's
supervision. The study counts events (instructions, refusals, corrections, scheduled runs) and
never reports their content; rules and jobs that concern other people or their data are left
out, because they cannot be published.

Replication package: prose rules versus enforced rules in a long-running coding agent harness. The package accompanies a manuscript under submission; this page will cite it once it is public.

Archive: DOI 10.5281/zenodo.23347509 (Zenodo, reserved; the record becomes public with the paper). See `CITATION.cff`.

## Reproduce

Python 3.12; `pip install -r env/requirements.txt`. From the repository root:

```
python3 -m pytest -q                                   # 165 tests, all green
python3 analysis/numbers.py                            # rebuilds every table, figure and results/numbers.json
git diff --exit-code results/numbers.json              # exit 0: the committed numbers are what the code produces
python3 e1/run_e1.py status                            # the E1 replay: runs present per case and arm (10 of 10 each)
python3 e1/regrade.py                                  # regrades the 200 runs from e1/runs.jsonl: 0 disagreements
```

`analysis/numbers.py` is byte-deterministic and reads only `data/` and `e1/` (the results, the
run records, the graders and the public hook copies). Re-running the replay itself needs a
Claude Code installation, model access and a context built from the published paragraphs and hooks
(`e1/README.md`, "Running it again"); it is not needed to reproduce the numbers.

## Folders

- `prereg/`: the preregistration of experiment E1.
- `data/`: derived tables only (one row per in-scope rule, weekly counts); `data/README.md` is the
  data dictionary.
- `e1/`: the E1 cases, the five ablated paragraphs (`e1/treatment/`), the pinned hooks
  (`e1/hooks/`, redacted with visible markers, `e1/REDACTIONS.md`), the graders, the runner, the
  per-run results (`e1/results.jsonl`) and run records (`e1/runs.jsonl`); see `e1/README.md`.
- `analysis/`: analysis code that produces the numbers.
- `results/`: `numbers.json`, `hypotheses.json`, `manifest.json` (what ran), the tables and figures.
- `tools/`: manuscript checks (render, check_numbers, wordcount, check_refs) and their tests.
- `env/`: the environment needed to rerun.

Raw logs cannot be shared because they contain third-party personal data. The derived tables and
the replay experiment are public.

## Licences

Code: MIT (`LICENSE`). Data: CC BY 4.0 (`LICENSE-DATA.md`).
