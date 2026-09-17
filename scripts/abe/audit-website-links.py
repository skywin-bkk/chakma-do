#!/usr/bin/env python3
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import sys

ROOT=Path('website')
MASTER={
'index.html','community.html','identity.html','history.html','villages.html','community-data.html','culture-heritage.html','gallery.html','language.html','people.html','directory.html','professionals.html','programs.html','education.html','youth.html','women-family.html','livelihoods.html','wellbeing.html','knowledge.html','opportunity-center.html','opportunities.html','services.html','library.html','community-life.html','updates.html','get-involved.html','participate.html','about.html','strategy.html','governance.html','departments.html','policies.html','contact.html','community-hub.html'
}
class P(HTMLParser):
 def __init__(self): super().__init__(); self.links=[]; self.ids=set()
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a: self.ids.add(a['id'])
  if tag in ('a','link','script','img'):
   for k in ('href','src'):
    if a.get(k): self.links.append(a[k])

def parse(path):
 p=P(); p.feed(path.read_text(encoding='utf-8')); return p

htmls=sorted(ROOT.glob('*.html')); parsed={p.name:parse(p) for p in htmls}; errors=[]
missing=sorted(MASTER-set(parsed))
if missing: errors.append('Missing master pages: '+', '.join(missing))
for path in htmls:
 src=parsed[path.name]
 for raw in src.links:
  if raw.startswith(('http://','https://','mailto:','tel:','javascript:','data:')): continue
  u=urlsplit(raw); rel=unquote(u.path)
  target=path if not rel else (path.parent/rel).resolve()
  try: target.relative_to(ROOT.resolve())
  except ValueError:
   errors.append(f'{path.name}: path escapes website: {raw}'); continue
  if rel and not target.exists():
   errors.append(f'{path.name}: missing target: {raw}'); continue
  if u.fragment and target.suffix.lower()=='.html' and target.exists():
   tp=parsed.get(target.name) or parse(target)
   if u.fragment not in tp.ids: errors.append(f'{path.name}: missing fragment #{u.fragment} in {target.name}')
print(f'Website audit: {len(htmls)} HTML pages; master pages {len(MASTER)-len(missing)}/{len(MASTER)} present')
if errors:
 print('Website audit FAIL')
 for e in errors: print(' - '+e)
 sys.exit(1)
print('Website links/fragments: PASS')
