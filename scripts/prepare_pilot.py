
import pandas as pd

df = pd.read_csv("apixaban_dataset.csv")

# Select answerable yes/no questions
answerable_yes = df[
    (df["question_type"] == "yes")
    & df["answer"].notna()
]

# Select numeric questions with known reference answers
answerable_numeric = df[
    (df["question_type"] == "numeric")
    & df["answer"].notna()
    & (df["not_specified"] == 0)
]

# Select questions explicitly marked as not specified
insufficient_numeric = df[
    (df["question_type"] == "numeric")
    & (df["not_specified"] == 1)
]

# Sample 8 cases from each category
pilot = pd.concat(
    [
        answerable_yes.sample(n=8, random_state=42),
        answerable_numeric.sample(n=8, random_state=42),
        insufficient_numeric.sample(n=8, random_state=42),
    ],
    ignore_index=True,
)

# Shuffle the sample and assign IDs
pilot = pilot.sample(frac=1, random_state=42).reset_index(drop=True)
pilot.insert(0, "pilot_id", range(1, len(pilot) + 1))

# Save locally
pilot.to_csv("apixaban_pilot_24.csv", index=False)

print("Pilot created successfully.")
print("Total cases:", len(pilot))
print("\nCase counts:")
print("Yes/no:", (pilot["question_type"] == "yes").sum())
print(
    "Numeric with answers:",
    (
        (pilot["question_type"] == "numeric")
        & pilot["answer"].notna()
    ).sum(),
)
print("Marked not specified:", (pilot["not_specified"] == 1).sum())
print("\nSaved to apixaban_pilot_24.csv")
