import hashlib, json, time
from urllib.parse import urlparse
from pathlib import Path
import requests
from .common import ROOT

class Fetcher:
 def __init__(self):
  self.session=requests.Session(); self.session.headers['User-Agent']='MacroConferenceTracker/0.1 (+https://github.com/patrickmschneider/macro-conferences)'
  self.cache=ROOT/'.cache/http'; self.cache.mkdir(parents=True,exist_ok=True); self.last={}; self.memo={}
 def get(self,url):
  if url in self.memo: return self.memo[url]
  host=urlparse(url).hostname
  if urlparse(url).scheme!='https' or not host: raise ValueError('Only HTTPS public sources supported')
  delay=max(0,0.5-(time.monotonic()-self.last.get(host,0)))
  if delay: time.sleep(delay)
  p=self.cache/(hashlib.sha256(url.encode()).hexdigest()+'.json')
  old=json.loads(p.read_text()) if p.exists() else {}
  headers={}
  if old.get('etag'): headers['If-None-Match']=old['etag']
  if old.get('modified'): headers['If-Modified-Since']=old['modified']
  self.last[host]=time.monotonic()
  response=self.session.get(url,headers=headers,timeout=25)
  # Do not retry access denials or challenge pages.
  if response.status_code in (429,500,502,503,504):
   time.sleep(2); response=self.session.get(url,headers=headers,timeout=25)
  if response.status_code==304 and old.get('html'): html=old['html']
  else:
   response.raise_for_status()
   if not any(t in response.headers.get('Content-Type','') for t in ['text/html','application/json']): raise ValueError('Non-HTML source needs a dedicated adapter')
   html=response.text
   if len(html)>5_000_000: raise ValueError('Source exceeds size limit')
   if any(x in html[:15000].lower() for x in ['sorry, you have been blocked','just a moment...','verify you are human']): raise ValueError('Source access challenge')
   p.write_text(json.dumps(dict(html=html,etag=response.headers.get('ETag'),modified=response.headers.get('Last-Modified'))))
  self.memo[url]=html
  return html
