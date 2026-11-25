"""
Build one comparison table from the scores_*.csv files made by score_results.py.

Usage:
    python3 compare_runs.py

Prints the table and saves it to comparison_table.csv.
"""

import pandas as pd

# Run name and its scores file (made by score_results.py)
RUNS = [
    ("Baseline (3B, full note)", "scores_baseline_ctx8k_results.csv"),
    ("v2 (3B, follow question)", "scores_v2_follow_question_results.csv"),
    ("v3 (7B, follow question)", "scores_v3_7b_results.csv"),
    ("v3 Yes-check (7B, 8 Yes cases)", "scores_v3_7b_yes8_results.csv"),
]

# Cases the scorer marked "unclear" that we checked by hand
MANUAL = {
    ("scores_v3_7b_yes8_results.csv", 31, "direct"): "correct",
    ("scores_v3_7b_yes8_results.csv", 31, "evidence"): "correct",
    ("scores_v3_7b_yes8_results.csv", 32, "direct"): "correct",
    ("scores_v3_7b_yes8_results.csv", 32, "evidence"): "correct",
}

GROUPS = [("1. yes/no", "yes/no"),
          ("2. numeric", "numeric"),
          ("3. not specified", "not specified")]

rows = []
for run_name, file_name in RUNS:
    df = pd.read_csv(file_name, keep_default_na=False)

    for method in ["direct", "evidence"]:
        col = f"{method}_score"

        # Apply the hand-checked scores
        for (f, pilot_id, m), score in MANUAL.items():
            if f == file_name and m == method:
                df.loc[df["pilot_id"] == pilot_id, col] = score

        row = {"run": run_name, "method": method}

        # Correct answers per question group
        for group, label in GROUPS:
            part = df[df["group"] == group]
            row[label] = f"{(part[col] == 'correct').sum()}/{len(part)}" if len(part) else "-"

        # Totals for answerable questions
        answerable = df[df["group"] != "3. not specified"]
        row["answerable correct"] = f"{(answerable[col] == 'correct').sum()}/{len(answerable)}"
        row["answerable abstained"] = f"{(answerable[col] == 'abstained').sum()}/{len(answerable)}"

        seconds = pd.to_numeric(df[f"{method}_seconds"], errors="coerce")
        row["avg seconds"] = round(seconds.mean(), 1)

        rows.append(row)

table = pd.DataFrame(rows)
print(table.to_string(index=False))
table.to_csv("comparison_table.csv", index=False)
print("\nSaved to comparison_table.csv")