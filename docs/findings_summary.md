# Pilot follow-up: comparison of runs 

All runs use the same pilot cases (8 yes/no, 8 numeric, 8 not-specified questions), temperature 0, local Ollama. Numbers are correct answers.

| Run | Model | Setup change | Direct: yes/no | Direct: numeric | Direct: all answerable (abstained) | Evidence-first: yes/no | Evidence-first: numeric | Evidence-first: all answerable (abstained) |
|---|---|---|---|---|---|---|---|---|
| Original pilot | 3B | Default context (notes cut off) | 5 | 0 | 5/16 (10) | 0 | 0 | 0/16 (16) |
| Baseline | 3B | Full note (num_ctx=8192) | 2 | 0 | 2/16 (13) | 0 | 0 | 0/16 (15) |
| v2 | 3B | Removed "INSUFFICIENT INFORMATION" instruction | 7 | 0 | 7/16 (8) | 6 | 1 | 7/16 (6) |
| v3 | 7B | Same as v2 | 8 | 5 | 13/16 (3) | 8 | 2 | 10/16 (2) |


Original pilot scored by hand from the original pilot summary, using the same rules as score_results.py.

Not-specified questions (correct = abstained): 8/8 in every run, except one evidence-first case in the baseline that got stuck repeating itself.

Extra check with 8 new Yes questions (7B, v2 prompt): direct 5/8, evidence-first 6/8. The original yes/no set was 7 No and 1 Yes, so the perfect yes/no score was partly from leaning toward No.

Speed: about 12 seconds per call for 3B, about 30 seconds for 7B.

## Key findings

1. **Setup issue: notes were being cut off.** For one test note, Ollama's default context read only about 2,000 of about 4,800 prompt tokens. Setting num_ctx fixed it, but abstention barely changed on its own.
2. **Overly restrictive instructions caused most yes/no abstentions.** Our extra "INSUFFICIENT INFORMATION" instruction made the model abstain even when it said the condition wasn't mentioned. Removing it fixed yes/no abstention.
3. **Model size mattered most for numeric questions.** The 3B model sometimes quoted the right value and still answered NA. The 7B model got 5/8 numeric correct with direct prompting.
4. **Evidence-first anchors on one piece of evidence.** On "highest/lowest value" questions it quoted a single lab line and answered from it, giving 4 wrong numeric answers on 7B.
5. **Possible annotation issue.** LVEF questions say to answer 55 if the value is 55% or higher, but two reference answers are the raw values (70 and 66).
6. **Most yes/no questions only imply their answer rule.** Only 1 of 15 yes/no question templates (100 of 1,500 questions) states "Answer No unless…". The other 14 just ask "Does the note describe…?", which implies No when something isn't mentioned. All 800 numeric questions state "Answer NA if…". So v2 helped yes/no mainly by removing the INSUFFICIENT INFORMATION option.

**Relevance to the taxonomy:** findings 2 and 4 are examples of "overly restrictive instructions / response formats." Finding 6 relates to "prompt wording."
