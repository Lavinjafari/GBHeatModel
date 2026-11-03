import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from gbheatmodel.weather_inputs import check_weather_inputs, ensure_weather_inputs

class WeatherInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root/'air_temp').mkdir()
        (self.root/'heat_demand_profiles_patterns'/'HD_heat_patterns_2012').mkdir(parents=True)
        (self.root/'air_temp'/'air_temp_2012.csv').write_text('date,1_2,3_4\n2050-01-01,1,2\n')
        (self.root/'air_temp'/'average_day_air_temp_2012.csv').write_text('date,1_2\n2050-01-01,1\n')
        for grid in ('1_2','3_4'):
            (self.root/'heat_demand_profiles_patterns'/'HD_heat_patterns_2012'/f'({grid})_2012.csv').write_text('date,daytime\n')
    def tearDown(self):
        self.tmp.cleanup()
    def test_complete_skips_network(self):
        with patch('gbheatmodel.zenodo_inputs.get_manifest', side_effect=AssertionError('network')):
            state = ensure_weather_inputs(2012, data_root=self.root, verbose=False)
        self.assertTrue(state['patterns_ok'])
        self.assertEqual(state['expected_grids'], 2)
    def test_missing_pattern_detected(self):
        (self.root/'heat_demand_profiles_patterns'/'HD_heat_patterns_2012'/'(1_2)_2012.csv').unlink()
        state = check_weather_inputs(2012, data_root=self.root)
        self.assertFalse(state['patterns_ok'])
        with self.assertRaises(FileNotFoundError):
            ensure_weather_inputs(2012, data_root=self.root, download_missing=False)
    def test_missing_daily_detected(self):
        (self.root/'air_temp'/'average_day_air_temp_2012.csv').unlink()
        self.assertFalse(check_weather_inputs(2012, data_root=self.root)['daily_ok'])

if __name__ == '__main__':
    unittest.main()
