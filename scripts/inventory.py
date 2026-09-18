import json
from pathlib import Path
import yaml
R=Path(__file__).resolve().parents[1]
events=json.loads((R/'data/conferences.json').read_text()); series=[]
for e in events:
 if e['series_id'] and e['series_id'] not in [s['id'] for s in series]:
  series.append(dict(id=e['series_id'],name=e['name'].replace(', Fall 2026',''),organizer=' / '.join(e['organizers']),topics=e['topics'],region=e['region'],url=e['source_url'],inclusion_rationale='Established academic meeting organised by the named research institution or network; edition and research scope verified against its announcement.',review_status='verified',monitoring='edition checks'))
extra=[
('cebra','CEBRA Annual Meeting','CEBRA',['Monetary policy','Financial stability'],'Global','https://cebra.org/events/annual-meeting/','Central-bank research association; academic committee and contributed research programme.'),
('sce','Computing in Economics and Finance','Society for Computational Economics',['Computational macro'],'Global','https://comp-econ.com/','Scientific society devoted to computational economics, including dynamic macroeconomic systems.'),
('wams','Workshop of the Australasian Macroeconomics Society','AMS',['General macro','Business cycles'],'Oceania','https://www.ausmacro.com/workshops/','Long-running macro workshop with university hosts and established macro researchers as invited speakers.'),
('netspar','Netspar International Pension Workshop','Netspar',['Pensions and retirement','Household finance'],'Europe','https://www.netspar.nl/agenda/ipw-international-pension-workshop-2026/','Specialist academic pension network with contributed research on saving, retirement and pension policy.'),
('bse-macrofinance','BSE Summer Forum: Macroeconomics and Finance','Barcelona School of Economics',['Macro-finance','Financial stability'],'Europe','https://bse.eu/summer-forum/workshops/macroeconomics-and-finance','Specialist research workshop in the BSE Summer Forum.'),
('bse-macrodevelopment','BSE Summer Forum: Macro-development','Barcelona School of Economics',['Growth'],'Europe','https://sites.google.com/bse.eu/summerforum2026/home','Summer Forum research workshop family; separate workshop announcements need monitoring.'),
('midwest','Midwest Macroeconomics Meetings','Rotating university hosts',['General macro'],'North America','https://www.depts.ttu.edu/economics/news-announcements/midwest-macroeconomics-meetings-2026.php','University-hosted contributed-paper macroeconomics meetings.'),
('nber-si','NBER Summer Institute: macro programmes','NBER',['General macro','Labour macro','Growth','Heterogeneous agents','Monetary policy'],'North America','https://www.nber.org/conferences/summer-institute-2026','Programme includes micro data and macro models, growth, monetary economics and dynamic-equilibrium methods. Track individual workshops, not one undifferentiated call.'),
('ecb-annual','ECB Annual Research Conference','European Central Bank',['International macro','Monetary policy'],'Europe','https://www.ecb.europa.eu/press/conferences/html/index.en.html','Research conference connecting academic contributors and central-bank researchers.'),
('ipra','International Pension Research Association Conference','CEPAR / OECD / Netspar / Wharton PRC',['Pensions and retirement'],'Global','https://www.cepar.edu.au/event/12th-international-pension-research-association-ipra-conference','Academic pension research network; next-edition details need extraction.'),
('ifs-hf','LSE–IFS–UCL–CEPR–Imperial Household Finance Workshop','IFS and university partners',['Household finance'],'Europe','https://ifs.org.uk/events/lse-ifs-ucl-cepr-imperial-business-school-workshop-household-finance-0','Programme includes household spending, income shocks, debt and consumer choice.'),
]
for id,name,org,topics,region,url,why in extra:
 series.append(dict(id=id,name=name,organizer=org,topics=topics,region=region,url=url,inclusion_rationale=why,review_status='verified',monitoring='discovery pilot'))
# Flagship leads are explicitly distinguished from sources already inspected.
for id,name,org,topics,url in [
 ('eea','EEA Congress','European Economic Association',['General macro'],'https://www.eeassoc.org/'),
 ('es','Econometric Society regional meetings','Econometric Society',['General macro'],'https://www.econometricsociety.org/'),
 ('aea','ASSA / AEA Annual Meeting','American Economic Association',['General macro'],'https://www.aeaweb.org/conference/'),
 ('essim','European Summer Symposium in International Macroeconomics','CEPR',['International macro','General macro'],'https://cepr.org/events'),
 ('carnegie','Carnegie-Rochester-NYU Conference','Carnegie Mellon / Rochester / NYU',['General macro','Monetary policy'],'https://www.carnegie-rochester.rochester.edu/'),
 ('eabcn','EABCN research conferences','Euro Area Business Cycle Network',['Business cycles','Monetary policy'],'https://eabcn.org/'),
 ('laef','LAEF research conferences','UC Santa Barbara',['General macro','Labour macro'],'https://laef.ucsb.edu/'),
]:
 series.append(dict(id=id,name=name,organizer=org,topics=topics,region='Global',url=url,inclusion_rationale='Priority coverage lead; primary announcement channel and current programme still need review.',review_status='pending',monitoring='not yet automated'))
(R/'data/series.json').write_text(json.dumps(series,ensure_ascii=False,indent=2)+'\n')
sources=[
 dict(id='nber-calls',name='NBER calls for papers',url='https://www.nber.org/calls-papers-and-proposals',adapter='nber',enabled=True,max_pages=1),
 dict(id='nber-events',name='NBER conferences',url='https://www.nber.org/conferences',adapter='nber',enabled=True,max_pages=2),
 dict(id='cepr-calls',name='CEPR calls for papers',url='https://cepr.org/events/open-calls-papers',adapter='cepr',enabled=True,max_pages=2),
 dict(id='cepr-events',name='CEPR forthcoming events',url='https://cepr.org/events/forthcoming-events',adapter='cepr',enabled=True,max_pages=7),
]
seen={s['url'] for s in sources}
for s in series:
 if s['url'] in seen: continue
 seen.add(s['url'])
 sources.append(dict(id=s['id'],name=s['name'],url=s['url'],adapter='watch',enabled=s['review_status']=='verified',max_pages=1))
(R/'sources.yaml').write_text(yaml.safe_dump({'version':1,'sources':sources},sort_keys=False,allow_unicode=True))
(R/'data/run-status.json').write_text(json.dumps({'state':'seeded','last_run':None,'last_successful_run':None,'message':'Initial primary-source review on 18 September 2026. Scheduled collection has not run yet.','sources':[]},indent=2)+'\n')
print(len(series),'series;',len(sources),'sources')
