#!/usr/bin/env python3
"""Schema lint for formal AI-Invest objects v1.1; exits non-zero on fatal errors.

v1.1 changes (2026-08-27):
- semantic_label 一致性检查：keep 标签必须有 chokepoint/falsifiers/catalysts（非社媒 evidence_type）
- stale_after 过期检查：thesis stale_after 日期已过 → warn
- evidence_type / semantic_label 枚举值校验
- 新质量字段（demand_wave/stack_position/chokepoint/mispricing_reason/catalysts/risks/tracking_metrics）识别
"""
from __future__ import annotations
import json, re, sys
from datetime import date
from pathlib import Path

V = Path(__file__).resolve().parent.parent.parent  # vault root (auto-detect from script location)
COMMON = {'source_url','source_type','evidence_level','updated_date','related_links','key_insight','next_action'}
THESIS = COMMON | {
    'thesis_id','ticker','direction','headline','claim','strength','status',
    'supporting_evidence','contradicting_evidence','horizon','falsifiers',
    'expected_event','refresh_trigger','stale_after',
    'signal_classification','signal_strength',
}
# v1.1 可选质量字段（不强制必填，但 keep 标签时建议完整——由 check_thesis_quality 单独检查）
THESIS_OPTIONAL_QUALITY = {
    'demand_wave','stack_position','chokepoint','mispricing_reason',
    'evidence_type','semantic_label','catalysts','risks','tracking_metrics',
}
EVIDENCE = COMMON | {'evidence_id','source_id','quote','locator','published_date','status','evidence_type'}
ASSUMPTION = COMMON | {'assumption_id','statement','status','last_checked','falsifier','related_thesis'}

VALID_EVIDENCE_TYPES = {
    'earnings_transcript','company_filing','conference_presentation','technical_paper',
    'customer_capex','supply_chain_check','x_tweet','substack','news','other','',
}
VALID_SEMANTIC_LABELS = {
    'keep','keep_deweighted','deweight','delete_from_this_signal',
    'remove_forward_keep_track_record','keep_as_explainer_deweight','delete','',
}
SOCIAL_EVIDENCE_TYPES = {'x_tweet','substack','news','other'}
KEEP_REQUIRED_QUALITY_FIELDS = ('chokepoint', 'falsifiers', 'catalysts')

ISSUES=[]

def frontmatter(path: Path):
    text=path.read_text(encoding='utf8',errors='replace')
    match=re.match(r'^---\s*\n(.*?)\n---',text,re.S)
    if not match: return None
    return {k:v.strip().strip('"\'') for k,v in re.findall(r'^([A-Za-z_]+):\s*(.*)$',match.group(1),re.M)}

def issue(path, severity, message):
    ISSUES.append({'path':str(path.relative_to(V)),'severity':severity,'message':message})

def _is_empty(value: str) -> bool:
    """YAML frontmatter 空值判定：空字符串、[]、{}、null、none。"""
    if not value: return True
    v = value.strip().lower()
    return v in ('', '[]', '{}', 'null', 'none', '~')

def check_thesis_quality(path: Path, data: dict):
    """v1.1: semantic_label 一致性 + keep 字段完整性 + stale_after 过期。"""
    label = data.get('semantic_label', '')
    ev_type = data.get('evidence_type', '')
    # semantic_label 枚举校验
    if label and label not in VALID_SEMANTIC_LABELS:
        issue(path, 'warn', f'invalid semantic_label: {label!r}')
    # evidence_type 枚举校验
    if ev_type and ev_type not in VALID_EVIDENCE_TYPES:
        issue(path, 'warn', f'invalid evidence_type: {ev_type!r}')
    # signal_classification 枚举校验
    sig_class = data.get('signal_classification', '')
    if sig_class and sig_class not in ('signal', 'weak_signal', 'noise'):
        issue(path, 'fatal', f'invalid signal_classification: {sig_class!r} (must be signal/weak_signal/noise)')
    # signal_strength 范围校验
    sig_strength = data.get('signal_strength', '')
    if sig_strength:
        try:
            ss = int(sig_strength)
            if not (1 <= ss <= 5):
                issue(path, 'fatal', f'signal_strength must be 1..5, got {ss}')
        except ValueError:
            issue(path, 'fatal', f'signal_strength must be an integer, got {sig_strength!r}')
    # keep 标签字段完整性（非社媒 evidence_type 时）
    if label == 'keep':
        if ev_type in SOCIAL_EVIDENCE_TYPES:
            issue(path, 'warn', 'semantic_label=keep but evidence_type is social-only (should be keep_deweighted)')
        else:
            missing = [f for f in KEEP_REQUIRED_QUALITY_FIELDS if _is_empty(data.get(f, ''))]
            if missing:
                issue(path, 'warn', f'semantic_label=keep but missing quality fields: {", ".join(missing)}')
    # stale_after 过期检查
    stale = data.get('stale_after', '')
    if stale and re.fullmatch(r'\d{4}-\d{2}-\d{2}', stale):
        try:
            stale_date = date.fromisoformat(stale)
            if stale_date < date.today():
                issue(path, 'warn', f'thesis stale_after={stale} has passed (status={data.get("status","?")})')
        except ValueError:
            pass
    # strength 范围
    strength = data.get('strength', '')
    if strength:
        try:
            s = int(strength)
            if not (1 <= s <= 5):
                issue(path, 'fatal', f'strength must be 1..5, got {s}')
        except ValueError:
            issue(path, 'fatal', f'strength must be an integer, got {strength!r}')

def check_dir(folder, required, prefix, quality_check=None):
    for path in folder.glob('*.md'):
        data=frontmatter(path)
        if data is None:
            issue(path,'fatal','missing frontmatter'); continue
        missing=sorted(k for k in required if k not in data)
        if missing: issue(path,'fatal',f'missing required fields: {", ".join(missing)}')
        ident=next((k for k in data if k.endswith('_id')), '')
        if ident and not data[ident].startswith(prefix): issue(path,'fatal',f'{ident} must start with {prefix}')
        if data.get('evidence_level') == 'pending_verification' and prefix in {'THESIS-','EVIDENCE-'}:
            issue(path,'fatal','pending_verification cannot be a formal Thesis or Evidence')
        if data.get('direction') and data['direction'] not in {'bull','bear'}: issue(path,'fatal','direction must be bull or bear')
        if data.get('updated_date') and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',data['updated_date']): issue(path,'fatal','updated_date must be YYYY-MM-DD')
        if quality_check:
            quality_check(path, data)

check_dir(V/'40_Thesis'/'theses', THESIS, 'THESIS-', check_thesis_quality)
check_dir(V/'40_Thesis'/'discovery', THESIS, 'THESIS-', check_thesis_quality)
check_dir(V/'40_Thesis'/'assumptions', ASSUMPTION, 'ASSUMPTION-')
check_dir(V/'30_Wiki'/'Sources', EVIDENCE, 'EVIDENCE-')
counts={'info':0,'warn':sum(x['severity']=='warn' for x in ISSUES),'fatal':sum(x['severity']=='fatal' for x in ISSUES)}
out={'severity_count':counts,'issues':ISSUES}
report=V/'90_Ops'/'lint-reports'; report.mkdir(parents=True,exist_ok=True)
(report/'latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(out,ensure_ascii=False)); sys.exit(1 if counts['fatal'] else 0)
