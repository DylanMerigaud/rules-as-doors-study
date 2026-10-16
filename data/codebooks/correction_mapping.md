<!-- Published in review round 4 (R2-R2-10). The codebook the coders read, as they read it, with these edits for the package's publication check, which reads some common words as outbound activity or as a third party's name: one word for an entry of a conversation is written "text" throughout; Nothing else is changed. -->

You review operator corrections for a research study of a software agent harness. Work alone, from the material below only. Some text is in French.

Setting: one engineer runs his one-person software business with a coding agent (Claude Code) on his laptop. He wrote behavioural rules (instruction files, hooks, tests). Each item below is one CORRECTION: a text in which he pushed back on the agent's last output. It was found by a phrase detector (many hits are venting or ordinary steering, not a rule violation) or logged by a tagging tool with a short tag. Some rows carry a "first_pass_join": a rule id found mechanically through a promotion of the row's tag; it can be wrong.

For EACH correction give:
1. behavioural (1 or 0): 1 when the correction says the agent did something a behavioural rule forbids, or failed to do something one requires (a cap, a pace, a window, a never, a gate, a sequence, a policy on when to ask the operator or when to end a turn, where to write, which tool or model to use). 0 for pure venting, taste or quality of content, a factual error, a new request, a change of plan, or anything no single observable action violated.
2. class: the class of the behaviour corrected, exactly one of: cap, pace, window, never, gate, sequence, ask, stop, write-path, other; or "none" when behavioural is 0.
   (ask: when the agent may put a question to the operator, or what a question must carry; stop: when the agent may end its turn or what a final text may say; write-path: where or how the agent may write; other: a behavioural rule none of the others fits, such as model choice, language, tool choice, reporting shape.)
3. rule: the id of the ONE rule in the lists below that the correction is about, i.e. the rule whose violation this is or whose gap it exposed; an IN id (K...) or an OUT id (R...). Use "NONE" when behavioural is 0 or no listed rule fits. Prefer a listed rule even when the match is partial, but never force a match: a rule must be about the same behaviour. If the first_pass_join is right, repeat it; if wrong, correct it.
4. join_verdict: "agree" (first_pass_join is right), "override" (you chose another rule or NONE), or "no_join" (the row had no first_pass_join).
5. confidence: "high", "medium" or "low".
6. reason: at most 15 words, generic, naming NO person, company, platform or file.

Answer with one JSON object per line and nothing else, one line per correction, in the order given, for example:
{"cid": "L0001", "behavioural": 1, "class": "ask", "rule": "K039", "join_verdict": "no_join", "confidence": "medium", "reason": "asked the operator something the machine could look up"}
