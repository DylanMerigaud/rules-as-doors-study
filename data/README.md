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
- **The ask shares known at registration and the published ones.** `ask.registration.*` come
  from the design inventory of 2026-09-30, `ask.<group>.<window>.*` from the final extraction;
  they differ in the denominator (turn ends a human message followed, against every turn end) and
  in what counts as asking (an asking phrase, against a turn end that ends on a question mark).
  `ask_reconcile.csv` changes one definition at a time on the same snapshot (`DEVIATIONS.md`,
  deviation 22): the question-mark rule takes the control's before share from 7 of 119 to 0 of
  119.
- **Test rows.** `door_refusals_test_rows.csv` lists the one counted ledger refusal that came
  from a planted test session (`DEVIATIONS.md`, deviation 20), with its recovery turns and
  output tokens. The published counts keep it. The K001 counts, took-effect shares, recovery
  means, review frame, review items, wrong shares (pooled and per coder), raw agreement and the
  pooled review kappa each have a `.without_test_session` twin. Kept with no twin: the total over
  every door in `door.refusals.not_located` (9 of 192), and `door.K001.review.kappa` and
  `.n_unclear`, whose values do not change without it (the item was coded right by both
  coders).

## What an interval treats as independent

- **Field shares** (`ask.*`, `prosp.*`, `dashstop.*`, `dashwrite.*`, `weekly.*`, `sched.*`,
  `door.<rule>.*.took_effect`, `door.<rule>.wrong_share`, `audit.*`): Wilson intervals that treat
  each counted event as one independent trial: a turn end, a refusal, a write call, a review or
  audit item, a due row-day. The events are nested in sessions (for the ask shares,
  `ask.<group>.<window>.sessions`: 141 and 555 door-group sessions, 9 and 20 control sessions),
  in days and in rules, and the events of one session are not independent, so these intervals are
  narrower than intervals that modelled that nesting; no field interval models it. The Newcombe
  intervals of differences (`ask.*.diff`, `rules.rq3.diff.*`, `replays.*.diff`) use the same unit.
- **Rates per 100 operator-active days** (`perrule.*.rate`): exact Poisson intervals that treat
  each correction as an independent event over the exposure days.
- **Agreement**: kappas and Gwet's AC1 resample items (units, refusals, audit items, corrections);
  `rules.kappa_*.rule_cluster` resamples rules.
- **Replays**: a cell's share (Wilson) treats each of its 10 runs as independent. A pooled
  hypothesis value is a mean over 4 or 5 cases, with the registered cluster bootstrap over cases
  (10,000 resamples, `default_rng(20260930)`), which has only 35 (4 cases) or 126 (5 cases)
  distinct resamples. When cases sit at exactly 0, the draws made of them alone give 0, and a
  percentile bound lands on 0 once they pass 2.5 percent of the draws
  (`<key>.draws_from_zero_cases`). Exploratory checks that do not use the bootstrap: the Student t
  interval over the per-case values (`.t95`, and `.t95.clipped` cut at the statistic's range), the
  sign count over cases (`.n_cases_positive`), the smallest level an exact sign test over 4 or 5
  cases can reach (`small_sample.exact_sign_test.<n>_cases`: 1 of 16 and 1 of 32, so with 4 or 5
  cases no exact test over cases reaches the 2.5 percent of one tail), and the Wilson bound of a zero
  (`small_sample.wilson.*`). They decide nothing; the registered criteria do.

## Who produced each label and each grader

No label, grader decision or code in this package was checked by a person; the author operated
the harness and set its rules, and every step below was done by code or by Anthropic's
`claude-opus-5-5`, the model whose turns the study judges.

- **Replay graders** (`e1/graders.py`, `e2/graders.py`): written by the model through Claude
  Code. E1's were first committed at 3bd3559 and refined after the model read the pilot output
  (`prereg/DEVIATIONS.md`, deviations 6 and 23); E2's changes were committed before any E2 run.
  Their proofs (`proof.json`) and tests were written by the same model; each completion grader
  is shown to fail on a copy of a real complete run with one item of the task broken
  (`e1/tests/test_completion_can_fail.py`). The door detectors in `e1/hooks/` and `e2/hooks/` are
  the harness's own hooks, part of the harness code the model wrote most of.
- **Rule inventory**: a script split every prose source into units (a paragraph or list item
  outside code fences; a memory note is one unit) and kept the units its normative-word pattern
  matched; units whose path marks them out of scope were not coded. Two coders, separate calls of
  the model with the codebook and no access to each other's output, gave each unit five labels
  (is a rule, class, enforceability, scope, the doors that enforce it); a third call of the same
  model saw both codes and resolved each disagreement, and both original codes are kept.
  Agreement: on the rule-or-not screen over the 256 candidate units whose final scope is in
  (`rules.screen.agreement`, `rules.screen.kappa`, `rules.screen.cells`: 177 end as rules, the
  published units, and 79 as not a rule), and on class and enforceability over the units both
  coders called a rule (`rules.kappa_class`, `rules.kappa_enforceability`). Agreement over every
  candidate unit is not published: that pool includes the out-of-scope units, of which the study
  gives no count. The doors were listed by a script from the harness's code (registered hooks,
  refusal sites) and coded the same way.
