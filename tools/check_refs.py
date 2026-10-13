#!/usr/bin/env python3
"""Check a manuscript's [n] citations against its refs.jsonl evidence file.

Usage: check_refs.py OUT REFS

OUT is the rendered manuscript. REFS is a JSON-lines file with one entry per reference, in the
same order as the manuscript's "## References" section (entry 1 describes reference [1], entry 2
describes [2], and so on); each entry is expected to carry "citation" (the IEEE-style string,
matched against the manuscript's own printed reference line), "supports" (a verbatim quote from
the source backing the claim it is cited for), "read_by", and exactly one identifier among "doi",
"arxiv", "url" or "isbn".

Checked, all without any network call:
- every "[n]" citation marker in the body has a matching numbered entry in the References
  section, and every References entry is cited at least once in the body;
- citation numbers are assigned in the order references are first cited (the manuscript may not
  cite [2] before [1] has appeared);
- refs.jsonl has exactly as many entries as the manuscript has references;
- every refs.jsonl entry has a non-empty "supports" quote, a non-empty "read_by", and at least
  one of doi, arxiv, url or isbn.

Checked with a network call, one per identifier type:
- a "doi" is looked up on Crossref (https://api.crossref.org/works/<doi>); the paper's title,
  year and first author's surname, parsed from the manuscript's own printed citation text, must
  match Crossref's record (title by token-set similarity at least 0.9, year exactly, surname
  case- and accent-insensitively);
- an "arxiv" id is looked up on arXiv's API; its title must match by the same similarity
  threshold;
- a "url" must answer with HTTP status 200.
- an "isbn" is checked for presence only: no isbn lookup API is used here.

All network access goes through urllib and through a single injectable `opener` argument on
every lookup function, so tests can substitute a fake opener and never touch the network.

A manuscript put into a name-and-year venue's form by venue_form.py (its References section
holds no "[n]" entry) is checked in that form instead: every work of refs.jsonl is printed once in
the References section (found by its DOI link, arXiv id or url), in venue_form's alphabetical
order; every citation in the body, "(Surname et al. 2025a; Other 2020)" or "Surname (2000)",
names a work of refs.jsonl, and every work is cited. The per-entry checks above run on each
printed reference with its links removed.

Exits 1 and prints every problem found (never just the first) if any check fails. Exits 0
otherwise.
"""
import argparse
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _mdutil  # noqa: E402
import venue_form  # noqa: E402

CITATION_MARKER_RE = re.compile(r"\[(\d+)\]")
REFERENCE_ENTRY_RE = re.compile(r"^\[(\d+)\]\s*(.*)$")
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
SIMILARITY_THRESHOLD = 0.9


def _default_opener(request, timeout=15):
    return urllib.request.urlopen(request, timeout=timeout)


def token_set_similarity(a, b):
    """Jaccard similarity of the two strings' lowercased alphanumeric token sets."""

    def tokens(s):
        return set(re.findall(r"[a-z0-9]+", (s or "").lower()))

    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _normalize_name(name):
    if not name:
        return ""
    decomposed = unicodedata.normalize("NFKD", name)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
    return ascii_only.strip().lower()


def parse_citation_text(text):
    """Heuristically pull a title, a year and a first-author surname out of an IEEE-style
    citation string, e.g. 'D. Merigaud, "A title," Venue, 2026.'."""
    title_m = re.search(r'"([^"]+)"', text)
    title = title_m.group(1).rstrip(",.").strip() if title_m else None
    years = re.findall(r"(?:19|20)\d\d", text)
    year = int(years[-1]) if years else None
    before_comma = text.split(",", 1)[0].strip()
    tokens = before_comma.split()
    surname = tokens[-1].rstrip(".") if tokens else None
    return {"title": title, "year": year, "surname": surname}


def body_citation_order(text):
    """Distinct citation numbers in the order they are first cited in the body (before
    References)."""
    refs = _mdutil.find_section(text, "References")
    body = text[: refs[0]] if refs is not None else text
    seen = []
    for m in CITATION_MARKER_RE.finditer(body):
        n = int(m.group(1))
        if n not in seen:
            seen.append(n)
    return seen


def references_list(text):
    """[(number, citation_text), ...] as printed in the manuscript's References section."""
    refs_body = _mdutil.section_body(text, "References")
    entries = []
    if refs_body is None:
        return entries
    for line in refs_body.splitlines():
        m = REFERENCE_ENTRY_RE.match(line.strip())
        if m:
            entries.append((int(m.group(1)), m.group(2).strip()))
    return entries


def load_refs_jsonl(path):
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError("refs.jsonl line %d is not valid JSON: %s" % (line_no, e))
    return entries


