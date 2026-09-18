"""Daily discovery and evidence rechecks. Run from the repository root."""
import argparse,json
from collections import deque
from datetime import date
from urllib.parse import urljoin
import yaml
from .common import ROOT,read,write,now
from .fetch import Fetcher
from .extract import clean,discover,extract,topics
from .research_events import discover_research,extract_research
from .reconcile import verify,duplicate
from .validate import validate

def round_robin(groups):
 queues=[deque(group) for group in groups if group]
 while queues:
  for q in list(queues):
   yield q.popleft()
   if not q:queues.remove(q)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int,default=240);parser.add_argument('--source',action='append');parser.add_argument('--group');args=parser.parse_args()
 stamp=now();records=read('data/conferences.json');validate(records)
 old_status=read('data/run-status.json');fetcher=Fetcher();statuses=[];groups=[];published=0
 pending_by_url={x['url']:x for x in read('data/candidates.json')} if (ROOT/'data/candidates.json').exists() else {}
 registry=yaml.safe_load((ROOT/'sources.yaml').read_text())['sources']
 selected=[s for s in registry if s['enabled'] and (not args.source or s['id'] in args.source) and (not args.group or s.get('coverage_group')==args.group)]
 for source in selected:
  item={'id':source['id'],'name':source['name'],'url':source['url'],'checked_at':stamp,'state':'ok','mode':'evidence-based discovery' if source['adapter']=='research-events' else 'discovery' if source['adapter']!='watch' else 'watch only','candidate_links':0,'published':0}
  candidates=[]
  try:
   listing_urls=[source['url'],*source.get('listing_urls',[])]
   for base in listing_urls:
    for page in range(source['max_pages']):
     url=base+('?' if '?' not in base else '&')+f'page={page}' if page else base
     html=fetcher.get(url)
     if source['adapter']=='nber-json':
      payload=json.loads(html);found=[{'url':urljoin(url,x['url'])} for x in payload['results'] if topics(x['title'])]
     else:
      title,text,_=clean(html)
      if len(text)<80:raise ValueError('Source content empty or incomplete')
      found=discover_research(html,url,source) if source['adapter']=='research-events' else [{'url':u} for u in discover(html,url)]
     candidates.extend((x,source) for x in found)
     if not found:break
   unique={c[0]['url']:c for c in candidates}
   # Rotate bounded work across the source's candidates, rather than permanently
   # starving the same lower entries. Previously verified URLs cost no requests.
   candidates=sorted(unique.values(),key=lambda c:pending_by_url.get(c[0]['url'],{}).get('last_checked',''));item['candidate_links']=len(candidates)
   item['discovery_state']='links_found' if candidates else 'no_candidate_links'
  except Exception as ex:item['state']='failed';item['discovery_state']='unavailable';item['error']=str(ex)[:200]
  groups.append(candidates);statuses.append(item);print(source['id'],item['state'],item['candidate_links'],flush=True)
 selected_domains={s['url'].split('/')[2] for s in selected}
 for i,record in enumerate(records):
  if (record.get('event_end') or record.get('event_start') or '9999')<date.today().isoformat():continue
  if (args.source or args.group) and record['source_url'].split('/')[2] not in selected_domains:continue
  try:records[i]=verify(record,fetcher.get(record['source_url']),stamp)
  except Exception as ex:
   records[i]['last_checked']=stamp
   if records[i]['health']!='needs_verification':records[i]['health']='fetch_failed'
   records[i]['check_error']=str(ex)[:200]
 seen=set();processed=0;per_source={}
 for candidate,source in round_robin(groups):
  url=candidate['url']
  if url in seen:continue
  seen.add(url)
  if any(url.rstrip('/') in {r['source_url'].rstrip('/'),*[u.rstrip('/') for u in r.get('supporting_urls',[])]} for r in records):
   pending_by_url.pop(url,None);continue
  if processed>=args.limit or per_source.get(source['id'],0)>=source.get('max_candidates',30):
   pending_by_url.setdefault(url,{'url':url,'source':source['id'],'reason':'Deferred by run budget'});continue
  processed+=1;per_source[source['id']]=per_source.get(source['id'],0)+1
  def pending(reason):pending_by_url[url]={'url':url,'source':source['id'],'reason':reason,'last_checked':stamp}
  try:
   if source['adapter']=='watch':pending('Discovery lead: no trusted event adapter yet');continue
   if candidate.get('document'):pending('Document announcement: PDF adapter required');continue
   html=fetcher.get(url)
   r=extract_research(html,url,source) if source['adapter']=='research-events' else extract(html,url,source.get('organizer','NBER' if source['adapter'].startswith('nber') else 'CEPR'))
   if not r:pending('No unambiguous, relevant single-event record extracted');continue
   if r['event_start']<date.today().isoformat() or r['event_start']>f'{date.today().year+2}-12-31':pending('Outside publication date window');continue
   r.update(discovered_at=stamp,last_checked=stamp,last_verified=stamp,verification_method='deterministic source extraction',source_id=source['id'])
   validate([r]);match=next((existing for existing in records if duplicate(r,existing)),None)
   if match:
    match.setdefault('supporting_urls',[])
    if url not in match['supporting_urls']:match['supporting_urls'].append(url)
   else:
    records.append(r);published+=1
    next(x for x in statuses if x['id']==source['id'])['published']+=1
   pending_by_url.pop(url,None)
  except Exception as ex:pending(str(ex)[:180])
 validate(records);write('data/conferences.json',records);write('data/candidates.json',list(pending_by_url.values()))
 # A scoped pilot must not erase other institutions' health reports.
 merged={s['id']:s for s in old_status.get('sources',[])};merged.update({s['id']:s for s in statuses})
 failed=sum(s['state']=='failed' for s in merged.values());checked=sum(r.get('last_verified')==stamp for r in records)
 state='partial' if failed or any(r['health']!='verified' for r in records if (r.get('event_end') or r['event_start'])>=date.today().isoformat()) else 'ok'
 if statuses and all(s['state']=='failed' for s in statuses):state='failed'
 write('data/run-status.json',dict(state=state,last_run=stamp,last_successful_run=stamp if state=='ok' and not (args.source or args.group) else old_status.get('last_successful_run'),sources=list(merged.values()),added=published,verified=checked,message=f'{checked} event records verified; {published} added in latest run. {failed} sources have a failed latest check. Discovery uses supported event dates; document-only and ambiguous announcements remain unpublished leads.'))
 print(f'{state}: {checked} verified, {published} added, {failed} failed sources')
if __name__=='__main__':main()
