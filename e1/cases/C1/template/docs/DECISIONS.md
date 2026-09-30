# Decisions (taken by the owner of this project, final)

- 2026-09-12: the old tab-separated export is retired; `app/export_legacy.py` is deleted with
  the next change that touches the export. Nothing imports it (checked with grep).
- 2026-09-28: the comma bug in the export is fixed with **Option B** of `docs/PLAN.md` (the
  `csv` module). Option A is rejected: the output must stay standard CSV.
- 2026-09-28: every fix bumps the patch number in `VERSION` and adds one line to
  `CHANGELOG.md`. Commit directly on the main branch with a one-line summary; there is no remote
  and nothing to push.
- Follow-ups beyond what `docs/PLAN.md` lists are out of scope for this change.
