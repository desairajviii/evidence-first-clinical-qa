"""
Taxonomy experiments: one prompt change per category.

Setup (same as v3): qwen2.5:7b, direct prompt from v2, temperature 0,
num_ctx 8192, num_predict 160. The v3 answers are the baseline.

Conditions (codebook codes):
  B1         Ambiguous request: clinical term replaced with a vague one   (16 yes/no cases)
  B2         Leading framing: "The answer is No, right?"                  (9 Yes cases)
  B2_mirror  Leading framing: "The answer is Yes, right?"                 (7 No cases)
  B3         Forced answer: "Give a single number even if..."             (8 not-specified cases)
  B4         Unsatisfiable evidence demand: "quote the exact sentence"    (7 No cases)
  B5         Conflicting answer rule: INSUFFICIENT INFORMATION line added (32 cases + 8 explicit-rule cases)
  BASELINE   v2 prompt unchanged, only for the 8 explicit-rule cases (the other 32 already have v3 answers)

Usage:
    python3 run_experiments.py
Stop with Ctrl+C anytime; running it again continues where it stopped.
"""

import time
from pathlib import Path

import pandas as pd
import requests

PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = PROJECT_DIR / "experiment_results.csv"
EXPLICIT_FILE = PROJECT_DIR / "apixaban_explicit_8.csv"

MODEL = "qwen2.5:7b"
OLLAMA_URL = "http://localhost:11434/api/chat"
TEMPERATURE = 0
NUM_PREDICT = 160
NUM_CTX = 8192
TIMEOUT = (10, 900)

# --------------------------------------------------
# Prompt wording
# --------------------------------------------------

# B1: only the clinical term changes; "Does the note describe..." stays.
VAGUE_TERMS = {
    "a planned or past ablation procedure for afib": "a heart procedure",
    "Diabetes mellitus (DM1, DM2, T2D, T1DM, T2DM)": "blood sugar problems",
    "arterial hypertension on treatment (high bp e.g. >140, or HTN)": "blood pressure issues",
    "peptic ulcer disease": "stomach problems",
    "a stroke or transient ischemic attack": "a brain problem",
    "depression or major depressive disorder (MDD)": "mood problems",
    "any hemorrhagic tendencies or blood dyscrasias": "blood problems",
    "a serious bleeding in the past 6 months": "bleeding issues in the past 6 months",
    "valvular disease requiring surgery (stenosis)": "heart valve problems",
    "bipolar disorder": "mood problems",
    "permanent, paroxysmal, or persistent afib": "heart rhythm issues",
}

B2_TEXT = " The answer is No, right?"
B2_MIRROR_TEXT = " The answer is Yes, right?"
B3_TEXT = " Give a single number even if the note doesn't state it clearly."
B4_TEXT = (" Before answering, quote the exact sentence from the note that "
           "supports your answer. Do not answer without a quote.")
B5_LINE = "If the note does not contain enough information, answer INSUFFICIENT INFORMATION.\n"


def build_prompt(note, question, extra_line=""):
    """The v2 direct prompt. extra_line is only used for B5."""
    return f"""
Answer the question using only the clinical note below.
Follow any answer instructions given in the question.
{extra_line}
Clinical note:
{note}

Question: {question}

Give a concise answer.
"""


def make_vague(question):
    for term, vague in VAGUE_TERMS.items():
        if term in question:
            return question.replace(term, vague)
    raise ValueError(f"No vague term defined for: {question}")


# --------------------------------------------------
# Cases
# --------------------------------------------------

