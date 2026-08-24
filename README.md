# X-Poker AI Agent

Inspectable Windows AI agent for an explicitly authorized private X-Poker test table.

The supported configurations are X-Poker 6-max and 9-max cash NLH, zero rake, a default 2 BB preflop open, and a chip-EV objective. Layout profiles and strategy artifacts remain table-size-specific. Live table control is disabled and cannot be enabled until the documented accuracy and safety gates pass.

Session setup supports user-selected 6-max or 9-max play and BB or native-chip display. Native values
stay exact internally and render as grouped numbers below 100,000, K from 100,000, and M from
1,000,000. Native values do not convert to BB until the blind is entered or reliably detected.

## Development quick start

PowerShell:

```powershell
.\scripts\bootstrap.ps1
.\scripts\dev.ps1
```

`bootstrap.ps1` creates a local Python 3.12 environment and installs the locked project dependencies. `dev.ps1` runs formatting/lint checks and tests before starting the local API at `http://127.0.0.1:8765`.

To validate without starting the server:

```powershell
.\scripts\check.ps1
```

To run the deterministic simulated hand:

```powershell
.\.venv\Scripts\python.exe -m xpoker_agent.simulation
```

## Current scope

Milestones 0, 1, 2, and 5 are complete. The repository includes capture/calibration, reconstruction
and vision foundations, deterministic range and poker-math engines, and isolated 6-max/9-max
reference priors. The priors are deliberately not labeled GTO. Perception/reconstruction promotion,
GTO integration, the dashboard, and live control remain later gated work.

See [the project plan](docs/PROJECT_PLAN.md), [live status](docs/STATUS.md), and [milestones](docs/MILESTONES.md).
