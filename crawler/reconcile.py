import copy,re
from datetime import date
from .extract import clean, deadline, dates

def norm(s): return re.sub(r'\s+',' ',s).strip().casefold()
def verify(old,html,stamp):
 r=copy.deepcopy(old); r['last_checked']=stamp
 title,text,_=clean(html)
 if re.search('blocked|access denied|just a moment',title,re.I): raise ValueError('Access blocked')
 # Evidence fragments can have different whitespace, but cannot disappear unnoticed.
 evidence=[r['evidence'].get('event_dates')]+[c.get('evidence') for c in r['calls'] if c.get('deadline')]
 supported=all(e and norm(e['text']) in norm(text) for e in evidence)
 new_date,quote,certainty=deadline(text)
 if len(r['calls'])==1 and new_date and r['calls'][0].get('deadline') and new_date!=r['calls'][0]['deadline']:
  # Conflicting old and new dates are not extensions unless the source explicitly says so.
  if re.search(r'deadline\s+(?:has been\s+)?extended|extended\s+(?:submission\s+)?deadline',text,re.I) and new_date>=r['calls'][0]['deadline'] and new_date<=r['event_start']:
   before=r['calls'][0]['deadline']; r['calls'][0]['deadline']=new_date
   r['calls'][0]['evidence']={'url':r['source_url'],'text':quote}; r['calls'][0]['deadline_time']=None; r['calls'][0]['deadline_timezone']=None
   r['history'].append({'at':stamp,'field':'deadline','old':before,'new':new_date,'evidence':quote})
   supported=norm(r['evidence']['event_dates']['text']) in norm(text)
  else: certainty='conflict'
 if certainty=='conflict': supported=False
 if supported:
  r['last_verified']=stamp; r['health']='verified'
  r['verification_method']='source evidence recheck'
 else: r['health']='needs_verification'
 # Never infer cancellations from a generic word elsewhere in a page.
 if re.search(r'(?:this|the) (?:conference|event|workshop) (?:has been|is) cancel(?:l)?ed',text,re.I):
  r['event_state']='cancelled'; r['health']='verified'; r['last_verified']=stamp
 elif re.search(r'(?:this|the) (?:conference|event|workshop) (?:has been|is) postponed',text,re.I):
  r['event_state']='postponed'; r['health']='needs_verification'
 for c in r['calls']:
  if re.search(r'no longer receiving submissions|deadline to submit a paper for consideration has passed|no longer accepting submissions',text,re.I): c['state']='closed'
  # Time-based closure is computed at display time in the source timezone.
 return r

def duplicate(a,b):
 urls_a={a['source_url'].rstrip('/'),*[u.rstrip('/') for u in a.get('supporting_urls',[])]}
 urls_b={b['source_url'].rstrip('/'),*[u.rstrip('/') for u in b.get('supporting_urls',[])]}
 if urls_a & urls_b: return True
 def title(s):
  s=re.sub(r'\b(?:NBER|annual|fall|spring|summer|winter|20\d{2}|\d+(?:st|nd|rd|th))\b','',s,flags=re.I)
  return re.sub(r'[^a-z0-9]','',s.lower())
 orgs_a={v.strip().casefold() for x in a['organizers'] for v in x.split('/')}
 orgs_b={v.strip().casefold() for x in b['organizers'] for v in x.split('/')}
 return title(a['name'])==title(b['name']) and a['event_start']==b['event_start'] and bool(orgs_a & orgs_b)
