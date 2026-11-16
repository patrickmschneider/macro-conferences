"""Structured event feeds. CEPR's event pages sit behind a bot challenge, but its official
events RSS feed (https://cepr.org/rss/events) is open and carries ISO start/end dates.
Feed records publish event dates only: submission deadlines stay unknown unless another
source supplies them."""
import hashlib,re
import xml.etree.ElementTree as ET
from datetime import date
from .extract import topics

CEPR='https://cepr.org/rss/ns/1.0'
KEEP_TYPES={'Conference','Workshop','Meeting','External'}
EXCLUDE=r'seminar series|seminars? -|online seminar|virtual seminar|webinar|virtual|award|prize|report launch|masterclass|lecture|gathering|summer school|training|VIOS|CAFFE|publishing in top'
REGIONS={**{c:'Europe' for c in ['United Kingdom','Ireland','France','Germany','Italy','Spain','Portugal','Netherlands','Belgium','Luxembourg','Switzerland','Austria','Denmark','Sweden','Norway','Finland','Iceland','Poland','Czech Republic','Czechia','Hungary','Greece','Slovenia','Slovakia','Croatia','Estonia','Latvia','Lithuania','Romania','Bulgaria','Cyprus','Malta','Montenegro','Serbia']},
 'United States':'North America','Canada':'North America','Mexico':'Latin America','Chile':'Latin America','Brazil':'Latin America','Colombia':'Latin America','Argentina':'Latin America','Peru':'Latin America',
 'Australia':'Oceania','New Zealand':'Oceania','China':'Asia','Japan':'Asia','Korea':'Asia','South Korea':'Asia','Singapore':'Asia','Hong Kong':'Asia','India':'Asia','Malaysia':'Asia','Indonesia':'Asia','Israel':'Middle East','Turkey':'Europe','South Africa':'Africa','Kenya':'Africa','Uganda':'Africa','Nigeria':'Africa'}

def parse_rss(xml):
 root=ET.fromstring(xml.encode() if isinstance(xml,str) else xml);items=[]
 for i in root.findall('./channel/item'):
  g=lambda k,ns=CEPR:(i.findtext(f'{{{ns}}}{k}') or '').strip()
  items.append(dict(url=(i.findtext('link') or '').strip(),title=re.sub(r'\s+',' ',i.findtext('title') or '').strip(),
   description=re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',i.findtext('description') or '')).strip(),
   type=g('type'),start=g('event_start'),end=g('event_end'),series=g('event_series'),format=g('event_format'),city=g('city'),country=g('country')))
 return [x for x in items if x['url'].startswith('https://') and re.match(r'\d{4}-\d{2}-\d{2}',x['start'])]

def relevant(item):
 if item['type'] not in KEEP_TYPES:return False
 if re.search(EXCLUDE,item['title']+' '+item['series'],re.I):return False
 return bool(topics(item['title']+' '+item['series']+' '+item['description']))

def feed_dates(item):
 start=date.fromisoformat(item['start'][:10]).isoformat()
 end=date.fromisoformat(item['end'][:10]).isoformat() if re.match(r'\d{4}-\d{2}-\d{2}',item['end']) else None
 return start,(end if end and end>=start else None)

def evidence(item,feed_url):
 start,end=feed_dates(item);values={'event_start':item['start']}
 if end:values['event_end']=item['end']
 return {'url':feed_url,'kind':'feed','item_url':item['url'],'values':values,'text':f"{item['title']}: "+'; '.join(f'{k} {v}' for k,v in values.items())}

def feed_record(item,source,feed_url):
 start,end=feed_dates(item);id='event-'+hashlib.sha256(item['url'].encode()).hexdigest()[:14]
 tags=topics(item['title']+' '+item['series']) or topics(item['description'])
 kind='Workshop' if item['type']=='Workshop' or 'workshop' in item['title'].lower() else 'Conference'
 return dict(id=id,series_id=None,name=item['title'],organizers=[source.get('organizer','CEPR')],event_type=kind,event_start=start,event_end=end,
  city=item['city'] or None,country=item['country'] or None,region=REGIONS.get(item['country']),topics=tags,source_url=item['url'],event_state='announced',
  calls=[dict(id=id+'-papers',kind='Paper submission',deadline=None,deadline_time=None,deadline_timezone=None,state='unknown',source_url=item['url'],evidence=None)],
  notes='Dates from the CEPR events feed. Check the event page for any call for papers.',evidence={'event_dates':evidence(item,feed_url)},history=[],health='verified')

def verify_feed(record,items,stamp):
 """Recheck a feed-derived record against today's feed. A changed date is a supported
 update from the same authoritative source; an absent item is left unchanged, never
 treated as a cancellation."""
 e=record['evidence']['event_dates'];item=items.get(e.get('item_url'))
 record['last_checked']=stamp
 if not item:return record
 start,end=feed_dates(item)
 for field,new in [('event_start',start),('event_end',end)]:
  if record.get(field)!=new:
   record['history'].append({'at':stamp,'field':field,'old':record.get(field),'new':new,'evidence':evidence(item,e['url'])['text']})
   record[field]=new
 record['evidence']['event_dates']=evidence(item,e['url'])
 record.update(last_verified=stamp,health='verified',verification_method='feed recheck');record.pop('check_error',None)
 return record
