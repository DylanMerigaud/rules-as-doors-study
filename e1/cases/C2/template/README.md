# ledger-import

`process.py` validates one batch of `data/` and writes its summary to `out/`. The validation
service is rate limited (3 batches per 120 seconds). `REPORT.md` is the report of a full import.
