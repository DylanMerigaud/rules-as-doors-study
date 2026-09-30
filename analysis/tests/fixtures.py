"""Synthetic inputs for the analysis tests: invented counts in the public schemas, never data."""
import csv
import json

TW_HEADER = ["week", "session_kind", "repo_group", "model", "cli_version", "sessions", "asst_msgs",
             "human_msgs", "human_msgs_operator_likely", "corr_hits", "corr_hits_operator_likely",
             "corr_hits_fulltext", "turn_ends", "ends_q_trailing", "ends_q_last400",
             "ends_q_trailing_replied", "askuserquestion_calls", "stop_firings",
             "ref_stop_promise", "ref_stop_promise_continued", "ref_stop_ask",
             "ref_stop_ask_continued", "ref_stop_rule", "ref_stop_rule_continued",
             "dash_stop_detected", "dash_stop_continued", "ref_stop_retired",
             "ref_ptu_askuserquestion", "ref_ptu_dash_write"]


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def tw_row(week, kind, group, turn_ends, q, q400, answered, human=50, corr=2, dash=0, dash_cont=0,
           write=0, model="model-a", cli="1.0.0"):
    vals = {"week": week, "session_kind": kind, "repo_group": group, "model": model,
            "cli_version": cli, "sessions": 5, "asst_msgs": 100, "human_msgs": human,
            "human_msgs_operator_likely": human, "corr_hits": corr, "corr_hits_operator_likely": corr,
            "corr_hits_fulltext": corr, "turn_ends": turn_ends, "ends_q_trailing": q,
            "ends_q_last400": q400, "ends_q_trailing_replied": answered,
            "dash_stop_detected": dash, "dash_stop_continued": dash_cont,
            "ref_ptu_dash_write": write}
    return [vals.get(h, 0) for h in TW_HEADER]


