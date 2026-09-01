---
source_url: "https://github.com/simonlin000/x-scan"
source_type: "github_repository"
problem_solved: "为 X 内容采集提供隔离 profile、稳定 ID 去重和结构化输出模式。"
use_case: "强化 x_collect.py、来源 allowlist 与 Raw/摘要分离时。"
key_insight: "以 Tweet ID 作幂等键；完整 Raw 存档与周报近重复压缩应分开。"
evidence_level: "primary_source"
updated_date: "2026-08-26"
related_links: "[[Sources]] [[Weekly-Reports]]"
---

## 阅读记录
仅借鉴公开仓库的采集与去重设计；不复制 Cookie、主浏览器 profile 或账户凭据，社媒证据默认低置信度。