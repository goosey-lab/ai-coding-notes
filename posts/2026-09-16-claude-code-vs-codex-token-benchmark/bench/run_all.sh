#!/usr/bin/env bash
# Runs every task in the order used for the published results, then scores them.
# The original experiment ran in two rounds (T0-T3, then claude-core and H1/H2)
# with identical settings; the sequence below is the same.
set -uo pipefail
cd "$(dirname "$0")"

./bench.sh start || exit 1

./bench.sh run T0_overhead claude gpt-5.6-luna
./bench.sh run T0_overhead codex gpt-5.6-luna

for step in \
  "T1_ledger codex" "T1_ledger claude" \
  "T2_durations claude" "T2_durations codex" \
  "T3_shop codex" "T3_shop claude" \
  "T1_ledger claude-core" "T2_durations claude-core" "T3_shop claude-core" \
  "H1_spans codex" "H1_spans claude" "H1_spans claude-core" \
  "H2_calc claude-core" "H2_calc claude" "H2_calc codex"; do
  ./bench.sh run $step gpt-5.6-terra
done

./bench.sh eval | tee results.txt
./bench.sh stop
