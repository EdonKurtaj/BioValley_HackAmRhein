# Rhine history window and MeteoSwiss cleanup

## State
F6 and F7 implemented and verified locally. Changes are uncommitted; no push performed. Prior branch creation was declined.

## Done
- Probed the public Rhine endpoint: 200 and 101 return HTTP 400 with a maximum limit of 100; 100 returns exactly 100 rows.
- Set the Rhine request to a central 48-row constant in source params, with URL encoding and the full request URL recorded in results. Traffic remains at 10.
- Removed the unused STAC station-fetch function, metadata loader, and metadata URL constant after checking for callers throughout the repository, including tests and the port transformer.
- Kept the numeric CSV parser and all still-used imports.
- Added three tests for request parameters, unchanged traffic size, and exact MeteoSwiss status formatting.
- All 15 API tests and four transformer tests pass; py_compile, import usage inspection, and git diff --check pass.
- Live --once returned HTTP 200 for all five sources and transformed port data successfully. The saved Rhine latest.json contains 48 rows; traffic contains 10. MeteoSwiss status formatting is unchanged.
- Recorded limit probes, the observed history span, and validation in docs/data-notes.md.

## Next
- Review and create a branch when authorized before committing.
- Run the repository privacy checks before committing or pushing.

## Files
- pythontest/api_requester.py
- pythontest/test_api_params.py
- docs/data-notes.md
- pythontest/README.md

## Resume prompt
Continue from the verified F6/F7 changes: Rhine uses 48 rows, traffic remains at 10, and unused MeteoSwiss STAC code is removed. Review local changes and data-notes before sharing.
