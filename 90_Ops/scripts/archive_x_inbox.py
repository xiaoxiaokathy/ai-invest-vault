#!/usr/bin/env python3
"""Deterministically archive collected X posts into write-once Raw documents."""
from __future__ import annotations
import hashlib, os, re
from datetime import date
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent  # vault root (auto-detect)
INBOX = Path(os.environ.get("HORIZON_X_INBOX", str(Path.home() / "projects" / "Horizon" / "data" / "x-inbox")))
OUT = VAULT / '20_Raw' / 'x'
POST = re.compile(r'^##\s+([^\s]+)\s+(https://x\.com/([^/]+)/status/(\d+))(?:\s+tweet_id=\d+)?\s*\n(.*?)(?=^##\s+|\Z)', re.M | re.S)

def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    written = 0
    for inbox in sorted(INBOX.glob('*.md')):
        text = inbox.read_text(encoding='utf8', errors='replace')
        for timestamp, url, handle, post_id, body in POST.findall(text):
            source_id = f'X-{post_id}'
            path = OUT / f'{source_id}.md'
            if path.exists():
                continue
            body = body.strip()
            digest = hashlib.sha256(body.encode('utf8')).hexdigest()
            published = timestamp[:10]
            path.write_text(
                f'---\nsource_id: {source_id}\nsource_url: {url}\nsource_type: x_tweet\n'
                f'evidence_level: primary_source\nupdated_date: {date.today()}\npublished_date: {published}\n'
                f'content_hash: {digest}\nrelated_links: ""\n'
                f'key_insight: Official post from @{handle}; raw text retained without investment inference.\n'
                f'next_action: Extract only quote-supported claims in a subsequent review.\n---\n\n# @{handle} — {published}\n\n{body}\n',
                encoding='utf8')
            written += 1
    print({'archived': written})
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
