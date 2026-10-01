"""Retain public commit metadata and recheck the previously acquired PDFs."""
from datetime import datetime, timezone
import json

from research import ROOT, fetch, save_json, sha


records = []
for source in json.loads((ROOT / 'sources.json').read_text()):
    url = f"https://api.github.com/repos/{source['repo']}/git/commits/{source['commit']}"
    data = fetch(url)
    metadata = json.loads(data)
    assert metadata['sha'] == source['commit']
    path = ROOT / 'evidence' / (source['id'] + '.commit.json')
    path.write_bytes(data)
    record = {'id': source['id'], 'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
              'sha256': sha(data), 'commit_date': metadata['committer']['date']}
    if source.get('report_pdf'):
        pdf = fetch(source['report_pdf'])
        assert sha(pdf) == sha((ROOT / 'evidence' / (source['id'] + '.pdf')).read_bytes())
        record.update(report_pdf=source['report_pdf'], report_sha256=sha(pdf), report_matches_existing=True)
    records.append(record)
    save_json(ROOT / 'evidence' / 'acquisition.json', records)
    print(source['id'], 'public commit confirmed', record['commit_date'])
