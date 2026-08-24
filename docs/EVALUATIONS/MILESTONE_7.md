# Milestone 7 Evaluation — Exploitative Modeling

- Date: 2026-08-24
- Result: Complete for synthetic profiles
- Live observation status: Not connected until Milestone 8
- Control status: Disabled

## Profile model

- Population priors and player evidence remain separate.
- Beta-Binomial updates retain occurrences, opportunities, posterior parameters, mean, standard
  deviation, approximate 95% interval, hand IDs, and evidence IDs.
- Statistic keys isolate position, street, and sizing buckets.
- Updates are immutable and reject unknown or duplicate slices and table-size-invalid positions.

## Exploit model

- Hero adjustments compare a posterior opponent frequency with a declared baseline.
- Deviations shrink by player sample size and population-prior confidence.
- Absolute action-frequency changes are policy-capped and other actions are renormalized.
- Results preserve baseline/adjusted mixes, evidence, interval, sample size, rule/version, applied
  delta, and cap status.

## Nodelock and response analysis

- Shared log-odds shifts change already-mixed combo actions while preserving hand ordering.
- Pure zero/one actions stay locked and produce explicit achievable-frequency bounds.
- Baseline, action-inferred, and exploit-adjusted ranges remain separate typed objects.
- Best-response analysis optimizes only over caller-supplied action EVs and reports improvement; it
  is not described as a poker-tree solve.

## Verification

- Synthetic small-sample and extreme-profile regressions pass.
- Nodelock aggregate targets, caps, immutability, and ordering regressions pass.
- Ruff, schema publication, and the full 205-test suite pass.
