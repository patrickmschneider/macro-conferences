import sys,json,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(R))
from crawler.validate import validate
from crawler.calendar import generate
records=json.loads((R/'data/conferences.json').read_text()); validate(records)
out=R/'dist'; out.mkdir(exist_ok=True)
for p in (R/'site').iterdir():
 if p.is_file(): shutil.copy2(p,out/p.name)
(out/'data').mkdir(exist_ok=True); (out/'calendars').mkdir(exist_ok=True)
for name in ['conferences.json','series.json','run-status.json']:
 shutil.copy2(R/'data'/name,out/'data'/name)
for kind,name in [('deadlines','cfp-deadlines.ics'),('events','conference-dates.ics')]:
 (out/'calendars'/name).write_bytes(generate(records,kind).encode())
(out/'.nojekyll').touch()
print(f'Built {len(records)} events into dist/')
