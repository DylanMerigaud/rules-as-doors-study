#!/usr/bin/env python3
"""Put a rendered manuscript into a name-and-year venue's form.

Usage: venue_form.py SRC REFS OUT

SRC is a manuscript whose numbers are already substituted (the output of render.py) and whose
citations are numbered markers "[n]", in order of first citation. REFS is the JSON-lines file of
its references, entry n describing [n], each with "citation" (an IEEE-style string: authors,
"title," venue, year) and an identifier ("doi", "arxiv", "url" or "isbn"). OUT is written with:

- every citation group "[n]" or "[n], [m], ..." in the body replaced by name and year in
  parentheses, "(Schneider 2000; Wang et al. 2025)": one author by surname, two joined by "and",
  three or more (or a citation that says "et al.") by the first surname and "et al."; two works
  with the same author key and year get "a", "b" in their order in REFS; works of the same author
  key inside one group are merged, "(Chatlatanagulchai et al. 2025a, 2025b)";
- a single citation right after its own author key ("Schneider [5] showed") written in the
  narrative form, "Schneider (2000) showed";
- the "## References" section rewritten as one paragraph per work, alphabetized by the first
  author's surname (accents ignored), then year, then letter; each is the citation string (its
  year given the letter when there is one) followed by its DOI as a full link: the "doi" field, or
  for an arXiv preprint its DataCite DOI 10.48550/arXiv.<id>; a "url" entry already prints its
  link;
- decimal heading numbers: every "##" heading numbered 1, 2, ... and every "###" under a numbered
  one numbered 1.1, 1.2, ..., except the front and back matter (Abstract, Keywords, Statements and
  Declarations, Declarations, Acknowledgments, References, About the author).

HTML comments are copied unchanged. Exits 1 and writes nothing when a citation names no entry of
REFS, an entry of REFS is never cited, a heading already carries a number, or a "Section n" or
"Section n.m" reference in the body names no numbered heading. Every problem is printed.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

GROUP_RE = re.compile(r"\[\d+\](?:\s*,\s*\[\d+\])*(?!\()")
NUM_RE = re.compile(r"\d+")
YEAR_RE = re.compile(r"\b(?:19|20)\d\d\b")
INITIAL_RE = re.compile(r"^(?:[A-Z]\.)+(?:-[A-Z]\.)?$")
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
HEADING_RE = re.compile(r"^(#{2,3})\s+(.*?)\s*$")
SECTION_REF_RE = re.compile(r"\bSections? (\d+(?:\.\d+)?)(?: and (\d+(?:\.\d+)?))?")
UNNUMBERED = {"abstract", "keywords", "statements and declarations", "declarations",
              "acknowledgments", "acknowledgements", "acknowledgment", "references",
              "about the author"}


def fold(s):
    """Lowercase, accents removed: the sort and match form of a name."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").lower()


def authors_of(citation):
    """The list of author names of an IEEE-style citation, and whether it says et al."""
    head = citation.split('"', 1)[0].strip().rstrip(",").strip()
    et_al = head.endswith("et al.")
    if et_al:
        head = head[: -len("et al.")].strip().rstrip(",")
    names = []
    for part in re.split(r",\s*|\s+and\s+", head):
        part = re.sub(r"^and\s+", "", part.strip())
        if part:
            names.append(part)
    return names, et_al


def surname(name):
    """A name without its initials: "F. B. Schneider" -> "Schneider"; an organization stays whole."""
    tokens = [t for t in name.split() if not INITIAL_RE.match(t)]
    return " ".join(tokens) if tokens else name


def author_key(citation):
    names, et_al = authors_of(citation)
    sur = [surname(n) for n in names]
    if et_al or len(sur) >= 3:
        return sur[0] + " et al."
    if len(sur) == 2:
        return sur[0] + " and " + sur[1]
    return sur[0]


def year_of(citation):
    years = YEAR_RE.findall(citation)
    return years[-1] if years else "n.d."


def keys(refs):
    """[{"n", "author", "year", "label", "sort"}] for every entry, n starting at 1: label is the
    year with its letter ("2025a")."""
    out = []
    for n, entry in enumerate(refs, start=1):
        c = entry["citation"]
        names, _ = authors_of(c)
        out.append({"n": n, "author": author_key(c), "year": year_of(c), "label": year_of(c),
                    "first": fold(surname(names[0])) if names else ""})
    groups = {}
    for k in out:
        groups.setdefault((k["author"], k["year"]), []).append(k)
    for same in groups.values():
        if len(same) > 1:
            for i, k in enumerate(same):
                k["label"] = k["year"] + "abcdefghijklmnopqrstuvwxyz"[i]
    for k in out:
        k["sort"] = (k["first"], fold(k["author"]), k["label"])
    return out


def doi_link(entry):
    if entry.get("doi"):
        return "https://doi.org/" + entry["doi"]
    if entry.get("arxiv"):
        return "https://doi.org/10.48550/arXiv." + entry["arxiv"]
    return None