- **Grouping units into rules** and the public description of each rule: one pass of the same
  model, with no second coder; no agreement is measured. Each description passed the
  privacy check, and a description the check refused was rewritten by the model.
- **Corrections**: two sources, the corrections the operator logged in the correction ledger and
  the operator's typed inputs that the pinned correction detector (a regular expression) flagged.
  A deterministic join gave a first rule for ledger rows (their tag, the rule it was promoted to,
  the unit that holds it). Two coders (calls of the same model) then read each correction and
  the rule list and gave its rule or none, and whether it corrects a behaviour at all; coder 1
  saw the first join, coder 2 did not. The published table uses coder 1's rule, and leaves out a
  correction whose coders disagree on in scope or out. Agreement on the rule over the 84
  corrections that at least one coder mapped to a public rule: `corrections.mapping.agreement`,
  `.kappa` and `.disagreements`. The detector's precision over all its hits is not published (the
  hits include out-of-scope corrections); the coders' "corrects a behaviour" code is the screen
  that removed hits that correct nothing.
- **Door refusal review** (right, wrong, unclear) and **ask audit** (only-him, avoidable,
  not-an-ask): two coders and a third resolving call per item, all the same model; kappas `door.<rule>.review.kappa`, `audit.kappa`, and AC1
  `door.<rule>.review.ac1`.
- **Everything else** (session kinds, turn ends, the answered share, took effect, recovery,
  scheduler outcomes, the replay measures) is computed by code from the logs, with no model call.

## What the raw logs can hold, and what left the machine for coding

- **The raw logs.** Session transcripts, the harness's ledgers and the replay's raw runs. A
  transcript can hold other people's personal data wherever it appeared in what a session read
  or wrote: names, contact details, account names and text other people wrote. The replay runs
  work in scratch repositories on the published prompts; one word of one E1 run text matched the
  list of third-party names and is redacted, and no word of E2's did (`e1/REDACTIONS.md`,
  `e2/REDACTIONS.md`, R60). Nothing in this package holds a transcript's text: the field files are
  counts and ids, and every published file passes the privacy check before a push.
- **The coding calls.** Every coder above was a headless call of `claude-opus-5-5`, Anthropic's
  hosted model, through Claude Code under the author's own subscription, with the provider the
  sessions themselves ran on; every recorded answer names that model (the ask audit rejected and
  coded again the answers another model gave, `DEVIATIONS.md`, deviation 11). Each call had no tool (`--tools ""`), no instruction file, hook
  or skill (`--bare`), ran from a scratch directory outside every repository and got its input on
  standard input; the rule, correction and ask coders also kept no local session record.
- **What each coder saw**, at most: a rule unit's text (1,400 characters) with its source kind
  and section heading; a door's refusal text (400) and description (900); a correction message
  (900) and the consequence the ledger recorded (400), with the rule list (id, heading, 110
  characters of text); for a refused end of turn, the operator's last message before it (its last
  1,500 characters) and the refused closing text (its last 6,000); for a refused tool or write
  call, the tool, the target file and windows of 300 characters around each forbidden character
  (at most 6), or the first 4,000 characters; for an ask, the last 1,200 characters of each of
  the operator's last two messages and the last 3,000 characters of the closing text or of the
  question tool's input.
- **Screening.** None: the excerpts were not screened for other people's data before coding.
  The rule coders saw candidate units later coded out of scope, which is how those were found.
  The coders' outputs kept on the machine are ids and codes; the item texts stay in private files
  there, and none is published.

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
  took effect, did not, cannot be judged, and the recovery measures. Every in-scope door with a
  counted refusal has its rows here. Of the 9 doors that write this ledger (`door_size.csv`,
  `writes_ledger`), three have none: K003's write refusal (its rows of the window are write-door
  rows that no session transcript shows, which deviation 12 leaves out), and the PreToolUse hooks
  of K039 and K089, which wrote no row in the window (`door.ledger_doors.without_counted_refusal`).
  The scheduler preconditions and the recovery pause write the scheduler's own ledgers (Table 8).
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
  the recorded coding kappas, the agreement on the rule-or-not screen and on the correction
  mapping, the tag and push times of the two preregistrations), each with its source. The push
  times are GitHub's record of the push of the commit each tag names
  (`e1.git.prereg_v1_commit_public_push`, `e2.git.prereg_e2_commit_public_push`); GitHub keeps no
  record of the tag pushes themselves.
- `ask_reconcile.csv`: the ask measure's before window rerun on the 2026-09-30 snapshot, one
  definition changed per step from the design inventory (A) to the final extraction (F): step,
  group, asked turn ends, turn ends, and what the step changes (`DEVIATIONS.md`, deviation 22).
