#!/usr/bin/env python3
"""Generate a self-contained interactive HTML visualization of the invest graph.

Reads graph-invest-<WW>.json and produces graph-viz-<WW>.html with embedded data.
Uses vis.js (CDN) for network rendering; no server required.

v2.0 (2026-08-27): Dark financial dashboard theme — stat cards, refined sidebar,
card-style detail panel with gradient header, phosphor icons, smooth animations.
"""
from __future__ import annotations
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

V = Path(__file__).resolve().parent.parent
WEEK = f"{date.today().isocalendar().year}-W{date.today().isocalendar().week:02d}"
GRAPH_JSON = V / ".kg" / f"graph-invest-{WEEK}.json"
OUT_HTML = V / ".kg" / f"graph-viz-{WEEK}.html"

LABEL_COLORS = {
    "Thesis": "#60A5FA", "Company": "#F87171", "Evidence": "#FBBF24",
    "Source": "#94A3B8", "Concept": "#34D399", "Product": "#A78BFA",
    "Person": "#FB923C", "Event": "#2DD4BF", "Assumption": "#CBD5E1",
}
SIGNAL_COLORS = {"signal": "#34D399", "weak_signal": "#FBBF24", "noise": "#475569"}
SIGNAL_BG = {"signal": "rgba(52,211,153,0.15)", "weak_signal": "rgba(251,191,36,0.15)", "noise": "rgba(71,85,105,0.25)"}
NODE_SIZES = {"Company": 34, "Thesis": 26, "Evidence": 14, "Source": 10}


def clean_text(text: str) -> str:
    if not text:
        return ""
    return text.replace("鈫?", "\u2192").replace("鈫?", "\u2192")


def build_html(graph: dict) -> str:
    nodes = graph["nodes"]
    rels = graph["rels"]

    vis_nodes = []
    for n in nodes:
        label = n["label"]
        props = n["properties"]
        pk = n["primary_key_value"]

        color = LABEL_COLORS.get(label, "#6B7280")
        if label == "Thesis":
            sig = props.get("signal_classification", "")
            color = SIGNAL_COLORS.get(sig, color)

        size = NODE_SIZES.get(label, 15)

        if label == "Thesis":
            headline = clean_text(props.get("headline", ""))
            if not headline:
                headline = clean_text(props.get("claim", ""))
            display = headline[:42] + "..." if len(headline) > 42 else headline
        elif label == "Company":
            display = props.get("ticker", pk)
        elif label == "Evidence":
            display = pk[:14]
        elif label == "Source":
            display = pk[:20]
        else:
            display = pk[:25]

        full_props_json = json.dumps(props, ensure_ascii=False)

        vis_nodes.append({
            "id": f"{label}:{pk}",
            "label": display,
            "shape": "star" if label == "Thesis" else "dot",
            "color": {"background": color, "border": "#1E293B", "highlight": {"background": color, "border": "#fff"}},
            "size": size,
            "font": {"size": 10 if label == "Thesis" else 11, "color": "#E2E8F0", "face": "'Inter',system-ui,sans-serif", "strokeWidth": 0},
            "title": clean_text(props.get("headline", props.get("claim", pk))),
            "group": label,
            "signal_class": props.get("signal_classification", ""),
            "is_thesis": label == "Thesis",
            "full_props": full_props_json,
        })

    vis_edges = []
    for r in rels:
        src, dst = r["src"], r["dst"]
        vis_edges.append({
            "from": f"{src['label']}:{src['key']}",
            "to": f"{dst['label']}:{dst['key']}",
            "label": r["type"],
            "font": {"size": 9, "color": "#64748B", "face": "'Inter',system-ui,sans-serif"},
            "arrows": "to",
            "color": {"color": "#334155", "highlight": "#60A5FA"},
            "smooth": {"type": "continuous"},
            "width": 1,
        })

    label_counts = Counter(n["label"] for n in nodes)
    sig_counts = Counter(
        n["properties"].get("signal_classification", "unknown")
        for n in nodes if n["label"] == "Thesis"
    )

    nodes_json = json.dumps(vis_nodes, ensure_ascii=False)
    edges_json = json.dumps(vis_edges, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI-Invest Knowledge Graph — {WEEK}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
:root {{
  --bg: #0F172A;
  --bg-elevated: #1E293B;
  --bg-card: #1E293B;
  --bg-hover: #334155;
  --border: #334155;
  --border-light: #475569;
  --text: #F1F5F9;
  --text-muted: #94A3B8;
  --text-dim: #64748B;
  --accent: #60A5FA;
  --accent-glow: rgba(96,165,250,0.3);
  --signal: #34D399;
  --weak: #FBBF24;
  --noise: #475569;
  --bull: #34D399;
  --bear: #F87171;
  --radius: 10px;
  --radius-sm: 6px;
  --shadow: 0 4px 24px rgba(0,0,0,0.4);
  --shadow-lg: 0 8px 40px rgba(0,0,0,0.5);
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); overflow: hidden; height: 100vh; }}

