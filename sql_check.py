import csv
import sqlite3
from pathlib import Path

from checker import check_csv


def compare_row_counts(path):
    report = check_csv(path)
    if report["columns"] != ["name", "age", "city"]:
        raise ValueError("This example needs name, age, city columns in that order.")

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE people (name TEXT, age TEXT, city TEXT)")
        with open(path, newline="", encoding="utf-8-sig") as file:
            reader = csv.reader(file, strict=True)
            # Skip the header, including any blank lines before it.
            for row in reader:
                if row:
                    break

            for row in reader:
                if row:
                    connection.execute("INSERT INTO people VALUES (?, ?, ?)", row)

        sql_count = connection.execute("SELECT COUNT(*) FROM people").fetchone()[0]
    finally:
        connection.close()

    return report["rows"], sql_count


if __name__ == "__main__":
    sample = Path(__file__).with_name("sample.csv")
    python_count, sql_count = compare_row_counts(sample)
    print(f"Python row count: {python_count}")
    print(f"SQLite row count: {sql_count}")
    print(f"Counts match: {python_count == sql_count}")
