import tempfile
import unittest
import zipfile
from pathlib import Path

from gbheatmodel.zenodo_inputs import extract_weather_year


class SafeZenodoTests(unittest.TestCase):
    def test_two_temperature_files_and_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'temp.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('dataset/air_temp_2012.csv', 'time,one\n0,2\n')
                z.writestr('dataset/average_day_air_temp_2012.csv', 'day,one\n0,2\n')
                z.writestr('dataset/air_temp_2011.csv', 'unrelated')
            self.assertEqual(extract_weather_year(archive, 'temperature', 2012, root / 'data'), 2)
            self.assertEqual(extract_weather_year(archive, 'temperature', 2012, root / 'data'), 0)
            self.assertFalse((root / 'data/air_temp/air_temp_2011.csv').exists())

    def test_mismatch_refused_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            archive=root/'temp.zip'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('air_temp_2012.csv','correct')
            dest=root/'data/air_temp/air_temp_2012.csv'
            dest.parent.mkdir(parents=True)
            dest.write_text('different')
            with self.assertRaises(FileExistsError):
                extract_weather_year(archive,'temperature',2012,root/'data')
            self.assertEqual(dest.read_text(),'different')

    def test_patterns_exact_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            archive=root/'patterns.zip'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('archive/HD_heat_patterns_2012/(-0.25_50.75)_2012.csv','ok')
                z.writestr('archive/HD_heat_patterns_2013/(-0.25_50.75)_2013.csv','wrong')
            self.assertEqual(extract_weather_year(archive,'patterns',2012,root/'data'),1)
            self.assertTrue((root/'data/heat_demand_profiles_patterns/HD_heat_patterns_2012/(-0.25_50.75)_2012.csv').exists())

if __name__ == '__main__':
    unittest.main()
