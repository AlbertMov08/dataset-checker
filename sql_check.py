import argparse
import csv
import os
import sqlite3
import sys
from pathlib import Path

from checker import DELIMITERS, check_csv_stream


def file_version(file):
    info = os.fstat(file.fileno())
    return info.st_size, info.st_mtime_ns


def compare_row_counts(path, *, delimiter=","):
    with open(path, newline="", encoding="utf-8-sig") as file:
        version = file_version(file)
        report = check_csv_stream(file, delimiter=delimiter)
        if report["columns"] != ["name", "age", "city"]:
            raise ValueError("This example needs name, age, city columns in that order.")

        # Read the same open file even if the path is replaced between passes.
        file.seek(0)
        reader = csv.reader(file, delimiter=delimiter, strict=True)
        for row in reader:
            if row:
                break

        connection = sqlite3.connect(":memory:")
        try:
            connection.execute("CREATE TABLE people (name TEXT, age TEXT, city TEXT)")
            connection.executemany(
                "INSERT INTO people VALUES (?, ?, ?)",
                (row for row in reader if row),
            )
            sql_count = connection.execute("SELECT COUNT(*) FROM people").fetchone()[0]
        finally:
            connection.close()
        if file_version(file) != version:
            raise ValueError("The file changed during the comparison. Run the check again.")

    return report["rows"], sql_count


def main():
    parser = argparse.ArgumentParser(description="Compare CSV and SQLite row counts.")
    parser.add_argument("path", nargs="?", type=Path, default=Path(__file__).with_name("sample.csv"),
                        help="CSV with name, age, city columns (default: sample.csv)")
    parser.add_argument(
        "--delimiter", choices=DELIMITERS, default="comma",
        help="Field separator (default: comma)",
    )
    args = parser.parse_args()
    try:
        python_count, sql_count = compare_row_counts(args.path, delimiter=DELIMITERS[args.delimiter])
    except UnicodeDecodeError:
        print("Could not compare row counts: the CSV must use UTF-8 encoding.", file=sys.stderr)
        return 1
    except (OSError, ValueError, csv.Error, sqlite3.Error) as error:
        print(f"Could not compare row counts: {error}", file=sys.stderr)
        return 1
    print(f"Python row count: {python_count}")
    print(f"SQLite row count: {sql_count}")
    print(f"Counts match: {python_count == sql_count}")
    return int(python_count != sql_count)


if __name__ == "__main__":
    sys.exit(main())