/* Top Bar */
.topbar {{
  height: 60px; background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%);
  border-bottom: 1px solid var(--border); display: flex; align-items: center;
  padding: 0 20px; gap: 20px; z-index: 100; position: relative;
}}
.topbar-title {{ display: flex; align-items: center; gap: 10px; }}
.topbar-title svg {{ width: 24px; height: 24px; color: var(--accent); }}
.topbar-title h1 {{ font-size: 15px; font-weight: 700; letter-spacing: -0.01em; }}
.topbar-title .week {{ font-size: 11px; color: var(--text-dim); font-weight: 500; background: var(--bg-elevated); padding: 2px 8px; border-radius: 4px; font-family: 'JetBrains Mono', monospace; }}

/* Stat Cards */
.stats {{ display: flex; gap: 10px; margin-left: auto; }}
.stat-card {{
  background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-sm);
  padding: 6px 12px; display: flex; align-items: center; gap: 8px; min-width: 72px;
}}
.stat-card .icon {{ width: 16px; height: 16px; flex-shrink: 0; }}
.stat-card .value {{ font-size: 16px; font-weight: 700; font-family: 'JetBrains Mono', monospace; line-height: 1; }}
.stat-card .label {{ font-size: 9px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }}
.stat-card .stat-text {{ display: flex; flex-direction: column; gap: 2px; }}

/* Main Layout */
.main {{ display: flex; height: calc(100vh - 60px); }}

/* Sidebar */
.sidebar {{
  width: 240px; background: var(--bg-elevated); border-right: 1px solid var(--border);
  padding: 16px; overflow-y: auto; flex-shrink: 0;
}}
.sidebar::-webkit-scrollbar {{ width: 4px; }}
.sidebar::-webkit-scrollbar-thumb {{ background: var(--border-light); border-radius: 2px; }}
.sidebar-section {{ margin-bottom: 20px; }}
.sidebar-section:last-child {{ margin-bottom: 0; }}
.sidebar h3 {{
  font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--text-dim); margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid var(--border);
}}
.filter-item {{
  display: flex; align-items: center; gap: 8px; padding: 5px 6px; border-radius: var(--radius-sm);
  cursor: pointer; transition: background 0.15s; margin-bottom: 2px;
}}
.filter-item:hover {{ background: var(--bg-hover); }}
.filter-item input {{ accent-color: var(--accent); cursor: pointer; width: 14px; height: 14px; }}
.filter-item .color-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; border: 1px solid rgba(255,255,255,0.1); }}
.filter-item .color-dots {{ display: flex; gap: 2px; flex-shrink: 0; }}
.filter-item .color-dots .dot {{ width: 7px; height: 7px; border-radius: 50%; border: 1px solid rgba(255,255,255,0.1); }}
.filter-item .name {{ font-size: 12px; font-weight: 500; flex: 1; }}
.filter-item .count {{ font-size: 10px; color: var(--text-dim); font-family: 'JetBrains Mono', monospace; background: var(--bg); padding: 1px 6px; border-radius: 8px; }}

.sidebar-actions {{ display: flex; gap: 6px; flex-wrap: wrap; }}
.btn {{
  display: inline-flex; align-items: center; gap: 5px; padding: 6px 10px; background: var(--bg-hover);
  border: 1px solid var(--border); border-radius: var(--radius-sm); color: var(--text-muted);
  font-size: 11px; font-weight: 500; cursor: pointer; transition: all 0.15s; font-family: inherit;
}}
.btn:hover {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
.btn svg {{ width: 12px; height: 12px; }}

.legend {{ font-size: 10px; color: var(--text-dim); line-height: 1.7; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); }}

/* Graph Container */
.graph-container {{ flex: 1; position: relative; background: var(--bg); }}
#graph {{ width: 100%; height: 100%; }}

