# Presentation launcher

## State
Status: done. Implemented one-command startup on feat/presentation-launcher, based on the verified reroute demo branch.

## Done
- Builds frontend, installs only declared dependencies if missing, checks port availability, opens browser after HTTP readiness.
- Reuses dashboard server to start/stop its API requester; Ctrl+C cleans up the collector.
- Supports custom port, no-browser and an existing collector.
- README contains the presentation command.

## Next
Launch verified on port 8011: build passed, website and reroute API returned HTTP 200, collector fetched and stored measurements, Ctrl+C stopped the process. Review and merge only after explicit approval.
