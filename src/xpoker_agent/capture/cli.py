"""Safe command-line X-Poker candidate discovery."""

from __future__ import annotations

import json

from xpoker_agent.capture.profile import load_target_profile, match_authorized_target
from xpoker_agent.capture.windows import discover_xpoker_windows


def main() -> None:
    profile = load_target_profile()
    candidates = discover_xpoker_windows(classify_visual_role=True)
    output = {
        "profile_id": profile.profile_id,
        "authorization_enabled": profile.enabled,
        "candidate_count": len(candidates),
        "candidates": [
            {
                "process_name": candidate.process_name,
                "window_class": candidate.window_class,
                "client_size": [candidate.client_rect.width, candidate.client_rect.height],
                "dpi": candidate.dpi,
                "visual_role": candidate.visual_role,
                "visual_role_confidence": candidate.visual_role_confidence,
                "match": match_authorized_target(candidate, profile).model_dump(mode="json"),
            }
            for candidate in candidates
        ],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
