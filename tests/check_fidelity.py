"""Fail publication if this public paper loses a verified image or reading order."""
import hashlib
import json
import os
import re
from pathlib import Path

os.environ['PAPER_READER_LIBRARY'] = '/tmp/acceptance-library'
os.environ['PAPERCUT_READER_ONLY'] = '1'
os.environ['PAPERCUT_WORKER'] = '0'  # This isolated check calls the parser directly.
os.environ['PAPERCUT_CROP_DPI'] = '300'
from app import library
from app.parse import parse_paper

baseline=json.loads(Path('/checks/acceptance-baseline.json').read_text())
pdf=Path('/fixtures/paper.pdf')
assert hashlib.sha256(pdf.read_bytes()).hexdigest()==baseline['pdf_sha256'], 'Public test PDF changed'
pid=library.ingest(pdf,'acceptance-paper.pdf')
paper=parse_paper(pid,lambda stage,fraction:print(stage,round(fraction,3),flush=True))

def label(caption):
    match=re.match(r'(Figure|TABLE)\s+(\d+)\s*:',caption,re.I)
    assert match,caption
    return match[1].lower(),int(match[2])

expected={(item['label'].split()[0],int(item['label'].split()[1])):item for item in baseline['assets']}
actual={}
from PIL import Image
for block in paper['blocks']:
    if block['type'] not in ('figure','table') or not block.get('image'):
        continue
    caption=' '.join(paper['sentences'][sid]['text'] for sid in block.get('caption_sentences',[]))
    key=label(caption)
    assert key not in actual, f'Duplicate figure/table {key}'
    path=library.paper_dir(pid)/block['image']
    with Image.open(path) as image:
        dimensions=list(image.size)
        image.verify()
    actual[key]={'page':block['page'],'pixels':dimensions,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                 'caption_sha256':hashlib.sha256(caption.encode()).hexdigest()}
assert set(actual)==set(expected), {'expected':list(expected),'actual':list(actual)}
for key,item in expected.items():
    for field in ('page','pixels','sha256','caption_sha256'):
        assert actual[key][field]==item[field], (key,field,actual[key][field],item[field])
references=[b for b in paper['blocks'] if b['type']=='references']
assert len(references)==baseline['reference_entries'],len(references)
texts=[' '.join(paper['sentences'][sid]['text'] for sid in b.get('sentences',[])) for b in paper['blocks']]
paragraph_hashes={hashlib.sha256(text.encode()).hexdigest() for text in texts}
assert set(baseline['reading_order_sha256']).issubset(paragraph_hashes), 'Reading-order checkpoint changed'
for number in range(1,9):
    assert any(b['type']=='heading' and re.match(str(number)+r'\.\s',b['text']) for b in paper['blocks']),number
print(json.dumps({'result':'PASS','images':len(actual),'references':len(references),'pdf_sha256':baseline['pdf_sha256']},indent=2))
