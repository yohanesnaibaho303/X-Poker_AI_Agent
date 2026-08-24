# Decision 0009 — Nine-max layout calibration and stable window identity

## Status

Accepted on 2026-08-24.

## Decision

Use a dedicated X-Poker 10.0 portrait 9-max profile with canonical seats numbered clockwise from
the bottom seat. Each seat has a versioned avatar/empty-anchor region and player-panel region.
Occupancy is classified as `occupied`, `empty`, or `ambiguous` using deterministic panel and plus
evidence; player names are not identity inputs.

Do not require the club administrator's mutable room title for authorization. Require the
allowlisted X-Poker executable SHA-256, process name, GLFW window class, supported client geometry,
and high-confidence visual table classification. PID and HWND are recorded only for the running
session and are expected to change after restart. More than one eligible table remains a
fail-closed error.

## Evidence and consequences

- Authorized 445×800 idle evidence exposed all nine anchors with five occupied and four empty.
- The first playing frame exposed three occupied and six empty, a full board, pot text, and a
  positive Bomb Pot countdown.
- Side empty anchors move a few pixels relative to occupied avatars, so plus detection searches
  within the calibrated anchor region rather than assuming one exact center pixel.
- Nine-max is the primary calibration target; the separate 6-max profile remains supported.
- This checkpoint calibrates geometry only. Card, stack, bet, dealer, player-status, and temporal
  action accuracy still require larger held-out live/replay evidence before promotion.
