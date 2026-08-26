# Decision 0015 — Nine-max and native-chip-only scope

Date: 2026-08-26

## Decision

Supported product configuration is 9-max cash NLH only. All internal amounts, strategy keys,
calculations, logs, APIs, and user-interface values use native chips. Fixed supported blinds are
SB 1 and BB 2 native chips.

User-interface values always use exact grouped native numbers, such as `200,000` or `1,000,000`.
K/M abbreviations are not used.

The 2-chip big blind is a forced contribution, not a default preflop opening raise. Any opening
raise must be observed and recorded as its native-chip amount.

## Consequences

- Remove 6-max selection, profiles, strategy artifacts, fixtures, and supported claims.
- Remove BB display and BB-normalized runtime paths.
- Remove table-size and display-unit choices from session setup.
- Migrate schemas, configurations, range keys, monitoring, tests, and documentation to 9-max native
  SB 1 / BB 2 semantics.
- Preserve historical evaluations as historical evidence marked as predating this decision.
- Keep live control disabled until revised safety and accuracy gates pass.
