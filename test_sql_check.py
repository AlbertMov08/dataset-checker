import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sql_check import compare_row_counts


class SqlCheckTests(unittest.TestCase):
    def test_sample(self):
        sample = Path(__file__).with_name("sample.csv")
        self.assertEqual(compare_row_counts(sample), (4, 4))

    def test_blank_lines_and_quoted_values(self):
        examples = [
            ("\nname,age,city\n\n", (0, 0)),
            ('name,age,city\n\n"O\'Neil",,"Oakland, CA"\n'
             'Sam,20,"two\nlines"\n,,\n\n', (3, 3)),
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "people.csv"
            for text, expected in examples:
                with self.subTest(text=text):
                    path.write_text(text, encoding="utf-8")
                    self.assertEqual(compare_row_counts(path), expected)

    def test_invalid_csv_is_rejected_before_sqlite_loading(self):
        examples = [
            ("name,age,city\nAna,20\n", ValueError),
            ("name,age,city\nAna,20,Oakland,extra\n", ValueError),
            ('name,age,city\nAna,20,"unfinished', csv.Error),
            ("name,age,city\nAna,20,Oakland\n".encode() + b"\xff", UnicodeError),
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "invalid.csv"
            for content, error in examples:
                raw = content.encode() if isinstance(content, str) else content
                path.write_bytes(raw)
                with self.subTest(raw=raw), self.assertRaises(error):
                    compare_row_counts(path)
                self.assertEqual(path.read_bytes(), raw)

    def test_bom_and_crlf_do_not_change_logical_row_counts(self):
        text = '\ufeff\r\n name , age , city \r\nAna,20,"two\r\nlines"\r\nSam,,Oakland'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "windows.csv"
            path.write_bytes(text.encode("utf-8"))
            self.assertEqual(compare_row_counts(path), (2, 2))

    def test_sql_text_values_are_bound_without_changing_the_source(self):
        rows = [
            ["name", "age", "city"],
            ["O'Neil", "20", "City, West"],
            ["'); DROP TABLE people; --", "", "two\nlines"],
            ["Zoë", "21", "東京"],
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "quoted.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                csv.writer(stream).writerows(rows)
            original = path.read_bytes()
            self.assertEqual(compare_row_counts(path), (3, 3))
            self.assertEqual(path.read_bytes(), original)

    def test_cli_accepts_a_csv_path_and_reports_invalid_input(self):
        script = Path(__file__).with_name("sql_check.py")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "people.csv"
            path.write_text("name,age,city\nAna,20,Oakland\n", encoding="utf-8")
            command = [sys.executable, str(script), str(path)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("SQLite row count: 1", result.stdout)
            path.write_text("name,age,city\nAna,20\n", encoding="utf-8")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("Line 2: expected 3 values", result.stderr)
            self.assertEqual(result.stdout, "")

    def test_wrong_columns(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "other.csv"
            path.write_text("product,price\nbook,12\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "name, age, city"):
                compare_row_counts(path)


if __name__ == "__main__":
    unittest.main()
