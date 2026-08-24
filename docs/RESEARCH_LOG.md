# Autonomous Research Log

## 2026-08-24 — Milestone 1 bootstrap

### Registered

- Official X-Poker Apple App Store listing: product/version/interface bootstrap, proprietary assets.
- GTO Wizard web application: conceptual/UI reference only; no assumed numerical-data access.
- PokerGPT repository: MIT architectural reference with six-player/PokerStars incompatibility noted.
- `dickreuter/Poker` repository: GPL-3.0 clean-room architectural reference only.
- Two public X-Poker interface articles: low-to-medium-confidence terminology evidence only.
- DriveHUD X-Poker setup video: YouTube video ID `IWckPxZyZ10`, discovered through the DriveHUD knowledge-base embed.
- PokerStars Learn NLH rules reference for deterministic rules cross-checking.
- GTO Wizard range-interface and equity-education references, explicitly separated from numerical solution artifacts.

### Evidence status

- Public articles describe X-Poker action buttons, sliders, hand history, and chip balance.
- Apple Lookup metadata identified version 1.12.0 and six iPhone plus six iPad screenshot URLs. Temporary iPhone copies were visually reviewed and not committed; OS-temp cleanup was blocked by execution policy.
- Official screenshots directly show the oval table, seats/stacks, hero and board cards, center pot labels, per-seat chip/amount indicators, transient Check/Fold labels, and Fold/Check/Bet/Call controls.
- Direct YouTube transcript/frame retrieval was throttled during this pass. The video is metadata-only and no component claim is derived from unseen frames.
- The initial component catalog has representative public evidence for all 12 critical targets. Higher-resolution iPad screenshots show a dealer marker, blind-posting amounts, Action Time settings, and yellow multi-table countdown bars. Raise/all-in controls, side-pot rendering, and exact active-seat highlighting remain partial subcomponent gaps for authorized-instance calibration.
- The asset manifest retains metadata only in this pass; no copyrighted screenshots, frames, or transcripts were committed.

### Next research pass

1. Revisit the registered video through a permitted accessible transcript or public embed.
2. Locate additional public gameplay footage with visible betting rounds rather than setup-only material.
3. Record representative-frame manifests only after use/license review; do not commit copyrighted video frames by default.
4. Verify the four unresolved critical components and classify layout, theme, orientation, version, game type, and street.
5. Calibrate exact regions later against the explicitly authorized running instance.

## 2026-08-24 — Milestone 5 range-source audit

- Audited public multi-player preflop solver and chart candidates for 6-max and 9-max coverage.
- Pinned `bmorrow10/preflopR` at commit `aed511d0451aea33a14f7e9204595fc2211f233f`.
- Verified its MIT license and recorded the upstream raw file SHA-256.
- Imported only its 6-player and 9-player unopened raise/fold charts as reference priors.
- Expanded each 169-class chart deterministically to all 1,326 physical combinations.
- Mapped upstream nine-player `UTG+2` to project `MP` and upstream `MP` to project `LJ`.
- Kept every artifact at confidence 0.55 with explicit warnings: upstream calls the charts
  approximate/not solver-derived and does not specify stack, rake, or open sizing.
- These artifacts complete the range-rendering foundation but do not satisfy Milestone 6's GTO
  solution requirement.