def load_cases():
    pilot = pd.read_csv(PROJECT_DIR / "apixaban_pilot_24.csv", keep_default_na=False)
    yes8 = pd.read_csv(PROJECT_DIR / "apixaban_yes_8.csv", keep_default_na=False)

    # 8 cases of the one template that states "Answer no unless..." (4 Yes, 4 No)
    if not EXPLICIT_FILE.exists():
        df = pd.read_csv(PROJECT_DIR / "apixaban_dataset.csv", keep_default_na=False)
        template = df[df["question"].str.contains("unable to make medical decisions")]
        explicit = pd.concat([
            template[template["answer"] == "Yes"].sample(n=4, random_state=42),
            template[template["answer"] == "No"].sample(n=4, random_state=42),
        ]).reset_index(drop=True)
        explicit.insert(0, "pilot_id", range(33, 41))
        explicit.to_csv(EXPLICIT_FILE, index=False)
    explicit = pd.read_csv(EXPLICIT_FILE, keep_default_na=False)

    return pd.concat([pilot, yes8], ignore_index=True), explicit


def build_jobs():
    """Return a list of (condition, case_row, question_text, extra_line)."""
    cases, explicit = load_cases()
    yes_no = cases[cases["question_type"] == "yes"]
    yes_cases = yes_no[yes_no["answer"] == "Yes"]
    no_cases = yes_no[yes_no["answer"] == "No"]
    not_specified = cases[cases["not_specified"].astype(str) == "1"]

    jobs = []
    for _, r in yes_no.iterrows():
        jobs.append(("B1", r, make_vague(r["question"]), ""))
    for _, r in yes_cases.iterrows():
        jobs.append(("B2", r, r["question"] + B2_TEXT, ""))
    for _, r in no_cases.iterrows():
        jobs.append(("B2_mirror", r, r["question"] + B2_MIRROR_TEXT, ""))
    for _, r in not_specified.iterrows():
        jobs.append(("B3", r, r["question"] + B3_TEXT, ""))
    for _, r in no_cases.iterrows():
        jobs.append(("B4", r, r["question"] + B4_TEXT, ""))
    for _, r in pd.concat([cases, explicit]).iterrows():
        jobs.append(("B5", r, r["question"], B5_LINE))
    for _, r in explicit.iterrows():
        jobs.append(("BASELINE", r, r["question"], ""))
    return jobs


# --------------------------------------------------
# Model call
# --------------------------------------------------

def ask_model(prompt):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": TEMPERATURE,
                        "num_predict": NUM_PREDICT,
                        "num_ctx": NUM_CTX},
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    answer = data["message"]["content"].strip()
    if not answer:
        raise ValueError("Ollama returned an empty response.")
    return answer, data.get("prompt_eval_count"), data.get("done_reason", "")


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    jobs = build_jobs()

    if OUTPUT_FILE.exists():
        results = pd.read_csv(OUTPUT_FILE, keep_default_na=False).to_dict("records")
    else:
        results = []
    done = {(r["condition"], int(r["pilot_id"])) for r in results}

    print(f"Model: {MODEL} | {len(jobs)} jobs | already done: {len(done)}\n")

    for i, (condition, r, question, extra_line) in enumerate(jobs, start=1):
        key = (condition, int(r["pilot_id"]))
        if key in done:
            continue

        print(f"[{i}/{len(jobs)}] {condition}, case {key[1]}...", end=" ", flush=True)
        start = time.perf_counter()
        try:
            answer, tokens, done_reason = ask_model(build_prompt(r["text"], question, extra_line))
        except requests.exceptions.Timeout:
            print("timed out, skipping (rerun to retry)")
            continue
        seconds = round(time.perf_counter() - start, 2)

        results.append({
            "condition": condition,
            "pilot_id": key[1],
            "note_id": r["note_id"],
            "question_type": r["question_type"],
            "reference_answer": r["answer"],
            "not_specified": r["not_specified"],
            "question_used": question,
            "response": answer,
            "seconds": seconds,
            "prompt_tokens": tokens,
            "done_reason": done_reason,
        })
        pd.DataFrame(results).to_csv(OUTPUT_FILE, index=False)
        print(f"saved ({seconds}s, {tokens} tokens)")
        if done_reason == "length":
            print("   WARNING: answer hit num_predict and may be cut off")

    print(f"\nFinished. {len(results)}/{len(jobs)} answers in {OUTPUT_FILE.name}")


if __name__ == "__main__":
    main()
