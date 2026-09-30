# analysis/

Every number the paper prints comes from these scripts, through `results/numbers.json`.

```
python3 analysis/numbers.py            # all tables, figures, results/numbers.json, results/hypotheses.json
python3 -m pytest analysis/tests -q    # tests on synthetic inputs only
```

`numbers.py` is byte-deterministic (two runs give identical files). A script whose input file is
absent is skipped with a message and its keys are not written; `results/manifest.json` lists what
ran and what was skipped. `--data`, `--e1` and `--out` point it at other folders.

Each entry of `results/numbers.json` carries `value`, `text` (the exact string the manuscript
prints through `tools/render.py`), `source`, and where they apply `k`, `n`, `interval`,
`ci_method` and `text_short` (the point value alone). Statistics follow `prereg/PREREG.md`
section 10 (`stats.py`).

| Script | ANALYSIS.md item | Input |
|---|---|---|
| `table01_rules.py` | Table 1 | `data/rules.csv` |
| `table02_enforceability.py` | Table 2 | `data/rules.csv` |
| `table03_per_rule.py`, `figure1_timelines.py` | Table 3, Figure 1 | `data/corrections_weekly.csv`, `data/rules.csv` |
| `table04_weekly.py` | Table 4, Figure 2 | `data/transcripts_weekly.csv` |
| `table05_ask_door.py` | Table 5 | `data/transcripts_weekly.csv` |
| `table06_prospective.py` | Table 6 | `data/transcripts_prospective.csv` |
| `table07_ask_audit.py` | Table 7 | `data/ask_audit.csv` |
| `table08_scheduler.py` | Table 8, Figure 3 | `data/scheduler_weekly.csv`, `data/scheduler_ontime.csv` |
| `table09_door_cost.py` | Table 9 | `data/door_refusals_weekly.csv`, `data/door_review.csv`, `data/door_size.csv` |
| `table10_doors_failed.py` | Table 10 | `data/transcripts_weekly.csv`, `data/door_size.csv` |
| `table11_replays.py` | Table 11 | `data/replays_past.csv` |
| `table12_e1.py` | Table 12, Figure 4, H1 to H5 | `e1/results.jsonl`, `e1/design.json`, `e1/run_order.csv` |
| `table13_cost.py` | Table 13 | `data/cost_weekly.csv` |
| `case_facts.py` | facts of the case measured elsewhere | `data/case_facts.csv` |

## Input schemas the scripts read

Columns beyond these are ignored. Weeks are the Monday of the week (`YYYY-MM-DD`, Europe/Paris);
weeks after the after window (2026-10-05) are left out of every table.

- `transcripts_weekly.csv`: week, session_kind, repo_group, model, cli_version, sessions,
  asst_msgs, human_msgs, human_msgs_operator_likely, corr_hits_operator_likely, turn_ends,
  ends_q_trailing, ends_q_last400, ends_q_trailing_replied, ref_stop_promise, ref_stop_ask,
  ref_stop_rule, dash_stop_detected, dash_stop_continued, ref_ptu_askuserquestion,
  ref_ptu_dash_write; optional dash_stop_still_violating, write_calls.
- `transcripts_prospective.csv`: part (retrospective, prospective), session_kind, repo_group,
  turn_ends, ends_q_trailing_replied, ref_stop_promise, ref_stop_promise_continued.
- `corrections_weekly.csv`: week (or a non-date label for undated corrections), rule_id, state
  (none, prose, door, unknown), count, exposure.
- `scheduler_weekly.csv`: week_start, door_class (`all` for launches and outcomes), jobs_created,
  launches, outcome_done, outcome_closed_by_ledger, outcome_error, outcome_blocked,
  outcome_to_operator, outcome_retry, outcome_superseded, door_rows, door_episodes, jobs_held,
  jobs_held_done_in_period, jobs_held_no_period.
- `scheduler_ontime.csv`: row_set, era, first_day, last_day, days, rows, due_row_days,
  logged_same_day, days_with_no_log_in_set.
- `cost_weekly.csv`: week_start, session_kind, sessions, turns, output_tokens,
  load_units_with_imputed_tier, share_of_week_load, envelope_attempts, envelope_usd,
  envelope_no_estimate.
- `ask_audit.csv`: window (before, after), week, coder1, coder2, final; codes only-him,
  avoidable, not-an-ask.
- `door_refusals_weekly.csv`: week, rule_id, door_type, refusals, took_effect, did_not,
  cannot_judge; optional recovery_n, recovery_turns, recovery_output_tokens (sums).
- `door_review.csv`: rule_id, stratum, coder1, coder2, final; codes right, wrong, unclear.
- `door_size.csv`: rule_id, door_type, code_lines, test_lines, n_tests; optional has_bypass,
  writes_ledger (0 or 1).
- `replays_past.csv`: case_id, runs_without, violations_without, runs_with, violations_with.
- `case_facts.csv`: key, value, text, source, k, n, ci_low, ci_high.
