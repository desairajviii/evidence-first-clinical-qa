"""
Score a results file and print counts only (no note text, no responses).

Usage:
    python3 score_results.py baseline_ctx8k_results.csv

Rules:
- Abstention: answer starting with NA, N/A or NONE, or text containing INSUFFICIENT,
  NO INFORMATION, or NOT AVAILABLE.
- Yes/no: answer starting with YES = Yes; starting with NO, or saying
  "does not" / "not mentioned" = No.
- Numeric: the first number in the answer must equal the reference.
- Not-specified questions: correct if the model abstained.
- For evidence-first, only the text after "Answer:" is scored.
"""

import re
import sys

import pandas as pd

file_name = sys.argv[1] if len(sys.argv) > 1 else "baseline_ctx8k_results.csv"
df = pd.read_csv(file_name, keep_default_na=False)


def final_answer(text):
    """Keep only the part after the last 'Answer:' (if there is one)."""
    return re.split(r"answer:", text, flags=re.IGNORECASE)[-1].strip()


def is_abstention(text):
    t = text.upper().strip(" .")
    return (re.match(r"^(NA|N/A|NONE)\b", t) is not None
            or "INSUFFICIENT" in t
            or "NO INFORMATION" in t
            or "NOT AVAILABLE" in t)


def score(row, method):
    answer = final_answer(row[f"{method}_response"])
    reference = str(row["reference_answer"]).strip()

    # Questions the dataset marks as not answerable
    if str(row["not_specified"]) == "1":
        return "correct" if is_abstention(answer) else "wrong"

    if is_abstention(answer):
        return "abstained"

    if row["question_type"] == "yes":
        t = answer.upper()
        if t.startswith("YES"):
            label = "Yes"
        elif t.startswith("NO") or "DOES NOT" in t or "NOT MENTIONED" in t:
            label = "No"
        else:
            return "unclear"
        return "correct" if label.lower() == reference.lower() else "wrong"

    # Numeric question
    match = re.search(r"-?\d+(\.\d+)?", answer)
    if not match:
        return "unclear"
    return "correct" if float(match.group()) == float(reference) else "wrong"


def group(row):
    if str(row["not_specified"]) == "1":
        return "3. not specified"
    if row["question_type"] == "yes":
        return "1. yes/no"
    return "2. numeric"


df["group"] = df.apply(group, axis=1)

for method in ["direct", "evidence"]:
    df[f"{method}_score"] = df.apply(lambda r: score(r, method), axis=1)

    print(f"\n===== {method.upper()} =====")
    table = pd.crosstab(df["group"], df[f"{method}_score"])
    print(table.to_string())

    answerable = df[df["group"] != "3. not specified"]
    correct = (answerable[f"{method}_score"] == "correct").sum()
    abstained = (answerable[f"{method}_score"] == "abstained").sum()
    print(f"Answerable questions: {correct}/{len(answerable)} correct, "
          f"{abstained}/{len(answerable)} abstained")

# Save per-case scores locally for manual review (keep this file private)
df.drop(columns=[c for c in df.columns if c.endswith("_response")]).to_csv(
    "scores_" + file_name, index=False
)
print(f"\nPer-case scores saved to scores_{file_name} (local only).")
