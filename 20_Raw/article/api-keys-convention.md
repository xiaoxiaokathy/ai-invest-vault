---
source_url: "file:///C:/Users/diansheng/.api-keys.md"
source_type: "local_spec"
problem_solved: "将 API 凭据从代码、笔记和 Git 历史中隔离。"
use_case: "LLM、embedding 或采集器需要 API 时。"
key_insight: "凭据只在运行时从用户本地配置读取；仓库只保留无密钥示例。"
evidence_level: "primary_source"
updated_date: "2026-08-26"
related_links: "[[SCHEMA]] [[Sources]]"
---

## 阅读记录
本卡不记录任何密钥内容。项目 `.env` 与用户目录 API-key 文件均不得提交或写入研究页面。