import unittest,copy
from pathlib import Path
from crawler.extract import deadline,event_dates,extract
from crawler.reconcile import verify,duplicate
from crawler.calendar import generate
from crawler.common import read
from crawler.validate import validate

class PipelineTests(unittest.TestCase):
 def setUp(self): self.seed=read('data/conferences.json')[0]
 def test_real_nber_excerpt(self):
  html=(Path(__file__).parent/'fixtures/nber-household-finance.html').read_text()
  r=extract(html,'https://www.nber.org/conferences/household-finance-working-group-meeting-fall-2026','NBER')
  self.assertEqual(r['event_start'],'2026-12-11'); self.assertEqual(r['calls'][0]['deadline'],'2026-10-08')
 def test_registration_is_not_submission(self):
  self.assertEqual(deadline('Registration deadline: 20 September 2026')[0],None)
  self.assertEqual(deadline('Registration closes 20 September 2026')[0],None)
 def test_ambiguous_dates_withheld(self):
  d,_,state=deadline('Submission deadline: 20 September 2026. Paper submission deadline: 25 September 2026.')
  self.assertIsNone(d);self.assertEqual(state,'conflict')
 def test_submission_and_notification_not_confused(self):
  self.assertEqual(deadline('Papers must be uploaded by November 1, 2026. Authors notified December 5, 2026.')[0],'2026-11-01')
 def test_invalid_date(self): self.assertEqual(deadline('Submission deadline: 31 February 2027')[0],None)
 def test_ranges(self):
  self.assertEqual(event_dates('Meeting June 18-19, 2027')[:2],('2027-06-18','2027-06-19'))
  self.assertEqual(event_dates('Meeting 30 Nov 2026 - 1 Dec 2026')[:2],('2026-11-30','2026-12-01'))
 def test_no_guessed_year(self): self.assertEqual(event_dates('The annual meeting is held in June')[:2],(None,None))
 def test_missing_evidence_not_fresh(self):
  r=verify(self.seed,'<h1>Conference</h1><p>New details coming soon.</p>','2026-09-19')
  self.assertEqual(r['last_verified'],self.seed['last_verified']); self.assertEqual(r['health'],'needs_verification')
 def test_related_events_excluded(self):
  r=extract('<main><h1>Macroeconomics conference</h1><p>Dates coming soon.</p><h2>Related Events</h2><p>June 18-19, 2027</p></main>','https://example.org/event','Test')
  self.assertIsNone(r)
 def test_validation(self): self.assertTrue(validate(read('data/conferences.json')))
 def test_duplicate(self):
  r=copy.deepcopy(self.seed); r['name']='Changed title';self.assertTrue(duplicate(r,self.seed))
 def test_new_call_on_known_event(self):
  r=copy.deepcopy(self.seed);r['calls'][0].update(deadline=None,evidence=None,state='unknown')
  html='<h1>Macroeconomic Policies</h1><p>'+r['evidence']['event_dates']['text']+'</p><p>Submission deadline: 20 September 2026</p>'
  result=verify(r,html,'2026-09-18');self.assertEqual(result['calls'][0]['deadline'],'2026-09-20');self.assertEqual(result['calls'][0]['state'],'open')
 def test_program_and_cfp_merge(self):
  a=copy.deepcopy(self.seed); b=copy.deepcopy(a); a.update(name='50th International Seminar on Macroeconomics',organizers=['NBER / Central Bank'],source_url='https://example.org/cfp'); b.update(name='International Seminar on Macroeconomics, 2027',organizers=['NBER'],source_url='https://example.org/program')
  self.assertTrue(duplicate(a,b))
 def test_calendar_uid_and_exclusive_end(self):
  r=copy.deepcopy(self.seed); r['health']='verified'; ics=generate([r],'events')
  self.assertIn('DTEND;VALUE=DATE:20261217',ics)
  uid=[x for x in ics.splitlines() if x.startswith('UID:')]
  r['event_start']='2026-12-16';self.assertEqual(uid,[x for x in generate([r],'events').splitlines() if x.startswith('UID:')])
 def test_unknown_timezone_all_day(self):
  self.assertIn('DTSTART;VALUE=DATE:20260920',generate([self.seed],'deadlines'))
 def test_supported_zone_utc(self):
  r=copy.deepcopy(self.seed);r['calls'][0].update(deadline='2026-10-08',deadline_time='23:59',deadline_timezone='America/New_York')
  self.assertIn('DTSTART:20261009T035900Z',generate([r],'deadlines'))
 def test_conflict_cancels_calendar(self):
  r=copy.deepcopy(self.seed); r['health']='needs_verification';self.assertIn('STATUS:CANCELLED',generate([r],'deadlines'))
 def test_calendar_folding(self):
  r=copy.deepcopy(self.seed);r['name']='É'*100
  self.assertTrue(all(len(line.encode())<=75 for line in generate([r],'events').split('\r\n')))
if __name__=='__main__': unittest.main()
