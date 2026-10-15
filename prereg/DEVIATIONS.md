# Deviations from the preregistration

Each deviation from `prereg/PREREG.md` or `prereg/ANALYSIS.md` after the tag `prereg-v1` is appended
here, dated, with its reason and the runs or numbers it touches. None at registration.

Each "Touches" line names the keys of `results/numbers.json` the deviation bears on, and says
whether it changed their values (how they were computed or what entered them) or only what they
measure. Exact since review round 2 (2026-10-15); `<case>`, `<arm>`, `<id>` and `<week>` stand
for every value they take.

## 2026-09-30, before the first counted run

1. **C1's question-tool door cannot fire.** Claude Code 2.1.285 does not offer the question tool
   (AskUserQuestion) in non-interactive runs (measured in a probe run). The PreToolUse hook on it
   is registered in C1's door arms as in production, but C1's door in E1 is in effect the Stop
   hook alone. Touches C1 AD and APD.
   Touches (what is measured, not how): `e1.C1.AD.*` and `e1.C1.APD.*` (C1's door arms tested
   one door, the Stop hook, not two), and through them `e1.h2.*`, `e1.h3.*` and `e1.h4.*`;
   checked by `e1.C1.question_hook_ran` (0 of 20). No key of another case.
2. **One more pinned file.** The question-tool hook imports a module of the same repository
   (`rc_activity.py`, inert outside remote-control sessions). It was taken at the same commit as
   the other project hooks and added to the private pin list (sha256 `9faae8a8...c5650`).
   Touches: no number (the module is not published; `e1/REDACTIONS.md`).
3. **Isolation and confinement.** Each run gets a minimal environment (no inherited Claude Code or
   API variable) and an empty Claude Code config directory, which is how the operator's global
   instruction file and hooks are excluded (a run started from inside another Claude Code session
   otherwise inherits a mode that loads no project file and no hook). Runs execute inside Claude
   Code's sandbox (writes confined to the scratch repository, no network, reads under the
   operator's directories denied). The sandbox also keeps `.git/config` and `.claude/` read-only
   for the run: pilot runs could not switch a git hook on through `git config`. Same for every
   arm and case.
   Touches (the conditions of all 200 runs, no computation): every key a run produces
   (`e1.<case>.<arm>.*`, `e1.h1.*` to `e1.h5.*`, `e1.door_arms.*`, `e1.refused_runs`). For C3 it
   also removed one way to comply: a run could not switch on a git hook through `git config` or
   write under `.claude/` (`e1.C3.*`). Checked by `e1.isolation.operator_skills_listed` (0 of
   200) and `e1.no_door_arms.hook_events` (0 of 100).
4. **Turn limit.** The runner sets no turn limit of its own; the 30-minute wall cap is the only
   limit of a run.
   Touches: `e1.n_killed` (0) and `e1.n_void` (0); no run reached the wall cap, so no other key.
5. **The two global long-dash hooks** are started as `python3 <hook>` instead of through their
   shebang; the code run is the pinned file.
   Touches (how the hook was started, not the code run): `e1.C4.AD-stop.*`, `e1.C4.APD-stop.*`,
   `e1.C4.AD-write.*`, `e1.C4.APD-write.*`, and through them `e1.h2.*` to `e1.h5.*`.
