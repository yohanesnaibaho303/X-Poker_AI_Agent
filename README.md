# X-Poker AI Agent

Inspectable Windows AI agent for an explicitly authorized private X-Poker test table.

Supported configuration is X-Poker 9-max cash NLH, zero rake, fixed native-chip blinds SB 1 / BB 2,
and chip EV. The 2-chip big blind is a forced blind, not an opening raise. Live table control is
disabled until documented accuracy and safety gates pass.

Session setup is fixed to 9-max and native chips. Values stay exact internally and render with grouped
digits, including 10,000, 200,000, and 1,000,000. No BB conversion or K/M abbreviation exists.

## Development quick start

PowerShell:

```powershell
.\scripts\bootstrap.ps1
.\scripts\dev.ps1
```

`bootstrap.ps1` creates a local Python 3.12 environment and installs the locked Python and dashboard dependencies. `dev.ps1` runs all checks, builds the dashboard, and starts the local application at `http://127.0.0.1:8765/monitor/`.

To validate without starting the server:

```powershell
.\scripts\check.ps1
```

To run the deterministic simulated hand:

```powershell
.\.venv\Scripts\python.exe -m xpoker_agent.simulation
```

## Current scope

Milestones 0, 1, 2, 5, and 7 are complete. The repository includes capture/calibration,
reconstruction and vision foundations, deterministic range and poker-math engines, isolated
9-max native-chip reference priors, opponent modeling, and a Milestone 8 synthetic-replay monitoring
checkpoint with authorized in-memory capture diagnostics. The priors are deliberately not labeled GTO. Perception/reconstruction promotion,
configuration-matched GTO data, live-session monitoring acceptance, and control remain gated work.

See [the project plan](docs/PROJECT_PLAN.md), [live status](docs/STATUS.md), and [milestones](docs/MILESTONES.md).