/* Detail Panel */
.detail-panel {{
  position: absolute; top: 16px; right: 16px; width: 400px; max-height: calc(100% - 32px);
  background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius);
  box-shadow: var(--shadow-lg); overflow-y: auto; z-index: 50; display: none;
  animation: slideIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}}
@keyframes slideIn {{ from {{ opacity: 0; transform: translateX(20px); }} to {{ opacity: 1; transform: translateX(0); }} }}
.detail-panel::-webkit-scrollbar {{ width: 5px; }}
.detail-panel::-webkit-scrollbar-thumb {{ background: var(--border-light); border-radius: 3px; }}
.detail-close {{
  position: absolute; top: 12px; right: 14px; cursor: pointer; color: var(--text-dim);
  font-size: 20px; z-index: 5; width: 24px; height: 24px; display: flex; align-items: center;
  justify-content: center; border-radius: 4px; transition: all 0.15s;
}}
.detail-close:hover {{ color: var(--text); background: var(--bg-hover); }}

/* Detail Header */
.detail-header {{
  padding: 16px 18px 14px; border-bottom: 1px solid var(--border); position: relative;
}}
.detail-header .thesis-id {{ font-size: 10px; color: var(--text-dim); font-family: 'JetBrains Mono', monospace; font-weight: 500; letter-spacing: 0.03em; }}
.detail-header .ticker-row {{ display: flex; align-items: center; gap: 10px; margin-top: 4px; }}
.detail-header .ticker {{ font-size: 22px; font-weight: 800; letter-spacing: -0.02em; }}
.detail-header .badges {{ display: flex; gap: 6px; margin-left: auto; }}
.badge {{
  display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px; border-radius: 20px;
  font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
}}
.badge-signal {{ background: var(--signal); color: #052e1a; }}
.badge-weak {{ background: var(--weak); color: #422006; }}
.badge-noise {{ background: var(--noise); color: #fff; }}
.badge-bull {{ background: rgba(52,211,153,0.15); color: var(--bull); border: 1px solid rgba(52,211,153,0.3); }}
.badge-bear {{ background: rgba(248,113,113,0.15); color: var(--bear); border: 1px solid rgba(248,113,113,0.3); }}

/* Headline */
.detail-headline {{
  padding: 14px 18px; border-bottom: 1px solid var(--border);
}}
.detail-headline .section-label {{
  font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--accent); margin-bottom: 6px; display: flex; align-items: center; gap: 5px;
}}
.detail-headline .section-label svg {{ width: 11px; height: 11px; }}
.detail-headline .headline-text {{
  font-size: 14px; font-weight: 600; line-height: 1.5; color: var(--text);
  border-left: 3px solid var(--accent); padding-left: 10px;
}}

/* Full Thesis (collapsible) */
.detail-full {{
  padding: 14px 18px; border-bottom: 1px solid var(--border);
}}
.detail-full details {{ }}
.detail-full summary {{
  cursor: pointer; font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--text-dim); list-style: none; display: flex;
  align-items: center; gap: 6px; margin-bottom: 0;
}}
.detail-full summary::-webkit-details-marker {{ display: none; }}
.detail-full summary::before {{ content: '\\25B6'; font-size: 8px; transition: transform 0.2s; color: var(--text-dim); }}
.detail-full details[open] summary::before {{ transform: rotate(90deg); }}
.detail-full .full-text {{
  margin-top: 10px; font-size: 12.5px; line-height: 1.7; color: #CBD5E1;
  white-space: pre-wrap; word-break: break-word; background: var(--bg); padding: 10px 12px;
  border-radius: var(--radius-sm); border: 1px solid var(--border);
}}

/* Detail Sections */
.detail-section {{ padding: 12px 18px; border-bottom: 1px solid var(--border); }}
.detail-section:last-child {{ border-bottom: none; }}
.detail-section .section-title {{
  font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--accent); margin-bottom: 8px; padding-bottom: 5px; border-bottom: 1px solid rgba(96,165,250,0.2);
  display: flex; align-items: center; gap: 6px;
}}
.detail-section .section-title svg {{ width: 12px; height: 12px; }}
.field-row {{
  display: flex; gap: 10px; padding: 4px 0; border-bottom: 1px solid rgba(51,65,85,0.5);
}}
.field-row:last-child {{ border-bottom: none; }}
.field-row .field-key {{
  min-width: 100px; font-size: 9px; color: var(--text-dim); text-transform: uppercase;
  font-weight: 600; padding-top: 2px; letter-spacing: 0.04em;
}}
.field-row .field-val {{ flex: 1; font-size: 12px; color: #CBD5E1; word-break: break-word; line-height: 1.5; }}
.field-row .field-val ul {{ margin: 2px 0; padding-left: 16px; }}
.field-row .field-val li {{ margin-bottom: 2px; }}

/* Non-thesis detail */
.detail-simple {{ padding: 16px 18px; }}
.detail-simple h2 {{ font-size: 15px; font-weight: 700; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }}

/* Company thesis summary */
.company-header {{ padding: 16px 18px 12px; border-bottom: 1px solid var(--border); }}
.company-header .ticker {{ font-size: 24px; font-weight: 800; letter-spacing: -0.02em; }}
.company-header .name {{ font-size: 12px; color: var(--text-muted); margin-top: 2px; }}
.summary-stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; padding: 14px 18px; border-bottom: 1px solid var(--border); }}
.summary-stat {{ background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 8px 10px; text-align: center; }}
.summary-stat .num {{ font-size: 20px; font-weight: 700; font-family: 'JetBrains Mono', monospace; line-height: 1; }}
.summary-stat .lbl {{ font-size: 9px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; margin-top: 4px; }}
.sentiment-bar {{ padding: 12px 18px; border-bottom: 1px solid var(--border); }}
.sentiment-bar .bar-label {{ font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-dim); margin-bottom: 6px; display: flex; justify-content: space-between; }}
.sentiment-bar .bar-track {{ height: 8px; background: var(--bg); border-radius: 4px; overflow: hidden; display: flex; }}
.sentiment-bar .bar-bull {{ background: var(--bull); height: 100%; transition: width 0.3s; }}
.sentiment-bar .bar-bear {{ background: var(--bear); height: 100%; transition: width 0.3s; }}
.sentiment-bar .bar-neutral {{ background: var(--border-light); height: 100%; transition: width 0.3s; }}
.sentiment-bar .net-label {{ font-size: 11px; margin-top: 6px; font-weight: 600; }}
.thesis-list {{ padding: 8px 18px 14px; }}
.thesis-list .list-title {{ font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); margin: 8px 0 6px; padding-bottom: 5px; border-bottom: 1px solid rgba(96,165,250,0.2); display: flex; align-items: center; gap: 6px; }}
.thesis-item {{ padding: 8px 10px; border-radius: var(--radius-sm); cursor: pointer; transition: background 0.15s; margin-bottom: 4px; border: 1px solid transparent; }}
.thesis-item:hover {{ background: var(--bg-hover); border-color: var(--border); }}
.thesis-item .ti-headline {{ font-size: 12px; font-weight: 500; line-height: 1.4; color: #CBD5E1; margin-bottom: 4px; }}
.thesis-item .ti-meta {{ display: flex; align-items: center; gap: 6px; }}
.thesis-item .ti-id {{ font-size: 9px; color: var(--text-dim); font-family: 'JetBrains Mono', monospace; }}
.thesis-empty {{ padding: 20px; text-align: center; color: var(--text-dim); font-size: 12px; }}

/* Empty state */
.graph-hint {{
  position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
  background: rgba(30,41,59,0.9); border: 1px solid var(--border); border-radius: 20px;
  padding: 8px 16px; font-size: 11px; color: var(--text-muted); backdrop-filter: blur(8px);
  display: flex; align-items: center; gap: 6px; pointer-events: none;
}}
.graph-hint svg {{ width: 14px; height: 14px; color: var(--accent); }}
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-title">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v6m0 10v6m11-11h-6m-10 0H1m15.5-7.5l-4.2 4.2m-6.6 6.6l-4.2 4.2m0-15l4.2 4.2m6.6 6.6l4.2 4.2"/></svg>
    <h1>AI-Invest Knowledge Graph</h1>
    <span class="week">{WEEK}</span>
  </div>
  <div class="stats">
    <div class="stat-card">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="#60A5FA" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
      <div class="stat-text"><span class="value">{len(nodes)}</span><span class="label">Nodes</span></div>
    </div>
    <div class="stat-card">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="#F87171" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
      <div class="stat-text"><span class="value">{len(rels)}</span><span class="label">Edges</span></div>
    </div>
    <div class="stat-card">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="#FBBF24" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
      <div class="stat-text"><span class="value">{label_counts.get('Thesis',0)}</span><span class="label">Theses</span></div>
    </div>
    <div class="stat-card">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
      <div class="stat-text"><span class="value" style="color:#34D399">{sig_counts.get('signal',0)}</span><span class="label">Signal</span></div>
    </div>
  </div>
</div>

<div class="main">
  <div class="sidebar">
    <div class="sidebar-section">
      <h3>Node Types</h3>
      <div id="label-filters"></div>
    </div>
    <div class="sidebar-section">
      <h3>Thesis Signal</h3>
      <div id="signal-filters">
        <div class="filter-item" data-signal="signal"><input type="checkbox" checked><span class="color-dot" style="background:#34D399"></span><span class="name">Signal</span><span class="count">{sig_counts.get('signal',0)}</span></div>
        <div class="filter-item" data-signal="weak_signal"><input type="checkbox" checked><span class="color-dot" style="background:#FBBF24"></span><span class="name">Weak Signal</span><span class="count">{sig_counts.get('weak_signal',0)}</span></div>
        <div class="filter-item" data-signal="noise"><input type="checkbox" checked><span class="color-dot" style="background:#475569"></span><span class="name">Noise</span><span class="count">{sig_counts.get('noise',0)}</span></div>
      </div>
    </div>
    <div class="sidebar-section">
      <h3>Actions</h3>
      <div class="sidebar-actions">
        <button class="btn" onclick="network.fit()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>Fit</button>
        <button class="btn" onclick="togglePhysics()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>Physics</button>
      </div>
    </div>
    <div class="legend">
      Click a <strong style="color:#60A5FA">Thesis</strong> node to view full detail.<br>
      Headline shown on node; full thesis in panel.<br>
      Scroll to zoom &middot; Drag to pan &middot; Drag nodes to reposition.
    </div>
  </div>
  <div class="graph-container">
    <div id="graph"></div>
    <div class="graph-hint">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
      Click any node to inspect details
    </div>
    <div class="detail-panel" id="detail-panel">
      <span class="detail-close" onclick="document.getElementById('detail-panel').style.display='none'">&times;</span>
      <div id="detail-content"></div>
    </div>
  </div>
</div>

<script>
const allNodes = new vis.DataSet({nodes_json});
const allEdges = new vis.DataSet({edges_json});

const container = document.getElementById('graph');
const data = {{ nodes: allNodes, edges: allEdges }};
const options = {{
  nodes: {{ shape: 'dot', borderWidth: 2, shadow: {{enabled: true, color: 'rgba(0,0,0,0.5)', size: 8, x: 0, y: 2}} }},
  edges: {{ width: 1, hoverWidth: 1.5, selectionWidth: 2 }},
  physics: {{
    enabled: true,
    barnesHut: {{ gravitationalConstant: -4000, centralGravity: 0.2, springLength: 160, springConstant: 0.04, damping: 0.4 }},
    stabilization: {{ iterations: 300 }}
  }},
  interaction: {{ hover: true, tooltipDelay: 200, zoomView: true, dragView: true, dragNodes: true, navigationButtons: false, keyboard: true }},
  layout: {{ improvedLayout: true, clusterThreshold: 150 }}
}};
const network = new vis.Network(container, data, options);

// Build label filters
const labelColors = {json.dumps(LABEL_COLORS, ensure_ascii=False)};
const labelCounts = {json.dumps(dict(label_counts), ensure_ascii=False)};
const labelFilterDiv = document.getElementById('label-filters');
Object.entries(labelCounts).forEach(([label, count]) => {{
  const color = labelColors[label] || '#6B7280';
  const div = document.createElement('div');
  div.className = 'filter-item';
  div.dataset.label = label;
  // Thesis nodes are colored by signal (green/yellow/gray), not by label color
  const dotHtml = label === 'Thesis'
    ? '<span class="color-dots"><span class="dot" style="background:#34D399"></span><span class="dot" style="background:#FBBF24"></span><span class="dot" style="background:#475569"></span></span>'
    : `<span class="color-dot" style="background:${{color}}"></span>`;
  div.innerHTML = `<input type="checkbox" checked>${{dotHtml}}<span class="name">${{label}}</span><span class="count">${{count}}</span>`;
  labelFilterDiv.appendChild(div);
}});

function applyFilters() {{
  const activeLabels = new Set();
  document.querySelectorAll('#label-filters .filter-item').forEach(item => {{
    if (item.querySelector('input').checked) activeLabels.add(item.dataset.label);
  }});
  const activeSignals = new Set();
  document.querySelectorAll('#signal-filters .filter-item').forEach(item => {{
    if (item.querySelector('input').checked) activeSignals.add(item.dataset.signal);
  }});
  allNodes.forEach(node => {{
    let visible = activeLabels.has(node.group);
    if (node.group === 'Thesis' && node.signal_class) {{
      visible = visible && activeSignals.has(node.signal_class);
    }}
    allNodes.update({{ id: node.id, hidden: !visible }});
  }});
}}
document.querySelectorAll('.filter-item input').forEach(cb => cb.addEventListener('change', applyFilters));

function togglePhysics() {{
  const enabled = !network.options.physics.enabled;
  network.setOptions({{ physics: {{ enabled }} }});
}}

// Node click -> detail panel
network.on('click', function(params) {{
  if (params.nodes.length > 0) {{
    const nodeId = params.nodes[0];
    const node = allNodes.get(nodeId);
    const panel = document.getElementById('detail-panel');
    const content = document.getElementById('detail-content');

    if (node.is_thesis && node.full_props) {{
      try {{
        const props = JSON.parse(node.full_props);
        content.innerHTML = renderThesisDetail(props);
      }} catch(e) {{
        content.innerHTML = '<div class="detail-simple"><h2>Parse Error</h2><p style="color:#F87171;font-size:12px">' + e.message + '</p></div>';
      }}
    }} else if (node.group === 'Company') {{
      content.innerHTML = renderCompanyDetail(node);
    }} else {{
      let html = '<div class="detail-simple"><h2>' + node.group + ': ' + node.id.split(':').slice(1).join(':') + '</h2>';
      if (node.full_props) {{
        try {{
          const props = JSON.parse(node.full_props);
          for (const [k, v] of Object.entries(props)) {{
            if (k === 'domain' || !v) continue;
            html += '<div class="field-row"><div class="field-key">' + k + '</div><div class="field-val">' + String(v) + '</div></div>';
          }}
        }} catch(e) {{}}
      }}
      html += '</div>';
      content.innerHTML = html;
    }}
    panel.style.display = 'block';
    document.querySelector('.graph-hint').style.display = 'none';
  }}
}});

function renderThesisDetail(props) {{
  const clean = (s) => (s || '');
  const headline = clean(props.headline);
  const claim = clean(props.claim);
  const thesisId = props.thesis_id || '';
  const ticker = props.ticker || '';
  const sigClass = props.signal_classification || 'unknown';
  const sigColors = {{ signal: '#34D399', weak_signal: '#FBBF24', noise: '#475569' }};
  const sigLabels = {{ signal: 'Signal', weak_signal: 'Weak', noise: 'Noise' }};
  const sigColor = sigColors[sigClass] || '#475569';
  const sigLabel = sigLabels[sigClass] || sigClass;
  const direction = props.direction || '';
  const dirClass = direction === 'bull' ? 'badge-bull' : 'badge-bear';

  const sections = [
    {{ name: 'Signal & Direction', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>', fields: ['direction','signal_classification','signal_strength','strength','status','semantic_label'] }},
    {{ name: 'Market Context', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>', fields: ['demand_wave','stack_position','chokepoint','mispricing_reason'] }},
    {{ name: 'Catalysts & Risk', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>', fields: ['catalysts','risks','tracking_metrics','falsifiers','horizon','expected_event'] }},
    {{ name: 'Evidence', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>', fields: ['supporting_evidence','contradicting_evidence','evidence_type','evidence_level'] }},
    {{ name: 'Metadata', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>', fields: ['thesis_id','ticker','updated_date','source_type','refresh_trigger','stale_after','obsidian_path'] }},
  ];

  const fmtVal = (key, val) => {{
    if (!val || val === '[]' || val === '{{}}' || val === "''" || val === '""' || val === 'pending') return '<span style="color:#475569">—</span>';
    try {{
      const parsed = JSON.parse(val);
      if (Array.isArray(parsed)) {{
        if (!parsed.length) return '<span style="color:#475569">—</span>';
        return '<ul>' + parsed.map(i => '<li>' + clean(String(i)) + '</li>').join('') + '</ul>';
      }}
    }} catch(e) {{}}
    if (key === 'signal_classification' && sigColors[val]) {{
      return '<span class="badge badge-' + (val === 'signal' ? 'signal' : val === 'weak_signal' ? 'weak' : 'noise') + '">' + sigLabels[val] + '</span>';
    }}
    if (key === 'direction') {{
      return '<span class="badge ' + (val === 'bull' ? 'badge-bull' : 'badge-bear') + '">' + val.toUpperCase() + '</span>';
    }}
    return clean(String(val));
  }};

  let html = `
    <div class="detail-header">
      <div class="thesis-id">${{thesisId}}</div>
      <div class="ticker-row">
        <span class="ticker">${{ticker}}</span>
        <div class="badges">
          <span class="badge badge-${{sigClass === 'signal' ? 'signal' : sigClass === 'weak_signal' ? 'weak' : 'noise'}}">${{sigLabel}}</span>
          <span class="badge ${{dirClass}}">${{direction.toUpperCase()}}</span>
        </div>
      </div>
    </div>
    <div class="detail-headline">
      <div class="section-label"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h7"/></svg>Headline</div>
      <div class="headline-text">${{headline || '<span style=\\'color:#475569\\'>No headline</span>'}}</div>
    </div>
    <div class="detail-full">
      <details open>
        <summary>Full Thesis</summary>
        <div class="full-text">${{claim || '<span style=\\'color:#475569\\'>No claim text</span>'}}</div>
      </details>
    </div>
  `;

  sections.forEach(sec => {{
    let rows = '';
    sec.fields.forEach(key => {{
      if (props[key] !== undefined && props[key] !== '' && props[key] !== 'pending' && props[key] !== '[]' && props[key] !== '{{}}') {{
        rows += '<div class="field-row"><div class="field-key">' + key + '</div><div class="field-val">' + fmtVal(key, String(props[key])) + '</div></div>';
      }}
    }});
    if (rows) {{
      html += '<div class="detail-section"><div class="section-title">' + sec.icon + sec.name + '</div>' + rows + '</div>';
    }}
  }});

  return html;
}}

function renderCompanyDetail(node) {{
  const props = node.full_props ? JSON.parse(node.full_props) : {{}};
  const ticker = props.ticker || node.id.split(':').slice(1).join(':');
  const name = props.name || ticker;

  // Find all thesis nodes for this company
  const theses = [];
  allNodes.forEach(n => {{
    if (n.is_thesis && n.full_props) {{
      try {{
        const tp = JSON.parse(n.full_props);
        if (tp.ticker === ticker) {{
          theses.push({{ node: n, props: tp }});
        }}
      }} catch(e) {{}}
    }}
  }});

  const total = theses.length;
  const noise = theses.filter(t => t.props.signal_classification === 'noise').length;
  const signal = theses.filter(t => t.props.signal_classification === 'signal').length;
  const weak = theses.filter(t => t.props.signal_classification === 'weak_signal').length;
  const active = theses.filter(t => t.props.signal_classification !== 'noise');
  const bull = active.filter(t => t.props.direction === 'bull').length;
  const bear = active.filter(t => t.props.direction === 'bear').length;
  const neutral = active.length - bull - bear;
  const net = bull - bear;
  const netPct = active.length > 0 ? Math.round((net / active.length) * 100) : 0;
  const bullPct = active.length > 0 ? Math.round((bull / active.length) * 100) : 0;
  const bearPct = active.length > 0 ? Math.round((bear / active.length) * 100) : 0;
  const neutralPct = active.length > 0 ? Math.round((neutral / active.length) * 100) : 0;

  const netColor = net > 0 ? 'var(--bull)' : net < 0 ? 'var(--bear)' : 'var(--text-dim)';
  const netLabel = net > 0 ? `Bullish +${{net}} (${{netPct}}%)` : net < 0 ? `Bearish ${{net}} (${{netPct}}%)` : 'Neutral';

  let html = `
    <div class="company-header">
      <div class="ticker">${{ticker}}</div>
      <div class="name">${{name}}</div>
    </div>
    <div class="summary-stats">
      <div class="summary-stat"><div class="num">${{total}}</div><div class="lbl">Total</div></div>
      <div class="summary-stat"><div class="num" style="color:var(--bull)">${{bull}}</div><div class="lbl">Bull</div></div>
      <div class="summary-stat"><div class="num" style="color:var(--bear)">${{bear}}</div><div class="lbl">Bear</div></div>
      <div class="summary-stat"><div class="num" style="color:#34D399">${{signal}}</div><div class="lbl">Signal</div></div>
      <div class="summary-stat"><div class="num" style="color:#FBBF24">${{weak}}</div><div class="lbl">Weak</div></div>
      <div class="summary-stat"><div class="num" style="color:#475569">${{noise}}</div><div class="lbl">Noise</div></div>
    </div>
    <div class="sentiment-bar">
      <div class="bar-label"><span>Sentiment (excl. noise)</span><span>${{bull}} bull / ${{bear}} bear / ${{neutral}} neutral</span></div>
      <div class="bar-track">
        <div class="bar-bull" style="width:${{bullPct}}%"></div>
        <div class="bar-neutral" style="width:${{neutralPct}}%"></div>
        <div class="bar-bear" style="width:${{bearPct}}%"></div>
      </div>
      <div class="net-label" style="color:${{netColor}}">${{netLabel}}</div>
    </div>
  `;

  if (theses.length === 0) {{
    html += '<div class="thesis-empty">No theses found for this company this week.</div>';
  }} else {{
    html += '<div class="thesis-list"><div class="list-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:11px;height:11px"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>Theses (${{total}})</div>';
    // Sort: signal first, then weak, then noise; within each, bull before bear
    const order = {{ signal: 0, weak_signal: 1, noise: 2 }};
    theses.sort((a, b) => {{
      const sa = order[a.props.signal_classification] || 99;
      const sb = order[b.props.signal_classification] || 99;
      if (sa !== sb) return sa - sb;
      if (a.props.direction === 'bull' && b.props.direction !== 'bull') return -1;
      if (b.props.direction === 'bull' && a.props.direction !== 'bull') return 1;
      return 0;
    }});
    theses.forEach(t => {{
      const tp = t.props;
      const sig = tp.signal_classification || 'unknown';
      const sigBadge = sig === 'signal' ? '<span class="badge badge-signal">Signal</span>' : sig === 'weak_signal' ? '<span class="badge badge-weak">Weak</span>' : '<span class="badge badge-noise">Noise</span>';
      const dirBadge = tp.direction === 'bull' ? '<span class="badge badge-bull">BULL</span>' : tp.direction === 'bear' ? '<span class="badge badge-bear">BEAR</span>' : '';
      const headline = tp.headline || tp.claim || tp.thesis_id || '(no headline)';
      const opacity = sig === 'noise' ? '0.5' : '1';
      html += `<div class="thesis-item" style="opacity:${{opacity}}" onclick="showThesisById('${{tp.thesis_id}}')">
        <div class="ti-headline">${{headline}}</div>
        <div class="ti-meta">${{sigBadge}}${{dirBadge}}<span class="ti-id">${{tp.thesis_id}}</span></div>
      </div>`;
    }});
    html += '</div>';
  }}

  return html;
}}

function showThesisById(thesisId) {{
  let found = null;
  allNodes.forEach(n => {{
    if (n.is_thesis && n.full_props) {{
      try {{
        const tp = JSON.parse(n.full_props);
        if (tp.thesis_id === thesisId) found = n;
      }} catch(e) {{}}
    }}
  }});
  if (found) {{
    const props = JSON.parse(found.full_props);
    document.getElementById('detail-content').innerHTML = renderThesisDetail(props);
    network.selectNodes([found.id]);
    network.focus(found.id, {{ scale: 1.5, animation: {{ duration: 500, easingFunction: 'easeInOutQuad' }} }});
  }}
}}

network.once('stabilizationIterationsDone', function() {{
  network.setOptions({{ physics: {{ enabled: false }} }});
  network.fit({{ animation: {{ duration: 500, easingFunction: 'easeInOutQuad' }} }});
}});
</script>
</body>
</html>"""


def main() -> int:
    if not GRAPH_JSON.exists():
        print(f"ERROR: graph JSON not found: {GRAPH_JSON}")
        print("Run build_graph_json.py first.")
        return 1

    graph = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
    html = build_html(graph)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Generated: {OUT_HTML}")
    print(f"  Nodes: {len(graph['nodes'])}, Edges: {len(graph['rels'])}")
    print(f"  Size: {OUT_HTML.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
