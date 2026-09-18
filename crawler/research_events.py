"""Conservative discovery/extraction for vetted institutional research listings."""
import hashlib,json,re
from datetime import date
from urllib.parse import urljoin,urlparse,urldefrag
from bs4 import BeautifulSoup
from .extract import clean,topics,deadline,event_dates,M,MONTHS

EVENT_WORDS=r'conference|workshop|symposium|micro\s*(?:for|4)\s*macro'
EXCLUDE=r'legal conference|press conference|media conference|speech|keynote remarks|webinar|research seminar|lounge session|training|summer school|scholars program|teacher|career|podcast|governance.*culture'

def discover_research(html,url,source):
 soup=BeautifulSoup(html,'html.parser')
 for t in soup.select('nav,footer,aside'):t.decompose()
 main=soup.find('main') or soup
 found=[];allowed={urlparse(url).hostname,*source.get('allowed_hosts',[])}
 for a in main.select('a[href]'):
  label=a.get_text(' ',strip=True);u=urldefrag(urljoin(url,a['href']))[0]
  if urlparse(u).scheme!='https' or urlparse(u).hostname not in allowed:continue
  if u.rstrip('/')==url.rstrip('/') or not re.search(source['link_pattern'],urlparse(u).path,re.I):continue
  if not re.search(EVENT_WORDS,label,re.I) and not topics(label):continue
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
 if not re.search(EVENT_WORDS,title,re.I) and not re.search(r'\b(?:conference|workshop|symposium)\b',text[:1200],re.I):return None
 tags=topics(title)
 if not tags:tags=topics(text[:1800])
 # Institutional pages often contain topical navigation. Require academic substance.
 if not tags or not re.search(r'\bresearch|\bpapers?\b|\bacademic|\bscholars?\b',text,re.I):return None
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
 if not start and not re.search(r'20\d{2}',title+' '+url):return None
 if not start:
  start,end,quote=event_dates(text)
  if quote:eq={'url':url,'text':quote}
 if not start:return None
 d,dq,certainty=deadline(text)
 if d and d>start:d=dq=None
 state='open' if d and d>=date.today().isoformat() else 'closed' if d else 'unknown'
 if re.search('no longer accepting submissions|call for papers is now closed|submissions are closed',text,re.I):state='closed'
 if certainty=='conflict':d=dq=None;state='unknown'
 id='event-'+hashlib.sha256(url.encode()).hexdigest()[:14]
 country=location.get('addressCountry');country=country.get('name') if isinstance(country,dict) else country
 country={'AU':'Australia','US':'United States','GB':'United Kingdom','DE':'Germany','CH':'Switzerland','CA':'Canada'}.get(country,country)
 return dict(id=id,series_id=source.get('series_id'),name=title,organizers=[source.get('organizer',source['name'])],event_type='Workshop' if 'workshop' in title.lower() else 'Conference',event_start=start,event_end=end,city=location.get('addressLocality'),country=country,region=None,topics=tags,source_url=url,event_state='announced',calls=[dict(id=id+'-papers',kind='Paper submission',deadline=d,deadline_time=None,deadline_timezone=None,state=state,source_url=url,evidence={'url':url,'text':dq} if dq else None)],notes='',evidence={'event_dates':eq},history=[],health='verified')
