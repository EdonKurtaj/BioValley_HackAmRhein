# Preserve successful source data after fetch failures

## State
F3 verified locally. Changes are uncommitted on main because task branch creation was declined. No push performed.

## Done
- save_result updates latest.json and raw HTML only for successful requests.
- Failed requests write last_error.json and append history without replacing the successful snapshot.
- check_source's storage-error fallback writes latest.json only when request_ok is true.
- Added five archive regression tests covering HTML, JSON, MeteoSwiss, network outages, HTTP 503/429, initial failure, recovery, storage failure, and two CLI --once cycles.
- Six API tests and four port transformer tests pass; git diff --check passes.
- Live acceptance passed in an isolated temporary directory: all five public sources returned HTTP 200, followed by a simulated network outage. All source latest.json and raw files remained byte-identical, last_error.json appeared, and each history gained one line.
- Port transformation succeeded after the outage with the original current and forecast fetch times.
- Archive behavior and test commands are documented in pythontest/README.md.

## Next
- Review local changes and create a branch when authorized before committing.
- Run required privacy hooks before committing or pushing.

## Files
- pythontest/api_requester.py
- pythontest/test_api_archive.py
- pythontest/README.md

## Resume prompt
Continue from F3's verified local fix. Preserve the last successful source snapshot on errors; review the uncommitted diff and follow repository privacy and branch rules before sharing.
