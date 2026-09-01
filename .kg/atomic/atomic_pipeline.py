#!/usr/bin/env python3
"""Deterministic atomic claim pipeline v1.1: verify -> dedup -> thesis -> report.

v1.1 changes (2026-08-27):
- semantic_label 7级分流：keep→active thesis, keep_deweighted→pending/discovery, 其余跳过
- evidence_type 权重加权 strength 计算
- 质量字段（chokepoint/mispricing_reason/catalysts/risks/tracking_metrics 等）写入 thesis frontmatter
- keep 标签字段完整性校验：缺 chokepoint/evidence_type(非社媒)/falsifiers/catalysts → 降级为 keep_deweighted
"""
from __future__ import annotations
import hashlib, json, re
from datetime import date, datetime
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent  # vault root (auto-detect from script location)
INBOX = VAULT / ".kg" / "atomic" / "inbox"
PROCESSED = INBOX / "processed"
QUARANTINE = VAULT / "90_Ops" / "quarantine"
THESIS = VAULT / "40_Thesis" / "theses"
DISCOVERY = VAULT / "40_Thesis" / "discovery"
EVIDENCE = VAULT / "30_Wiki" / "Sources"
CONCEPTS = VAULT / "30_Wiki" / "Concepts"
MARKET_DIRS = ("news", "article", "google_news", "x", "podcast", "substack", "filings", "macro", "website")
WEEK = f"{date.today().isocalendar().year}-W{date.today().isocalendar().week:02d}"

# evidence_type → strength 权重（SCHEMA.md v1.1 §2）
EVIDENCE_TYPE_WEIGHTS = {
    "earnings_transcript": 1.0,
    "company_filing": 1.0,
    "conference_presentation": 0.85,
    "technical_paper": 0.85,
    "customer_capex": 0.7,
    "supply_chain_check": 0.7,
    "x_tweet": 0.5,
    "substack": 0.5,
    "news": 0.5,
    "other": 0.5,
}
# 社媒类 evidence_type 的 strength 上限
SOCIAL_EVIDENCE_TYPES = {"x_tweet", "substack", "news", "other"}
SOCIAL_STRENGTH_CAP = 3

# semantic_label → 处理方式
# keep: 生成 active thesis（字段完整时）
# keep_deweighted: 生成 pending thesis，写入 discovery
# deweight / keep_as_explainer_deweight: 写入 Concepts，不生成 thesis
# delete_from_this_signal / remove_forward_keep_track_record / delete: 跳过，记录 quarantine
THESIS_LABELS = {"keep", "keep_deweighted"}
CONCEPT_LABELS = {"deweight", "keep_as_explainer_deweight"}
SKIP_LABELS = {"delete_from_this_signal", "remove_forward_keep_track_record", "delete"}
DEFAULT_LABEL = "keep_deweighted"

# keep 标签必须包含的质量字段（非社媒 evidence_type 时）
KEEP_REQUIRED_FIELDS = ("chokepoint", "falsifiers", "catalysts")

# 信号 vs 噪声分类关键词（书中标准：信号=对收入/成本/业绩有持续重大影响）
NOISE_KEYWORDS = (
    "announces", "unveils", "launches", "showcases", "demonstrates", "introduces", "reveals",
    "performance", "throughput", "efficiency", "bandwidth", "spec", "parameters", "token cost",
    "award", "honor", "recognition", "winner",
    "partnership", "collaboration", "alliance", "joint", "cooperation",
    "planned", "vision", "strategy", "roadmap", "commitment",
    "research institution", "research hub", "r&d center", "research center",
    "keynote", "teaser", "save the date",
)
SIGNAL_KEYWORDS = (
    "deployment", "deployed", "deploying", "operational", "production", "ramping", "ramp",
    "volume", "shipments", "shipping",
    "customer", "design win", "qualified", "adoption", "orders", "backlog",
    "capacity", "bottleneck", "constraint", "shortage", "scarcity", "chokepoint",
    "revenue", "margin", "earnings", "guidance", "outperform",
    "demand", "supply", "inventory", "pricing power",
    "key factor", "critical for", "essential for",
)

