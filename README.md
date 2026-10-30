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

To count potential outliers in a numerical column:

python3 checker.py sample.csv --outlier-column age

This also includes the numerical summary. Repeat the option for more columns. The check uses inclusive quartiles and flags values strictly outside Q1 - 1.5 IQR and Q3 + 1.5 IQR, where IQR is Q3 - Q1. At least four nonmissing values are required; smaller samples return null. Repeated rows count, and no values are removed. A flag is a reason to review a value, not proof of an error. Small or skewed samples can give misleading results. JSON reports include potential_outliers for the chosen columns.

A made-up outlier example is included for reviewing the rule:

python3 checker.py outlier_example.csv --outlier-column amount

It has five rows, one duplicate, no missing cells, and an average amount of 21.6.
The sorted amounts are 1, 2, 2, 3, 100. Inclusive Q1 is 2 and Q3 is 3, so the
fences are 0.5 and 4.5. Only 100 is flagged. If 100 represents a valid large
purchase, the flag is not a data error. The repeated 2 is counted in the
quartiles but flagged only as a duplicate row. Review what the values mean
before removing anything. Values exactly on a fence are not flagged.

There's also a small SQL example for sample.csv. It loads the name, age, and city columns into SQLite, counts the rows with SELECT COUNT(*), and compares that with the Python count. The database only exists while the example runs.

python3 sql_check.py

To run the tests:

python3 -m unittest -v

First-version progress: 6 of 8 milestones are done (75% by milestone count). CSV checks, missing-value percentages, JSON export, the SQLite example, numerical summaries, and an opt-in outlier check are done. A small ML comparison and a final example walkthrough are still planned. This isn't an estimate of time remaining; the later steps will take more work.

Next step: choose a small, clearly labeled synthetic dataset with reviewed normal and anomalous cases for an ML comparison.
