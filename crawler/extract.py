"""Conservative extraction: only single-event content and explicit submission language."""
import re, hashlib
from datetime import date,timedelta
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
MONTHS={m.lower():i for i,m in enumerate(['January','February','March','April','May','June','July','August','September','October','November','December'],1)}
MONTHS.update({m[:3]:i for m,i in list(MONTHS.items())});MONTHS['sept']=9
M=r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)'
WEEKDAY=r'(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.?,?\s+)?'
ORD=r'(?:st|nd|rd|th)?'
# Words that make a nearby date a deadline, notice or posting date rather than the event itself.
NOT_EVENT=re.compile(r'deadline|submi|\bdue\b|registr|register|notif|accept|decision|posted|published|updated|closes|\bapply|applications?\b|until|by\s*$',re.I)
# Day-month-year with a month name, month-day-year, or the dotted European form 18.03.2027.
# Slashed numeric dates are ambiguous between US and European order and never qualify.
DATE=re.compile(rf'\b(?:(?P<d>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<m>{M})\s*,?\s*(?P<y>20\d{{2}})|(?P<m2>{M})\s+(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?\s*,?\s*(?P<y2>20\d{{2}})|(?<![\d.])(?P<d3>\d{{1,2}})\.(?P<mo3>\d{{1,2}})\.(?P<y3>20\d{{2}})(?![\d.]))\b',re.I)
def dates(text):
 result=[]
 for m in DATE.finditer(text):
  try:
   v=date(int(m['y3']),int(m['mo3']),int(m['d3'])) if m['d3'] else date(int(m['y'] or m['y2']),MONTHS[(m['m'] or m['m2']).lower()],int(m['d'] or m['d2']))
   result.append((v.isoformat(),m.group()))
  except ValueError: pass
 return result

def clean(html):
 s=BeautifulSoup(html,'html.parser')
 # Google Sites (and similar builders) keep embedded pages as escaped HTML in data-code.
 # Without this, a CFP posted as an embed is invisible text.
 for tag in s.select('[data-code]'):
  inner=BeautifulSoup(tag['data-code'],'html.parser')
  for x in inner.select('script,style,noscript,template'):x.decompose()
  body=inner.find('body') or inner
  del tag['data-code'];tag.clear();tag.append(body)
 main=s.find('main') or s.find('article') or s
 h=main.find('h1') or s.find('h1')
 meta=s.find('meta',property='og:title')
 title=h.get_text(' ',strip=True) if h else meta.get('content','') if meta else s.title.get_text(' ',strip=True) if s.title else ''
 # Some sites use the h1 for their own banner ("Board of Governors of the Federal Reserve
 # System"). When the h1 is absent from the page's <title>/og:title, prefer a heading that is.
 named=' '.join([meta.get('content','') if meta else '',s.title.get_text(' ',strip=True) if s.title else '']).casefold()
 if title and named.strip() and title.casefold() not in named:
  title=next((x for x in (y.get_text(' ',strip=True) for y in main.find_all(['h1','h2','h3'])[:8]) if len(x)>12 and x.casefold() in named),title)
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

RANGES=[
 # June 18-19, 2027 / June 18th and 19th, 2027
 rf'(?P<m>{M})\s+(?P<d>\d{{1,2}}){ORD}\s*(?:[–—&-]|and|to)\s*{WEEKDAY}(?P<e>\d{{1,2}}){ORD},?\s+(?P<y>20\d{{2}})',
 # 18-19 June 2027 / Tuesday, 1 and Wednesday, 2 December 2026
 rf'(?<!\d)(?P<d>\d{{1,2}}){ORD}\s*(?:[–—&-]|and|to)\s*{WEEKDAY}(?P<e>\d{{1,2}}){ORD}\s+(?:of\s+)?(?P<m>{M}),?\s+(?P<y>20\d{{2}})',
 # April 30 - May 1, 2027
 rf'(?P<m>{M})\s+(?P<d>\d{{1,2}}){ORD}\s*(?:[–—-]|to|until)\s*{WEEKDAY}(?P<m2>{M})\s+(?P<e>\d{{1,2}}){ORD},?\s+(?P<y>20\d{{2}})',
 # 30 April - 1 May 2027
 rf'(?<!\d)(?P<d>\d{{1,2}}){ORD}\s+(?P<m>{M})\s*(?:[–—-]|to|until)\s*{WEEKDAY}(?P<e>\d{{1,2}}){ORD}\s+(?P<m2>{M}),?\s+(?P<y>20\d{{2}})',
 # 30 Nov 2026 - 1 Dec 2026 (CEPR)
 rf'(?<!\d)(?P<d>\d{{1,2}}){ORD}\s+(?P<m>{M}),?\s+(?P<y0>20\d{{2}})\s*(?:[–—-]|to|until)\s*{WEEKDAY}(?P<e>\d{{1,2}}){ORD}\s+(?P<m2>{M}),?\s+(?P<y>20\d{{2}})']
