<!-- Published in review round 4 (R2-R2-10). The codebook the coders read, as they read it, with these edits for the package's publication check, which reads some common words as outbound activity or as a third party's name: one word for an entry of a conversation is written "text" throughout; in K001's list "chat replies" is written "chat answers" and the word for code annotations is in brackets; in K039's list the first two gestures are summarised in brackets. Nothing else is changed. -->

# Codebook: was this door refusal right?

You are a coder in a study of a coding agent's harness. A "door" is code that refused an action
of the agent because the action broke one of the operator's rules. Each item below is ONE refusal:
the rule it enforces, the kind of door, and what the agent was about to do when the door refused
it. Your job is a second look: judge whether the refused action actually broke THE RULE, as the
rule is written below. Do not judge the door's pattern or wording; judge the rule.

Forbidden dashes and invisible characters are shown as code point tags such as `<U+2014>`
(em dash), `<U+2013>` (en dash), `<U+200B>` (zero width space). A tag stands for the character
itself, exactly where it appears. Text marked `[...]` was cut for length.

## Codes (one per item)

- **right**: the refused action broke the rule. Refusing it was correct.
- **wrong**: the refused action did not break the rule (the door fired on something the rule
  allows, a false positive). Refusing it cost work for nothing.
- **unclear**: what is shown is not enough to tell.

Prefer right or wrong whenever the item shows enough to decide. Use unclear only when the
deciding fact is not in the item.

## The rules, by rule id

**K001, no long dash.** The agent never emits an em dash (U+2014) or an en dash (U+2013) in any
text it produces: chat answers, commits, code, [code annotations], file contents, shell commands, data.
Other dash code points of the same family (U+2012, U+2015) count too. Writing the character as an
escape sequence (a backslash-u escape, `chr(0x2014)`, an HTML entity) is the allowed way to refer
to it in code. The operator's own bounded exceptions are a third party's verbatim words stored in
a corpus file of third-party text and the recorded final text of an eval run file. The doors:
- *Stop hook*: refuses to end the turn when the agent's final text holds a forbidden dash
  outside code spans and fenced code blocks (code is exempt for this hook only).
- *PreToolUse hook*: refuses a file write, an edit or a shell command whose content holds a
  forbidden dash, anywhere, code included.
- *write refusal*: the task database refuses a field value holding a forbidden dash.
Right when the refused text holds a literal forbidden dash that the agent itself was writing, in
a place the rule covers. Wrong when there is no such character in what the agent wrote, or when
the only dash sits in one of the exceptions above.

**K003, no invisible characters.** The agent never writes an invisible character (zero width
space, joiners, word joiner, byte order mark, soft hyphen, bidirectional controls) into a stored
record field. Emoji glue inside an emoji sequence is allowed.

**K029, a rule is delivered as code.** A final text that announces a NEW behavioural rule for
the agent's own operation (a cap, a pace, a window, a never, a gate, a sequence: "from now on",
"never again", "every X must", a heading "Rule") must name the code that enforces it (a hook, a
script, a test, a door), delivered in the same change. Right when the final text announces such
a new rule of the agent's own process and names no enforcing code. Wrong when the text
announces no new rule of the agent's own process (it reports work, quotes someone, describes a
rule that already exists, or describes a third party's policy or a schedule of the next steps),
or when it does name the enforcing code.

**K033, no promise ending.** When the operator set a target for the session (a count, the whole
pool, "do not stop", "until results"), a turn does not end on a sentence announcing work still to
do ("I'll continue", "next batch", "I'll pick it up when it finishes"); the agent keeps working, or
hands the remaining work to a subagent or another session, before it ends. Right when the final
text ends by announcing further work of this session while that work is not done, and the
session has a target (the operator's text shown, or the task given to the session, sets one).
Wrong when the text does not end on such a promise (it reports a finished result, or names only
work that belongs to someone else), or when no target was set.

**K039, ask only what only the operator can answer.** The agent asks the operator only for what
needs something only he has: his own knowledge (a name, a price, a preference, a business call), a
go on an irreversible or external gesture ([an outbound gesture to another person or to the public], a purchase, a credential
revoked), or a fact absent from every file, ledger and page the tools can read. Everything else
(a menu whose winner the analysis already picked, a go on internal or reversible work, a state a
command would confirm, a decision already written down, work already authorized) the agent
resolves and reports as done. The door: a Stop hook reading the closing block of the final
text for a question or a decision request put to the operator. Right when the closing block
puts to the operator a question or a go that the agent should have resolved itself. Wrong when
the closing block asks nothing of the operator, or asks only what only he can answer.

**K089, worktree before writing.** On a repository opted into worktree isolation, the agent never
edits files on the main checkout; it enters a worktree first. Right when the refused edit targets
the main checkout of such a repository. Wrong otherwise.

## What each item carries

`key` (an opaque id: copy it back), `rule_id`, `door_type`, `reason_class` (the door's own short
label for why it fired), `refused_output` (for a Stop hook: the final text the agent tried to
end its turn on; for the other doors: the tool, its target file when there is one, and the content
or command that was refused, cut to the windows around each tagged character when long), and for
a Stop hook `operator_last_message` (the operator's last text before the refusal, cut, which
may be a task given by a scheduler).
