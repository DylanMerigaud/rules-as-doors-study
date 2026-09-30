"""Every field table on synthetic inputs in the public schemas."""
import pytest

import case_facts
import figure1_timelines
import table01_rules
import table02_enforceability
import table03_per_rule
import table04_weekly
import table05_ask_door
import table06_prospective
import table07_ask_audit
import table08_scheduler
import table09_door_cost
import table10_doors_failed
import table11_replays
import table13_cost
from common import Context, Missing
from fixtures import build, write_csv


@pytest.fixture
def ctx(tmp_path):
    build(tmp_path / "data")
    return Context(data_dir=tmp_path / "data", e1_dir=tmp_path / "e1", out_dir=tmp_path / "out")


def test_rules_tables(ctx):
    table01_rules.run(ctx)
    table02_enforceability.run(ctx)
    r = ctx.registry.entries
    assert r["rules.n_in_scope"]["value"] == 4
    assert (r["rules.n_prose_only"]["k"], r["rules.n_door_only"]["k"], r["rules.n_both"]["k"]) == (2, 1, 1)
    assert r["rules.share_efull"]["k"] == 2
    assert (r["rules.prose_only.share_enone"]["k"], r["rules.prose_only.share_enone"]["n"]) == (1, 2)
    assert (r["rules.with_door.share_efull"]["k"], r["rules.with_door.share_efull"]["n"]) == (2, 2)


def test_per_rule_rates_listing_and_window(ctx):
    table03_per_rule.run(ctx)
    figure1_timelines.run(ctx)
    r = ctx.registry.entries
    # K001 prose: 2 corrections over 10 days, rated; door: 3 days, listed; the week after the
    # after window is left out.
    assert r["perrule.K001.prose.rate"]["value"] == pytest.approx(20.0)
    assert r["perrule.K001.prose.rate"]["n"] == 10
    assert r["perrule.K001.door.listed"]["n"] == 3
    assert r["perrule.K003.unknown.listed"]["k"] == 1
    assert "perrule.K002.prose.rate" not in r  # no correction mapped to K002
    assert r["perrule.n_rules"]["value"] == 2
    assert r["perrule.n_undated_corrections"]["value"] == 2
    assert (ctx.out / "figures" / "figure1_timelines.svg").exists()


def test_weekly_series(ctx):
    table04_weekly.run(ctx)
    r = ctx.registry.entries
    e = r["weekly.2026-09-14.operator.corr_per100"]
    assert (e["k"], e["n"]) == (4, 100)  # door and control operator sessions together
    assert r["weekly.2026-09-21.model"]["value"] == "model-b"
    assert "weekly.2026-10-12.operator.corr_per100" not in r
    rows = (ctx.out / "tables" / "table04_weekly.csv").read_text()
    assert "two changes" in rows


def test_ask_door_against_control(ctx):
    table05_ask_door.run(ctx)
    r = ctx.registry.entries
    assert (r["ask.door.before.answered_q"]["k"], r["ask.door.before.answered_q"]["n"]) == (36, 900)
    assert (r["ask.door.after.answered_q"]["k"], r["ask.door.after.answered_q"]["n"]) == (0, 900)
    assert r["ask.door.diff"]["value"] == pytest.approx(-0.04)
    assert r["ask.door.diff"]["interval"][1] < 0
    assert r["ask.control.before.answered_q"]["insufficient"] is False
    assert r["ask.control.after.qmark400"]["k"] == 9
    assert r["ask.criterion.control_drops"]["value"] is False


def test_prospective_predictions(ctx):
    table06_prospective.run(ctx)
    r = ctx.registry.entries
    assert r["prosp.door.verdict"]["value"] == "met"          # 2 of 400
    assert r["prosp.control.verdict"]["value"] == "insufficient"  # 60 turn ends
    assert (r["prosp.promise.continued"]["k"], r["prosp.promise.continued"]["n"]) == (9, 10)
    assert r["prosp.promise.verdict"]["value"] == "met"
    assert r["prosp.criterion.door_drifts_back"]["value"] is False


def test_prospective_failures(tmp_path):
    data = tmp_path / "data"
    write_csv(data / "transcripts_prospective.csv",
              ["part", "session_kind", "repo_group", "turn_ends", "ends_q_trailing_replied",
               "ref_stop_promise", "ref_stop_promise_continued"],
              [["prospective", "operator session", "door", 100, 3, 10, 5],
               ["prospective", "operator session", "control", 200, 1, 0, 0]])
    ctx = Context(data_dir=data, out_dir=tmp_path / "out")
    table06_prospective.run(ctx)
    r = ctx.registry.entries
    assert r["prosp.door.verdict"]["value"] == "failed"
    assert r["prosp.criterion.door_drifts_back"]["value"] is True
    assert r["prosp.control.verdict"]["value"] == "failed"
    assert r["prosp.promise.verdict"]["value"] == "failed"


