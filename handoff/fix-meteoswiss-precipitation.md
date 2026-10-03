# MeteoSwiss current-weather parsing

## State
Done locally. The parser and offline tests pass, and a fresh live Basel/Binningen fetch saved the full station row.

## Done
- Read and save every current-weather measurement column from the Basel/Binningen row, including temperature, ten-minute precipitation, wind, gusts, radiation and humidity.
- Preserve missing `-` or blank values as `null`, distinct from zero precipitation. Add labels and units for the fields likely to inform risk assessment.
- Keep temperature parsing and HTTP 429 handling working. No forecast source was added.
- Update `docs/SOURCES.md` and `docs/data-signals.md` to describe the fields and their limits.
- Verify with offline tests, Python compilation, `doc-check` and `git diff --check`.
- Run the updated requester against the live CSV: the 3 October 2026 11:20 local observation saved 12 numeric readings from 20 fields, with eight unavailable fields as `null`.

## Next
- Build risk rules that use the weather fields only as external hazard signals; product-temperature and packaging evidence still need separate inputs.
- Review and merge this branch separately from `docs/plan`; that plan branch contains the corrected no-forecast scope and is ahead of its remote by two local commits.

## Files
- `pythontest/api_requester.py`
- `pythontest/test_api_requester.py`
- `docs/SOURCES.md`
