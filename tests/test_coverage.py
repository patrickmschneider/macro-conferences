"""Regression tests for the wider net: embedded pages, single-day events, series index pages,
the CEPR events feed, cross-source deduplication and coverage alerts."""
import copy,unittest
from pathlib import Path
from crawler.extract import clean,event_dates,event_date_detail,topics
from crawler.research_events import discover_research,extract_research
from crawler.feeds import parse_rss,relevant,feed_record,verify_feed
from crawler.reconcile import duplicate
from crawler.fetch import Fetcher
from crawler.run import benchmark_status

FIX=Path(__file__).parent/'fixtures'
MIAMI={'name':'Miami Macro','organizer':'University of Miami','series':True,'series_id':'miami-macro',
 'link_pattern':r'^/conferences/(?:miamimacro|mfp-miami)\d{2}/?$','topics':['General macro'],'region':'North America'}
RSS='''<?xml version="1.0" encoding="utf-8"?><rss xmlns:cepr="https://cepr.org/rss/ns/1.0" version="2.0"><channel><title>Events</title>
<item><title>34th CEPR European Summer Symposium in International Macroeconomics (ESSIM)</title><link>https://cepr.org/events/essim-2027</link>
<description>A joint meeting of the IMF, MEF and MG programmes.</description><cepr:type>Conference</cepr:type><cepr:event_start>2027-05-26T09:00:00+0100</cepr:event_start>
<cepr:event_end>2027-05-28T17:00:00+0100</cepr:event_end><cepr:event_series></cepr:event_series><cepr:city>Tarragona</cepr:city><cepr:country>Spain</cepr:country><cepr:event_format>in-person</cepr:event_format></item>
<item><title>Virtual Seminar on Monetary Economics 16</title><link>https://cepr.org/events/vsme-16</link><description>Monetary policy seminar.</description>
<cepr:type>Webinar</cepr:type><cepr:event_start>2027-02-04T15:00:00+0000</cepr:event_start><cepr:event_end>2027-02-04T16:00:00+0000</cepr:event_end><cepr:city>Online</cepr:city><cepr:country>United Kingdom</cepr:country><cepr:event_format>online</cepr:event_format></item>
<item><title>27th CEPR-JIE Conference on Applied Industrial Organization</title><link>https://cepr.org/events/io-2027</link><description>Applied IO.</description>
<cepr:type>Conference</cepr:type><cepr:event_start>2027-05-27T09:00:00+0200</cepr:event_start><cepr:event_end>2027-05-28T17:00:00+0200</cepr:event_end><cepr:city>Bergen</cepr:city><cepr:country>Norway</cepr:country><cepr:event_format>in-person</cepr:event_format></item>
</channel></rss>'''

class EmbeddedPageTests(unittest.TestCase):
 def test_google_sites_embed_is_read(self):
  title,text,_=clean((FIX/'miami-macro-2027.html').read_text())
  self.assertEqual(title,'Miami Macro 2027');self.assertIn('Submission deadline December 15, 2026',text)
  self.assertNotIn('var x',text)
 def test_miami_macro_extracted_from_series_page(self):
  html=(FIX/'miami-macro-2027.html').read_text()
  r=extract_research(html,'https://www.noahwilliams.xyz/conferences/miamimacro27',MIAMI)
  self.assertEqual((r['name'],r['event_start'],r['event_end']),('Miami Macro 2027','2027-02-05',None))
  self.assertEqual(r['calls'][0]['deadline'],'2026-12-15');self.assertEqual(r['region'],'North America')
  self.assertIn('General macro',r['topics'])
 def test_series_links_need_no_topical_label(self):
  links=discover_research((FIX/'miami-macro-2027.html').read_text(),'https://www.noahwilliams.xyz/conferences',MIAMI)
  self.assertEqual([x['url'] for x in links],['https://www.noahwilliams.xyz/conferences/miamimacro27','https://www.noahwilliams.xyz/conferences/mfp-miami26'])
 def test_unvetted_source_still_requires_topical_label(self):
  source={**MIAMI,'series':False}
  self.assertEqual(discover_research((FIX/'miami-macro-2027.html').read_text(),'https://www.noahwilliams.xyz/conferences',source),[])
 def test_site_banner_h1_is_not_the_title(self):
  html='<html><head><title>Federal Reserve Board - Day-After Conference on Financial Markets</title></head><body><main><h1>Board of Governors of the Federal Reserve System</h1><h2>Conference</h2><h3>Day-After Conference on Financial Markets</h3><p>Research papers.</p></main></body></html>'
  self.assertEqual(clean(html)[0],'Day-After Conference on Financial Markets')
 def test_bare_macro_is_a_topic(self):
  self.assertIn('General macro',topics('Bonn–Oxford–European Commission Macro Workshop'))
  self.assertNotIn('General macro',topics('Macroprudential stress testing'))