def build(data):
    """Build every synthetic input file under `data` and give back that folder."""

    write_csv(data / "rules.csv", ["id", "description", "class", "delivery", "prose_first_seen",
                                   "door_landed", "enforceability"],
              [["K001", "x", "never", "both", "2026-09-01", "2026-09-10", "E-full"],
               ["K002", "x", "ask", "prose only", "2026-09-01", "", "E-none"],
               ["K003", "x", "gate", "prose only", "2026-09-01", "", "E-partial"],
               ["K004", "x", "stop", "door only", "", "2026-09-21", "E-full"]])

    write_csv(data / "corrections_weekly.csv", ["week", "rule_id", "state", "count", "exposure"],
              [["pre-2026-08-31", "K001", "none", 2, ""],
               ["2026-08-31", "K001", "prose", 1, 6],
               ["2026-09-07", "K001", "prose", 1, 4],
               ["2026-09-14", "K001", "door", 0, 3],
               ["2026-09-07", "K002", "prose", 0, 7],
               ["2026-09-07", "K003", "unknown", 1, 2],
               ["2026-10-12", "K001", "door", 9, 5]])

    rows = []
    for w in ("2026-08-24", "2026-08-31", "2026-09-07", "2026-09-14"):
        rows.append(tw_row(w, "operator session", "door", 300, 15, 20, 12, dash=10, dash_cont=1,
                           write=2))
        rows.append(tw_row(w, "operator session", "control", 40, 3, 3, 2))
    for w in ("2026-09-21", "2026-09-28", "2026-10-05", "2026-10-12"):
        rows.append(tw_row(w, "operator session", "door", 300, 2, 8, 0, dash=1, dash_cont=1,
                           write=1, model="model-b", cli="1.1.0"))
        rows.append(tw_row(w, "popped terminal", "control", 40, 2, 3, 1, model="model-b",
                           cli="1.1.0"))

    write_csv(data / "transcripts_weekly.csv", TW_HEADER, rows)

    write_csv(data / "transcripts_prospective.csv",
              ["part", "session_kind", "repo_group", "turn_ends", "ends_q_trailing_replied",
               "ref_stop_promise", "ref_stop_promise_continued"],
              [["retrospective", "operator session", "door", 500, 9, 10, 2],
               ["prospective", "operator session", "door", 400, 2, 8, 7],
               ["prospective", "popped terminal", "control", 60, 3, 0, 0],
               ["prospective", "scheduler worker", "door", 100, 0, 2, 2]])

    write_csv(data / "ask_audit.csv", ["window", "week", "coder1", "coder2", "final"],
              [["before", "2026-09-14", "avoidable", "avoidable", "avoidable"],
               ["before", "2026-09-14", "only-him", "avoidable", "only-him"],
               ["before", "2026-09-07", "only-him", "only-him", "only-him"],
               ["before", "2026-09-07", "not-an-ask", "not-an-ask", "not-an-ask"],
               ["after", "2026-09-21", "only-him", "only-him", "only-him"],
               ["after", "2026-09-28", "avoidable", "avoidable", "avoidable"]])

    write_csv(data / "scheduler_weekly.csv",
              ["week_start", "door_class", "jobs_created", "launches", "outcome_done",
               "outcome_closed_by_ledger", "outcome_error", "outcome_blocked",
               "outcome_to_operator", "outcome_retry", "outcome_superseded", "dry_run_rows",
               "door_rows", "door_episodes", "jobs_held", "jobs_held_done_in_period",
               "jobs_held_no_period"],
              [["2026-09-14", "all", 5, 10, 6, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
               ["2026-09-21", "all", 9, 20, 15, 1, 2, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
               ["2026-09-21", "cap", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 30, 6, 5, 4, 1],
               ["2026-09-21", "precondition", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 3, 3, 1, 0]])

    write_csv(data / "scheduler_ontime.csv",
              ["row_set", "era", "first_day", "last_day", "days", "rows", "due_row_days",
               "logged_same_day", "days_with_no_log_in_set"],
              [["all_open_rows", "pre", "2026-08-31", "2026-09-19", 20, 4, 60, 30, 5],
               ["all_open_rows", "post", "2026-09-21", "2026-10-11", 21, 4, 70, 60, 0]])

    write_csv(data / "door_refusals_weekly.csv",
              ["week", "rule_id", "door_type", "refusals", "took_effect", "did_not",
               "cannot_judge", "recovery_n", "recovery_turns", "recovery_output_tokens"],
              [["2026-09-28", "K001", "write refusal", 8, 6, 1, 1, 7, 14, 7000],
               ["2026-10-05", "K001", "write refusal", 2, 2, 0, 0, 2, 2, 1000]])

    write_csv(data / "door_review.csv", ["rule_id", "stratum", "coder1", "coder2", "final"],
              [["K001", "took_effect", "right", "right", "right"],
               ["K001", "did_not", "wrong", "right", "wrong"],
               ["K001", "did_not", "unclear", "unclear", "unclear"],
               ["K004", "took_effect", "right", "right", "right"]])

    write_csv(data / "door_size.csv", ["rule_id", "door_type", "code_lines", "test_lines",
                                       "n_tests", "has_bypass", "writes_ledger"],
              [["K001", "write refusal", 80, 40, 5, 1, 1],
               ["K001", "lifecycle hook", 20, 10, 2, 0, 0],
               ["K004", "lifecycle hook", 50, 60, 6, 1, 0]])

    write_csv(data / "replays_past.csv", ["case_id", "runs_without", "violations_without",
                                          "runs_with", "violations_with"],
              [["R1", 3, 3, 3, 1], ["R2", 3, 1, 3, 1], ["R3", 3, 0, 3, 1]])

    write_csv(data / "cost_weekly.csv",
              ["week_start", "session_kind", "sessions", "turns", "output_tokens",
               "cache_read_tokens", "load_units", "load_units_with_imputed_tier",
               "share_of_week_load", "unpriced_turns", "envelope_attempts", "envelope_usd",
               "envelope_no_estimate"],
              [["2026-09-14", "interactive", 3, 100, 1000, 0, 1.0, 1.0, 0.5, 0, "", "", ""],
               ["2026-09-21", "scheduler_worker", 3, 100, 3000, 0, 1.0, 1.0, 0.5, 0, 10, 12.5, 2],
               ["2026-09-28", "scheduler_worker", 3, 100, 1000, 0, 1.0, 1.0, 0.5, 0, 4, 2.5, 1]])

    write_csv(data / "case_facts.csv", ["key", "value", "text", "source", "k", "n", "ci_low",
                                        "ci_high"],
              [["case.commits", "1234", "1,234", "git history", "", "", "", ""],
               ["rules.kappa_class", "0.9", "0.90 (0.85 to 0.95)", "coding table", "", "10",
                "0.85", "0.95"]])

    return data


def build_e1(e1dir):
    e1dir.mkdir(parents=True, exist_ok=True)
    design = {"model": "model-a", "cases": {"C1": {"doors": {"door": []}},
                                            "C5": {"doors": {}}}}
    (e1dir / "design.json").write_text(json.dumps(design))
    runs = []
    for arm, nv in (("A0", 4), ("AP", 1), ("AD", 0), ("APD", 0)):
        for i in range(5):
            runs.append({"case": "C1", "arm": arm, "run_index": i, "counted": True, "void": None,
                         "model_requested": "model-a", "model": "model-a", "cli_version": "1",
                         "trimwrit_commit": "abc", "ts": "2026-10-01T00:00:0%dZ" % i,
                         "V": i < nv, "V_door": i < nv, "C": True, "B": 0, "B_stop": 0,
                         "B_deny": 0, "K_stop": [], "K_deny": [], "E": None, "turns": 3,
                         "output_tokens": 10, "wall_s": 1.0, "killed": False})
    (e1dir / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in runs))
    return e1dir
