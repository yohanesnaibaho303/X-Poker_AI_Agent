# Development Guide

## Requirements

- Windows PowerShell
- Python 3.12 (the Codex workspace bundle is detected automatically)
- Internet access for the first dependency installation

Node.js is present for the later React dashboard but is not required by Milestone 0.

## Setup

From the repository root:

```powershell
.\scripts\bootstrap.ps1
```

This creates `.venv`, verifies Python 3.12, and installs the exact direct dependencies in `pyproject.toml`. The fully resolved environment is recorded in `requirements.lock`.

## Commands

```powershell
# Lint and test
.\scripts\check.ps1

# Lint, test, then start the local API
.\scripts\dev.ps1

# Start without repeating checks
.\scripts\dev.ps1 -SkipChecks

# Re-export JSON Schemas
.\.venv\Scripts\python.exe -m xpoker_agent.schema_export

# Run the deterministic replay fixture
.\.venv\Scripts\python.exe -m xpoker_agent.simulation

# List X-Poker candidates and fail-closed authorization results
.\.venv\Scripts\python.exe -m xpoker_agent.capture.cli

# Record and verify local authorized client-area frames (Git-ignored)
.\.venv\Scripts\python.exe -m xpoker_agent.capture.recording --frames 5
```

The API binds only to `127.0.0.1:8765`. Interactive documentation is available locally at `/docs` while it is running.

## Dependencies

- Pydantic: strict typed contracts and JSON Schema generation.
- FastAPI and Uvicorn: lightweight local API boundary.
- Pytest and Hypothesis: unit and property-based testing.
- Ruff: linting and import/style checks.

No computer-vision, OCR, ML, solver, or browser-shell dependency is installed yet. Those selections require milestone-specific benchmarks.

## Supported functionality

- Authoritative 9-max cash NLH configuration validation.
- Separate table lifecycle, street, seat participation, betting action, and internal event models.
- Exact-decimal stack and pot accounting for the simulated path.
- Deterministic event reduction and replay identifiers.
- Versioned JSON Schemas under `schemas/v1`.
- Observe-only local API with an explicitly unavailable controller.
- X-Poker-only Win32 discovery and machine-local target authorization.
- Occlusion-tolerant client-area capture, canonical BGRA8 normalization, and replay manifests.
- First supported X-Poker 10.0 portrait capture layout at 445×800 and 96 canonical DPI.

## Current limitations

- The first capture layout has broad primary regions; component-specific recognition regions and accuracy calibration belong to Milestone 3.
- No complete visual recognition, OCR, range library, equity engine, GTO data, exploit model, or dashboard exists yet.
- The reducer foundation validates event ordering, cards, chip debits, street changes, and awards for the simulated path; full NLH action-order, minimum-raise, all-in, multiway, and side-pot rules belong to Milestone 4.
- No table input/control implementation exists. Control is disabled in configuration, schemas, and API responses.
- The project license has not been selected; external-source boundaries are documented in ADR 0002.

## Capture privacy and authorization

Copy `configs/capture/authorized_target.example.json` to the ignored
`configs/capture/authorized_target.local.json` only while calibrating an explicitly authorized
X-Poker instance. Live replay frames are written beneath ignored `data/frames/`. Do not commit raw
frames containing account balances, player names, club identifiers, or table identifiers.
