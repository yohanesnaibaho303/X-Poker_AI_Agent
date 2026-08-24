# Milestone 2 Evaluation

- Date: 2026-08-24
- Scope: Authorized X-Poker window capture and layout calibration
- Runtime target: X-Poker 10.0 for Windows only
- Control mode: Disabled; read-only capture only

## Authorized-instance result

- X-Poker candidates discovered: 2.
- Authorized table candidates after all gates: 1.
- Sibling lobby candidates rejected: 1.
- Process: `X-Poker.exe`.
- Window class: `GLFW30`.
- Source client geometry: 445×800 at 96 DPI.
- Canonical geometry: 445×800 BGRA8 at 96 DPI, portrait.
- Table visual-role confidence: 0.95.
- Five-frame replay: one stable target fingerprint and five changing content hashes.
- Mean end-to-end capture latency: 71.6 ms.
- Deterministic replay verification issues: 0.
- Full automated suite: 56 tests passed; Ruff passed.

## Commands

```powershell
.\.venv\Scripts\python.exe -m xpoker_agent.capture.cli
.\.venv\Scripts\python.exe -m xpoker_agent.capture.recording --frames 5
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\pytest.exe
```

## Safety and privacy evidence

- The table was spectated only; no mouse, keyboard, seat, bet, or action input was sent.
- Authorization requires X-Poker identity, allowlisted executable/class/title, executable hash when configured, and a high-confidence table visual role.
- Every frame rediscovers and revalidates the target, so movement is followed and minimization, identity loss, ambiguity, or multiple eligible tables stop capture.
- The lobby and table have identical metadata and dimensions; the stable table hamburger anchor distinguishes the table from the lobby back-button geometry.
- The machine-local authorization profile and raw live replay are Git-ignored.
- No account balance, player name, club ID, table ID, or raw authorized-instance screenshot is committed.

## Supported-layout boundary

The versioned `xpoker-windows-10-portrait-v1` profile defines canonical capture geometry, broad
table/board/pot/seat/action regions, and the first stable anchor. These broad regions satisfy
capture calibration; component-level recognition regions and accuracy targets remain Milestone 3.
