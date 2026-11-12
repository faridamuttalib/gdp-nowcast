"""Source-integrity tests. No live requests are made by these tests."""
from pathlib import Path
import unittest,sys,json,uuid,copy
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import update_data as sources
class SourceIntegrity(unittest.TestCase):
 def setUp(self):self.data=json.loads((ROOT/'tests/fixtures/excel-reference.json').read_text())
 def test_duplicate_period_rejected(self):
  self.data['monthly'].append(self.data['monthly'][0].copy())
  with self.assertRaisesRegex(ValueError,'Duplicate'):sources.validate(self.data)
 def test_previously_observed_values_cannot_disappear(self):
  new=copy.deepcopy(self.data);new['monthly'][-2]['mining']=None
  with self.assertRaisesRegex(ValueError,'Refresh lost'):sources.validate(new,self.data)
 def test_component_reconciliation(self):
  self.data['gdp'][-1]['total']+=10000
  with self.assertRaisesRegex(ValueError,'reconcile'):sources.validate(self.data)
 def test_schema_change_rejected(self):
  with self.assertRaisesRegex(ValueError,'schema'):sources.records('date,wrong\n2026-01-01,3',['date','index'])
 def test_month_names_and_slug_abbreviations(self):
  from datetime import date
  entries=[('/portal-main/release-content/index-of-industrial-production-malaysia-janu-2023',date(2023,3,13),'Index of Industrial Production Malaysia')]
  self.assertEqual(sources.monthly_calendar(entries,'industrial production'),{'2023-01-01':'2023-03-13'})
 def test_new_year_cpo_page_can_be_pending_but_observed_values_are_required(self):
  from datetime import date
  self.assertTrue(sources.unpublished_cpo_year_allowed(self.data,date(2027,1,5)))
  self.assertFalse(sources.unpublished_cpo_year_allowed(self.data,date(2027,3,1)))
  self.assertFalse(sources.unpublished_cpo_year_allowed(self.data,date(2026,2,15)))
 def test_failed_download_retains_exact_snapshot_bytes(self):
  directory=ROOT/'.runtime';directory.mkdir(exist_ok=True)
  file=directory/('test-snapshot-'+uuid.uuid4().hex+'.json')
  try:
   original=json.dumps(self.data).encode();file.write_bytes(original)
   with patch.object(sources,'fetch',side_effect=OSError('Simulated source outage')):
    with self.assertRaisesRegex(OSError,'outage'):sources.refresh(file)
   self.assertEqual(file.read_bytes(),original)
  finally:file.unlink(missing_ok=True)
if __name__=='__main__':unittest.main()
