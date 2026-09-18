"""Idempotent central-bank/e61 source registry expansion."""
from pathlib import Path
import yaml
R=Path(__file__).resolve().parents[1]
# Institution, primary listing, research-event URL pattern. Publication requires a
# topical single-event page and supported dates, never the institution name alone.
S=[
('boe','Bank of England','https://www.bankofengland.co.uk/events',r'/events/20\d{2}/','Europe'),
('fed-board','Federal Reserve Board','https://www.federalreserve.gov/conferences.htm',r'/conferences/','North America'),
('fed-boston','Federal Reserve Bank of Boston','https://www.bostonfed.org/news-and-events/events.aspx',r'/events/','North America'),
('fed-newyork','Federal Reserve Bank of New York','https://www.newyorkfed.org/newsevents/events/index',r'/(?:research/conference|newsevents/events)/','North America'),
('fed-philadelphia','Federal Reserve Bank of Philadelphia','https://www.philadelphiafed.org/calendar-of-events',r'/calendar-of-events/','North America'),
('fed-cleveland','Federal Reserve Bank of Cleveland','https://www.clevelandfed.org/events',r'/events/','North America'),
('fed-richmond','Federal Reserve Bank of Richmond','https://www.richmondfed.org/conferences_and_events',r'/conferences_and_events/','North America'),
('fed-atlanta','Federal Reserve Bank of Atlanta','https://www.atlantafed.org/news-and-events/events',r'/events/20\d{2}/','North America'),
('fed-chicago','Federal Reserve Bank of Chicago','https://www.chicagofed.org/events/research-conferences',r'/events/20\d{2}/','North America'),
('fed-stlouis','Federal Reserve Bank of St. Louis','https://www.stlouisfed.org/research/specialized-research-conferences',r'/(?:research|events)/','North America'),
('fed-minneapolis','Federal Reserve Bank of Minneapolis','https://www.minneapolisfed.org/economic-research/conferences',r'/(?:events|conferences)/','North America'),
('fed-kansascity','Federal Reserve Bank of Kansas City','https://www.kansascityfed.org/research/',r'/(?:research|events)/','North America'),
('fed-dallas','Federal Reserve Bank of Dallas','https://www.dallasfed.org/events',r'/(?:research/events|events)/','North America'),
('fed-sanfrancisco','Federal Reserve Bank of San Francisco','https://www.frbsf.org/news-and-media/events/',r'/(?:news-and-media/events|economic-research/events)/','North America'),
('bank-canada','Bank of Canada','https://www.bankofcanada.ca/research/engaging-with-the-research-community/conferences-workshops/',r'/(?:20\d{2}/|research/)','North America'),
('rbnz','Reserve Bank of New Zealand','https://www.rbnz.govt.nz/research-and-publications/research',r'/(?:research|news-and-events|events)/','Oceania'),
('bis-research','Bank for International Settlements','https://www.bis.org/forum/research.htm',r'/(?:events|forum|am_conferences)/','Global'),
('bis-events','BIS events','https://www.bis.org/media/events',r'/events/','Global'),
('bis-americas','BIS Americas research conferences','https://www.bis.org/am_conferences/index.htm',r'/(?:events|am_conferences)/','Global'),
('bundesbank','Deutsche Bundesbank','https://www.bundesbank.de/en/bundesbank/research/conferences',r'/research/conferences/','Europe'),
('banque-france','Banque de France','https://www.banque-france.fr/en/publications-and-research/economic-research',r'/(?:events|evenements|conferences|publications-and-research)/','Europe'),
('banca-italia','Banca d’Italia','https://www.bancaditalia.it/media/agenda/index.html',r'/(?:media/agenda|pubblicazioni/altri-atti-convegni)/','Europe'),
('banco-espana','Banco de España','https://www.bde.es/wbe/en/noticias-eventos/eventos/conferencias/',r'/conferencias/','Europe'),
('snb','Swiss National Bank','https://www.snb.ch/en/the-snb/mandates-goals/research',r'/(?:research|the-snb/mandates-goals/research|mmr)/','Europe'),
('riksbank','Sveriges Riksbank','https://www.riksbank.se/en-gb/press-and-published/conferences/',r'/conferences/','Europe'),
('norges','Norges Bank','https://www.norges-bank.no/en/topics/Research/Conferences/',r'/(?:Conferences|conferences)/','Europe'),
('bank-finland','Bank of Finland','https://www.suomenpankki.fi/en/research/seminars-and-conferences/',r'/(?:events|seminars-and-conferences)/','Europe'),
('dnb','De Nederlandsche Bank','https://www.dnb.nl/en/research/dnb-research-conferences/',r'/(?:research|events|general-news)/','Europe'),
('oenb','Oesterreichische Nationalbank','https://www.oenb.at/Termine.html',r'/(?:Termine|en/Calendar|en/Monetary-Policy)/','Europe'),
('bank-ireland','Central Bank of Ireland','https://www.centralbank.ie/research-exchange/research-engagement-programme/research-events-seminars',r'/(?:events|research-exchange)/','Europe'),
('e61','e61 Institute','https://e61.in/events/',r'/events/','Oceania'),
]
p=R/'sources.yaml';doc=yaml.safe_load(p.read_text());existing={s['id'] for s in doc['sources']}
for id,name,url,pattern,region in S:
 if id in existing: continue
 doc['sources'].append(dict(id=id,name=name,url=url,organizer=name,adapter='research-events',enabled=True,max_pages=1,max_candidates=8,link_pattern=pattern,region=region,scope='Academic macro, household finance and pensions conferences; excludes speeches, press briefings, training and standalone seminars.',coverage_group='Central banks and e61'))
for s in doc['sources']:
 if s['id']=='ecb-annual':
  s.update(name='European Central Bank conferences',organizer='European Central Bank',adapter='research-events',link_pattern=r'/press/conferences/html/20\d{6}[^/]*\.en\.html',max_candidates=20,coverage_group='Central banks and e61')
 if s['id']=='rba-quant':
  s.update(organizer='Reserve Bank of Australia',adapter='research-events',link_pattern=r'/publications/(?:workshops|confs)/',max_candidates=8,coverage_group='Central banks and e61')
p.write_text(yaml.safe_dump(doc,sort_keys=False,allow_unicode=True))
print('Added',len(S),'institutional listings')
