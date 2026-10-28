import argparse
import csv
import json
import math
from statistics import mean
import sys


def percentage(part, total):
    if total == 0:
        return 0.0
    return part / total * 100


def check_csv(path, numeric_columns=()):
    """Count missing cells and repeated rows in a CSV."""
    with open(path, newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file, strict=True)
        columns = []
        for row in reader:
            if row:
                columns = row
                break
        if not columns:
            raise ValueError("The file needs a header row.")

        columns = [name.strip() for name in columns]
        if "" in columns:
            raise ValueError("Each column needs a name.")
        if len(set(columns)) != len(columns):
            raise ValueError("Column names must be different.")
        numeric_values = {column: [] for column in numeric_columns}
        for column in numeric_values:
            if column not in columns:
                raise ValueError(f"Numeric column {column!r} is not in the header.")

        missing = dict.fromkeys(columns, 0)
        seen = set()
        row_count = 0
        duplicates = 0

        for row in reader:
            if not row:
                continue
            if len(row) != len(columns):
                raise ValueError(
                    f"Line {reader.line_num}: expected {len(columns)} values, "
                    f"got {len(row)}."
                )

            row_count += 1
            for column, value in zip(columns, row):
                if value.strip() == "":
                    missing[column] += 1
                elif column in numeric_values:
                    try:
                        number = float(value)
                        if not math.isfinite(number):
                            raise ValueError
                    except ValueError as error:
                        raise ValueError(
                            f"Line {reader.line_num}: {column!r} needs a finite number."
                        ) from error
                    numeric_values[column].append(number)

            # Count repeats after the first copy.
            record = tuple(row)
            if record in seen:
                duplicates += 1
            seen.add(record)

    report = {
        "rows": row_count,
        "columns": columns,
        "missing": missing,
        "duplicates": duplicates,
    }
    if numeric_values:
        report["numeric"] = {
            column: {
                "count": len(values),
                "min": min(values) if values else None,
                "max": max(values) if values else None,
                "mean": mean(values) if values else None,
            }
            for column, values in numeric_values.items()
        }
    return report


def main():
    parser = argparse.ArgumentParser(description="Check a CSV for basic data problems.")
    parser.add_argument("path", help="CSV file to check")
    parser.add_argument("--output", help="Save the report to a new JSON file")
    parser.add_argument(
        "--numeric-column", action="append", default=[], metavar="NAME",
        help="Summarize a numeric column; repeat for more columns",
    )
    args = parser.parse_args()

    try:
        report = check_csv(args.path, args.numeric_column)
    except (OSError, ValueError, csv.Error) as error:
        print(f"Could not check the file: {error}", file=sys.stderr)
        return 1

    print(f"Rows: {report['rows']}")
    print(f"Columns: {len(report['columns'])}")
    print(f"Duplicate rows: {report['duplicates']}")
    print("Missing values:")
    for column, count in report["missing"].items():
        missing_percent = percentage(count, report["rows"])
        print(f"  {column}: {count} ({missing_percent:.1f}%)")

    for column, summary in report.get("numeric", {}).items():
        if summary["count"]:
            print(f"Numeric {column}: min={summary['min']:g}, "
                  f"max={summary['max']:g}, mean={summary['mean']:g} "
                  f"({summary['count']} values)")
        else:
            print(f"Numeric {column}: no numeric values")

    if args.output:
        try:
            # Don't overwrite an existing file.
            with open(args.output, "x", encoding="utf-8") as file:
                json.dump(report, file, indent=2)
                file.write("\n")
        except OSError as error:
            print(f"Could not save the report: {error}", file=sys.stderr)
            return 1
        print(f"Report saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
