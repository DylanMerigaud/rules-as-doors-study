# rules-as-doors-study

Replication package: prose rules versus enforced rules in a long-running coding agent harness.

The harness runs recurring operations of the author's one-person software business, such as job
scheduling, data pipelines, monitoring and alerting, cost and quota control, and the maintenance
of the author's code repositories and documentation, on one laptop under the author's
supervision. The study counts events (instructions, refusals, corrections, scheduled runs) and
never reports their content; rules and jobs that concern other people or their data are left
out, because they cannot be published.

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
