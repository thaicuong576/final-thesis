"""Rasterize and check the illustrated Word export with bundled libraries."""
from pathlib import Path
import json
import re
import pypdfium2 as pdfium
import pdfplumber
from PIL import Image,ImageChops

root=Path(__file__).resolve().parents[1]
out=root/'reports/thesis-visuals-20260910/render'
pdf=pdfium.PdfDocument(out/'THESIS-DRAFT-VI.pdf')
layout=pdfplumber.open(out/'THESIS-DRAFT-VI.pdf')
details=[]
for i,page in enumerate(pdf,1):
    page.render(scale=120/72).to_pil().save(out/f'page-{i}.png')
    lp=layout.pages[i-1]
    content=lp.extract_text() or ''
    assert content or lp.images,f'Blank page {i}'
    assert all(c['x0']>=64 and c['x1']<=lp.width-64 for c in lp.chars),f'Text overflow {i}'
    assert all(im['x0']>=64 and im['x1']<=lp.width-64 for im in lp.images),f'Image overflow {i}'
    details.append({'page':i,'chars':len(content),'images':len(lp.images),
                    'captions':re.findall(r'(?:Hình|Bảng) \d\.\d[^\n]*',content),
                    'first_line':content.splitlines()[0] if content else '',
                    'last_line':content.splitlines()[-1] if content else ''})
alltext='\n'.join((p.extract_text() or '') for p in layout.pages)
assert len(pdf)>25
for cap in ['Bảng 3.1','Bảng 4.1','Bảng 6.1','Bảng 6.2','Bảng 6.3','Hình 4.1','Hình 4.2','Hình 5.1','Hình 5.2']:
    assert cap in alltext,cap
assert sum(len(p.images) for p in layout.pages)==4
figures=[]
for name in ['figure-4-1-architecture.png','figure-4-2-workflow.png']:
    im=Image.open(root/'docs/assets/thesis-visuals-20260910'/name).convert('RGB')
    r,g,b=im.split()
    figures.append({'file':name,'size':im.size,'max_channel_difference':max(ImageChops.difference(r,g).getextrema()[1],ImageChops.difference(g,b).getextrema()[1])})
result={'pages':len(pdf),'bounds':'passed','caption_presence':'passed','images':4,'diagrams':figures,'pagination':details}
(out.parent/'pagination-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'pages':len(pdf),'bounds':'passed','images':4,'diagrams':figures}))
