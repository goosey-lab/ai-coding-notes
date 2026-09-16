#!/usr/bin/env bash
# Captures the first request each agent would send, without calling any model
# (a local stub records the body and answers 400), then breaks it down into tokens.
# Uses the same configuration variables as bench.sh; capture.py needs aiohttp,
# and litellm + tiktoken for token counting (falls back to chars/4).
set -uo pipefail
BENCH="$(cd "$(dirname "$0")" && pwd)"
CAP="${CAPTURE_DIR:-/tmp/agent-bench/capture}"
PY="${BENCH_PYTHON:-python3}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
CODEX_BIN="${CODEX_BIN:-codex}"
CODEX_PROVIDER="${CODEX_PROVIDER:-gateway}"
MODEL="${CAPTURE_MODEL:-gpt-5.6-terra}"
PROMPT="Reply with exactly the single word OK. Do not run any tools or commands."
rm -rf "$CAP"; mkdir -p "$CAP"

capture() {  # name command...
  local name=$1; shift
  "$PY" "$BENCH/capture.py" serve "$CAP/$name" &
  local server=$!
  sleep 2
  ( cd "$(mktemp -d)" && git init -q && timeout 60 "$@" >/dev/null 2>&1 </dev/null )
  kill "$server"; wait "$server" 2>/dev/null
  ls "$CAP/$name" | tail -n +2 | while read -r f; do rm -f "$CAP/$name/$f"; done
  echo "captured $name"
}

claude_env=(env ANTHROPIC_BASE_URL=http://127.0.0.1:4199 ANTHROPIC_AUTH_TOKEN=capture-only
  ANTHROPIC_MODEL="$MODEL" ANTHROPIC_DEFAULT_HAIKU_MODEL="$MODEL" ANTHROPIC_SMALL_FAST_MODEL="$MODEL"
  CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_AUTOUPDATER=1)

capture claude_default "${claude_env[@]}" "$CLAUDE_BIN" -p "$PROMPT" --model "$MODEL" --permission-mode bypassPermissions
capture claude_core_tools "${claude_env[@]}" "$CLAUDE_BIN" -p "$PROMPT" --model "$MODEL" --permission-mode bypassPermissions \
  --tools "Bash,Read,Edit,Write,Glob,Grep"
capture codex_default env OPENAI_API_KEY="${OPENAI_API_KEY:-capture-only}" "$CODEX_BIN" exec --json --ephemeral \
  --ignore-rules --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox -m "$MODEL" \
  -c model_reasoning_effort=medium -c "model_providers.$CODEX_PROVIDER.base_url=\"http://127.0.0.1:4199/v1\"" "$PROMPT"

for name in claude_default claude_core_tools codex_default; do
  echo; echo "##### $name"
  "$PY" "$BENCH/capture.py" analyze "$CAP/$name"
done