def test_ask_audit(ctx):
    table07_ask_audit.run(ctx)
    r = ctx.registry.entries
    assert (r["audit.before.avoidable"]["k"], r["audit.before.avoidable"]["n"]) == (1, 3)
    assert r["audit.before.n_not_an_ask"]["value"] == 1
    assert r["audit.kappa"]["label"] == "model-coded"
    assert -1 <= r["audit.kappa"]["value"] <= 1


def test_ask_audit_refuses_unknown_codes(tmp_path):
    data = tmp_path / "data"
    write_csv(data / "ask_audit.csv", ["window", "week", "coder1", "coder2", "final"],
              [["before", "2026-09-14", "maybe", "avoidable", "avoidable"]])
    with pytest.raises(ValueError):
        table07_ask_audit.run(Context(data_dir=data, out_dir=tmp_path / "out"))


def test_scheduler(ctx):
    table08_scheduler.run(ctx)
    r = ctx.registry.entries
    assert r["sched.launches"]["value"] == 30
    assert r["sched.refusals.cap"]["value"] == 6 and r["sched.refusals.cap"]["rows"] == 30
    assert (r["sched.held_done_in_period.cap"]["k"], r["sched.held_done_in_period.cap"]["n"]) == (4, 4)
    assert (r["sched.on_time_share"]["k"], r["sched.on_time_share"]["n"]) == (60, 70)
    assert r["sched.days_no_log.all_open_rows.before"]["value"] == 5
    assert (ctx.out / "figures" / "figure3_scheduler.svg").exists()


def test_door_cost_and_failed_doors(ctx):
    table09_door_cost.run(ctx)
    table10_doors_failed.run(ctx)
    r = ctx.registry.entries
    assert r["door.K001.refusals"]["value"] == 10
    assert (r["door.K001.took_effect"]["k"], r["door.K001.took_effect"]["n"]) == (8, 9)
    assert r["door.K001.recovery_turns"]["value"] == pytest.approx(16 / 9)
    assert (r["door.K001.wrong_share"]["k"], r["door.K001.wrong_share"]["n"]) == (1, 2)
    assert r["door.K001.loc"]["value"] == 100 and r["door.K004.n_tests"]["value"] == 6
    # Four weeks of 10 and the week of 09-21 (1) come before the week of the repair.
    assert r["dashstop.blocks"]["value"] == 41
    assert (r["dashstop.followed"]["k"], r["dashstop.followed"]["n"]) == (5, 41)
    assert r["dashstop.repair_week_and_after.blocks"]["value"] == 2
    assert r["dashwrite.denials"]["value"] == 11  # 4 x 2 + 3 x 1, the week after the window out
    assert (r["doors.n_with_bypass"]["k"], r["doors.n_with_bypass"]["n"]) == (2, 3)
    assert r["doors.n_no_ledger"]["k"] == 2


def test_replays_and_cost_and_case_facts(ctx):
    table11_replays.run(ctx)
    table13_cost.run(ctx)
    case_facts.run(ctx)
    r = ctx.registry.entries
    assert [r["replays.n_%s" % x]["value"] for x in ("cases", "positive", "zero", "negative")] == [3, 1, 1, 1]
    assert r["cost.api_equiv_total"]["value"] == pytest.approx(15.0)
    assert r["cost.api_equiv_total"]["no_estimate"] == 3
    assert r["case.commits"]["value"] == 1234 and r["case.commits"]["text"] == "1,234"
    assert r["rules.kappa_class"]["interval"] == [0.85, 0.95]


def test_a_missing_input_raises_missing(tmp_path):
    ctx = Context(data_dir=tmp_path / "none", out_dir=tmp_path / "out")
    for mod in (table03_per_rule, table04_weekly, table05_ask_door, table06_prospective,
                table07_ask_audit, table08_scheduler, table09_door_cost, table10_doors_failed,
                table11_replays, table13_cost, case_facts, table01_rules):
        with pytest.raises(Missing):
            mod.run(ctx)


def test_a_missing_column_raises_missing(tmp_path):
    data = tmp_path / "data"
    write_csv(data / "replays_past.csv", ["case_id", "runs_without"], [["R1", 3]])
    with pytest.raises(Missing):
        table11_replays.run(Context(data_dir=data, out_dir=tmp_path / "out"))
