# Blind human scoring protocol for analysis-report-v2

This protocol evaluates the user-facing report, not the number of agents used
to produce it. The reviewer sees a packet with the arm, model, run ID and
manifest filename removed. Gold data and page-aware evidence remain visible so
the reviewer can check the claims.

## Dimensions

Score every packet on a 0–4 scale. A score must have a short decision basis;
empty scores or unsupported machine scores are invalid.

| Dimension | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| Correctness | materially wrong or fabricated | several major errors | mixed; material caveat or partial errors | mostly correct; only minor issues | fully correct within declared scope |
| Usefulness | unusable for the stated question | mostly repeats data | adequate summary but weak “so what” | useful prioritization/comparison | decision-useful, specific and appropriately scoped |
| Evidence | absent, wrong or misleading | a few references but not traceable | partial page/source support | mostly traceable with minor gaps | claims can be followed to the correct source/page/evidence |
| Limitation | hides or misstates limitations | generic disclaimer only | mentions some missingness/scope limits | clear limits for most material claims | limitations are precise, actionable and prevent overclaiming |

## Review procedure

1. Read the question and scope in the packet.
2. Read the headline, comparison, issuer profiles and claims.
3. Check the material claims against the Gold reference and the evidence catalog.
4. Score all four dimensions independently of the machine diagnostics.
5. Write one or two sentences explaining the score, including the most important
   error or strength.

The local blind reviewer console is `research/evaluation-ui/review.html`.

The queue is arm-blind, not issuer-blind: issuer names and periods are needed to
check factual correctness. Do not infer a score from the presence of more claims
or more evidence IDs. A report with more content can still be less correct or
less useful.

## Aggregation

For each packet, the normalized quality score is the mean of the four scores
divided by four. The primary comparison reports the mean and median by workload
tier and arm, plus each arm's cost, latency, token count and failure rate.

The crossover is not declared from cost alone. It is the smallest workload tier
where a multi-agent arm has a pre-registered quality gain of at least 0.05 over
single-agent, does not lose evidence/limitation discipline, the result is
visible across repetitions, and both compared arms complete all planned
repetitions. The last condition prevents selective-completion bias: a fragile
arm cannot qualify by scoring only the runs that happened to finish.

The semantic quality mean is reported separately from the secondary
completion-adjusted quality (`semantic quality mean × completion rate`). The
adjusted value is useful for deployment decisions, but it is not a replacement
for human quality scoring. If no tier meets all conditions, the result is
reported as “no observed crossover”, not as a universal negative theorem.