6. **Situations and graders after the pilot.** Four cases were redesigned (C1 twice, C2, C3 and
   C4 once each) and four graders refined after reading pilot runs, all before the first counted
   run and before the case files' commit; see `e1/PILOT.md`.
   Touches (values): every key a grader decides, that is V, C, E and the Stop K of every cell
   (`e1.<case>.<arm>.V`, `.C`, `.E`, `.K`), `e1.h1.*` to `e1.h4.*`, the detector-free parts of
   `e1.C4.*`, and the pilot outcomes in `e1/PILOT.md` (and with them which situations were kept).
   Not touched: blocks (`.B`), the write door's K (`e1.h5.write.*`), the door's detector
   (`.V_door`) and the run facts. The counted runs graded with the graders as first committed
   (`e1/graders_first_committed.py`, verbatim from 3bd3559): V differs in 20 of 200 runs, all in
   C3 (`e1.first_graders.runs_with_another_V`), where it is 0 of 10 in every arm; H1 is then
   `e1.first_graders.h1.diff` (supported by the registered criterion) and H2 to H4 stay not
   supported (`e1.first_graders.*`). Under the graders in force when the pilot ran (the V the
   driver recorded at the end of each pilot run equals the V of the first committed graders in
   30 of 30 runs, `e1.pilot.recorded_equals_first_graders`; the first pilot batch started at
   18:19 +0200, before that commit at 18:24), C3's kept situation had no violating pilot run
   (`e1.pilot.kept_without_violation.first_graders`) and so
   failed the registered pilot rule, and C2's first situation had one (`e1.pilot.C2.s1.*`) and was
   redesigned anyway. The pilot runs, their times and V under both grader versions are in
   `e1/pilot_runs.csv`.

## 2026-09-30, after the counted runs

7. **The long-dash Stop hook was repaired before E1, not after it.** PREREG section 11 planned the
   repair after the long-dash cells. It was made on 2026-09-30 at about 17:30 +0200, before the
   tag, by a separate change in the harness repository (the same change removed the gates' bypasses), and was not
   listed at registration. E1 is unaffected: every run used the pinned copy taken at 16:27 +0200,
   before the repair. The repair is dated in `ANALYSIS.md` section 9.
   Touches (what is measured): the field keys `dashstop.*`, `weekly.<week>.*` from 2026-09-28
   and `door.K001.refusals.stop_hook*` (the ledger holds the repaired hook only); no `e1.*` value.
   It made the tagged description of the pinned hooks as "the door as it ran in production" out
   of date at the tag, which is why E2 (`e2/`) reran the door arms with the repaired hooks.
8. **The privacy check dropped number-only tokens.** A results row was flagged because its output
   token count equalled a third party's name spelled as a number. The check was narrowed (a token
   with no letter is not an identifier, with a test); no result was changed.
   Touches: no number.

## 2026-10-09, before the freeze (field extraction built, no field number published)

9. **The final transcript extraction reads two snapshots merged.** ANALYSIS.md section 2 says the
   field tables come from a snapshot taken on the freeze day. The transcript store keeps about 30
   days, so by 2026-10-12 most of the before window is gone (one week already fell from 1,212
   sessions in the 2026-09-30 snapshot to 73 on disk). The extraction therefore reads the freeze
   day snapshot merged with the 2026-09-30 one; each older file is checked to be a prefix of its
   newer copy, and the weeks before 2026-09-28 reproduce the 2026-09-30 output exactly.
   Touches: every key from `data/transcripts_weekly.csv` and `data/transcripts_prospective.csv`
   (`weekly.*`, `ask.*`, `prosp.*`, `dashstop.*`, `dashwrite.*`, `transcripts.*`, `headless.*`),
   and `audit.before.*`.
10. **The long-dash Stop block is counted in both forms.** After its repair (deviation 7) the hook
    reports its block in a different form, which the registered detector did not match; both forms
    are counted, so the weeks after the repair are not read as zero blocks.
   Touches: `dashstop.*`, `dashstop.repair_week_and_after.*`, `weekly.<week>.*` from 2026-09-28.
11. **The ask audit's coders.** Each coder is a separate headless call of the pinned model with no
    tool and no instruction file, the codebook as its whole system prompt; an answer from another
    model is rejected and recoded. Coders see the tails of the last two operator messages and the
    end of the closing text, not the whole session. The item filter is wide on purpose and a
    not-an-ask code removes false items. Disagreements go to a third model call, not a person.
    The before window items come from the 2026-09-30 snapshot.
   Touches: `audit.*` only. The `ask.*` shares come from the transcripts and do not use the
   audit (an earlier version of this line said they did).
