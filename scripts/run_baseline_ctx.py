"""
Baseline rerun of the 24-case pilot with an explicit context window.

Same cases, model, prompts, temperature and num_predict as
run_clean_pilot.py. Changes:
  1. num_ctx is set explicitly (Ollama's default is too small for these notes).
  2. prompt_eval_count, eval_count and done_reason are saved for every call,
     so truncation of the input or the output can be checked afterwards.
  3. The literal "NA" response is preserved on every CSV read.
  4. A timeout on one method no longer skips the other method.
  5. Writes to a new file, so clean_pilot_results.csv is untouched.
"""

import time
from pathlib import Path

import pandas as pd
import requests


# --------------------------------------------------
# Settings
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent
INPUT_FILE = PROJECT_DIR / "apixaban_pilot_24.csv"
OUTPUT_FILE = PROJECT_DIR / "baseline_ctx8k_results.csv"

MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://localhost:11434/api/chat"

TEMPERATURE = 0
NUM_PREDICT = 160
NUM_CTX = 8192          # pilot notes max out around 7,100 tokens
TIMEOUT = (10, 900)

METHODS = ["direct", "evidence"]
TEXT_COLUMNS = [f"{m}_{c}" for m in METHODS for c in ("response", "done_reason")]


# --------------------------------------------------
# Model call
# --------------------------------------------------

def ask_model(prompt, num_ctx=NUM_CTX):
    """Query Ollama; return the answer plus token counts."""

    options = {"temperature": TEMPERATURE, "num_predict": NUM_PREDICT}
    if num_ctx is not None:
        options["num_ctx"] = num_ctx

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": options,
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()

    answer = data["message"]["content"]
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Ollama returned an empty response.")

    return {
        "answer": answer.strip(),
        "prompt_tokens": data.get("prompt_eval_count"),
        "gen_tokens": data.get("eval_count"),
        "done_reason": data.get("done_reason", ""),
    }


# --------------------------------------------------
# Prompt construction (unchanged from run_clean_pilot.py)
# --------------------------------------------------

def build_prompts(note, question):
    direct = f"""
Answer the question using only the clinical note below.
If the note does not contain enough information, respond:
INSUFFICIENT INFORMATION

Clinical note:
{note}

Question: {question}

Give a concise answer.
"""

    evidence_first = f"""
Answer the question using only the clinical note below.

First identify the specific text that supports your answer.
Then provide your answer based on that evidence.

If the note does not contain enough information, say:
INSUFFICIENT INFORMATION.

Do not invent missing values or facts.

Clinical note:
{note}

Question: {question}

Use this format:
Evidence: [quote or concise description of supporting text]
Answer: [answer or INSUFFICIENT INFORMATION]
"""

    return direct, evidence_first


# --------------------------------------------------
# Saving and loading
# --------------------------------------------------

def read_results():
    """Read results so a literal "NA" answer stays a string."""
    return pd.read_csv(
        OUTPUT_FILE,
        dtype={c: str for c in TEXT_COLUMNS},
        keep_default_na=False,
    )


def save_results(results):
    """Save atomically, then verify the saved responses."""

    temporary_file = OUTPUT_FILE.with_suffix(".tmp")
    results.sort_values("pilot_id").to_csv(temporary_file, index=False)
    temporary_file.replace(OUTPUT_FILE)

    saved = read_results()

    if len(saved) != len(results):
        raise RuntimeError("Saved file has the wrong number of rows.")
    if saved["pilot_id"].duplicated().any():
        raise RuntimeError("Saved file contains duplicate pilot IDs.")

    for column in ["direct_response", "evidence_response"]:
        expected = results.set_index("pilot_id")[column].fillna("").astype(str).sort_index()
        actual = saved.set_index("pilot_id")[column].fillna("").astype(str).sort_index()
        if not expected.equals(actual):
            raise RuntimeError(f"Saved {column} values do not match memory.")


def has_response(value):
    return isinstance(value, str) and bool(value.strip())


# --------------------------------------------------
# One model call for one method
# --------------------------------------------------

