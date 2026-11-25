

import time
from pathlib import Path

import pandas as pd
import requests


# --------------------------------------------------
# Settings
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent
INPUT_FILE = PROJECT_DIR / "apixaban_pilot_24.csv"
OUTPUT_FILE = PROJECT_DIR / "clean_pilot_results.csv"

MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://localhost:11434/api/chat"

# Use the same settings for both prompting methods.
TEMPERATURE = 0
NUM_PREDICT = 160
TIMEOUT = (10, 900)


# --------------------------------------------------
# Model call
# --------------------------------------------------

def ask_model(prompt):
    """Query the local Ollama model and reject empty answers."""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {
                "temperature": TEMPERATURE,
                "num_predict": NUM_PREDICT,
            },
        },
        timeout=TIMEOUT,
    )

    response.raise_for_status()
    answer = response.json()["message"]["content"]

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError(
            "Ollama returned an empty response. "
            "This response was not saved as complete."
        )

    return answer.strip()


# --------------------------------------------------
# Prompt construction
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
# Save progress safely
# --------------------------------------------------


def save_results(results):
    """Save atomically, then verify the saved responses."""

    temporary_file = OUTPUT_FILE.with_name(
        "clean_pilot_results.tmp"
    )

    # Write a complete temporary copy first.
    results.sort_values("pilot_id").to_csv(
        temporary_file, index=False
    )

    # Replace the original only after writing succeeds.
    temporary_file.replace(OUTPUT_FILE)

    # Read the actual saved file back from disk.
    saved = pd.read_csv(
    OUTPUT_FILE,
    dtype={"direct_response": str, "evidence_response": str},
    keep_default_na=False
    )

    if len(saved) != len(results):
        raise RuntimeError(
            "Saved file has the wrong number of rows."
        )

    if saved["pilot_id"].duplicated().any():
        raise RuntimeError(
            "Saved file contains duplicate pilot IDs."
        )

    for column in ["direct_response", "evidence_response"]:
        expected = results.set_index("pilot_id")[column].fillna("")
        actual = saved.set_index("pilot_id")[column].fillna("")

        expected = expected.astype(str).sort_index()
        actual = actual.astype(str).sort_index()

        if not expected.equals(actual):
            raise RuntimeError(
                f"Saved {column} values do not match memory."
            )


def has_response(value):
    """Return True only for a nonempty saved response."""

    return isinstance(value, str) and bool(value.strip())


# --------------------------------------------------
# Main experiment
# --------------------------------------------------

def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Pilot file not found: {INPUT_FILE}"
        )

    pilot = pd.read_csv(INPUT_FILE)

    required = [
        "pilot_id", "note_id", "question", "text",
        "answer", "question_type", "not_specified"
    ]

    missing = [col for col in required if col not in pilot.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if pilot["pilot_id"].duplicated().any():
        raise ValueError("The input pilot contains duplicate pilot IDs.")

    # Start a completely separate results file.
    # If this script is interrupted, the next run resumes from it.
    if OUTPUT_FILE.exists():
        results = pd.read_csv(
        OUTPUT_FILE,
        keep_default_na=False
    )

        if results["pilot_id"].duplicated().any():
            raise ValueError(
                "The clean results file contains duplicate IDs. "
                "Please inspect it before continuing."
            )

        expected_ids = set(pilot["pilot_id"].astype(int))
        saved_ids = set(results["pilot_id"].astype(int))

        if saved_ids != expected_ids:
            raise ValueError(
                "The saved results do not match the pilot IDs. "
                "Please inspect the clean results file.")

        results["pilot_id"] = results["pilot_id"].astype(int)
        results = results.set_index("pilot_id").reindex(
            pilot["pilot_id"].astype(int)
        ).reset_index()

    else:
        results = pd.DataFrame({
            "pilot_id": pilot["pilot_id"].astype(int),
            "note_id": pilot["note_id"],
            "question": pilot["question"],
            "question_type": pilot["question_type"],
            "reference_answer": pilot["answer"],
            "not_specified": pilot["not_specified"],
            "direct_response": "",
            "direct_seconds": float("nan"),
            "evidence_response": "",
            "evidence_seconds": float("nan"),
        })
        save_results(results)

    print("Pilot cases:", len(pilot))
    print("Model:", MODEL)
    print("Output:", OUTPUT_FILE)
    print("Settings: temperature =", TEMPERATURE,
          "| max generated tokens =", NUM_PREDICT)
    print("Starting local inference...\n")

    for _, row in pilot.iterrows():
        pilot_id = int(row["pilot_id"])
        result_index = results.index[
            results["pilot_id"] == pilot_id
        ][0]

        note = str(row["text"])
        question = str(row["question"])
        direct_prompt, evidence_prompt = build_prompts(
            note, question
        )

        # Run direct prompting if it has not been completed.
        if not has_response(results.at[result_index, "direct_response"]):
            print(
                f"Case {pilot_id}/{len(pilot)}: "
                "running direct prompt..."
            )

            start = time.perf_counter()
            try:
                answer = ask_model(direct_prompt)
            except requests.exceptions.Timeout:
                print(
                    f"Case {pilot_id}: direct prompt timed out. "
                    "Skipping for now."
                )
                continue
            elapsed = time.perf_counter() - start

            results.at[result_index, "direct_response"] = answer
            results.at[result_index, "direct_seconds"] = round(
                elapsed, 2
            )
            save_results(results)

            print(f"Direct response saved ({elapsed:.1f}s).")

        # Run evidence-first prompting if it has not been completed.
        if not has_response(
            results.at[result_index, "evidence_response"]
        ):
            print(
                f"Case {pilot_id}/{len(pilot)}: "
                "running evidence-first prompt..."
            )

            start = time.perf_counter()
            answer = ask_model(evidence_prompt)
            elapsed = time.perf_counter() - start

            results.at[result_index, "evidence_response"] = answer
            results.at[result_index, "evidence_seconds"] = round(
                elapsed, 2
            )
            save_results(results)

            print(
                f"Evidence-first response saved ({elapsed:.1f}s)."
            )

        print(f"Case {pilot_id} saved.\n")

    # Final integrity check: read results from disk
    results = pd.read_csv(OUTPUT_FILE)

    direct_complete = results["direct_response"].apply(has_response)
    evidence_complete = results["evidence_response"].apply(has_response)

    print("\nClean pilot run finished.")
    print("Total cases:", len(results))
    print("Cases with direct responses:", int(direct_complete.sum()))
    print(
        "Cases with evidence-first responses:",
        int(evidence_complete.sum())
    )
    print(
        "Cases with both responses:",
        int((direct_complete & evidence_complete).sum())
    )
    print("Results saved to:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