12. **Test rows left out of the refusal counts.** Before the store door of 2026-10-05, test runs
    wrote refusal rows into the live ledger of two write doors; those rows (all but a handful have
    no session behind them) are excluded, and the real ones kept.
   Touches (values): `door.<id>.refusals`, `door.<id>.refusals.<door type>`,
   `door.<id>.took_effect`, `door.<id>.refusals.<door type>.took_effect`,
   `door.<id>.recovery_*` and `door.<id>.review.frame.*`. One planted row the filter missed is
   deviation 20.
13. **Doors added after the rule inventory are not counted.** Five doors landed after the
    inventory and carry no rule identifier; they are listed and left out rather than coded late.
   Touches (what enters): `doors.*` (the 24 doors counted), `door.<id>.loc`,
   `door.<id>.n_tests`, `door.<id>.test_loc`; no `rules.*` value (the five doors carry no rule).
14. **Past replays under the strict scope rule.** A replay case whose situation is a run of an
    excluded job is out of scope, even when its rule is in scope.
   Touches (what enters): `replays.*`. The tagged PREREG's sentence on the earlier replays is
   about all of them and no key reproduces it; Table 11 is deviation 19.
15. **"Took effect" for write and pre-tool doors.** ANALYSIS.md defines it for turn-ending doors
    only; for a door that refuses a tool call it means the next call of the same tool ran.
   Touches (how it is computed): `door.K001.took_effect`,
   `door.K001.refusals.pretooluse_hook.took_effect` and `door.K001.refusals.write_refusal.took_effect`
   (113 and 6 of the 123 K001 refusals). The Stop doors (K029, K033, K039 and K001's Stop
   refusals) keep the registered definition, read as the ledger's daily pass reads it
   (`data/README.md`). No review key depends on it.

## 2026-10-13, after review (round 1), no counted case or result changed

16. **The exploratory cells were not run.** PREREG section 5 allowed C1 and C2 on
    `claude-sonnet-5-5` if the weekly quota allowed after the counted runs; they were not run, so no
    second model was tried. Logged here from review; the count was already in the results.
    Touches: `e1.n_exploratory_runs` (0).
17. **The door review sample is drawn per door type and only from located refusals.** ANALYSIS.md
    section 4 says up to 20 refusals per door. The draw took a door as a (rule, door type) stratum,
    so K001's three door types were sampled separately (20 of its PreToolUse refusals, all 4 Stop
    and all 6 write refusals), and only refusals found in a transcript could be coded (107 of 113,
    4 of 4, 6 of 6 for K001; 30 of 30 for K029; 19 of 21 for K033; 17 of 18 for K039).
    `data/door_review_frame.csv` gives the frame.
    Touches (what enters): `door.review.kappa`, `door.<id>.wrong_share`, `door.<id>.review.*`
    and the per-coder keys `door.<id>.wrong_share.coder1`, `.coder2` of review round 2.
18. **The pinned Stop gates of C1 to C3 judged the text before the closing one.** The ask, promise
    and rule-announcement Stop hooks pinned for E1 read the last assistant text from the session
    transcript, which at Stop time does not yet hold the closing text, so each judged the text before
    it (C2's door arms: the decision equals the detector on the previous text at 22 of 22 stop
    attempts, on the closing text at 18 of 22). The same harness change that repaired the long-dash
    Stop hook (`ANALYSIS.md` section 9, 2026-09-30 17:27 +0200) made these hooks read the closing
    text from the Stop payload; that part of the change was not listed. E1 tested the doors as
    pinned. Found from review on 2026-10-13 with the published run records (`e1/runs.jsonl`); no
    counted result changes, the facts are new keys.
    Touches (what is measured, not how): `e1.C1.AD.*`, `e1.C1.APD.*`, `e1.C2.AD.*`,
    `e1.C2.APD.*`, `e1.C3.AD.*`, `e1.C3.APD.*` (V, B, K and E: the doors refused on the earlier
    text), `e1.h2.*`, `e1.h3.*` and `e1.h4.*` through them; the facts are
    `e1.C2.door_arms.stop_decisions_match_detector_on_*`. E2 (`e2/`) is the run with the repaired
    reading.

