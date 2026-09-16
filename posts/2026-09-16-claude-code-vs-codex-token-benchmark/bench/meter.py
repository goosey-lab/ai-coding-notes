#!/usr/bin/env python3
"""Metering reverse proxy for the Claude Code vs Codex benchmark.

One listening port per tool (claude: 4101, codex: 4102). Requests are forwarded
to the upstream OpenAI-compatible gateway (METER_UPSTREAM, e.g.
http://gateway.example:3000) unchanged, except that the reasoning effort can be
pinned (METER_EFFORT) and streamed chat completions are asked to include usage.
One JSON line per request goes to METER_LOG: model, effort, sizes and token
usage -- never headers or message content. Requires aiohttp.
"""
import asyncio
import json
import os
import time

from aiohttp import ClientSession, ClientTimeout, web

UPSTREAM = os.environ["METER_UPSTREAM"].rstrip("/")
LOG_PATH = os.environ.get("METER_LOG", os.path.join(os.path.dirname(os.path.abspath(__file__)), "meter.jsonl"))
EFFORT = os.environ.get("METER_EFFORT") or None
PORTS = {"claude": 4101, "codex": 4102}
DROP_REQUEST = {"host", "content-length", "accept-encoding", "connection", "transfer-encoding"}
DROP_RESPONSE = {"content-length", "content-encoding", "connection", "transfer-encoding"}


def normalize_usage(obj):
    usage = obj.get("usage") if isinstance(obj, dict) else None
    if not isinstance(usage, dict):
        return None
    if "prompt_tokens" in usage:
        return {"input": usage.get("prompt_tokens") or 0,
                "cached": (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0,
                "output": usage.get("completion_tokens") or 0,
                "reasoning": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0}
    if "input_tokens" in usage:
        return {"input": usage.get("input_tokens") or 0,
                "cached": (usage.get("input_tokens_details") or {}).get("cached_tokens") or 0,
                "output": usage.get("output_tokens") or 0,
                "reasoning": (usage.get("output_tokens_details") or {}).get("reasoning_tokens") or 0}
    return None


def rewrite(path, payload, rec):
    rec["model"] = payload.get("model")
    rec["stream"] = bool(payload.get("stream"))
    rec["tools"] = len(payload.get("tools") or [])
    if path.endswith("/responses"):
        reasoning = payload.get("reasoning") if isinstance(payload.get("reasoning"), dict) else {}
        rec["effort_in"] = reasoning.get("effort")
        if EFFORT:
            payload["reasoning"] = {**reasoning, "effort": EFFORT}
        items = payload.get("input")
        rec["items"] = len(items) if isinstance(items, list) else 1
    elif path.endswith("/chat/completions"):
        rec["effort_in"] = payload.get("reasoning_effort")
        if EFFORT:
            payload["reasoning_effort"] = EFFORT
        if payload.get("stream"):
            payload["stream_options"] = {**(payload.get("stream_options") or {}), "include_usage": True}
        rec["items"] = len(payload.get("messages") or [])
    rec["effort_sent"] = EFFORT or rec.get("effort_in")


def make_handler(tool):
    async def handle(request):
        started = time.time()
        body = await request.read()
        rec = {"ts": round(started, 3), "tool": tool, "method": request.method,
               "path": request.path, "req_bytes": len(body)}
        if request.method == "POST" and body and "Content-Encoding" not in request.headers:
            try:
                payload = json.loads(body)
            except ValueError:
                payload = None
            if isinstance(payload, dict):
                rewrite(request.path, payload, rec)
                body = json.dumps(payload).encode()
        headers = {k: v for k, v in request.headers.items() if k.lower() not in DROP_REQUEST}
        response, usage, status = None, None, 502
        try:
            async with request.app["session"].request(
                    request.method, UPSTREAM + request.path_qs, headers=headers, data=body or None) as upstream:
                status = upstream.status
                response = web.StreamResponse(status=status, headers={
                    k: v for k, v in upstream.headers.items() if k.lower() not in DROP_RESPONSE})
                await response.prepare(request)
                is_sse = "text/event-stream" in upstream.headers.get("Content-Type", "")
                pending, whole = b"", bytearray()
                async for chunk in upstream.content.iter_any():
                    await response.write(chunk)
                    if not is_sse:
                        whole += chunk
                        continue
                    pending += chunk
                    *lines, pending = pending.split(b"\n")
                    for line in lines:
                        line = line.strip()
                        if not line.startswith(b"data:"):
                            continue
                        try:
                            event = json.loads(line[5:])
                        except ValueError:
                            continue
                        if isinstance(event, dict):
                            usage = normalize_usage(event) or normalize_usage(event.get("response")) or usage
                await response.write_eof()
            if whole:
                try:
                    usage = normalize_usage(json.loads(whole))
                except ValueError:
                    pass
        except Exception as exc:
            rec["error"] = f"{type(exc).__name__}: {exc}"[:200]
        rec.update(status=status, secs=round(time.time() - started, 2), usage=usage)
        with open(LOG_PATH, "a") as log:
            log.write(json.dumps(rec) + "\n")
        return response if response is not None else web.Response(status=502, text="meter: upstream error")
    return handle


async def main():
    session = ClientSession(timeout=ClientTimeout(total=None, sock_connect=15, sock_read=900))
    for tool, port in PORTS.items():
        app = web.Application(client_max_size=256 * 1024 * 1024)
        app["session"] = session
        app.router.add_route("*", "/{tail:.*}", make_handler(tool))
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        await web.TCPSite(runner, "127.0.0.1", port).start()
    print(f"meter up: ports={PORTS} upstream={UPSTREAM} effort={EFFORT}", flush=True)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
