"""Daily discovery and evidence rechecks. Run from the repository root."""
import argparse,json
from collections import deque
from datetime import date,datetime,timedelta
from urllib.parse import urljoin
import yaml
from bs4 import BeautifulSoup
from .common import ROOT,read,write,now
from .fetch import Fetcher
from .extract import clean,discover,extract,topics
from .research_events import discover_research,extract_research
from .feeds import parse_rss,relevant,feed_record,verify_feed
from .reconcile import verify,duplicate
from .validate import validate

ALERT_AFTER=3        # consecutive failed runs before a source raises an alert
QUIET_DAYS=30        # no new record for this long suggests discovery has stopped working
HEALTHY_SHARE=0.75   # share of sources that must fetch for a run to count as successful
MODES={'research-events':'evidence-based discovery','cepr-rss':'events feed','watch':'watch only'}

def round_robin(groups):
 queues=[deque(group) for group in groups if group]
 while queues:
  for q in list(queues):
   yield q.popleft()
   if not q:queues.remove(q)

def urls_of(r):return {r['source_url'].rstrip('/'),*[u.rstrip('/') for u in r.get('supporting_urls',[])]}

def benchmark_status(records,entries=None):
 """Known calls the tracker must find (data/benchmark.json). Each entry is a real miss or a
 must-have call, so a regression in coverage raises an alert instead of going unnoticed."""
 path=ROOT/'data/benchmark.json'
 if entries is None:entries=json.loads(path.read_text()) if path.exists() else []
 result=[]
 for b in entries:
  match=next((r for r in records if b['url'].rstrip('/') in urls_of(r)),None)
  found=bool(match) and (not b.get('deadline') or any(c.get('deadline')==b['deadline'] for c in match['calls']))
  result.append(dict(name=b['name'],url=b['url'],deadline=b.get('deadline'),event_start=b.get('event_start'),found=found,record_id=match['id'] if match else None))
 return result

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int,default=240);parser.add_argument('--source',action='append');parser.add_argument('--group');args=parser.parse_args()
 stamp=now();today=date.today().isoformat();records=read('data/conferences.json');validate(records)
 old_status=read('data/run-status.json');fetcher=Fetcher();statuses=[];groups=[];published=0
 registry=yaml.safe_load((ROOT/'sources.yaml').read_text())['sources']
 enabled={s['id'] for s in registry if s['enabled']}
 pending_by_url={x['url']:x for x in read('data/candidates.json') if x['source'] in enabled} if (ROOT/'data/candidates.json').exists() else {}
 selected=[s for s in registry if s['enabled'] and (not args.source or s['id'] in args.source) and (not args.group or s.get('coverage_group')==args.group)]
 feed_items={};fetched_feeds=set();discovered=set()
 for source in selected:
  item={'id':source['id'],'name':source['name'],'url':source['url'],'checked_at':stamp,'state':'ok','mode':'series index' if source.get('series') else MODES.get(source['adapter'],'discovery'),'candidate_links':0,'published':0}
  candidates=[]
  try:
   listing_urls=[source['url'],*source.get('listing_urls',[])]
   for base in listing_urls:
    for page in range(source['max_pages']):
     url=base+('?' if '?' not in base else '&')+f'page={page}' if page else base
     html=fetcher.get(url)
     if source['adapter']=='nber-json':
      payload=json.loads(html);found=[{'url':urljoin(url,x['url'])} for x in payload['results'] if topics(x['title'])]
     elif source['adapter']=='cepr-rss':
      items=parse_rss(html)
      if not items:raise ValueError('Feed empty or unreadable')
      feed_items.update({x['url']:x for x in items});fetched_feeds.add(url)
      found=[{'url':x['url'],'feed_item':x} for x in items if relevant(x)]
     else:
      # Judge emptiness on the whole page: clean() trims at "Related content" markers,
      # which suits single event pages but can blank out a listing.
      if len(BeautifulSoup(html,'html.parser').get_text(' ',strip=True))<200:raise ValueError('Source content empty or incomplete (JavaScript-rendered?)')
      found=discover_research(html,url,source) if source['adapter']=='research-events' else [{'url':u} for u in discover(html,url)]
     candidates.extend((x,source) for x in found)
     if not found:break
   unique={c[0]['url']:c for c in candidates}
   # Rotate bounded work across the source's candidates, rather than permanently
   # starving the same lower entries. Previously verified URLs cost no requests.
   candidates=sorted(unique.values(),key=lambda c:pending_by_url.get(c[0]['url'],{}).get('last_checked',''));item['candidate_links']=len(candidates)
   item['discovery_state']='links_found' if candidates else 'no_candidate_links'
   discovered.update(unique)
  except Exception as ex:item['state']='failed';item['discovery_state']='unavailable';item['error']=str(ex)[:200]
  groups.append(candidates);statuses.append(item);print(source['id'],item['state'],item['candidate_links'],flush=True)
 # A listing that fetched today and no longer links a candidate has dropped it.
 ok_sources={s['id'] for s in statuses if s['state']=='ok'}
 pending_by_url={u:x for u,x in pending_by_url.items() if x['source'] not in ok_sources or u in discovered}
 selected_domains={s['url'].split('/')[2] for s in selected}
 for i,record in enumerate(records):
  if (record.get('event_end') or record.get('event_start') or '9999')<today:continue
  if (args.source or args.group) and record['source_url'].split('/')[2] not in selected_domains:continue
  e=(record.get('evidence') or {}).get('event_dates') or {}
  if e.get('kind')=='feed':
   # Feed records are rechecked against today's feed, never against the blocked page.
   if e['url'] in fetched_feeds:records[i]=verify_feed(record,feed_items,stamp)
   else:
    records[i]['last_checked']=stamp
    if records[i]['health']!='needs_verification':records[i]['health']='fetch_failed'
   continue
  try:records[i]=verify(record,fetcher.get(record['source_url']),stamp)
  except Exception as ex:
   records[i]['last_checked']=stamp
   if records[i]['health']!='needs_verification':records[i]['health']='fetch_failed'
   records[i]['check_error']=str(ex)[:200]
 seen=set();processed=0;per_source={}
 for candidate,source in round_robin(groups):
  url=candidate['url'];from_feed='feed_item' in candidate
  if url in seen:continue
  seen.add(url)
  if any(url.rstrip('/') in urls_of(r) for r in records):
   pending_by_url.pop(url,None);continue
  # Feed items cost no request, so only the per-source cap bounds them.
  if (not from_feed and processed>=args.limit) or per_source.get(source['id'],0)>=source.get('max_candidates',30):
   pending_by_url.setdefault(url,{'url':url,'source':source['id'],'reason':'Deferred by run budget'});continue
  processed+=0 if from_feed else 1;per_source[source['id']]=per_source.get(source['id'],0)+1
  def pending(reason):pending_by_url[url]={'url':url,'source':source['id'],'reason':reason,'last_checked':stamp}
  try:
   if source['adapter']=='watch':pending('Discovery lead: no trusted event adapter yet');continue
   if candidate.get('document'):pending('Document announcement: PDF adapter required');continue
   if from_feed:r=feed_record(candidate['feed_item'],source,source['url']);method='events feed'
   else:
    html=fetcher.get(url);method='deterministic source extraction'
    r=extract_research(html,url,source) if source['adapter']=='research-events' else extract(html,url,source.get('organizer','NBER' if source['adapter'].startswith('nber') else 'CEPR'))
   if not r:pending('No unambiguous, relevant single-event record extracted');continue
   if r['event_start']<today or r['event_start']>f'{date.today().year+2}-12-31':pending('Outside publication date window');continue
   if source.get('series_id') and not r.get('series_id'):r['series_id']=source['series_id']
   r.update(discovered_at=stamp,last_checked=stamp,last_verified=stamp,verification_method=method,source_id=source['id'])
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
 # Health. A scoped pilot must not erase other institutions' reports; disabled sources drop out.
 merged={s['id']:s for s in old_status.get('sources',[]) if s['id'] in enabled}
 for s in statuses:
  prev=merged.get(s['id'],{})
  if s['state']=='failed':
   s['consecutive_failures']=prev.get('consecutive_failures',0)+1
   s['failing_since']=prev.get('failing_since') if prev.get('consecutive_failures') else stamp[:10]
  else:s['consecutive_failures']=0
  s['last_ok']=stamp if s['state']=='ok' else prev.get('last_ok')
  merged[s['id']]=s
 sources=list(merged.values());failed=sum(s['state']=='failed' for s in sources)
 checked=sum(r.get('last_verified')==stamp for r in records)
 bench=benchmark_status(records)
 latest_added=max((r.get('discovered_at') or '' for r in records),default='')
 alerts=[{'key':f"source:{s['id']}",'text':f"{s['name']} has failed every run since {s.get('failing_since') or 'an earlier run'} ({s.get('error','unknown error')[:120]})"} for s in sources if s.get('consecutive_failures',0)>=ALERT_AFTER]
 alerts+=[{'key':f"benchmark:{b['url']}",'text':f"Known call not found: {b['name']} ({b['url']})"} for b in bench if not b['found'] and max(b['deadline'] or '',b['event_start'] or '')>=today]
 if latest_added and datetime.fromisoformat(latest_added).date()<date.today()-timedelta(days=QUIET_DAYS):
  alerts.append({'key':'quiet','text':f'No new event has been added since {latest_added[:10]}; discovery may have stopped working.'})
 ok_share=sum(s['state']=='ok' for s in statuses)/max(1,len(statuses));scoped=bool(args.source or args.group)
 state='failed' if statuses and ok_share==0 else 'partial' if alerts or ok_share<HEALTHY_SHARE else 'ok'
 write('data/run-status.json',dict(state=state,last_run=stamp,
  last_successful_run=stamp if not scoped and ok_share>=HEALTHY_SHARE else old_status.get('last_successful_run'),
  last_added=latest_added or None,sources=sources,added=published,verified=checked,alerts=alerts if not scoped else old_status.get('alerts',[]),benchmark=bench,
  message=f'{checked} event records verified; {published} added in latest run. {failed} of {len(sources)} sources failed their latest check. Discovery uses supported event dates; document-only and ambiguous announcements remain unpublished leads.'))
 print(f'{state}: {checked} verified, {published} added, {failed} failed sources, {len(alerts)} alerts')
if __name__=='__main__':main()
