"""Use existing Conda Python only: python -m unittest discover -s tests -p test_zenodo_archive_year.py -v"""
import tempfile
import unittest
import zipfile
from pathlib import Path
from gbheatmodel.zenodo_inputs import extract_weather_year, select_archive

class ArchiveYearTests(unittest.TestCase):
    def test_exact_archive(self):
        manifest = [{'key':'air_temp.zip','size':7},{'key':'heat_demand_profiles_patterns.zip','size':9}]
        self.assertEqual(select_archive(manifest,'temperature')['key'],'air_temp.zip')
        self.assertEqual(select_archive(manifest,'patterns')['key'],'heat_demand_profiles_patterns.zip')

    def test_extract_temperature_one_year(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); archive=root/'a.zip'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('air_temp/air_temp_2011.csv','x')
                z.writestr('air_temp/air_temp_2012.csv','2012')
            self.assertEqual(extract_weather_year(archive,'temperature',2012,root/'data'),1)
            self.assertEqual((root/'data/air_temp/air_temp_2012.csv').read_text(),'2012')
            self.assertFalse((root/'data/air_temp/air_temp_2011.csv').exists())

    def test_extract_patterns_one_year(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); archive=root/'a.zip'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('root/HD_heat_patterns_2012/(1_2)_2012.csv','2012')
                z.writestr('root/HD_heat_patterns_2011/(1_2)_2011.csv','2011')
            self.assertEqual(extract_weather_year(archive,'patterns',2012,root/'data'),1)
            self.assertTrue((root/'data/heat_demand_profiles_patterns/HD_heat_patterns_2012/(1_2)_2012.csv').exists())
            self.assertFalse((root/'data/heat_demand_profiles_patterns/HD_heat_patterns_2011').exists())


    def test_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            archive = root / "a.zip"
            data_root = root / "data"

            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("air_temp_2012.csv", "original")

            # First extraction installs the file.
            self.assertEqual(
                extract_weather_year(archive, "temperature", 2012, data_root),
                1
            )

            destination = data_root / "air_temp" / "air_temp_2012.csv"

            # Repeating extraction with identical contents is safe.
            self.assertEqual(
                extract_weather_year(archive, "temperature", 2012, data_root),
                0
            )

            # A conflicting existing file must never be overwritten.
            destination.write_text("locally_modified")

            with self.assertRaises(FileExistsError):
                extract_weather_year(archive, "temperature", 2012, data_root)

            self.assertEqual(
                destination.read_text(),
                "locally_modified"
            )


    def test_zip_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); archive=root/'a.zip'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('../evil.txt','x')
                z.writestr('air_temp_2012.csv','y')
            with self.assertRaises(ValueError):
                extract_weather_year(archive,'temperature',2012,root/'data')
            self.assertFalse((root/'data').exists())

if __name__=='__main__':unittest.main()
