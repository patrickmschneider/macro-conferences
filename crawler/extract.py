"""Conservative extraction: only single-event content and explicit submission language."""
import re, hashlib
from datetime import date
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
MONTHS={m.lower():i for i,m in enumerate(['January','February','March','April','May','June','July','August','September','October','November','December'],1)}
MONTHS.update({m[:3]:i for m,i in list(MONTHS.items())})
M=r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
DATE=re.compile(rf'\b(?:(?P<d>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<m>{M})\s*,?\s*(?P<y>20\d{{2}})|(?P<m2>{M})\s+(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?\s*,?\s*(?P<y2>20\d{{2}}))\b',re.I)
def dates(text):
 result=[]
 for m in DATE.finditer(text):
  try: result.append((date(int(m['y'] or m['y2']),MONTHS[(m['m'] or m['m2']).lower()],int(m['d'] or m['d2'])).isoformat(),m.group()))
  except ValueError: pass
 return result

def clean(html):
 s=BeautifulSoup(html,'html.parser')
 main=s.find('main') or s.find('article') or s
 h=main.find('h1') or s.find('h1')
 meta=s.find('meta',property='og:title')
 title=h.get_text(' ',strip=True) if h else meta.get('content','') if meta else s.title.get_text(' ',strip=True) if s.title else ''
 for tag in s.select('script,style,nav,footer,aside,.share,.related-content'):tag.decompose()
 for tag in s.select('header'):
  if not tag.find_parent(['main','article']) and not tag.find('h1'):tag.decompose()
 text=' '.join(main.stripped_strings)
 text=re.split(r'\b(?:Related Events|Related Content|Upcoming events in series|Themes & Issues|Event Navigation)\b',text)[0]
 return title,re.sub(r'\s+',' ',text).strip(),s

def deadline(text):
 # Bound each clause to its first explicit date. A registration deadline never qualifies.
 anchors=r'(?:submission deadline(?:\s+is)?|deadline for (?:paper )?submissions(?:\s+is|\s+was)?|(?:papers?|abstracts?)\s+(?:must be |should be |to be )?(?:uploaded|submitted)|submit\s+(?:a |your |the )?(?:paper|abstract)|upload a pdf|(?:email|send) (?:a )?draft of (?:their|your) paper|closes)'
 hits=[]
 for m in re.finditer(anchors,text,re.I):
  if re.search(r'registration|booking|notification',text[max(0,m.start()-35):m.start()],re.I): continue
  clause=text[m.start():m.end()+180]
  ds=list(DATE.finditer(clause))
  if not ds: continue
  first=ds[0]; snippet=clause[:first.end()]
  if re.search(r'\bregistration\b',snippet,re.I): continue
  vals=dates(snippet)
  if vals: hits.append((vals[0][0],snippet))
 values={d for d,_ in hits}
 if len(values)!=1: return None,None,'conflict' if values else 'missing'
 return hits[0][0],hits[0][1],'supported'

def event_dates(text):
 # Explicit date ranges, or a labelled DATE line on NBER conference pages.
 pats=[rf'(?P<m>{M})\s+(?P<d>\d{{1,2}})\s*(?:[–—&-]|and)\s*(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+)?(?P<e>\d{{1,2}}),?\s+(?P<y>20\d{{2}})',rf'(?P<d>\d{{1,2}})\s*(?:[–—&-]|and)\s*(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+)?(?P<e>\d{{1,2}})\s+(?P<m>{M}),?\s+(?P<y>20\d{{2}})']
 for p in pats:
  m=re.search(p,text[:1100],re.I)
  if m:
   try:
    start=date(int(m['y']),MONTHS[m['m'].lower()],int(m['d'])).isoformat(); end=date(int(m['y']),MONTHS[m['m'].lower()],int(m['e'])).isoformat()
    if end>=start: return start,end,m.group()
   except ValueError: pass
 # CEPR full date ranges.
 m=re.search(rf'(\d{{1,2}}\s+{M}\s+20\d{{2}})\s*[–—-]\s*(\d{{1,2}}\s+{M}\s+20\d{{2}})',text[:1100],re.I)
 if m:
  a,b=dates(m[1]),dates(m[2])
  if a and b: return a[0][0],b[0][0],m.group()
 m=re.search(r'\b(?:DATE|Date & Time|Date:)\s+(.{1,65})',text)
 if m and dates(m[1]): return dates(m[1])[0][0],None,dates(m[1])[0][1]
 return None,None,None

