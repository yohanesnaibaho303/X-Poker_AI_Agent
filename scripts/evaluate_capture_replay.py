"""Run production recognition over a recorded authorized capture manifest."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from xpoker_agent.vision.replay import (
    diagnose_capture_replay,
    write_recognition_replay_report,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = asyncio.run(diagnose_capture_replay(args.manifest))
    write_recognition_replay_report(report, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
