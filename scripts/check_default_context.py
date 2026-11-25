"""
Runs pilot case 1 (direct prompt) twice: once with Ollama's default context
and once with num_ctx=8192, and prints how many prompt tokens Ollama actually
processed each time. If the default run processes far fewer tokens than the
8192 run, the original pilot notes were being truncated.
"""

from pathlib import Path

import pandas as pd

from run_baseline_ctx import ask_model, build_prompts

PROJECT_DIR = Path(__file__).resolve().parent
pilot = pd.read_csv(PROJECT_DIR / "apixaban_pilot_24.csv")
row = pilot[pilot["pilot_id"] == 1].iloc[0]

direct_prompt, _ = build_prompts(str(row["text"]), str(row["question"]))

print("Note length:", len(str(row["text"])), "characters")
print("Reference answer:", row["answer"], "\n")

for label, ctx in [("Ollama default", None), ("num_ctx=8192", 8192)]:
    out = ask_model(direct_prompt, num_ctx=ctx)
    print(f"{label}:")
    print("  prompt tokens processed:", out["prompt_tokens"])
    print("  answer:", out["answer"][:200], "\n")