# Month and days without a year ("July 1-3"), used only when the same sentence states the year.
YEARLESS=re.compile(rf'(?P<m>{M})\s+(?P<d>\d{{1,2}}){ORD}(?:\s*(?:[–—-]|to|and)\s*(?P<e>\d{{1,2}}){ORD})?(?![\d,]*\s*20\d\d)',re.I)
EVENT_CONTEXT=re.compile(r'\b(?:takes? place|(?:will|to) be held|is held|will meet|meets in person|will convene|scheduled for|will be hosted|(?:conference|workshop|symposium|meeting) (?:date|day)s?)\b',re.I)

def deadline_context(text,pos,span=45):
 return bool(NOT_EVENT.search(text[max(0,pos-span):pos]))

# "Published on 21st of April 2026", "Last updated: May 3, 2026 10:57": page stamps, not events.
PUBLISHED=re.compile(rf'(?:Published|Posted|Last updated|Updated|Last modified)(?:\s+on)?:?\s+(?:{WEEKDAY})?(?:\d{{1,2}}{ORD}(?:\s+of)?\s+{M}\.?,?\s+20\d{{2}}|{M}\.?\s+\d{{1,2}}{ORD},?\s+20\d{{2}}|20\d{{2}}-\d{{2}}-\d{{2}}|\d{{1,2}}/\d{{1,2}}/\d{{2,4}})(?:,?\s+\d{{1,2}}[:.]\d{{2}})?',re.I)
TIME_AFTER=re.compile(r'\s*(?:[,–—-]|at|from)?\s*\d{1,2}[:.]\d{2}\s*(?:[ap]\.?m\.?)?',re.I)