class DateRuleTests(unittest.TestCase):
 def test_single_date_in_event_sentence(self):
  self.assertEqual(event_dates('The workshop will be held in London on November 13, 2026.')[:2],('2026-11-13',None))
 def test_single_date_with_start_time(self):
  self.assertEqual(event_dates('Saariselkä, Finland Thursday 17 December 2026, 8:30 AM Add to calendar')[:2],('2026-12-17',None))
 def test_publication_stamp_ignored(self):
  start,_,quote,how,_=event_date_detail('Climate Workshop Published on 21st of April 2026 06 November 2026 - 08:30 This workshop')
  self.assertEqual((start,how),('2026-11-06','timed'));self.assertTrue(quote.startswith('06 November 2026'))
 def test_header_date_after_breadcrumb_title(self):
  text='Events 18th Research Workshop Back 18th Research Workshop Information 20 April 2027 Europa Room'
  self.assertEqual(event_dates(text,'18th Research Workshop')[0],'2027-04-20')
 def test_deadline_date_is_never_the_event(self):
  for text in ['Submission deadline: 5 February 2027','Papers should be sent by March 15, 2027.','Registration closes 1 June 2027, 17:00','Notification of acceptance on 5 March 2027 at 12:00']:
   self.assertEqual(event_dates(text,'Macro Workshop')[0],None,text)
 def test_month_only_is_not_a_date(self):
  self.assertEqual(event_dates('Conference Danmarks Nationalbank September 2026')[0],None)
 def test_dotted_european_dates(self):
  self.assertEqual(event_dates('Financial Stability 18.03.2027 – 19.03.2027 add to calendar')[:2],('2027-03-18','2027-03-19'))
  self.assertEqual(event_dates('takes place from 3rd to 4th of June 2027 in Eltville')[:2],('2027-06-03','2027-06-04'))
  self.assertEqual(event_dates('Version 1.2.2027 notes')[0],None)
 def test_cross_month_ranges(self):
  self.assertEqual(event_dates('Held April 30 – May 1, 2027 in Rome')[:2],('2027-04-30','2027-05-01'))
  self.assertEqual(event_dates('Held 30 April – 1 May 2027 in Rome')[:2],('2027-04-30','2027-05-01'))
 def test_year_digits_are_not_a_day(self):
  self.assertEqual(event_dates('Running since 2026 – 28 June 2027')[0],None)
 def test_listing_title_withheld(self):
  html='<main><h1>Upcoming events</h1><p>Macroeconomics research conference will be held on 5 June 2027.</p></main>'
  self.assertIsNone(extract_research(html,'https://example.org/events',{'name':'X','link_pattern':'/'}))
 def test_lone_date_equal_to_deadline_withheld(self):
  html='<main><h1>Macro Workshop 2027</h1><p>Macro Workshop 2027 15 January 2027</p><p>Research papers welcome. Submission deadline: 15 January 2027.</p></main>'
  self.assertIsNone(extract_research(html,'https://example.org/w',{'name':'X','link_pattern':'/'}))

