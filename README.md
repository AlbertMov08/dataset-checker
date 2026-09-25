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

To run the tests:

python3 -m unittest -v

Next step: load the sample CSV into SQLite and count the rows with a SQL query. Compare that number with the Python report.
