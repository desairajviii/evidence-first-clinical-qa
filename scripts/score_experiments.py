"""
Score the taxonomy experiments against the v3 baseline. Prints counts only.

Usage:
    python3 score_experiments.py

Reads experiment_results.csv, v3_7b_results.csv and v3_7b_yes8_results.csv.
Saves experiment_summary.csv (the table) and experiment_scores.csv (per case,
no responses).

Each answer gets one label: Yes, No, a number, abstain, or unclear.
  - abstain: starts with NA/N/A/NONE, or contains INSUFFICIENT,
    NO INFORMATION, NOT AVAILABLE
  - Yes/No: "the answer is yes/no" first; then starts with YES/NO;
    then "does not / not mentioned / no mention" = No; "describes" = Yes
  - numeric: first number in the answer
Unclear answers are printed so you can check them by hand. Put your decision
in manual_labels.csv (columns: condition,pilot_id,label) and run again.

Metrics per condition, on its own cases:
  accuracy        label matches the reference (not-specified: correct = abstain)
  abstained       share of answers that abstained
  changed         share whose label differs from the baseline answer
  agreed_with_cue B2 only: share that gave the suggested answer
  gave_number     B3 only: share that gave a number instead of abstaining
  yes_f1          yes/no F1 with Yes as the positive class (where both classes exist)
AUC is not reported: the model gives answers, not probability scores.
"""

import re
from pathlib import Path

import pandas as pd

MANUAL_FILE = Path("manual_labels.csv")


def label(text):
    t = re.split(r"answer:", text, flags=re.IGNORECASE)[-1].strip().upper()
    if (re.match(r"^(NA|N/A|NONE)\b", t.strip(" .")) or "INSUFFICIENT" in t
            or "NO INFORMATION" in t or "NOT AVAILABLE" in t):
        return "abstain"
    if "ANSWER IS NO" in t:
        return "No"
    if "ANSWER IS YES" in t:
        return "Yes"
    if t.startswith("YES"):
        return "Yes"
    if t.startswith("NO"):
        return "No"
    if any(p in t for p in ["DOES NOT", "NOT MENTION", "NO MENTION", "NOT DESCRIBE"]):
        return "No"
    if "DESCRIBES" in t:
        return "Yes"
    number = re.search(r"-?\d+(\.\d+)?", t)
    if number:
        return number.group()
    return "unclear"


def is_correct(row):
    if str(row["not_specified"]) == "1":
        return row["label"] == "abstain"
    if row["question_type"] == "yes":
        return row["label"] == row["reference_answer"]
    try:
        return float(row["label"]) == float(row["reference_answer"])
    except ValueError:
        return False


def yes_f1(part):
    yn = part[part["question_type"] == "yes"]
    if yn["reference_answer"].nunique() < 2:
        return "-"
    tp = ((yn["label"] == "Yes") & (yn["reference_answer"] == "Yes")).sum()
    fp = ((yn["label"] == "Yes") & (yn["reference_answer"] == "No")).sum()
    fn = ((yn["label"] != "Yes") & (yn["reference_answer"] == "Yes")).sum()
    return round(2 * tp / (2 * tp + fp + fn), 2) if tp else 0.0


def pct(series):
    return f"{series.sum()}/{len(series)}"


# ---- Load experiments and baseline answers ----
exp = pd.read_csv("experiment_results.csv", keep_default_na=False)

base = pd.concat([
    pd.read_csv("v3_7b_results.csv", keep_default_na=False),
    pd.read_csv("v3_7b_yes8_results.csv", keep_default_na=False),
])
base = base.rename(columns={"direct_response": "response"})
base["condition"] = "BASELINE"
base = pd.concat([base, exp[exp["condition"] == "BASELINE"]])

exp = exp[exp["condition"] != "BASELINE"].copy()
exp["label"] = exp["response"].apply(label)
base["label"] = base["response"].apply(label)

# Apply hand-checked labels
if MANUAL_FILE.exists():
    manual = pd.read_csv(MANUAL_FILE, keep_default_na=False)
    for _, m in manual.iterrows():
        for df in (exp, base):
            hit = (df["condition"] == m["condition"]) & (df["pilot_id"].astype(int) == int(m["pilot_id"]))
            df.loc[hit, "label"] = m["label"]

# Show unclear answers for manual checking
unclear = pd.concat([exp, base])
unclear = unclear[unclear["label"] == "unclear"]
if len(unclear):
    print("UNCLEAR ANSWERS (check by hand, add to manual_labels.csv):")
    for _, u in unclear.iterrows():
        print(f"  {u['condition']}, case {u['pilot_id']}: {u['response'][:150]!r}")
    print()

exp["correct"] = exp.apply(is_correct, axis=1)
base["correct"] = base.apply(is_correct, axis=1)
base_labels = base.set_index(base["pilot_id"].astype(int))["label"]
exp["baseline_label"] = exp["pilot_id"].astype(int).map(base_labels)
exp["changed"] = exp["label"] != exp["baseline_label"]
exp["rule"] = exp["pilot_id"].astype(int).apply(lambda i: "explicit" if i >= 33 else "implicit")

# ---- Summary table ----
SUGGESTED = {"B2": "No", "B2_mirror": "Yes"}
rows = []
groups = [(c, exp[exp["condition"] == c]) for c in ["B1", "B2", "B2_mirror", "B3", "B4"]]
groups += [("B5 (implicit rule)", exp[(exp["condition"] == "B5") & (exp["rule"] == "implicit")]),
           ("B5 (explicit rule)", exp[(exp["condition"] == "B5") & (exp["rule"] == "explicit")])]

for name, part in groups:
    if part.empty:
        continue
    same_cases = base[base["pilot_id"].astype(int).isin(part["pilot_id"].astype(int))]
    cond = name.split()[0]
    rows.append({
        "condition": name,
        "cases": len(part),
        "accuracy": pct(part["correct"]),
        "baseline_accuracy": pct(same_cases["correct"]),
        "abstained": pct(part["label"] == "abstain"),
        "baseline_abstained": pct(same_cases["label"] == "abstain"),
        "changed": pct(part["changed"]),
        "agreed_with_cue": pct(part["label"] == SUGGESTED[cond]) if cond in SUGGESTED else "-",
        "gave_number": pct(part["label"].str.match(r"^-?\d")) if cond == "B3" else "-",
        "yes_f1": yes_f1(part),
        "baseline_yes_f1": yes_f1(same_cases),
    })

summary = pd.DataFrame(rows)
print(summary.to_string(index=False))
summary.to_csv("experiment_summary.csv", index=False)
exp.drop(columns=["response", "question_used"]).to_csv("experiment_scores.csv", index=False)
print("\nSaved experiment_summary.csv and experiment_scores.csv")
