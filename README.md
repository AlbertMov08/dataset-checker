# dataset-checker

A small Python tool for checking CSV files before using them in a data or ML project.

Right now it counts rows, columns, empty cells, and duplicate rows. It also shows the percentage of values missing from each column. Cells with only spaces count as empty. Duplicate rows are exact matches, and only copies after the first row count. It doesn't change the file.

Run the example with Python 3:

```sh
python3 checker.py sample.csv
```

You can replace `sample.csv` with the path to your own CSV. The file should be UTF-8, comma-separated, and start with unique column names. For now, values like `NA` and `null` are treated as text.

To save the counts and column names as JSON:

```sh
python3 checker.py sample.csv --output report.json
```

The results still print in the terminal. Pick a new filename each time; existing files aren't overwritten.

To run the tests:

```sh
python3 -m unittest -v
```

Next: try the same checks with SQL.
