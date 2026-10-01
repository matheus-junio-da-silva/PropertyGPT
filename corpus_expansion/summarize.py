"""Compute research inventory and validate archive-to-snapshot correspondence.

Counts files/content hashes, not semantic properties or successful proofs.
Only reads downloaded sources; does not execute them.
"""
import collections
import json
import re
import tarfile

from research import ROOT, REPO, sha, save_json, verify


def main():
    verify()
    baseline = json.loads((ROOT / 'baseline.json').read_text())
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    baseline_hashes = {f['sha256'] for f in baseline['files']}
    result = {
        'baseline_commit': baseline['commit'],
        'baseline_manifest_sha256': sha((ROOT / 'baseline.json').read_bytes()),
        'baseline_files': len(baseline['files']),
        'baseline_unique_contents': len(baseline_hashes),
        'baseline_extensions': baseline['extensions'],
        'counts': manifest['counts'],
        'sources': [],
        'evidence': [],
    }
    for source in manifest['sources']:
        files = [f for f in manifest['files'] if f['source'] == source['id']]
        by_path = {f['source_path']: f for f in files}
        archive_path = ROOT / 'archives' / (source['id'] + '-' + source['commit'] + '.tar.gz')
        matched = set()
        with tarfile.open(archive_path, 'r:gz') as archive:
            for member in archive:
                rel = '/'.join(member.name.split('/')[1:])
                if member.isfile() and rel in by_path:
                    assert sha(archive.extractfile(member).read()) == by_path[rel]['sha256'], rel
                    matched.add(rel)
        assert matched == set(by_path)
        specs = [f for f in files if f['kind'] in {'.spec', '.cvl'}]
        # A lexical sanity check only: not a CVL parser or proof validation.
        declarations = []
        for f in specs:
            text = (REPO / f['path']).read_text()
            text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
            if re.search(r'\b(rule|invariant|methods|ghost|hook)\b', text):
                declarations.append(f['source_path'])
        result['sources'].append({
            'id': source['id'], 'repo': source['repo'], 'commit': source['commit'],
            'files': len(files), 'bytes': sum(f['bytes'] for f in files),
            'extensions': dict(collections.Counter(f['kind'] for f in files)),
            'unique_contents_within_snapshot': len({f['sha256'] for f in files}),
            'incremental_new_contents': sum(f['duplicate_of'] is None for f in files),
            'duplicates_against_baseline': sum(f['sha256'] in baseline_hashes for f in files),
            'duplicates_against_expansion_only': sum(f['duplicate_of'] is not None and f['sha256'] not in baseline_hashes for f in files),
            'spec_files': len(specs),
            'spec_files_with_cvl_declaration_tokens': len(declarations),
            'cvl_examples': declarations[:3],
            'license_files': [f['source_path'] for f in files if re.match(r'(?i)^(license|copying|notice)', f['source_path'].split('/')[-1])],
            'license_labels': dict(collections.Counter(label for f in files for label in f['license'])),
            'archive_sha256': source['archive_sha256'],
        })
    for path in sorted((ROOT / 'evidence').iterdir()):
        if path.is_file():
            result['evidence'].append({'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())})
    result['snapshots_with_cvl'] = sum(s['spec_files_with_cvl_declaration_tokens'] > 0 for s in result['sources'])
    result['new_unique_cvl_contents'] = len({f['sha256'] for f in manifest['files'] if f['kind'] in {'.spec', '.cvl'} and f['sha256'] not in baseline_hashes})
    result['combined_files'] = len(baseline['files']) + len(manifest['files'])
    result['combined_unique_contents'] = len(baseline_hashes | {f['sha256'] for f in manifest['files']})
    result['verification'] = 'baseline, snapshots and archive SHA-256 passed; all manifest snapshot bytes match archive members'
    assert not manifest['failures'], manifest['failures']
    assert result['snapshots_with_cvl'] >= 3
    save_json(ROOT / 'summary.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
