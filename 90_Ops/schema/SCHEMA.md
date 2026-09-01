# AI-Invest Vault Schema

版本：1.1.0；生效：2026-08-27。所有写入先遵守本文件，未知字段或路径一律拒绝。v1.1.0 新增：Thesis 质量字段（chokepoint/mispricing_reason/evidence_type/semantic_label 等）、claim inbox 可选质量字段、semantic_label 与 evidence_type 枚举。

## 1. 不变量

- `20_Raw/` 为 write-once 原始来源；市场语料仅限 news/article/google_news/x/podcast/substack/filings/macro/website。`pending_verification` 来源不得生成正式 Evidence 或 Thesis。
- 正式对象的来源链为 `Thesis → Evidence → source_id → Raw`；LLM 只提交 claim，确定性 S9 负责验证、去重和落盘。
- 所有图节点带 `domain: invest`；Neo4j 是可重建投影，不是事实源。

## 2. 公共字段

所有 Raw/Wiki/Thesis/Assumption/Evidence：`source_url`、`source_type`、`evidence_level`、`updated_date`（YYYY-MM-DD）、`related_links`（[[wikilink]]）、`key_insight`、`next_action`。

`source_type`：news, article, google_news, x_tweet, podcast, substack, filings, website, video_note, documentation, github_repository, project_spec。

`evidence_level`：primary_source, secondary, opinion, pending_verification。

`evidence_type`（claim/thesis 可选，证据来源类型）：earnings_transcript, conference_presentation, technical_paper, customer_capex, supply_chain_check, company_filing, x_tweet, substack, news, other。权重：earnings_transcript/company_filing=1.0，conference_presentation/technical_paper=0.85，customer_capex/supply_chain_check=0.7，x_tweet/substack/news/other=0.5。

`semantic_label`（claim/thesis 可选，7 级语义分类）：
- `keep`：完整前瞻 thesis（公司/技术+堆栈位置+chokepoint+证据+催化+风险）→ 生成 active thesis
- `keep_deweighted`：有效 thesis 但缺证据/时点/估值/风险之一 → 生成 pending thesis，进入 discovery
- `deweight`：技术科普/行业综述/宽泛篮子/watchlist → 写入 30_Wiki/Concepts/，不生成 thesis
- `delete_from_this_signal`：ticker 仅在引用/对比/无关上下文出现 → 不生成该 ticker claim
- `remove_forward_keep_track_record`：历史战绩/组合回顾/营销内容 → 写入 _archive 上下文，不进入前瞻信号
- `keep_as_explainer_deweight`：有用框架课但不挂钩具体信号 → 写入 30_Wiki/Concepts/
- `delete`：付费/私有/重复/无关 → 不归档，记录删除原因到 quarantine

`signal_classification`（thesis 必填，v1.2 新增，2026-08-27）：信号 vs 噪声分类，**噪声不删除，全部保留在图谱中**。
- `signal`：对公司收入/成本/业绩有持续重大影响的信息。包括：客户部署/设计赢单（有真实收入影响）、产能爬坡/量产（供给侧信号）、结构性瓶颈/供需变化（chokepoint）、核心团队变动/竞争格局变化、用户需求变化。
- `weak_signal`：有潜在影响但缺乏量化/验证的信息。包括：单一信源（x_tweet）未交叉验证、客户验证但缺 chokepoint/催化剂/风险、产能信息但缺瓶颈分析。
- `noise`：不直接改变基本面的信息。包括：产品参数/性能发布（技术科普）、planned investment/战略声明、获奖/荣誉、生态合作/联合发布（收入影响不明）、领导关注/分析师推荐。

`signal_strength`（thesis 必填，v1.2 新增，1-5 整数）：信号强度，与 signal_classification 配合使用。
- 5：强信号——多信源交叉验证 + 量化收入/成本影响 + chokepoint + 催化剂 + 风险
- 4：中强信号——客户验证 + 收入/产能影响，缺部分维度
- 3：弱信号——有潜在影响但缺量化/验证（weak_signal 默认值）
- 2：弱噪声——可能有间接影响但不直接影响基本面
- 1：纯噪声——产品参数/营销/获奖/战略声明（noise 默认值）

## 3. 对象

