# data/rules.csv

One row per in-scope behavioural rule of the harness, as inventoried on 2026-09-30. A rule is a
statement of what the agent must or must not do that one observable action can violate. Units of
text that state the same rule in several places (instruction files, skills, memory notes) are
grouped into one row, and a door that enforces the rule belongs to that row. Rules and doors that
concern other people or their data are left out and are not counted here.

Columns:

- `id`: the rule's id in this study. Ids are not contiguous: they were given before the
  inventory's last review, and an id that left the inventory then was not reused. The gaps are not
  a count of the rules left out of scope (a rule left out before ids were given never had one),
  and the study gives no such count.
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
disagreement. The labels are model-coded. The coders were not blind to the doors: the codebook
gave them the list of doors and asked which door, if any, enforces each unit (its field 5), so a
unit's class and enforceability were coded knowing whether a door existed.

`data/rules_coding.csv` publishes both coders' labels for the 177 text units behind the public
rules (a unit id, the rule it belongs to, and per coder: is it a rule, its class, its
enforceability); the unit texts stay private. The class and enforceability kappas are computed on
the 174 units both coders called a rule, and `analysis/field_supplement.py` recomputes them from
this file (`rules.kappa_class.recomputed`, `rules.kappa_enforceability.recomputed`, equal to the
recorded `rules.kappa_class` and `rules.kappa_enforceability`).

Door entries and door-only rules: a door is coded like a text unit. Its unit is the door's own
refusal text and description; the same codebook, two independent coders of the same model and a
third resolving pass give it a class and an enforceability. The 12 door-only rules (K003, K047,
K137 to K146) have no text unit: each one is a single door entry, so its labels come from that
entry alone and it is outside the kappas above. The public rules hold 24 door entries (one for
each door-only rule, 12 for the 10 rules delivered both ways); the two coders gave the same
class to 23 and the same enforceability to all 24 (`rules.door_entries.coders_agree.class` and
`.enforceability`).

From members to the rule's label: `data/rule_members.csv` lists every member of every public rule
(the text units under their `U` ids and the door entries as `<rule>.door<n>`), in the order the
rule's cluster lists them, with both coders' labels and the final label of each. A rule's class
and its enforceability are each the most frequent final label among its members; a tie goes to
the earliest member. Six rules are decided by that tie for their class (K024, K027, K029, K063,
K090, K099) and six for their enforceability (K017, K026, K089, K090, K099, K110).
`analysis/round2_supplement.py` recomputes every rule's labels from this file and finds the
published labels for 134 of 134 rules (`rules.labels.recomputed_agree.class` and
`.enforceability`). Eleven rules have a member that both coders labelled alike with an
enforceability other than the rule's (`rules.labels.agreed_unit_unlike_rule`): the rule takes the
mode of all its members, not of its agreed ones.

Units the two coders did not both call a rule: three, each made a rule by the resolver (U097 of
K057, coder 1 yes and coder 2 no; U124 of K036, yes and no; U143 of K125, no and yes;
`rules.coding.units_not_both_rule`). K036 and K125 have no other text unit, so their labels rest
on one coder and the resolver; with the 12 door-only rules they are the 14 rules outside the class
and enforceability kappas (`rules.coding.rules_outside_the_kappa`). Units of one rule are not
independent: `rules.kappa_class.rule_cluster` and `rules.kappa_enforceability.rule_cluster` give
the same kappas with an interval that resamples whole rules.

Descriptions: on 2026-10-13, after review, every row was checked against the domain sentence at
the top of `README.md`, and the 26 descriptions that named an activity beyond it were rewritten in
generic terms (K035, K036, K037, K042, K048, K050, K051,
K076 to K083, K113, K122, K125, K126, K128, K130, K133, K137 to K140). Only the `description`
column changed; no analysis reads it, and every number is unchanged.
