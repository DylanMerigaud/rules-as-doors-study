# Frozen analysis plan for the field data (descriptive analyses)

Frozen by the annotated git tag `prereg-v1`, together with `prereg/PREREG.md` (experiment E1).
Everything in this file above the section "Events of the field window" is frozen at the tag; that
section only receives dated additions. Every analysis here is descriptive: it carries counts and
intervals, never a p-value, and never attributes a change to one cause when several landed together.
The statistics are those of `PREREG.md` section 10.

## 1. Research questions

- **RQ1.** In a long-running agent harness, how often do behavioural rules delivered as prose hold,
  measured by recurrence of the violations they forbid and by replays with and without the text?
- **RQ2.** What changes when the same rule is delivered as a door, and what does a door cost
  (refusals that were wrong, work deferred, turns spent recovering, code to maintain)?
- **RQ3.** Which rules can become doors at all, and what property of a rule decides it
  (enforceability at a choke point the harness owns)?

## 2. Windows, weeks and time zone

- **Before window**: 2026-08-31 to 2026-09-20 (21 days, the ISO weeks starting 08-31, 09-07 and
  09-14): the first full day of the transcripts still on disk to the last day before the ask door
  and the scheduler cut-over.
- **After window**: 2026-09-21 to 2026-10-11 (21 days, the weeks starting 09-21, 09-28 and 10-05).
- **Freeze**: 2026-10-12. The extractions run for their final numbers on or after that day, over a
  snapshot taken that day; nothing after 2026-10-11 enters a window.
- **Prospective part**: from the tagger date of `prereg-v1` (as `git for-each-ref
  refs/tags/prereg-v1 --format='%(taggerdate:iso)'` prints it) to 2026-10-11 23:59:59. Events in
  that span happened after this plan was frozen; the paper names these days and keeps them apart
  from the retrospective part of the after window, which the authors had partly seen.
- Weeks start on Monday. Days and weeks are in the operator's time zone (Europe/Paris).
- Data before 2026-08-31 appear in the weekly series only, labelled partial: the transcripts before
  2026-08-30 were deleted by the coding agent's 30-day retention.

## 3. Sources (all public files are derived; the raw logs are not public)

| File | Built from | Keys | Content |
|---|---|---|---|
| `data/rules.csv` | instruction files, skills, memory notes, door sources and their history | rule id | one row per in-scope rule: class, delivery, dates, door type, enforceability |
| `data/corrections_weekly.csv` | the operator's corrections ledger and the fixed correction detector over the transcripts | week, rule id, delivery state | corrections and exposure (operator-active days) |
| `data/transcripts_weekly.csv` | the transcript snapshot | week, session kind, repository group (door, control), model id, tool version | sessions, operator turns, correction hits, turn ends, turn ends on a question and those the operator answered, question-tool calls, refusals per Stop and PreToolUse hook and whether each was followed by a new closing text |
| `data/transcripts_prospective.csv` | the same snapshot and extractor | part (retrospective, prospective), session kind, repository group | the columns of section 5's predictions, split at the tagger date |
| `data/scheduler_weekly.csv` | the scheduler's run ledger, its recovery ledger and the engagement log | week, door class | launches, outcomes, door refusals, recoveries, on-time execution of due obligations (in-scope jobs only) |
| `data/door_refusals_weekly.csv` | the door refusal ledger (from 2026-09-30) | week, rule id, door type | refusals, and how many took effect, did not, or cannot be judged |
| `data/door_review.csv` | a stratified sample of door refusals, coded twice | door (by rule id), stratum | the two codes of each sampled refusal (right, wrong, unclear), no content |
| `data/door_size.csv` | the door sources and their tests | rule id, door type | lines of code, lines of tests, number of tests |
| `data/ask_audit.csv` | turn ends and question-tool calls of the door repository in both windows, coded twice | window, week | the two codes of each ask, no content |
| `data/cost_weekly.csv` | the model usage ledger and the scheduler's token fields | week, session kind | turns, output tokens, the tool's API-equivalent cost estimate, share of the week's load |
| `data/replays_past.csv` | earlier replays of in-scope cases with and without the whole instruction file | case id | runs, violations per arm |
| `e1/results.jsonl` | experiment E1 | run | the outcomes of `PREREG.md` section 7 |

