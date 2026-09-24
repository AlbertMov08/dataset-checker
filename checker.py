import argparse
import csv
import sys


def check_csv(path):
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

            # Count each repeat after the first copy.
            record = tuple(row)
            if record in seen:
                duplicates += 1
            seen.add(record)

    return {
        "rows": row_count,
        "columns": columns,
        "missing": missing,
        "duplicates": duplicates,
    }


def main():
    parser = argparse.ArgumentParser(description="Check a CSV for basic data problems.")
    parser.add_argument("path", help="CSV file to check")
    args = parser.parse_args()

    try:
        report = check_csv(args.path)
    except (OSError, ValueError, csv.Error) as error:
        print(f"Could not check the file: {error}", file=sys.stderr)
        return 1

    print(f"Rows: {report['rows']}")
    print(f"Columns: {len(report['columns'])}")
    print(f"Duplicate rows: {report['duplicates']}")
    print("Missing values:")
    for column, count in report["missing"].items():
        print(f"  {column}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
