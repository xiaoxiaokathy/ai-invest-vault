---
source_url: "file:///D:/dxx/agentic-kg/scripts/export_graph_viz.py"
source_type: "project_implementation"
problem_solved: "将教程作者缺失的私有图谱架构材料落到当前项目可执行约束。"
use_case: "实现 S7 图 JSON、S8 Neo4j 幂等加载和图谱可视化时。"
key_insight: "图谱需按 9 类节点、主键和 domain=invest 隔离构建，并始终可由 Vault 重建。"
evidence_level: "primary_source"
updated_date: "2026-08-26"
related_links: "[[SCHEMA]] [[Theses]] [[Evidence]]"
---

## 阅读记录
已阅读教程附录与项目 STATUS 的 S7/S8 约束。原作者 `.kg/ARCHITECTURE.md` 不在仓库，因此此卡只引用当前项目中可审计的实现契约，不能虚构原文内容。