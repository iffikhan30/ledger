# In-Memory Account Ledger Core

A standard-library-only Python implementation of an append-only, in-memory ledger. No web layer, persistence, UI, or database is used.

## Run

```bash
python3 ledger.py
python3 -m unittest discover -s tests -p 'test_ledger.py' -v
```

The script replays the supplied event stream in the exact listed order and prints, for each of Days 1–6, closing ledger balances, active holds, available balances, fee assessments, authorization/settlement states, daily interest accruals, event statuses, and errors.

The deliberately failing design-assumption test is kept out of the passing suite. Run it separately to see the failure that demonstrates why a reversal does not delete prior fee entries:

```bash
python3 tests/known_failure_demo.py
```

That command is expected to exit non-zero. The failure is intentional and annotated inline.

## Key design choices

- Money uses `Decimal`, quantized to AED 0.01 and BHD 0.001 with `ROUND_HALF_UP`.
- Events and ledger entries are immutable dataclasses. Reversals append a compensating entry; they do not mutate or delete the original.
- `posted_day` controls when an event becomes known in the replay; `value_day` controls which historical closes include its ledger entry.
- A late/backdated event triggers a scan of historical days through its posting day. A fee is appended once when a previously unassessed account/day is found negative. Already assessed fees are not silently removed if later events change the historical net balance.
- Authorization holds affect available balance only. Settlement requires an active approved authorization, and releases its hold after an accepted settlement.
- The final interest run uses the final replayed closing balance for each day, rounds each daily accrual to currency precision, and capitalizes the sum once at Day 6.
- Three instalments are allocated as 3.333, 3.333, and 3.334 BHD to preserve the exact 10.000 BHD total.

See `NUMBERS.md`, `AMBIGUITIES.md`, and `REJECTED.md` for detailed reasoning.