def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()

def raw_by_id(source_id: str) -> Path | None:
    for name in MARKET_DIRS:
        path = VAULT / "20_Raw" / name / f"{source_id}.md"
        if path.is_file(): return path
    return None

def jaccard(a: str, b: str) -> float:
    grams = lambda s: {s[i:i+3] for i in range(max(0, len(s)-2))} or {s}
    left, right = grams(norm(a).lower()), grams(norm(b).lower())
    return len(left & right) / len(left | right)

def next_id() -> str:
    year = date.today().year
    ids = []
    # 同时检查 theses/ 和 discovery/，避免 pending thesis ID 冲突覆盖
    for d in (THESIS, DISCOVERY):
        for path in d.glob(f"THESIS-{year}-*.md"):
            match = re.fullmatch(rf"THESIS-{year}-(\d{{3}})\.md", path.name)
            if match: ids.append(int(match.group(1)))
    return f"THESIS-{year}-{max(ids, default=0)+1:03d}"

def frontmatter_value(raw: str, key: str, default: str = "") -> str:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.*)$", raw)
    return match.group(1).strip().strip("\"'") if match else default

def evidence_id(source_id: str, quote: str) -> str:
    digest = hashlib.sha256(f"{source_id}\0{norm(quote)}".encode("utf-8")).hexdigest()[:16]
    return f"EVIDENCE-{digest}"

def write_evidence(claim: dict) -> str:
    raw = Path(claim["raw_path"]).read_text(encoding="utf-8", errors="replace")
    eid = evidence_id(claim["source_id"], claim["quote"])
    path = EVIDENCE / f"{eid}.md"
    if not path.exists():
        source_type = frontmatter_value(raw, "source_type", "article")
        source_url = frontmatter_value(raw, "source_url")
        published = claim.get("published_date") or frontmatter_value(raw, "published_date")
        locator = claim.get("evidence_locator", "full_text")
        ev_type = claim.get("evidence_type", "")
        content = (
            f"---\nevidence_id: {eid}\nsource_id: {claim['source_id']}\nquote: {json.dumps(norm(claim['quote']), ensure_ascii=False)}\n"
            f"locator: {json.dumps(locator, ensure_ascii=False)}\nstatus: verified\nsource_url: {json.dumps(source_url, ensure_ascii=False)}\n"
            f"source_type: {source_type}\nevidence_level: secondary\nupdated_date: {date.today()}\npublished_date: {published}\n"
        )
        if ev_type:
            content += f"evidence_type: {ev_type}\n"
        content += (
            f"related_links: ''\nkey_insight: {json.dumps(claim['claim'], ensure_ascii=False)}\nnext_action: verify contrary evidence\n---\n\n# {eid}\n\n> {norm(claim['quote'])}\n"
        )
        path.write_text(content, encoding="utf-8")
    return eid

def classify_semantic_label(claim: dict) -> str:
    """根据 claim 字段和 semantic_label 判定最终标签。keep 缺必要字段时降级为 keep_deweighted。"""
    label = claim.get("semantic_label", DEFAULT_LABEL)
    if label not in THESIS_LABELS | CONCEPT_LABELS | SKIP_LABELS:
        label = DEFAULT_LABEL
    if label == "keep":
        ev_type = claim.get("evidence_type", "")
        # 非社媒 evidence_type 时，keep 必须有 chokepoint/falsifiers/catalysts
        if ev_type and ev_type not in SOCIAL_EVIDENCE_TYPES:
            missing = [f for f in KEEP_REQUIRED_FIELDS if not claim.get(f)]
            if missing:
                return "keep_deweighted"
        # 社媒 evidence_type 的 keep 也降级（社媒不足以单独支撑 active thesis）
        if ev_type in SOCIAL_EVIDENCE_TYPES:
            return "keep_deweighted"
    return label

