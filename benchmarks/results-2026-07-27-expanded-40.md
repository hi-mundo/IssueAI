# IssueAI expanded benchmark results — July 27, 2026

## Scope

- Combined dataset: 40 historical issue cases
- Composition:
  - 20 validated cases from `historical-route-20-v1`
  - 20 additive cases from `historical-route-20-v2`
- Evaluation question: are all expected real mechanisms present inside the top 100 ranked hypotheses?

## Primary result

- Observed result: **40/40 cases passed** `top100_all`

## Position telemetry

Case-level distribution:

- all expected mechanisms inside top 5: 4/40 cases
- all expected mechanisms inside top 10: 38/40 cases
- all expected mechanisms inside top 20: 40/40 cases

Mechanism-level distribution across 120 expected mechanisms:

- top 1: 10/120
- top 3: 40/120
- top 5: 68/120
- top 10: 118/120
- top 20: 120/120

## Important interpretation

This artifact is useful because it shows the current method is not merely passing
the first validated batch. It is also recovering the expected mechanisms on a
second independent batch.

That said, the second 20-case batch is still marked `proposed-from-artifacts`.
So this document should be read as strong internal benchmark evidence, not as a
claim that all 40 cases are manually gold-validated.

## What still needs improvement

- ranking purity among correlated mechanism families
- stronger top-3 and top-5 ordering
- broader validation-probe productization

## Worst-positioned successful cases

The most borderline successful cases in the current run still landed within the
top 20, but they show where ranking noise remains:

- `black-1102`
- `rails-49463`
- `requests-5846`
- `flask-5836`
