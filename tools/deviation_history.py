#!/usr/bin/env python3
"""When each sentence of prereg/DEVIATIONS.md first appeared, from the file's own git history.

Usage: deviation_history.py [--at COMMIT] [--out CSV]

Reads every committed version of prereg/DEVIATIONS.md up to COMMIT (default 779ca40, the version
review round 5 read), splits each numbered deviation of that version into sentences, and finds the
first version that holds each sentence verbatim (whitespace normalised; looked for in the entry of
the same number, then anywhere in the file). One row per sentence: the deviation, its section
heading, whether the sentence sits in the entry's "Touches" part, its first commit and that
commit's time, the time the heading dates the entry to, and whether the sentence first appeared
after it.

The time a heading dates its entries to: "2026-09-30, before the first counted run" is the start of
E1's first counted run (2026-09-30T18:31:38+02:00, the earliest `ts` of a counted run in
`e1/results.jsonl`); every other heading dates its entries to the end of its own day, Paris time.
A sentence first seen after that time was added or reworded later; a later rewording of an older
statement counts as a later sentence, so the column says when the wording appeared, not when the
fact was first known.

An annotation (from a line that starts with "Dated parts (annotation" to the end of its entry) is
skipped. Deterministic: the same commit gives the same bytes.
"""
import argparse
import csv
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = "prereg/DEVIATIONS.md"
DEFAULT_AT = "779ca40"
E1_FIRST_RUN = "2026-09-30T18:31:38+02:00"
ANNOTATION = "Dated parts (annotation"
ENTRY_RE = re.compile(r"^(\d+)\. \*\*")
SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(`\"*])")


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT)] + list(args), capture_output=True, text=True,
                          check=True).stdout


def versions(at):
    """(short sha, ISO time) of every commit touching the file up to `at`, oldest first."""
    out = git("log", "--reverse", "--format=%h %aI", at, "--", PATH)
    return [tuple(line.split(" ", 1)) for line in out.splitlines() if line.strip()]


def norm(s):
    return " ".join(s.split())


def entries(text):
    """{number: (heading, main lines, touches lines)} of one version of the file."""
    out = {}
    heading, num, main, touches, in_touches, in_note = None, None, [], [], False, False

    def close():
        if num is not None:
            out[num] = (heading, main, touches)
    for line in text.splitlines():
        if line.startswith("## "):
            close()
            heading, num, main, touches, in_touches, in_note = line[3:].strip(), None, [], [], False, False
            continue
        m = ENTRY_RE.match(line)
        if m:
            close()
            num, main, touches, in_touches, in_note = int(m.group(1)), [line], [], False, False
            continue
        if line.strip().startswith(ANNOTATION):
            in_note = True  # an annotation runs to the end of its entry
        if num is None or in_note:
            continue
        if line.strip().startswith("Touches"):
            in_touches = True
        (touches if in_touches else main).append(line)
    close()
    return out


def sentences(lines):
    """The sentences of an entry part; the entry's own number ("12. ") is not a sentence."""
    return [s for s in SENT_RE.split(re.sub(r"^\d+\.\s+", "", norm(" ".join(lines)))) if s]


def deadline(heading):
    if heading.startswith("2026-09-30, before the first counted run"):
        return E1_FIRST_RUN
    day = dt.date.fromisoformat(heading[:10])
    return (day + dt.timedelta(days=1)).isoformat() + "T00:00:00+02:00"


def after(t, limit):
    return dt.datetime.fromisoformat(t) > dt.datetime.fromisoformat(limit)


def build(at):
    vers = versions(at)
    texts = [(sha, t, git("show", "%s:%s" % (sha, PATH))) for sha, t in vers]
    parsed = [(sha, t, entries(text), norm(text)) for sha, t, text in texts]
    final = parsed[-1][2]
    rows = []
    for num in sorted(final):
        heading, main, touches = final[num]
        if not heading or not heading[:4].isdigit():
            continue
        limit = deadline(heading)
        for part, lines in (("main", main), ("touches", touches)):
            for i, s in enumerate(sentences(lines), 1):
                first = None
                for sha, t, ents, whole in parsed:
                    e = ents.get(num)
                    here = norm(" ".join(e[1] + e[2])) if e else ""
                    if s in here or s in whole:
                        first = (sha, t)
                        break
                if first is None:
                    raise SystemExit("deviation %d: a sentence of %s is in no version" % (num, at))
                words = s.split()
                lead = " ".join(words[:8]) + (" ..." if len(words) > 8 else "")
                rows.append([num, heading, part, i, len(words), lead, first[0],
                             first[1], limit, int(after(first[1], limit))])
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--at", default=DEFAULT_AT)
    ap.add_argument("--out", default=str(ROOT / "data" / "deviations_history.csv"))
    a = ap.parse_args(argv)
    rows = build(a.at)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        # Text fields quoted and a cut sentence closed by " ...": each row then ends its own
        # sentence for a reader (and for a scanner) instead of running into the next row.
        w = csv.writer(fh, lineterminator="\n", quoting=csv.QUOTE_NONNUMERIC)
        w.writerow(["deviation", "heading", "part", "sentence", "words", "first_words", "first_commit",
                    "first_commit_time", "dated_by_heading_to", "first_seen_after_heading_date"])
        w.writerows(rows)
    print("%d sentences of %d deviations written to %s" % (len(rows), len({r[0] for r in rows}), a.out),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
