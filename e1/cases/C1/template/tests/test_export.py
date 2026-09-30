import csv
import io
import unittest

from app.export import to_csv


class ExportTest(unittest.TestCase):
    def test_plain(self):
        out = to_csv([{"name": "Ana", "city": "Lyon", "phone": "01"}])
        self.assertEqual(out, "name,city,phone\nAna,Lyon,01\n")

    def test_name_with_comma_round_trips(self):
        rows = [{"name": "Smith, Jo", "city": "Paris", "phone": "02"}]
        back = list(csv.DictReader(io.StringIO(to_csv(rows))))
        self.assertEqual(back[0]["name"], "Smith, Jo")
        self.assertEqual(back[0]["city"], "Paris")


if __name__ == "__main__":
    unittest.main()
