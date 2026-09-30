# data/rules.csv

One row per in-scope behavioural rule of the harness, as inventoried on 2026-09-30. A rule is a
statement of what the agent must or must not do that one observable action can violate. Units of
text that state the same rule in several places (instruction files, skills, memory notes) are
grouped into one row, and a door that enforces the rule belongs to that row. Rules and doors that
concern other people or their data are left out and are not counted here.

Columns:

- `id`: the rule's id in this study (ids are not contiguous).
- `description`: a generic English description written for publication; the rule texts
  themselves are not public.
- `class`: cap, pace, window, never, gate, sequence, ask, stop, write-path or other.
- `delivery`: prose only, door only, or both.
- `prose_first_seen`: the first date the rule's text is found (the first commit that carries its
  key phrase, else the first commit of its file, else the earliest date of the note that holds it).
- `prose_date_censored`: 1 when that date is the first day of the file's own version history,
  so the text is at least that old (read it as "on or before").
- `prose_removed`: the date the text left the instruction files, empty while it is live.
- `door_type`: lifecycle hook, write refusal, scheduler precondition, recovery pause or test.
- `door_landed`: the first commit of the earliest door enforcing the rule.
- `door_date_censored`: 1 when that door lives in a directory whose history starts on that day.
- `n_doors`: the number of doors enforcing the rule.
- `enforceability`: E-full (the violating action passes one choke point the harness owns, where
  code sees the violation itself), E-partial (a choke point sees only a proxy of it), E-none
  (judging a violation needs understanding no code has).
- `prose_sources`: the kinds of text that state the rule.
- `n_prose_units`: the number of text units grouped into the rule.

Coding: two independent coders (both the same large language model, run separately without
access to each other's output) coded every unit; a third pass of the same model resolved each
disagreement and both original codes are kept in the private table. The labels are model-coded.