def run_method(results, idx, method, prompt, pilot_id, n_cases):
    print(f"Case {pilot_id}/{n_cases}: running {method} prompt...")

    start = time.perf_counter()
    try:
        out = ask_model(prompt)
    except requests.exceptions.Timeout:
        print(f"Case {pilot_id}: {method} prompt timed out. Rerun to resume.")
        return
    elapsed = time.perf_counter() - start

    results.at[idx, f"{method}_response"] = out["answer"]
    results.at[idx, f"{method}_seconds"] = round(elapsed, 2)
    results.at[idx, f"{method}_prompt_tokens"] = out["prompt_tokens"]
    results.at[idx, f"{method}_gen_tokens"] = out["gen_tokens"]
    results.at[idx, f"{method}_done_reason"] = out["done_reason"]
    save_results(results)

    print(
        f"  saved ({elapsed:.1f}s) | prompt tokens: {out['prompt_tokens']} "
        f"| generated: {out['gen_tokens']} | done: {out['done_reason']}"
    )
    if out["prompt_tokens"] and out["prompt_tokens"] >= NUM_CTX:
        print("  WARNING: prompt reached num_ctx; input may be truncated.")
    if out["done_reason"] == "length":
        print("  WARNING: output hit num_predict; answer may be cut off.")


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Pilot file not found: {INPUT_FILE}")

    pilot = pd.read_csv(INPUT_FILE)

    required = ["pilot_id", "note_id", "question", "text",
                "answer", "question_type", "not_specified"]
    missing = [c for c in required if c not in pilot.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if pilot["pilot_id"].duplicated().any():
        raise ValueError("The input pilot contains duplicate pilot IDs.")

    if OUTPUT_FILE.exists():
        results = read_results()
        if results["pilot_id"].duplicated().any():
            raise ValueError("Results file has duplicate IDs; inspect it first.")
        if set(results["pilot_id"].astype(int)) != set(pilot["pilot_id"].astype(int)):
            raise ValueError("Saved results do not match the pilot IDs.")
        results["pilot_id"] = results["pilot_id"].astype(int)
        results = (results.set_index("pilot_id")
                   .reindex(pilot["pilot_id"].astype(int))
                   .reset_index())
    else:
        results = pd.DataFrame({
            "pilot_id": pilot["pilot_id"].astype(int),
            "note_id": pilot["note_id"],
            "question": pilot["question"],
            "question_type": pilot["question_type"],
            "reference_answer": pilot["answer"],
            "not_specified": pilot["not_specified"],
            "note_chars": pilot["text"].astype(str).str.len(),
        })
        for m in METHODS:
            results[f"{m}_response"] = ""
            results[f"{m}_seconds"] = float("nan")
            results[f"{m}_prompt_tokens"] = float("nan")
            results[f"{m}_gen_tokens"] = float("nan")
            results[f"{m}_done_reason"] = ""
        save_results(results)

    print("Pilot cases:", len(pilot))
    print("Model:", MODEL)
    print("Output:", OUTPUT_FILE)
    print(f"Settings: temperature={TEMPERATURE} | num_predict={NUM_PREDICT} "
          f"| num_ctx={NUM_CTX}\n")

    for _, row in pilot.iterrows():
        pilot_id = int(row["pilot_id"])
        idx = results.index[results["pilot_id"] == pilot_id][0]
        prompts = dict(zip(METHODS, build_prompts(str(row["text"]), str(row["question"]))))

        for method in METHODS:
            if not has_response(results.at[idx, f"{method}_response"]):
                run_method(results, idx, method, prompts[method], pilot_id, len(pilot))

    # Final check, read back from disk with NA preserved
    results = read_results()
    print("\nBaseline run finished.")
    print("Total cases:", len(results))
    for m in METHODS:
        complete = results[f"{m}_response"].apply(has_response).sum()
        tokens = pd.to_numeric(results[f"{m}_prompt_tokens"], errors="coerce")
        cut_off = (results[f"{m}_done_reason"] == "length").sum()
        print(f"{m}: {complete}/{len(results)} responses | "
              f"max prompt tokens: {tokens.max():.0f} | "
              f"hit num_predict: {cut_off}")
    print("Results saved to:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
