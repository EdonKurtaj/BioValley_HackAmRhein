# Raw HTML retention and Swiss numeric formats

## State
F8/F9 implemented and verified locally. Changes are uncommitted; no push performed. Prior branch creation was declined.

## Done
- Confirmed successful HTML fetches had no retention limit.
- Added RAW_KEEP=50 and cleanup ordered by timestamp filename after successful latest/history writes. The current latest HTML is protected, including when its timestamp sorts behind other files.
- Verified 60 simulated saves retain exactly 50 newest files and an existing latest reference. Also tested a backwards clock and failed latest write.
- Searched saved HTML for digit-apostrophe-digit patterns; no straight or curly apostrophes were found in numeric values.
- Added a shared Swiss-number parser and reused it for current readings, flood discharge thresholds, and forecasts. It handles grouping apostrophes/spaces, signed values, and comma decimals; approximation prefixes and units are parsed separately.
- Preserved existing integer measurement values and float forecast fields.
- Compared transformation output before/after on existing saved pages: serialized JSON identical except for generated updated_at.
- All 27 regression tests, py_compile, and git diff --check pass. Updated archive and data notes.

## Next
- Review and create a branch when authorized before committing.
- Run repository privacy checks before committing or pushing.

## Files
- pythontest/api_requester.py
- pythontest/transform_port_pegel.py
- pythontest/test_api_retention.py
- pythontest/test_parse_swiss_number.py
- pythontest/README.md
- docs/data-notes.md

## Resume prompt
Continue the verified F8/F9 changes. Keep at most 50 HTML files per source after successful saves while protecting latest.json's reference, and accept Swiss numeric formats without changing existing output.
