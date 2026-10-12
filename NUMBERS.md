# NUMBERS.md — constants and precision decisions

| Constant / value | Decision and reason | Why not half? |
|---|---|---|
| 6 days | The exercise explicitly defines Day 1 through Day 6. | A shorter window would omit required events and the Day 6 capitalization. |
| AED precision: 2 decimal places | AED amounts are specified to fils/cents-style 0.01 precision in the brief. | One decimal place cannot represent valid AED amounts such as 0.05. |
| BHD precision: 3 decimal places | BHD amounts are specified to 0.001 precision in the brief. | Two places would lose valid BHD precision and make the 10.000 total impossible to represent exactly in the stated unit. |
| Overdraft fee: AED 25.00 | Supplied by the task; applied once per account/value day when a negative close is first discovered. | AED 12.50 would contradict the specified fee rather than improve the implementation. |
| Daily interest rate: 0.0004 (0.04%) | Supplied by the task. | 0.0002 would accrue half the required interest. |
| Opening balances: AED 0.00 and BHD 0.000 | Supplied by the task. | Halving zero changes nothing and does not represent a different policy. |
| E1 credit: AED 1,200.00 | Supplied event amount. | Halving it would alter the source event and invalidate the replay. |
| E2 debit: AED 950.00 | Supplied event amount. | Halving it would alter the source event and invalidate the replay. |
| Auth-A hold: AED 200.00 | Supplied authorization amount. | Halving it would test a different authorization. |
| E4 credit: AED 400.00 | Supplied event amount. | Halving it would alter the source event and invalidate the replay. |
| Auth-A settlement: AED 185.00 | Supplied settlement amount. | Halving it would no longer exercise the specified settlement. |
| Auth-Z settlement: AED 180.00 | Supplied event amount; rejected because no Auth-Z authorization exists. | Halving it would not address the missing authorization. |
| E7 debit / E9 reversal: AED 620.00 | Supplied debit and its compensating reversal. | A half-sized reversal would fail to offset the original debit. |
| Auth-B hold: AED 90.00 | Supplied authorization amount. | Halving it would alter the event and the authorization decision. |
| E10 total: BHD 10.000; 3 instalments | Supplied total and count. | Half the total would violate the stated total. Three rounded 3.334 instalments sum to 10.002; residual allocation is necessary. |
| Interest rounding: `ROUND_HALF_UP` | Explicit deterministic rounding rule chosen because the prompt requires rounded amounts but does not name a tie-breaking rule. | A different rule can produce different results at exact half-way values; silent defaults are less auditable. |
| Fee assessment scan: through the event's `posted_day` | A backdated event becomes known only when it is replayed, so only days up through that posting day can be reconsidered. | Scanning only the posting day misses the historical Day 2 overdraft; scanning future days invents facts not yet reached in the replay. |
| Fee uniqueness key: `(account_id, value_day)` | The rule says once per day per account. | Keying only by day could incorrectly suppress fees for another account; keying by event would charge multiple fees for one account/day. |
| Settlement cap: settlement amount ≤ original authorization amount | Conservative interpretation of authorization integrity; this stream's Auth-A settlement is within its hold. | Removing the cap permits settling more than the customer authorized. |
| Batch/instalment allocation: first `n-1` rounded shares, final share = residual | Guarantees the rounded instalments sum exactly to the agreed total. | Equal independent rounding can over- or under-shoot the agreed total. |

No performance tuning constants (batch size, thread count, cache TTL) were invented because this is an in-memory six-day replay, not a throughput benchmark.