A session kind is one of: operator session, scheduler worker, popped terminal, subagent. The door
repository is the harness's own repository; the control group is the operator's other
repositories, which load the same global instruction file and have none of the project doors.
Counts from transcripts are keyed only by the keys above (time, session kind, repository group,
hook, rule id, model and tool version), never by topic, channel, person or platform.

## 4. Tables and figures

Each is produced by a script under `analysis/` from the file named, and every number the paper
prints is written to `results/numbers.json` with its source file, its counts and its interval.

- **Table 1, the rules.** In-scope rules by class, delivery (prose only, door only, both) and
  enforceability. Source: `data/rules.csv`.
- **Table 2, enforceability (RQ3).** The share of rules in E-full, E-partial and E-none, with Wilson
  intervals, and the same split for prose-only rules against rules with a door: do prose-only rules
  concentrate in E-none and E-partial? A rule that could not become a door is reported as a reason,
  not a failure. Source: `data/rules.csv`.
- **Table 3, per rule (RQ1, RQ2).** For each in-scope rule with at least one correction mapped to
  it: corrections of the rule per 100 exposure days in each delivery state (none, prose live, door
  live), counts and exposure printed, exact Poisson intervals. Rules with fewer than 5 exposure
  days in a state are listed for that state, not rated. Source: `data/corrections_weekly.csv`,
  with the delivery dates of `data/rules.csv`.
- **Figure 1, per-rule timelines.** For the rules of Table 3, the prose date, the door date and the
  weekly corrections on one time axis. Source: the same two files.
- **Figure 2 and Table 4, the weekly series.** Per week and session kind: operator turns,
  corrections per 100 operator turns, turn ends on a question per 100 turn ends, refusals per hook,
  with the model id and tool version in force marked on the axis. The week starting 2026-09-21 is
  marked as the week of two changes (the scheduler cut-over on 09-20 and the ask door on 09-21);
  the series never attributes a change of that week to one of them. The fall of the general rates
  that preceded both (the week starting 09-14) is shown, not explained away. Source:
  `data/transcripts_weekly.csv`.
- **Table 5, the ask door against its control (RQ2).** For the door repository and the control
  repositories, in the before and the after window, over operator sessions and popped terminals:
  turn ends that put a question to the operator and got his answer, over all turn ends (the gated
  measure), and turn ends with a question mark in their last 400 characters (a measure that does
  not depend on the gate). Each cell with its counts and Wilson interval; the change in each group
  with a Newcombe interval for the difference of two proportions. A group with fewer than 100 turn
  ends in a window is labelled insufficient for that window. Source: `data/transcripts_weekly.csv`.
- **Table 6, the prospective predictions.** The three predictions of section 5, each with its
  counts, interval and verdict. Source: `data/transcripts_prospective.csv`.
