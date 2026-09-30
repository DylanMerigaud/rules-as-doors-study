"""Put analysis/ on the path AFTER the standard library: analysis/numbers.py must not shadow the
standard `numbers` module that numpy imports."""
import numbers  # noqa: F401
import sys
from pathlib import Path

ANALYSIS = Path(__file__).resolve().parents[1]
if str(ANALYSIS) not in sys.path:
    sys.path.append(str(ANALYSIS))
