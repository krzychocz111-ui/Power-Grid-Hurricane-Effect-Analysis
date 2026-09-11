import sys, types, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.modules.setdefault('uno',types.ModuleType('uno'))
import app
class SubstationTest(unittest.TestCase):
 def test_ordinal_spacing_matches_map_and_service_area(self):
  name = app.normalize_name('Unknown substation at 72 nd  Ave')
  self.assertEqual(name, app.normalize_name('Unknown substation at 72nd Ave'))
  results = {name: {'full': True, 'partial': False}}
  self.assertEqual(app.classify_feature({'CONCATENATE_title': 'Unknown substation at 72nd Ave'}, results), ('full', 1, 0, 1))

 def test_summary_counts_each_station_once_and_includes_partial_repairs(self):
  results={'one':{'name':'One','full':True,'partial':False,'repair_cost':100},'two':{'name':'Two','full':False,'partial':True,'repair_cost':25},'three':{'name':'Three','full':False,'partial':False,'repair_cost':0}}
  blocks={'type':'FeatureCollection','features':[{'id':i,'properties':{'CONCATENATE_title':'One|Two'}} for i in range(3)]}
  with patch.object(app,'load_blocks',return_value=blocks):state=app.build_dashboard_state(results,include_geojson=False)
  self.assertEqual(state['summary']['fully_outaged_substations'],1)
  self.assertEqual(state['summary']['substation_repair_cost'],125)
  self.assertEqual(len(state['substations']),3)
  self.assertNotIn('geojson',state)
 def test_ebrp_totals_are_subset_and_deduplicated(self):
  results = {'one': {'name':'One','full':True,'partial':False,'repair_cost':100},
             'two': {'name':'Two','full':False,'partial':True,'repair_cost':25},
             'outside': {'name':'Outside','full':True,'partial':False,'repair_cost':300}}
  locations = {'features':[{'properties':{'name':n}} for n in ['One','One','Two']]}
  with patch.object(app,'load_blocks',return_value={'features':[]}), patch.object(app.Path,'read_text',return_value=app.json.dumps(locations)):
   summary = app.build_dashboard_state(results)['summary']
  self.assertEqual(summary['ebrp_fully_outaged_substations'],1)
  self.assertEqual(summary['ebrp_substation_repair_cost'],125)
  self.assertEqual(summary['ebrp_modeled_substations'],2)
  self.assertEqual(summary['fully_outaged_substations'],2)
  self.assertEqual(summary['substation_repair_cost'],425)
  self.assertEqual(summary['modeled_substations'],3)

if __name__=='__main__':unittest.main()
