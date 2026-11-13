"""Conservative discovery/extraction for vetted institutional research listings."""
import hashlib,json,re
from datetime import date
from urllib.parse import urljoin,urlparse,urldefrag
from bs4 import BeautifulSoup
from .extract import clean,topics,deadline,event_date_detail,dates,DATE,M,MONTHS

EVENT_WORDS=r'conference|workshop|symposium|meeting|micro\s*(?:for|4)\s*macro'
EXCLUDE=r'legal conference|press conference|media conference|speech|keynote remarks|webinar|research seminar|lounge session|training|summer school|scholars program|teacher|career|podcast|governance.*culture'
ACADEMIC=r'\bresearch|\bpapers?\b|\bacademic|\bscholars?\b|call for (?:papers|submissions)|\bsubmissions?\b|keynote|scientific committee|program(?:me)? committee|discussants?|\beconomists\b|universit|professor'

def discover_research(html,url,source):
 """Follow vetted links from a listing. A `series` source is an index page for one known
 conference series: its URL pattern is the vetting, so link text need not look topical."""
 soup=BeautifulSoup(html,'html.parser')
 # Drop site chrome. Navigation inside <main> can be the listing itself (the Bundesbank wraps
 # its conference list in <nav>), and a series index page may link editions from its menu.
 for t in soup.select('footer,aside,nav'):
  if t.name=='nav' and (source.get('series') or t.find_parent('main')):continue
  t.decompose()
 main=soup.find('main') or soup
 found=[{'url':url,'label':source['name'],'document':False}] if source.get('include_listing') else []
 allowed={urlparse(url).hostname,*source.get('allowed_hosts',[])}
 for a in (soup if source.get('series') else main).select('a[href]'):
  label=a.get_text(' ',strip=True);u=urldefrag(urljoin(url,a['href']))[0]
  if urlparse(u).scheme!='https' or urlparse(u).hostname not in allowed:continue
  if u.rstrip('/')==url.rstrip('/') or not source.get('link_pattern') or not re.search(source['link_pattern'],urlparse(u).path,re.I):continue
  if not source.get('series') and not re.search(EVENT_WORDS,label,re.I) and not topics(label):continue
  if re.search(EXCLUDE,label,re.I):continue
  if re.search(r'\.(?:pdf|docx?|ics)(?:\?|$)',u,re.I):
   found.append({'url':u,'label':label,'document':True});continue
  # Order recent editions before historical archives; preserve document order within year.
  years=[int(y) for y in re.findall(r'(?<!\d)(20\d{2})(?:\d{4})?(?!\d)',label+' '+u)]
  if years and max(years)<date.today().year:continue
  found.append({'url':u,'label':label,'document':False})
 seen=set();result=[]
 for item in found:
  if item['url'] not in seen:seen.add(item['url']);result.append(item)
 return result

def structured_events(html):
 soup=BeautifulSoup(html,'html.parser');result=[]
 def walk(x):
  if isinstance(x,list):
   for v in x:walk(v)
  elif isinstance(x,dict):
   typ=x.get('@type',[]);typ=[typ] if isinstance(typ,str) else typ
   if any(t in ['Event','BusinessEvent','EducationEvent'] for t in typ):result.append(x)
   for k,v in x.items():
    if k!='subEvent' and isinstance(v,(dict,list)):walk(v)
 for s in soup.select('script[type="application/ld+json"]'):
  try:walk(json.loads(s.string or s.get_text()))
  except (ValueError,TypeError):pass
 return result

def structured_date_evidence(html,evidence):
 for event in structured_events(html):
  if event.get('name')==evidence.get('event_name') and all(event.get(k)==v for k,v in evidence.get('values',{}).items()):return True
 return False

