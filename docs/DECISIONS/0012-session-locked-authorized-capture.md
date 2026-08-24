# Decision 0012 — Session-locked authorized capture

## Status

Accepted on 2026-08-24.

## Decision

Require full authorization at continuous-observation startup: allowlisted X-Poker executable hash
and process, window class, supported geometry, and high-confidence visual table role. After that
gate passes, lock the exact PID and HWND into the target fingerprint and select only that identity
for subsequent read-only frames.

Do not require the visual-role classifier to pass again on every in-hand animation. Continue to
record its confidence as diagnostic evidence. Stop immediately if the PID, HWND, executable,
class, geometry, or derived target fingerprint changes.

## Consequences

- Transient table animations and overlays no longer create false "zero eligible table" failures.
- A different X-Poker table window cannot silently replace the authorized session target.
- Re-entering from a lobby or starting another table requires a fresh full authorization gate.
- This decision authorizes read-only capture only; future control must independently reverify the
  target and all control gates at action time.
