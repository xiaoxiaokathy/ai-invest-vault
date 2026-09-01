#!/usr/bin/env python3
"""Generate per-company thesis overview section for the weekly report.

Reads all thesis files from discovery/ and theses/, groups by ticker,
and outputs a Markdown section listing each thesis with signal classification,
strength, and claim. Can be appended to the weekly report or printed to stdout.
"""
from __future__ import annotations
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

V = Path(__file__).resolve().parent.parent.parent  # vault root
WEEK = f"{date.today().isocalendar().year}-W{date.today().isocalendar().week:02d}"
DISCOVERY = V / "40_Thesis" / "discovery"
THESES = V / "40_Thesis" / "theses"
WEEKLY = V / "15_Weekly" / f"{WEEK}.md"

SIGNAL_EMOJI = {
    "signal": "🟢",
    "weak_signal": "🟡",
    "noise": "⚪",
}


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    d = {}
    for k, v in re.findall(r"^([A-Za-z_]+):\s*(.*)$", m.group(1), re.M):
        d[k] = v.strip().strip('"\'')
    return d


def load_all_theses() -> list[dict]:
    theses = []
    for folder in (DISCOVERY, THESES):
        if not folder.exists():
            continue
        for p in folder.glob("THESIS-*.md"):
            fm = parse_frontmatter(p)
            if fm.get("thesis_id"):
                fm["_path"] = str(p.relative_to(V))
                fm["_status_folder"] = folder.name
                theses.append(fm)
    return theses


def generate_overview(theses: list[dict]) -> str:
    by_ticker = defaultdict(list)
    for t in theses:
        by_ticker[t.get("ticker", "UNKNOWN")].append(t)

    lines = []
    lines.append("## Company Thesis Overview")
    lines.append("")
    lines.append(f"> Auto-generated from {len(theses)} thesis files in `40_Thesis/discovery/` + `40_Thesis/theses/`. ")
    lines.append(f"> Signal legend: 🟢 signal (对基本面有持续重大影响) · 🟡 weak_signal (有潜在影响但缺量化/验证) · ⚪ noise (不直接改变基本面，保留用于回溯)")
    lines.append("")

    # Summary table
    lines.append("### Summary")
    lines.append("")
    lines.append("| Ticker | Total | 🟢 signal | 🟡 weak_signal | ⚪ noise | Avg Strength |")
    lines.append("|--------|-------|-----------|----------------|----------|-------------|")
    for ticker in sorted(by_ticker.keys()):
        ts = by_ticker[ticker]
        sig = sum(1 for t in ts if t.get("signal_classification") == "signal")
        weak = sum(1 for t in ts if t.get("signal_classification") == "weak_signal")
        noise = sum(1 for t in ts if t.get("signal_classification") == "noise")
        strengths = [int(t.get("signal_strength", 0)) for t in ts if t.get("signal_strength", "").isdigit()]
        avg = sum(strengths) / len(strengths) if strengths else 0
        lines.append(f"| {ticker} | {len(ts)} | {sig} | {weak} | {noise} | {avg:.1f} |")
    lines.append("")

    # Per-company thesis list
    for ticker in sorted(by_ticker.keys()):
        ts = by_ticker[ticker]
        # Sort by signal strength descending, then signal_classification priority
        sig_priority = {"signal": 0, "weak_signal": 1, "noise": 2}
        ts.sort(key=lambda t: (
            sig_priority.get(t.get("signal_classification", "noise"), 3),
            -int(t.get("signal_strength", 0) or 0),
        ))

        lines.append(f"### {ticker}")
        lines.append("")
        for t in ts:
            sig_class = t.get("signal_classification", "unknown")
            emoji = SIGNAL_EMOJI.get(sig_class, "❓")
            strength = t.get("signal_strength", "?")
            thesis_id = t.get("thesis_id", "")
            claim = t.get("claim", "")
            # Clean up claim (remove arrow artifacts, truncate)
            claim = claim.replace("鈫?", "→").replace("鈫?", "→")
            if len(claim) > 200:
                claim = claim[:197] + "..."
            evidence_count = 0
            se = t.get("supporting_evidence", "[]")
            try:
                evidence_count = len(json.loads(se))
            except (json.JSONDecodeError, TypeError):
                pass

            lines.append(f"- {emoji} **{thesis_id}** `[{sig_class}|s={strength}]` — {claim}")
            lines.append(f"  - Evidence: {evidence_count} | Status: {t.get('status', '?')} | Path: `{t.get('_path', '')}`")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    theses = load_all_theses()
    if not theses:
        print("No thesis files found.")
        return 1

    overview = generate_overview(theses)

    # Print to stdout
    print(overview)

    # Append to weekly report if it exists (replace existing section if present)
    if WEEKLY.exists():
        report_text = WEEKLY.read_text(encoding="utf-8")
        # Remove existing Company Thesis Overview section
        report_text = re.sub(
            r"\n## Company Thesis Overview\n.*?(?=\n## |\Z)",
            "",
            report_text,
            flags=re.S,
        )
        # Append new section
        report_text = report_text.rstrip() + "\n\n" + overview + "\n"
        WEEKLY.write_text(report_text, encoding="utf-8")
        print(f"\n--- Appended to {WEEKLY} ---")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
