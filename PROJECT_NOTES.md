# Project notes

Starting with idea 9: a dataset-quality assistant.

First step: check a CSV for empty cells and duplicate rows. Keep it small enough to understand each part. There isn't a model in this version yet.

Next sessions:
- Walk through `check_csv` and the example output.
- Add the percentage of missing values for each column. (Done)
- Save a report as JSON.
- Try SQL for some of the same checks.
- Later, explore numeric outliers and compare simple rules with an ML model.

Other project ideas to come back to:
- Idea 8: an LLM evaluation lab. Compare models or prompts on a narrow task and record accuracy, mistakes, response time, and cost.
- Idea 10: a GitHub issue classifier. Start with a text classifier for issue categories, then try embeddings and duplicate-issue search.

Working style: one small change per session, plain comments, short README, and explanations of the Python being used. Commit real progress as it happens.
