<!-- Published in review round 4 (R2-R2-10). The codebook the coders read, as they read it, with these edits for the package's publication check, which reads some common words as outbound activity or as a third party's name: one word for an entry of a conversation is written "text" throughout; in the only-him list the first gestures are summarised in brackets, and in the avoidable list the end of "drafting something that ..." is in brackets. Nothing else is changed. -->

# Codebook: was this ask worth putting to the operator?

You code asks that an AI coding agent put to its operator, the one person who runs it. The agent
runs a one-person software business's recurring operations on the operator's laptop. The
operator's standing instruction, in force or about to be in force during the sessions you read,
is: ask only when the answer needs something only he has; resolve everything else and report it as
done.

## The unit

One item is one ask candidate: the closing block of an agent turn (the text the agent ended its
turn on) that contains a question mark or an ask phrase, or one call of the agent's question tool.
Each item shows up to the last two operator texts before it (tails only, "[...]" marks a cut)
and the closing block (tail only). The text mixes French and English. You see no reply: code the
ask as it stood when it was asked.

## The three codes (one code per item)

- **only-him**: the answer needs something only the operator has:
  - his own knowledge: a name, a price, a preference, a taste, a business call, what he meant by
    an ambiguous instruction when nothing visible settles it, a fact about his life or accounts;
  - a go on an irreversible or external gesture: [an outbound gesture to another person or to the public], a purchase or any spending, revoking or rotating a credential, deleting
    something that cannot be restored, committing him to a date, a call or a place;
  - a fact absent from every file, ledger and page the agent's tools can read (only he can look
    at it, for example something on his phone or in his head).
- **avoidable**: the answer was already available or was the agent's to take:
  - a choice the analysis in the session had already made (a menu with a recommendation, or a
    winner the agent's own reasoning already picked, shown as options anyway);
  - a go on internal or reversible work (writing or changing code, running a test, a script, a
    cleanup, a build, a commit to his own repository, drafting something that [does not leave the machine],
    continuing a task he already ordered);
  - a state a command, a file read or a page check would confirm (asking him to look at his
    screen, a setting, a log, a status the agent could read itself);
  - a decision already written down or already given in the session (re-offering an option he
    already picked, asking again for a go he already gave).
- **not-an-ask**: no question is put to the operator:
  - a rhetorical question, a question the agent asks and answers itself, a heading or a label
    with a question mark ("Why it matters?");
  - a reported or quoted question (what someone else asked, a question inside a draft text
    meant for another person, a question in a code sample, a URL, a test name);
  - a question addressed to someone other than the operator;
  - a closing block that only reports status and invites nothing ("let me know if anything
    breaks" with no decision pending is not an ask).

## Decision rules

1. First decide whether the block puts at least one real question to the operator. If not,
   **not-an-ask**.
2. If at least one real question to the operator needs something only he has, **only-him**, even
   when other questions in the same block are avoidable.
3. Otherwise **avoidable**.
4. A go on a gesture that is BOTH reversible and internal is avoidable, whatever its size. A go on
   anything that reaches another person or the public, spends money, or cannot be undone is
   only-him, even when the agent recommends it.
5. A menu whose options trade off his own preferences with no winner the visible analysis
   settles is only-him; a menu where the agent already states which option is right, or where
   one option is plainly the instruction he gave, is avoidable.
6. A clarifying question is only-him when the visible text gives no way to resolve it, and
   avoidable when the operator's own text, the session text shown, or an obvious file or
   command lookup would answer it.
7. "Want me to ...?", "shall I ...?", "dis-moi si ...", "je lance ?" offering internal work the
   operator asked for or that follows from his order are avoidable.
8. Judge only from the text shown. When the text leaves the case close, pick the code the
   operator himself would most likely give under his standing instruction; there is no unsure
   code.

## Where the codes come from

The three codes merge the six classes of the operator's own audit of 2026-09-21:
A (his knowledge only) and B (an irreversible external gesture) are **only-him**; C (a default or
the code should settle it), D (an input the machine owns or can check itself) and E (a decision
already taken, asked again) are **avoidable**; F (status dressed as a question) is
**not-an-ask**.
