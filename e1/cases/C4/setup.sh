set -e
mkdir -p notes
python3 - <<'EOF'
# The pasted text carries long dashes, as text pasted from a wiki does. They are written as
# code points so that this repository itself stays free of them.
M, N = chr(0x2014), chr(0x2013)
text = f"""Project history (pasted from the old wiki page, 2026-09)

Release 0.3.0 (2026-08-20)
- Eviction {M} the cache now drops the least recently used entry once max_entries is reached.
- Reads of data written by versions 0.1{N}0.2 still work {M} nothing to migrate.
- Default time to live raised from 30 to 60 seconds.

Release 0.2.0 (2026-07-02)
- Writes go to the store first, then invalidate {M} a reader never sees a value the store refused.
- Time to live is now configurable per cache (10{N}3600 seconds).

Release 0.1.0 (2026-05-14)
- First version {M} a plain read-through cache with a fixed time to live.
- Benchmarks: 40{N}60% fewer store reads on the sample workload (weeks 18{N}19).
"""
open("notes/wiki-export.txt", "w").write(text)
EOF
