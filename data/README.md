# Data dictionary

Every file here is derived; the raw logs are not public. Counts from transcripts are keyed only
by week, session kind, repository group, hook, rule id, model id and tool version, never by topic,
channel, person or platform. The sources of each file are in `prereg/ANALYSIS.md` section 3; this
page adds what a reader needs to read the numbers right. Weeks start on Monday, in the operator's
time zone (Europe/Paris).

## Windows

- Before window: 2026-08-31 to 2026-09-20 (weeks of 08-31, 09-07, 09-14). After window: 2026-09-21
  to 2026-10-11 (weeks of 09-21, 09-28, 10-05). The week of 2026-08-24 is partial and appears in
  the weekly series only.
- Door refusal ledger window: 2026-09-30 to 2026-10-11 (12 days). Every count in
  `door_refusals_weekly.csv`, `door_review.csv` and `door_review_frame.csv` comes from that
  window only (key `door.ledger_window`).
- Correction probe windows (`case_facts.csv`, keys `dig.corr_before` and `dig.corr_after`): the
  after figure covers 2026-09-04 21:56 to 2026-09-18 21:56 +02:00 (14 days, 490 operator turns
  scanned); the before figure is the same scanner replayed at 2026-09-01 over the 14 days before
  it (93 of 2,011). The probe and its expected value were declared on 2026-09-01 in the harness's
  own probe ledger, not in the preregistration; the before figure cannot be recomputed because
  the transcripts before 2026-08-30 were deleted by the tool's 30-day retention.

## Session kinds

`transcripts_weekly.csv`, `transcripts_prospective.csv` and `cost_weekly.csv` use four kinds,
read from each transcript's own fields:

