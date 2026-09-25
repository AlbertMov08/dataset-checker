import csv
import tempfile
import unittest
from pathlib import Path

from checker import check_csv, percentage


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "data.csv"

    def check_text(self, text):
        self.path.write_text(text, encoding="utf-8")
        return check_csv(self.path)

    def test_counts(self):
        report = self.check_text("name,age\nAna,19\nSam,\nAna,19\nAna,19\n")
        self.assertEqual(report["rows"], 4)
        self.assertEqual(report["columns"], ["name", "age"])
        self.assertEqual(report["missing"], {"name": 0, "age": 1})
        self.assertEqual(report["duplicates"], 2)

    def test_blanks(self):
        report = self.check_text('name,age\n\n"   ",\n,\n')
        self.assertEqual(report["rows"], 2)
        self.assertEqual(report["missing"], {"name": 2, "age": 2})
        self.assertEqual(report["duplicates"], 0)

    def test_header_only(self):
        report = self.check_text("name,age\n")
        self.assertEqual(report["rows"], 0)
        self.assertEqual(report["duplicates"], 0)
        self.assertEqual(report["missing"], {"name": 0, "age": 0})

    def test_blank_lines_before_header(self):
        report = self.check_text("\n\nname,age\nAna,19\n")
        self.assertEqual(report["rows"], 1)
        self.assertEqual(report["columns"], ["name", "age"])

    def test_bad_headers(self):
        for text in ["", "\n\n", "name,\n", "name,  \n", "name, name\n"]:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    self.check_text(text)

    def test_wrong_row_length(self):
        for text in ["name,age\nAna\n", "name,age\nAna,19,Berkeley\n"]:
            with self.subTest(text=text):
                with self.assertRaisesRegex(ValueError, "expected 2 values"):
                    self.check_text(text)

    def test_quoted_cells(self):
        report = self.check_text('name,note\nAna,"hello, there"\nSam,"two\nlines"\n')
        self.assertEqual(report["rows"], 2)
        self.assertEqual(report["missing"], {"name": 0, "note": 0})

    def test_header_spaces_and_bom(self):
        report = self.check_text("\ufeff name , age \nAna,19\n")
        self.assertEqual(report["columns"], ["name", "age"])

    def test_unfinished_quote(self):
        with self.assertRaises(csv.Error):
            self.check_text('name,note\nAna,"unfinished')

    def test_invalid_encoding(self):
        self.path.write_bytes(b"name\n\xff\n")
        with self.assertRaises(UnicodeDecodeError):
            check_csv(self.path)

    def test_percentage(self):
        self.assertEqual(percentage(1, 4), 25.0)
        self.assertEqual(percentage(0, 0), 0.0)


if __name__ == "__main__":
    unittest.main()
