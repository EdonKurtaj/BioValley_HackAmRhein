# Transport risk evidence

## State
Status: done. Implementation and checks complete; Git checkpoint/share in progress on `feat/transport-risk-evidence`, based on the existing `feat/local-risk-assessment` implementation at 1213e0f (not yet main).

## Done
- Added optional verified detector/class/reference-speed and event/version/effect contracts.
- Connected OpenTransportData to observed scoring and existing action policy without changing weights or thermal quality rules.
- Added speed-loss calculation, feed freshness/validity checks, revocation/version checks, candidate JSON, and observed missing-evidence score bounds.
- Kept unknown selected evidence unknown and combined overlapping traffic signals via maximum.
- Extended collector event metadata; older event snapshots require refresh.
- Added calculation and integration checks; repaired existing archive test's missing mock for the previously added OTD source.
- Documented assumptions and CLI usage. No packages or database changes.

## Next
128 automated checks passed (76 risk/integration and 52 collector), observed CLI and full scenario JSON ran successfully, documentation and whitespace checks passed. No formatter is configured/installed in this standard-library project. Save/share the checkpoint; do not merge without approval.

## Limits
No shipment routes or normal speeds are invented. Operator assertions must identify the remaining route, direction, vehicle applicability and comparable normal speed. No calibrated delay or damage probability. No ETA inference. Minute counters expire after five minutes; use minute watch mode for fresh evidence. Event effect is explicitly reviewed per source version; recurring validity is excluded.

## Resume
Read this handoff and `docs/risk-assessment.md` (OpenTransportData section), inspect the working diff, complete checks and checkpoint the transport evidence integration. Preserve existing risk/collector work.
