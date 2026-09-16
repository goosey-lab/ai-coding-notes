#!/usr/bin/env python3
"""Score benchmark runs: hidden tests, diffs, metered tokens, tool activity."""
import glob
import json
import os
import shutil
import subprocess
import tempfile
from collections import Counter

BENCH = os.path.dirname(os.path.abspath(__file__))
RUNS = os.environ.get("BENCH_RUNS", "/tmp/agent-bench/runs")
RUNNER = r"""
import json, sys, unittest
loader = unittest.defaultTestLoader
suite = loader.loadTestsFromNames(sys.argv[1:]) if sys.argv[1:] else loader.discover(".", pattern="test_*.py")
ids = []
def walk(s):
    for x in s:
        walk(x) if isinstance(x, unittest.TestSuite) else ids.append(x.id())
walk(suite)
result = unittest.TestResult()
suite.run(result)
failed = sorted({getattr(t, "test_case", t).id() for t, _ in result.failures + result.errors})
print(json.dumps({"total": len(ids), "failed": failed}))
"""


def run_tests(workdir, names=()):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        proc = subprocess.run(["python3", "-c", RUNNER, *names], cwd=workdir, env=env,
                              capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return {"total": 0, "failed": ["<test run timed out>"]}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"total": 0, "failed": ["<runner crashed>"], "stderr": proc.stderr[-500:]}


def git(workdir, *args):
    return subprocess.run(["git", "-C", workdir, *args], capture_output=True, text=True).stdout


def meter_usage(tool, start, end):
    path = os.path.join(BENCH, "meter.jsonl")
    if not os.path.exists(path):
        return {}
    agg, models, efforts, paths = Counter(), Counter(), Counter(), Counter()
    for line in open(path):
        rec = json.loads(line)
        if rec.get("tool") != tool or not (start <= rec["ts"] <= end):
            continue
        paths[f'{rec.get("method")} {rec.get("path")} {rec.get("status")}'] += 1
        if not str(rec.get("path", "")).endswith(("/responses", "/chat/completions")):
            continue
        agg["requests"] += 1
        models[rec.get("model")] += 1
        efforts[str(rec.get("effort_in"))] += 1
        usage = rec.get("usage") or {}
        if not usage:
            agg["no_usage"] += 1
        for key in ("input", "cached", "output", "reasoning"):
            agg[key] += usage.get(key, 0)
        agg["req_bytes"] += rec.get("req_bytes", 0)
        agg["max_tools"] = max(agg["max_tools"], rec.get("tools", 0))
    agg["uncached"] = agg["input"] - agg["cached"]
    return {**agg, "models": dict(models), "effort_in": dict(efforts), "paths": dict(paths)}


def claude_activity(path):
    tools, final = Counter(), {}
    for line in open(path, errors="replace"):
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if obj.get("type") == "assistant":
            for block in obj.get("message", {}).get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tools[block.get("name")] += 1
        elif obj.get("type") == "result":
            final = {k: obj.get(k) for k in ("subtype", "is_error", "num_turns", "duration_ms", "usage", "result")}
            if isinstance(final.get("result"), str):
                final["result"] = final["result"][:300]
    return {"tool_calls": dict(tools), "final": final}


def codex_activity(path):
    items, usage, errors, last_message = Counter(), Counter(), [], ""
    for line in open(path, errors="replace"):
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        kind = obj.get("type")
        if kind == "item.completed":
            item = obj.get("item") or {}
            items[item.get("type")] += 1
            if item.get("type") == "agent_message":
                last_message = str(item.get("text", ""))[:300]
        elif kind == "turn.completed":
            usage.update({k: v for k, v in (obj.get("usage") or {}).items() if isinstance(v, int)})
        elif kind in ("error", "turn.failed"):
            errors.append(str(obj)[:300])
    return {"tool_calls": dict(items), "reported_usage": dict(usage), "errors": errors, "final": last_message}


def score(meta_path):
    meta = json.load(open(meta_path))
    rundir = os.path.dirname(meta_path)
    task, tool = meta["task"], meta["tool"]
    out = {**meta, "secs": round(meta["end"] - meta["start"], 1)}
    with tempfile.TemporaryDirectory() as tmp:
        copy = os.path.join(tmp, "w")
        shutil.copytree(os.path.join(rundir, "work"), copy,
                        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        subprocess.run(["git", "-C", copy, "add", "-A"], capture_output=True)
        numstat = [l.split("\t") for l in git(copy, "diff", "--cached", "--numstat", "HEAD").splitlines() if l]
        out["changed_files"] = {p: f"+{a}/-{d}" for a, d, p in numstat}
        original_tests = {os.path.basename(p) for p in
                          glob.glob(os.path.join(BENCH, "tasks", task, "repo", "test_*.py"))}
        out["visible_tests_modified"] = sorted(original_tests & set(out["changed_files"]))
        if original_tests:
            out["visible"] = run_tests(copy)
        hidden = sorted(glob.glob(os.path.join(BENCH, "hidden", task, "test_*.py")))
        if hidden:
            for h in hidden:
                shutil.copy(h, copy)
            out["hidden"] = run_tests(copy, [os.path.splitext(os.path.basename(h))[0] for h in hidden])
    kind = "claude" if tool.startswith("claude") else "codex"
    out["meter"] = meter_usage(kind, meta["start"], meta["end"])
    log = os.path.join(rundir, f"{kind}.jsonl")
    if os.path.exists(log):
        out["activity"] = claude_activity(log) if kind == "claude" else codex_activity(log)
    err = os.path.join(rundir, "stderr.txt")
    out["stderr_tail"] = open(err, errors="replace").read()[-400:] if os.path.exists(err) else ""
    return out


def fraction(t):
    return f'{t["total"] - len(t["failed"])}/{t["total"]}' if t else "-"


def main():
    results = [score(p) for p in sorted(glob.glob(os.path.join(RUNS, "*", "*", "meta.json")))]
    with open(os.path.join(BENCH, "results.json"), "w") as f:
        json.dump(results, f, indent=1)
    print(f'{"task":<13}{"tool":<12}{"hidden":>7}{"visib":>6}{"req":>5}{"input":>9}{"cached":>9}'
          f'{"uncach":>8}{"output":>8}{"reason":>8}{"secs":>6}  tool calls')
    for r in results:
        m = r.get("meter", {})
        calls = (r.get("activity") or {}).get("tool_calls") or {}
        print(f'{r["task"]:<13}{r["tool"]:<12}{fraction(r.get("hidden")):>7}{fraction(r.get("visible")):>6}'
              f'{m.get("requests", 0):>5}{m.get("input", 0):>9}{m.get("cached", 0):>9}{m.get("uncached", 0):>8}'
              f'{m.get("output", 0):>8}{m.get("reasoning", 0):>8}{r["secs"]:>6.0f}  {sum(calls.values())} {calls}')


if __name__ == "__main__":
    main()
