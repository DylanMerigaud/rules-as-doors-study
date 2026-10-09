# Deviations from the preregistration

Each deviation from `prereg/PREREG.md` or `prereg/ANALYSIS.md` after the tag `prereg-v1` is appended
here, dated, with its reason and the runs or numbers it touches. None at registration.

## 2026-09-30, before the first counted run

1. **C1's question-tool door cannot fire.** Claude Code 2.1.285 does not offer the question tool
   (AskUserQuestion) in non-interactive runs (measured in a probe run). The PreToolUse hook on it
   is registered in C1's door arms as in production, but C1's door in E1 is in effect the Stop
   hook alone. Touches C1 AD and APD.
2. **One more pinned file.** The question-tool hook imports a module of the same repository
   (`rc_activity.py`, inert outside remote-control sessions). It was taken at the same commit as
   the other project hooks and added to the private pin list (sha256 `9faae8a8...c5650`).
3. **Isolation and confinement.** Each run gets a minimal environment (no inherited Claude Code or
   API variable) and an empty Claude Code config directory, which is how the operator's global
   instruction file and hooks are excluded (a run started from inside another Claude Code session
   otherwise inherits a mode that loads no project file and no hook). Runs execute inside Claude
   Code's sandbox (writes confined to the scratch repository, no network, reads under the
   operator's directories denied). The sandbox also keeps `.git/config` and `.claude/` read-only
   for the run: pilot runs could not switch a git hook on through `git config`. Same for every
   arm and case.
4. **Turn limit.** The runner sets no turn limit of its own; the 30-minute wall cap is the only
   limit of a run.
5. **The two global long-dash hooks** are started as `python3 <hook>` instead of through their
   shebang; the code run is the pinned file.
6. **Situations and graders after the pilot.** Four cases were redesigned (C1 twice, C2, C3 and
   C4 once each) and four graders refined after reading pilot runs, all before the first counted
   run and before the case files' commit; see `e1/PILOT.md`.

## 2026-09-30, after the counted runs

7. **The long-dash Stop hook was repaired before E1, not after it.** PREREG section 11 planned the
   repair after the long-dash cells. It was made on 2026-09-30 at about 17:30 +0200, before the
   tag, by a separate change in the harness repository (the same change removed the gates' bypasses), and was not
   listed at registration. E1 is unaffected: every run used the pinned copy taken at 16:27 +0200,
   before the repair. The repair is dated in `ANALYSIS.md` section 9.
8. **The privacy check dropped number-only tokens.** A results row was flagged because its output
   token count equalled a third party's name spelled as a number. The check was narrowed (a token
   with no letter is not an identifier, with a test); no result was changed.

## 2026-10-09, before the freeze (field extraction built, no field number published)

9. **The final transcript extraction reads two snapshots merged.** ANALYSIS.md section 2 says the
   field tables come from a snapshot taken on the freeze day. The transcript store keeps about 30
   days, so by 2026-10-12 most of the before window is gone (one week already fell from 1,212
   sessions in the 2026-09-30 snapshot to 73 on disk). The extraction therefore reads the freeze
   day snapshot merged with the 2026-09-30 one; each older file is checked to be a prefix of its
   newer copy, and the weeks before 2026-09-28 reproduce the 2026-09-30 output exactly.
10. **The long-dash Stop block is counted in both forms.** After its repair (deviation 7) the hook
    reports its block in a different form, which the registered detector did not match; both forms
    are counted, so the weeks after the repair are not read as zero blocks.
11. **The ask audit's coders.** Each coder is a separate headless call of the pinned model with no
    tool and no instruction file, the codebook as its whole system prompt; an answer from another
    model is rejected and recoded. Coders see the tails of the last two operator messages and the
    end of the closing text, not the whole session. The item filter is wide on purpose and a
    not-an-ask code removes false items. Disagreements go to a third model call, not a person.
    The before window items come from the 2026-09-30 snapshot.
12. **Test rows left out of the refusal counts.** Before the store door of 2026-10-05, test runs
    wrote refusal rows into the live ledger of two write doors; those rows (all but a handful have
    no session behind them) are excluded, and the real ones kept.
13. **Doors added after the rule inventory are not counted.** Five doors landed after the
    inventory and carry no rule identifier; they are listed and left out rather than coded late.
14. **Past replays under the strict scope rule.** A replay case whose situation is a run of an
    excluded job is out of scope, even when its rule is in scope.
15. **"Took effect" for write and pre-tool doors.** ANALYSIS.md defines it for turn-ending doors
    only; for a door that refuses a tool call it means the next call of the same tool ran.
