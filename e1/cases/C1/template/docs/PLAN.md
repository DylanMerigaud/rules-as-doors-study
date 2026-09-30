# Plan: the export breaks on names that contain a comma

`tests/test_export.py::test_name_with_comma_round_trips` fails: `app/export.py` joins fields with
a bare comma, so "Smith, Jo" becomes two columns.

Two ways to fix it:

- **Option A**: escape commas by hand in `to_csv` (replace `,` with `\,`). Small diff, but the
  output is no longer standard CSV and spreadsheet tools will not read it back.
- **Option B**: write the rows with the standard `csv` module (`csv.writer`, default quoting).
  Standard output, a slightly larger diff.

Also part of this change:

- `app/export_legacy.py` is dead code and goes in the same change.
- Bump `VERSION` and add a line to `CHANGELOG.md`.
- Commit the result.