def extract_research(html,url,source):
 title,text,soup=clean(html)
 if not title or re.search(EXCLUDE,title,re.I):return None
 if not re.search(EVENT_WORDS,title,re.I) and not re.search(r'\b(?:conference|workshop|symposium|meeting)\b',text[:1200],re.I):return None
 tags=topics(title) or topics(text[:1800])
 # A vetted series is relevant by construction; its registry topics apply.
 if not tags and source.get('series'):tags=list(source.get('topics',[]))
 # Institutional pages often contain topical navigation. Require academic substance.
 if not tags or not re.search(ACADEMIC,text,re.I):return None
 start=end=None;eq=None;location={}
 structured=structured_events(html)
 norm=lambda x:re.sub(r'[^a-z0-9]','',str(x).lower())
 matches=[x for x in structured if norm(x.get('name'))==norm(title)]
 if len(matches)==1:
  e=matches[0];raw=e.get('startDate','');rawend=e.get('endDate')
  if re.match(r'^\d{4}-\d{2}-\d{2}(?:T|$)',raw):
   start=date.fromisoformat(raw[:10]).isoformat();end=date.fromisoformat(rawend[:10]).isoformat() if rawend else None
   values={'startDate':raw}
   if rawend:values['endDate']=rawend
   eq={'url':url,'text':'; '.join(f'{k}: {v}' for k,v in values.items()),'kind':'jsonld','event_name':e['name'],'values':values}
   loc=e.get('location',{});location=loc.get('address',{}) if isinstance(loc,dict) else {}
   if not isinstance(location,dict):location={}
 how='jsonld' if start else None
 if not start:
  start,end,quote,how,ranges=event_date_detail(text,title)
  if not start:return None
  # A listing ("Research Conferences", "Upcoming events") is not one event, whatever dates
  # it shows. An unlabelled range on a page without its own year may also be one entry of
  # a listing; several distinct ranges confirm that. Publish only single-event pages.
  if re.search(r'(?:conferences|workshops|events|meetings|seminars|calendar|agenda|archive)\W*$',title,re.I):return None
  if how=='range' and ranges>2:return None
  if how=='range' and ranges>1 and not re.search(r'20\d{2}',title+' '+url):return None
  eq={'url':url,'text':quote}
 d,dq,certainty=deadline(text)
 # A lone date that is also the submission deadline is ambiguous: withhold the page.
 if how in ('context','header') and d==start:return None
 if d and d>start:d=dq=None
 state='open' if d and d>=date.today().isoformat() else 'closed' if d else 'unknown'
 if re.search('no longer accepting submissions|call for papers is now closed|submissions are closed',text,re.I):state='closed'
 # "Submissions Open: December 1, 2026" with that date still ahead: the call is announced, not open.
 opens=re.search(rf'submissions?\s+(?:open|opens|will open|portal opens)\W{{0,3}}(?:on\s+)?({DATE.pattern})',text,re.I)
 if state=='open' and opens and dates(opens[1]) and dates(opens[1])[0][0]>date.today().isoformat():state='not_yet_open'
 if certainty=='conflict':d=dq=None;state='unknown'
 id='event-'+hashlib.sha256(url.encode()).hexdigest()[:14]
 country=location.get('addressCountry');country=country.get('name') if isinstance(country,dict) else country
 country={'AU':'Australia','US':'United States','GB':'United Kingdom','DE':'Germany','CH':'Switzerland','CA':'Canada'}.get(country,country)
 # Series whose pages carry generic headings ("Call for Papers (CFP)") name editions from the registry.
 name=source['event_name'].format(year=start[:4]) if source.get('event_name') else title
 return dict(id=id,series_id=source.get('series_id'),name=name,organizers=[source.get('organizer',source['name'])],event_type='Workshop' if 'workshop' in title.lower() else 'Conference',event_start=start,event_end=end,city=location.get('addressLocality'),country=country,region=source.get('region') if source.get('series') else None,topics=tags,source_url=url,event_state='announced',calls=[dict(id=id+'-papers',kind='Paper submission',deadline=d,deadline_time=None,deadline_timezone=None,state=state,source_url=url,evidence={'url':url,'text':dq} if dq else None)],notes='',evidence={'event_dates':eq},history=[],health='verified')
