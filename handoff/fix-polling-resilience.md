# Keep polling after isolated errors

## State
F4 implemented and verified locally. Changes remain uncommitted alongside F3; task branch creation was previously declined. No push performed.

## Done
- Each source check catches Exception, reports the source plus exception type/message, and continues to the next source.
- The complete transformation block, including its import, catches unexpected exceptions after the existing specific handlers.
- Watch mode logs unexpected cycle exceptions, sleeps for the configured interval, and retries.
- KeyboardInterrupt remains outside Exception handlers and stops watch mode cleanly.
- Added six offline regression tests covering remaining sources, repeated cycles, unexpected transformation/import failures, watch retries and delays, and interrupt behavior.
- All 12 API tests and four existing transformer tests pass; git diff --check passes.
- Updated pythontest/README.md with polling behavior.

## Next
- Review the local F3/F4 changes and create a branch when authorized before committing.
- Run privacy checks before committing or pushing.

## Files
- pythontest/api_requester.py
- pythontest/test_api_loop.py
- pythontest/README.md

## Resume prompt
Continue from F4's verified local fix. An isolated source, transformation, or watch-cycle Exception must be reported while polling continues. Preserve clean KeyboardInterrupt handling and the pending F3 archive changes.