TOPICS={
 'General macro':r'macroeconom|economic dynamics', 'Monetary policy':r'monetary|inflation|central bank',
 'Fiscal policy':r'fiscal|sovereign debt|budget deficit','International macro':r'international macro|open econom|tariff|global imbalance|international economics|international.*dollar',
 'Growth':r'growth|productivity|structural transformation','Business cycles':r'business cycle|fluctuation',
 'Macro-finance':r'macro.?finance|nonbank financial|non-bank financial|money markets|financial markets|bank funding','Financial stability':r'financial stability|macroprudential|banking',
 'Labour macro':r'labo[u]?r market|labo[u]?r macro','Heterogeneous agents':r'heterogen|inequality|micro\s*(?:for|4)\s*macro',
 'Computational macro':r'computational|macroeconometric|dynamic equilibrium',
 'Household finance':r'household finance|household saving|consumer (?:credit|finance)|mortgage|auto lending',
 'Pensions and retirement':r'pension|retirement|population ag[ei]ing'}
def topics(text): return [k for k,v in TOPICS.items() if re.search(v,text,re.I)]
def extract(html,url,organizer):
 title,text,s=clean(html)
 if not title or re.search(r'blocked|access denied|just a moment|attention required',title,re.I): raise ValueError('Access blocked or challenge page')
 # Require topical title, not site navigation or tangential terms in a long page.
 tags=topics(title)
 if not tags or re.search(r'webinar|seminar series|summer school|training school|local labor markets|mentoring',title,re.I): return None
 start,end,eq=event_dates(text)
 if not start: return None
 d,dq,certainty=deadline(text)
 closed=bool(re.search(r'no longer receiving submissions|deadline to submit a paper for consideration has passed|no longer accepting submissions',text,re.I))
 state='closed' if closed else 'open' if d and d>=date.today().isoformat() else 'closed' if d else 'unknown'
 if certainty=='conflict': state='unknown'
 country=None; city=None
 loc=re.search(r'\bLOCATION\s+(.+?)(?:\bORGANIZERS\b|\bDATE\b)',text)
 if loc:
  location=loc[1].strip()
  for city_name in ['Cambridge, MA','San Francisco, CA','Washington, DC','New York, NY']:
   if city_name in location: city=city_name; country='United States'
 id='event-'+hashlib.sha256(url.encode()).hexdigest()[:14]
 evidence={'event_dates':{'url':url,'text':eq},'deadline':{'url':url,'text':dq} if dq else None}
 return dict(id=id,series_id=None,name=title,organizers=[organizer],event_type='Workshop' if 'workshop' in title.lower() else 'Conference',event_start=start,event_end=end,city=city,country=country,region='North America' if country=='United States' else None,topics=tags,source_url=url,event_state='announced',calls=[dict(id=id+'-papers',kind='Paper submission',deadline=d,deadline_time=None,deadline_timezone=None,state=state,source_url=url,evidence=evidence['deadline'])],notes='',evidence=evidence,history=[],health='verified')

def discover(html,url):
 _,_,s=clean(html); s=s.find('main') or s; links=[]
 for a in s.select('a[href]'):
  u=urljoin(url,a['href']).split('#')[0]; label=a.get_text(' ',strip=True)
  if urlparse(u).hostname!=urlparse(url).hostname: continue
  if topics(label) and len(label)>12 and not re.search(r'/papers/|/people/|/programs-projects/|/brd|/macroannual|\.pdf|event-series|programme-areas',u): links.append(u)
 return sorted(set(links))
