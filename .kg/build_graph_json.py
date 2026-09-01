#!/usr/bin/env python3
"""Build a deterministic Neo4j import projection from AI-Invest Markdown."""
from __future__ import annotations
import json, re
from datetime import date
from pathlib import Path

V = Path(__file__).resolve().parent.parent  # vault root (auto-detect from script location)
OUT = V / '.kg' / f"graph-invest-{date.today().isocalendar().year}-W{date.today().isocalendar().week:02d}.json"
PK = {'Thesis':'thesis_id','Assumption':'assumption_id','Evidence':'evidence_id','Company':'name','Concept':'name','Product':'name','Person':'name','Event':'name','Source':'name'}
def fm(p):
 t=p.read_text(encoding='utf8',errors='replace'); m=re.match(r'^---\s*\n(.*?)\n---',t,re.S); d={}
 if m:
  for k,v in re.findall(r'^([A-Za-z_]+):\s*(.*)$',m.group(1),re.M): d[k]=v.strip().strip('"\'')
 return d,t
def add(nodes, label, key, props):
 if key: nodes[(label,key)]={'label':label,'primary_key_value':key,'properties':{'domain':'invest',**props}}
def main():
 nodes={}; rels=[]
 for folder,label,keyfield in [(V/'40_Thesis'/'theses','Thesis','thesis_id'),(V/'40_Thesis'/'discovery','Thesis','thesis_id'),(V/'40_Thesis'/'assumptions','Assumption','assumption_id')]:
  for p in folder.glob('*.md'):
   d,t=fm(p); key=d.get(keyfield); add(nodes,label,key,{**d,'obsidian_path':str(p.relative_to(V))})
   ticker=d.get('ticker')
   if ticker:
    add(nodes,'Company',ticker,{'name':ticker,'ticker':ticker}); rels.append({'src':{'label':label,'key':key},'dst':{'label':'Company','key':ticker},'type':'ABOUT','properties':{'domain':'invest'}})
   for sid in re.findall(r'EVIDENCE-[A-Za-z0-9_-]+',d.get('supporting_evidence','')):
    rels.append({'src':{'label':label,'key':key},'dst':{'label':'Evidence','key':sid},'type':'CITES','properties':{'domain':'invest'}})
 for p in (V/'30_Wiki'/'Sources').glob('EVIDENCE-*.md'):
  d,_=fm(p); eid=d.get('evidence_id'); add(nodes,'Evidence',eid,{**d,'obsidian_path':str(p.relative_to(V))})
  sid=d.get('source_id')
  if sid:
   add(nodes,'Source',sid,{'name':sid}); rels.append({'src':{'label':'Evidence','key':eid},'dst':{'label':'Source','key':sid},'type':'FROM_SOURCE','properties':{'domain':'invest'}})
 for name in ('news','article','google_news','x','podcast','substack','filings','macro','website'):
  for p in (V/'20_Raw'/name).glob('*.md'):
   d,_=fm(p);
   if d.get('source_type') in {'project_spec','local_spec','documentation','github_repository','video_note'}: continue
   sid=d.get('source_id',p.stem); add(nodes,'Source',sid,{'name':sid,**d,'obsidian_path':str(p.relative_to(V))})
 OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps({'nodes':list(nodes.values()),'rels':rels},ensure_ascii=False,indent=2),encoding='utf8'); print(OUT)
if __name__=='__main__': main()
