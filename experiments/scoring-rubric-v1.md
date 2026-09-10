# Blind scoring rubric v1

Status: draft ready for advisor review; freeze before observing arm outputs.

## Unit of scoring

Reviewers split each answer into atomic claims. A numeric claim is atomic when
it has one issuer, metric, period, unit, and value. A trend or anomaly statement
is scored against its supporting gold label and evidence record.

## Primary measures

| Measure | Score rule |
|---|---|
| Factual correctness | 1 if the claim agrees with the gold observation or correctly states that the value is missing/conflicting; 0 otherwise. |
| Evidence completeness | 1 if a published claim has source ID and a page/table/section locator; 0 otherwise. |
| Citation correctness | 1 if the cited source actually supports the claim's issuer, metric, value, and period; 0 otherwise. |
| Coverage discipline | 1 if every required metric is returned or explicitly marked unavailable with a valid reason; 0 otherwise. |
| Anomaly classification | 1 if the label matches the independently reviewed gold category: true contradiction, explainable divergence, data conflict, or insufficient evidence. |

Report each measure as numerator/denominator and percentage. Do not hide
unscorable claims; classify them as contract or review failures.

## Secondary measures

- invalid payloads and contract violations per run;
- wall-clock latency per question;
- model calls, token counts, and cost estimate;
- number of critique attempts and unresolved cases.

## Review procedure

1. Freeze the gold labels, question set, rubric, and arm configuration.
2. Randomize answer order and hide the arm identity from reviewers.
3. Use two independent checkers for the review subset.
4. Resolve disagreements by an adjudicator or report them as unresolved.
5. Preserve the original answer, reviewer decisions, and reason codes.

Each review record must also include the run ID and the frozen evaluation
binding: snapshot ID, question-set SHA-256, rubric version, prompt version, and
model ID. The scoring CLI rejects a file that mixes any frozen binding across
records. This is a data-integrity guard, not a claim about model quality.

## Interpretation guardrails

- A higher score on one question is not evidence of universal multi-agent
  superiority.
- Compare arms on the same questions and accepted inputs.
- Report paired differences plus latency/cost trade-offs.
- Treat a null or negative result as valid.
- Do not use prose fluency as a primary outcome.
