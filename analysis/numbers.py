#!/usr/bin/env python3
"""Produce every number of the paper into results/numbers.json, every table under
results/tables/, every figure under results/figures/ and the E1 judgment in
results/hypotheses.json.

Usage: python3 analysis/numbers.py [--data DIR] [--e1 DIR] [--out DIR]

Each entry of numbers.json is keyed by a stable name and carries: value, text (the exact string the
manuscript prints), source (the file it comes from), and where they apply k, n, interval and the
interval's method. The output is byte-identical from run to run on the same inputs.

A script whose input file is absent is skipped with a message on stderr, and its keys are not
written (the field tables are published after the freeze of ANALYSIS.md section 2); the run still
exits 0. results/manifest.json lists what ran and what was skipped.
"""
import argparse
import json
import sys
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
# This folder holds numbers.py, which would shadow the standard library's `numbers` module that
# numpy imports: take the folder off the front of the path, load the real module, append it.
if sys.path and str(Path(sys.path[0] or ".").resolve()) == _HERE:
    sys.path.pop(0)
import numbers  # noqa: E402,F401
if _HERE not in sys.path:
    sys.path.append(_HERE)
import case_facts  # noqa: E402
import figure1_timelines  # noqa: E402
import table01_rules  # noqa: E402
import table02_enforceability  # noqa: E402
import table03_per_rule  # noqa: E402
import table04_weekly  # noqa: E402
import table05_ask_door  # noqa: E402
import table06_prospective  # noqa: E402
import table07_ask_audit  # noqa: E402
import table08_scheduler  # noqa: E402
import table09_door_cost  # noqa: E402
import table10_doors_failed  # noqa: E402
import table11_replays  # noqa: E402
import table12_e1  # noqa: E402
import table13_cost  # noqa: E402
from common import Context, Missing  # noqa: E402

SCRIPTS = (
    ("case facts", case_facts),
    ("table 1", table01_rules),
    ("table 2", table02_enforceability),
    ("table 3", table03_per_rule),
    ("figure 1", figure1_timelines),
    ("table 4 and figure 2", table04_weekly),
    ("table 5", table05_ask_door),
    ("table 6", table06_prospective),
    ("table 7", table07_ask_audit),
    ("table 8 and figure 3", table08_scheduler),
    ("table 9", table09_door_cost),
    ("table 10", table10_doors_failed),
    ("table 11", table11_replays),
    ("table 12 and figure 4", table12_e1),
    ("table 13", table13_cost),
)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data")
    ap.add_argument("--e1")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    ctx = Context(args.data, args.e1, args.out)
    manifest = {"ran": [], "skipped": {}, "notes": []}
    for name, mod in SCRIPTS:
        before = len(ctx.notes)
        try:
            mod.run(ctx)
            manifest["ran"].append(name)
        except Missing as e:
            del ctx.notes[before:]
            manifest["skipped"][name] = str(e)
            print("skip %s: %s" % (name, e), file=sys.stderr)
    for n in ctx.notes:
        print("note: %s" % n, file=sys.stderr)
    manifest["notes"] = list(ctx.notes)
    out = ctx.registry.dump(ctx.out / "numbers.json")
    (ctx.out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n",
                                          encoding="utf-8")
    print("%d keys written to %s" % (len(ctx.registry.entries), out), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
