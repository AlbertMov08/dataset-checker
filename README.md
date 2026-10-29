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

To get the minimum, maximum, and average for a numerical column:

python3 checker.py sample.csv --numeric-column age

Repeat --numeric-column for more columns. Empty cells are excluded from these summaries, while repeated rows still count. A column with no numbers has null statistics in JSON. Other nonnumeric values, including NA, NaN, and infinity, stop the check with a line number. Nonzero values too small for Python to represent as a float also stop the check instead of becoming zero. Columns are summarized only when you name them, so numeric-looking identifiers stay text by default. Add --output report.json to include the summaries in a JSON report.

There's also a small SQL example for sample.csv. It loads the name, age, and city columns into SQLite, counts the rows with SELECT COUNT(*), and compares that with the Python count. The database only exists while the example runs.

python3 sql_check.py

To run the tests:

python3 -m unittest -v

First-version progress: 5 of 8 milestones are done (62.5% by milestone count). CSV checks, missing-value percentages, JSON export, the SQLite example, and numerical summaries are done. A statistical outlier check, a small ML comparison, and a final example walkthrough are still planned. This isn't an estimate of time remaining; the later steps will take more work.

Next step: add a statistical outlier check for a chosen numerical column and explain its limitations.
