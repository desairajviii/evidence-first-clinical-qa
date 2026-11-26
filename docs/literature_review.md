# Literature Review

## A Taxonomy of Prompt Defects in LLM Systems (Tian et al., 2025, arXiv:2509.14404)

This paper addresses prompt failures in general software systems rather than medical applications specifically. The authors conducted a broad survey of prompt engineering and LLM robustness research, organizing prompt failures into six top-level categories. This work establishes a useful reference point for distinguishing "prompt wording" issues from "overly restrictive instructions," two categories that can otherwise overlap.

## SycEval: Evaluating LLM Sycophancy (Fanous et al., Stanford University, arXiv:2502.08177)

This study evaluated ChatGPT-4o, Claude-Sonnet, and Gemini-1.5-Pro on mathematics questions and medical advice questions drawn from the MedQuad dataset. The authors distinguish between two forms of sycophancy. Progressive sycophancy occurs when a model agrees with the user and still arrives at the correct answer, observed in 43.52% of cases. Regressive sycophancy occurs when agreement with the user produces an incorrect answer, observed in 14.66% of cases. Overall sycophantic behavior across the three models was 58.19%. This distinction provides a basis for refining the "leading/confirmatory language" category rather than treating all instances uniformly.

## Knowing When to Abstain: Medical LLMs Under Clinical Uncertainty (Machcha et al., 2026, arXiv:2601.12471)

This paper introduces MedAbstain, a benchmark for evaluating abstention behavior in medical question answering. The central finding is that providing a model with an explicit abstention option increases cautious behavior substantially more than increasing model size, or than applying chain-of-thought or few-shot prompting. Their abstention option is implemented as an added multiple-choice answer, a methodological distinction from a free-text instruction approach. The direction of the finding nonetheless supports the broader pattern that explicit abstention framing, rather than model scale, is the primary driver of cautious behavior.

## When Confidence Fails: Overconfidence in LLMs under Uncertainty and Missing Clinical Information (arXiv:2608.09080)

This paper presents a complementary finding to MedAbstain. Even when an explicit abstention option is available, models demonstrate a strong bias toward producing an answer rather than acknowledging insufficient information. A substantial proportion of resulting incorrect answers are accompanied by high stated confidence. Considered alongside MedAbstain, this provides a coherent explanation for why prompt wording shifts which failure mode predominates, over-abstention versus under-abstention, rather than eliminating either one.

## This Treatment Works, Right? Evaluating LLM Sensitivity to Patient Question Framing in Medical QA (Yun et al., 2026, arXiv:2604.05051)

This study examined how positive versus negative framing of the same clinical question affects model responses, using a retrieval-augmented generation setup grounded in clinical trial evidence. The central finding is that asking the same question with positive framing ("Does this treatment work?") versus negative framing ("Does this treatment not work?") produces measurably less consistent conclusions than asking the same framing twice, approximately 72% agreement compared to 76%, and this inconsistency increases across multi-turn conversations. A related finding, that LLMs can selectively cite evidence to make a misleading answer appear credible, originates from a separate study (Ajwani et al.) cited within this paper rather than from Yun et al.'s own experiment.

## Mapping to Taxonomy Categories

- Ambiguous terminology: Tian et al.
- Leading or confirmatory language: SycEval, Yun et al.
- Requests for unsupported decisions: Ajwani et al., as cited within Yun et al.
- Inadequate evidence instructions: MedAbstain, the overconfidence paper
- Missing context / missing timing: requires further review
- Unclear task format: Tian et al.
- Incorrect assumptions: Yun et al.