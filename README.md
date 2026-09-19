# AI Coding Notes

AI 编程工具的实测记录与技术总结。每篇都尽量写清环境、方法、数据和局限，方便以后回看和复现。

## 文章

| 日期 | 标题 | 标签 |
|---|---|---|
| 2026-09-19 | [VCS 波形分割实测：按任务完成节点切换 FSDB](posts/2026-09-19-vcs-task-boundary-waveform-splitting/README.md) | VCS · Verdi · FSDB · 仿真调试 |
| 2026-09-16 | [Claude Code vs Codex CLI：同一模型下的效果与 Token 消耗对照实验](posts/2026-09-16-claude-code-vs-codex-token-benchmark/README.md) | Claude Code · Codex CLI · Token 成本 · 对照实验 |

## 目录约定

```
posts/
  YYYY-MM-DD-主题/
    README.md    正文
    data/        原始数据（CSV 等）
    bench/       复现脚本（如有）
templates/
  post-template.md   新文章模板
```

新文章：复制 `templates/post-template.md` 到 `posts/YYYY-MM-DD-主题/README.md`，写完后在上面的表格里加一行。
