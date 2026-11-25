import pandas as pd

df = pd.read_csv("apixaban_dataset.csv")
pilot = pd.read_csv("apixaban_pilot_24.csv")

# Yes/no questions whose reference answer is Yes
yes_cases = df[(df["question_type"] == "yes") & (df["answer"].str.lower() == "yes")]

# Leave out any question already in the 24-case pilot
used = set(zip(pilot["note_id"], pilot["question"]))
keep = [(n, q) not in used for n, q in zip(yes_cases["note_id"], yes_cases["question"])]
yes_cases = yes_cases[keep]

# Pick 8 at random and number them 25-32
extra = yes_cases.sample(n=8, random_state=42).reset_index(drop=True)
extra.insert(0, "pilot_id", range(25, 33))
extra.to_csv("apixaban_yes_8.csv", index=False)

print("Saved", len(extra), "Yes cases to apixaban_yes_8.csv")