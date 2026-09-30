"""Shared plumbing of the analysis scripts: paths, the numbers registry, formatting, windows.

Every script under analysis/ exposes `run(ctx)`; `numbers.py` runs them all in a fixed order and
writes results/numbers.json. A script whose input file is absent raises `Missing`, and numbers.py
skips it with a message instead of failing (the field tables are published after the freeze).
"""
import csv
import json
import math
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ANALYSIS.md section 2: weeks start on Monday, windows of three ISO weeks each.
BEFORE_WEEKS = ("2026-08-31", "2026-09-07", "2026-09-14")
AFTER_WEEKS = ("2026-09-21", "2026-09-28", "2026-10-05")
LAST_WEEK = AFTER_WEEKS[-1]
TWO_CHANGES_WEEK = "2026-09-21"
MAIN_KINDS = ("operator session", "popped terminal")
KIND_SLUG = {
    "operator session": "operator",
    "popped terminal": "popped",
    "scheduler worker": "worker",
    "subagent": "subagent",
}


class Missing(Exception):
    """An input file of a script is absent: the script is skipped, not failed."""


def window_of(week):
    if week in BEFORE_WEEKS:
        return "before"
    if week in AFTER_WEEKS:
        return "after"
    return None


def in_series(week):
    """A dated week that the series may show: from the first partial week to the last after week."""
    return len(week) == 10 and week[4] == "-" and week <= LAST_WEEK


def monday(d):
    d = date.fromisoformat(d)
    return (d - timedelta(days=d.weekday())).isoformat()


class Context:
    def __init__(self, data_dir=None, e1_dir=None, out_dir=None):
        self.data = Path(data_dir) if data_dir else ROOT / "data"
        self.e1 = Path(e1_dir) if e1_dir else ROOT / "e1"
        self.out = Path(out_dir) if out_dir else ROOT / "results"
        self.registry = Registry()
        self.notes = []

    def data_path(self, name):
        p = self.data / name
        if not p.exists():
            raise Missing("data/%s not found" % name)
        return p

    def read_csv(self, name, required=()):
        p = self.data_path(name)
        with open(p, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fields = reader.fieldnames or []
        lacking = [c for c in required if c not in fields]
        if lacking:
            raise Missing("data/%s lacks column(s) %s" % (name, ", ".join(lacking)))
        return rows

    def has_data(self, name):
        return (self.data / name).exists()

    def note(self, text):
        self.notes.append(text)

    def write_table(self, name, header, rows):
        p = self.out / "tables" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(header)
            for r in rows:
                w.writerow([_cell(x) for x in r])
        return p

    def figure_path(self, name):
        p = self.out / "figures" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


def _cell(x):
    if x is None:
        return ""
    if isinstance(x, bool):
        return "1" if x else "0"
    if isinstance(x, float):
        return "%.6g" % x if not math.isnan(x) else ""
    return x


def num(x, default=0):
    """Parse a CSV cell as a number; an empty cell gives `default`."""
    if x is None or x == "":
        return default
    v = float(x)
    return int(v) if v.is_integer() else v


def r6(x):
    if x is None:
        return None
    if isinstance(x, bool) or isinstance(x, int):
        return x
    return round(float(x), 6)


class Registry:
    """The numbers registry: key -> {value, text, source, k, n, ci, ...}."""

    def __init__(self):
        self.entries = {}

    def add(self, key, value, text, source, k=None, n=None, ci=None, **extra):
        if key in self.entries:
            raise ValueError("duplicate key %s" % key)
        e = {"value": _clean(value), "text": text, "source": source}
        if k is not None:
            e["k"] = _clean(k)
        if n is not None:
            e["n"] = _clean(n)
        if ci is not None:
            e["interval"] = [r6(ci[0]), r6(ci[1])]
        for name, v in extra.items():
            e[name] = _clean(v)
        self.entries[key] = e
        return e

    def dump(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(self.entries, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
        path.write_text(text, encoding="utf-8")
        return path


def _clean(v):
    if isinstance(v, float):
        return r6(v)
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    return v


# Formatting. Proportions as "k of n (p%, 95% CI lo% to hi%)"; the text is what the manuscript
# prints, `text_short` the point value alone.

def pct(x, digits=1):
    return "%.*f%%" % (digits, 100 * x)


def fmt_prop(k, n, ci, digits=1):
    if not n:
        return "0 of 0"
    return "%s of %s (%s, 95%% CI %s to %s)" % (
        _int(k), _int(n), pct(k / n, digits), pct(ci[0], digits), pct(ci[1], digits))


def fmt_num(x, digits=2):
    return "%.*f" % (digits, x)


def fmt_signed(x, digits=2):
    s = "%.*f" % (digits, x)
    if s.startswith("-") and float(s) == 0:
        s = s[1:]
    return s


def fmt_diff(d, ci, digits=2):
    return "%s (95%% CI %s to %s)" % (fmt_signed(d, digits), fmt_signed(ci[0], digits),
                                      fmt_signed(ci[1], digits))


def fmt_points(d, ci, digits=1):
    return "%s points (95%% CI %s to %s)" % (fmt_signed(100 * d, digits),
                                             fmt_signed(100 * ci[0], digits),
                                             fmt_signed(100 * ci[1], digits))


def fmt_int(x):
    return "{:,}".format(int(x))


def _int(x):
    return fmt_int(x) if float(x).is_integer() else str(x)


def add_prop(reg, key, k, n, source, digits=1, **extra):
    """Register a proportion with its Wilson interval. Returns the entry, or None when n is 0."""
    from stats import wilson

    if not n:
        reg.add(key, None, "no data (0 of 0)", source, k=k, n=n, **extra)
        return None
    ci = wilson(k, n)
    return reg.add(key, k / n, fmt_prop(k, n, ci, digits), source, k=k, n=n, ci=ci,
                   ci_method="Wilson 95%", text_short=pct(k / n, digits), **extra)


def add_count(reg, key, value, source, **extra):
    return reg.add(key, value, fmt_int(value), source, **extra)


def svg_setup():
    """matplotlib configured for byte-identical SVG output."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["svg.hashsalt"] = "rules-as-doors-study"
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["font.family"] = "DejaVu Sans"
    return plt


def save_svg(plt, fig, path):
    """Save without the RDF metadata block matplotlib writes (it carries only namespace URLs)."""
    import io
    import re

    buf = io.StringIO()
    fig.savefig(buf, format="svg", metadata={"Date": None, "Creator": None}, bbox_inches="tight")
    plt.close(fig)
    text = re.sub(r"\s*<metadata>.*?</metadata>", "", buf.getvalue(), flags=re.DOTALL)
    Path(path).write_text(text, encoding="utf-8")


def standalone(run):
    """Entry point for running one script alone: `python3 analysis/<script>.py`."""
    import sys

    ctx = Context()
    try:
        run(ctx)
    except Missing as e:
        print("skipped: %s" % e, file=sys.stderr)
        return 0
    json.dump(ctx.registry.entries, sys.stdout, indent=1, sort_keys=True, ensure_ascii=False)
    print()
    return 0

