"""numbers.py end to end, in a subprocess (it must own its interpreter's module path)."""
import json
import subprocess
import sys
from pathlib import Path

from fixtures import build, build_e1

NUMBERS = Path(__file__).resolve().parents[1] / "numbers.py"


def run(*args):
    return subprocess.run([sys.executable, str(NUMBERS)] + [str(a) for a in args],
                          capture_output=True, text=True)


def test_twice_gives_byte_identical_outputs(tmp_path):
    data, e1 = build(tmp_path / "data"), build_e1(tmp_path / "e1")
    out = tmp_path / "out"
    p = run("--data", data, "--e1", e1, "--out", out)
    assert p.returncode == 0, p.stderr
    first = {f.relative_to(out): f.read_bytes() for f in sorted(out.rglob("*")) if f.is_file()}
    p = run("--data", data, "--e1", e1, "--out", out)
    assert p.returncode == 0, p.stderr
    second = {f.relative_to(out): f.read_bytes() for f in sorted(out.rglob("*")) if f.is_file()}
    assert first == second
    names = {str(k) for k in first}
    assert {"numbers.json", "hypotheses.json", "manifest.json",
            "figures/figure4_e1.svg", "figures/figure2_weekly.svg"} <= names
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["skipped"] == {}


def test_every_entry_has_text_and_source(tmp_path):
    data, e1 = build(tmp_path / "data"), build_e1(tmp_path / "e1")
    out = tmp_path / "out"
    assert run("--data", data, "--e1", e1, "--out", out).returncode == 0
    numbers = json.loads((out / "numbers.json").read_text())
    for key, e in numbers.items():
        assert isinstance(e.get("text"), str) and e["text"], key
        assert e.get("source"), key
        if "interval" in e:
            assert len(e["interval"]) == 2, key


def test_missing_field_inputs_are_skipped_not_fatal(tmp_path):
    e1 = build_e1(tmp_path / "e1")
    out = tmp_path / "out"
    (tmp_path / "empty").mkdir()
    p = run("--data", tmp_path / "empty", "--e1", e1, "--out", out)
    assert p.returncode == 0, p.stderr
    assert "skip table 5: data/transcripts_weekly.csv not found" in p.stderr
    numbers = json.loads((out / "numbers.json").read_text())
    assert numbers and all(k.startswith("e1.") for k in numbers)
    manifest = json.loads((out / "manifest.json").read_text())
    assert "table 12 and figure 4" in manifest["ran"]
    assert "table 3" in manifest["skipped"]
