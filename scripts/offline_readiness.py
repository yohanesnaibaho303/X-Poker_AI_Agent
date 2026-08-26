"""Run reproducible offline endurance and packaging checks."""

from __future__ import annotations

import argparse
from pathlib import Path

from xpoker_agent.hardening.offline import (
    machine_exit_code,
    run_offline_readiness,
    write_offline_readiness,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions", type=int, default=100)
    parser.add_argument("--replay-budget-ms", type=float, default=200.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_offline_readiness(sessions=args.sessions, replay_budget_ms=args.replay_budget_ms)
    write_offline_readiness(report, args.output)
    return machine_exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
