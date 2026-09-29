import sys, types, unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.modules.setdefault('uno',types.ModuleType('uno'))
import app

class ScenarioSwitchTest(unittest.TestCase):
    def test_restores_formula_range_without_resetting_other_cells(self):
        sheet, desktop = MagicMock(), MagicMock()
        template = desktop.loadComponentFromURL.return_value
        formulas = (('=1',),) * 188
        template.Sheets.getByName.return_value.getCellRangeByName.return_value.getFormulaArray.return_value = formulas
        with patch.object(app,'system_path_to_file_url',return_value='file:///template.ods'), patch.object(app.uno,'createUnoStruct',return_value=types.SimpleNamespace(),create=True), patch.object(app,'cell_string',return_value='Example'):
            app.prepare_inundation_mode(sheet,desktop,'H')
        sheet.getCellRangeByName.assert_called_once_with('W4:W191')
        sheet.getCellRangeByName.return_value.setFormulaArray.assert_called_once_with(formulas)
        template.close.assert_called_once_with(True)

    def test_custom_mode_does_not_restore_and_none_clears_depth(self):
        sheet, desktop = MagicMock(), MagicMock()
        app.prepare_inundation_mode(sheet,desktop,'G')
        app.prepare_inundation_mode(sheet,desktop,'S')
        desktop.loadComponentFromURL.assert_not_called()
        sheet.getCellRangeByName.assert_not_called()
        app.prepare_inundation_mode(sheet,desktop,'N')
        sheet.getCellRangeByName.return_value.setDataArray.assert_called_once_with(((0.0,),)*188)

if __name__=='__main__': unittest.main()

