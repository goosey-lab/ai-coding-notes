#!/usr/bin/env bash
set -euo pipefail
bench_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
: "${VERDI_HOME:?Set VERDI_HOME and put VCS/Verdi in PATH first}"
out=$(mktemp -d "${PWD}/wave-split-run.XXXXXX")
echo "OUTPUT_DIR=$out"
cd "$out"
vcs -full64 -sverilog -debug_access+all \
  "$bench_dir/tb_wave_split.sv" -top tb_wave_split -o simv -l compile.log
for config in case1 case2; do
  mkdir "$config"
  cd "$config"
  if [[ "$config" == case1 ]]; then
    ../simv +A=3 +B=7 +C=4 -l sim.log
  else
    ../simv +A=6 +B=2 +C=9 -l sim.log
  fi
  if grep -Eq 'Error-|\*Verdi\* ERROR|Fatal' sim.log; then
    echo "Simulation log contains an error" >&2
    exit 1
  fi
  grep -q SIM_PASS sim.log
  [[ $(find . -maxdepth 1 -name '0*.fsdb' | wc -l) -eq 4 ]]
  for wave in 0*.fsdb; do
    fsdb2vcd "$wave" -o "${wave%.fsdb}.vcd" > "${wave%.fsdb}.convert.log" 2>&1
    fsdb2vcd "$wave" -summary > "${wave%.fsdb}.summary.txt" 2>&1
  done
  cd ..
done
python3 "$bench_dir/check.py" "$out"