def calc_strength(cluster: list[dict]) -> int:
    """evidence_type 加权 strength：min(5, round(cluster_size * avg_weight * 2))，社媒上限 3。"""
    weights = []
    for c in cluster:
        et = c.get("evidence_type", "")
        weights.append(EVIDENCE_TYPE_WEIGHTS.get(et, 0.5))
    avg_w = sum(weights) / len(weights) if weights else 0.5
    raw = min(5, round(len(cluster) * avg_w * 2))
    # 如果簇内所有 claim 都是社媒类型，strength 上限 3
    all_social = all(c.get("evidence_type", "") in SOCIAL_EVIDENCE_TYPES for c in cluster)
    if all_social:
        raw = min(raw, SOCIAL_STRENGTH_CAP)
    return raw

def quality_fields_from_cluster(cluster: list[dict]) -> dict:
    """从簇中提取质量字段（取 lead claim 的值，列表字段合并去重）。"""
    lead = cluster[0]
    fields = {}
    scalar_fields = ("demand_wave", "stack_position", "chokepoint", "mispricing_reason", "evidence_type", "semantic_label")
    list_fields = ("catalysts", "risks", "tracking_metrics", "falsifiers")
    for f in scalar_fields:
        v = lead.get(f)
        if v:
            fields[f] = v if isinstance(v, str) else str(v)
    for f in list_fields:
        merged = []
        seen = set()
        for c in cluster:
            v = c.get(f)
            if isinstance(v, list):
                for item in v:
                    if item and item not in seen:
                        merged.append(item); seen.add(item)
            elif isinstance(v, str) and v:
                if v not in seen:
                    merged.append(v); seen.add(v)
        if merged:
            fields[f] = merged
    return fields


def classify_signal(cluster: list[dict]) -> tuple[str, int]:
    """确定性信号分类器：返回 (signal_classification, signal_strength)。
    优先使用 LLM 提交的 signal_classification/signal_strength，否则用关键词+证据类型+chokepoint 启发式分类。
    噪声不删除，全部保留在图谱中，用标签区分。"""
    lead = cluster[0]
    # 优先使用 LLM 提交的值
    llm_class = lead.get("signal_classification", "")
    llm_strength = lead.get("signal_strength")
    if llm_class in ("signal", "weak_signal", "noise") and llm_strength and 1 <= int(llm_strength) <= 5:
        return llm_class, int(llm_strength)

    # 确定性启发式分类
    claim_text = (lead.get("claim", "") + " " + lead.get("chokepoint", "")).lower()
    has_chokepoint = bool(lead.get("chokepoint"))
    has_signal_kw = any(kw in claim_text for kw in SIGNAL_KEYWORDS)
    has_noise_kw = any(kw in claim_text for kw in NOISE_KEYWORDS)
    ev_type = lead.get("evidence_type", "")

    # 分类判定
    if has_chokepoint and has_signal_kw:
        classification = "signal"
        base_strength = 4
    elif has_signal_kw and not has_noise_kw:
        classification = "weak_signal"
        base_strength = 3
    elif has_noise_kw and not has_signal_kw:
        classification = "noise"
        base_strength = 1
    elif has_signal_kw and has_noise_kw:
        # 混合：有信号词但也有噪声词，偏 weak_signal
        classification = "weak_signal"
        base_strength = 2
    else:
        classification = "weak_signal"
        base_strength = 3

    # 证据类型调整
    if ev_type in ("earnings_transcript", "company_filing"):
        base_strength = min(5, base_strength + 1)
    elif ev_type in SOCIAL_EVIDENCE_TYPES:
        base_strength = max(1, base_strength - 1)

    # 簇大小调整（多独立证据交叉验证）
    if len(cluster) >= 3:
        base_strength = min(5, base_strength + 1)
    elif len(cluster) == 1:
        base_strength = max(1, base_strength - 1)

    # 按分类级别设下限，保证强弱有区分度
    floor = {"signal": 3, "weak_signal": 2, "noise": 1}.get(classification, 1)
    base_strength = max(floor, base_strength)

    return classification, base_strength

