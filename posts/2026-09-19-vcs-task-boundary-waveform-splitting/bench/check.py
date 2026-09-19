#!/usr/bin/env python3
"""Check this small benchmark's scalar/vector VCDs; not a general VCD parser."""
import csv
import re
import sys
from pathlib import Path

SIGNALS = ("clk", "counter", "phase_id", "held_value")

def read_vcd(path):
    text = path.read_text()
    assert re.search(r"\$timescale\s+1\s*ps\s+\$end", text), path
    ids, values, states = {}, {}, {}
    now = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("$var "):
            fields = line.split()
            if fields[4] in SIGNALS:
                ids[fields[3]] = fields[4]
        elif line == "$dumpvars" and now is None:
            now = 0
        elif line.startswith("#"):
            if now is not None:
                states[now] = values.copy()
            now = int(line[1:])
        elif line and line[0] in "bB":
            value, key = line[1:].split()
            if key in ids:
                values[ids[key]] = int(value, 2)
        elif line and line[0] in "01xXzZ" and line[1:] in ids:
            values[ids[line[1:]]] = int(line[0], 2)
    if now is not None:
        states[now] = values.copy()
    assert set(ids.values()) == set(SIGNALS), path
    return states

def at(states, tick):
    return states[max(t for t in states if t <= tick)]

def main(root):
    rows = []
    configs = {"case1": (3, 7, 4), "case2": (6, 2, 9)}
    for case, (a, b, c) in configs.items():
        directory = root / case
        ref = read_vcd(directory / "reference.vcd")
        starts = [0, 20000, 20000 + a*10000, 20000 + (a+b)*10000]
        ends = starts[1:] + [20000 + (a+b+c)*10000]
        manifest = list(csv.DictReader((directory / "boundaries.csv").open()))
        assert [int(row["start_ps"]) for row in manifest] == starts
        assert [int(row["counter_at_switch"]) for row in manifest] == [s//10000 for s in starts]
        for i, row in enumerate(manifest):
            wave = directory / row["filename"]
            states = read_vcd(wave.with_suffix(".vcd"))
            start, end = starts[i], ends[i]
            summary = wave.with_suffix(".summary.txt").read_text()
            assert re.search(r"file status\s*:\s*finished", summary), wave
            assert int(re.search(r"min xtag\s*:\s*\(0 (\d+)\)", summary)[1]) == start
            assert int(re.search(r"max xtag\s*:\s*\(0 (\d+)\)", summary)[1]) == end
            assert min(states) == start, wave
            assert states[start]["held_value"] == 0xcafe1234, wave
            assert states[start]["counter"] == start//10000, wave
            assert states[start]["phase_id"] == i, wave
            # Compare settled values at every timestamp in the union, in [start,end).
            # A boundary timestamp may also appear in the preceding file.
            ticks = sorted(t for t in set(ref) | set(states) if start <= t < end)
            for tick in ticks:
                assert at(states, tick) == at(ref, tick), (wave.name, tick, at(states, tick), at(ref, tick))
            # Final counter value must also be retained at the end of each file.
            assert at(states, end)["counter"] == end//10000, wave
            rows.append(dict(case=case, file=wave.name, start_ps=start, end_ps=end,
                             size_bytes=wave.stat().st_size, checked_timestamps=len(ticks),
                             signals=len(SIGNALS), initial_snapshot="PASS", reference_match="PASS"))
    with (root / "results.csv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("WAVE_CHECK_PASS files={} timestamps={} signals_per_timestamp={}".format(
        len(rows), sum(row["checked_timestamps"] for row in rows), len(SIGNALS)))

if __name__ == "__main__":
    main(Path(sys.argv[1]))
