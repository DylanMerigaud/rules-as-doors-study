"""The published run records reproduce every recorded measure (review round 1, R3 B1)."""
import os
import sys

E1 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, E1)
import regrade  # noqa: E402


def test_runs_jsonl_regrades_to_results_jsonl():
    bad, rows = regrade.compare()
    assert len(rows) == 200
    assert bad == []
