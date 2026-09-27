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

    def test_wrong_columns(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "other.csv"
            path.write_text("product,price\nbook,12\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "name, age, city"):
                compare_row_counts(path)


if __name__ == "__main__":
    unittest.main()
