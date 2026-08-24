# Development Guide

## Requirements

- Windows PowerShell
- Python 3.12 (the Codex workspace bundle is detected automatically)
- Node.js 22 and npm 10
- Internet access for the first dependency installation

The React dashboard is built into local static assets and is served by the same loopback-only API.

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

# Reproduce pinned, hash-verified reference-prior range artifacts
.\.venv\Scripts\python.exe scripts\import_preflopr_reference.py

# List X-Poker candidates and fail-closed authorization results
.\.venv\Scripts\python.exe -m xpoker_agent.capture.cli

# Record and verify local authorized client-area frames (Git-ignored)
.\.venv\Scripts\python.exe -m xpoker_agent.capture.recording --frames 5
```

The application binds only to `127.0.0.1:8765`. The dashboard is available at `/monitor/` and interactive API documentation at `/docs` while it is running.

## Dependencies

- Pydantic: strict typed contracts and JSON Schema generation.
- FastAPI and Uvicorn: lightweight local API boundary.
- WebSockets: local schema-versioned monitoring updates.
- React, TypeScript, and Vite: local monitoring dashboard and production bundle.
- Pytest and Hypothesis: unit and property-based testing.
- Ruff: linting and import/style checks.

Milestone 3 adds small Windows-only Python projections for the operating system's local
`Windows.Media.Ocr` engine. No Pillow, OpenCV, Tesseract, ONNX Runtime, ML model, solver, or
browser-shell dependency is installed. The Windows OCR selection remains provisional until the
X-Poker-specific held-out benchmark passes.

The range importer uses only the Python standard library. It downloads a pinned MIT source file,
verifies its SHA-256, and fails closed on drift. Its generated artifacts are reference priors, not
GTO solutions.

## Supported functionality

- Authoritative 6-max and 9-max cash NLH configuration validation.
- Separate table lifecycle, street, seat participation, betting action, and internal event models.
- Exact-decimal stack and pot accounting for the simulated path.
- Deterministic event reduction and replay identifiers.
- Versioned JSON Schemas under `schemas/v1`.
- Observe-only local API with an explicitly unavailable controller.
- X-Poker-only Win32 discovery and machine-local target authorization.
- Occlusion-tolerant client-area capture, canonical BGRA8 normalization, and replay manifests.
- First supported X-Poker 10.0 portrait capture layout at 445×800 and 96 canonical DPI.
- Canonical 1,326-combo ranges, 169-class projection, blockers, action conditioning, and matrices.
- Exact/seeded equity, exhaustive hand evaluation, and deterministic chip-EV metrics.
- Hash-verified, isolated 6-max and 9-max reference-prior RFI libraries.
- Synthetic 6-max/9-max monitoring replay with bounded WebSocket delivery, gap recovery, health,
  action history, range matrix inspection, and explicit control lockout.

## Current limitations

- The first capture layout has broad primary regions; component-specific recognition regions and accuracy calibration belong to Milestone 3.
- Visual recognition and reconstruction promotion still require held-out complete X-Poker replays.
- Reference priors are approximate and low-confidence; no configuration-matched GTO data exists yet.
- The exploit model is complete for synthetic profiles but is not connected to live reconstructed observations.
- The monitoring dashboard currently consumes synthetic replays. Capture overlays, opponent-range
  views, resolved strategy/math panels, and authorized complete-session soak evidence remain pending.
- No table input/control implementation exists. Control is disabled in configuration, schemas, and API responses.
- The project license has not been selected; external-source boundaries are documented in ADR 0002.

## Capture privacy and authorization

Copy `configs/capture/authorized_target.example.json` to the ignored
`configs/capture/authorized_target.local.json` only while calibrating an explicitly authorized
X-Poker instance. Live replay frames are written beneath ignored `data/frames/`. Do not commit raw
frames containing account balances, player names, club identifiers, or table identifiers.
