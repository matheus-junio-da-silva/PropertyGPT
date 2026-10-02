# Corpus expansion research

Research inventory captured on 2026-10-01 against PropertyGPT baseline
`24a80982a6d3d69ad70a114490847d4cccc0609e`.

## Published artifacts

- `sources.json`: upstream repositories, immutable commits, report URLs and scope caveats.
- `baseline.json`: SHA-256 inventory of 2,615 baseline files.
- `manifest.json`: provenance, size, license labels and hashes of 1,524 locally
  materialized snapshot files from seven pinned sources.
- `summary.json`: acquisition-time inventory, deduplication and evidence hashes.
- `evidence/*.commit.json`, `evidence/*.links.json`, `evidence/acquisition.json`:
  public commit metadata, PDF link annotations and acquisition records.
- Python scripts: acquisition, evidence extraction and inventory verification.
- `snapshots/`: all 1,524 materialized source, specification, configuration and
  license files at the recorded upstream commits.
- `archives/`: the seven original repository archives.
- `evidence/*.pdf` and `evidence/*.txt`: collected reports and extracted text.

Counts describe files and content hashes, not semantic properties or successful
formal proofs. The 32 specification files contain 26 contents new to the baseline.
Supplemental public snapshots are not asserted to be audited. The historical Aave
V4 Hub snapshot is report-cited context, not the final verified revision.

## Upstream material and licensing

`archives/`, `snapshots/`, PDF reports and their extracted full text are bundled
in the repository. A fresh clone contains the materialized research collection;
downloads are needed only to reproduce acquisition or restore missing files.

Snapshots contain mixed MIT, Apache, GPL, LGPL, AGPL, BUSL/LicenseRef-BUSL,
unspecified and UNLICENSED labels. In particular, the Compound snapshot has three
UNLICENSED test files and Euler has `test/unit/evault/POC.t.sol` marked UNLICENSED.
License labels are extraction results, not a license grant or a legal determination.
Consult each pinned upstream license and file notice before reuse or redistribution.
Original license files and source notices are retained. Inclusion here does not
relicense upstream material. Archives preserve the original downloads (about 42 MB).

## Reproduce and verify

Run from the PropertyGPT repository root with Python 3 and network access to GitHub
and the report hosts:

```sh
python3 corpus_expansion/research.py collect
python3 corpus_expansion/research.py verify
python3 corpus_expansion/research.py reports
uv run --with pypdf==6.1.1 python corpus_expansion/pdf_evidence.py
```

`collect` downloads the pinned archives and materializes selected source, spec,
configuration and license files without executing downloaded project code. It
rewrites `manifest.json`; compare it with the committed manifest and retain the
original expected hashes when checking a new acquisition. Upstream archive bytes
or report URLs may change or become unavailable despite immutable source commits.
Compare downloaded archive hashes to the committed `archive_sha256` values and
PDF/evidence hashes to `summary.json` before accepting a reproduction.

`verify` requires local snapshots and archives: it checks the baseline and snapshot
content hashes and all seven archive hashes. It does not verify PDF evidence.
`summarize.py` additionally checks archive-member correspondence and rewrites the
summary. `capture_provenance.py` re-fetches commit metadata, checks PDF equality and
rewrites acquisition timestamps; it is not needed to verify the saved inventory.
Do not regenerate `baseline.json` for routine verification.
