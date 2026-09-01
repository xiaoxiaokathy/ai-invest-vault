#!/usr/bin/env python3
from __future__ import annotations
import json, os, re
from pathlib import Path
from urllib.parse import urlparse
from neo4j import GraphDatabase
V=Path(__file__).resolve().parent.parent  # vault root (auto-detect from script location)
W=__import__('datetime').date.today().isocalendar(); P=V/'.kg'/f'graph-invest-{W.year}-W{W.week:02d}.json'
LABELS={'Thesis':'thesis_id','Assumption':'assumption_id','Evidence':'evidence_id','Company':'name','Concept':'name','Product':'name','Person':'name','Event':'name','Source':'name'}
REL_TYPES={'ABOUT','CITES','MENTIONS','SUPPORTS','CONTRADICTS','RELATED_TO','PRODUCES','COMPETES_WITH','FROM_SOURCE'}

def dsn():
 value=os.environ.get('NEO4J_DSN')
 if value: return value
 for line in (Path('D:/dxx/agentic-kg/.env')).read_text(encoding='utf8').splitlines():
  if line.startswith('NEO4J_DSN='): return line.split('=',1)[1].strip().strip('"')
 raise RuntimeError('NEO4J_DSN is not configured')

def main():
 d=json.loads(P.read_text(encoding='utf8')); u=urlparse(dsn()); driver=GraphDatabase.driver(f'{u.scheme}://{u.hostname}:{u.port or 7687}',auth=(u.username,u.password))
 domain=os.environ.get('KG_DOMAIN','invest')
 with driver.session(database='neo4j') as s:
  for label,key in LABELS.items():
   s.run(f'CREATE CONSTRAINT invest_{label.lower()}_identity IF NOT EXISTS FOR (n:`{label}`) REQUIRE (n.domain, n.`{key}`) IS UNIQUE')
  for n in d['nodes']:
   label=n['label'];
   if label not in LABELS: raise ValueError(f'unsupported node label: {label}')
   key=LABELS[label]; props={k:v for k,v in n['properties'].items() if k != 'domain'}; props[key]=n['primary_key_value']; props['domain']=domain
   s.run(f'MERGE (n:`{label}` {{domain:$domain, `{key}`:$key}}) SET n += $props',domain=domain,key=n['primary_key_value'],props=props)
  for r in d['rels']:
   src,dst=r['src'],r['dst']; typ=r['type']
   if src['label'] not in LABELS or dst['label'] not in LABELS or typ not in REL_TYPES: raise ValueError('unsupported graph relationship')
   sk=LABELS[src['label']]; dk=LABELS[dst['label']]
   q=f'MATCH (a:`{src["label"]}` {{domain:$d, `{sk}`:$sk}}),(b:`{dst["label"]}` {{domain:$d, `{dk}`:$dk}}) MERGE (a)-[x:`{typ}` {{domain:$d}}]->(b) SET x += $p'
   props={k:v for k,v in r.get('properties',{}).items() if k != 'domain'}; props['domain']=domain
   s.run(q,d=domain,sk=src['key'],dk=dst['key'],p=props)
  count=s.run('MATCH (n {domain:$d}) RETURN count(n) AS n',d=domain).single()['n']
 driver.close(); print(json.dumps({'nodes_loaded':len(d['nodes']),'rels_loaded':len(d['rels']),'graph_nodes':count}))
if __name__=='__main__': main()