def printed_reference(entry, key):
    c = entry["citation"].strip()
    if key["label"] != key["year"]:
        idx = [m.start() for m in YEAR_RE.finditer(c)][-1]
        c = c[:idx] + key["label"] + c[idx + 4:]
    link = doi_link(entry)
    return c + (" " + link if link else "")


def _cite_group(numbers, ks, before, errors):
    """The replacement text of one citation group, and whether it took the narrative form."""
    items = []
    for n in numbers:
        if n < 1 or n > len(ks):
            errors.append("citation [%d] names no entry of REFS" % n)
            return None, False
        items.append(ks[n - 1])
    if len(items) == 1 and before.rstrip().endswith(items[0]["author"]):
        return "(%s)" % items[0]["label"], True
    merged = []
    for k in items:
        if merged and merged[-1][0] == k["author"]:
            merged[-1][1].append(k["label"])
        else:
            merged.append((k["author"], [k["label"]]))
    return "(" + "; ".join(a + " " + ", ".join(ls) for a, ls in merged) + ")", False


def cite_body(body, ks, errors, cited):
    out, last = [], 0
    for m in GROUP_RE.finditer(body):
        numbers = [int(x) for x in NUM_RE.findall(m.group(0))]
        before = body[:m.start()]
        text, _narrative = _cite_group(numbers, ks, before, errors)
        if text is None:
            continue
        cited.update(numbers)
        out.append(body[last:m.start()].rstrip(" ") + " ")
        out.append(text)
        last = m.end()
    out.append(body[last:])
    return "".join(out)


def number_headings(lines, errors):
    """Lines with decimal numbers put on the ## and ### headings; returns (lines, numbered),
    numbered the set of "n" and "n.m" labels given."""
    top = sub = 0
    numbered_top = False
    labels = set()
    out = []
    for line in lines:
        m = HEADING_RE.match(line)
        if not m:
            out.append(line)
            continue
        hashes, title = m.group(1), m.group(2)
        if re.match(r"^\d", title):
            errors.append("heading already numbered: %s" % line.strip())
            out.append(line)
            continue
        if hashes == "##":
            if title.lower() in UNNUMBERED:
                numbered_top = False
                out.append(line)
                continue
            top += 1
            sub = 0
            numbered_top = True
            labels.add(str(top))
            out.append("## %d %s" % (top, title))
        else:
            if not numbered_top or title.lower() in UNNUMBERED:
                out.append(line)
                continue
            sub += 1
            labels.add("%d.%d" % (top, sub))
            out.append("### %d.%d %s" % (top, sub, title))
    return out, labels


def form(text, refs):
    """Return (out_text, errors)."""
    errors = []
    ks = keys(refs)
    pieces = []
    last = 0
    for m in COMMENT_RE.finditer(text):
        pieces.append(("text", text[last:m.start()]))
        pieces.append(("comment", m.group(0)))
        last = m.end()
    pieces.append(("text", text[last:]))

    cited = set()
    in_refs = False
    rebuilt = []
    for kind, chunk in pieces:
        if kind == "comment":
            if not in_refs:
                rebuilt.append(chunk)
            continue
        if in_refs:
            continue
        m = re.search(r"^## References[ \t]*$", chunk, re.M)
        if m:
            rebuilt.append(cite_body(chunk[:m.start()], ks, errors, cited))
            order = sorted(ks, key=lambda k: k["sort"])
            entries = [printed_reference(refs[k["n"] - 1], k) for k in order]
            rebuilt.append("## References\n\n" + "\n\n".join(entries) + "\n")
            in_refs = True
        else:
            rebuilt.append(cite_body(chunk, ks, errors, cited))
    if not in_refs:
        errors.append("no ## References section")
    for k in ks:
        if k["n"] not in cited:
            errors.append("reference [%d] (%s %s) is never cited" % (k["n"], k["author"],
                                                                    k["label"]))
    out = "".join(rebuilt)
    lines, labels = number_headings(out.split("\n"), errors)
    out = "\n".join(lines)
    visible = COMMENT_RE.sub("", out)
    refs_at = visible.find("## References")
    body = visible[:refs_at] if refs_at >= 0 else visible
    for m in SECTION_REF_RE.finditer(body):
        for label in m.groups():
            if label and label not in labels:
                errors.append("Section %s is referenced but no heading carries that number"
                              % label)
    return out, errors


def main(argv):
    if len(argv) != 4:
        print("usage: venue_form.py SRC REFS OUT", file=sys.stderr)
        return 1
    text = Path(argv[1]).read_text(encoding="utf-8")
    refs = [json.loads(ln) for ln in Path(argv[2]).read_text(encoding="utf-8").splitlines()
            if ln.strip()]
    out, errors = form(text, refs)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    Path(argv[3]).write_text(out, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