def write_thesis(cluster: list[dict], status: str) -> str:
    lead = cluster[0]
    ticker = lead["ticker"]
    thesis_id = next_id()
    cited = list(dict.fromkeys(write_evidence(c) for c in cluster))
    strength = calc_strength(cluster)
    qf = quality_fields_from_cluster(cluster)
    signal_class, signal_strength = classify_signal(cluster)
    # headline: LLM 提供优先，否则从 claim 自动生成
    headline = lead.get("headline", "").strip()
    if not headline:
        claim_text = lead["claim"]
        if "\u2192" in claim_text:
            headline = claim_text.split("\u2192")[0].strip()
        else:
            headline = re.split(r'[.!?]', claim_text)[0].strip()
        if len(headline) > 120:
            headline = headline[:117] + "..."
    today = date.today()
    content = (
        f"---\nthesis_id: {thesis_id}\nticker: {ticker}\ndirection: {lead['direction']}\n"
        f"headline: {json.dumps(headline, ensure_ascii=False)}\n"
        f"claim: {json.dumps(lead['claim'], ensure_ascii=False)}\nstrength: {strength}\nstatus: {status}\n"
        f"signal_classification: {signal_class}\nsignal_strength: {signal_strength}\n"
        f"source_url: ''\nsource_type: article\nevidence_level: secondary\nupdated_date: {today}\n"
        f"related_links: ''\nkey_insight: {json.dumps(headline, ensure_ascii=False)}\nnext_action: verify contrary evidence\n"
        f"supporting_evidence: {json.dumps(cited, ensure_ascii=False)}\ncontradicting_evidence: []\n"
        f"horizon: pending\nfalsifiers: {json.dumps(qf.get('falsifiers', []), ensure_ascii=False)}\n"
        f"expected_event: pending\nrefresh_trigger: new evidence\nstale_after: ''\n"
    )
    # 写入可选质量字段
    for key in ("demand_wave", "stack_position", "chokepoint", "mispricing_reason", "evidence_type", "semantic_label"):
        if key in qf:
            content += f"{key}: {json.dumps(qf[key], ensure_ascii=False) if isinstance(qf[key], (list, dict)) else qf[key]}\n"
    for key in ("catalysts", "risks", "tracking_metrics"):
        if key in qf:
            content += f"{key}: {json.dumps(qf[key], ensure_ascii=False)}\n"
    content += (
        f"---\n\n# {thesis_id}\n\n## Headline\n\n{headline}\n\n## Full Thesis\n\n{lead['claim']}\n\n## Evidence\n\n"
        + "\n".join(f"- `{eid}`" for eid in cited) + "\n"
    )
    out_dir = THESIS if status == "active" else DISCOVERY
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{thesis_id}.md").write_text(content, encoding="utf-8")
    return thesis_id

def write_concept(claim: dict) -> None:
    """deweight/keep_as_explainer_deweight 标签的 claim 写入 Concepts。"""
    CONCEPTS.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", claim["claim"][:50].lower()).strip("-")
    path = CONCEPTS / f"concept-{slug}.md"
    if path.exists():
        return
    content = (
        f"---\nconcept_id: CONCEPT-{slug}\nsource_id: {claim['source_id']}\n"
        f"semantic_label: {claim.get('semantic_label', 'deweight')}\nupdated_date: {date.today()}\n"
        f"related_links: ''\nkey_insight: {json.dumps(claim['claim'], ensure_ascii=False)}\n---\n\n"
        f"# {claim['claim'][:80]}\n\n> {norm(claim.get('quote', ''))}\n"
    )
    path.write_text(content, encoding="utf-8")