- **Table 7, the ask audit replicated.** The 2026-09-21 audit of avoidable asks, re-run with the
  codebook of section 7 by two independent coders (the same large language model, run separately
  with no access to each other's output), on the before window and on the after window: asks per
  class, the avoidable share with its Wilson interval, Cohen's kappa. Labelled model-coded.
  Source: `data/ask_audit.csv`.
- **Figure 3 and Table 8, the scheduler.** Launches, outcomes and door refusals per week and door
  class (precondition, executor cap, model-quota pacing, write door, operator-facing floor,
  recovery pause), in-scope jobs only; the share of due obligations executed within their period
  after the cut-over; and, before it, only what the engagement log allows (days with no logged
  activity, the share logged per day for obligations alive in both eras), each measure stating what
  it cannot say. Source: `data/scheduler_weekly.csv`.
- **Table 9, what a door costs (RQ2).** Per door: refusals and the share that took effect (the
  door refusal ledger); the share of refusals a second look calls wrong, on a stratified sample
  (up to 20 refusals per door drawn with `default_rng(20260930)`, all when fewer; two coders; kappa;
  labelled model-coded); the turns and output tokens between a refusal and the next accepted action
  (from the transcripts); lines of code and tests. Sources: `data/door_refusals_weekly.csv`,
  `data/door_review.csv`, `data/transcripts_weekly.csv`, `data/door_size.csv`.
- **Table 10, doors that failed.** The long-dash Stop hook's refusals against the ones followed by a
  new closing text, the bypasses each door carries (from its source), and the doors that write no
  ledger. Sources: `data/transcripts_weekly.csv`, `data/door_size.csv`, `data/rules.csv`.
- **Table 11, earlier replays.** Earlier replays of in-scope cases with and without the whole
  instruction file, per case, with Wilson intervals; the model of those runs was not recorded, and
  the table says so. Source: `data/replays_past.csv`.
- **Table 12 and Figure 4, experiment E1.** Per cell: V (both graders), B, E, K, C, turns, output
  tokens, wall time; the pooled values and intervals of H1 to H5 as `PREREG.md` defines them.
  Source: `e1/results.jsonl`.
- **Table 13, cost context.** Weekly model usage by session kind and the tool's API-equivalent cost
  estimate, which is an estimate printed by the tool on a subscription and never money spent.
  Descriptive context only. Source: `data/cost_weekly.csv`.

## 5. Preregistered predictions for the prospective part

Written before the days they concern existed. Each is judged on the prospective part only (section
2), over operator sessions and popped terminals, from `data/transcripts_prospective.csv`.

1. **The door repository stays low.** Turn ends that put a question to the operator and got his
   answer are at or below 1 percent of turn ends.
2. **The control repositories stay where they were.** The same share is at or above 2 percent. With
   fewer than 100 turn ends in the prospective part, the prediction is reported as insufficient,
   neither met nor failed.
3. **The promise gate keeps holding.** At least 80 percent of the promise Stop hook's refusals are
   followed by continued work (a new assistant turn before the next operator turn), over all
   session kinds the hook covers.

## 6. What changes the paper (field criteria)

- **The control repositories drop too**: their share of answered questions ending a turn falls
  below 2 percent over the full after window: the ask door's effect is not claimed; the fall is
  reported as shared.
- **The door repository drifts back**: the same share rises above 2 percent in the prospective part:
  the ask door's field result is reported as not holding forward. A value above 1 and at most 2
  percent fails prediction 1 and is reported as such, without this consequence.
- **Scope or class labels agree poorly** (Cohen's kappa below 0.6, for the rule inventory, the ask
  audit or the door review): the analysis that rests on them is shown under both codings and no
  pooled rate is given.

## 7. Codebook of the ask audit

Unit: one ask, that is a turn end whose closing block puts a question to the operator, or one call
of the question tool, in an operator session or a popped terminal of the door repository. Each
coder sees the ask and the session up to it, privately; only the codes are published.

- **only-him**: the answer needs something only the operator has: his own knowledge (a name, a
  price, a preference, a business call), a go on an irreversible or external gesture, or a fact
  absent from every file, ledger and page the tools can read.
- **avoidable**: the answer was already available or was the agent's to take: a choice the analysis
  in the session had already made, a go on internal or reversible work, a state a command or a page
  would confirm, a decision already written down.
- **not-an-ask**: a rhetorical or reported question, or a question to someone other than the
  operator.

One code per ask. The avoidable share is avoidable over (only-him plus avoidable). Disagreements
are resolved by a third pass that sees both codes; both original codes are kept and kappa is
computed on them.

## 8. Known confounds, stated before the numbers

- The scheduler cut-over (2026-09-20) and the ask door (2026-09-21) landed within a day; the global
  prose paragraph on asking landed the same morning as the ask door, for the door and the control
  repositories alike.
- The model and the tool changed during both windows (a new model generation in the week starting
  09-21 for the main model and in the week starting 09-28 for the smaller one; tool versions from
  2.1.258 to 2.1.285). Only comparisons that share those changes (door against control
  repositories) or pin them (E1) support a claim.
- The scheduler's workers run with no instruction file and no hook: the Stop doors do not cover
  them.
- A rule got a door because its prose failed, so prose-only failure rates are partly how doors were
  chosen; E1 compares arms on the same rule.
- A correction is a violation the operator noticed; prose rates from corrections are lower bounds.

## 9. Events of the field window

Known at registration:

- 2026-08-31: first full day of the transcripts still on disk.
- 2026-09-01: twelve rules promoted into the instruction files; the promise Stop hook live.
- 2026-09-20: the scheduler replaces the daily session.
- 2026-09-21: the ask door (Stop hook, question-tool hook, the workers' result schema) and the
  global prose paragraph on asking; the rule-announcement Stop hook.
- 2026-09-30: the door refusal ledger starts counting refusals and whether they took effect; the
  preregistration is tagged.

Dated additions after the tag (repairs, incidents, version changes) are appended below this line.
