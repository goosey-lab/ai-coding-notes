#!/usr/bin/env python3
"""Zero-cost request capture: record what each agent would send, then refuse it.

  capture.py serve DIR     listen on 127.0.0.1:4199, save each POST body to DIR, answer 400
  capture.py analyze DIR   break the captured requests down into estimated tokens
"""
import glob
import json
import os
import sys


def serve(outdir):
    from aiohttp import web

    os.makedirs(outdir, exist_ok=True)

    async def handle(request):
        body = await request.read()
        if request.method == "POST" and body:
            name = f"{len(os.listdir(outdir)):02d}{request.path.replace('/', '_')}.json"
            with open(os.path.join(outdir, name), "wb") as f:
                f.write(body)
        return web.json_response({"error": {"type": "invalid_request_error", "message": "captured"}}, status=400)

    app = web.Application(client_max_size=256 * 1024 * 1024)
    app.router.add_route("*", "/{tail:.*}", handle)
    web.run_app(app, host="127.0.0.1", port=4199, print=None, access_log=None)


def encoder():
    import litellm
    os.environ.setdefault("TIKTOKEN_CACHE_DIR",
                          os.path.join(os.path.dirname(litellm.__file__), "litellm_core_utils", "tokenizers"))
    import tiktoken
    for name in ("o200k_base", "cl100k_base"):
        try:
            enc = tiktoken.get_encoding(name)
            return name, lambda text: len(enc.encode(text, disallowed_special=()))
        except Exception:
            continue
    return "chars/4", lambda text: len(text) // 4


def analyze(outdir):
    enc_name, count = encoder()
    tok = lambda obj: count(obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False))
    print(f"tokenizer: {enc_name}")
    for path in sorted(glob.glob(os.path.join(outdir, "*.json"))):
        req = json.load(open(path))
        if "system" in req or "messages" in req:        # Anthropic Messages API (Claude Code)
            system = req.get("system", "")
            system_text = system if isinstance(system, str) else "".join(b.get("text", "") for b in system)
            prompt_part, prompt_tokens = "messages", tok(req.get("messages", []))
        else:                                           # OpenAI Responses API (Codex)
            system_text = req.get("instructions") or ""
            prompt_part, prompt_tokens = "input", tok(req.get("input", []))
        tools = req.get("tools") or []
        per_tool = sorted(((t.get("name") or t.get("type"), tok(t)) for t in tools), key=lambda x: -x[1])
        tools_total = sum(n for _, n in per_tool)
        print(f"\n== {os.path.basename(path)}  ({os.path.getsize(path)} bytes)")
        print(f"   system/instructions: {tok(system_text):>6} tokens ({len(system_text)} chars)")
        print(f"   tools: {len(tools):>2} defs    {tools_total:>6} tokens")
        print(f"   {prompt_part:<19}: {prompt_tokens:>6} tokens")
        print(f"   estimated total    : {tok(system_text) + tools_total + prompt_tokens:>6} tokens")
        other = sorted(k for k in req if k not in ("system", "instructions", "tools", "messages", "input"))
        print(f"   other fields: {other}")
        print("   largest tools: " + ", ".join(f"{n}={t}" for n, t in per_tool[:12]))


if __name__ == "__main__":
    {"serve": serve, "analyze": analyze}[sys.argv[1]](sys.argv[2])
