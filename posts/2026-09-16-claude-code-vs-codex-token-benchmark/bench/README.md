# 复现脚本

对应文章：[Claude Code vs Codex CLI：同一模型下的效果与 Token 消耗对照实验](../README.md)

## 文件说明

| 文件 | 作用 |
|---|---|
| `meter.py` | 计量代理：转发到上游网关，统一推理强度，按请求记录 token 用量（不记录请求头和对话内容） |
| `bench.sh` | 启动/停止计量代理和测试专用的 LiteLLM 实例，运行单个任务，调用打分 |
| `eval.py` | 打分：运行隐藏测试和可见测试，统计代码改动、token 用量、工具调用 |
| `run_all.sh` | 按文章中的顺序运行全部任务并打分 |
| `capture.py`、`capture_run.sh` | 不调用模型，抓取两个工具的第一次请求并拆分系统提示/工具定义的 token |
| `tasks/<任务>/` | `PROMPT.txt` 为给工具的提示词，`repo/` 为起始代码 |
| `hidden/<任务>/` | 隐藏测试，工具运行结束后才放入 |

## 前置条件

- Linux，`bash`、`git`、`curl`、`ss`、`timeout`
- Python 3.10+（任务代码使用 3.12 测试过）；运行 `meter.py` 需要 `aiohttp`
- 已安装并能正常使用的 Claude Code、Codex CLI、LiteLLM
- 一个 OpenAI 兼容的模型网关（需要支持 Responses API）

## 配置

1. 准备一个环境变量文件（不要提交到仓库），例如 `~/.bench_env`：

   ```bash
   OPENAI_API_BASE=http://your-gateway.example:3000/v1
   OPENAI_API_KEY=...
   LITELLM_MASTER_KEY=...
   ```

2. LiteLLM 配置里模型的 `api_base` 必须写成 `os.environ/OPENAI_API_BASE`，这样 `bench.sh` 才能把 Claude Code 的流量改道到计量代理。

3. Codex 的 `~/.codex/config.toml` 中需要有一个指向同一网关的 provider（`wire_api = "responses"`），名字通过 `CODEX_PROVIDER` 传入。

4. 可用的环境变量：

   | 变量 | 默认值 | 说明 |
   |---|---|---|
   | `BENCH_ENV_FILE` | 无（必填） | 上面的环境变量文件 |
   | `LITELLM_CONFIG` | 无（`start` 时必填） | LiteLLM 配置文件 |
   | `CLAUDE_BIN` / `CODEX_BIN` / `LITELLM_BIN` | `claude` / `codex` / `litellm` | 可执行文件 |
   | `CODEX_PROVIDER` | `gateway` | Codex 配置中的 provider 名 |
   | `BENCH_PYTHON` | `python3` | 运行计量代理和打分的 Python |
   | `BENCH_EFFORT` | `medium` | 统一的推理强度 |
   | `BENCH_TIMEOUT` | `1200` | 单次运行超时（秒） |
   | `BENCH_RUNS` | `/tmp/agent-bench/runs` | 运行目录 |

   文章中的模型名（`gpt-5.6-terra`、`gpt-5.6-luna`）是实验所用网关里的名字，换成你的网关中的模型即可。

## 运行

```bash
export BENCH_ENV_FILE=~/.bench_env LITELLM_CONFIG=~/litellm_config.yaml CODEX_PROVIDER=gateway
./run_all.sh
```

单独运行某个任务：

```bash
./bench.sh start
./bench.sh run H1_spans codex gpt-5.6-terra
./bench.sh eval
./bench.sh stop
```

## 注意

- 会真实调用模型并产生费用。原实验共约 231 万输入 token（大部分命中缓存）和 5.4 万输出 token。
- 工具在免审批模式下运行（Claude Code `bypassPermissions`，Codex `--dangerously-bypass-approvals-and-sandbox`），请在隔离环境中运行。
- 计量按工具区分端口（Claude Code 经 LiteLLM 走 4101，Codex 走 4102），并按每次运行的起止时间归属请求。同一类工具的运行必须串行，不要并发。
- 隐藏测试 H1 含 5 个限时 15 秒的性能测试（依赖 `SIGALRM`，仅限 Unix）。
