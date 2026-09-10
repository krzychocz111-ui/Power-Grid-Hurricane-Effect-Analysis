import sys, types, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.modules.setdefault('uno',types.ModuleType('uno'))
import app
class SubstationTest(unittest.TestCase):
 def test_summary_counts_each_station_once_and_includes_partial_repairs(self):
  results={'one':{'name':'One','full':True,'partial':False,'repair_cost':100},'two':{'name':'Two','full':False,'partial':True,'repair_cost':25},'three':{'name':'Three','full':False,'partial':False,'repair_cost':0}}
  blocks={'type':'FeatureCollection','features':[{'id':i,'properties':{'CONCATENATE_title':'One|Two'}} for i in range(3)]}
  with patch.object(app,'load_blocks',return_value=blocks):state=app.build_dashboard_state(results,include_geojson=False)
  self.assertEqual(state['summary']['fully_outaged_substations'],1)
  self.assertEqual(state['summary']['substation_repair_cost'],125)
  self.assertEqual(len(state['substations']),3)
  self.assertNotIn('geojson',state)
if __name__=='__main__':unittest.main()
