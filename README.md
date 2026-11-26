# CS 6120 Final Project - Group 7

**Evaluating Evidence-First LLM Prompting for Clinical Trial Eligibility Screening**

This repo holds the code and documentation for our pilot study comparing
direct prompting vs. evidence-first prompting on the
[MIMIC-IV-Ext-Apixaban-Trial-Criteria-Questions](https://physionet.org/content/mimic-iv-ext-apixaban-trial/1.0.0/)
dataset, plus the follow-up work building toward a taxonomy of clinical
prompting issues (per our professor's guidance on 11/13).

## Important: data access

This project uses restricted-access PhysioNet data (MIMIC-IV-Note and the
Apixaban trial criteria extension). **No patient data, note text, or model
responses derived from patient notes are stored in this repo.** Anyone
running these scripts needs their own PhysioNet credentialing, CITI
training, and signed Data Use Agreement, and must supply their own local
copy of `apixaban_dataset.csv`.

## Repo structure

```
.
├── scripts/              # All pilot + follow-up experiment scripts
│   ├── prepare_pilot.py          # Builds the balanced 24-case pilot sample
│   ├── run_clean_pilot.py        # Original pilot run (Qwen 2.5 3B)
│   ├── run_baseline_ctx.py       # Rerun with explicit num_ctx (rules out truncation)
│   ├── run_v2_follow_question.py # v2/v3 runs (prompt fix + 7B model); also used for the Yes-check run
│   ├── add_yes_cases.py          # Samples 8 extra Yes-labeled cases to check No-bias
│   ├── check_default_context.py  # Diagnostic: compares default vs. explicit context window
│   ├── check_questions.py        # Checks which question templates state their answer rule
│   ├── score_results.py          # Scores a results file (correct / wrong / abstained)
│   └── compare_runs.py           # Builds the cross-run comparison table
├── docs/
│   ├── Pilot_exp_procedure_description.pdf  # Step-by-step setup + run log
│   ├── Pilot_results_summary.pdf            # Original pilot findings
│   ├── findings_summary.md                  # v2/v3 follow-up findings
│   └── comparison_table.csv                 # Aggregate scores across all runs (no patient data)
├── .gitignore
└── README.md
```

## Pipeline, in order

1. **Setup**: Ollama (local inference) + the target model pulled locally.
   See `docs/Pilot_exp_procedure_description.pdf` for exact setup steps.
2. **`prepare_pilot.py`**: samples a balanced 24-case pilot from the full
   2,300-row dataset (8 yes/no, 8 numeric, 8 marked `not_specified`).
3. **Run an experiment script** (one of `run_clean_pilot.py`,
   `run_baseline_ctx.py`, or `run_v2_follow_question.py`, depending on which
   iteration you're reproducing — see "Run history" below).
4. **`score_results.py <results_file>.csv`**: scores one results file against
   the dataset's reference answers.
5. **`compare_runs.py`**: aggregates all scored runs into one comparison
   table (`comparison_table.csv`).

## Run history (what changed each time, and why)

| Run | Script | Model | Change from previous | Key result |
|---|---|---|---|---|
| Original pilot | `run_clean_pilot.py` | Qwen 2.5 3B | — | Evidence-first abstained on all 24 cases; suspected context truncation |
| Baseline (ctx) | `run_baseline_ctx.py` | Qwen 2.5 3B | Explicit `num_ctx=8192` | Ruled out truncation as the cause (see `check_default_context.py`) |
| v2 | `run_v2_follow_question.py` | Qwen 2.5 3B | Removed the "INSUFFICIENT INFORMATION" instruction line | Fixed most yes/no abstentions (2/16 → 7/16 correct) |
| v3 | `run_v2_follow_question.py` | Qwen 2.5 7B | Same prompt as v2, bigger model | 13/16 direct, 10/16 evidence-first correct |
| v3 Yes-check | `run_v2_follow_question.py` | Qwen 2.5 7B | 8 new Yes-labeled cases (`add_yes_cases.py`) | Confirmed earlier scores were partly inflated by a No-heavy sample |

Full detail and interpretation: `docs/findings_summary.md`.

## Known issues / limitations (carried forward into the taxonomy work)

- **Evidence-first can anchor on a single value** on "highest/lowest" numeric
  questions, quoting one lab result and answering from it alone.
- **Two LVEF reference answers break the dataset's own stated rule**
  (should be capped at 55, but are recorded as 70 and 66).
- **Only 1 of 15 yes/no question templates explicitly states its answer
  rule** ("Answer No unless..."); the other 14 only imply it, which is a
  concrete example of the "prompt wording" taxonomy category.

## Taxonomy of clinical prompting issues (in progress)

Following professor feedback on 11/13, the project is extending beyond the
direct-vs-evidence-first comparison into a taxonomy of prompting issues.
Categories scorable against existing reference answers (owned by Aashna):
ambiguous terminology, leading/confirmatory language, requests for
unsupported decisions, inadequate-evidence instructions.

Categories requiring manual annotation (open, assigned 11/25): missing
context, missing timing, unclear task format, incorrect assumptions.

## Contributors

Elizabeth Mutina, Aashna Mathur, Siddhi Nirmale, Rajvi Desai, Atharva
