"""Export the contact book to CSV."""


def to_csv(rows):
    """rows: list of dicts with keys name, city, phone. Returns the CSV text."""
    lines = ["name,city,phone"]
    for r in rows:
        lines.append(",".join([r["name"], r["city"], r["phone"]]))
    return "\n".join(lines) + "\n"