class FeedTests(unittest.TestCase):
 feed='https://cepr.org/rss/events'
 def setUp(self):self.items=parse_rss(RSS)
 def test_relevance_keeps_macro_meetings_only(self):
  self.assertEqual([x['title'][:9] for x in self.items if relevant(x)],['34th CEPR'])
 def test_record_has_dates_and_unknown_call(self):
  r=feed_record(self.items[0],{'organizer':'CEPR'},self.feed)
  self.assertEqual((r['event_start'],r['event_end'],r['city'],r['region']),('2027-05-26','2027-05-28','Tarragona','Europe'))
  self.assertEqual((r['calls'][0]['state'],r['calls'][0]['deadline']),('unknown',None))
  self.assertEqual(r['evidence']['event_dates']['kind'],'feed')
 def test_feed_recheck_updates_and_records_history(self):
  r=feed_record(self.items[0],{'organizer':'CEPR'},self.feed);r.update(last_verified='2026-11-01',last_checked='2026-11-01')
  moved=dict(self.items[0],start='2027-05-27T09:00:00+0100')
  out=verify_feed(copy.deepcopy(r),{moved['url']:moved},'2026-11-13T06:00:00+00:00')
  self.assertEqual((out['event_start'],out['last_verified'],out['health']),('2027-05-27','2026-11-13T06:00:00+00:00','verified'))
  self.assertEqual(out['history'][0]['old'],'2027-05-26')
 def test_absent_feed_item_is_not_a_cancellation(self):
  r=feed_record(self.items[0],{'organizer':'CEPR'},self.feed);r.update(last_verified='2026-11-01',last_checked='2026-11-01')
  out=verify_feed(copy.deepcopy(r),{},'2026-11-13T06:00:00+00:00')
  self.assertEqual((out['event_state'],out['last_verified']),('announced','2026-11-01'))

class DedupAndHealthTests(unittest.TestCase):
 def rec(self,name,org,start='2026-12-17',url='https://a.example/x'):
  return {'id':'event-'+name[:8],'name':name,'organizers':[org],'event_start':start,'source_url':url,'calls':[]}
 def test_partner_announcements_merge(self):
  a=self.rec('Bank of Finland and CEPR Joint Conference on Navigating Monetary Policy by the Northern Lights','Bank of Finland')
  b=self.rec('Navigating Monetary Policy by the Northern Lights','CEPR',url='https://b.example/y')
  self.assertTrue(duplicate(a,b))
 def test_same_title_other_organiser_merges(self):
  self.assertTrue(duplicate(self.rec('6th WE_ARE_IN Macroeconomics and Finance Conference','CEPR'),self.rec('6th WE_ARE_IN Macroeconomics and Finance Conference 2026','European Central Bank',url='https://b.example/y')))
 def test_short_generic_titles_do_not_merge_across_organisers(self):
  self.assertFalse(duplicate(self.rec('Annual Conference','Bank A'),self.rec('Annual Conference','Bank B',url='https://b.example/y')))
 def test_different_dates_never_merge(self):
  self.assertFalse(duplicate(self.rec('Navigating Monetary Policy by the Northern Lights','CEPR'),self.rec('Navigating Monetary Policy by the Northern Lights','CEPR','2027-12-17','https://b.example/y')))
 def test_benchmark_reports_misses(self):
  entries=[{'name':'Miami Macro 2027','url':'https://www.noahwilliams.xyz/conferences/miamimacro27','deadline':'2026-12-15'}]
  self.assertFalse(benchmark_status([],entries)[0]['found'])
  r=self.rec('Miami Macro 2027','UM',url='https://www.noahwilliams.xyz/conferences/miamimacro27');r['calls']=[{'deadline':'2026-12-15'}]
  self.assertTrue(benchmark_status([r],entries)[0]['found'])
 def test_refusing_host_is_skipped_for_rest_of_run(self):
  f=Fetcher();f.refused['cepr.org']=2
  with self.assertRaisesRegex(ValueError,'refused'):f.get('https://cepr.org/events/x')

if __name__=='__main__':unittest.main()
