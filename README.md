dataset-checker

A small Python tool for checking CSV files before using them in a data or ML project.

It counts rows, columns, missing values, and duplicate rows. It also shows the percentage of missing values for each column and can save the counts as JSON.

Empty cells and cells with only spaces count as missing. Duplicate rows have to match exactly, and only copies after the first row count. The original CSV stays the same.

Run the example with Python 3:

python3 checker.py sample.csv

Replace sample.csv with your own file to check it. The file should use UTF-8, have comma-separated values, and start with a header row. Each column needs a different name. For now, NA and null are treated as text.

To save the counts and column names as JSON:

python3 checker.py sample.csv --output report.json

The results still print in the terminal. Pick a new filename each time; existing files aren't overwritten.

There's also a small SQL example for sample.csv. It loads the name, age, and city columns into SQLite, counts the rows with SELECT COUNT(*), and compares that with the Python count. The database only exists while the example runs.

python3 sql_check.py

To run the tests:

python3 -m unittest -v

First-version progress: 4 of 8 milestones are done (50% by milestone count). CSV checks, missing-value percentages, JSON export, and the SQLite example are done. Numerical summaries, a statistical outlier check, a small ML comparison, and a final example walkthrough are still planned. This isn't an estimate of time remaining; the later steps will take more work.

Next step: add minimum, maximum, and average values for numerical columns, starting with age in sample.csv.