def crossref_lookup(doi, opener=None):
    opener = opener or _default_opener
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/")
    with opener(url) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    message = data.get("message", {})
    titles = message.get("title") or []
    title = titles[0] if titles else None
    year = None
    for key in ("published-print", "published-online", "published", "issued"):
        block = message.get(key)
        if block and block.get("date-parts"):
            parts = block["date-parts"][0]
            if parts and parts[0]:
                year = int(parts[0])
                break
    authors = message.get("author") or []
    surname = authors[0].get("family") if authors else None
    return {"title": title, "year": year, "surname": surname}


def arxiv_lookup(arxiv_id, opener=None):
    opener = opener or _default_opener
    url = "https://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(arxiv_id)
    with opener(url) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    entry = root.find("atom:entry", ATOM_NS)
    if entry is None:
        return {"title": None}
    title_el = entry.find("atom:title", ATOM_NS)
    title = title_el.text.strip() if title_el is not None and title_el.text else None
    if title:
        title = re.sub(r"\s+", " ", title)
    return {"title": title}


def url_status(url, opener=None):
    opener = opener or _default_opener
    request = urllib.request.Request(url, method="HEAD")
    try:
        with opener(request) as resp:
            return getattr(resp, "status", None) or resp.getcode()
    except urllib.error.HTTPError as e:
        return e.code


def check_entry(number, manuscript_citation, entry, opener=None):
    opener = opener or _default_opener
    errors = []
    if not entry.get("supports"):
        errors.append("reference %d: refs.jsonl entry has no supports quote" % number)
    if not entry.get("read_by"):
        errors.append("reference %d: refs.jsonl entry has no read_by" % number)

    identifiers = [k for k in ("doi", "arxiv", "url", "isbn") if entry.get(k)]
    if not identifiers:
        errors.append("reference %d: refs.jsonl entry has no doi, arxiv, url or isbn" % number)
        return errors

    claimed = parse_citation_text(manuscript_citation)

    if entry.get("doi"):
        try:
            found = crossref_lookup(entry["doi"], opener=opener)
        except Exception as e:
            errors.append(
                "reference %d: crossref lookup for %s failed: %s" % (number, entry["doi"], e)
            )
        else:
            if token_set_similarity(claimed["title"], found["title"]) < SIMILARITY_THRESHOLD:
                errors.append(
                    "reference %d: crossref title does not match (manuscript %r vs crossref %r)"
                    % (number, claimed["title"], found["title"])
                )
            if (
                claimed["year"] is not None
                and found["year"] is not None
                and claimed["year"] != found["year"]
            ):
                errors.append(
                    "reference %d: crossref year does not match (manuscript %s vs crossref %s)"
                    % (number, claimed["year"], found["year"])
                )
            if _normalize_name(claimed["surname"]) != _normalize_name(found["surname"]):
                errors.append(
                    "reference %d: crossref first author does not match "
                    "(manuscript %r vs crossref %r)" % (number, claimed["surname"], found["surname"])
                )
    elif entry.get("arxiv"):
        try:
            found = arxiv_lookup(entry["arxiv"], opener=opener)
        except Exception as e:
            errors.append(
                "reference %d: arxiv lookup for %s failed: %s" % (number, entry["arxiv"], e)
            )
        else:
            if token_set_similarity(claimed["title"], found["title"]) < SIMILARITY_THRESHOLD:
                errors.append(
                    "reference %d: arxiv title does not match (manuscript %r vs arxiv %r)"
                    % (number, claimed["title"], found["title"])
                )
    elif entry.get("url"):
        try:
            status = url_status(entry["url"], opener=opener)
        except Exception as e:
            errors.append("reference %d: url check for %s failed: %s" % (number, entry["url"], e))
        else:
            if status != 200:
                errors.append(
                    "reference %d: url %s answered %s, not 200" % (number, entry["url"], status)
                )
    # isbn: presence only, no lookup API used here.

    return errors


PAREN_RE = re.compile(r"\(([^()]*)\)")
CITE_ITEM_RE = re.compile(r"^([A-Z][^\d;()]*?) ((?:19|20)\d\d[a-z]?(?:, (?:19|20)\d\d[a-z]?)*)$")
YEARS_ONLY_RE = re.compile(r"^(?:19|20)\d\d[a-z]?(?:, (?:19|20)\d\d[a-z]?)*$")
URL_RE = re.compile(r"\s*https?://\S+")


