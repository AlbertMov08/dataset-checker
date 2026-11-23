import csv
from decimal import Context, localcontext
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from checker import check_csv, percentage, save_report


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "data.csv"

    def check_text(self, text):
        self.path.write_text(text, encoding="utf-8")
        return check_csv(self.path)

    def test_cli_escapes_control_characters_in_column_names(self):
        column = "amount\x1b[2J"
        self.path.write_text(f"{column}\n1\n2\n3\n100\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "checker.py", str(self.path), "--outlier-column", column],
            capture_output=True, text=True, check=True,
        )
        self.assertNotIn("\x1b", result.stdout)
        self.assertIn("amount\\x1b[2J", result.stdout)

    def test_duplicate_detection_preserves_cell_whitespace_and_spelling(self):
        report = self.check_text("value,other\n1,x\n1 ,x\n01,x\n1,x\n ,\n,\n")
        self.assertEqual(report["rows"], 6)
        self.assertEqual(report["duplicates"], 1)
        self.assertEqual(report["missing"], {"value": 2, "other": 2})

    def test_repeated_numeric_flags_produce_one_summary_and_outlier_count(self):
        self.path.write_text("amount\n1\n2\n3\n100\n", encoding="utf-8")
        report = check_csv(self.path, ["amount", "amount"], ["amount", "amount"])
        self.assertEqual(list(report["numeric"]), ["amount"])
        self.assertEqual(report["numeric"]["amount"]["count"], 4)
        self.assertEqual(report["numeric"]["amount"]["potential_outliers"], 1)

    def test_mean_of_opposite_extreme_values_stays_finite(self):
        self.path.write_text("amount\n1e308\n1e308\n-1e308\n-1e308\n", encoding="utf-8")
        report = check_csv(self.path, ["amount"])
        self.assertEqual(report["numeric"]["amount"]["mean"], 0)
        self.assertEqual(report["numeric"]["amount"]["count"], 4)
        json.dumps(report, allow_nan=False)

    def test_nonserializable_report_leaves_no_destination_or_temporary(self):
        output = Path(self.folder.name) / "report.json"
        for report in ({"value": object()}, {"value": float("nan")}):
            with self.subTest(report=report):
                with self.assertRaises((TypeError, ValueError)):
                    save_report(report, output)
                self.assertFalse(output.exists())
                self.assertEqual(list(Path(self.folder.name).iterdir()), [])

    def test_cli_errors_escape_control_characters_in_missing_filenames(self):
        path = Path(self.folder.name) / "missing\x1b[2J.csv"
        for script in ("checker.py", "sql_check.py"):
            with self.subTest(script=script):
                result = subprocess.run([sys.executable, script, str(path)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                self.assertNotIn("\x1b", result.stderr)
                self.assertIn("missing", result.stderr)

        import io
        from contextlib import redirect_stderr
        import checker
        import sql_check
        for module, operation in ((checker, "check_csv"), (sql_check, "compare_row_counts")):
            error_output = io.StringIO()
            with self.subTest(module=module.__name__), \
                    patch.object(module, operation, side_effect=OSError("bad\x1b[2J input")), \
                    patch.object(sys, "argv", [module.__name__, "missing.csv"]), \
                    redirect_stderr(error_output):
                self.assertEqual(module.main(), 1)
            self.assertNotIn("\x1b", error_output.getvalue())
            self.assertIn("bad\\x1b[2J input", error_output.getvalue())

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

    def test_blank_header_name_identifies_the_line_and_column(self):
        with self.assertRaisesRegex(ValueError, r"Line 2: .*Column 2 is blank"):
            self.check_text("\nname, ,city\nAna,20,Oakland\n")

    def test_repeated_header_names_identify_the_trimmed_name(self):
        with self.assertRaisesRegex(ValueError, r"Line 2: .*'age' more than once, in columns 2 and 3"):
            self.check_text("\nname,age, age ,city\n")

    def test_wrong_row_length(self):
        for text in ["name,age\nAna\n", "name,age\nAna,19,Berkeley\n"]:
            with self.subTest(text=text):
                with self.assertRaisesRegex(ValueError, "expected 2 values"):
                    self.check_text(text)

    def test_quoted_cells(self):
        report = self.check_text('name,note\nAna,"hello, there"\nSam,"two\nlines"\n')
        self.assertEqual(report["rows"], 2)
        self.assertEqual(report["missing"], {"name": 0, "note": 0})

    def test_cli_accepts_tab_and_semicolon_delimiters_with_quoted_fields(self):
        for kind, separator in (("tab", "\t"), ("semicolon", ";")):
            with self.subTest(kind=kind):
                self.path.write_text(
                    f'name{separator}note{separator}age\n'
                    f'Ana{separator}"one{separator}two"{separator}19\n'
                    f'Sam{separator}{separator}21\n',
                    encoding="utf-8",
                )
                result = subprocess.run(
                    [sys.executable, "checker.py", str(self.path),
                     "--delimiter", kind, "--numeric-column", "age"],
                    capture_output=True, text=True, check=True,
                )
                self.assertIn("Columns: 3", result.stdout)
                self.assertIn("  note: 1 (50.0%)", result.stdout)
                self.assertIn("mean=20 (2 values)", result.stdout)

    def test_multiline_cells_keep_physical_line_numbers_in_errors(self):
        self.check_text('name,age\n"two\nlines",20\nSam,nope\n')
        with self.assertRaisesRegex(ValueError, "Line 4: 'age' needs a finite number"):
            check_csv(self.path, ["age"])
        self.path.write_text('name,age\n"two\nlines",20\nSam\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Line 4: expected 2 values, got 1"):
            check_csv(self.path)

    def test_multiline_row_validation_names_the_full_record_range(self):
        self.path.write_text('name,age\n"two\nlines",nope\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Lines 2–3: 'age' needs a finite number"):
            check_csv(self.path, ["age"])

    def test_header_spaces_and_bom(self):
        report = self.check_text("\ufeff name , age \nAna,19\n")
        self.assertEqual(report["columns"], ["name", "age"])

    def test_unfinished_quote(self):
        with self.assertRaises(csv.Error):
            self.check_text('name,note\nAna,"unfinished')

    def test_csv_parser_errors_include_the_physical_line(self):
        for text, location in (('"unfinished', "Line 1"),
                           ('name,note\nAna,"two\nunfinished', "Lines 2–3"),
                           ('name\n' + 'x' * (csv.field_size_limit() + 1), "Line 2")):
            with self.subTest(location=location):
                with self.assertRaisesRegex(csv.Error, f"{location}:"):
                    self.check_text(text)
                original = self.path.read_bytes()
                result = self.run_export(self.path.with_suffix(".json"))
                self.assertEqual(result.returncode, 1)
                self.assertIn(f"{location}:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(self.path.read_bytes(), original)
                self.assertFalse(self.path.with_suffix(".json").exists())

    def test_invalid_encoding(self):
        self.path.write_bytes(b"name\n\xff\n")
        with self.assertRaises(UnicodeDecodeError):
            check_csv(self.path)

    def test_percentage(self):
        self.assertEqual(percentage(1, 4), 25.0)
        self.assertEqual(percentage(0, 0), 0.0)

    def test_numeric_summary_skips_missing_values_and_keeps_repeated_rows(self):
        self.check_text("name,age\nAna,19\nSam,\nAna,19\nLee,22\n")
        report = check_csv(self.path, ["age"])
        self.assertEqual(report["numeric"], {
            "age": {"count": 3, "min": 19, "max": 22, "mean": 20},
        })
        self.assertEqual(report["missing"]["age"], 1)
        self.assertEqual(report["duplicates"], 1)

    def test_numeric_empty_columns_have_null_statistics(self):
        for text in ("age\n", 'age\n" "\n'):
            with self.subTest(text=text):
                self.check_text(text)
                self.assertEqual(check_csv(self.path, ["age"])["numeric"]["age"], {
                    "count": 0, "min": None, "max": None, "mean": None,
                })

    def test_numeric_columns_reject_missing_headers_and_invalid_values(self):
        self.check_text("age\n19\n")
        with self.assertRaisesRegex(ValueError, "not in the header"):
            check_csv(self.path, ["height"])
        for value in ("unknown", "NaN", "inf", "-inf", "1e400"):
            with self.subTest(value=value):
                self.check_text(f"age\n{value}\n")
                with self.assertRaisesRegex(ValueError, "Line 2: 'age' needs a finite number"):
                    check_csv(self.path, ["age"])

    def test_multiple_numeric_columns_and_large_finite_means(self):
        self.check_text("x,y\n1e308,-2.5\n1e308,1.5\n")
        report = check_csv(self.path, ["x", "y", "x"])
        self.assertEqual(report["numeric"]["x"]["mean"], 1e308)
        self.assertEqual(report["numeric"]["y"]["mean"], -0.5)
        json.dumps(report, allow_nan=False)

    def test_numeric_underflow_is_reported_instead_of_becoming_zero(self):
        for value in ("1e-400", "-1e-400", "1e-9999999999999999999999"):
            with self.subTest(value=value):
                self.check_text(f"amount\n{value}\n")
                with self.assertRaisesRegex(ValueError, "Line 2:.*too small"):
                    check_csv(self.path, ["amount"])

    def test_small_representable_numbers_and_zero_remain_valid(self):
        self.check_text("amount\n5e-324\n0e-400\n-0.0\n-0e9999999999999999999999\n")
        summary = check_csv(self.path, ["amount"])["numeric"]["amount"]
        self.assertEqual(summary["count"], 4)
        self.assertEqual(summary["max"], 5e-324)
        self.assertEqual(summary["min"], 0)

    def test_numeric_cli_prints_and_exports_summary(self):
        self.check_text("age,height\n19,160\n,170\n21,180\n")
        output = self.path.with_suffix(".json")
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("checker.py")),
             str(self.path), "--numeric-column", "age", "--numeric-column", "height",
             "--output", str(output)], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Numeric age: min=19, max=21, mean=20 (2 values)", result.stdout)
        self.assertEqual(json.loads(output.read_text())["numeric"]["height"]["mean"], 170)

    def test_outlier_counts_are_opt_in_and_do_not_remove_rows(self):
        self.check_text("x\n1\n2\n2\n3\n100\n")
        self.assertNotIn("numeric", check_csv(self.path))
        report = check_csv(self.path, outlier_columns=["x"])
        self.assertEqual(report["rows"], 5)
        self.assertEqual(report["numeric"]["x"]["potential_outliers"], 1)
        self.assertEqual(report["numeric"]["x"]["count"], 5)

    def test_outlier_small_constant_and_extreme_samples(self):
        for values, expected in (([], None), ([1, 2, 3], None),
                                 ([2]*4, 0), ([0, 1, 1, 2], 0),
                                 ([-1e308, 0, 0, 0, 1e308], 2)):
            with self.subTest(values=values):
                self.check_text("x\n" + "".join(f"{value}\n" for value in values))
                report = check_csv(self.path, outlier_columns=["x"])
                self.assertEqual(report["numeric"]["x"]["potential_outliers"], expected)
                json.dumps(report, allow_nan=False)

    def test_outlier_fences_include_endpoints_but_flag_values_beyond_them(self):
        for last, expected in (("6", 0), ("6.000000000000001", 1)):
            with self.subTest(last=last):
                self.check_text(f"x\n0\n1\n2\n3\n{last}\n")
                summary = check_csv(self.path, outlier_columns=["x"])["numeric"]["x"]
                self.assertEqual(summary["potential_outliers"], expected)

    def test_outlier_fences_do_not_inherit_decimal_exponent_limits(self):
        self.path.write_text("amount\n1e-20\n2e-20\n2e-20\n3e-20\n1e-18\n", encoding="utf-8")
        with localcontext(Context(Emin=-5, Emax=5)):
            report = check_csv(self.path, outlier_columns=["amount"])
        self.assertEqual(report["numeric"]["amount"]["potential_outliers"], 1)

    def test_outlier_cli(self):
        self.check_text("x\n1\n2\n2\n3\n100\n")
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("checker.py")),
             str(self.path), "--outlier-column", "x"], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Potential outliers x: 1 (1.5 IQR rule)", result.stdout)

    def test_outlier_export_distinguishes_unavailable_from_zero(self):
        output = self.path.with_suffix(".json")
        for values, expected in (([], None), ([2, 2, 2], None),
                                 ([2, 2, 2, 2], 0), ([1, 2, 2, 3, 100], 1)):
            with self.subTest(values=values):
                original = "x,y\n" + "".join(f"{value},\n" for value in values)
                self.path.write_text(original, encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(Path(__file__).with_name("checker.py")),
                     str(self.path), "--outlier-column", "x", "--numeric-column", "x",
                     "--outlier-column", "x", "--output", str(output)],
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(report["numeric"]["x"]["potential_outliers"], expected)
                self.assertEqual(report["numeric"]["x"]["count"], len(values))
                self.assertEqual(report["rows"], len(values))
                self.assertEqual(report["missing"]["y"], len(values))
                self.assertEqual(result.stdout.count("Potential outliers x:"), 1)
                self.assertEqual(self.path.read_text(encoding="utf-8"), original)
                output.unlink()

    def run_export(self, output):
        return subprocess.run(
            [sys.executable, str(Path(__file__).with_name("checker.py")),
             str(self.path), "--output", str(output)],
            capture_output=True, text=True,
        )

    def test_report_publication_failure_cleans_temporary_file(self):
        output = self.path.with_suffix(".json")
        for failure in (OSError("disk full"), KeyboardInterrupt()):
            with self.subTest(failure=type(failure).__name__):
                with patch("checker.os.link", side_effect=failure):
                    with self.assertRaises(type(failure)):
                        save_report({"rows": 0}, output)
                self.assertEqual(list(Path(self.folder.name).iterdir()), [])

    def test_json_export_preserves_unicode_and_control_character_headers(self):
        report = self.check_text('"東京\nvalue",café\n,hello\n')
        output = self.path.with_suffix(".json")
        save_report(report, output)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), report)
        self.assertEqual(report["missing"]["東京\nvalue"], 1)
        self.assertEqual(output.read_bytes()[-1:], b"\n")

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

    def test_export_refuses_symlinks_without_touching_their_targets(self):
        self.check_text("name,age\nAna,19\n")
        output = self.path.with_suffix(".json")
        target = self.path.parent / "target.json"
        for existing in (False, True):
            with self.subTest(existing=existing):
                if existing:
                    target.write_bytes(b"preserve this report")
                output.symlink_to(target)
                result = self.run_export(output)
                self.assertEqual(result.returncode, 1)
                self.assertIn("Could not save the report", result.stderr)
                self.assertNotIn("Report saved", result.stdout)
                self.assertTrue(output.is_symlink())
                self.assertEqual(output.readlink(), target)
                if existing:
                    self.assertEqual(target.read_bytes(), b"preserve this report")
                else:
                    self.assertFalse(target.exists())
                output.unlink()

    def test_export_preserves_a_report_created_while_writing(self):
        output = self.path.with_suffix(".json")
        original_dump = json.dump

        def write_then_create_destination(report, file, **options):
            original_dump(report, file, **options)
            output.write_text("concurrent report", encoding="utf-8")

        with patch("checker.json.dump", side_effect=write_then_create_destination):
            with self.assertRaises(FileExistsError):
                save_report({"rows": 4}, output)
        self.assertEqual(output.read_text(encoding="utf-8"), "concurrent report")
        self.assertEqual(list(output.parent.iterdir()), [output])

    def test_failed_report_write_leaves_no_partial_output(self):
        output = self.path.with_suffix(".json")

        def fail_after_write(report, file, **options):
            file.write('{"rows":')
            raise OSError("Simulated write failure")

        with patch("checker.json.dump", side_effect=fail_after_write):
            with self.assertRaisesRegex(OSError, "Simulated write failure"):
                save_report({"rows": 4}, str(output))
        self.assertEqual(list(output.parent.iterdir()), [])

    def test_failed_report_close_prevents_publication(self):
        output = self.path.with_suffix(".json")

        class FailingClose:
            def __init__(self, temporary):
                self.temporary = temporary
                self.name = temporary.name

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self.temporary.close()
                raise OSError("Simulated close failure")

            def write(self, text):
                return self.temporary.write(text)

        from tempfile import NamedTemporaryFile
        with patch("checker.NamedTemporaryFile",
                   side_effect=lambda **options: FailingClose(NamedTemporaryFile(**options))):
            with self.assertRaisesRegex(OSError, "Simulated close failure"):
                save_report({"rows": 4}, output)
        self.assertEqual(list(output.parent.iterdir()), [])

    def test_export_rejects_nonfinite_values_without_creating_a_report(self):
        output = self.path.with_suffix(".json")
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    save_report({"numeric": {"age": {"mean": value}}}, output)
                self.assertEqual(list(output.parent.iterdir()), [])

    def test_export_missing_folder(self):
        self.check_text("name,age\nAna,19\n")
        result = self.run_export(self.path.parent / "missing" / "report.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Could not save the report", result.stderr)
        self.assertNotIn("Report saved", result.stdout)

    def test_export_rejects_an_empty_output_path(self):
        self.check_text("name,age\nAna,19\n")
        result = self.run_export("")
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

    def test_cli_parse_failures_preserve_input_and_do_not_create_reports(self):
        for content in (b"name\n\xff\n", b'name,note\nAna,"unfinished',
                        b"name,name\nAna,Sam\n", b"\n\n"):
            with self.subTest(content=content):
                self.path.write_bytes(content)
                output = self.path.with_suffix(".json")
                result = self.run_export(output)
                self.assertEqual(result.returncode, 1)
                self.assertIn("Could not check the file:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertEqual(self.path.read_bytes(), content)
                self.assertFalse(output.exists())

    def test_numeric_cli_failures_preserve_input_and_existing_reports(self):
        output = self.path.with_suffix(".json")
        for option in ("--numeric-column", "--outlier-column"):
            for value, column in (("bad", "amount"), ("NaN", "amount"),
                                  ("1e-400", "amount"), ("1", "missing")):
                for existing in (False, True):
                    with self.subTest(option=option, value=value, column=column, existing=existing):
                        original = f"amount\n{value}\n".encode()
                        self.path.write_bytes(original)
                        if existing:
                            output.write_bytes(b"previous report")
                        result = subprocess.run(
                            [sys.executable, str(Path(__file__).with_name("checker.py")),
                             str(self.path), option, column, "--output", str(output)],
                            capture_output=True, text=True,
                        )
                        self.assertEqual(result.returncode, 1)
                        self.assertIn("Could not check the file:", result.stderr)
                        self.assertNotIn("Traceback", result.stderr)
                        self.assertEqual(result.stdout, "")
                        self.assertEqual(self.path.read_bytes(), original)
                        if existing:
                            self.assertEqual(output.read_bytes(), b"previous report")
                            output.unlink()
                        else:
                            self.assertFalse(output.exists())

    def test_cli_missing_input_does_not_create_a_report(self):
        output = self.path.with_suffix(".json")
        result = self.run_export(output)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Could not check the file:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(self.path.exists())
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
