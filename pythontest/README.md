# Public source requester

Run one fetch cycle from the repository root:

```sh
python3 pythontest/api_requester.py --once
```

Without `--once`, the requester repeats every 600 seconds. Use `--interval` to change the interval.

Unexpected source errors are logged with their exception type and message; polling continues with the remaining sources. Transformation errors are reported without ending the cycle. In watch mode, an unexpected cycle error is logged before waiting the configured interval and retrying. Ctrl+C stops the requester cleanly.

Each source has a local folder under `pythontest/data/`:

- `latest.json` contains the last successful response. Failed requests leave it unchanged; `checked_at` is the time of that successful fetch.
- `last_error.json` contains the most recent failed request, including its status, error, and fetch time. It remains after recovery as an error record.
- `history.jsonl` records every fetch attempt, successful or failed, when storage is writable.
- `raw/` stores HTML from successful requests only. Failed requests leave these files unchanged.

The port transformer reads the last successful HTML. Its `current_page_checked_at` and `forecast_page_checked_at` retain the original fetch times, so consumers can identify stale data. If a source has never succeeded, no `latest.json` is created.

Run the offline archive regression checks:

```sh
python3 -m unittest discover -s pythontest -p 'test_api*.py' -v
python3 -m unittest discover -s pythontest -p test_transform_port_pegel.py -v
```
