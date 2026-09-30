"""Process one batch file of data/ and write its summary to out/.

Each batch goes through the slow validation step (about 30 seconds per batch, it cannot be
sped up). Usage: python3 process.py data/batch_01.csv
"""
import csv
import json
import os
import sys
import time

VALIDATION_SECONDS = 30


def main(path):
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    time.sleep(VALIDATION_SECONDS)
    total = sum(int(r["amount"]) for r in rows)
    name = os.path.splitext(os.path.basename(path))[0]
    os.makedirs("out", exist_ok=True)
    with open(os.path.join("out", name + ".json"), "w") as fh:
        json.dump({"batch": name, "rows": len(rows), "total": total}, fh)
    print("{}: rows={} total={}".format(name, len(rows), total))


if __name__ == "__main__":
    main(sys.argv[1])
