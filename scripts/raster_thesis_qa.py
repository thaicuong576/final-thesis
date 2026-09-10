"""Rasterize the Word-exported PDF for per-page visual QA."""
from pathlib import Path
import json
import pypdfium2 as pdfium
import pdfplumber

root = Path(__file__).resolve().parents[1]
out = root / 'reports/thesis-essay-20260910/render'
pdf = pdfium.PdfDocument(out / 'THESIS-DRAFT-VI.pdf')
layout = pdfplumber.open(out / 'THESIS-DRAFT-VI.pdf')
pages = []
for i, page in enumerate(pdf, 1):
    image = page.render(scale=120/72).to_pil()
    image.save(out / f'page-{i}.png')
    lp = layout.pages[i-1]
    content = lp.extract_text()
    assert content, f'Blank page {i}'
    assert all(c['x0'] >= 65 and c['x1'] <= lp.width - 65 for c in lp.chars), f'Horizontal overflow {i}'
    pages.append({'page': i, 'text_chars': len(content),
                  'first_line': content.splitlines()[0],
                  'last_line': content.splitlines()[-1],
                  'fonts': sorted({c['fontname'] for c in lp.chars})})
(out.parent / 'pagination-check.json').write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'pages': len(pdf), 'all_pages_nonblank': True, 'bounds': 'passed', 'details': pages}, ensure_ascii=True))