- `subagent`: a sub-session another session started for a delegated task (its transcript sits
  under the parent's).
- `popped terminal`: an interactive session whose first prompt is one of the harness's prepared
  task prompts (the harness opened it in a terminal for the operator).
- `operator session`: any other interactive session.
- `scheduler worker`: EVERY non-interactive (headless) session, whoever started it. The label is
  wider than its name: it holds the scheduler's own workers and every other headless call.
  `headless_split.csv` splits it.
  The scheduler's workers run in the tool's bare mode with no instruction file and no hook: in
  their rows every hook count is 0 (keys `headless.worker_prompt.*`). All the hook events counted
  under `scheduler worker` (1,073 Stop hook firings, keys `headless.other.*`) come from the other
  headless sessions, which load the hooks of the repository they run in.
- `subagent`: a sub-session a session starts for a delegated task.

Operator turns and answered questions (`transcripts_weekly.csv`, `transcripts_prospective.csv`):

- `turn_ends`: closing texts, that is main-thread assistant-role entries that carry text and no
  tool call.
- `human_msgs`: main-thread user-role messages that carry text (not empty, not starting with `<` or
  `[`, which is command output, a notification or an interruption notice, and not a
  context-continuation summary) and whose recorded prompt source is typed or queued input.
- `human_msgs_operator_likely`: those of them that are at most 1,500 characters, are not a
  keepalive ("continue", "go", "go on", 30 characters or fewer) and are not the first prompt of a
  popped terminal (a prepared prompt). It is the denominator of every correction rate; the
  corrections (`corr_hits_operator_likely`) are found by a fixed detector on the first 400
  characters of these messages only.
- `ends_q_trailing`: turn ends whose closing text ends on a question mark (trailing markup and
  quotes ignored). `ends_q_last400`: a question mark anywhere in the last 400 characters.
- `ends_q_trailing_replied` ("answered"): a turn end counted in `ends_q_trailing` whose next
  main-thread user-role message (tool results and system notes set aside) carries text under the
  same exclusions as `human_msgs`. Its prompt source is not checked: unlike `human_msgs`, it is
  not required to be typed or queued input, so an answer is not shown to be the operator's. A turn
  end followed by a Stop hook's feedback, or by the end of the transcript, is not answered. Read
  it as "answered by a user-role message".

An `operator session` is an interactive session that is not a popped terminal; its messages are
not all typed by the operator, which is why the correction rate uses the operator-likely filter
above.

`headless_split.csv` columns: `window` (before, after, or the partial week of 2026-08-24),
`headless_kind` (`scheduler worker prompt`: the session opens on the scheduler's worker prompt;
`other headless`), `repo_group`, then the hook columns and `write_calls` of
`transcripts_weekly.csv`, counted the same way. Rows are placed by the week a session started
(the weekly table places each event in its own week), so the two tables agree over all weeks
(22,874 write calls under `scheduler worker` in both) but not window by window. Session counts are
not given.

## Counts that come from different sources

- **Long-dash write refusals: 345 against 123.** `dashwrite.denials` (345) counts the PreToolUse
  long-dash refusals found in the transcripts (`ref_ptu_dash_write`), all session kinds, all
  repository groups, every week on disk from 2026-08-24 to 2026-10-11 (338 in the two windows,
  7 in the partial week). `door.K001.refusals` (123) is the door refusal ledger, which the live
  doors write themselves, over 2026-09-30 to 2026-10-11, all three of K001's door types: 113
  PreToolUse hook, 4 Stop hook and 6 write refusals (`door.K001.refusals.<type>`). The two
  differ in source, window and scope; in the two ledger weeks the transcripts count 126 PreToolUse
  refusals, two days of which precede the ledger. The rate `dashwrite.rate` (345 of 132,988 write
  calls) divides by the write calls of every session; `dashwrite.rate.hook_loaded` (345 of
  115,836) leaves out the 17,152 write calls of the scheduler's bare workers, which load no hook.
- **Field doors and E1 doors.** Every field count (transcripts, ledgers, `door_size.csv`) is the
  live code of the harness, which changed during the windows (dated in `ANALYSIS.md` section 9).
  The doors of experiment E1 are the copies pinned on 2026-09-30 at 16:27 +0200
  (`e1/hooks/`, redacted, and `e1/README.md`), before the repair of that day.
- **"Took effect"** is read per door type (`prereg/DEVIATIONS.md`, deviation 15). Keys
  `door.<rule>.refusals.<door type>.took_effect`.
  - Stop hook: the ledger's own daily pass takes the last assistant text of the main thread
    after the refusal and before the next new user turn (a main-thread user-role entry that is
    neither a tool result nor the hook's own feedback), and runs the door's own detector (its code
    on the day of the pass) on it: took effect when the detector no longer trips; did not when it
    still trips, or when no assistant text follows; cannot be judged when the transcript is not
    found. A detector that raises an error counts as took effect.
  - PreToolUse hook or write refusal: the refused call is found in the transcript; took effect
    when a later call of the same tool, in the same thread and before the next operator turn,
    ran without being refused (for a write door, a call that the write door let through).
  What the field measure cannot show: it reads no file. It does not check that the accepted
  call, or anything after it, is free of the violation (in E1 one door-alone run wrote the long
  dashes into the changelog through a shell command after its denial, and still counts under
  this definition: `e1.h5.write_strict.k`, 9 of 10, against `e1.h5.write.k`); it does not count
  violations the door never refused (no escape count, so no recall), and a Stop hook's "took
  effect" is judged by the same detector that refused. It cannot be made stricter from the
  derived tables, which hold no call content. A refusal that took effect may still have been
  wrong; `door_review.csv` codes that. The E1 and E2 measure K is stricter (`prereg/PREREG.md`
  section 7; `prereg/PREREG-E2.md` for the strict K that also reads the files).
- **The long-dash Stop hook: ledger 4 of 4, transcripts 3 of 4.** The two count different events.
  `door.K001.refusals.stop_hook.took_effect` is the ledger: rows the repaired hook wrote from
  2026-09-30 17:45 +0200 (`door.ledger.first_counted_refusal`) in every session kind, one of them
  a planted test session of the study (`door_refusals_test_rows.csv`; without it 3 of 3,
  `door.K001.refusals.stop_hook.took_effect.without_test_session`), judged by the rule above.
  `dashstop.repair_week_and_after.followed` is the transcripts: blocks in operator sessions and
  popped terminals from Monday 2026-09-28, so including the days before the repair of 2026-09-30
  17:27 +0200, when the hook's block did not stop the turn, judged as "followed by a new closing
  text before the next operator turn". No counted ledger refusal precedes the repair.
- **Test rows.** `door_refusals_test_rows.csv` lists the one counted ledger refusal that came
  from a planted test session (`DEVIATIONS.md`, deviation 20), with its recovery turns and
  output tokens. The published counts keep it. The K001 counts, took-effect shares, recovery
  means, review frame, review items, wrong shares (pooled and per coder), raw agreement and the
  pooled review kappa each have a `.without_test_session` twin. Kept with no twin: the total over
  every door in `door.refusals.not_located` (9 of 192), and `door.K001.review.kappa` and
  `.n_unclear`, whose values do not change without it (the item was coded right by both
  coders).

## Files

- `rules.csv`, `rules.md`: one row per in-scope rule; `rules.md` documents the columns, the
  coding and the descriptions rewritten on 2026-10-13.
- `rules_coding.csv`: both coders' labels for the 177 text units behind the public rules (unit,
  rule id, per coder: is a rule 1 or 0, class, enforceability). See `rules.md`.
- `corrections_weekly.csv`: week, rule id, delivery state (prose, door), corrections and
  exposure (operator-active days: days with at least one operator-likely input, sub-sessions
  left out). A rule whose text lives in the global instruction file counts the active days of
  every repository (the file loads everywhere); any other rule counts the active days of the
  harness's repository only. So two rules live all week can carry different exposures in the
  same week.
- `transcripts_weekly.csv`: week, session kind, repository group (`door`: the harness's own
  repository; `control`: the operator's other repositories), model id and tool version, then
  counts. The `ref_*` columns count hook refusals (`ref_stop_*` Stop hooks, `ref_ptu_*` PreToolUse hooks) and
  their `*_continued` twins count the refusals followed by a new closing text. `dash_stop_*` are
  the long-dash Stop hook's blocks, in both forms (`DEVIATIONS.md`, deviation 10).
  `ref_stop_retired` counts the blocks of the daily session's Stop gate, retired with the daily
  session at the 2026-09-20 cut-over.
- `transcripts_prospective.csv`: the same columns split into the retrospective and the
  prospective part of the after window. The retrospective part runs from 2026-09-21 to the tag
  (2026-09-30 18:05 +0200); in all of it but its last 38 minutes the field's ask, promise and
  rule-announcement Stop hooks judged the text before the closing one, not the closing text
  (`ANALYSIS.md` section 9, the change of 2026-09-30 17:27 +0200; `DEVIATIONS.md`, deviation 18).
  The prospective part runs the repaired hooks only. Keys `prosp.retrospective.<group>.answered_q`
  and `prosp.<group>.answered_q`.
- `scheduler_weekly.csv`: per week and door class (`all` is the total), jobs created, launches
  and outcomes. `sched.launches` (530) sums every week; 14 of them fall in the week of
  2026-09-14, before the after window, and 516 in it (`sched.launches.before_window`,
  `sched.launches.after_window`).
- `scheduler_ontime.csv`: per row set and era, the due row-days of the obligations of the
  engagement log and how many were logged the same day (`logged_same_day`): a due row-day counts
  as on time when the log holds an entry for that obligation dated that day. `rows_with_logs_in_both_eras`
  keeps the obligations logged at least once before and after the cut-over.
- `door_refusals_weekly.csv`: the door refusal ledger by week, rule id and door type: refusals,
  took effect, did not, cannot be judged, and the recovery measures.
- `door_review.csv`: the two codes (right, wrong, unclear) and the final code of each sampled
  refusal, by rule id and stratum (the door type).
- `door_review_frame.csv`: the sampling frame of the review. The draw took up to 20 refusals per
  (rule, door type), only among the refusals located in a transcript (`DEVIATIONS.md`, deviation
  17). Columns: refusals in the ledger, located in a transcript, sampled.
- `door_size.csv`: per door, lines of code and tests, number of tests, whether it has a bypass,
  whether it writes the ledger.
- `ask_audit.csv`: the ask audit, one row per item: window, week, the two codes and the final
  code. 559 items (299 before, 260 after); `audit.kappa` is computed over all of them, and
  `audit.kappa.before` and `audit.kappa.after` per window.
- `cost_weekly.csv`: per week and session kind, turns, tokens, the API-equivalent estimate.
- `replays_past.csv`: earlier replays of the in-scope cases (`DEVIATIONS.md`, deviations 14 and
  19), runs and violations without and with the whole instruction file; the model of those runs
  was not recorded.
- `rule_members.csv`: every member of the public rules, in the order the rule's cluster lists
  them: the text units (the `U` ids of `rules_coding.csv`) and the door entries (`<rule>.door<n>`),
  with both coders' labels and the final label of each. `rules.md` gives the rule that turns
  member labels into the rule's label.
- `door_refusals_test_rows.csv`: see "Test rows" above (week, time in UTC, rule, door type,
  located, took effect, in the review sample, the review codes, recovery turns and output tokens,
  why it is a test row).
- `case_facts.csv`: single facts about the case (commit counts, code size, the probe figures,
  the recorded coding kappas), each with its source.
