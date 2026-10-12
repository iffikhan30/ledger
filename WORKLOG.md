# WORKLOG.md

All timestamps below are UTC wall-clock timestamps recorded during this build session. They describe the actual work performed in this repository.

- 2026-10-12T19:36:55Z — Created repository directory and started the ledger implementation.
- 2026-10-12T19:37:00Z — Implemented immutable event/entry models, currency-specific Decimal rounding, event replay, authorization holds, settlement validation, compensating reversals, fee discovery, instalment residual allocation, and end-of-window interest capitalization.
- 2026-10-12T19:37:00Z — Added the passing unit test suite and a separately runnable, intentionally failing test documenting the mistaken assumption that a reversal erases fee entries.
- 2026-10-12T19:37:00Z — Documented constants, ambiguity resolutions, rejected acceptance criteria, and abandoned approaches.
- 2026-10-12T19:37:00Z — Pending verification: run the replay, passing tests, and expected-failure demonstration; record results before final packaging.
- 2026-10-12T19:37:30Z — First verification found an additional Day 5 overdraft fee: after Day 2 and Day 4 fees, Day 5 also remains negative. Updated the test and rejection reasoning to include fees on Days 2, 4, and 5.
- 2026-10-12T19:38:00Z — Passing suite verified (6 tests). Replay output verified; renamed hold/available fields to clarify that these are current active holds/current availability, while closes are value-date based.
- 2026-10-12T19:39:00Z — Final verification complete: all 6 standard tests pass; the separately invoked annotated known-failure test exits non-zero as intended. The script prints all six daily closes, fees, authorization states, event statuses, errors, and capitalized interest. Repository has four non-squashed commits.
