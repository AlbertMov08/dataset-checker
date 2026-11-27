import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from checker import check_csv_stream
from sql_check import compare_row_counts


class SqlCheckTests(unittest.TestCase):
    def test_sql_counts_retain_duplicates_instead_of_counting_distinct_people(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "repeated.csv"
            path.write_text("name,age,city\nAna,20,Paris\n" + "Ana,20,Paris\n" * 4,
                            encoding="utf-8")
            original = path.read_bytes()
            self.assertEqual(compare_row_counts(path), (5, 5))
            self.assertEqual(path.read_bytes(), original)


    def test_database_failure_closes_connection_and_preserves_csv(self):
        import sqlite3

        sample = Path(__file__).with_name("sample.csv")
        original = sample.read_bytes()
        with patch("sql_check.sqlite3.connect") as connect:
            connection = connect.return_value
            connection.executemany.side_effect = sqlite3.OperationalError("database full")
            with self.assertRaisesRegex(sqlite3.OperationalError, "database full"):
                compare_row_counts(sample)
            connection.close.assert_called_once_with()
        self.assertEqual(sample.read_bytes(), original)

    def test_wrong_schema_is_rejected_before_creating_a_database(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "wrong.csv"
            for header in ("age,name,city", "name,age,country", "name,age,city,extra"):
                path.write_text(header + "\n", encoding="utf-8")
                with patch("sql_check.sqlite3.connect") as connect:
                    with self.assertRaisesRegex(ValueError, "name, age, city"):
                        compare_row_counts(path)
                    connect.assert_not_called()

    def test_sql_comparison_keeps_nul_cells_as_bound_text(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "people.csv"
            original = b"name,age,city\nAna\x00Lee,20,Paris\nAna\x00Lee,20,Paris\n"
            path.write_bytes(original)
            self.assertEqual(compare_row_counts(path), (2, 2))
            self.assertEqual(path.read_bytes(), original)

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

    def test_cli_uses_the_separator_for_validation_and_sqlite(self):
        script = Path(__file__).with_name("sql_check.py")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "people.tsv"
            path.write_text('name\tage\tcity\nAna\t20\t"Oakland\tCA"\n', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(script), str(path), "--delimiter", "tab"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Python row count: 1", result.stdout)
            self.assertIn("SQLite row count: 1", result.stdout)

    def test_both_commands_explain_unsupported_csv_encoding(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "people.csv"
            path.write_bytes("name,age,city\nZoë,20,Paris\n".encode("latin-1"))
            for script in ("checker.py", "sql_check.py"):
                with self.subTest(script=script):
                    result = subprocess.run(
                        [sys.executable, str(Path(__file__).with_name(script)), str(path)],
                        capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn("CSV must use UTF-8", result.stderr)
                    self.assertEqual(result.stdout, "")

    def test_both_counts_use_the_same_file_after_path_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "people.csv"
            path.write_text("name,age,city\nAna,20,Oakland\n", encoding="utf-8")
            replacement = path.with_name("replacement.csv")
            replacement.write_text("name,age,city\nSam,21,Paris\nLee,22,Rome\n",
                                   encoding="utf-8")

            def replace_after_check(stream, **kwargs):
                report = check_csv_stream(stream, **kwargs)
                replacement.replace(path)
                return report

            with patch("sql_check.check_csv_stream", side_effect=replace_after_check):
                self.assertEqual(compare_row_counts(path), (1, 1))
            self.assertEqual(compare_row_counts(path), (2, 2))

    def test_comparison_rejects_an_edit_to_the_open_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "people.csv"
            path.write_text("name,age,city\nAna,20,Oakland\n", encoding="utf-8")

            def append_after_check(stream, **kwargs):
                report = check_csv_stream(stream, **kwargs)
                with path.open("a", encoding="utf-8") as writer:
                    writer.write("Sam,21,Paris\n")
                return report

            with patch("sql_check.check_csv_stream", side_effect=append_after_check):
                with self.assertRaisesRegex(ValueError, "changed during the comparison"):
                    compare_row_counts(path)
            self.assertEqual(compare_row_counts(path), (2, 2))

    def test_cli_escapes_control_characters_in_saved_report_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report\x1b[2J\n.json"
            sample = Path(__file__).with_name("sample.csv")
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("checker.py")),
                 str(sample), "--output", str(path)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(path.is_file())
            self.assertNotIn("\x1b", result.stdout)
            self.assertIn("\\x1b", result.stdout)
            self.assertIn("\\n.json", result.stdout)

    def test_wrong_columns(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "other.csv"
            path.write_text("product,price\nbook,12\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "name, age, city"):
                compare_row_counts(path)


if __name__ == "__main__":
    unittest.main()
