# E1 audit of escaped mutants (orchestrator, 2026-10-13, zero model calls)
Source: experiments/mut1/mutants.jsonl (1,210 mutants; 71 escaped; 4 operators have escapes).
Post-hoc classification by the orchestrator (heuristic, not a blind label): a mutant is "degenerate" when it
makes the sentence refer to itself (same entity twice in a comparison, "từ quý X đến quý X", "thấp nhất – thấp nhất").

| Operator | All n | Degenerate | Substantive n | Caught | Rate | Wilson 95% |
|---|---|---|---|---|---|---|
| period | 118 | 14 (0 caught) | 104 | 98 | 94.2% | [88.0, 97.3] |
| entity_swap | 123 | 21 (4 caught) | 102 | 102 | 100% | [96.4, 100] |
| direction_flip | 76 | 6 (0 caught) | 70 | 67 | 95.7% | [88.1, 98.5] |
| metric_swap | 120 | 0 | 120 | 95 | 79.2% | [71.1, 85.5] |

Reading: 37 of the 71 escapes (52%) are self-referential mutants the generator should not have produced as realistic
errors (a gap, but a different, narrower one: no self-comparison check). The real weakness is metric_swap: when the
sentence keeps a number and only the metric name changes (e.g. "bao phủ nợ xấu của HDB là 50,0%" -> "nợ xấu ... 50,0%"),
the verifier accepts 25 of 120 (20.8%). Remaining 9 substantive escapes: period (6) and direction_flip (3), concentrated
in sentences with a qualitative direction/period clause without its own number.
