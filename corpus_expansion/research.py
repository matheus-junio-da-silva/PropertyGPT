"""Research-only corpus acquisition. Never executes downloaded project code."""
import argparse
import collections
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
BASE = '24a80982a6d3d69ad70a114490847d4cccc0609e'


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'PropertyGPT-corpus-research'}), timeout=120) as r:
        return r.read()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save_json(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(path)


def baseline():
    records = []
    names = subprocess.check_output(['git', 'ls-tree', '-rz', '--name-only', BASE], cwd=REPO).decode().split('\0')
    for name in filter(None, names):
        data = subprocess.check_output(['git', 'show', f'{BASE}:{name}'], cwd=REPO)
        records.append({'path': name, 'bytes': len(data), 'sha256': sha(data)})
    save_json(ROOT / 'baseline.json', {'commit': BASE, 'files': records,
        'extensions': dict(collections.Counter(Path(x['path']).suffix for x in records))})


def reports():
    for source in json.loads((ROOT / 'sources.json').read_text()):
        if not source.get('report_pdf'):
            continue
        dest = ROOT / 'evidence' / (source['id'] + '.pdf')
        dest.parent.mkdir(exist_ok=True)
        if not dest.exists():
            dest.write_bytes(fetch(source['report_pdf']))
        print(source['id'], sha(dest.read_bytes()))


def collect():
    base = json.loads((ROOT / 'baseline.json').read_text())
    known = {x['sha256']: 'baseline:' + x['path'] for x in base['files']}
    manifest = {'baseline_commit': BASE, 'sources': [], 'files': [], 'failures': []}
    for source in json.loads((ROOT / 'sources.json').read_text()):
        if 'commit' not in source:
            manifest['failures'].append({'id': source['id'], 'status': 'no_verified_pin'})
            continue
        try:
            commit = source['commit']
            if not re.fullmatch('[0-9a-f]{40}', commit):
                raise ValueError('Requires full immutable commit SHA')
            url = f"https://codeload.github.com/{source['repo']}/tar.gz/{commit}"
            cache = ROOT / 'archives' / (source['id'] + '-' + commit + '.tar.gz')
            cache.parent.mkdir(exist_ok=True)
            data = cache.read_bytes() if cache.exists() else fetch(url)
            if not cache.exists():
                cache.write_bytes(data)
            source = dict(source, archive_url=url, archive_sha256=sha(data), status='downloaded')
            manifest['sources'].append(source)
            with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
                for member in archive:
                    if not member.isfile():
                        continue
                    rel = Path(*Path(member.name).parts[1:])
                    if rel.is_absolute() or '..' in rel.parts:
                        raise ValueError('Unsafe archive path')
                    kind = rel.suffix.lower()
                    if kind not in {'.sol', '.spec', '.cvl', '.conf'} and not re.match(r'(?i)^(license|copying|notice)', rel.name):
                        continue
                    content = archive.extractfile(member).read()
                    digest = sha(content)
                    dest = ROOT / 'snapshots' / source['id'] / commit / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if dest.exists() and dest.read_bytes() != content:
                        raise ValueError(f'Local content differs: {dest}')
                    if not dest.exists():
                        dest.write_bytes(content)
                    spdx = re.findall(rb'SPDX-License-Identifier:\s*([^\r\n*]+)', content)
                    record = {'source': source['id'], 'commit': commit, 'path': str(dest.relative_to(REPO)),
                        'source_path': str(rel), 'url': f"https://github.com/{source['repo']}/blob/{commit}/{rel.as_posix()}",
                        'sha256': digest, 'bytes': len(content), 'kind': kind,
                        'license': [x.decode(errors='replace').strip() for x in spdx] or ['unspecified; consult snapshot license files'],
                        'status': 'materialized', 'duplicate_of': known.get(digest),
                        'audit_scope': source.get('audit_scope', 'repository context at report-cited commit; not every file individually audited')}
                    manifest['files'].append(record)
                    known.setdefault(digest, record['path'])
        except Exception as exc:
            manifest['failures'].append({'id': source['id'], 'status': 'failed', 'error': str(exc)})
        save_json(ROOT / 'manifest.json', manifest)
    manifest['counts'] = {'materialized_files': len(manifest['files']),
        'unique_new_contents': sum(x['duplicate_of'] is None for x in manifest['files']),
        'duplicate_contents': sum(x['duplicate_of'] is not None for x in manifest['files']),
        'extensions': dict(collections.Counter(x['kind'] for x in manifest['files'])),
        'failures': len(manifest['failures'])}
    save_json(ROOT / 'manifest.json', manifest)
    print(json.dumps(manifest['counts'], indent=2))


def verify():
    base = json.loads((ROOT / 'baseline.json').read_text())
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    for x in base['files'] + manifest['files']:
        assert sha((REPO / x['path']).read_bytes()) == x['sha256'], x['path']
    for source in manifest['sources']:
        archive = ROOT / 'archives' / (source['id'] + '-' + source['commit'] + '.tar.gz')
        assert sha(archive.read_bytes()) == source['archive_sha256']
    print(f"Verified {len(base['files'])} baseline files, {len(manifest['files'])} additions and {len(manifest['sources'])} archives")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['baseline', 'reports', 'collect', 'verify'])
    globals()[parser.parse_args().command]()
