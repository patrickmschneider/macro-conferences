"""Daily discovery and evidence rechecks. Run from the repository root."""
import argparse,copy,hashlib,json
from urllib.parse import urljoin
from datetime import date
import yaml
from .common import ROOT,read,write,now
from .fetch import Fetcher
from .extract import clean,discover,extract,topics
from .reconcile import verify,duplicate
from .validate import validate

def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--limit',type=int,default=120); parser.add_argument('--source',action='append'); args=parser.parse_args()
 stamp=now(); records=read('data/conferences.json'); validate(records)
 old_status=read('data/run-status.json'); fetcher=Fetcher(); statuses=[]; candidates=[]; published=0
 registry=yaml.safe_load((ROOT/'sources.yaml').read_text())['sources']
 for source in registry:
  if not source['enabled'] or args.source and source['id'] not in args.source: continue
  item={'id':source['id'],'name':source['name'],'url':source['url'],'checked_at':stamp,'state':'ok','mode':'discovery' if source['adapter']!='watch' else 'watch only'}
  try:
   for page in range(source['max_pages']):
    url=source['url']+('?' if '?' not in source['url'] else '&')+f'page={page}' if page else source['url']
    html=fetcher.get(url)
    if source['adapter']=='nber-json':
     payload=json.loads(html)
     found=[urljoin(url,x['url']) for x in payload['results'] if topics(x['title'])]
     candidates.extend((u,source) for u in found)
     continue
    title,text,_=clean(html)
    if len(text)<80: raise ValueError('Source content empty or incomplete')
    found=discover(html,url)
    if source['adapter']!='watch': candidates.extend((u,source) for u in found)
    elif found: candidates.extend((u,source) for u in found[:10])
    if not found: break
   item['candidate_links']=len(found)
  except Exception as ex: item['state']='failed'; item['error']=str(ex)[:200]
  statuses.append(item)
  print(source['id'],item['state'],flush=True)
 # Always recheck upcoming records, independently from discovery failures.
 for i,record in enumerate(records):
  if (record.get('event_end') or record.get('event_start') or '9999')<date.today().isoformat(): continue
  if args.source:
   domains={s['url'].split('/')[2] for s in registry if s['id'] in args.source}
   if record['source_url'].split('/')[2] not in domains: continue
  try: records[i]=verify(record,fetcher.get(record['source_url']),stamp)
  except Exception as ex:
   records[i]['last_checked']=stamp
   if records[i]['health']!='needs_verification': records[i]['health']='fetch_failed'
   records[i]['check_error']=str(ex)[:200]
 pending=[]; seen=set()
 for url,source in candidates:
  if url in seen: continue
  seen.add(url)
  if len(seen)>args.limit: break
  if any(url.rstrip('/') in {r['source_url'].rstrip('/'),*[u.rstrip('/') for u in r.get('supporting_urls',[])]} for r in records): continue
  try:
   if source['adapter']=='watch':
    pending.append({'url':url,'source':source['id'],'reason':'Discovery lead: no trusted event adapter yet'}); continue
   html=fetcher.get(url); r=extract(html,url,'NBER' if source['adapter'].startswith('nber') else 'CEPR')
   if not r: continue
   if r['event_start']<date.today().isoformat() or r['event_start']>f'{date.today().year+2}-12-31': continue
   r.update(discovered_at=stamp,last_checked=stamp,last_verified=stamp,verification_method='deterministic source extraction')
   validate([r])
   match=next((existing for existing in records if duplicate(r,existing)),None)
   if match:
    match.setdefault('supporting_urls',[])
    if url not in match['supporting_urls']: match['supporting_urls'].append(url)
   else: records.append(r); published+=1
  except Exception as ex: pending.append({'url':url,'source':source['id'],'reason':str(ex)[:160]})
 validate(records)
 write('data/conferences.json',records)
 write('data/candidates.json',pending)
 failed=sum(s['state']=='failed' for s in statuses)
 checked=sum(r.get('last_verified')==stamp for r in records)
 state='failed' if statuses and failed==len(statuses) else 'partial' if failed or any(r['health']!='verified' for r in records if (r.get('event_end') or r['event_start'])>=date.today().isoformat()) else 'ok'
 write('data/run-status.json',dict(state=state,last_run=stamp,last_successful_run=stamp if state=='ok' else old_status.get('last_successful_run'),sources=statuses,added=published,verified=checked,message=f'{checked} event records verified; {published} added; {failed} source checks failed. Watch-only sources collect leads but do not yet publish new events.'))
 print(f'{state}: {checked} verified, {published} added, {failed} failed sources')
if __name__=='__main__': main()
