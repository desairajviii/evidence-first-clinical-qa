import pandas as pd

df = pd.read_csv("apixaban_dataset.csv")

# Lowercase and drop quote marks so 'Answer "No" unless' matches
q = df["question"].str.lower().str.replace('"', "").str.replace("'", "")

df["has_no_rule"] = q.str.contains("answer no unless")
df["has_na_rule"] = q.str.contains("answer na")

for qtype, rule in [("yes", "has_no_rule"), ("numeric", "has_na_rule")]:
    part = df[df["question_type"] == qtype]
    print(f"\n{qtype} questions: {len(part)}")
    print(f"  with answer instruction:    {part[rule].sum()}")
    print(f"  without answer instruction: {(~part[rule]).sum()}")
    print("  Unique question texts without it:")
    for text in part.loc[~part[rule], "question"].unique():
        print("   -", text)