"""Old tab-separated export. Nothing imports it since version 1.3 (see docs/DECISIONS.md)."""


def to_tsv(rows):
    return "\n".join("\t".join([r["name"], r["city"], r["phone"]]) for r in rows) + "\n"
