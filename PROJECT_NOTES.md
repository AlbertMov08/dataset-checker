# Project notes

Starting with idea 9: a dataset-quality assistant.

First step: check a CSV for empty cells and duplicate rows. Keep it small enough to understand each part. There isn't a model in this version yet.

Next sessions:

- Walk through `check_csv` and the example output.
- Add the percentage of missing values for each column. (Done)
- Save a report as JSON. (Done: use `--output report.json`.)
- Load the sample CSV into SQLite, count the rows with SQL, and compare with the Python report. (Done: run `python3 sql_check.py`.)
- Add minimum, maximum, and average values for numerical columns.
- Later, explore numeric outliers and compare simple rules with an ML model.

First-version scope (set September 26, 2026):

1. CSV validation and basic counts. Done.
2. Missing-value percentages. Done.
3. JSON export. Done.
4. SQLite row-count example. Done; uses the sample's name, age, city columns.
5. Numerical summaries. Next.
6. Statistical outlier checks. Planned.
7. Small ML anomaly-detection comparison with reviewed examples and limitations. Planned.
8. Final example walkthrough, reproducible results, and README review. Planned.

Progress is 4 of 8 milestones, or 50% by milestone count. These aren't equal amounts of work, so this doesn't measure time remaining or personal learning progress. Keep this scope stable and update completed items as they are finished. The other two project ideas below are separate projects.

Other project ideas to come back to:

- Idea 8: an LLM evaluation lab. Compare models or prompts on a narrow task and record accuracy, mistakes, response time, and cost.
- Idea 10: a GitHub issue classifier. Start with a text classifier for issue categories, then try embeddings and duplicate-issue search.

Working style: one small change per session, short useful comments, and a plain README with no fancy formatting or code boxes. Keep a concrete next step at the end of the README and update it after each change. Explain the Python being used. Commit real progress as it happens.
