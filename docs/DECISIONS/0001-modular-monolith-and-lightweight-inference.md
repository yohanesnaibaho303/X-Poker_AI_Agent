# ADR 0001: Modular monolith and lightweight-first inference

- Status: Accepted
- Date: 2026-08-24

## Context

The agent spans capture, vision, state reconstruction, poker mathematics, strategy, monitoring, and eventually gated control. The first version targets one Windows machine and one authorized table. Multiple services and heavyweight models would increase deployment cost and latency before their value is measured.

## Decision

Begin with a modular Python 3.12 monolith behind explicit typed boundaries, a local FastAPI/WebSocket interface, SQLite metadata storage, and a React/TypeScript dashboard. Prefer geometry, templates, change detection, and specialized OCR. Use ONNX Runtime for learned inference when required; use PyTorch primarily for offline training.

Modules may move to separate processes only after profiling demonstrates an isolation, reliability, or throughput need.

## Consequences

- Initial setup, resource use, debugging, and packaging stay comparatively small.
- Domain boundaries must be enforced through packages, schemas, and tests rather than network separation.
- A slow or unstable component could affect the process, so health checks and bounded queues are required.
- Later extraction remains possible because persisted and API-facing contracts are versioned.

## Alternatives considered

- Independent microservices from the start: rejected as unnecessary operational overhead for one local table.
- End-to-end general vision-language inference: rejected as the sole perception path because it is heavier, harder to validate, and unsuitable as the only source of observed state.

