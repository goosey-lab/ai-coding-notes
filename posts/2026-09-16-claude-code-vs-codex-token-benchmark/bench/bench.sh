#!/usr/bin/env bash
# Controlled comparison of Claude Code and Codex CLI on the same upstream model.
#   bench.sh start | stop | run TASK VARIANT MODEL | eval
# VARIANT: claude | claude-core | codex. See README.md for the required configuration.
set -uo pipefail
BENCH="$(cd "$(dirname "$0")" && pwd)"
RUNS="${BENCH_RUNS:-/tmp/agent-bench/runs}"
ENV_FILE="${BENCH_ENV_FILE:?set BENCH_ENV_FILE to a file exporting OPENAI_API_KEY, OPENAI_API_BASE and LITELLM_MASTER_KEY}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
CODEX_BIN="${CODEX_BIN:-codex}"
CODEX_PROVIDER="${CODEX_PROVIDER:-gateway}"   # [model_providers.<name>] in ~/.codex/config.toml
LITELLM_BIN="${LITELLM_BIN:-litellm}"
LITELLM_CONFIG="${LITELLM_CONFIG:-}"          # must use api_base: os.environ/OPENAI_API_BASE
PY="${BENCH_PYTHON:-python3}"                 # needs aiohttp for the meter
TIMEOUT="${BENCH_TIMEOUT:-1200}"
EFFORT="${BENCH_EFFORT:-medium}"
CORE_TOOLS="Bash,Read,Edit,Write,Glob,Grep"

load_env() {
  set -a; . "$ENV_FILE"; set +a
  export NO_PROXY="localhost,127.0.0.1,::1${NO_PROXY:+,$NO_PROXY}"
  export no_proxy="$NO_PROXY"
}

litellm_ready() {
  for _ in $(seq 1 60); do
    if curl -fsS -m 2 -H "Authorization: Bearer $LITELLM_MASTER_KEY" -o /dev/null \
         http://127.0.0.1:4011/health/liveliness 2>/dev/null; then
      return 0
    fi
    sleep 1
  done
  return 1
}

start() {
  mkdir -p "$BENCH/logs" "$RUNS"
  if ! ss -ltn | grep -q '127.0.0.1:4101 '; then
    ( load_env
      METER_UPSTREAM="${OPENAI_API_BASE%/v1}" METER_EFFORT="$EFFORT" METER_LOG="$BENCH/meter.jsonl" \
        nohup "$PY" "$BENCH/meter.py" >"$BENCH/logs/meter.log" 2>&1 </dev/null &
      echo $! >"$BENCH/logs/meter.pid" )
  fi
  if ! ss -ltn | grep -q '127.0.0.1:4011 '; then
    ( load_env
      # Point LiteLLM at the meter instead of the real gateway.
      export OPENAI_API_BASE="http://127.0.0.1:4101/v1" LITELLM_LOCAL_MODEL_COST_MAP=true
      nohup "$LITELLM_BIN" --config "${LITELLM_CONFIG:?set LITELLM_CONFIG}" --port 4011 \
        >"$BENCH/logs/litellm.log" 2>&1 </dev/null &
      echo $! >"$BENCH/logs/litellm.pid" )
  fi
  sleep 2
  grep -h "meter up" "$BENCH/logs/meter.log" || { echo "meter failed"; tail -20 "$BENCH/logs/meter.log"; return 1; }
  if ( load_env; litellm_ready ); then
    echo "litellm (bench instance, port 4011) up"
  else
    echo "litellm failed"; tail -20 "$BENCH/logs/litellm.log"; return 1
  fi
}

stop() {
  for name in litellm meter; do
    pid_file="$BENCH/logs/$name.pid"
    if [ -s "$pid_file" ] && kill "$(cat "$pid_file")" 2>/dev/null; then
      echo "stopped $name"
    fi
    rm -f "$pid_file"
  done
}

prepare() {  # task variant
  local dir="$RUNS/$1/$2"
  rm -rf "$dir"; mkdir -p "$dir/work"
  cp -r "$BENCH/tasks/$1/repo/." "$dir/work/"
  ( cd "$dir/work" && git init -q && git add -A &&
    git -c user.name=bench -c user.email=bench@example.com commit -q --allow-empty -m init )
}

run() {  # task variant model
  local task=$1 variant=$2 model=$3
  local dir="$RUNS/$task/$variant" prompt start end rc
  prompt="$(cat "$BENCH/tasks/$task/PROMPT.txt")"
  prepare "$task" "$variant"
  start=$(date +%s.%N)
  if [ "$variant" = claude ] || [ "$variant" = claude-core ]; then
    local extra=()
    [ "$variant" = claude-core ] && extra=(--tools "$CORE_TOOLS")
    ( load_env
      export ANTHROPIC_BASE_URL="http://127.0.0.1:4011" ANTHROPIC_AUTH_TOKEN="$LITELLM_MASTER_KEY"
      # Every request, including background ones, uses the model under test.
      export ANTHROPIC_MODEL="$model" ANTHROPIC_DEFAULT_OPUS_MODEL="$model" ANTHROPIC_DEFAULT_SONNET_MODEL="$model"
      export ANTHROPIC_DEFAULT_HAIKU_MODEL="$model" ANTHROPIC_SMALL_FAST_MODEL="$model"
      export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1 CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_AUTOUPDATER=1
      cd "$dir/work" &&
      timeout "$TIMEOUT" "$CLAUDE_BIN" -p "$prompt" --model "$model" --permission-mode bypassPermissions \
        "${extra[@]}" --output-format stream-json --verbose >"$dir/claude.jsonl" 2>"$dir/stderr.txt" </dev/null )
  else
    ( load_env
      cd "$dir/work" &&
      timeout "$TIMEOUT" "$CODEX_BIN" exec --json --ephemeral --ignore-rules --skip-git-repo-check \
        --dangerously-bypass-approvals-and-sandbox -m "$model" -c "model_reasoning_effort=$EFFORT" \
        -c "model_providers.$CODEX_PROVIDER.base_url=\"http://127.0.0.1:4102/v1\"" \
        "$prompt" >"$dir/codex.jsonl" 2>"$dir/stderr.txt" </dev/null )
  fi
  rc=$?
  end=$(date +%s.%N)
  printf '{"task":"%s","tool":"%s","model":"%s","start":%s,"end":%s,"exit":%d}\n' \
    "$task" "$variant" "$model" "$start" "$end" "$rc" >"$dir/meta.json"
  echo "$task/$variant finished: exit=$rc"
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  run) shift; run "$@" ;;
  eval) BENCH_RUNS="$RUNS" "$PY" "$BENCH/eval.py" ;;
  *) echo "usage: $0 start|stop|run TASK VARIANT MODEL|eval" >&2; exit 2 ;;
esac
