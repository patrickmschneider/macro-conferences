from datetime import date
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from urllib.parse import urlparse

def validate(records):
 schema=json.loads((Path(__file__).resolve().parents[1]/'schemas/conferences.schema.json').read_text())
 Draft202012Validator(schema,format_checker=FormatChecker()).validate(records)
 ids=set(); calls=set()
 for r in records:
  assert r['id'] not in ids, 'Duplicate event ID'; ids.add(r['id'])
  assert r['name'] and r['organizers'] and r['topics'], 'Missing identity or topic'
  assert urlparse(r['source_url']).scheme=='https', 'HTTPS source required'
  start=date.fromisoformat(r['event_start']) if r.get('event_start') else None
  end=date.fromisoformat(r['event_end']) if r.get('event_end') else None
  assert not end or start and end>=start, 'Invalid event range'
  if start: assert r['evidence']['event_dates']['text'], 'Event evidence required'
  for c in r['calls']:
   assert c['id'] not in calls, 'Duplicate call ID'; calls.add(c['id'])
   assert c['state'] in ['open','closed','unknown','not_yet_open','withdrawn']
   if c.get('deadline'):
    d=date.fromisoformat(c['deadline'])
    assert c.get('evidence',{}).get('text'), 'Deadline evidence required'
    assert not start or d<=start, 'Deadline after event requires explicit handling'
   if c['state']=='open': assert c.get('deadline') and c.get('evidence'), 'Open call requires supported deadline'
 return True
