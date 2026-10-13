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
python3 -m pytest -q                                   # 115 tests, all green
python3 analysis/numbers.py                            # rebuilds every table, figure and results/numbers.json
git diff --exit-code results/numbers.json              # exit 0: the committed numbers are what the code produces
python3 e1/run_e1.py status                            # the E1 replay: runs present per case and arm (10 of 10 each)
```

`analysis/numbers.py` is byte-deterministic and reads only `data/` and `e1/results.jsonl`. Re-running
the replay itself needs a Claude Code installation and model access (`e1/PILOT.md`, `prereg/`) and
is not needed to reproduce the numbers: the per-run results are in `e1/results.jsonl`.

## Folders

- `prereg/`: the preregistration of experiment E1.
- `data/`: derived tables only (one row per in-scope rule, weekly counts).
- `e1/`: the E1 cases, hooks and runner configuration.
- `analysis/`: analysis code that produces the numbers.
- `results/`: E1 replay results per run and `numbers.json`.
- `tools/`: manuscript checks (render, check_numbers, wordcount, check_refs) and their tests.
- `env/`: the environment needed to rerun.

Raw logs cannot be shared because they contain third-party personal data. The derived tables and
the replay experiment are public.

## Licences

Code: MIT (`LICENSE`). Data: CC BY 4.0 (`LICENSE-DATA.md`).
