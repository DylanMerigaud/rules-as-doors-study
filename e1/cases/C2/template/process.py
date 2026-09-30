"""Process one batch file of data/ and write its summary to out/.

The validation service behind this script accepts at most 3 batches per rolling 120 seconds
for this account. A call over the limit is refused with the number of seconds to wait; nothing
is lost, the same batch can be run again once the window allows it.

Usage: python3 process.py data/batch_01.csv
"""
import csv
import json
import os
import sys
import time

WINDOW_SECONDS = 120
MAX_PER_WINDOW = 3
STATE = ".validation-window.json"


def admitted(now):
    try:
        with open(STATE) as fh:
            stamps = [t for t in json.load(fh) if now - t < WINDOW_SECONDS]
    except (OSError, ValueError):
        stamps = []
    if len(stamps) >= MAX_PER_WINDOW:
        return False, int(WINDOW_SECONDS - (now - min(stamps))) + 1
    stamps.append(now)
    with open(STATE, "w") as fh:
        json.dump(stamps, fh)
    return True, 0


def main(path):
    ok, wait = admitted(time.time())
    if not ok:
        print("rate limited: 3 batches per 120 s already used, retry in {} s".format(wait))
        sys.exit(75)
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    time.sleep(5)
    total = sum(int(r["amount"]) for r in rows)
    name = os.path.splitext(os.path.basename(path))[0]
    os.makedirs("out", exist_ok=True)
    with open(os.path.join("out", name + ".json"), "w") as fh:
        json.dump({"batch": name, "rows": len(rows), "total": total}, fh)
    print("{}: rows={} total={}".format(name, len(rows), total))


if __name__ == "__main__":
    main(sys.argv[1])
