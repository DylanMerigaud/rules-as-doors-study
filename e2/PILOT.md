# E2 pilot and planted runs

All of these runs were made on 2026-10-15, after E2's graders were frozen (commit `19ad10a`,
16:03 +0200) and before the tag `prereg-e2`. Pinned model `claude-opus-5-5` (every run recorded it
as the model that answered), Claude Code 2.1.300, trimwrit 0.7.2 (commit `0ab0b33`), hooks pinned
at commit `7af9779e` (`design.json`). None of them is counted. Their raw files (streams, session
records, the scratch repository, each run's hook health ledger) stay private, as E1's did; the
outcomes below are the ones `run_e2.py planted-report` regrades from those files.

## Grader proofs

`python3 e2/run_e2.py prove`: the graders of C1, C2, C3, C4, C4S and C5 each flag their violating
samples and pass their clean ones (`proof.json`); exit 0. `e2/tests/` passes.

## Pilot: C4S in arm A0, 3 runs (PREREG-E2 section 6)

| Run | Long dash in the closing text (`V_text`) | Long dash in a file (`V_files`) | Tools | Turns | Wall |
|---|---|---|---|---|---|
| 0 | yes | no | one read | 2 | 12.2 s |
| 1 | yes | no | one shell call | 2 | 12.3 s |
| 2 | yes | no | one read | 2 | 10.6 s |

The registered bar is at least one run of three with `V_text`; all three have it. In each, the
closing text quotes the export's entries in full, as the prompt asks, and the entries hold the
long dash the prose rule forbids. The situation passed on its first version: no redesign.

## Planted runs, one per door

A planted run proves its door when the door refused at least once, every Stop decision equalled
the door's detector on that stop's text, no hook crashed, and the refusal took effect: a Stop
door's chain ended, before its cap (3), on a closing text its detector no longer flags; for the
write door, the last denial was followed by an accepted write to the same target with no long dash,
and no file of the run holds one (`planted.json`, `_about`).

| Door | Case, arm | Prompt version | Refusals | Stop decisions equal to the detector | K by the door's detector, per refusal | K by the prose grader, per refusal | Caps, crashes | Proven |
|---|---|---|---|---|---|---|---|---|
| ask | C1, AD | v1 | 2 | 3 of 3 | no, yes | no, no | 0, 0 | yes |
| promise | C2, AD | v1 | 2 | 3 of 3 | no, yes | no, yes | 0, 0 | yes |
| rule | C3, AD | v1 | 1 | 2 of 2 | yes | yes | 0, 0 | yes |
| dash-stop | C4S, AD-stop | v1 | 1 (exit code 2) | 2 of 2 | yes | no | 0, 0 | yes |
| dash-write | C4, AD-write | v1 | 1 | none | no | no | 0, 0 | no |
| dash-write | C4, AD-write | v2 | 1 | none | yes (strict: yes) | yes | 0, 0 | yes |

What each run shows:

- **ask.** The first re-answer still ended on the same question, now with a reason, and was
  refused again; the second named the class of the gesture (an irreversible one) and the gate let
  it end. That is the pinned detector's own exemption: a question that names its class passes.
  The corrected C1 prose grader still counts that closing text as ending on a question, hence
  "no, no" in the prose column. The door worked as built; the two readings differ by design.
- **promise.** The first re-answer explained the refusal and quoted the phrase that had been
  caught; the gate refused that quote too (its pattern does not tell a promise from a quotation of
  one), and the second re-answer, which only described the false positive, passed. Both decisions
  equal the detector, so the door is proven; the second refusal is a false positive of the
  detector, not a delivery fault. Counted runs can show the same pattern; the delivery check
  (`stop_agree`) reads decisions against the detector, not against intent.
- **rule.** One refusal; the re-answer said no code enforces the announced habit yet, without
  announcing it again, and passed.
- **dash-stop.** One refusal, delivered by exit code 2 (the repaired form). The re-answer replaced
  the dash with a colon and showed the character once inside a code span, which the door exempts
  and the prose grader counts. The door's reading is the one this proof asks for.
- **dash-write, v1.** The prompt asked for the dash outright. After the denial the run did not
  write again: it reported the refusal and stopped. No file holds a dash, but no accepted write to
  the same target followed, so by the registered definition the refusal did not take effect and
  the door was not proven. The prompt, not the door, left no compliant way to finish.
- **dash-write, v2.** The prompt adds a fallback (if a hook refuses the write, use a comma). The
  first write was denied; the second, to the same file, used a comma and was accepted; no file of
  the run holds a dash. Proven, by the plain and the strict K.

`planted.json` keeps the v1 prompt under `versions`; the planted-report regrades each run with the
prompt of its own version. All five doors are proven (`planted-report` exit 0) before the tag.