def main() -> int:
    INBOX.mkdir(parents=True, exist_ok=True); PROCESSED.mkdir(parents=True, exist_ok=True)
    QUARANTINE.mkdir(parents=True, exist_ok=True); THESIS.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True); DISCOVERY.mkdir(parents=True, exist_ok=True)
    claims, bad = [], []
    concept_claims = []
    processed_files: list[Path] = []
    for file in sorted(INBOX.glob("claims-*.json")):
        try:
            rows = json.loads(file.read_text(encoding="utf-8"))
            if not isinstance(rows, list): raise ValueError("inbox file is not a JSON array")
        except Exception as exc:
            bad.append({"file": file.name, "reason": str(exc)}); continue
        for row in rows:
            source = raw_by_id(str(row.get("source_id", "")))
            quote = str(row.get("quote", ""))
            if not source or not quote:
                bad.append({"claim": row, "reason": "missing raw source or quote"}); continue
            raw = source.read_text(encoding="utf-8", errors="replace")
            if frontmatter_value(raw, "evidence_level") == "pending_verification":
                bad.append({"claim": row, "reason": "source pending verification", "raw_path": str(source)}); continue
            if norm(quote) not in norm(raw):
                bad.append({"claim": row, "reason": "quote not found in source", "raw_path": str(source)}); continue
            row["raw_path"] = str(source)
            # semantic_label 分流
            label = classify_semantic_label(row)
            row["_resolved_label"] = label
            if label in SKIP_LABELS:
                bad.append({"claim": {k: v for k, v in row.items() if not k.startswith("_")}, "reason": f"semantic_label={label}, skipped", "raw_path": str(source)})
                continue
            if label in CONCEPT_LABELS:
                concept_claims.append(row)
                continue
            claims.append(row)
        processed_files.append(file)
    if bad:
        (QUARANTINE / f"atomic-{WEEK}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False)+"\n" for x in bad), encoding="utf-8")
    # concept claims 写入 Concepts（不参与 thesis 聚类）
    for c in concept_claims:
        write_concept(c)
    # thesis claims 聚类
    clusters: list[list[dict]] = []
    for claim in claims:
        for cluster in clusters:
            lead = cluster[0]
            if (claim["ticker"], claim["direction"]) == (lead["ticker"], lead["direction"]) and jaccard(claim["claim"], lead["claim"]) >= 0.72:
                cluster.append(claim); break
        else: clusters.append([claim])
    by_ticker: dict[str, dict[str, int]] = {}
    active_count = 0
    pending_count = 0
    signal_counts = {"signal": 0, "weak_signal": 0, "noise": 0}
    for cluster in clusters:
        lead = cluster[0]; ticker = lead["ticker"]
        entry = by_ticker.setdefault(ticker, {"bull": 0, "bear": 0, "net": 0})
        entry[lead["direction"]] += 1; entry["net"] = entry["bull"] - entry["bear"]
        label = lead.get("_resolved_label", DEFAULT_LABEL)
        status = "active" if label == "keep" else "pending"
        thesis_id = write_thesis(cluster, status)
        if status == "active":
            active_count += 1
        else:
            pending_count += 1
        sc, ss = classify_signal(cluster)
        signal_counts[sc] = signal_counts.get(sc, 0) + 1
    report = {
        "week": WEEK, "run_id": datetime.now().isoformat(timespec="seconds"),
        "new_bull": sum(v["bull"] for v in by_ticker.values()),
        "new_bear": sum(v["bear"] for v in by_ticker.values()),
        "by_ticker": by_ticker,
        "net_bias": sum(v["net"] for v in by_ticker.values()),
        "corroboration_avg": (sum(len(c) for c in clusters)/len(clusters)) if clusters else 0,
        "new_evidence_n": len(claims),
        "new_thesis_active": active_count,
        "new_thesis_pending": pending_count,
        "signal_classification": signal_counts,
        "new_concepts": len(concept_claims),
        "new_assumptions": 0,
        "quarantine_n": len(bad),
    }
    (VAULT / ".kg" / "atomic" / f"report-{WEEK}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    for file in processed_files:
        file.replace(PROCESSED / file.name)
    print(json.dumps(report, ensure_ascii=False)); return 0

if __name__ == "__main__": raise SystemExit(main())