def event_date_detail(text,title=None):
 """Return (start,end,quote,how,n_ranges). `how` records which rule fired, so callers can
 demand stronger evidence from weaker rules. Dates near deadline words never qualify."""
 # Blank out publication stamps with equal-length padding so positions (and quotes taken
 # from the original text) stay aligned.
 text_in=text;text=PUBLISHED.sub(lambda m:' '*len(m.group()),text)
 head=text[:1500];found=[]
 for p in RANGES:
  for m in re.finditer(p,head,re.I):
   if deadline_context(head,m.start()):continue
   try:
    y=int(m['y']);m1=MONTHS[m['m'].lower()];m2=MONTHS[(m.groupdict().get('m2') or m['m']).lower()]
    y0=int(m.groupdict().get('y0') or y)
    start=date(y0,m1,int(m['d'])).isoformat();end=date(y,m2,int(m['e'])).isoformat()
    if end>=start:found.append((m.start(),start,end,text_in[m.start():m.end()]))
   except ValueError:pass
 for m in re.finditer(r'(?<![\d.])(\d{1,2})\.(\d{1,2})\.(20\d{2})\s*(?:[–—-]|to|bis)\s*(\d{1,2})\.(\d{1,2})\.(20\d{2})(?![\d.])',head):
  if deadline_context(head,m.start()):continue
  try:
   start=date(int(m[3]),int(m[2]),int(m[1])).isoformat();end=date(int(m[6]),int(m[5]),int(m[4])).isoformat()
   if end>=start:found.append((m.start(),start,end,text_in[m.start():m.end()]))
  except ValueError:pass
 distinct={(s,e) for _,s,e,_ in found}
 if found:
  pos,start,end,quote=min(found);return start,end,quote,'range',len(distinct)
 m=re.search(r'\b(?:DATE|Date & Time|Date:)\s+(.{1,65})',text)
 if m and dates(m[1]):return dates(m[1])[0][0],None,dates(m[1])[0][1],'label',0
 # An explicit event sentence: "will take place ... from June 10-13, 2027", "... on 5 February
 # 2027", or "The 2027 SED meeting will take place July 1-3" (year stated in that sentence).
 for m in EVENT_CONTEXT.finditer(text[:6000]):
  seg=text[m.end():m.end()+110]
  ranged=[]
  for p in RANGES:
   r=re.search(p,seg,re.I)
   if r and not NOT_EVENT.search(seg[:r.start()]):ranged.append(r)
  for r in sorted(ranged,key=lambda r:r.start()):
   try:
    y=int(r['y']);y0=int(r.groupdict().get('y0') or y);m2=(r.groupdict().get('m2') or r['m']).lower()
    start=date(y0,MONTHS[r['m'].lower()],int(r['d'])).isoformat();end=date(y,MONTHS[m2],int(r['e'])).isoformat()
    if end>=start:return start,end,text_in[m.start():m.end()+r.end()],'context',1
   except ValueError:pass
  d=DATE.search(seg)
  if d and not NOT_EVENT.search(seg[:d.start()]) and dates(d.group()):
   return dates(d.group())[0][0],None,text_in[m.start():m.end()+d.end()],'context',0
  s0=max(text.rfind('. ',0,m.start()),0);years=set(re.findall(r'(?<!\d)(20\d\d)(?!\d)',text[s0:m.start()]))
  y=YEARLESS.match(seg.lstrip()) or YEARLESS.match(re.sub(r'^\s*(?:on|from)\s+','',seg))
  if len(years)==1 and y and not NOT_EVENT.search(text[s0:m.start()]):
   try:
    year=int(years.pop());start=date(year,MONTHS[y['m'].lower()],int(y['d'])).isoformat()
    end=date(year,MONTHS[y['m'].lower()],int(y['e'])).isoformat() if y['e'] else None
    if not end or end>=start:return start,end,text_in[s0:m.end()+len(seg)-len(seg.lstrip())+y.end()].lstrip('. '),'context',0
   except ValueError:pass
 # A single date with a start time ("Thursday 17 December 2026, 8:30 AM", "06 November
 # 2026 - 08:30") is an event start; deadline wording nearby still disqualifies it.
 for d in DATE.finditer(head):
  if TIME_AFTER.match(head,d.end()) and not deadline_context(head,d.start()) and dates(d.group()):
   return dates(d.group())[0][0],None,text_in[d.start():TIME_AFTER.match(head,d.end()).end()],'timed',0
 # A single date directly under the event title, as in a CFP header. The title can also
 # appear earlier as a breadcrumb, so try each early occurrence.
 if title:
  i=text.find(title)
  while 0<=i<3000:
   seg=text[i+len(title):i+len(title)+90];d=DATE.search(seg)
   if d and d.start()<40 and not NOT_EVENT.search(seg[:d.start()]) and dates(d.group()):
    start=dates(d.group())[0][0];end=None;stop=d.end()
    # Event templates often print the end date right after the start: "April 8, 2027 April 9, 2027".
    nxt=DATE.match(text,i+len(title)+d.end()+1) or DATE.match(text,i+len(title)+d.end()+3)
    if nxt and dates(nxt.group()) and start<dates(nxt.group())[0][0]<=(date.fromisoformat(start)+timedelta(days=14)).isoformat():
     end=dates(nxt.group())[0][0];stop=nxt.end()-i-len(title)
    return start,end,text_in[i:i+len(title)+stop],'header',0
   i=text.find(title,i+1)
 return None,None,None,None,0

def event_dates(text,title=None):
 return event_date_detail(text,title)[:3]

TOPICS={
 'General macro':r'macroeconom|economic dynamics|\bmacro\b|\bexpectations\b', 'Monetary policy':r'monetary|inflation|central bank|digital currenc|\bCBDC\b|stablecoin',
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
 start,end,eq=event_dates(text,title)
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
