# The codebooks and coder prompts of the field coding

Published in review round 4 (R2-R2-10). Every coder below was a headless, tool-less call of
`claude-opus-5-5` (`claude -p --bare --tools ""`; the rule, correction and ask coders also with
`--no-session-persistence`), given the codebook,
then the reference lists, then a batch of items, on standard input (data/README.md, "Who produced
each label and each grader"). Two coders coded each item without seeing each other's output; for
the inventory, the refusal review and the ask audit a third call saw both codes and resolved each
disagreement. Agreement is computed on the two original codes.

| File | Step | What the prompt also carried | What is withheld, and why |
| --- | --- | --- | --- |
| `rule_inventory.md` | the rule inventory: is a rule, class, enforceability, scope, doors (`data/rules_coding.csv`, `rules.screen.*`, `rules.kappa_*`) | the list of the harness's blocking doors (id, kind, name, 200 characters of refusal text, 260 of description), then the units (1,400 characters each, with source kind and section heading) | field 4 (scope): its criteria list private paths, the harness's job channel names and the third-party platforms the business uses, so they are replaced by a summary of the same four clauses; the door list, which names out-of-scope doors |
| (same file) | the door coding (door-only rules) | the same codebook with one paragraph put before "For EACH unit give five fields": each unit is a door (its name, refusal text and description are given), code the rule it enforces; is_rule is 1 when the refusal enforces a behavioural rule on the agent, 0 when it only validates input or guards data integrity; field 5 is always [] | the door items, for the same reason |
| `correction_mapping.md` | the correction mapping: rule, class, behavioural (the per-rule rates `perrule.*`; `data/corrections_coded.csv`, `corrections.mapping.*`) | the in-scope rules (id, class, the public description as it stood when the review ran), the out-of-scope rules (id, class, heading, 110 characters of text), then the corrections (900 characters of the correction's text, 400 of the consequence the ledger recorded, the ledger tag, and for coder 1 only the first deterministic join) | the out-of-scope rule list and the correction texts |
| `refusal_review.md` | the door refusal review: right, wrong, unclear (`data/door_review.csv`) | the refusals (`refused_output` and, for a Stop hook, the operator's last input, both cut as data/README.md says) | the refusal texts |
| `ask_audit.md` | the ask audit: only-him, avoidable, not-an-ask (`data/ask_audit.csv`) | the ask candidates (the operator's last two inputs and the closing block, tails only) | the item texts |
| `correction_pattern.py` | the pinned correction detector, a regular expression, not a coder | not a prompt: the pattern and normalisation the extraction applied to the first 400 characters of each operator-likely input | its precision over all hits, which would give a count of out-of-scope corrections |

The codebooks are verbatim apart from the edits each file states in its first lines. The
operator's audit of 2026-09-21 that `ask_audit.md` names under "Where the codes come from" is the
audit `ANALYSIS.md` section 7 describes.
