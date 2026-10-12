# REJECTED.md — incorrect acceptance criteria and abandoned approaches

## Incorrect acceptance criteria refused

### 1. “E7 causes exactly one overdraft fee to be assessed, on Day 2.” — REJECTED
E7's backdated -620.00 debit makes Day 2's pre-fee close -370.00. It also makes Day 4's pre-fee close negative: 250 - 620 + 400 - 185 = -155.00. The Day 2 fee itself is booked on Day 2 and affects later closes, but Day 4 still closes negative (-180.00 after the Day 2 fee), and Day 5 remains negative after the Day 4 fee (-205.00), so fees are assessed on Days 2, 4, and 5. Fees are once per account per negative day, not once per debit event.

### 2. “After E9, all balances and fees return to their pre-E7 values.” — REJECTED
E9 appends +620.00 against E7's -620.00 using E7's value date; it does not delete or mutate E7. It restores the debit's principal effect, but previously assessed fees remain as separate append-only entries. Under this design, final ACC-001 Day 2 close is 225.00 (250.00 less the Day 2 fee), Day 4 close is 415.00, and Day 5/Day 6 close is 390.00 after the three fees and Auth-A settlement. No fee-reversal rule was supplied.

### 3. “The three BHD instalments in E10 must each be BHD 3.334.” — REJECTED
Three instalments of 3.334 sum to 10.002 BHD, exceeding the agreed 10.000 total. Use 3.333, 3.333, and 3.334 BHD so each is rounded to BHD precision and the sum is exact.

### 4. “If the rounded daily interest accruals do not sum to the capitalized total, the remainder is discarded.” — REJECTED
Discarding a remainder breaks the conservation rule. The capitalized total is defined as the sum of the rounded daily accruals, so no remainder should exist. If a different contract requires a fixed target total, the residual must be allocated explicitly to one accrual; it must not silently disappear.

## Criteria retained (with interpretation)

- **Day 2 close at end of Day 5 before any fee: -370.00 AED.** Retained as a pre-fee historical close: 1,200 - 950 - 620 = -370.00. After fee entries and the later E9 reversal, the final ledger close differs.
- **Auth-A settlement accepted.** Retained: Auth-A was approved for 200.00 and E5 settles 185.00, within the authorized amount. The full hold is released.
- **Unknown authorization settlement rejected.** Retained: E6 references Auth-Z without a preceding authorization and therefore creates no ledger entry.
- **An approved Auth-B hold affects available balance, not ledger balance.** Retained as a rule statement, but in this stream Auth-B is not approved: after E7 and the discovered Day 2/Day 4 fees, available balance is negative. Its hold is therefore zero.

## Approaches abandoned during implementation

- **Mutating E7 to mark it reversed:** abandoned because it violates append-only event/ledger history. E9 is a compensating entry instead.
- **Deleting or recomputing away an already booked overdraft fee after E9:** abandoned because the brief forbids deletion/mutation and supplies no fee-reversal event or policy.
- **Rounding each instalment independently to 3.334:** abandoned because it creates 10.002 BHD from a fixed 10.000 BHD total.
- **Using binary floating point (`float`) for money:** abandoned because binary floating-point cannot exactly represent many decimal fractions and can cause cumulative monetary discrepancies.
- **Treating a settlement as valid merely because its amount is affordable:** abandoned because settlement must be linked to an active approved authorization.
- **Sorting events by posted day before replay:** abandoned because the prompt explicitly requires replay in supplied event-stream order. Posted day and value date remain separate concepts.
- **Silently approving Auth-B after the later E9 reversal:** abandoned because authorization is decided when E8 is replayed; a later reversal does not rewrite an earlier decision.
