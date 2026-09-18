from datetime import date,datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import hashlib

def esc(s): return str(s).replace('\\','\\\\').replace('\n','\\n').replace(';','\\;').replace(',','\\,')
def fold(line):
 result=[]; current=''
 for char in line:
  if len((current+char).encode())>74: result.append(current); current=' '+char
  else: current+=char
 result.append(current); return '\r\n'.join(result)
def generate(records,kind):
 lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Macro Conference Tracker//EN','CALSCALE:GREGORIAN','METHOD:PUBLISH',f'X-WR-CALNAME:{"Macro submission deadlines" if kind=="deadlines" else "Macro conference dates"}']
 for r in records:
  # Retain past entries for stable subscriptions. Withheld entries get explicit cancellation.
  entries=r['calls'] if kind=='deadlines' else [{'id':r['id'],'deadline':r['event_start'],'kind':''}]
  for c in entries:
   d=c.get('deadline')
   if not d: continue
   uid=f'{c["id"]}-{kind}@macro-conferences.patrickmschneider.com'
   updated=r.get('last_verified') or r['discovered_at']
   dt=datetime.fromisoformat((r.get('last_checked') or updated).replace('Z','+00:00'))
   if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
   lines+=['BEGIN:VEVENT','UID:'+uid,'DTSTAMP:'+dt.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),'LAST-MODIFIED:'+dt.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),'SEQUENCE:'+str(int((dt.astimezone(timezone.utc)-datetime(2020,1,1,tzinfo=timezone.utc)).total_seconds()))]
   cancelled=r.get('event_state')=='cancelled' or r.get('health')=='needs_verification' or r.get('event_state')=='postponed' or c.get('state')=='withdrawn'
   if kind=='deadlines' and d>=date.today().isoformat() and (date.today()-date.fromisoformat(updated[:10])).days>14: cancelled=True
   lines+=['STATUS:'+('CANCELLED' if cancelled else 'CONFIRMED')]
   if kind=='deadlines' and c.get('deadline_time') and c.get('deadline_timezone'):
    cutoff=datetime.fromisoformat(d+'T'+c['deadline_time']).replace(tzinfo=ZoneInfo(c['deadline_timezone']))
    lines+=['DTSTART:'+cutoff.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')]
   else:
    lines+=['DTSTART;VALUE=DATE:'+d.replace('-','')]
    end=date.fromisoformat((r.get('event_end') or d) if kind=='events' else d)+timedelta(days=1)
    lines+=['DTEND;VALUE=DATE:'+end.strftime('%Y%m%d')]
   title=(c.get('kind','Paper submission')+' deadline · ' if kind=='deadlines' else '')+r['name']
   desc=r.get('notes','')+'\nSource: '+c.get('source_url',r['source_url'])+'\nLast verified: '+updated[:10]
   if kind=='deadlines' and c.get('deadline_time') and not c.get('deadline_timezone'): desc+='\nSource cutoff: '+c['deadline_time']+'; time zone unspecified. All-day calendar entry.'
   lines+=['SUMMARY:'+esc(title),'DESCRIPTION:'+esc(desc),'URL:'+c.get('source_url',r['source_url']),'LOCATION:'+esc(', '.join(x for x in [r.get('city'),r.get('country')] if x)),'END:VEVENT']
 lines+=['END:VCALENDAR']; return '\r\n'.join(fold(line) for line in lines)+'\r\n'
