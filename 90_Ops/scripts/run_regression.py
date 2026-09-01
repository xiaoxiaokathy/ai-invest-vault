#!/usr/bin/env python3
"""Private regression test for S9/S7/S8; creates and removes only TEST-* artifacts."""
from pathlib import Path
from datetime import date
import json, os, subprocess
V=Path(__file__).resolve().parent.parent.parent; py=Path('D:/dxx/agentic-kg/.venv/Scripts/python.exe'); raw=V/'20_Raw'/'website'; inbox=V/'.kg'/'atomic'/'inbox'; thesis=V/'40_Thesis'/'theses'; q=V/'90_Ops'/'quarantine'
evidence=V/'30_Wiki'/'Sources'
raw.mkdir(parents=True,exist_ok=True); inbox.mkdir(parents=True,exist_ok=True)
week=f'{date.today().isocalendar().year}-W{date.today().isocalendar().week:02d}'
report_path=V/'.kg'/'atomic'/f'report-{week}.json'; quarantine_path=q/f'atomic-{week}.jsonl'
graph_path=V/'.kg'/f'graph-invest-{week}.json'
prior_report=report_path.read_bytes() if report_path.exists() else None
prior_quarantine=quarantine_path.read_bytes() if quarantine_path.exists() else None
prior_graph=graph_path.read_bytes() if graph_path.exists() else None
before_theses={p.name for p in thesis.glob('THESIS-*.md')}
before_evidence={p.name for p in evidence.glob('EVIDENCE-*.md')}
source=raw/'TEST-RAW-001.md'; source.write_text('---\nsource_id: TEST-RAW-001\nsource_type: website\nevidence_level: primary_source\nupdated_date: 2026-08-27\nsource_url: https://example.test\nrelated_links: ""\nkey_insight: test\nnext_action: test\n---\n\nDemand increased materially. Supply constraints worsened.\n',encoding='utf8')
rows=[{'ticker':'TEST','direction':'bull','claim':'Demand increased materially implies upside.','quote':'Demand increased materially.','source_id':'TEST-RAW-001'},{'ticker':'TEST','direction':'bull','claim':'Demand increased materially implies upside.','quote':'Demand increased materially.','source_id':'TEST-RAW-001'},{'ticker':'TEST','direction':'bear','claim':'Supply constraints worsened imply downside.','quote':'Supply constraints worsened.','source_id':'TEST-RAW-001'},{'ticker':'TEST2','direction':'bull','claim':'Demand increased materially supports a separate company read-through.','quote':'Demand increased materially.','source_id':'TEST-RAW-001'},{'ticker':'TEST','direction':'bear','claim':'Bad quote must quarantine.','quote':'not in raw','source_id':'TEST-RAW-001'}]
(inbox/'claims-TEST.json').write_text(json.dumps(rows),encoding='utf8')
try:
 # 清理 inbox 中非 TEST 文件（防止上次运行遗留）
 for p in inbox.glob('claims-*.json'):
  if 'TEST' not in p.name: p.unlink()
 subprocess.run([str(py),str(V/'.kg/atomic/atomic_pipeline.py')],check=True)
 report=json.loads(report_path.read_text(encoding='utf8'))
 assert report['new_bull']==2 and report['new_bear']==1 and report['quarantine_n']==1,report
 # v1.1: 无 semantic_label 的 claim 默认 keep_deweighted → 全部 pending（写入 discovery/）
 assert report.get('new_thesis_pending',0)==3,report
 assert report.get('new_thesis_active',0)==0,report
 assert any(p.name.startswith('THESIS-') for p in (V/'40_Thesis'/'discovery').glob('*.md'))
 subprocess.run([str(py),str(V/'.kg/build_graph_json.py')],check=True)
 subprocess.run([str(py),str(V/'.kg/load_kg.py')],check=True,env={**os.environ,'KG_DOMAIN':'invest_regression'})
 print('PASS G1/G2/G3/G5')
finally:
 for p in [source,inbox/'claims-TEST.json',inbox/'processed'/'claims-TEST.json']:
  p.unlink(missing_ok=True)
 for p in thesis.glob('THESIS-*.md'):
  if p.name not in before_theses: p.unlink()
 for p in (V/'40_Thesis'/'discovery').glob('THESIS-*.md'):
  if p.name not in before_theses: p.unlink()
 for p in evidence.glob('EVIDENCE-*.md'):
  if p.name not in before_evidence: p.unlink()
 if prior_report is None: report_path.unlink(missing_ok=True)
 else: report_path.write_bytes(prior_report)
 if prior_quarantine is None: quarantine_path.unlink(missing_ok=True)
 else: quarantine_path.write_bytes(prior_quarantine)
 if prior_graph is None: graph_path.unlink(missing_ok=True)
 else: graph_path.write_bytes(prior_graph)
