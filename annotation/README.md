# Taxonomy annotation and inter-rater agreement

This folder holds the annotation study, which tests whether the project's taxonomy of clinical prompting issues is clear enough for different people to apply consistently. Two annotators independently labeled example prompts with the taxonomy categories, and `agreement.py` computes Cohen's kappa per category.

## The taxonomy

| Code | Category | Test (label 1 if yes) |
| --- | --- | --- |
| A1 | Missing context | Is information needed to answer, including which value or what time window, absent from the prompt? |
| A2 | Unsupported premise | Does the prompt present, as background it builds on, a patient fact the note does not support? |
| B1 | Ambiguous request | Could a key term or the task itself be read in two clinically different ways? |
| B2 | Leading framing | Does the wording signal which answer the user expects? |
| B3 | Forced answer | Does an instruction remove the option to express uncertainty? |
| B4 | Unsatisfiable evidence demand | Does the prompt require evidence the correct answer cannot provide? |
| B5 | Conflicting answer rule | Does an instruction contradict the answer rule the question itself sets? |

Full definitions, examples, boundary rules and the annotation procedure are in `docs/taxonomy_codebook.pdf`.

## Results (main round, 46 prompts, 2 annotators)

| Category | Cohen's κ | % agreement |
| --- | --- | --- |
| A1 Missing context | 0.56 | 91.3 |
| A2 Unsupported premise | 0.70 | 89.1 |
| B1 Ambiguous request | 0.80 | 93.5 |
| B2 Leading framing | 0.91 | 97.8 |
| B3 Forced answer | 1.00 | 100 |
| B4 Unsatisfiable evidence demand | 1.00 | 100 |
| B5 Conflicting answer rule | 1.00 | 100 |
| Primary label | 0.78 | 80.4 |

Mean κ across categories: 0.85. The instruction categories (B2–B5) were applied almost identically. The 13 disagreements clustered on two boundaries, which were settled in adjudication and added to the codebook:

- **A1 vs B1:** if the question is clear but doesn't say which value or when, it is A1 only; B1 only when a word or the task itself has more than one meaning.
- **A2 vs B4:** demanding proof that something didn't happen is B4; it is A2 only if the prompt states the absence as a fact it builds on.

These κ values were obtained with the **original codebook**, before adjudication. The two boundary rules were added afterwards and have not yet been re-tested on new items.

**Annotator familiarity.** The prompts and design labels were drafted with AI assistance for this taxonomy, not collected from real users. Annotator 1 co-developed the codebook and received clarifications of codebook rules (not labels) on two calibration items. Annotator 2 wrote the project's literature review and read the codebook before labeling. Both knew the item set's composition from the protocol. Neither annotator viewed the design key before finishing the main round.

Limitations: two annotators from the same team, 3–13 positive labels per category, and AI-drafted items reviewed by the team rather than real user prompts.

## Files

| File | What it is |
| --- | --- |
| `docs/taxonomy_codebook.pdf` | Category definitions, annotation guidelines, agreement protocol, revised boundary rules, references |
| `annotation/annotation_sheet_template.xlsx` | Blank labeling sheet: Instructions, Calibration (C01–C10), Main (M01–M46) |
| `scripts/agreement.py` | Computes agreement between two filled sheets |
| `annotation/results/annotator1.xlsx`, `annotation/results/annotator2.xlsx` | The two annotators' independent labels (before adjudication) |
| `annotation/results/design_key.csv` | Intended labels for each item, withheld from annotators until both finished |
| `annotation/results/agreement_results.csv` | Main-round agreement table |
| `annotation/results/calibration_agreement_results.csv` | Calibration-round agreement (practice round, not reported) |
| `annotation/results/disagreements.csv` | Items the annotators labeled differently, with their notes, used for adjudication |

## Data

The 56 prompts are paraphrased from the MIMIC-IV-Ext-Apixaban question templates. Each comes with a one-line synthetic "note facts" summary. **No patient data or note text is included in this folder.**

## Procedure

1. Each annotator read the codebook and labeled the Calibration tab on their own.
2. Annotators compared calibration labels and discussed disagreements; the rules were kept unchanged.
3. Each annotator labeled the Main tab independently, with no discussion.
4. Agreement was computed, disagreements adjudicated, and two boundary rules added to the codebook.

## Rerunning the agreement script

Requires Python 3 with `pandas` and `openpyxl`. From the repo root:

```
pip install pandas openpyxl
python scripts/agreement.py annotation/results/annotator1.xlsx annotation/results/annotator2.xlsx \
    --key annotation/results/design_key.csv --out-dir annotation/results
```

Add `--sheet Calibration` to check the calibration round. Categories with κ below 0.60 are flagged for refinement. This is an exploratory threshold chosen for this study, informed by McHugh (2012), not a universal standard.
