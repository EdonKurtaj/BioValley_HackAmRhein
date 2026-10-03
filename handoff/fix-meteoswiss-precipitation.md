# MeteoSwiss precipitation parsing

## State
Done locally. The parser and offline tests pass; a fresh live CSV fetch was not verified because network approval was declined.

## Done
- Read the existing `rre150z0` ten-minute precipitation field from the Basel/Binningen row in the current-observations CSV.
- Save the value in `measurements` with mm metadata. Preserve missing `-` or blank values as `null`, distinct from zero precipitation.
- Keep temperature parsing and HTTP 429 handling working. No forecast source was added.
- Update `docs/SOURCES.md` to describe the fields used.
- Verify with offline tests, Python compilation, `doc-check` and `git diff --check`.

## Next
- When a live MeteoSwiss fetch is allowed, run the requester once and inspect the newly saved Basel/Binningen `rre150z0` value. Do not infer a real reading from the old local snapshot.
- Review and merge this branch separately from `docs/plan`; that plan branch contains the corrected no-forecast scope and is ahead of its remote by two local commits.

## Files
- `pythontest/api_requester.py`
- `pythontest/test_api_requester.py`
- `docs/SOURCES.md`