def author_year_citations(body, known_authors):
    """[(author, label)] for every name-and-year citation in the body: the items of a
    parenthesis that read "Author 2025a" (several labels after one author split), and a
    parenthesis of years alone right after an author key the references know (narrative)."""
    found = []
    for m in PAREN_RE.finditer(body):
        inner = m.group(1).strip()
        if YEARS_ONLY_RE.match(inner):
            before = body[:m.start()].rstrip()
            for author in known_authors:
                if before.endswith(author):
                    found.extend((author, y) for y in inner.split(", "))
                    break
            continue
        items = [it.strip() for it in inner.split(";")]
        parsed = [CITE_ITEM_RE.match(it) for it in items]
        if not all(parsed):
            continue
        for p in parsed:
            found.extend((p.group(1), y) for y in p.group(2).split(", "))
    return found


def check_author_year(manuscript_text, refs_entries, opener=None):
    errors = []
    ks = venue_form.keys(refs_entries)
    refs = _mdutil.find_section(manuscript_text, "References")
    body = manuscript_text[: refs[0]] if refs is not None else manuscript_text
    refs_body = _mdutil.section_body(manuscript_text, "References") or ""
    printed = [ln.strip() for ln in refs_body.splitlines() if ln.strip()]

    if len(printed) != len(refs_entries):
        errors.append("refs.jsonl has %d entries but the manuscript lists %d references"
                      % (len(refs_entries), len(printed)))

    def ident(entry):
        for field in ("doi", "arxiv", "url", "isbn"):
            if entry.get(field):
                return entry[field]
        return None

    position = {}
    for k in ks:
        entry = refs_entries[k["n"] - 1]
        mark = ident(entry)
        hits = [i for i, ln in enumerate(printed) if mark and mark in ln]
        if len(hits) != 1:
            errors.append("reference %s %s: printed %d times in the References section"
                          % (k["author"], k["label"], len(hits)))
            continue
        position[k["n"]] = hits[0]
        errors.extend(check_entry(k["n"], URL_RE.sub("", printed[hits[0]]), entry,
                                  opener=opener))
    expected = [k["n"] for k in sorted(ks, key=lambda k: k["sort"])]
    actual = sorted(position, key=lambda n: position[n])
    if len(position) == len(ks) and actual != expected:
        errors.append("References section is not in alphabetical order of first author")

    known = {(k["author"], k["label"]): k["n"] for k in ks}
    cited = set()
    for author, label in author_year_citations(body, {k["author"] for k in ks}):
        n = known.get((author, label))
        if n is None:
            errors.append("citation (%s %s) has no entry in the References section"
                          % (author, label))
        else:
            cited.add(n)
    for k in ks:
        if k["n"] not in cited:
            errors.append("References entry %s %s is never cited in the text"
                          % (k["author"], k["label"]))
    return errors


def check(manuscript_text, refs_entries, opener=None):
    opener = opener or _default_opener
    errors = []
    # HTML comments are not shown in the rendered page: a citation inside one is not a citation.
    manuscript_text = _mdutil.strip_comments(manuscript_text)
    refs_body = _mdutil.section_body(manuscript_text, "References")
    if refs_body is not None and refs_body.strip() and not references_list(manuscript_text):
        return check_author_year(manuscript_text, refs_entries, opener=opener)

    cited_order = body_citation_order(manuscript_text)
    expected_order = list(range(1, len(cited_order) + 1))
    if cited_order != expected_order:
        errors.append(
            "citations are not numbered in order of first citation: found %r, expected %r"
            % (cited_order, expected_order)
        )

    listed = references_list(manuscript_text)
    listed_numbers = [n for n, _text in listed]
    if listed_numbers != list(range(1, len(listed_numbers) + 1)):
        errors.append(
            "References section entries are not numbered 1..N in order: %r" % listed_numbers
        )

    cited_set = set(cited_order)
    listed_set = set(listed_numbers)
    for n in sorted(cited_set - listed_set):
        errors.append("citation [%d] has no entry in the References section" % n)
    for n in sorted(listed_set - cited_set):
        errors.append("References entry [%d] is never cited in the text" % n)

    if len(refs_entries) != len(listed):
        errors.append(
            "refs.jsonl has %d entries but the manuscript lists %d references"
            % (len(refs_entries), len(listed))
        )

    for (number, citation_text), entry in zip(listed, refs_entries):
        errors.extend(check_entry(number, citation_text, entry, opener=opener))

    return errors


def main(argv):
    parser = argparse.ArgumentParser(prog="check_refs.py")
    parser.add_argument("manuscript")
    parser.add_argument("refs")
    args = parser.parse_args(argv[1:])

    manuscript_text = Path(args.manuscript).read_text(encoding="utf-8")
    try:
        refs_entries = load_refs_jsonl(args.refs)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    errors = check(manuscript_text, refs_entries)
    if errors:
        for e in errors:
            print(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
