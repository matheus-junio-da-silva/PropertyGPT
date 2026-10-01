"""Optional small PDF parser for provenance; run with uv --with pypdf==6.1.1."""
from pathlib import Path
import json
from pypdf import PdfReader

root = Path(__file__).resolve().parent / 'evidence'
for path in sorted(root.glob('*.pdf')):
    reader = PdfReader(path)
    text = '\n'.join(f'\nPAGE {i + 1}\n{page.extract_text()}' for i, page in enumerate(reader.pages))
    path.with_suffix('.txt').write_text(text)
    links = []
    for i, page in enumerate(reader.pages):
        for item in page.get('/Annots', []):
            action = item.get_object().get('/A', {})
            if action.get('/URI'):
                links.append({'page': i + 1, 'url': str(action['/URI'])})
    path.with_suffix('.links.json').write_text(json.dumps(links, indent=2) + '\n')
    print(path.name, len(reader.pages), 'pages', len(links), 'links')