## E2 (tag `prereg-e2`), after its counted runs: none

E2's 220 counted runs ran on 2026-10-15 from 17:08:48 to 18:47:09 +0200, in the registered order,
4 at a time, all on Claude Code 2.1.300 with `claude-opus-5-5` reported by every run, trimwrit
`0ab0b33` and the pinned hooks; none was voided, none hit the wall cap, and the model-quota door
stayed open throughout. The analysis is the registered one (`analysis/table14_e2.py`). No E2
deviation to declare. Deviations 19 to 21 below were logged after review round 2 and concern E1's
earlier replays and the field record, not E2.

## 2026-10-15, after review (round 2), no counted case or result changed

19. **Table 11 is reported on the in-scope earlier replays only.** `ANALYSIS.md` registers Table
    11 (the earlier replays), and PREREG section 12 bases the H1 prediction on them. The table and
    its keys cover the earlier replay cases whose rule and situation are both in scope (deviation
    14): the other earlier replay cases concern rules outside the study's scope (rules and jobs
    that concern other people or their data), and the study gives no count of them. The tagged
    PREREG keeps its own sentence. The in-scope cases compare the whole instruction file given and
    left out, on a model their runs did not record, which is not E1's paragraph ablation on
    `claude-opus-5-5`.
    Touches: `replays.*`, with the per-case keys `replays.<case>.v_without`, `.v_with` and `.diff`
    and the pooled runs `replays.pooled_runs.*`; no `e1.*` key.
20. **One planted test session was counted in the door refusal ledger.** The check of the
    repaired long-dash Stop hook (`ANALYSIS.md` section 9) ran a planted session in a scratch
    repository on 2026-09-30 at 17:39 UTC, which is 19:39 +0200, after the tag (`ANALYSIS.md`
    section 9 writes "17:39 +0200": the hour is UTC). Deviation 12's filter left out planted
    sessions by their name and missed this one, which ran under another name. It is one of
    K001's 4 Stop refusals in the ledger, took effect, and is one of the 4 sampled K001 Stop
    items (coded right by both coders). The counted keys stay as published; the row is
    `data/door_refusals_test_rows.csv`, and the `.without_test_session` keys give every count
    without it.
    Touches: `door.K001.refusals`, `door.K001.refusals.stop_hook`, `door.K001.took_effect`,
    `door.K001.refusals.stop_hook.took_effect`, `door.K001.review.frame.stop_hook`,
    `door.K001.review.n_items`, `door.K001.wrong_share` and `door.review.kappa` (each has a
    `.without_test_session` twin), and the ledger side of the comparison with
    `dashstop.repair_week_and_after.*` (`data/README.md`).
21. **The control criterion of the ask door was applied as "is below 2 percent".** `ANALYSIS.md`
    section 6 says the control's share "falls below 2 percent over the full after window".
    `analysis/table05_ask_door.py` applied it as "is below 2 percent" and the change was not
    logged. The control's share was 0 of 220 before the door, so it could not fall below 2
    percent: read word for word, the condition is not met (`ask.criterion.control_drops.literal`);
    read as applied, it is met (`ask.criterion.control_drops`). With the control at 0 before, no
    reading can separate the door's effect from what the control did. Prediction 2 ("stay where
    they were ... at or above 2 percent") meets the same 0 before
    (`prosp.control.prediction2.literal`). The values known when both were written, from the
    design inventory of 2026-09-30, are `ask.registration.*` (control 8 of 133 before, 2 of 39
    after); the final extraction (deviations 9 and 11) gives `ask.control.*`.
    Touches: `ask.criterion.control_drops` (its reading, not its value), and the new
    `ask.criterion.control_drops.literal`, `prosp.control.prediction2.literal` and
    `ask.registration.*`.
