import sys, types, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.setdefault('uno', types.ModuleType('uno'))
import app

class SubstationTimingTest(unittest.TestCase):
    def test_flood_hours_and_component_days_are_combined(self):
        class Sheet:
            def getCellByPosition(self, col, row):
                values = {app.column_index('Z'): 36, app.column_index('AG'): 2}
                return types.SimpleNamespace(String='Example' if col == 1 and row == 3 else '', Value=values.get(col, 0) if row == 3 else 0)
        result = app.read_substation_results(Sheet())['example']
        self.assertEqual(result['total_flood_time_hours'], 36)
        self.assertEqual(result['lead_time_days'], 2)
        self.assertEqual(result['time_until_repaired_hours'], 84)

if __name__ == '__main__': unittest.main()
