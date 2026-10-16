<!-- Published in review round 4 (R2-R2-10). The codebook the two rule inventory coders read,
as they read it, with two edits for publication: field 4 (scope) is replaced by a summary,
because its criteria list private paths, the harness's job channel names and the third-party
platforms the business uses (README.md in this folder); the operator's first name is replaced by
"the operator"; for the package's publication check, which reads some common words as outbound activity
or as a third party's name, one word for an entry of a conversation is written "text" and one
adjective of the cap class is in brackets. Nothing else is changed. -->

You are one of two independent coders labelling the prose rules of a software agent harness for a research study. Work alone, from the material below only. Some units are in French; code them the same way.

The harness is a coding agent (Claude Code) that runs one engineer's software business on his laptop for months: an operator session, scheduled headless workers, subagents. The units come from its instruction files, skills, memory notes and an archived pre-cut copy of the instruction files. Each unit is one paragraph or list item (a memory note is one unit).

For EACH unit give five fields.

1. is_rule (1 or 0). 1 when the unit states a BEHAVIOURAL RULE: a statement of what the agent must or must not do that can be violated by one observable action (a cap, a pace, a window, a never, a gate, a sequence, a policy on asking the operator or on ending a turn, where it may write). 0 for: narrative, an incident story with no instruction, a definition, a description of how a system works, a pointer to a document, a fact or reference (an account id, a URL, a price), a procedure step of a tool manual that no one could "violate" in a meaningful sense, a preference of style no action violates, a heading-like fragment. If a unit holds several rules, code the main one. When is_rule is 0 put null in fields 2, 3 and 5 but still code field 4.

2. class, exactly one of:
   cap (a [number] or count limit: at most N, a budget, a quota),
   pace (a minimum gap or rate between actions),
   window (allowed or forbidden time of day or date range),
   never (an absolute prohibition of an action or of a string in output),
   gate (an action allowed only after a check or approval passes),
   sequence (an order of steps: do X before Y, always finish with Z),
   ask (when the agent may or may not put a question to the operator, or what an ask must carry),
   stop (when the agent may or may not end its turn or stop working; what a final text may say),
   write-path (where or how the agent may write: which file, store, tool, repository, branch, worktree, command is the only allowed path for a write),
   other (a behavioural rule none of the above fits: model choice, language of text, tool choice, reporting shape).

3. enforceability, exactly one of:
   E-full: the violating action necessarily passes one choke point the harness owns (a tool call, a file write, a command, a scheduler launch, the end of a turn) where code could see the violation itself with certainty (a forbidden character, a write outside an allowed path, a launch outside a window, a count over a cap).
   E-partial: a choke point sees only a proxy of the violation (a word class or pattern in a final text, a question mark, a phrase that announces work), so code can catch most but not all cases, or can only catch it with false positives.
   E-none: judging a violation needs understanding no code has (quality, relevance, whether something was worth doing, tone, truthfulness).

4. scope, "IN" or "OUT", and clause. [Withheld for publication. The field had four OUT clauses,
   each with a closed list: (a) the unit concerns a listed path of the operator's repositories
   that holds work toward other people or other people's data; (b) it concerns one of a listed
   set of the harness's job channels whose work reaches or reads a third party; (c) it names a
   person other than the operator, a company other than his own, or an account on a third-party
   platform, or it is about text another human reads; (d) it exists to protect an external
   account from a platform's checks. In doubt, OUT. IN otherwise: the harness talking to itself
   and to its operator (when it may ask, when it may stop, what it may write where, how it paces
   its own jobs and model usage, how it recovers, how it is scheduled, how a rule is tested, its
   code, repos, docs, costs, quotas). clause: the first letter that applies (a, b, c or d) when
   OUT, "" when IN.]

5. doors: the ids of the DOORS (list below) that enforce this rule: a door enforces a rule when its refusal text, name or description names or implements exactly this rule (the unit may also name the door's file). Usually zero or one or two ids. [] when none. Do not link a door that merely touches the same topic.

Answer with one JSON object per line and nothing else, one line per unit, in the order given, for example:
{"id": "R0001", "is_rule": 1, "class": "never", "enforceability": "E-full", "scope": "IN", "clause": "", "doors": ["D012"]}
{"id": "R0002", "is_rule": 0, "class": null, "enforceability": null, "scope": "OUT", "clause": "c", "doors": null}
