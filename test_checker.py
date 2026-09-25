import csv
import json
import subprocess
import sys
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

    def run_export(self, output):
        return subprocess.run(
            [sys.executable, str(Path(__file__).with_name("checker.py")),
             str(self.path), "--output", str(output)],
            capture_output=True, text=True,
        )

    def test_json_export(self):
        self.check_text("name,age\nAna,19\nSam,\nAna,19\n")
        output = self.path.with_suffix(".json")
        result = self.run_export(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("age: 1 (33.3%)", result.stdout)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {
            "rows": 3, "columns": ["name", "age"],
            "missing": {"name": 0, "age": 1}, "duplicates": 1,
        })

    def test_export_does_not_overwrite_input(self):
        original = "name,age\nAna,19\n"
        self.check_text(original)
        result = self.run_export(self.path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Could not save the report", result.stderr)
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_export_missing_folder(self):
        self.check_text("name,age\nAna,19\n")
        result = self.run_export(self.path.parent / "missing" / "report.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Could not save the report", result.stderr)
        self.assertNotIn("Report saved", result.stdout)

    def test_invalid_csv_does_not_create_report(self):
        self.path.write_text("name,age\nAna\n", encoding="utf-8")
        output = self.path.with_suffix(".json")
        result = self.run_export(output)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Could not check the file", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
