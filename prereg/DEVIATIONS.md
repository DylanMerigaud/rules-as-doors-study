# Deviations from the preregistration

Each deviation from `prereg/PREREG.md` or `prereg/ANALYSIS.md` after the tag `prereg-v1` is appended
here, dated, with its reason and the runs or numbers it touches. None at registration.

## 2026-09-30, before the first counted run

1. **C1's question-tool door cannot fire.** Claude Code 2.1.285 does not offer the question tool
   (AskUserQuestion) in non-interactive runs (measured in a probe run). The PreToolUse hook on it
   is registered in C1's door arms as in production, but C1's door in E1 is in effect the Stop
   hook alone. Touches C1 AD and APD.
   Touches: `e1.C1.*` of the door arms, H1 and H2 through C1, `e1.C1.question_hook_ran` (0 of 20).
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
   Touches: every `e1.*` key; checked by `e1.isolation.operator_skills_listed` (0 of 200) and
   `e1.no_door_arms.hook_events` (0 of 100).
4. **Turn limit.** The runner sets no turn limit of its own; the 30-minute wall cap is the only
   limit of a run.
   Touches: `e1.n_killed`, `e1.n_void`.
5. **The two global long-dash hooks** are started as `python3 <hook>` instead of through their
   shebang; the code run is the pinned file.
   Touches: `e1.C4.*` of the door arms.
6. **Situations and graders after the pilot.** Four cases were redesigned (C1 twice, C2, C3 and
   C4 once each) and four graders refined after reading pilot runs, all before the first counted
   run and before the case files' commit; see `e1/PILOT.md`.
   Touches: every `e1.*` key; C3 most (`e1.C3.<arm>.V_first_committed_grader`, 0 of 10 in every
   arm, against `e1.C3.<arm>.V`).

## 2026-09-30, after the counted runs

7. **The long-dash Stop hook was repaired before E1, not after it.** PREREG section 11 planned the
   repair after the long-dash cells. It was made on 2026-09-30 at about 17:30 +0200, before the
   tag, by a separate change in the harness repository (the same change removed the gates' bypasses), and was not
   listed at registration. E1 is unaffected: every run used the pinned copy taken at 16:27 +0200,
   before the repair. The repair is dated in `ANALYSIS.md` section 9.
   Touches: the field keys `dashstop.*` and `weekly.*` (before and after the repair); no `e1.*`
   key.
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
   Touches: `audit.*`, `ask.*` through the audit's not-an-ask code.
12. **Test rows left out of the refusal counts.** Before the store door of 2026-10-05, test runs
    wrote refusal rows into the live ledger of two write doors; those rows (all but a handful have
    no session behind them) are excluded, and the real ones kept.
   Touches: `door.<id>.refusals`, `door.<id>.took_effect`, `door.<id>.refusals.<door type>`.
13. **Doors added after the rule inventory are not counted.** Five doors landed after the
    inventory and carry no rule identifier; they are listed and left out rather than coded late.
   Touches: `rules.*`, `doors.*`, `door.K137` to `door.K146` (their sizes).
14. **Past replays under the strict scope rule.** A replay case whose situation is a run of an
    excluded job is out of scope, even when its rule is in scope.
   Touches: `replays.*`.
15. **"Took effect" for write and pre-tool doors.** ANALYSIS.md defines it for turn-ending doors
    only; for a door that refuses a tool call it means the next call of the same tool ran.
   Touches: `door.K001.took_effect` and `door.K001.refusals.pretooluse_hook.took_effect` and
   `door.K001.refusals.write_refusal.took_effect` (113 and 6 of the 123 K001 refusals); the Stop
   doors (K029, K033, K039 and K001's 4 Stop refusals) keep the registered definition.

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
    Touches: `door.review.kappa`, `door.<id>.wrong_share`, `door.<id>.review.*`.
18. **The pinned Stop gates of C1 to C3 judged the text before the closing one.** The ask, promise
    and rule-announcement Stop hooks pinned for E1 read the last assistant text from the session
    transcript, which at Stop time does not yet hold the closing text, so each judged the text before
    it (C2's door arms: the decision equals the detector on the previous text at 22 of 22 stop
    attempts, on the closing text at 18 of 22). The same harness change that repaired the long-dash
    Stop hook (`ANALYSIS.md` section 9, 2026-09-30 17:27 +0200) made these hooks read the closing
    text from the Stop payload; that part of the change was not listed. E1 tested the doors as
    pinned. Found from review on 2026-10-13 with the published run records (`e1/runs.jsonl`); no
    counted result changes, the facts are new keys.
    Touches: `e1.C1.*`, `e1.C2.*`, `e1.C3.*` of the door arms (V, B, K, E), H2, H3 and H4 through
    them, and the new `e1.C2.door_arms.stop_decisions_match_detector_on_*` keys.

## E2 (tag `prereg-e2`), after its counted runs: none

E2's 220 counted runs ran on 2026-10-15 from 17:08:48 to 18:47:09 +0200, in the registered order,
4 at a time, all on Claude Code 2.1.300 with `claude-opus-5-5` reported by every run, trimwrit
`0ab0b33` and the pinned hooks; none was voided, none hit the wall cap, and the model-quota door
stayed open throughout. The analysis is the registered one (`analysis/table14_e2.py`). No E2
deviation to declare; one that appears later is numbered from 19 under this heading.
