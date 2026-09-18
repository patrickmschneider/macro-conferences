import json, os
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def read(name): return json.loads((ROOT/name).read_text())
def write(name,value):
 p=ROOT/name; p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_suffix(p.suffix+'.tmp'); tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n'); os.replace(tmp,p)
