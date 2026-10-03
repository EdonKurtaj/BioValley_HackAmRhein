# Unavailable saved port HTML

## State
Fix verified locally. No commit or push performed.

## Done
- Reproduced AttributeError from data: null and FileNotFoundError from a missing HTML file with offline fixtures.
- latest_page treats null data as an empty mapping and raises RuntimeError when the HTML path is unavailable.
- Referenced HTML must be a file; otherwise RuntimeError explains that the fetch needs checking.
- Added regression checks for unavailable paths, missing files, existing HTML, and two successive run_cycle calls after transformation failure.
- All four transformer tests and the HTTP 429 regression test pass; git diff --check passes.

## Next
- Re-run the offline regression tests after further changes.
- Commit only after the repository's privacy and identity checks are complete; preserve unrelated changes.

## Files
- pythontest/transform_port_pegel.py
- pythontest/test_transform_port_pegel.py

## Resume prompt
Continue F2: unavailable port HTML must raise RuntimeError, and run_cycle must report the failure and remain usable. Check this handoff and run the offline regression tests.
