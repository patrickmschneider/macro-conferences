import json,unittest
from crawler.research_events import discover_research,extract_research,structured_date_evidence
from crawler.extract import clean,event_dates
from crawler.run import round_robin
from crawler.reconcile import verify

class ResearchEventsTests(unittest.TestCase):
 source={'name':'Central Bank','organizer':'Central Bank','link_pattern':r'/research/conference/','region':'Europe'}
 def test_research_paths_discovered(self):
  html='<main><a href="/research/conference/2027/heterogeneity">Heterogeneous Agents Conference 2027</a><a href="/research/conference/2027/speech">Speech at the macroeconomic conference</a></main>'
  links=discover_research(html,'https://example.org/research',self.source)
  self.assertEqual(len(links),1);self.assertIn('/research/',links[0]['url'])
 def test_old_compact_date_urls_excluded(self):
  html='<a href="/research/conference/20200102_macro">Macroeconomics conference</a><a href="/research/conference/20270102_macro">Macroeconomics conference</a>'
  links=discover_research(html,'https://example.org/research',self.source)
  self.assertEqual(len(links),1);self.assertIn('20270102',links[0]['url'])
 def test_host_boundary(self):
  html='<a href="https://unrelated.example/research/conference/2027">Macroeconomics conference 2027</a>'
  self.assertEqual(discover_research(html,'https://example.org/research',self.source),[])
 def test_documents_remain_candidates(self):
  rows=discover_research('<a href="/research/conference/cfp2027.pdf">Macro conference 2027</a>','https://example.org/research',self.source)
  self.assertTrue(rows[0]['document'])
 def test_header_title_survives(self):
  self.assertEqual(clean('<main><header><h1>Macroeconomics Conference 2027</h1></header><p>Research papers</p></main>')[0],'Macroeconomics Conference 2027')
 def test_weekday_range(self):
  self.assertEqual(event_dates('Tuesday, 1 and Wednesday, 2 December 2026')[:2],('2026-12-01','2026-12-02'))
 def test_structured_dates(self):
  event={'@type':'Event','name':'Micro for Macro 2027','startDate':'2027-12-14T09:00:00+11:00','endDate':'2027-12-15T17:00:00+11:00','location':{'address':{'addressLocality':'Sydney','addressCountry':'AU'}}}
  html='<script type="application/ld+json">'+json.dumps(event)+'</script><main><h1>Micro for Macro 2027</h1><p>Workshop on heterogeneous households. Academic research papers. Submission deadline: 17 July 2027.</p></main>'
  r=extract_research(html,'https://example.org/events/m4m-2027',self.source)
  self.assertEqual(r['event_start'],'2027-12-14');self.assertEqual(r['country'],'Australia')
  self.assertEqual(r['organizers'],['Central Bank'])
  self.assertTrue(structured_date_evidence(html,r['evidence']['event_dates']))
  r.update(last_verified='2026-09-18',last_checked='2026-09-18')
  self.assertEqual(verify(r,html,'2026-09-19')['health'],'verified')
 def test_multiple_unmatched_events_not_published(self):
  html='<h1>Research Conferences</h1><p>Macroeconomics conference research June 18-19, 2027</p>'
  self.assertIsNone(extract_research(html,'https://example.org/research/conferences',self.source))
 def test_fair_source_budget(self):
  self.assertEqual(list(round_robin([[1,2,3],['a','b'],['x']])),[1,'a','x',2,'b',3])
if __name__=='__main__':unittest.main()