### Raw
必填：公共字段、`source_id`（文件名，不含 .md）、`published_date`（可空）、`content_hash`（可空）。Raw 不可覆盖。

### Evidence
必填：公共字段、`evidence_id`（`EVIDENCE-<sha>`）、`source_id`、`quote`、`locator`、`published_date`、`status`。`status`：verified, pending_verification, challenged, stale。

### Thesis
必填：公共字段、`thesis_id`（`THESIS-YYYY-NNN`）、`ticker`、`direction`、`claim`、`strength`（1..5）、`status`、`supporting_evidence`、`contradicting_evidence`、`horizon`、`falsifiers`、`expected_event`、`refresh_trigger`、`stale_after`、`signal_classification`（signal/weak_signal/noise，见 §2）、`signal_strength`（1..5，见 §2）。
可选质量字段（semantic_label=keep 时建议填全，keep_deweighted 时可缺 1-2 项）：`demand_wave`（大需求浪潮）、`stack_position`（价值链位置：上游材料/设备/IP/晶圆制造/封装测试/芯片设计/互连/系统集成/应用）、`chokepoint`（瓶颈/稀缺性）、`mispricing_reason`（市场错误定价原因）、`evidence_type`（证据来源类型枚举）、`semantic_label`（7 级语义分类）、`catalysts`（催化剂列表）、`risks`（风险列表）、`tracking_metrics`（跟踪指标列表）。
`status`：active, pending, broken, archived。semantic_label=keep → status=active；semantic_label=keep_deweighted → status=pending（进入 discovery，需更多证据升格）。
**噪声保留原则**：signal_classification=noise 的 thesis 不删除，全部保留在 discovery/ 并进入图谱，用 signal_classification 和 signal_strength 标签区分，便于后续回溯和信号演化追踪。

### Assumption
必填：公共字段、`assumption_id`（`ASSUMPTION-YYYY-NNN`）、`statement`、`status`、`last_checked`、`falsifier`、`related_thesis`。

## 4. Atomic inbox v1.1

路径：`.kg/atomic/inbox/claims-<timestamp>.json`。格式为 UTF-8 JSON **数组**，不是 JSONL。每条必填：`ticker`（`^[A-Z][A-Z0-9.-]{0,9}$`）、`direction`（bull/bear）、`claim`、`quote`、`source_id`（裸文件名）。可选：`confidence`（0..1）、`evidence_locator`、`published_date`、`run_id`、`extracted_at`、`evidence_type`（枚举，见 §2）、`semantic_label`（枚举，见 §2）、`demand_wave`、`stack_position`、`chokepoint`、`mispricing_reason`、`catalysts`（数组）、`risks`（数组）、`tracking_metrics`（数组）、`falsifiers`（数组）、`signal_classification`（signal/weak_signal/noise，LLM 提取时标注，缺失时由 S9 确定性分类器补全）、`signal_strength`（1..5，LLM 提取时标注，缺失时由 S9 确定性分类器补全）。S9 无法逐字/空白归一化匹配 quote 时必须写 `90_Ops/quarantine/`。

S9 处理规则：
- `semantic_label` 未提供时默认为 `keep_deweighted`（保守，不自动升格为 active）。
- `semantic_label=keep` 但缺 chokepoint/evidence_type(非x_tweet/substack/news)/falsifiers/catalysts 之一 → 自动降级为 `keep_deweighted`，status=pending。
- `semantic_label` 为 deweight/keep_as_explainer_deweight → 不生成 thesis，写入 30_Wiki/Concepts/（如 claim 含概念）。
- `semantic_label` 为 delete_from_this_signal/remove_forward_keep_track_record/delete → 不生成 thesis，记录到 quarantine。
- `strength` = `min(5, round(cluster_size * evidence_type_weight * 2))`，evidence_type=x_tweet/substack/news 时 strength 上限 3（社媒低置信度）。

## 5. 图谱

节点与主键：Thesis/thesis_id，Assumption/assumption_id，Evidence/doc_id，Company/Concept/Product/Person/Event/Source 均为 name。关系最少包括 `CITES`、`ABOUT`、`SUPPORTS`、`CHALLENGES`；S8 以 `domain + primary key` 参数化 MERGE。